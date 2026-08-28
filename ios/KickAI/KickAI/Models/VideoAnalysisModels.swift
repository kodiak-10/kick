import AVFoundation
import CoreTransferable
import Foundation
import UIKit

struct ImportedVideo {
    let url: URL
    let fileName: String
    let fileSizeBytes: Int64
    let durationSeconds: Double
    let thumbnailImage: UIImage?

    var fileSizeLabel: String {
        ByteCountFormatter.string(fromByteCount: fileSizeBytes, countStyle: .file)
    }

    var durationLabel: String {
        guard durationSeconds.isFinite, durationSeconds > 0 else {
            return "时长未知"
        }
        return String(format: "%.1f 秒", durationSeconds)
    }
}

enum VideoAnalysisFailureKind: String, Equatable {
    case validation
    case connectivity
    case serviceError
    case structuredAnalysisFailure
    case configurationMissing
    case decodingFailure
    case unknown
}

struct VideoAnalysisFailureState: Equatable {
    let kind: VideoAnalysisFailureKind
    let message: String
    let requestURL: String?
    let statusCode: Int?
    let networkErrorCode: Int?
    let networkErrorDescription: String?
    let failureMessage: String?
    let failureReason: String?
    let analysisStatus: String?
    let routeDebugText: String?
    let responseBodyPreview: String?

    var statusCodeText: String {
        statusCode.map(String.init) ?? "未返回"
    }

    var networkErrorCodeText: String {
        networkErrorCode.map(String.init) ?? "无"
    }
}

struct VideoAnalysisDebugState: Equatable {
    var requestURL: String?
    var requestTimeoutSeconds: TimeInterval?
    var requestMethod: String?
    var baseURL: String?
    var baseURLSource: String?
    var host: String?
    var port: Int?
    var endpointPath: String?
    var selectedActionValue: String?
    var analysisTemplateValue: String?
    var multipartFieldNames: [String] = []
    var filename: String?
    var mimeType: String?
    var requestBodySize: Int64?
    var uploadStarted = false
    var uploadFinished = false
    var responseReceived = false
    var responseStatusCode: Int?
    var responseTextPreview: String?
    var analysisStatus: String?
    var failureMessage: String?
    var failureReason: String?
    var failureKind: String?
    var networkErrorCode: Int?
    var networkErrorDescription: String?
    var routeDebugText: String?
    var errorMessage: String?
}

extension ImportedVideo {
    static func make(from url: URL) async throws -> ImportedVideo {
        let persistedURL = try persistForAnalysisIfNeeded(url)
        let attributes = try FileManager.default.attributesOfItem(atPath: persistedURL.path)
        let fileSizeBytes = (attributes[.size] as? NSNumber)?.int64Value ?? 0
        let duration = try await AVAsset(url: persistedURL).load(.duration)
        let durationSeconds = max(CMTimeGetSeconds(duration), 0)
        let thumbnailImage = VideoPreviewFactory.thumbnail(for: persistedURL)

        return ImportedVideo(
            url: persistedURL,
            fileName: persistedURL.lastPathComponent.isEmpty ? "未命名视频" : persistedURL.lastPathComponent,
            fileSizeBytes: fileSizeBytes,
            durationSeconds: durationSeconds,
            thumbnailImage: thumbnailImage
        )
    }

    private static func persistForAnalysisIfNeeded(_ sourceURL: URL) throws -> URL {
        let directory = analysisVideoDirectory
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)

        if sourceURL.path.hasPrefix(directory.path),
           FileManager.default.fileExists(atPath: sourceURL.path) {
            return sourceURL
        }

        let originalName = sourceURL.lastPathComponent.nonEmpty ?? "video.mov"
        let destinationURL = directory.appendingPathComponent("\(UUID().uuidString)-\(originalName)")
        if FileManager.default.fileExists(atPath: destinationURL.path) {
            try FileManager.default.removeItem(at: destinationURL)
        }
        try FileManager.default.copyItem(at: sourceURL, to: destinationURL)
        return destinationURL
    }

    private static var analysisVideoDirectory: URL {
        let documents = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first
        let root = documents ?? FileManager.default.temporaryDirectory
        return root.appendingPathComponent("ImportedAnalysisVideos", isDirectory: true)
    }
}

struct ImportedVideoFile: Transferable {
    let url: URL

    static var transferRepresentation: some TransferRepresentation {
        FileRepresentation(importedContentType: .movie) { received in
            let folderURL = FileManager.default.temporaryDirectory
                .appendingPathComponent("kickai-video-\(UUID().uuidString)", isDirectory: true)
            try FileManager.default.createDirectory(
                at: folderURL,
                withIntermediateDirectories: true
            )

            let destinationURL = folderURL.appendingPathComponent(received.file.lastPathComponent)
            try FileManager.default.copyItem(at: received.file, to: destinationURL)
            return ImportedVideoFile(url: destinationURL)
        }
    }
}

enum VideoPreviewFactory {
    static func thumbnail(for url: URL) -> UIImage? {
        let asset = AVAsset(url: url)
        let generator = AVAssetImageGenerator(asset: asset)
        generator.appliesPreferredTrackTransform = true
        generator.maximumSize = CGSize(width: 960, height: 960)

        let candidateTimes = [
            CMTime(seconds: 0.5, preferredTimescale: 600),
            .zero
        ]

        for time in candidateTimes {
            if let cgImage = try? generator.copyCGImage(at: time, actualTime: nil) {
                return UIImage(cgImage: cgImage)
            }
        }

        return nil
    }
}

struct FlexibleString: Decodable, Hashable {
    let value: String

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()

        if let stringValue = try? container.decode(String.self) {
            value = stringValue
            return
        }

        if let intValue = try? container.decode(Int.self) {
            value = String(intValue)
            return
        }

        if let doubleValue = try? container.decode(Double.self) {
            if doubleValue.rounded(.towardZero) == doubleValue {
                value = String(Int(doubleValue))
            } else {
                value = String(format: "%.2f", doubleValue)
            }
            return
        }

        if let boolValue = try? container.decode(Bool.self) {
            value = boolValue ? "true" : "false"
            return
        }

        throw DecodingError.dataCorruptedError(
            in: container,
            debugDescription: "Unsupported value type."
        )
    }
}

private struct AnyCodingKey: CodingKey {
    let stringValue: String
    let intValue: Int?

    init(stringValue: String) {
        self.stringValue = stringValue
        intValue = nil
    }

    init(intValue: Int) {
        self.stringValue = String(intValue)
        self.intValue = intValue
    }
}

enum JSONValue: Hashable, Decodable {
    case object([String: JSONValue])
    case array([JSONValue])
    case string(String)
    case number(Double)
    case bool(Bool)
    case null

    init(from decoder: Decoder) throws {
        if let container = try? decoder.container(keyedBy: AnyCodingKey.self) {
            var object: [String: JSONValue] = [:]
            for key in container.allKeys {
                object[key.stringValue] = try container.decode(JSONValue.self, forKey: key)
            }
            self = .object(object)
            return
        }

        if var container = try? decoder.unkeyedContainer() {
            var values: [JSONValue] = []
            while !container.isAtEnd {
                values.append(try container.decode(JSONValue.self))
            }
            self = .array(values)
            return
        }

        let container = try decoder.singleValueContainer()

        if container.decodeNil() {
            self = .null
            return
        }

        if let boolValue = try? container.decode(Bool.self) {
            self = .bool(boolValue)
            return
        }

        if let intValue = try? container.decode(Int.self) {
            self = .number(Double(intValue))
            return
        }

        if let doubleValue = try? container.decode(Double.self) {
            self = .number(doubleValue)
            return
        }

        if let stringValue = try? container.decode(String.self) {
            self = .string(stringValue)
            return
        }

        throw DecodingError.dataCorruptedError(
            in: container,
            debugDescription: "Unsupported JSON value."
        )
    }
}

extension JSONValue {
    var objectValue: [String: JSONValue]? {
        if case let .object(object) = self {
            return object
        }
        return nil
    }

    var arrayValue: [JSONValue]? {
        if case let .array(array) = self {
            return array
        }
        return nil
    }

    var stringValue: String? {
        switch self {
        case .string(let value):
            return value.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty
        case .number(let value):
            if value.rounded(.towardZero) == value {
                return String(Int(value))
            }
            return String(format: "%.2f", value)
        case .bool(let value):
            return value ? "true" : "false"
        case .null:
            return nil
        case .array(let values):
            let flattened = values.compactMap { $0.stringValue }.filter { !$0.isEmpty }
            return flattened.isEmpty ? nil : flattened.joined(separator: ", ")
        case .object(let object):
            let primitivePairs = object.keys.sorted().compactMap { key -> String? in
                guard let nested = object[key], nested.isPrimitive else { return nil }
                return "\(key): \(nested.displayString)"
            }

            if !primitivePairs.isEmpty {
                return primitivePairs.joined(separator: " · ")
            }

            return nil
        }
    }

    var displayString: String {
        stringValue ?? "—"
    }

    var isPrimitive: Bool {
        switch self {
        case .string, .number, .bool, .null:
            return true
        case .array, .object:
            return false
        }
    }

    func searchValue(for key: String) -> JSONValue? {
        switch self {
        case .object(let object):
            if let direct = object[key] {
                return direct
            }

            for child in object.values {
                if let nested = child.searchValue(for: key) {
                    return nested
                }
            }
        case .array(let array):
            for child in array {
                if let nested = child.searchValue(for: key) {
                    return nested
                }
            }
        case .string, .number, .bool, .null:
            break
        }

        return nil
    }

    func stringArray(preferredKeys: [String] = []) -> [String] {
        switch self {
        case .array(let array):
            return array.flatMap { element in
                if let extracted = element.stringValue(preferredKeys: preferredKeys) {
                    return [extracted]
                }
                return element.flattenedLines()
            }
        case .object(let object):
            for key in preferredKeys {
                if let nested = object[key] {
                    return nested.stringArray(preferredKeys: preferredKeys)
                }
            }
            return flattenedLines()
        case .string, .number, .bool, .null:
            if let extracted = stringValue(preferredKeys: preferredKeys) {
                return [extracted]
            }
            return []
        }
    }

    func flattenedLines(prefix: String? = nil) -> [String] {
        switch self {
        case .string, .number, .bool, .null:
            if let prefix {
                return ["\(prefix): \(displayString)"]
            }
            return [displayString]
        case .array(let array):
            guard !array.isEmpty else {
                return prefix.map { ["\($0): —"] } ?? []
            }

            return array.enumerated().flatMap { index, element in
                let nestedPrefix = prefix.map { "\($0)[\(index)]" } ?? "[\(index)]"

                if element.isPrimitive {
                    return ["\(nestedPrefix): \(element.displayString)"]
                }

                let nestedLines = element.flattenedLines(prefix: nestedPrefix)
                return nestedLines.isEmpty ? ["\(nestedPrefix): \(element.displayString)"] : nestedLines
            }
        case .object(let object):
            guard !object.isEmpty else {
                return prefix.map { ["\($0): {}"] } ?? ["{}"]
            }

            return object.keys.sorted().flatMap { key in
                guard let value = object[key] else {
                    return [String]()
                }

                let nestedPrefix = prefix.map { "\($0).\(key)" } ?? key

                if value.isPrimitive {
                    return ["\(nestedPrefix): \(value.displayString)"]
                }

                let nestedLines = value.flattenedLines(prefix: nestedPrefix)
                return nestedLines.isEmpty ? ["\(nestedPrefix): \(value.displayString)"] : nestedLines
            }
        }
    }

    func stringValue(preferredKeys: [String]) -> String? {
        switch self {
        case .string(let value):
            return value.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty
        case .number(let value):
            if value.rounded(.towardZero) == value {
                return String(Int(value))
            }
            return String(format: "%.2f", value)
        case .bool(let value):
            return value ? "true" : "false"
        case .null:
            return nil
        case .array(let array):
            let strings = array.compactMap { $0.stringValue(preferredKeys: preferredKeys) }
            return strings.isEmpty ? nil : strings.joined(separator: ", ")
        case .object(let object):
            for key in preferredKeys {
                if let nested = object[key], let string = nested.stringValue(preferredKeys: preferredKeys), !string.isEmpty {
                    return string
                }
            }

            if object.count == 1, let nested = object.values.first {
                return nested.stringValue(preferredKeys: preferredKeys)
            }

            let primitivePairs = object.keys.sorted().compactMap { key -> String? in
                guard let nested = object[key], nested.isPrimitive else { return nil }
                return "\(key): \(nested.displayString)"
            }

            return primitivePairs.isEmpty ? nil : primitivePairs.joined(separator: " · ")
        }
    }

    func confidenceValue() -> ResultConfidenceLevel? {
        switch self {
        case .string(let value):
            return ResultConfidenceLevel.parse(from: value)
        case .number(let value):
            return value <= 0.5 ? .low : .high
        case .bool(let value):
            return value ? .high : .low
        case .null:
            return nil
        case .array:
            return nil
        case .object(let object):
            if let nested = object["low_confidence"], let confidence = nested.boolValue {
                return confidence ? .low : .high
            }

            if let nested = object["is_low_confidence"], let confidence = nested.boolValue {
                return confidence ? .low : .high
            }

            if let nested = object["confidence"], let confidence = nested.confidenceValue() {
                return confidence
            }

            if let nested = object["confidence_label"], let string = nested.stringValue, let confidence = ResultConfidenceLevel.parse(from: string) {
                return confidence
            }

            if let nested = object["confidence_level"], let string = nested.stringValue, let confidence = ResultConfidenceLevel.parse(from: string) {
                return confidence
            }

            if let nested = object["confidence_score"], let score = nested.doubleValue {
                return score <= 0.5 ? .low : .high
            }

            return nil
        }
    }

    var boolValue: Bool? {
        switch self {
        case .bool(let value):
            return value
        case .string(let value):
            switch value.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() {
            case "true", "1", "yes", "low_confidence", "low":
                return true
            case "false", "0", "no", "high_confidence", "high":
                return false
            default:
                return nil
            }
        case .number(let value):
            return value != 0
        case .array, .object, .null:
            return nil
        }
    }

    var doubleValue: Double? {
        switch self {
        case .number(let value):
            return value
        case .string(let value):
            return Double(value.trimmingCharacters(in: .whitespacesAndNewlines))
        case .bool(let value):
            return value ? 1 : 0
        case .array, .object, .null:
            return nil
        }
    }
}

private extension ResultConfidenceLevel {
    static func parse(from string: String) -> ResultConfidenceLevel? {
        let normalized = string
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()

        switch normalized {
        case "high", "high_confidence", "high confidence", "confident", "strong", "true", "高", "高置信度":
            return .high
        case "low", "low_confidence", "low confidence", "uncertain", "weak", "false", "低", "低置信度":
            return .low
        default:
            return nil
        }
    }
}

struct VideoAnalysisResponse: Decodable {
    struct MetricSnapshot: Hashable {
        let value: String
        let band: String?
        let confidence: ResultConfidenceLevel

        var confidenceBadgeText: String? {
            confidence == .low ? confidence.displayLabel : nil
        }
    }

    struct DebugSnapshot: Hashable {
        let matchedKey: [String]
        let weight: [String]
        let sourceClass: [String]
        let rawActionCandidates: [String]
        let candidateScores: [String]
        let metricDebug: [String]
        let qualityGate: [String]
    }

    struct ConsistencyState: Hashable {
        let shouldBlockDisplay: Bool
        let summary: String
        let reasons: [String]
        let safeActionDisplayName: String
        let safeLevelLabelText: String
    }

    struct MatchAnalysisSnapshot: Hashable {
        let title: String
        let status: String
        let summary: String
        let durationText: String
        let captureQuality: String
        let captureScore: String
        let methodology: [String]
        let reliabilityNotes: [String]
        let physicalStats: [MatchStat]
        let eventStats: [MatchStat]
        let substitutionSegments: [MatchSegment]
        let biomechanics: [String]
        let timeline: [MatchTimelineItem]
    }

    struct MatchStat: Hashable, Identifiable {
        let id: String
        let title: String
        let value: String
        let detail: String
        let status: String
    }

    struct MatchSegment: Hashable, Identifiable {
        let id: String
        let title: String
        let minutes: String
        let summary: String
        let status: String
    }

    struct MatchTimelineItem: Hashable, Identifiable {
        let id: String
        let minute: String
        let label: String
        let detail: String
    }

    let actionName: String?
    let actionDisplayName: String?
    let resolvedActionName: String?
    let mappedRuleKey: String?
    let recommendedTemplate: String?
    let detectedAction: String?
    let rawDetectedAction: String?
    let selectedActionValue: String?
    let analysisRoutedBy: String?
    let routedAnalyzer: String?
    let analysisStatus: String?
    let failureMessage: String?
    let failureReason: String?
    let overallScore: String?
    let levelLabel: String?
    let summary: String?
    let metrics: [ResultMetricKey: MetricSnapshot]
    let feedbackMessages: [String]
    let matchAnalysis: MatchAnalysisSnapshot?
    let debug: DebugSnapshot

    init(from decoder: Decoder) throws {
        let root = try JSONValue(from: decoder)
        let payload = root.analysisPayload
        self = Self.resolve(from: payload)
    }

    private init(
        actionName: String?,
        actionDisplayName: String?,
        resolvedActionName: String?,
        mappedRuleKey: String?,
        recommendedTemplate: String?,
        detectedAction: String?,
        rawDetectedAction: String?,
        selectedActionValue: String?,
        analysisRoutedBy: String?,
        routedAnalyzer: String?,
        analysisStatus: String?,
        failureMessage: String?,
        failureReason: String?,
        overallScore: String?,
        levelLabel: String?,
        summary: String?,
        metrics: [ResultMetricKey: MetricSnapshot],
        feedbackMessages: [String],
        matchAnalysis: MatchAnalysisSnapshot?,
        debug: DebugSnapshot
    ) {
        self.actionName = actionName
        self.actionDisplayName = actionDisplayName
        self.resolvedActionName = resolvedActionName
        self.mappedRuleKey = mappedRuleKey
        self.recommendedTemplate = recommendedTemplate
        self.detectedAction = detectedAction
        self.rawDetectedAction = rawDetectedAction
        self.selectedActionValue = selectedActionValue
        self.analysisRoutedBy = analysisRoutedBy
        self.routedAnalyzer = routedAnalyzer
        self.analysisStatus = analysisStatus
        self.failureMessage = failureMessage
        self.failureReason = failureReason
        self.overallScore = overallScore
        self.levelLabel = levelLabel
        self.summary = summary
        self.metrics = metrics
        self.feedbackMessages = feedbackMessages
        self.matchAnalysis = matchAnalysis
        self.debug = debug
    }

    var actionDisplayNameText: String {
        consistencyState.safeActionDisplayName
    }

    var backendActionDisplayNameText: String {
        Self.derivedActionDisplayName(
            from: actionDisplayName?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty ?? primaryActionKey
        )
    }

    func preferredActionDisplayName(selectedAction: AnalysisActionChoice? = nil) -> String {
        selectedAction?.displayTitle ?? backendActionDisplayNameText
    }

    func actionSuggestionText(selectedAction: AnalysisActionChoice?) -> String? {
        guard let selectedAction else {
            return nil
        }

        let backendActionDisplay = backendActionDisplayNameText
        guard !Self.displayNamesMatch(selectedAction.displayTitle, backendActionDisplay) else {
            return nil
        }

        return "系统建议：这段视频更像\(backendActionDisplay)，当前仍按你选择的“\(selectedAction.displayTitle)”进行分析"
    }

    func routeMismatchMessage(selectedAction: AnalysisActionChoice?) -> String? {
        guard let selectedAction else {
            return nil
        }

        let expectedValue = selectedAction.selectedActionValue
        let backendSelectedAction = backendSelectedActionChoice
        let routedBy = analysisRoutedBy?.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()

        guard let backendSelectedAction else {
            return "当前分析没有按你选择的动作类型执行"
        }

        guard backendSelectedAction.selectedActionValue == expectedValue else {
            return "当前分析没有按你选择的动作类型执行"
        }

        guard routedBy == "user_selected" else {
            return "当前分析没有按你选择的动作类型执行"
        }

        return nil
    }

    var overallScoreText: String {
        overallScore?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty ?? "未返回"
    }

    var overallScoreValue: Int? {
        guard let matchRange = overallScoreText.range(of: #"\d+(?:\.\d+)?"#, options: .regularExpression) else {
            return nil
        }

        let token = String(overallScoreText[matchRange])
        if let intValue = Int(token) {
            return intValue
        }

        if let doubleValue = Double(token) {
            return Int(doubleValue.rounded())
        }

        return nil
    }

    var levelLabelText: String {
        consistencyState.safeLevelLabelText
    }

    var backendLevelLabelText: String {
        levelLabel?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty ?? fallbackLevelLabel
    }

    private var backendSelectedActionChoice: AnalysisActionChoice? {
        AnalysisActionChoice.backendMatch(for: selectedActionValue)
    }

    var summaryText: String {
        if consistencyState.shouldBlockDisplay {
            return consistencyState.summary
        }

        return summary?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty ?? "后端暂未返回总结。"
    }

    var trainingSuggestionMessages: [String] {
        feedbackMessages
    }

    var trainingSuggestions: [String] {
        feedbackMessages
    }

    var analysisStatusText: String {
        analysisStatus?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty ?? "未返回"
    }

    var failureMessageText: String? {
        failureMessage?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty
    }

    var failureReasonText: String? {
        failureReason?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty
    }

    var isAnalysisFailure: Bool {
        guard let normalized = analysisStatus?.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() else {
            return false
        }

        return ["failed", "failure", "error"].contains(normalized)
    }

    var routeDebugText: String {
        [
            "analysis_status: \(analysisStatusText)",
            "failure_reason: \(failureReasonText ?? "nil")",
            "failure_message: \(failureMessageText ?? "nil")",
            "analysis_routed_by: \(analysisRoutedBy?.nonEmpty ?? "nil")",
            "routed_analyzer: \(routedAnalyzer?.nonEmpty ?? "nil")"
        ]
        .joined(separator: "\n")
    }

    func metricSnapshot(for key: ResultMetricKey) -> MetricSnapshot? {
        metrics[key]
    }

    func metricValueText(for key: ResultMetricKey) -> String {
        metricSnapshot(for: key)?.value ?? "未返回"
    }

    func metricBandText(for key: ResultMetricKey) -> String? {
        metricSnapshot(for: key)?.band?.nonEmpty
    }

    func metricConfidence(for key: ResultMetricKey) -> ResultConfidenceLevel {
        metricSnapshot(for: key)?.confidence ?? key.defaultConfidence
    }

    func isLowConfidence(for key: ResultMetricKey) -> Bool {
        metricConfidence(for: key) == .low
    }

    var consistencyState: ConsistencyState {
        let mainActionKey = primaryActionKey
        let mainActionDisplay = Self.derivedActionDisplayName(from: mainActionKey)
        let rawActionDisplay = actionDisplayName?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty
        let rawLevelLabel = levelLabel?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty ?? fallbackLevelLabel

        var reasons: [String] = []

        if let rawActionDisplay, !Self.displayNamesMatch(rawActionDisplay, mainActionDisplay) {
            reasons.append("动作类型和模板信息不一致，已优先采用后端主动作字段")
        }

        if let recommendedTemplate {
            let recommendedDisplay = Self.derivedActionDisplayName(from: recommendedTemplate)
            if !recommendedDisplay.isEmpty, !Self.displayNamesMatch(recommendedDisplay, mainActionDisplay) {
                reasons.append("动作模板和本次主动作不一致，已优先采用后端主动作字段")
            }
        }

        if let detectedAction {
            let detectedDisplay = Self.derivedActionDisplayName(from: detectedAction)
            if !detectedDisplay.isEmpty, !Self.displayNamesMatch(detectedDisplay, mainActionDisplay) {
                reasons.append("识别到的动作与主动作结果不一致，已优先采用后端主动作字段")
            }
        }

        if let scoreValue = overallScoreValue,
           let scoreRank = Self.scoreRank(for: scoreValue),
           let labelRank = Self.labelRank(for: rawLevelLabel),
           abs(scoreRank - labelRank) >= 2 {
            reasons.append("总分和等级不匹配，当前结果不建议直接相信")
        }

        let shouldBlockDisplay = !reasons.isEmpty
        if shouldBlockDisplay {
            print("[Kick][VideoAnalysis][Integrity] blocked=true reasons=\(reasons.joined(separator: " | ")) action_name=\(mainActionKey) action_display_name=\(rawActionDisplay ?? "nil") resolved_action_name=\(resolvedActionName ?? "nil") mapped_rule_key=\(mappedRuleKey ?? "nil") recommended_template=\(recommendedTemplate ?? "nil") detected_action=\(detectedAction ?? "nil") raw_detected_action=\(rawDetectedAction ?? "nil") overall_score=\(overallScoreText) level_label=\(rawLevelLabel)")
        }

        return ConsistencyState(
            shouldBlockDisplay: shouldBlockDisplay,
            summary: "本次结果存在异常，请重新分析",
            reasons: reasons,
            safeActionDisplayName: shouldBlockDisplay ? mainActionDisplay : (rawActionDisplay ?? mainActionDisplay),
            safeLevelLabelText: shouldBlockDisplay ? "异常" : rawLevelLabel
        )
    }

    var integrityState: TrainingFeedbackResultIntegrityState {
        let state = consistencyState
        return TrainingFeedbackResultIntegrityState(
            shouldBlockDisplay: state.shouldBlockDisplay,
            summary: state.summary,
            reasons: state.reasons,
            safeActionDisplayName: state.safeActionDisplayName,
            safeLevelLabelText: state.safeLevelLabelText
        )
    }

    func resolvedIntegrityState(selectedAction: AnalysisActionChoice? = nil) -> TrainingFeedbackResultIntegrityState {
        guard selectedAction != nil else {
            return integrityState
        }

        let reasons = scoreLevelMismatchReason.map { [$0] } ?? []
        if reasons.isEmpty {
            return .clean
        }

        let rawLevelLabel = levelLabel?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty ?? fallbackLevelLabel
        print("[Kick][VideoAnalysis][Integrity] blocked=true reasons=\(reasons.joined(separator: " | ")) selected_action=\(selectedAction?.selectedActionValue ?? "nil") action_display_name=\(backendActionDisplayNameText) overall_score=\(overallScoreText) level_label=\(rawLevelLabel)")

        return TrainingFeedbackResultIntegrityState(
            shouldBlockDisplay: true,
            summary: "本次结果存在异常，请重新分析",
            reasons: reasons,
            safeActionDisplayName: selectedAction?.displayTitle ?? backendActionDisplayNameText,
            safeLevelLabelText: "异常"
        )
    }

    var pendingFindings: [ResultFinding] {
        ResultMetricKey.allCases.compactMap { key in
            guard isLowConfidence(for: key) else {
                return nil
            }

            return ResultFinding(
                trigger: .lowConfidence,
                title: pendingTitle(for: key),
                detail: pendingDetail(for: key)
            )
        }
    }

    private var fallbackLevelLabel: String {
        guard let score = overallScoreValue else {
            return "未返回"
        }

        switch score {
        case 90...:
            return "A级"
        case 80..<90:
            return "B级"
        case 70..<80:
            return "C级"
        default:
            return "D级"
        }
    }

    private var scoreLevelMismatchReason: String? {
        guard let scoreValue = overallScoreValue,
              let scoreRank = Self.scoreRank(for: scoreValue) else {
            return nil
        }

        let rawLevelLabel = levelLabel?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty ?? fallbackLevelLabel
        guard let labelRank = Self.labelRank(for: rawLevelLabel),
              abs(scoreRank - labelRank) >= 2 else {
            return nil
        }

        return "总分和等级不匹配，当前结果不建议直接相信"
    }

    private func pendingTitle(for key: ResultMetricKey) -> String {
        switch key {
        case .passReceiveGapS:
            return "传接间隔低置信"
        case .nextActionReadiness:
            return "下一动作准备度低置信"
        default:
            return "\(key.displayTitle)低置信"
        }
    }

    private func pendingDetail(for key: ResultMetricKey) -> String {
        switch key {
        case .passReceiveGapS:
            return "这一项当前样本下的结论还不够稳定，建议结合更多视频再确认。"
        case .nextActionReadiness:
            return "下一动作准备度更适合结合连续片段一起看，先作为参考即可。"
        default:
            return "这一项当前置信度偏低，先作为参考，不要直接当成错误结论。"
        }
    }

    private static func resolve(from payload: JSONValue) -> VideoAnalysisResponse {
        let actionName = stringValue(for: ["action_name", "actionName"], in: payload)
        let actionDisplayName = stringValue(
            for: ["action_display_name", "actionDisplayName", "action_label", "actionLabel", "motion_type", "motionType"],
            in: payload
        )
        let resolvedActionName = stringValue(for: ["resolved_action_name", "resolvedActionName"], in: payload)
        let mappedRuleKey = stringValue(for: ["mapped_rule_key", "mappedRuleKey"], in: payload)
        let recommendedTemplate = stringValue(for: ["recommended_template", "recommendedTemplate"], in: payload)
        let detectedAction = stringValue(for: ["detected_action", "detectedAction"], in: payload)
        let rawDetectedAction = stringValue(for: ["raw_detected_action", "rawDetectedAction"], in: payload)
        let selectedActionValue = stringValue(for: ["selected_action", "selectedAction"], in: payload)
        let analysisRoutedBy = stringValue(for: ["analysis_routed_by", "analysisRoutedBy"], in: payload)
        let routedAnalyzer = stringValue(for: ["routed_analyzer", "routedAnalyzer"], in: payload)
        let analysisStatus = stringValue(for: ["analysis_status", "analysisStatus", "status", "state"], in: payload)
        let failureMessage = stringValue(
            for: ["failure_message", "failureMessage", "message", "detail", "error_message", "errorMessage"],
            in: payload
        )
        let failureReason = stringValue(
            for: ["failure_reason", "failureReason", "reason", "failure_detail", "failureDetail"],
            in: payload
        )
        let overallScore = stringValue(
            for: ["overall_score", "overallScore", "total_score", "totalScore"],
            in: payload
        ) ?? nestedStringValue(
            parentKeys: ["score"],
            childKeys: ["overall", "overall_score", "overallScore", "total_score", "totalScore"],
            in: payload
        )
        let levelLabel = stringValue(
            for: ["level_label", "levelLabel", "grade", "summary_tag", "summaryTag"],
            in: payload
        ) ?? nestedStringValue(
            parentKeys: ["score"],
            childKeys: ["level_label", "levelLabel", "grade"],
            in: payload
        )
        let summary = stringValue(for: ["summary", "overall_summary", "overallSummary"], in: payload)
        let feedbackMessages = stringArray(for: ["feedback_messages", "feedbackMessages"], in: payload)

        let matchedKeyLines = stringArray(for: ["matched_key", "matchedKey", "matched_keys", "matchedKeys"], in: payload)
        let weightLines = stringArray(for: ["weight", "weights"], in: payload)
        let sourceClassLines = stringArray(for: ["source_class", "sourceClass", "source_classes", "sourceClasses"], in: payload)
        let candidateScoreLines = stringArray(for: ["candidate_scores", "candidateScores"], in: payload)
        let metricDebugLines = stringArray(for: ["metric_debug", "metricDebug"], in: payload)

        let metrics = decodeMetrics(in: payload, metricDebugLines: metricDebugLines)
        let matchAnalysis = parseMatchAnalysis(in: payload)
        let rawActionCandidates = stringArray(for: ["raw_action_candidates", "rawActionCandidates"], in: payload)
        let qualityGateLines = stringArray(for: ["quality_gate", "qualityGate"], in: payload)

        return VideoAnalysisResponse(
            actionName: actionName,
            actionDisplayName: actionDisplayName,
            resolvedActionName: resolvedActionName,
            mappedRuleKey: mappedRuleKey,
            recommendedTemplate: recommendedTemplate,
            detectedAction: detectedAction,
            rawDetectedAction: rawDetectedAction,
            selectedActionValue: selectedActionValue,
            analysisRoutedBy: analysisRoutedBy,
            routedAnalyzer: routedAnalyzer,
            analysisStatus: analysisStatus,
            failureMessage: failureMessage,
            failureReason: failureReason,
            overallScore: overallScore,
            levelLabel: levelLabel,
            summary: summary,
            metrics: metrics,
            feedbackMessages: feedbackMessages,
            matchAnalysis: matchAnalysis,
            debug: DebugSnapshot(
                matchedKey: matchedKeyLines,
                weight: weightLines,
                sourceClass: sourceClassLines,
                rawActionCandidates: rawActionCandidates,
                candidateScores: candidateScoreLines,
                metricDebug: metricDebugLines,
                qualityGate: qualityGateLines
            )
        )
    }

    private var primaryActionKey: String {
        [
            actionName,
            resolvedActionName,
            mappedRuleKey,
            recommendedTemplate,
            detectedAction,
            rawDetectedAction,
            actionDisplayName
        ]
        .compactMap { $0?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty }
        .first ?? ""
    }

    private static func derivedActionDisplayName(from actionName: String) -> String {
        let lowerAction = actionName.lowercased()
        if lowerAction.contains("full_match") || lowerAction.contains("match_player") || lowerAction.contains("整场比赛") || lowerAction.contains("全场") || lowerAction.contains("比赛分析") || lowerAction.contains("单一球员") {
            return "单一球员分析"
        }
        if lowerAction.contains("uncertain") || lowerAction.contains("pending_confirmation") || lowerAction.contains("needs_confirmation") {
            return "低置信"
        }
        if lowerAction.contains("pass_receive_sequence") || lowerAction.contains("sequence") {
            return "传接球"
        }
        if lowerAction.contains("short_pass") || lowerAction.contains("pass_like") || lowerAction.contains("pass") {
            return "传球"
        }
        if lowerAction.contains("传接球") {
            return "传接球"
        }
        if lowerAction.contains("停球") {
            return "接球"
        }
        if lowerAction.contains("接球") {
            return "接球"
        }
        if lowerAction.contains("receive_control") || lowerAction.contains("first_touch") || lowerAction.contains("touch") {
            return "接球"
        }
        if lowerAction.contains("shot_instep") || lowerAction.contains("shoot") || lowerAction.contains("shot") {
            return "射门"
        }
        return actionName.isEmpty ? "动作" : actionName
    }

    private static func displayNamesMatch(_ lhs: String, _ rhs: String) -> Bool {
        normalizeDisplayName(lhs) == normalizeDisplayName(rhs)
    }

    private static func normalizeDisplayName(_ text: String) -> String {
        text
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
            .replacingOccurrences(of: " ", with: "")
            .replacingOccurrences(of: "·", with: "")
            .replacingOccurrences(of: "-", with: "")
            .replacingOccurrences(of: "_", with: "")
    }

    private static func scoreRank(for score: Int) -> Int? {
        switch score {
        case 90...:
            return 3
        case 80..<90:
            return 2
        case 70..<80:
            return 1
        case 0..<70:
            return 0
        default:
            return nil
        }
    }

    private static func labelRank(for label: String) -> Int? {
        let normalized = normalizeDisplayName(label)
        if normalized.contains("优秀") || normalized.contains("a级") || normalized == "a" || normalized.contains("excellent") || normalized.contains("理想") {
            return 3
        }
        if normalized.contains("良好") || normalized.contains("b级") || normalized == "b" || normalized.contains("good") || normalized.contains("稳定") || normalized.contains("流畅") || normalized.contains("可控") {
            return 2
        }
        if normalized.contains("需加强") || normalized.contains("需提升") || normalized.contains("c级") || normalized == "c" || normalized.contains("review") || normalized.contains("观察中") {
            return 1
        }
        if normalized.contains("poor") || normalized.contains("d级") || normalized == "d" || normalized.contains("需修正") || normalized.contains("偏高") || normalized.contains("偏慢") {
            return 0
        }
        return nil
    }

    private static func decodeMetrics(
        in payload: JSONValue,
        metricDebugLines: [String]
    ) -> [ResultMetricKey: MetricSnapshot] {
        var metrics: [ResultMetricKey: MetricSnapshot] = [:]

        for key in ResultMetricKey.allCases {
            guard let rawValue = firstValue(for: key.rawValue, in: payload) else {
                continue
            }

            let valueText = metricValueText(from: rawValue)
            let band = metricBandText(from: rawValue)
            let confidence = metricConfidence(
                for: key,
                rawValue: rawValue,
                metricDebugLines: metricDebugLines
            )

            metrics[key] = MetricSnapshot(
                value: valueText,
                band: band,
                confidence: confidence
            )
        }

        return metrics
    }

    private static func metricValueText(from value: JSONValue) -> String {
        if let object = value.objectValue {
            let preferredKeys = [
                "display_value",
                "displayValue",
                "text",
                "result",
                "current_value",
                "currentValue",
                "score",
                "value"
            ]

            for key in preferredKeys {
                guard let nested = object[key],
                      let string = nested.stringValue(preferredKeys: preferredKeys),
                      let cleaned = cleanMetricDisplayText(string)
                else {
                    continue
                }
                return cleaned
            }

            let statusText = object["band"]?.stringValue(preferredKeys: [])
                ?? object["status"]?.stringValue(preferredKeys: [])
                ?? object["level"]?.stringValue(preferredKeys: [])

            if let statusText,
               statusText.localizedCaseInsensitiveContains("reference") ||
                statusText.localizedCaseInsensitiveContains("low") ||
                statusText.localizedCaseInsensitiveContains("unresolved") ||
                statusText.localizedCaseInsensitiveContains("待确认") {
                return "参考项"
            }

            if object.keys.contains(where: isMetricDebugKey) {
                return "待确认"
            }
        }

        let rawText = value.stringValue(preferredKeys: ["display_value", "displayValue", "text", "result", "score", "value", "current_value", "currentValue"])
            ?? value.displayString
        return cleanMetricDisplayText(rawText) ?? "待确认"
    }

    nonisolated private static func cleanMetricDisplayText(_ text: String) -> String? {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }

        let lowercased = trimmed.lowercased()
        let debugMarkers = [
            "band:",
            "confidence:",
            "source:",
            "event_source:",
            "fallback_to_video_end:",
            "start_event:",
            "end_event:",
            "low_confidence:",
            "resolved:"
        ]

        if debugMarkers.contains(where: { lowercased.contains($0) }) {
            return nil
        }

        if trimmed.count > 42 && trimmed.contains(":") {
            return nil
        }

        return trimmed
    }

    nonisolated private static func isMetricDebugKey(_ key: String) -> Bool {
        let normalized = key.lowercased()
        return normalized.contains("source") ||
            normalized.contains("confidence") ||
            normalized.contains("event") ||
            normalized.contains("fallback") ||
            normalized.contains("resolved") ||
            normalized.contains("debug")
    }

    private static func metricBandText(from value: JSONValue) -> String? {
        guard let object = value.objectValue else {
            return nil
        }

        for key in ["band", "label", "status", "level", "state", "quality"] {
            if let nested = object[key], let string = nested.stringValue(preferredKeys: [])?.nonEmpty {
                return string
            }
        }

        return nil
    }

    private static func metricConfidence(
        for key: ResultMetricKey,
        rawValue: JSONValue,
        metricDebugLines: [String]
    ) -> ResultConfidenceLevel {
        if let confidence = rawValue.confidenceValue() {
            return confidence
        }

        if metricDebugLines.contains(where: { line in
            line.localizedCaseInsensitiveContains(key.rawValue) &&
                line.localizedCaseInsensitiveContains("low_confidence")
        }) {
            return .low
        }

        if metricDebugLines.contains(where: { line in
            line.localizedCaseInsensitiveContains(key.rawValue) &&
                (line.localizedCaseInsensitiveContains("confidence=low") || line.localizedCaseInsensitiveContains("confidence: low") || line.localizedCaseInsensitiveContains("low confidence"))
        }) {
            return .low
        }

        return key.defaultConfidence
    }

    private static func stringValue(for keys: [String], in payload: JSONValue) -> String? {
        for key in keys {
            if let value = firstValue(for: key, in: payload), let string = value.stringValue(preferredKeys: ["value", "current_value", "currentValue", "display_value", "displayValue", "text", "result"]) {
                return string
            }
        }

        return nil
    }

    private static func stringArray(for keys: [String], in payload: JSONValue) -> [String] {
        for key in keys {
            if let value = firstValue(for: key, in: payload) {
                return value.stringArray(preferredKeys: ["message", "text", "detail", "content", "summary", "value"])
            }
        }

        return []
    }

    private static func nestedStringValue(parentKeys: [String], childKeys: [String], in payload: JSONValue) -> String? {
        for parentKey in parentKeys {
            guard let object = firstValue(for: parentKey, in: payload)?.objectValue else {
                continue
            }

            for childKey in childKeys {
                if let nested = object[childKey],
                   let string = nested.stringValue(preferredKeys: ["value", "current_value", "currentValue", "display_value", "displayValue", "text", "result"])?.nonEmpty {
                    return string
                }
            }
        }

        return nil
    }

    private static func firstValue(for key: String, in payload: JSONValue) -> JSONValue? {
        if case let .object(object) = payload, let direct = object[key] {
            return direct
        }

        return payload.searchValue(for: key)
    }

    private static func parseMatchAnalysis(in payload: JSONValue) -> MatchAnalysisSnapshot? {
        let matchValue = firstValue(for: "match_analysis", in: payload) ?? firstValue(for: "matchAnalysis", in: payload)
        guard let object = matchValue?.objectValue else {
            return nil
        }

        let capture = object["capture"]?.objectValue ?? [:]
        let durationText: String
        if let durationMin = capture["duration_min"]?.doubleValue {
            durationText = String(format: "%.1f 分钟", durationMin)
        } else if let durationS = capture["duration_s"]?.doubleValue {
            durationText = String(format: "%.1f 秒", durationS)
        } else {
            durationText = "待读取"
        }

        let captureQuality = capture["quality_label"]?.stringValue(preferredKeys: []) ?? "待标定"
        let captureScore = capture["quality_score"]?.stringValue(preferredKeys: []) ?? "—"
        let playerTracking = object["player_tracking"]?.objectValue ?? [:]
        let events = object["events"]?.objectValue ?? [:]
        let substitution = object["substitution_analysis"]?.objectValue ?? [:]
        let biomechanics = object["biomechanics"]?.objectValue ?? [:]

        return MatchAnalysisSnapshot(
            title: object["title"]?.stringValue(preferredKeys: []) ?? "长视频单一球员分析",
            status: object["status"]?.stringValue(preferredKeys: []) ?? "requires_player_lock",
            summary: object["summary"]?.stringValue(preferredKeys: []) ?? "请先锁定目标球员后继续分析。",
            durationText: durationText,
            captureQuality: captureQuality,
            captureScore: captureScore,
            methodology: object["methodology"]?.stringArray(preferredKeys: ["text", "value"]) ?? [],
            reliabilityNotes: object["reliability_notes"]?.stringArray(preferredKeys: ["text", "value"]) ?? [],
            physicalStats: parseMatchStats(from: playerTracking["stats"]),
            eventStats: parseMatchStats(from: events["stats"]),
            substitutionSegments: parseMatchSegments(from: substitution["segments"]),
            biomechanics: biomechanics["items"]?.stringArray(preferredKeys: ["text", "value"]) ?? [],
            timeline: parseMatchTimeline(from: events["timeline"])
        )
    }

    private static func parseMatchStats(from value: JSONValue?) -> [MatchStat] {
        guard let array = value?.arrayValue else {
            return []
        }

        return array.enumerated().compactMap { index, value in
            guard let object = value.objectValue else {
                return nil
            }

            let key = object["key"]?.stringValue(preferredKeys: []) ?? "stat_\(index)"
            let displayValue = object["display_value"]?.stringValue(preferredKeys: [])
                ?? object["value"]?.stringValue(preferredKeys: [])
                ?? "待锁定球员"
            return MatchStat(
                id: key,
                title: object["title"]?.stringValue(preferredKeys: []) ?? key,
                value: displayValue,
                detail: object["detail"]?.stringValue(preferredKeys: []) ?? "",
                status: object["status"]?.stringValue(preferredKeys: []) ?? ""
            )
        }
    }

    private static func parseMatchSegments(from value: JSONValue?) -> [MatchSegment] {
        guard let array = value?.arrayValue else {
            return []
        }

        return array.enumerated().compactMap { index, value in
            guard let object = value.objectValue else {
                return nil
            }

            let id = object["id"]?.stringValue(preferredKeys: []) ?? "segment_\(index)"
            let minutes: String
            if let minuteValue = object["minutes"]?.doubleValue {
                minutes = String(format: "%.1f 分钟", minuteValue)
            } else {
                minutes = "待标记"
            }

            return MatchSegment(
                id: id,
                title: object["title"]?.stringValue(preferredKeys: []) ?? "比赛阶段",
                minutes: minutes,
                summary: object["summary"]?.stringValue(preferredKeys: []) ?? "",
                status: object["status"]?.stringValue(preferredKeys: []) ?? ""
            )
        }
    }

    private static func parseMatchTimeline(from value: JSONValue?) -> [MatchTimelineItem] {
        guard let array = value?.arrayValue else {
            return []
        }

        return array.enumerated().compactMap { index, value in
            guard let object = value.objectValue else {
                return nil
            }

            let minute: String
            if let minuteValue = object["minute"]?.doubleValue {
                minute = String(format: "%.1f'", minuteValue)
            } else {
                minute = "—"
            }

            return MatchTimelineItem(
                id: object["event"]?.stringValue(preferredKeys: []) ?? "timeline_\(index)",
                minute: minute,
                label: object["label"]?.stringValue(preferredKeys: []) ?? "事件",
                detail: object["detail"]?.stringValue(preferredKeys: []) ?? ""
            )
        }
    }
}

private extension JSONValue {
    var analysisPayload: JSONValue {
        var current = self

        while case .object(let object) = current {
            guard let nested = object["data"] ?? object["result"] ?? object["analysis"] ?? object["payload"] ?? object["response"] else {
                break
            }
            current = nested
        }

        return current
    }
}
