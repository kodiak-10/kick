import Combine
import PhotosUI
import SwiftUI

enum VideoAnalysisStage: Equatable {
    case idle
    case loadingSelection
    case ready
    case analyzing
    case slowProcessing
    case timeoutFailed
    case failed(String)

    var isBusy: Bool {
        switch self {
        case .loadingSelection, .analyzing, .slowProcessing:
            return true
        case .idle, .ready, .timeoutFailed, .failed:
            return false
        }
    }
}

enum VideoAnalysisProgressPhase: Int, CaseIterable, Hashable {
    case uploading
    case recognizingAction
    case generatingFeedback

    var title: String {
        switch self {
        case .uploading:
            return "正在上传视频"
        case .recognizingAction:
            return "正在确认动作类型"
        case .generatingFeedback:
            return "正在生成训练反馈"
        }
    }

    var detail: String {
        switch self {
        case .uploading:
            return "视频正在发送到后端，请稍候。"
        case .recognizingAction:
            return "系统会辅助判断动作趋势，但当前以你选择的动作类型为准。"
        case .generatingFeedback:
            return "系统正在整理结论、问题和训练建议。"
        }
    }
}

@MainActor
final class VideoAnalysisFlowViewModel: ObservableObject {
    @Published private(set) var selectedVideo: ImportedVideo?
    @Published private(set) var selectedAction: AnalysisActionChoice?
    @Published private(set) var stage: VideoAnalysisStage = .idle
    @Published private(set) var analysisPhase: VideoAnalysisProgressPhase = .uploading
    @Published private(set) var debugState = VideoAnalysisDebugState()

    private let service: VideoAnalysisService
    let requestTimeoutSeconds: TimeInterval
    private var activeAnalysisID: UUID?
    private var activeAnalysisTask: Task<VideoAnalysisResponse, Error>?
    private var phasePromotionTask: Task<Void, Never>?
    private var slowProcessingTask: Task<Void, Never>?
    private var timeoutTask: Task<Void, Never>?
    private var didReachTimeout = false

    init(service: VideoAnalysisService? = nil) {
        let resolvedService = service ?? VideoAnalysisService(configuration: .live)
        self.service = resolvedService
        self.requestTimeoutSeconds = resolvedService.requestTimeoutSeconds
    }

    var statusMessage: String? {
        if case let .failed(message) = stage {
            return message
        }
        return nil
    }

    var statusTitle: String {
        switch stage {
        case .idle:
            return "等待选择"
        case .loadingSelection:
            return "正在读取视频"
        case .ready:
            return selectedVideo == nil ? "等待选择" : "视频已就绪"
        case .analyzing:
            return "分析中"
        case .slowProcessing:
            return "继续处理中"
        case .timeoutFailed:
            return "分析超时"
        case .failed:
            return "分析失败"
        }
    }

    var statusSubtitle: String {
        switch stage {
        case .idle:
            return "请先从相册选择一个本地视频。"
        case .loadingSelection:
            return "正在准备文件与预览，请稍候。"
        case .ready:
            return selectedVideo == nil ? "请先从相册选择一个本地视频。" : "视频已保留，可以开始分析。"
        case .analyzing:
            return analysisPhase.detail
        case .slowProcessing:
            return "分析时间比平时更长，仍在继续尝试。当前视频已保留，无需重新选择。"
        case .timeoutFailed:
            return "当前视频较长或分析较复杂，建议等待更久，或换 5-8 秒的单一动作视频"
        case .failed(let message):
            return message
        }
    }

    func loadVideo(from item: PhotosPickerItem) async {
        stage = .loadingSelection
        debugState = VideoAnalysisDebugState()

        do {
            guard let importedFile = try await item.loadTransferable(type: ImportedVideoFile.self) else {
                throw VideoAnalysisFlowError.unableToLoadVideo
            }

            selectedVideo = try await ImportedVideo.make(from: importedFile.url)
            stage = .ready
            analysisPhase = .uploading
        } catch {
            selectedVideo = nil
            stage = .failed(message(for: error))
        }
    }

    func selectAction(_ action: AnalysisActionChoice) {
        cancelAnalysisLifecycle()
        selectedAction = action
        analysisPhase = .uploading
        debugState = VideoAnalysisDebugState()
        stage = selectedVideo == nil ? .idle : .ready
    }

    func clearActionSelection() {
        cancelAnalysisLifecycle()
        selectedAction = nil
        analysisPhase = .uploading
        debugState = VideoAnalysisDebugState()
        stage = selectedVideo == nil ? .idle : .ready
    }

    func analyze(selectedAction: AnalysisActionChoice) async throws -> VideoAnalysisResponse {
        guard selectedVideo != nil else {
            stage = .failed("请先选择一个视频。")
            throw VideoAnalysisFlowError.noVideoSelected
        }

        cancelAnalysisLifecycle()
        debugState = VideoAnalysisDebugState()
        didReachTimeout = false
        analysisPhase = .uploading
        stage = .analyzing

        let sessionID = UUID()
        activeAnalysisID = sessionID

        schedulePhasePromotion(for: sessionID)
        scheduleSlowProcessingTimer(for: sessionID)
        scheduleTimeoutTimer(for: sessionID)

        guard let videoURL = selectedVideo?.url else {
            stage = .failed("请先选择一个视频。")
            throw VideoAnalysisFlowError.noVideoSelected
        }

        let task = Task<VideoAnalysisResponse, Error> { [service] in
            try await service.analyzeVideo(fileURL: videoURL, selectedAction: selectedAction) { [weak self] event in
                Task { @MainActor [weak self] in
                    self?.apply(event, sessionID: sessionID)
                }
            }
        }
        activeAnalysisTask = task

        do {
            let response = try await task.value
            finishAnalysisLifecycle(for: sessionID)
            stage = .ready
            analysisPhase = .uploading
            return response
        } catch is CancellationError {
            let timedOut = didReachTimeout
            finishAnalysisLifecycle(for: sessionID)
            analysisPhase = .uploading

            if timedOut {
                stage = .timeoutFailed
                throw VideoAnalysisFlowError.analysisTimedOut
            }

            stage = selectedVideo == nil ? .idle : .ready
            throw VideoAnalysisFlowError.analysisCancelled
        } catch let error as URLError where error.code == .cancelled {
            let timedOut = didReachTimeout
            finishAnalysisLifecycle(for: sessionID)
            analysisPhase = .uploading

            if timedOut {
                stage = .timeoutFailed
                throw VideoAnalysisFlowError.analysisTimedOut
            }

            stage = selectedVideo == nil ? .idle : .ready
            throw VideoAnalysisFlowError.analysisCancelled
        } catch {
            finishAnalysisLifecycle(for: sessionID)
            analysisPhase = .uploading
            stage = .failed(message(for: error))
            throw error
        }
    }

    func requireActionSelection() {
        stage = .failed("请先选择本次要分析的动作类型")
    }

    func resetSelection() {
        cancelAnalysisLifecycle()
        selectedVideo = nil
        selectedAction = nil
        stage = .idle
        analysisPhase = .uploading
        debugState = VideoAnalysisDebugState()
    }

    func cancelAnalysis() {
        guard stage == .analyzing || stage == .slowProcessing else {
            return
        }

        cancelAnalysisLifecycle()
        didReachTimeout = false
        analysisPhase = .uploading
        stage = selectedVideo == nil ? .idle : .ready
    }

    private func apply(_ event: VideoAnalysisServiceEvent, sessionID: UUID) {
        guard activeAnalysisID == sessionID else { return }

        switch event {
        case .requestURL(let requestURL):
            debugState.requestURL = requestURL
        case .requestTimeout(let requestTimeout):
            debugState.requestTimeoutSeconds = requestTimeout
        case .multipartFieldNames(let fieldNames):
            debugState.multipartFieldNames = fieldNames
        case .filename(let filename):
            debugState.filename = filename
        case .mimeType(let mimeType):
            debugState.mimeType = mimeType
        case .requestBodySize(let requestBodySize):
            debugState.requestBodySize = requestBodySize
        case .uploadStarted:
            debugState.uploadStarted = true
            stage = .analyzing
            analysisPhase = .uploading
        case .uploadFinished:
            debugState.uploadFinished = true
            stage = .analyzing
            analysisPhase = .recognizingAction
            scheduleGeneratingFeedbackTimer(for: sessionID)
        case .responseReceived:
            debugState.responseReceived = true
            stage = .analyzing
            analysisPhase = .generatingFeedback
        case .responseStatusCode(let statusCode):
            debugState.responseStatusCode = statusCode
        case .responseTextPreview(let responseTextPreview):
            debugState.responseTextPreview = responseTextPreview
        case .errorMessage(let message):
            debugState.errorMessage = message
        }
    }

    private func scheduleGeneratingFeedbackTimer(for sessionID: UUID) {
        phasePromotionTask?.cancel()
        phasePromotionTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 5_000_000_000)
            await MainActor.run {
                guard let self,
                      self.activeAnalysisID == sessionID,
                      self.stage == .analyzing,
                      self.analysisPhase == .recognizingAction else {
                    return
                }

                self.analysisPhase = .generatingFeedback
            }
        }
    }

    private func schedulePhasePromotion(for sessionID: UUID) {
        phasePromotionTask?.cancel()
        phasePromotionTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 8_000_000_000)
            await MainActor.run {
                guard let self,
                      self.activeAnalysisID == sessionID,
                      self.stage == .analyzing,
                      self.analysisPhase == .uploading else {
                    return
                }

                self.analysisPhase = .recognizingAction
            }
        }
    }

    private func scheduleSlowProcessingTimer(for sessionID: UUID) {
        slowProcessingTask?.cancel()
        slowProcessingTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 20_000_000_000)
            await MainActor.run {
                guard let self,
                      self.activeAnalysisID == sessionID,
                      self.stage == .analyzing else {
                    return
                }

                self.stage = .slowProcessing
            }
        }
    }

    private func scheduleTimeoutTimer(for sessionID: UUID) {
        timeoutTask?.cancel()
        timeoutTask = Task { [weak self] in
            let timeoutNanoseconds = UInt64((self?.requestTimeoutSeconds ?? 60) * 1_000_000_000)
            try? await Task.sleep(nanoseconds: timeoutNanoseconds)
            await MainActor.run {
                guard let self,
                      self.activeAnalysisID == sessionID,
                      self.stage == .analyzing || self.stage == .slowProcessing else {
                    return
                }

                self.didReachTimeout = true
                self.stage = .timeoutFailed
                self.activeAnalysisTask?.cancel()
            }
        }
    }

    private func finishAnalysisLifecycle(for sessionID: UUID) {
        guard activeAnalysisID == sessionID else { return }
        cancelAnalysisLifecycle()
    }

    private func cancelAnalysisLifecycle() {
        activeAnalysisID = nil
        activeAnalysisTask?.cancel()
        activeAnalysisTask = nil
        phasePromotionTask?.cancel()
        phasePromotionTask = nil
        slowProcessingTask?.cancel()
        slowProcessingTask = nil
        timeoutTask?.cancel()
        timeoutTask = nil
    }

    private func message(for error: Error) -> String {
        if let serviceError = error as? VideoAnalysisServiceError {
            return serviceError.localizedDescription
        }

        if let urlError = error as? URLError {
            switch urlError.code {
            case .notConnectedToInternet,
                 .networkConnectionLost,
                 .cannotConnectToHost,
                 .cannotFindHost,
                 .dnsLookupFailed,
                 .timedOut:
                if urlError.code == .timedOut {
                    return "当前视频较长或分析较复杂，建议等待更久，或换 5-8 秒的单一动作视频"
                }
                return "后端不可达，请检查网络或服务器地址。"
            default:
                return "网络请求失败，请稍后再试。"
            }
        }

        return "无法处理当前视频，请重新选择后再试。"
    }
}

private enum VideoAnalysisFlowError: LocalizedError {
    case noActionSelected
    case noVideoSelected
    case unableToLoadVideo
    case analysisCancelled
    case analysisTimedOut

    var errorDescription: String? {
        switch self {
        case .noActionSelected:
            return "请先选择本次要分析的动作类型"
        case .noVideoSelected:
            return "请先选择一个视频。"
        case .unableToLoadVideo:
            return "无法读取当前视频，请重新选择。"
        case .analysisCancelled:
            return "分析已取消。"
        case .analysisTimedOut:
            return "当前视频较长或分析较复杂，建议等待更久，或换 5-8 秒的单一动作视频"
        }
    }
}
