import Foundation

enum AnalysisBackendConfig {
    static var baseURL: URL {
        if let override = ProcessInfo.processInfo.environment["KICK_BACKEND_BASE_URL"],
           let url = URL(string: override) {
            return url
        }

        if let plistOverride = Bundle.main.object(forInfoDictionaryKey: "KickBackendBaseURL") as? String,
           let url = URL(string: plistOverride) {
            return url
        }

        return URL(string: "http://127.0.0.1:8000")!
    }
    static let healthPath = "health"
    static let analyzePath = "analyze_video"
    static let uploadFieldName = "video_file"
    static let calibrationPathFieldName = "calibration_path"
    static let calibrationPathValue = "calibration/user_profile.json"

    static var healthCheckURL: URL {
        baseURL.appendingPathComponent(healthPath)
    }

    static var analyzeVideoURL: URL {
        baseURL.appendingPathComponent(analyzePath)
    }
}

struct AnalysisDebugInfo: Hashable {
    let requestURL: String
    let healthCheckURL: String
    let uploadFieldName: String
    var responseStatusCode: Int?
    var errorMessage: String?
    var rawResponseSnippet: String?
    var selectedAction: String?
    var systemActionSuggestion: String?
    var analysisRoutedBy: String?
    var routedAnalyzer: String?
    var analysisStatus: String?
    var failureReason: String?
    var failureMessage: String?
    var integrityState: String?
    var routeMismatchMessage: String?
    var videoDurationSeconds: Double?
    var frameCount: Int?
    var sampledFrameCount: Int?
    var fastModeEnabled: Bool?
    var longVideoLocalized: Bool?
    var candidateWindowCount: Int?
    var selectedWindowIndex: Int?
    var selectedWindowStartSeconds: Double?
    var selectedWindowEndSeconds: Double?
    var selectedWindowDurationSeconds: Double?
    var processingTimeSeconds: Double?
    var warnings: [String]?

    init(
        requestURL: URL,
        healthCheckURL: URL,
        uploadFieldName: String = AnalysisBackendConfig.uploadFieldName,
        responseStatusCode: Int? = nil,
        errorMessage: String? = nil,
        rawResponseSnippet: String? = nil,
        selectedAction: String? = nil,
        systemActionSuggestion: String? = nil,
        analysisRoutedBy: String? = nil,
        routedAnalyzer: String? = nil,
        analysisStatus: String? = nil,
        failureReason: String? = nil,
        failureMessage: String? = nil,
        integrityState: String? = nil,
        routeMismatchMessage: String? = nil,
        videoDurationSeconds: Double? = nil,
        frameCount: Int? = nil,
        sampledFrameCount: Int? = nil,
        fastModeEnabled: Bool? = nil,
        longVideoLocalized: Bool? = nil,
        candidateWindowCount: Int? = nil,
        selectedWindowIndex: Int? = nil,
        selectedWindowStartSeconds: Double? = nil,
        selectedWindowEndSeconds: Double? = nil,
        selectedWindowDurationSeconds: Double? = nil,
        processingTimeSeconds: Double? = nil,
        warnings: [String]? = nil
    ) {
        self.requestURL = requestURL.absoluteString
        self.healthCheckURL = healthCheckURL.absoluteString
        self.uploadFieldName = uploadFieldName
        self.responseStatusCode = responseStatusCode
        self.errorMessage = errorMessage
        self.rawResponseSnippet = rawResponseSnippet
        self.selectedAction = selectedAction
        self.systemActionSuggestion = systemActionSuggestion
        self.analysisRoutedBy = analysisRoutedBy
        self.routedAnalyzer = routedAnalyzer
        self.analysisStatus = analysisStatus
        self.failureReason = failureReason
        self.failureMessage = failureMessage
        self.integrityState = integrityState
        self.routeMismatchMessage = routeMismatchMessage
        self.videoDurationSeconds = videoDurationSeconds
        self.frameCount = frameCount
        self.sampledFrameCount = sampledFrameCount
        self.fastModeEnabled = fastModeEnabled
        self.longVideoLocalized = longVideoLocalized
        self.candidateWindowCount = candidateWindowCount
        self.selectedWindowIndex = selectedWindowIndex
        self.selectedWindowStartSeconds = selectedWindowStartSeconds
        self.selectedWindowEndSeconds = selectedWindowEndSeconds
        self.selectedWindowDurationSeconds = selectedWindowDurationSeconds
        self.processingTimeSeconds = processingTimeSeconds
        self.warnings = warnings
    }
}

struct HealthCheckResult {
    let isAvailable: Bool
    let status: String?
    let service: String?
    let host: String?
    let port: Int?
    let version: String?
    let analyzerAvailability: [String: String]?
    let startupWarnings: [String]?
    let responseStatusCode: Int?
    let rawResponseSnippet: String?
    let errorMessage: String?
}

struct AnalysisExecutionResult {
    let response: VideoAnalysisResponse
    let record: AnalysisRecord
    let debugInfo: AnalysisDebugInfo
}

struct VideoAnalysisResponse {
    fileprivate let payload: BackendJSON
    let statusCode: Int?
    let rawResponseSnippet: String?

    var selectedAction: String {
        string("selected_action")
    }

    var systemActionSuggestion: String {
        payload.string("system_action_suggestion") ?? payload.string("suggested_action") ?? ""
    }

    var analysisRoutedBy: String {
        string("analysis_routed_by")
    }

    var routedAnalyzer: String {
        string("routed_analyzer")
    }

    var analysisStatus: AnalysisStatus {
        AnalysisStatus(rawValue: string("analysis_status").lowercased()) ?? inferredAnalysisStatus
    }

    var failureReason: AnalysisFailureReason? {
        let raw = string("failure_reason").trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard !raw.isEmpty else {
            return nil
        }
        return AnalysisFailureReason(rawValue: raw)
    }

    var failureMessage: String? {
        string("failure_message")
    }

    var integrityState: AnalysisIntegrityState {
        AnalysisIntegrityState(rawValue: string("integrity_state").lowercased()) ?? inferredIntegrityState
    }

    var routeMismatchMessage: String? {
        let value = string("route_mismatch_message").trimmingCharacters(in: .whitespacesAndNewlines)
        return value.isEmpty ? nil : value
    }

    var videoDurationSeconds: Double {
        double("video_duration_s") ?? double("duration_s") ?? 0.0
    }

    var frameCount: Int {
        int("frame_count") ?? 0
    }

    var sampledFrameCount: Int {
        int("sampled_frame_count") ?? 0
    }

    var fastModeEnabled: Bool {
        bool("fast_mode_enabled") ?? false
    }

    var longVideoLocalized: Bool {
        bool("long_video_localized") ?? false
    }

    var candidateWindowCount: Int {
        int("candidate_window_count") ?? 0
    }

    var selectedWindowIndex: Int? {
        int("selected_window_index")
    }

    var selectedWindowStartSeconds: Double? {
        double("selected_window_start_s")
    }

    var selectedWindowEndSeconds: Double? {
        double("selected_window_end_s")
    }

    var selectedWindowDurationSeconds: Double? {
        double("selected_window_duration_s")
    }

    var processingTimeSeconds: Double? {
        double("processing_time_s")
    }

    var warnings: [String] {
        stringArray(payload.array("warnings"))
    }

    var debugContext: AnalysisDebugContext {
        return AnalysisDebugContext(
            selectedAction: string("selected_action"),
            systemActionSuggestion: systemActionSuggestion,
            analysisRoutedBy: analysisRoutedBy,
            routedAnalyzer: routedAnalyzer,
            videoDuration: videoDurationSeconds,
            frameCount: frameCount,
            sampledFrameCount: sampledFrameCount,
            fastModeEnabled: fastModeEnabled,
            longVideoLocalized: longVideoLocalized,
            candidateWindowCount: candidateWindowCount,
            selectedWindowIndex: selectedWindowIndex,
            selectedWindowStartSeconds: selectedWindowStartSeconds,
            selectedWindowEndSeconds: selectedWindowEndSeconds,
            selectedWindowDurationSeconds: selectedWindowDurationSeconds,
            processingTime: processingTimeSeconds,
            failureReason: failureReason?.rawValue,
            failureMessage: failureMessage,
            routeMismatchMessage: routeMismatchMessage,
            warnings: warnings
        )
    }

    var runtimeState: AnalysisRuntimeState {
        AnalysisRuntimeState(
            analysisStatus: analysisStatus,
            failureReason: failureReason,
            failureMessage: failureMessage,
            integrityState: integrityState,
            routeMismatchMessage: routeMismatchMessage,
            selectedAction: selectedAction,
            systemActionSuggestion: systemActionSuggestion,
            analysisRoutedBy: analysisRoutedBy,
            routedAnalyzer: routedAnalyzer,
            videoDurationSeconds: videoDurationSeconds,
            frameCount: frameCount,
            sampledFrameCount: sampledFrameCount,
            fastModeEnabled: fastModeEnabled,
            longVideoLocalized: longVideoLocalized,
            candidateWindowCount: candidateWindowCount,
            selectedWindowIndex: selectedWindowIndex,
            selectedWindowStartSeconds: selectedWindowStartSeconds,
            selectedWindowEndSeconds: selectedWindowEndSeconds,
            selectedWindowDurationSeconds: selectedWindowDurationSeconds,
            processingTimeSeconds: processingTimeSeconds,
            warnings: warnings,
            debugContext: debugContext
        )
    }

    var isFailure: Bool {
        analysisStatus == .failed
    }

    var isPartial: Bool {
        analysisStatus == .partial
    }

    private var inferredAnalysisStatus: AnalysisStatus {
        if failureReason != nil || failureMessage != nil {
            return .failed
        }

        if fastModeEnabled || longVideoLocalized {
            return .partial
        }

        let backendStatus = string("status").lowercased()
        if backendStatus == "provisional" {
            return .partial
        }
        if backendStatus == "ok" {
            return .success
        }
        if backendStatus == "error" || backendStatus == "unsupported" {
            return .failed
        }
        return .success
    }

    private var inferredIntegrityState: AnalysisIntegrityState {
        if analysisStatus == .failed && failureReason == .routeMismatch {
            return .anomaly
        }
        if let routeMessage = routeMismatchMessage, !routeMessage.isEmpty {
            return .routeMismatch
        }
        return .normal
    }

    private func string(_ firstKey: String, _ rest: String...) -> String {
        payload.string(path: [firstKey] + rest) ?? ""
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func double(_ firstKey: String, _ rest: String...) -> Double? {
        payload.double(path: [firstKey] + rest)
    }

    private func int(_ firstKey: String, _ rest: String...) -> Int? {
        payload.int(path: [firstKey] + rest)
    }

    private func bool(_ firstKey: String, _ rest: String...) -> Bool? {
        payload.bool(path: [firstKey] + rest)
    }
}

struct AnalysisServiceFailure: LocalizedError {
    let debugInfo: AnalysisDebugInfo
    let message: String

    var errorDescription: String? {
        message
    }
}

final class AnalysisService {
    static let shared = AnalysisService()

    private let session: URLSession

    init(session: URLSession = .shared) {
        self.session = session
    }

    func healthCheck() async -> HealthCheckResult {
        do {
            let (data, response) = try await session.data(from: AnalysisBackendConfig.healthCheckURL)
            let statusCode = (response as? HTTPURLResponse)?.statusCode
            let snippet = Self.responseSnippet(from: data)

            guard let payload = BackendJSON(data) else {
                return HealthCheckResult(
                    isAvailable: false,
                    status: nil,
                    service: nil,
                    host: nil,
                    port: nil,
                    version: nil,
                    analyzerAvailability: nil,
                    startupWarnings: nil,
                    responseStatusCode: statusCode,
                    rawResponseSnippet: snippet,
                    errorMessage: "健康检查返回了非 JSON 响应。"
                )
            }

            let status = payload.string("status")
            let service = payload.string("service")
            let host = payload.string("host")
            let port = payload.int("port")
            let version = payload.string("version")
            let analyzerAvailability: [String: String]? = payload.dict("analyzer_availability").map { availability in
                availability.raw.reduce(into: [String: String]()) { result, entry in
                    if let value = entry.value as? String {
                        result[entry.key] = value
                    } else {
                        result[entry.key] = String(describing: entry.value)
                    }
                }
            }
            let startupWarnings = stringArray(payload.array("startup_warnings"))
            let isAvailable = status == "ok" || status == "degraded"
            let errorMessage = isAvailable ? nil : "健康检查返回 status=\(status ?? "nil")"

            return HealthCheckResult(
                isAvailable: isAvailable,
                status: status,
                service: service,
                host: host,
                port: port,
                version: version,
                analyzerAvailability: analyzerAvailability,
                startupWarnings: startupWarnings,
                responseStatusCode: statusCode,
                rawResponseSnippet: snippet,
                errorMessage: errorMessage
            )
        } catch {
            return HealthCheckResult(
                isAvailable: false,
                status: nil,
                service: nil,
                host: nil,
                port: nil,
                version: nil,
                analyzerAvailability: nil,
                startupWarnings: nil,
                responseStatusCode: nil,
                rawResponseSnippet: nil,
                errorMessage: error.localizedDescription
            )
        }
    }

    func analyze(draft: UploadDraft) async throws -> AnalysisExecutionResult {
        let videoURL = try bundledDemoVideoURL()
        let selectedActionValue = draft.goal.backendActionName
        let analysisTemplateValue = draft.goal.backendAnalysisTemplateName
        let (body, boundary) = try multipartBody(
            videoURL: videoURL,
            calibrationPath: AnalysisBackendConfig.calibrationPathValue,
            selectedAction: selectedActionValue,
            analysisTemplate: analysisTemplateValue
        )

        var request = URLRequest(url: AnalysisBackendConfig.analyzeVideoURL)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue("no-cache", forHTTPHeaderField: "Cache-Control")
        request.timeoutInterval = 120

        do {
            let (data, response) = try await session.upload(for: request, from: body)
            let statusCode = (response as? HTTPURLResponse)?.statusCode
            let snippet = Self.responseSnippet(from: data)

            guard let payload = BackendJSON(data) else {
                throw makeFailure(
                    "后端返回了 \(statusCode ?? -1) 状态，但不是可解析的 JSON。",
                    responseStatusCode: statusCode,
                    rawResponseSnippet: snippet
                )
            }

            let responseModel = VideoAnalysisResponse(payload: payload, statusCode: statusCode, rawResponseSnippet: snippet)
            let actionName = Self.currentActionName(from: payload)
            let actionDisplayName = Self.currentActionDisplayName(from: payload)
            let inferredGoal = Self.inferredGoal(
                actionName: actionName,
                actionDisplayName: actionDisplayName,
                fallback: draft.goal
            )

            let templateDraft = UploadDraft(
                clipName: draft.clipName,
                durationSeconds: responseModel.videoDurationSeconds > 0 ? responseModel.videoDurationSeconds : (payload.double("duration_s") ?? draft.durationSeconds),
                goal: inferredGoal,
                sourceLabel: draft.sourceLabel,
                demoClip: draft.demoClip
            )
            let baseRecord = MockData.generateRecord(from: templateDraft, existingCount: 0)

            let record = Self.makeRecord(
                from: payload,
                draft: draft,
                baseRecord: baseRecord,
                inferredGoal: inferredGoal,
                response: responseModel
            )

            Self.frontendPrintAnalysisResponse(responseModel)

#if DEBUG
            Self.debugPrintAnalysisFields(payload)
#endif

            let debugInfo = AnalysisDebugInfo(
                requestURL: AnalysisBackendConfig.analyzeVideoURL,
                healthCheckURL: AnalysisBackendConfig.healthCheckURL,
                responseStatusCode: statusCode,
                errorMessage: responseModel.isFailure ? (responseModel.failureMessage ?? responseModel.routeMismatchMessage ?? Self.backendErrorMessage(payload: payload, statusCode: statusCode)) : nil,
                rawResponseSnippet: snippet,
                selectedAction: responseModel.selectedAction,
                systemActionSuggestion: responseModel.systemActionSuggestion,
                analysisRoutedBy: responseModel.analysisRoutedBy,
                routedAnalyzer: responseModel.routedAnalyzer,
                analysisStatus: responseModel.analysisStatus.rawValue,
                failureReason: responseModel.failureReason?.rawValue,
                failureMessage: responseModel.failureMessage,
                integrityState: responseModel.integrityState.rawValue,
                routeMismatchMessage: responseModel.routeMismatchMessage,
                videoDurationSeconds: responseModel.videoDurationSeconds,
                frameCount: responseModel.frameCount,
                sampledFrameCount: responseModel.sampledFrameCount,
                fastModeEnabled: responseModel.fastModeEnabled,
                longVideoLocalized: responseModel.longVideoLocalized,
                candidateWindowCount: responseModel.candidateWindowCount,
                selectedWindowIndex: responseModel.selectedWindowIndex,
                selectedWindowStartSeconds: responseModel.selectedWindowStartSeconds,
                selectedWindowEndSeconds: responseModel.selectedWindowEndSeconds,
                selectedWindowDurationSeconds: responseModel.selectedWindowDurationSeconds,
                processingTimeSeconds: responseModel.processingTimeSeconds,
                warnings: responseModel.warnings
            )

            return AnalysisExecutionResult(response: responseModel, record: record, debugInfo: debugInfo)
        } catch let failure as AnalysisServiceFailure {
            throw failure
        } catch {
            throw makeFailure(
                error.localizedDescription,
                rawResponseSnippet: nil
            )
        }
    }

    private func bundledDemoVideoURL() throws -> URL {
        let candidates = [
            ("传球", "mp4"),
            ("sample01", "mp4")
        ]

        for candidate in candidates {
            if let url = Bundle.main.url(forResource: candidate.0, withExtension: candidate.1) {
                return url
            }
        }

        throw makeFailure(
            "未找到可上传的示例视频资源。",
            rawResponseSnippet: nil
        )
    }

    private static func analysisTemplate(for goal: TrainingGoal) -> String {
        switch goal {
        case .shooting:
            return "shot_instep"
        case .passing:
            return "short_pass"
        case .firstTouch:
            return "receive_control"
        }
    }

    private static func frontendPrintAnalysisResponse(_ response: VideoAnalysisResponse) {
        let log: [String: Any] = [
            "selected_action": response.selectedAction,
            "system_action_suggestion": response.systemActionSuggestion,
            "analysis_routed_by": response.analysisRoutedBy,
            "routed_analyzer": response.routedAnalyzer,
            "analysis_status": response.analysisStatus.rawValue,
            "failure_reason": response.failureReason?.rawValue ?? "",
            "failure_message": response.failureMessage ?? "",
            "integrity_state": response.integrityState.rawValue,
            "route_mismatch_message": response.routeMismatchMessage ?? "",
            "video_duration": response.videoDurationSeconds,
            "frame_count": response.frameCount,
            "sampled_frame_count": response.sampledFrameCount,
            "fast_mode_enabled": response.fastModeEnabled,
            "long_video_localized": response.longVideoLocalized,
            "candidate_window_count": response.candidateWindowCount,
            "selected_window_index": response.selectedWindowIndex.map { $0 as Any } ?? NSNull(),
            "selected_window_start_s": response.selectedWindowStartSeconds.map { $0 as Any } ?? NSNull(),
            "selected_window_end_s": response.selectedWindowEndSeconds.map { $0 as Any } ?? NSNull(),
            "selected_window_duration_s": response.selectedWindowDurationSeconds.map { $0 as Any } ?? NSNull(),
            "processing_time": response.processingTimeSeconds ?? 0.0,
            "warnings": response.warnings,
        ]

        if let data = try? JSONSerialization.data(withJSONObject: log, options: [.sortedKeys]),
           let text = String(data: data, encoding: .utf8) {
            print("KICK_FRONTEND_ANALYZE_RESPONSE = \(text)")
        } else {
            print("KICK_FRONTEND_ANALYZE_RESPONSE = \(log)")
        }
    }

    private func multipartBody(
        videoURL: URL,
        calibrationPath: String?,
        selectedAction: String?,
        analysisTemplate: String?
    ) throws -> (body: Data, boundary: String) {
        let boundary = "Boundary-\(UUID().uuidString)"
        let videoData = try Data(contentsOf: videoURL)
        var body = Data()

        func append(_ string: String) {
            body.append(Data(string.utf8))
        }

        append("--\(boundary)\r\n")
        append("Content-Disposition: form-data; name=\"\(AnalysisBackendConfig.uploadFieldName)\"; filename=\"\(videoURL.lastPathComponent)\"\r\n")
        append("Content-Type: video/mp4\r\n\r\n")
        body.append(videoData)
        append("\r\n")

        if let calibrationPath {
            append("--\(boundary)\r\n")
            append("Content-Disposition: form-data; name=\"\(AnalysisBackendConfig.calibrationPathFieldName)\"\r\n\r\n")
            append("\(calibrationPath)\r\n")
        }

        if let selectedAction, !selectedAction.isEmpty {
            append("--\(boundary)\r\n")
            append("Content-Disposition: form-data; name=\"selected_action\"\r\n\r\n")
            append("\(selectedAction)\r\n")

            append("--\(boundary)\r\n")
            append("Content-Disposition: form-data; name=\"selectedAction\"\r\n\r\n")
            append("\(selectedAction)\r\n")

            append("--\(boundary)\r\n")
            append("Content-Disposition: form-data; name=\"action\"\r\n\r\n")
            append("\(selectedAction)\r\n")
        }

        if let analysisTemplate, !analysisTemplate.isEmpty {
            append("--\(boundary)\r\n")
            append("Content-Disposition: form-data; name=\"analysis_template\"\r\n\r\n")
            append("\(analysisTemplate)\r\n")
        }

        append("--\(boundary)--\r\n")
        return (body, boundary)
    }

    private func makeFailure(
        _ message: String,
        responseStatusCode: Int? = nil,
        rawResponseSnippet: String? = nil
    ) -> AnalysisServiceFailure {
        AnalysisServiceFailure(
            debugInfo: AnalysisDebugInfo(
                requestURL: AnalysisBackendConfig.analyzeVideoURL,
                healthCheckURL: AnalysisBackendConfig.healthCheckURL,
                responseStatusCode: responseStatusCode,
                errorMessage: message,
                rawResponseSnippet: rawResponseSnippet
            ),
            message: message
        )
    }

    private static func makeRecord(
        from payload: BackendJSON,
        draft: UploadDraft,
        baseRecord: AnalysisRecord,
        inferredGoal: TrainingGoal,
        response: VideoAnalysisResponse
    ) -> AnalysisRecord {
        let score = makeScore(from: payload)
        let reportState = makeReportState(from: payload)
        let qualityStatus = makeQualityStatus(from: payload)
        let analysisMetrics = makeAnalysisMetrics(from: payload, fallback: baseRecord.analysisMetrics)
        let triggeredRules = makeTriggeredRules(from: payload, fallback: baseRecord.triggeredRules)
        let failReasons = makeFailReasons(from: payload, fallback: baseRecord.failReasons)
        let feedbackMessages = makeFeedbackMessages(from: payload, fallback: baseRecord.feedbackMessages)
        let issues = makeIssues(from: payload, reportState: reportState, fallback: baseRecord.issues)
        let observations = makeObservations(from: payload, reportState: reportState, fallback: baseRecord.observations, issues: issues)
        let errorTimestamps = makeErrorTimestamps(from: payload, fallback: baseRecord.errorTimestamps)
        let summary = makeSummary(from: payload, score: score, issues: issues)
        let sequenceResult = makeSequenceResult(from: payload, summaryOverride: summary)
        let createdAt = iso8601Date(from: payload.string("generated_at")) ?? Date()
        let durationSeconds = response.videoDurationSeconds > 0 ? response.videoDurationSeconds : (payload.double("duration_s") ?? draft.durationSeconds)
        let athleteLabel = payload.string("athlete_label") ?? baseRecord.athleteLabel
        let thumbnailStyle = inferredGoal.templateStyle

        return AnalysisRecord(
            id: UUID(),
            createdAt: createdAt,
            athleteLabel: athleteLabel,
            clipName: baseRecord.clipName,
            durationSeconds: durationSeconds,
            goal: inferredGoal,
            score: score,
            reportState: reportState,
            qualityStatus: qualityStatus,
            summary: summary,
            positiveNote: baseRecord.positiveNote,
            targetZone: baseRecord.targetZone,
            contactDescription: baseRecord.contactDescription,
            releaseDescription: baseRecord.releaseDescription,
            thumbnailStyle: thumbnailStyle,
            analysisMetrics: analysisMetrics,
            triggeredRules: triggeredRules,
            failReasons: failReasons,
            feedbackMessages: feedbackMessages,
            issues: issues,
            observations: observations,
            errorTimestamps: errorTimestamps,
            suggestions: baseRecord.suggestions,
            premiumInsights: baseRecord.premiumInsights,
            sequenceResult: sequenceResult,
            runtimeState: response.runtimeState
        )
    }

    private static func makeScore(from payload: BackendJSON) -> ScoreBreakdown {
        let overall = intScore(
            payload,
            paths: [
                ["overall_score"],
                ["score", "overall"],
                ["score", "confidence_adjusted_score"],
                ["score", "provisional_score"]
            ]
        ) ?? 0

        let technique = intScore(
            payload,
            paths: [
                ["score", "pass_subscore"],
                ["score", "technical_execution"],
                ["technique_score"],
                ["score", "technical_execution_score"]
            ]
        ) ?? 0

        let control = intScore(
            payload,
            paths: [
                ["score", "receive_subscore"],
                ["score", "control_stability"],
                ["control_score"],
                ["score", "sequence_continuity_score"]
            ]
        ) ?? 0

        let safety = intScore(
            payload,
            paths: [
                ["score", "next_action_readiness"],
                ["score", "action_safety"],
                ["safety_score"]
            ]
        ) ?? 0

        let levelCode = payload.string("score", "level_code")
            ?? payload.string("score", "levelCode")
            ?? payload.string("level_code")
            ?? payload.string("levelCode")
            ?? ""
        let levelLabel = payload.string("score", "level_label")
            ?? payload.string("score", "levelLabel")
            ?? payload.string("level_label")
            ?? payload.string("levelLabel")
            ?? ""
        let needsConfirmation = payload.bool("needs_confirmation")
            ?? payload.bool("score", "needs_confirmation")
            ?? payload.bool("score", "needsConfirmation")
            ?? false
        let confidence = payload.double("confidence")
            ?? payload.double("score", "confidence")
            ?? 0.0
        let confidenceGap = payload.double("confidence_gap")
            ?? payload.double("score", "confidence_gap")
            ?? payload.double("score", "confidenceGap")
            ?? 0.0
        let actionLabel = payload.string("action_label")
            ?? payload.string("score", "action_label")
            ?? payload.string("score", "actionLabel")
            ?? ""
        let actionDisplayName = payload.string("action_display_name")
            ?? payload.string("score", "action_display_name")
            ?? payload.string("score", "actionDisplayName")
            ?? currentActionDisplayName(from: payload)
        let actionCandidates = makeActionCandidates(from: payload)
        let uncertaintyReasons = stringArray(payload.array("uncertainty_reasons"))
            .isEmpty ? stringArray(payload.array("score", "uncertainty_reasons")) : stringArray(payload.array("uncertainty_reasons"))

        return ScoreBreakdown(
            overall: overall,
            technique: technique,
            control: control,
            safety: safety,
            levelCode: levelCode,
            levelLabel: levelLabel,
            needsConfirmation: needsConfirmation,
            confidence: confidence,
            confidenceGap: confidenceGap,
            actionLabel: actionLabel,
            actionDisplayName: actionDisplayName,
            actionCandidates: actionCandidates,
            uncertaintyReasons: uncertaintyReasons
        )
    }

    private static func makeSummary(from payload: BackendJSON, score: ScoreBreakdown, issues: [AnalysisIssue]) -> String {
        let actionDisplayName = currentActionDisplayName(from: payload)
        let rawSummary = payload.string("summary")?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let analysisConfidence = payload.double("analysis_confidence") ?? 0.0
        let needsConfirmation = payload.bool("needs_confirmation") ?? score.needsConfirmation

        if needsConfirmation {
            return confirmationSummary(actionDisplayName: actionDisplayName, score: score)
        }

        if !summaryNeedsRewrite(summary: rawSummary, score: score, issues: issues) {
            return rawSummary
        }

        return rewriteSummary(
            actionDisplayName: actionDisplayName,
            score: score,
            issues: issues,
            analysisConfidence: analysisConfidence
        )
    }

    private static func makeReportState(from payload: BackendJSON) -> ResultReportState {
        if payload.bool("needs_confirmation") ?? payload.bool("score", "needs_confirmation") ?? false {
            return .needsConfirmation
        }

        let scoringState = payload.string("scoring_state")
        let qualityStatus = payload.string("quality_status")

        if scoringState == "ready_to_score" {
            return .readyToScore
        }

        if scoringState == "quality_fail" || qualityStatus == "fail" {
            return .qualityFail
        }

        return .insufficientEvidence
    }

    private static func makeQualityStatus(from payload: BackendJSON) -> VideoQualityStatus {
        let qualityStatus = (payload.string("quality_status") ?? payload.string("quality_gate", "quality_status") ?? "").lowercased()
        let shouldReshoot = payload.bool("quality_gate", "should_reshoot") ?? false
        let passed = payload.bool("quality_gate", "passed") ?? (qualityStatus == "pass")

        if qualityStatus == "pass" || passed {
            return .good
        }

        if qualityStatus == "outcome_only" || qualityStatus == "limited" {
            return .limited
        }

        if shouldReshoot || qualityStatus == "fail" {
            return .poor
        }

        return .limited
    }

    private static func makeAnalysisMetrics(from payload: BackendJSON, fallback: [AnalysisMetric]) -> [AnalysisMetric] {
        let primaryMetrics = payload.array("primary_metrics").compactMap(dictionaryValue)
        if !primaryMetrics.isEmpty {
            return primaryMetrics.map { metric in
                makeAnalysisMetric(from: metric)
            }
        }

        let phaseScores = payload.dict("phase_scores")?.raw ?? [:]
        if !phaseScores.isEmpty {
            return phaseScores.compactMap { key, value in
                guard let numeric = asDouble(value) else { return nil }
                let title: String
                let tone: AnalysisSignalTone

                switch key {
                case "preparation":
                    title = "准备阶段"
                case "support":
                    title = "支撑阶段"
                case "contact":
                    title = "触球阶段"
                case "follow_through":
                    title = "随挥阶段"
                default:
                    title = key
                }

                tone = toneForScore(numeric)
                return AnalysisMetric(
                    key: key,
                    title: title,
                    valueText: "\(Int(round(numeric)))",
                    detail: "phase score",
                    tone: tone
                )
            }
        }

        return fallback
    }

    private static func makeAnalysisMetric(from raw: [String: Any]) -> AnalysisMetric {
        let key = stringValue(raw["metric"]) ?? stringValue(raw["label"]) ?? "metric"
        let title = stringValue(raw["label"]) ?? key
        let valueText = formattedMetricValue(metricKey: key, rawValue: asDouble(raw["raw_value"]), score: asDouble(raw["score"]))
        let detail = [
            stringValue(raw["role"]),
            stringValue(raw["source_class"]),
            stringValue(raw["band"])
        ]
        .compactMap { $0 }
        .joined(separator: " · ")

        return AnalysisMetric(
            key: key,
            title: title,
            valueText: valueText,
            detail: detail.isEmpty ? title : detail,
            tone: toneForMetric(raw)
        )
    }

    private static func makeTriggeredRules(from payload: BackendJSON, fallback: [RuleTriggerSummary]) -> [RuleTriggerSummary] {
        let rawRules = payload.array("triggered_rules").compactMap(dictionaryValue)
        if !rawRules.isEmpty {
            return rawRules.map { raw in
                let key = stringValue(raw["id"]) ?? stringValue(raw["metric"]) ?? stringValue(raw["rule_id"]) ?? UUID().uuidString
                let title = stringValue(raw["label"]) ?? stringValue(raw["title"]) ?? key
                let phase = motionStage(from: stringValue(raw["phase"]) ?? stringValue(raw["stage"]))
                let detail = stringValue(raw["reason"]) ?? stringValue(raw["detail"]) ?? stringValue(raw["quality_impact"]) ?? ""
                return RuleTriggerSummary(key: key, title: title, phase: phase, detail: detail)
            }
        }

        return fallback
    }

    private static func makeFailReasons(from payload: BackendJSON, fallback: [String]) -> [String] {
        let values = stringArray(payload.array("fail_reasons"))
        return values.isEmpty ? fallback : values
    }

    private static func makeFeedbackMessages(from payload: BackendJSON, fallback: [String]) -> [String] {
        let values = stringArray(payload.array("feedback_messages"))
        return values.isEmpty ? fallback : values
    }

    private static func makeIssues(from payload: BackendJSON, reportState: ResultReportState, fallback: [AnalysisIssue]) -> [AnalysisIssue] {
        let rawIssues = payload.array("issues").compactMap(dictionaryValue)
        if !rawIssues.isEmpty {
            return rawIssues.map { raw in
                let id = stringValue(raw["id"]) ?? UUID().uuidString
                let title = stringValue(raw["title"]) ?? stringValue(raw["label"]) ?? id
                let stage = motionStage(from: stringValue(raw["phase"]) ?? stringValue(raw["stage"]))
                let detail = stringValue(raw["explanation"]) ?? stringValue(raw["short_hint"]) ?? stringValue(raw["detail"]) ?? ""
                let impact = stringValue(raw["fix_advice"]) ?? stringValue(raw["training_advice"]) ?? stringValue(raw["severity"]) ?? ""
                let time = formattedTime(from: raw["time"])
                return AnalysisIssue(
                    id: UUID(uuidString: id) ?? UUID(),
                    stage: stage,
                    title: title,
                    detail: detail,
                    impact: impact,
                    time: time
                )
            }
        }

        if reportState == .readyToScore {
            return fallback
        }

        return []
    }

    private static func makeObservations(
        from payload: BackendJSON,
        reportState: ResultReportState,
        fallback: [ResultObservation],
        issues: [AnalysisIssue]
    ) -> [ResultObservation] {
        let rawObservations = payload.array("observations").compactMap(dictionaryValue)
        if !rawObservations.isEmpty {
            return rawObservations.map { raw in
                ResultObservation(
                    id: UUID(),
                    phase: motionStage(from: stringValue(raw["phase"]) ?? stringValue(raw["stage"])),
                    time: stringValue(raw["time"]) ?? "",
                    title: stringValue(raw["title"]) ?? stringValue(raw["label"]) ?? "Observation",
                    detail: stringValue(raw["detail"]) ?? stringValue(raw["explanation"]) ?? ""
                )
            }
        }

        if reportState == .readyToScore {
            return []
        }

        if !issues.isEmpty {
            return issues.map { issue in
                ResultObservation(
                    id: issue.id,
                    phase: issue.stage,
                    time: issue.time ?? "",
                    title: issue.title,
                    detail: issue.detail
                )
            }
        }

        return fallback
    }

    private static func makeErrorTimestamps(from payload: BackendJSON, fallback: [ResultTimestamp]) -> [ResultTimestamp] {
        let rawItems = payload.array("error_timestamps").compactMap(dictionaryValue)
        if !rawItems.isEmpty {
            return rawItems.map { raw in
                let start = asDouble(raw["start_time"]) ?? asDouble(raw["time"]) ?? 0.0
                let end = asDouble(raw["end_time"]) ?? start
                let label = stringValue(raw["reason"]) ?? stringValue(raw["label"]) ?? stringValue(raw["rule_id"]) ?? "Error"
                let detail = stringValue(raw["detail"]) ?? stringValue(raw["reason"]) ?? ""
                return ResultTimestamp(
                    id: UUID(),
                    start: start,
                    end: end,
                    label: label,
                    detail: detail
                )
            }
        }

        return fallback
    }

    private static func makeQualityGate(
        from payload: BackendJSON,
        actionName: String
    ) -> SequenceQualityGate {
        let qualityStatus = payload.string("quality_gate", "quality_status")
            ?? payload.string("quality_status")
            ?? "pass"

        return SequenceQualityGate(
            actionName: payload.string("quality_gate", "action_name")
                ?? payload.string("quality_gate", "actionName")
                ?? actionName,
            qualityStatus: qualityStatus,
            passed: payload.bool("quality_gate", "passed") ?? (qualityStatus == "pass"),
            allowMicroTechniqueScore: payload.bool("quality_gate", "allow_micro_technique_score") ?? true,
            hideMicroTechniqueScore: payload.bool("quality_gate", "hide_micro_technique_score") ?? false,
            shouldReshoot: payload.bool("quality_gate", "should_reshoot") ?? false,
            reshootHint: payload.string("quality_gate", "reshoot_hint") ?? "",
            thresholds: doubleDictionary(payload.dict("quality_gate", "thresholds")?.raw) ?? [:],
            observed: doubleDictionary(payload.dict("quality_gate", "observed")?.raw) ?? [:],
            triggeredRules: stringArray(payload.array("quality_gate", "triggered_rules")),
            failReasons: stringArray(payload.array("quality_gate", "fail_reasons"))
        )
    }

    private static func makeSequenceCandidates(from payload: BackendJSON) -> [SequenceActionCandidate] {
        let rawCandidates = payload.array("raw_action_candidates").compactMap(dictionaryValue)
        if !rawCandidates.isEmpty {
            return rawCandidates.map { raw in
                SequenceActionCandidate(
                    action: stringValue(raw["action"]) ?? stringValue(raw["label"]) ?? UUID().uuidString,
                    score: asDouble(raw["score"]) ?? 0,
                    sources: stringArray(raw["sources"] as? [Any])
                )
            }
        }

        return []
    }

    private static func makeActionCandidates(from payload: BackendJSON) -> [ActionCandidate] {
        let primaryCandidates = payload.array("action_candidates").compactMap(dictionaryValue)
        let fallbackCandidates = payload.array("score", "action_candidates").compactMap(dictionaryValue)
        let rawCandidates = primaryCandidates.isEmpty ? fallbackCandidates : primaryCandidates

        if !rawCandidates.isEmpty {
            return rawCandidates.map { raw in
                ActionCandidate(
                    action: stringValue(raw["action"]) ?? stringValue(raw["label"]) ?? UUID().uuidString,
                    label: stringValue(raw["label"]) ?? stringValue(raw["action"]) ?? "",
                    displayName: stringValue(raw["display_name"]) ?? stringValue(raw["displayName"]) ?? stringValue(raw["label"]) ?? stringValue(raw["action"]) ?? "",
                    score: asDouble(raw["score"]) ?? 0.0,
                    sources: stringArray(raw["sources"] as? [Any]),
                    template: stringValue(raw["template"]) ?? stringValue(raw["route_template"]) ?? ""
                )
            }
        }

        return []
    }

    private static func makeCandidateScores(from payload: BackendJSON) -> [String: Double] {
        if let raw = payload.dict("candidate_scores") {
            return doubleDictionary(raw.raw) ?? [:]
        }

        return [:]
    }

    private static func makeMetricDebug(from payload: BackendJSON) -> [String: SequenceMetricDebugField] {
        let raw = payload.dict("metric_debug")?.raw ?? [:]
        if !raw.isEmpty {
            return raw.compactMapValues { value in
                guard let dict = value as? [String: Any] else { return nil }
                return makeMetricDebugField(from: dict)
            }
        }

        return [:]
    }

    private static func makeMetricDebugField(from raw: [String: Any]) -> SequenceMetricDebugField {
        SequenceMetricDebugField(
            value: asDouble(raw["value"]),
            resolved: asBool(raw["resolved"]),
            lowConfidence: asBool(raw["low_confidence"]),
            confidence: asDouble(raw["confidence"]),
            startTime: asDouble(raw["start_time"]),
            endTime: asDouble(raw["end_time"]),
            startEvent: stringValue(raw["start_event"]),
            endEvent: stringValue(raw["end_event"]),
            eventSource: stringValue(raw["event_source"]),
            fallbackToVideoEnd: asBool(raw["fallback_to_video_end"]),
            rawValue: asDouble(raw["raw_value"]),
            score: asDouble(raw["score"]),
            band: stringValue(raw["band"]),
            direction: stringValue(raw["direction"]),
            thresholds: doubleDictionary(raw["thresholds"] as? [String: Any]),
            logic: logicSteps(raw["logic"] as? [Any]),
            contactDetected: asBool(raw["contact_detected"]),
            receiveContactDetected: asBool(raw["receive_contact_detected"]),
            stabilizationDetected: asBool(raw["stabilization_detected"]),
            usedProxyLocalWindow: asBool(raw["used_proxy_local_window"]),
            usedVideoEndTime: asBool(raw["used_video_end_time"]),
            passExecutionLowConfidence: asBool(raw["pass_execution_low_confidence"]),
            passReceiveGapLowConfidence: asBool(raw["pass_receive_gap_low_confidence"]),
            receiveStabilizationLowConfidence: asBool(raw["receive_stabilization_low_confidence"])
        )
    }

    private static func makeSequenceMetrics(from rawMetrics: [[String: Any]]) -> [SequenceMetricSummary] {
        rawMetrics.map { raw in
            let id = metricIdentifier(raw)
            let title = stringValue(raw["label"]) ?? stringValue(raw["title"]) ?? id
            let valueText = formattedMetricValue(metricKey: id, rawValue: asDouble(raw["raw_value"]), score: asDouble(raw["score"]))
            let detail = [
                stringValue(raw["role"]),
                stringValue(raw["source_class"]),
                stringValue(raw["band"])
            ]
            .compactMap { $0 }
            .joined(separator: " · ")

            return SequenceMetricSummary(
                id: id,
                title: title,
                valueText: valueText,
                detail: detail.isEmpty ? title : detail,
                tone: toneForMetric(raw),
                lowConfidence: asBool(raw["low_confidence"]) ?? (stringValue(raw["band"]) == "low_confidence")
            )
        }
    }

    private static func toneForMetric(_ raw: [String: Any]) -> AnalysisSignalTone {
        if asBool(raw["low_confidence"]) == true || asBool(raw["diagnostic_only"]) == true {
            return .watch
        }

        if let band = stringValue(raw["band"]) {
            switch band {
            case "excellent", "good":
                return .good
            case "needs_work", "warning":
                return .warn
            case "poor", "fail":
                return .fail
            case "low_confidence":
                return .watch
            default:
                break
            }
        }

        if let score = asDouble(raw["score"]) {
            return toneForScore(score)
        }

        return .neutral
    }

    private static func toneForScore(_ score: Double) -> AnalysisSignalTone {
        switch score {
        case 90...:
            return .good
        case 75..<90:
            return .watch
        case 60..<75:
            return .warn
        default:
            return .fail
        }
    }

    private static func formattedMetricValue(metricKey: String, rawValue: Double?, score: Double?) -> String {
        if let rawValue {
            if metricKey.contains("rate") || metricKey.contains("success") || metricKey.contains("readiness") {
                return "\(Int(round(rawValue * 100)))%"
            }

            if metricKey.contains("_m") || metricKey.contains("distance") || metricKey.contains("error") {
                return String(format: "%.3f m", rawValue)
            }

            if metricKey.contains("_s") || metricKey.contains("time") || metricKey.contains("gap") || metricKey.contains("duration") {
                return String(format: "%.3f s", rawValue)
            }

            return String(format: "%.3f", rawValue)
        }

        if let score {
            return String(format: "%.0f", score)
        }

        return "--"
    }

    private static func backendErrorMessage(payload: BackendJSON, statusCode: Int?) -> String {
        if let summary = payload.string("summary"), !summary.isEmpty {
            return summary
        }

        if let status = payload.string("status"), status != "ok" {
            return "后端返回 status=\(status)"
        }

        if let statusCode {
            return "HTTP \(statusCode)"
        }

        return "后端返回了无法识别的响应。"
    }

    private static func currentActionName(from payload: BackendJSON) -> String {
        let candidates = [
            payload.string("selected_action"),
            payload.string("action_name"),
            payload.string("action_label"),
            payload.string("resolved_action_name"),
            payload.string("mapped_rule_key"),
            payload.string("recommended_template"),
            payload.string("detected_action"),
            payload.string("raw_detected_action"),
            payload.string("routed_analyzer")
        ]

        for candidate in candidates {
            let value = candidate?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            if !value.isEmpty {
                return value
            }
        }

        return ""
    }

    private static func currentActionDisplayName(from payload: BackendJSON) -> String {
        let actionName = currentActionName(from: payload)
        let needsConfirmation = payload.bool("needs_confirmation") ?? payload.bool("score", "needs_confirmation") ?? false
        if let label = payload.string("action_display_name")?.trimmingCharacters(in: .whitespacesAndNewlines), !label.isEmpty {
            if needsConfirmation || actionName.isEmpty || actionDisplayNameMatches(actionName: actionName, displayName: label) {
                return label
            }
        }

        if needsConfirmation {
            return "待确认"
        }

        return derivedActionDisplayName(from: actionName)
    }

    private static func derivedActionDisplayName(from actionName: String) -> String {
        let lowerAction = actionName.lowercased()
        if lowerAction.contains("uncertain") || lowerAction.contains("pending_confirmation") || lowerAction.contains("needs_confirmation") {
            return "待确认"
        }
        if lowerAction.contains("pass_receive_sequence") || lowerAction.contains("sequence") {
            return "传接球序列"
        }
        if lowerAction.contains("short_pass") || lowerAction.contains("pass_like") || lowerAction.contains("pass") {
            return "传球"
        }
        if lowerAction.contains("receive_control") || lowerAction.contains("first_touch") || lowerAction.contains("touch") {
            return "停球"
        }
        if lowerAction.contains("shot_instep") || lowerAction.contains("shoot") || lowerAction.contains("shot") {
            return "射门"
        }
        return actionName.isEmpty ? "动作" : actionName
    }

    private static func actionDisplayNameMatches(actionName: String, displayName: String) -> Bool {
        let lowerAction = actionName.lowercased()
        let lowerDisplay = displayName.lowercased()

        if lowerAction.contains("pass_receive_sequence") || lowerAction.contains("sequence") {
            return displayName.contains("传接球") || displayName.contains("传球") || lowerDisplay.contains("sequence") || lowerDisplay.contains("pass")
        }
        if lowerAction.contains("short_pass") || lowerAction.contains("pass_like") || lowerAction.contains("pass") {
            return displayName.contains("传") || lowerDisplay.contains("pass")
        }
        if lowerAction.contains("receive_control") || lowerAction.contains("first_touch") || lowerAction.contains("touch") {
            return displayName.contains("接") || displayName.contains("停") || lowerDisplay.contains("touch")
        }
        if lowerAction.contains("shot_instep") || lowerAction.contains("shoot") || lowerAction.contains("shot") {
            return displayName.contains("射门") || lowerDisplay.contains("shot") || lowerDisplay.contains("shoot")
        }

        return true
    }

    private static func summaryPrimaryIssue(from issues: [AnalysisIssue]) -> AnalysisIssue? {
        for issue in issues {
            let title = issue.title.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
            if title.contains("动作整体稳定") || title.contains("动作识别不够明确") || title.contains("视频证据不足") || title.contains("视频质量问题") {
                continue
            }
            return issue
        }
        return issues.first
    }

    private static func summaryNeedsRewrite(summary: String, score: ScoreBreakdown, issues: [AnalysisIssue]) -> Bool {
        let text = summary.trimmingCharacters(in: .whitespacesAndNewlines)
        if text.isEmpty {
            return true
        }

        if text.contains("当前动作") || text.contains("最值得继续保持的是当前动作") || text.contains("继续保持的是当前动作") || text.contains("当前最值得继续保持") {
            return true
        }

        let primaryIssue = summaryPrimaryIssue(from: issues)
        let primaryTitle = primaryIssue?.title.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let overall = Double(score.overall)

        if overall < 60.0 {
            if ["动作整体稳定", "动作识别不够明确", "视频证据不足", "视频质量问题", "动作质量"].contains(primaryTitle) {
                return true
            }
            if !primaryTitle.isEmpty && !text.contains(primaryTitle) {
                return true
            }
            if primaryTitle.isEmpty && !text.contains("主要问题") {
                return true
            }
        }

        return false
    }

    private static func rewriteSummary(
        actionDisplayName: String,
        score: ScoreBreakdown,
        issues: [AnalysisIssue],
        analysisConfidence: Double
    ) -> String {
        let overall = Double(score.overall)
        let primaryIssue = summaryPrimaryIssue(from: issues)
        let primaryTitleCandidate = primaryIssue?.title.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let primaryTitle = primaryTitleCandidate.isEmpty || primaryTitleCandidate.contains("动作整体稳定") || primaryTitleCandidate.contains("动作识别不够明确") ? "动作完成度" : primaryTitleCandidate
        let confidenceNote = analysisConfidence < 0.45 ? " 当前证据偏少，结论请按保守结果理解。" : ""

        let base: String
        if overall >= 90.0 {
            base = "\(actionDisplayName) 动作得分 \(score.overall)/100，完成度很高，当前重点是继续稳定\(primaryTitle)。"
        } else if overall >= 75.0 {
            base = "\(actionDisplayName) 动作得分 \(score.overall)/100，整体表现良好，仍需优化\(primaryTitle)。"
        } else if overall >= 60.0 {
            base = "\(actionDisplayName) 动作得分 \(score.overall)/100，当前主要问题是\(primaryTitle)。"
        } else if overall >= 40.0 {
            base = "\(actionDisplayName) 动作得分 \(score.overall)/100，当前主要问题是\(primaryTitle)，建议先把这个环节稳定下来。"
        } else {
            base = "\(actionDisplayName) 动作得分 \(score.overall)/100，当前主要问题是\(primaryTitle)，建议优先重拍或重点纠正。"
        }

        return base + confidenceNote
    }

    private static func confirmationSummary(actionDisplayName: String, score: ScoreBreakdown) -> String {
        let candidateText = score.actionCandidates
            .prefix(2)
            .map { candidate in
                "\(candidate.title) \(String(format: "%.2f", candidate.score))"
            }
            .joined(separator: "、")
        let reasonText = score.uncertaintyReasons
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
            .prefix(2)
            .joined(separator: "、")

        var base = "当前动作类型仍待确认，"
        if !candidateText.isEmpty {
            base += "候选更像 \(candidateText)，"
        }
        base += "建议补充更清晰角度后再分析。"
        if !reasonText.isEmpty {
            base += " 主要不确定原因：\(reasonText)。"
        }
        return base
    }

    private static func debugPrintAnalysisFields(_ payload: BackendJSON) {
        let overallScore = payload.double("overall_score") ?? payload.double("score", "overall") ?? 0.0
        let scoreOverall = payload.double("score", "overall") ?? 0.0
        let scoreLabel = payload.string("score", "level_label") ?? ""
        let fields: [String: String] = [
            "action_label": payload.string("action_label") ?? "",
            "action_name": payload.string("action_name") ?? "",
            "action_display_name": payload.string("action_display_name") ?? "",
            "detected_action": payload.string("detected_action") ?? "",
            "recommended_template": payload.string("recommended_template") ?? "",
            "score.overall": String(format: "%.1f", scoreOverall),
            "score.level_code": payload.string("score", "level_code") ?? "",
            "score.level_label": scoreLabel,
            "overall_score": String(format: "%.1f", overallScore),
            "needs_confirmation": (payload.bool("needs_confirmation") ?? payload.bool("score", "needs_confirmation") ?? false) ? "true" : "false",
            "confidence": String(format: "%.3f", payload.double("confidence") ?? payload.double("score", "confidence") ?? 0.0),
            "confidence_gap": String(format: "%.3f", payload.double("confidence_gap") ?? payload.double("score", "confidence_gap") ?? 0.0),
            "summary": payload.string("summary") ?? ""
        ]
        print("[AnalysisService] result fields: \(fields)")
    }

    private static func inferredGoal(
        actionName: String?,
        actionDisplayName: String?,
        fallback: TrainingGoal
    ) -> TrainingGoal {
        let combined = [actionName, actionDisplayName]
            .compactMap { $0 }
            .joined(separator: " ")
            .lowercased()

        if combined.contains("pass") || combined.contains("传球") || combined.contains("接球") || combined.contains("sequence") {
            return .passing
        }

        if combined.contains("shot") || combined.contains("shoot") || combined.contains("射门") {
            return .shooting
        }

        if combined.contains("touch") || combined.contains("停球") || combined.contains("first") {
            return .firstTouch
        }

        return fallback
    }

    private static func metricIdentifier(_ raw: [String: Any]) -> String {
        let metric = stringValue(raw["metric"]) ?? stringValue(raw["label"]) ?? stringValue(raw["id"]) ?? UUID().uuidString
        return metric.lowercased()
    }

    private static func motionStage(from value: String?) -> MotionStage {
        switch value?.lowercased() {
        case "setup":
            return .setup
        case "support":
            return .support
        case "strike", "contact":
            return .strike
        case "follow_through", "followthrough":
            return .followThrough
        default:
            return .setup
        }
    }

    private static func makeSequenceResult(
        from payload: BackendJSON,
        summaryOverride: String?
    ) -> PassReceiveSequenceResult? {
        let actionName = currentActionName(from: payload).lowercased()
        let actionDisplayName = currentActionDisplayName(from: payload)

        guard actionName.contains("pass_receive_sequence")
            || actionDisplayName.contains("传接球")
            || actionDisplayName.lowercased().contains("sequence") else {
            return nil
        }

        let rawMetrics = payload.array("primary_metrics").compactMap(dictionaryValue)
        let passMetrics = makeSequenceMetrics(
            from: rawMetrics.filter {
                let identifier = metricIdentifier($0)
                return identifier.contains("pass_") && !identifier.contains("gap") && !identifier.contains("sequence")
            }
        )
        let receiveMetrics = makeSequenceMetrics(
            from: rawMetrics.filter { metricIdentifier($0).contains("receive_") }
        )
        let sequenceMetrics = makeSequenceMetrics(
            from: rawMetrics.filter {
                let identifier = metricIdentifier($0)
                return identifier.contains("sequence") || identifier.contains("gap") || identifier.contains("next_action")
            }
        )

        let feedbackMessages = stringArray(payload.array("feedback_messages"))
        let overallScore = payload.double("overall_score") ?? payload.double("score", "overall") ?? 0.0
        let levelLabel = payload.bool("needs_confirmation") == true
            ? "待确认"
            : (payload.string("score", "level_label")
                ?? payload.string("score", "levelLabel")
                ?? ResultLevel.level(for: overallScore).title)
        let summary = summaryOverride?.trimmingCharacters(in: .whitespacesAndNewlines)
            ?? payload.string("summary")?.trimmingCharacters(in: .whitespacesAndNewlines)
            ?? ""

        return PassReceiveSequenceResult(
            actionDisplayName: actionDisplayName,
            overallScore: overallScore,
            levelLabel: levelLabel,
            summary: summary,
            passMetrics: passMetrics,
            receiveMetrics: receiveMetrics,
            sequenceMetrics: sequenceMetrics,
            feedbackMessages: feedbackMessages,
            rawActionCandidates: makeSequenceCandidates(from: payload),
            candidateScores: makeCandidateScores(from: payload),
            metricDebug: makeMetricDebug(from: payload),
            qualityGate: makeQualityGate(from: payload, actionName: actionName)
        )
    }

    private static func responseSnippet(from data: Data, limit: Int = 1200) -> String {
        let text: String
        if let object = try? JSONSerialization.jsonObject(with: data),
           JSONSerialization.isValidJSONObject(object),
           let prettyData = try? JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys]),
           let prettyText = String(data: prettyData, encoding: .utf8) {
            text = prettyText
        } else {
            text = String(decoding: data, as: UTF8.self)
        }

        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.count <= limit {
            return trimmed
        }

        return String(trimmed.prefix(limit)) + "…"
    }

    private static func iso8601Date(from value: String?) -> Date? {
        guard let value else { return nil }

        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = formatter.date(from: value) {
            return date
        }

        formatter.formatOptions = [.withInternetDateTime]
        return formatter.date(from: value)
    }
}

fileprivate struct BackendJSON {
    let raw: [String: Any]

    init?(_ data: Data) {
        guard let object = try? JSONSerialization.jsonObject(with: data),
              let dict = object as? [String: Any] else {
            return nil
        }
        raw = dict
    }

    init(raw: [String: Any]) {
        self.raw = raw
    }

    func value(_ firstKey: String, _ rest: String...) -> Any? {
        value(path: [firstKey] + rest)
    }

    func value(path keys: [String]) -> Any? {
        var current: Any? = raw
        for key in keys {
            guard let dict = current as? [String: Any] else {
                return nil
            }
            current = dict[key]
        }
        return current
    }

    func string(_ firstKey: String, _ rest: String...) -> String? {
        stringValue(value(path: [firstKey] + rest))
    }

    func string(path keys: [String]) -> String? {
        stringValue(value(path: keys))
    }

    func double(_ firstKey: String, _ rest: String...) -> Double? {
        asDouble(value(path: [firstKey] + rest))
    }

    func double(path keys: [String]) -> Double? {
        asDouble(value(path: keys))
    }

    func int(_ firstKey: String, _ rest: String...) -> Int? {
        asInt(value(path: [firstKey] + rest))
    }

    func int(path keys: [String]) -> Int? {
        asInt(value(path: keys))
    }

    func bool(_ firstKey: String, _ rest: String...) -> Bool? {
        asBool(value(path: [firstKey] + rest))
    }

    func bool(path keys: [String]) -> Bool? {
        asBool(value(path: keys))
    }

    func dict(_ firstKey: String, _ rest: String...) -> BackendJSON? {
        guard let raw = value(path: [firstKey] + rest) as? [String: Any] else {
            return nil
        }
        return BackendJSON(raw: raw)
    }

    func array(_ firstKey: String, _ rest: String...) -> [Any] {
        value(path: [firstKey] + rest) as? [Any] ?? []
    }
}

private func dictionaryValue(_ value: Any) -> [String: Any]? {
    value as? [String: Any]
}

private func intScore(_ payload: BackendJSON, paths: [[String]]) -> Int? {
    for path in paths {
        guard let value = payload.value(path: path) else { continue }
        if let int = asInt(value) {
            return int
        }
        if let double = asDouble(value) {
            return Int(round(double))
        }
    }

    return nil
}

private func stringValue(_ value: Any?) -> String? {
    switch value {
    case let string as String:
        return string
    case let number as NSNumber:
        return number.stringValue
    case .none:
        return nil
    default:
        return nil
    }
}

private func asDouble(_ value: Any?) -> Double? {
    switch value {
    case let double as Double:
        return double
    case let int as Int:
        return Double(int)
    case let number as NSNumber:
        return number.doubleValue
    case let string as String:
        return Double(string)
    default:
        return nil
    }
}

private func asInt(_ value: Any?) -> Int? {
    switch value {
    case let int as Int:
        return int
    case let double as Double:
        return Int(round(double))
    case let number as NSNumber:
        return number.intValue
    case let string as String:
        return Int(string)
    default:
        return nil
    }
}

private func asBool(_ value: Any?) -> Bool? {
    switch value {
    case let bool as Bool:
        return bool
    case let number as NSNumber:
        return number.boolValue
    case let string as String:
        switch string.lowercased() {
        case "true", "yes", "1":
            return true
        case "false", "no", "0":
            return false
        default:
            return nil
        }
    default:
        return nil
    }
}

private func doubleDictionary(_ raw: [String: Any]?) -> [String: Double]? {
    guard let raw else { return nil }
    var values: [String: Double] = [:]
    for (key, value) in raw {
        if let numeric = asDouble(value) {
            values[key] = numeric
        }
    }
    return values.isEmpty ? nil : values
}

private func stringArray(_ values: [Any]?) -> [String] {
    guard let values else { return [] }
    return values.compactMap { stringValue($0) }
}

private func formattedTime(from value: Any?) -> String? {
    guard let value = asDouble(value) else { return nil }
    return String(format: "%.1fs", value)
}

private func logicSteps(_ values: [Any]?) -> [SequenceBandLogicStep]? {
    guard let values, !values.isEmpty else { return nil }
    let steps = values.compactMap { value -> SequenceBandLogicStep? in
        guard let raw = value as? [String: Any] else { return nil }
        return SequenceBandLogicStep(
            condition: stringValue(raw["if"]),
            band: stringValue(raw["band"]),
            otherwise: stringValue(raw["otherwise"])
        )
    }
    return steps.isEmpty ? nil : steps
}
