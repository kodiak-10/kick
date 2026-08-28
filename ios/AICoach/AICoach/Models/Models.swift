import Foundation

enum TrainingGoal: String, CaseIterable, Identifiable, Codable, Hashable {
    case shooting
    case passing
    case firstTouch

    var id: String { rawValue }

    var title: String {
        switch self {
        case .shooting:
            return "射门动作质量"
        case .passing:
            return "传球稳定性"
        case .firstTouch:
            return "停球控制"
        }
    }

    var subtitle: String {
        switch self {
        case .shooting:
            return "支撑脚、摆腿轨迹、触球完成度"
        case .passing:
            return "出球方向、节奏与身体对齐"
        case .firstTouch:
            return "第一脚控制、缓冲与重心管理"
        }
    }

    var displayTitle: String {
        switch self {
        case .shooting:
            return "射门"
        case .passing:
            return "传球"
        case .firstTouch:
            return "停球"
        }
    }

    var englishTitle: String {
        switch self {
        case .shooting:
            return "Shooting"
        case .passing:
            return "Passing"
        case .firstTouch:
            return "First Touch"
        }
    }

    var purpose: String {
        switch self {
        case .shooting:
            return "先看支撑脚、上体后仰和随摆是否完整。"
        case .passing:
            return "先看出球方向、触球节奏和身体对齐是否稳定。"
        case .firstTouch:
            return "先看第一脚缓冲、重心回收和控制区是否稳。"
        }
    }

    var backendActionName: String {
        switch self {
        case .shooting:
            return "shot"
        case .passing:
            return "pass"
        case .firstTouch:
            return "receive_control"
        }
    }

    var backendAnalysisTemplateName: String {
        switch self {
        case .shooting:
            return "shot_instep"
        case .passing:
            return "short_pass"
        case .firstTouch:
            return "receive_control"
        }
    }

    var coreMetrics: [String] {
        switch self {
        case .shooting:
            return ["支撑脚落点", "上体后仰", "随摆完整度"]
        case .passing:
            return ["出球方向", "触球节奏", "身体对齐"]
        case .firstTouch:
            return ["第一脚缓冲", "重心回收", "控制区"]
        }
    }

    var templateStyle: ThumbnailStyle {
        switch self {
        case .shooting:
            return .stadiumBlue
        case .passing:
            return .trainingGreen
        case .firstTouch:
            return .sunsetOrange
        }
    }
}

enum CameraSystemStatus: String, Codable, Hashable {
    case ready = "camera_ready"
    case warning = "camera_warning"
    case error = "camera_error"

    var title: String {
        switch self {
        case .ready:
            return "摄像头已就绪"
        case .warning:
            return "摄像头警告"
        case .error:
            return "摄像头错误"
        }
    }

    var subtitle: String {
        switch self {
        case .ready:
            return "可继续录制并开始分析"
        case .warning:
            return "当前为演示模式，流程可继续"
        case .error:
            return "请检查权限或设备连接"
        }
    }

    var symbol: String {
        switch self {
        case .ready:
            return "camera.fill"
        case .warning:
            return "camera.fill.badge.exclamationmark"
        case .error:
            return "exclamationmark.triangle.fill"
        }
    }
}

enum ResultReportState: String, Codable, Hashable {
    case readyToScore = "ready_to_score"
    case insufficientEvidence = "insufficient_evidence"
    case qualityFail = "quality_fail"
    case needsConfirmation = "needs_confirmation"

    var title: String {
        switch self {
        case .readyToScore:
            return "正式评分"
        case .insufficientEvidence:
            return "证据不足"
        case .qualityFail:
            return "质量不通过"
        case .needsConfirmation:
            return "待确认"
        }
    }

    var subtitle: String {
        switch self {
        case .readyToScore:
            return "动作证据充分，可输出总分与分项分"
        case .insufficientEvidence:
            return "当前只检测到部分动作线索，暂不输出正式评分"
        case .qualityFail:
            return "视频质量不足，建议重拍后再分析"
        case .needsConfirmation:
            return "当前动作类型仍待确认，请补充更清晰视频后再判断"
        }
    }

    var bullets: [String] {
        switch self {
        case .readyToScore:
            return ["动作阶段已锁定", "球轨迹清晰", "可输出正式评分"]
        case .insufficientEvidence:
            return ["动作未完成", "球轨迹不清晰", "阶段未锁定"]
        case .qualityFail:
            return ["画面模糊或抖动", "球体遮挡严重", "不输出技术评分"]
        case .needsConfirmation:
            return ["候选动作接近", "置信度不足", "建议补充更清晰视频"]
        }
    }

    var symbol: String {
        switch self {
        case .readyToScore:
            return "checkmark.seal.fill"
        case .insufficientEvidence:
            return "eye.slash.fill"
        case .qualityFail:
            return "exclamationmark.triangle.fill"
        case .needsConfirmation:
            return "questionmark.circle.fill"
        }
    }
}

enum VideoQualityStatus: String, Codable, Hashable {
    case good
    case limited
    case poor

    var title: String {
        switch self {
        case .good:
            return "视频质量良好"
        case .limited:
            return "视频质量有限"
        case .poor:
            return "视频质量不达标"
        }
    }

    var subtitle: String {
        switch self {
        case .good:
            return "可支持正式评分"
        case .limited:
            return "可用于观察结果"
        case .poor:
            return "建议重拍后再分析"
        }
    }

    var symbol: String {
        switch self {
        case .good:
            return "video.fill"
        case .limited:
            return "video.badge.exclamationmark"
        case .poor:
            return "video.slash.fill"
        }
    }
}

enum AnalysisStatus: String, Codable, Hashable {
    case success
    case failed
    case partial

    var title: String {
        switch self {
        case .success:
            return "成功"
        case .failed:
            return "失败"
        case .partial:
            return "部分完成"
        }
    }

    var subtitle: String {
        switch self {
        case .success:
            return "结果可直接查看"
        case .failed:
            return "本次结果未能完成"
        case .partial:
            return "已完成自动定位分析"
        }
    }

    var symbol: String {
        switch self {
        case .success:
            return "checkmark.seal.fill"
        case .failed:
            return "xmark.octagon.fill"
        case .partial:
            return "clock.arrow.circlepath"
        }
    }
}

enum AnalysisIntegrityState: String, Codable, Hashable {
    case normal
    case routeMismatch = "route_mismatch"
    case anomaly

    var title: String {
        switch self {
        case .normal:
            return "正常"
        case .routeMismatch:
            return "路由提示"
        case .anomaly:
            return "结果异常"
        }
    }

    var subtitle: String {
        switch self {
        case .normal:
            return "当前链路正常"
        case .routeMismatch:
            return "系统建议与当前选择不一致"
        case .anomaly:
            return "检测到结果或路由不一致"
        }
    }

    var symbol: String {
        switch self {
        case .normal:
            return "checkmark.shield.fill"
        case .routeMismatch:
            return "arrow.triangle.2.circlepath"
        case .anomaly:
            return "exclamationmark.shield.fill"
        }
    }
}

enum AnalysisFailureReason: String, Codable, Hashable {
    case videoTooLong = "video_too_long"
    case noActionWindowFound = "no_action_window_found"
    case lowMotionSignal = "low_motion_signal"
    case analysisTimeout = "analysis_timeout"
    case unsupportedAction = "unsupported_action"
    case routeMismatch = "route_mismatch"
    case videoOpenFailed = "video_open_failed"
    case mediapipePoseInitFailed = "mediapipe_pose_init_failed"
    case mediapipePoseRuntimeFailed = "mediapipe_pose_runtime_failed"
    case poseEvidenceLow = "pose_evidence_low"
    case ballEvidenceLow = "ball_evidence_low"
    case contactNotDetected = "contact_not_detected"
    case analysisResultEmpty = "analysis_result_empty"
    case unknownError = "unknown_error"

    var title: String {
        switch self {
        case .videoTooLong:
            return "视频时长过长"
        case .noActionWindowFound, .lowMotionSignal:
            return "未找到有效动作片段"
        case .analysisTimeout:
            return "分析超时"
        case .unsupportedAction:
            return "动作暂不支持"
        case .routeMismatch:
            return "动作路由异常"
        case .videoOpenFailed:
            return "视频无法打开"
        case .mediapipePoseInitFailed:
            return "姿态模型初始化失败"
        case .mediapipePoseRuntimeFailed:
            return "姿态分析运行失败"
        case .poseEvidenceLow, .ballEvidenceLow, .contactNotDetected:
            return "视频证据不足"
        case .analysisResultEmpty:
            return "分析结果为空"
        case .unknownError:
            return "分析失败"
        }
    }

    func message(durationSeconds: Double? = nil) -> String {
        switch self {
        case .videoTooLong:
            if let durationSeconds {
                return String(format: "当前视频为 %.1f 秒，当前版本支持 30 秒以内视频自动分析。", durationSeconds)
            }
            return "当前视频过长，当前版本支持 30 秒以内视频自动分析。"
        case .noActionWindowFound:
            return "请确保视频里包含完整传球动作，且人物和球清晰可见。"
        case .lowMotionSignal:
            return "当前视频动作信号太弱，请确保视频里包含完整传球动作，且人物和球清晰可见。"
        case .analysisTimeout:
            return "当前分析耗时过长，请稍后重试或换更短视频。"
        case .unsupportedAction:
            return "当前动作暂不支持，请切换到已支持的分析模板。"
        case .routeMismatch:
            return "当前动作与分析模型不一致，请重新分析。"
        case .videoOpenFailed:
            return "视频无法打开，请检查文件是否损坏或格式是否受支持。"
        case .mediapipePoseInitFailed:
            return "姿态模型初始化失败，请稍后重试。"
        case .mediapipePoseRuntimeFailed:
            return "姿态分析运行失败，请稍后重试。"
        case .poseEvidenceLow:
            return "请确保全身、球、支撑脚完整入镜，机位固定，动作前后保留 1 秒。"
        case .ballEvidenceLow:
            return "请确保球体完整入镜并持续可见，机位固定，动作前后保留 1 秒。"
        case .contactNotDetected:
            return "请确保触球瞬间清晰入镜，球、支撑脚和全身都能同时看到。"
        case .analysisResultEmpty:
            return "当前视频没有可用的分析结果，请重试。"
        case .unknownError:
            return "本次分析未完成，请重试。"
        }
    }
}

struct AnalysisDebugContext: Codable, Hashable {
    let selectedAction: String
    let systemActionSuggestion: String
    let analysisRoutedBy: String
    let routedAnalyzer: String
    let videoDuration: Double
    let frameCount: Int
    let sampledFrameCount: Int
    let fastModeEnabled: Bool
    let longVideoLocalized: Bool
    let candidateWindowCount: Int
    let selectedWindowIndex: Int?
    let selectedWindowStartSeconds: Double?
    let selectedWindowEndSeconds: Double?
    let selectedWindowDurationSeconds: Double?
    let processingTime: Double?
    let failureReason: String?
    let failureMessage: String?
    let routeMismatchMessage: String?
    let warnings: [String]
}

struct AnalysisRuntimeState: Codable, Hashable {
    let analysisStatus: AnalysisStatus
    let failureReason: AnalysisFailureReason?
    let failureMessage: String?
    let integrityState: AnalysisIntegrityState
    let routeMismatchMessage: String?
    let selectedAction: String
    let systemActionSuggestion: String
    let analysisRoutedBy: String
    let routedAnalyzer: String
    let videoDurationSeconds: Double
    let frameCount: Int
    let sampledFrameCount: Int
    let fastModeEnabled: Bool
    let longVideoLocalized: Bool
    let candidateWindowCount: Int
    let selectedWindowIndex: Int?
    let selectedWindowStartSeconds: Double?
    let selectedWindowEndSeconds: Double?
    let selectedWindowDurationSeconds: Double?
    let processingTimeSeconds: Double?
    let warnings: [String]
    let debugContext: AnalysisDebugContext?

    init(
        analysisStatus: AnalysisStatus = .success,
        failureReason: AnalysisFailureReason? = nil,
        failureMessage: String? = nil,
        integrityState: AnalysisIntegrityState = .normal,
        routeMismatchMessage: String? = nil,
        selectedAction: String = "",
        systemActionSuggestion: String = "",
        analysisRoutedBy: String = "",
        routedAnalyzer: String = "",
        videoDurationSeconds: Double = 0.0,
        frameCount: Int = 0,
        sampledFrameCount: Int = 0,
        fastModeEnabled: Bool = false,
        longVideoLocalized: Bool = false,
        candidateWindowCount: Int = 0,
        selectedWindowIndex: Int? = nil,
        selectedWindowStartSeconds: Double? = nil,
        selectedWindowEndSeconds: Double? = nil,
        selectedWindowDurationSeconds: Double? = nil,
        processingTimeSeconds: Double? = nil,
        warnings: [String] = [],
        debugContext: AnalysisDebugContext? = nil
    ) {
        self.analysisStatus = analysisStatus
        self.failureReason = failureReason
        self.failureMessage = failureMessage
        self.integrityState = integrityState
        self.routeMismatchMessage = routeMismatchMessage
        self.selectedAction = selectedAction
        self.systemActionSuggestion = systemActionSuggestion
        self.analysisRoutedBy = analysisRoutedBy
        self.routedAnalyzer = routedAnalyzer
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
        self.debugContext = debugContext
    }
}

struct ResultObservation: Identifiable, Codable, Hashable {
    let id: UUID
    let phase: MotionStage
    let time: String
    let title: String
    let detail: String
}

struct ResultTimestamp: Identifiable, Codable, Hashable {
    let id: UUID
    let start: Double
    let end: Double
    let label: String
    let detail: String

    var rangeText: String {
        let startText = Self.format(seconds: start)
        let endText = Self.format(seconds: end)
        if abs(start - end) < 0.05 {
            return startText
        }
        return "\(startText) - \(endText)"
    }

    private static func format(seconds: Double) -> String {
        String(format: "%.1fs", seconds)
    }
}

enum ProPlan: String, CaseIterable, Identifiable, Codable, Hashable {
    case monthly
    case yearly

    var id: String { rawValue }

    var title: String {
        switch self {
        case .monthly:
            return "Pro 月订阅"
        case .yearly:
            return "Pro 年订阅"
        }
    }

    var price: String {
        switch self {
        case .monthly:
            return "¥38 / 月"
        case .yearly:
            return "¥268 / 年"
        }
    }

    var badge: String {
        switch self {
        case .monthly:
            return "灵活开通"
        case .yearly:
            return "最划算"
        }
    }
}

enum AnalysisSignalTone: String, Codable, Hashable {
    case good
    case watch
    case warn
    case fail
    case neutral
}

struct AnalysisMetric: Identifiable, Codable, Hashable {
    let key: String
    let title: String
    let valueText: String
    let detail: String
    let tone: AnalysisSignalTone

    var id: String { key }
}

struct RuleTriggerSummary: Identifiable, Codable, Hashable {
    let key: String
    let title: String
    let phase: MotionStage
    let detail: String

    var id: String { key }
}

struct SequenceMetricSummary: Identifiable, Codable, Hashable {
    let id: String
    let title: String
    let valueText: String
    let detail: String
    let tone: AnalysisSignalTone
    let lowConfidence: Bool
}

struct SequenceActionCandidate: Identifiable, Codable, Hashable {
    let action: String
    let score: Double
    let sources: [String]

    var id: String { action }
}

struct ActionCandidate: Identifiable, Codable, Hashable {
    let action: String
    let label: String
    let displayName: String
    let score: Double
    let sources: [String]
    let template: String

    var id: String { action.isEmpty ? label : action }

    var title: String {
        let trimmed = displayName.trimmingCharacters(in: .whitespacesAndNewlines)
        if !trimmed.isEmpty {
            return trimmed
        }

        let fallback = label.trimmingCharacters(in: .whitespacesAndNewlines)
        if !fallback.isEmpty {
            return fallback
        }

        return action
    }

    enum CodingKeys: String, CodingKey {
        case action
        case label
        case displayName = "display_name"
        case score
        case sources
        case template
    }
}

struct SequenceBandLogicStep: Codable, Hashable {
    let condition: String?
    let band: String?
    let otherwise: String?
}

struct SequenceMetricDebugField: Codable, Hashable {
    let value: Double?
    let resolved: Bool?
    let lowConfidence: Bool?
    let confidence: Double?
    let startTime: Double?
    let endTime: Double?
    let startEvent: String?
    let endEvent: String?
    let eventSource: String?
    let fallbackToVideoEnd: Bool?
    let rawValue: Double?
    let score: Double?
    let band: String?
    let direction: String?
    let thresholds: [String: Double]?
    let logic: [SequenceBandLogicStep]?
    let contactDetected: Bool?
    let receiveContactDetected: Bool?
    let stabilizationDetected: Bool?
    let usedProxyLocalWindow: Bool?
    let usedVideoEndTime: Bool?
    let passExecutionLowConfidence: Bool?
    let passReceiveGapLowConfidence: Bool?
    let receiveStabilizationLowConfidence: Bool?
}

struct SequenceQualityGate: Codable, Hashable {
    let actionName: String
    let qualityStatus: String
    let passed: Bool
    let allowMicroTechniqueScore: Bool
    let hideMicroTechniqueScore: Bool
    let shouldReshoot: Bool
    let reshootHint: String
    let thresholds: [String: Double]
    let observed: [String: Double]
    let triggeredRules: [String]
    let failReasons: [String]
}

struct PassReceiveSequenceResult: Codable, Hashable {
    let actionDisplayName: String
    let overallScore: Double
    let levelLabel: String
    let summary: String
    let passMetrics: [SequenceMetricSummary]
    let receiveMetrics: [SequenceMetricSummary]
    let sequenceMetrics: [SequenceMetricSummary]
    let feedbackMessages: [String]
    let rawActionCandidates: [SequenceActionCandidate]
    let candidateScores: [String: Double]
    let metricDebug: [String: SequenceMetricDebugField]
    let qualityGate: SequenceQualityGate
}

enum SubscriptionState: Codable, Hashable {
    case free
    case pro(ProPlan)

    var isPro: Bool {
        if case .pro = self {
            return true
        }
        return false
    }

    var title: String {
        switch self {
        case .free:
            return "基础版"
        case let .pro(plan):
            return plan.title
        }
    }

    var subtitle: String {
        switch self {
        case .free:
            return "可体验基础分析与有限次数"
        case .pro(.monthly):
            return "已解锁完整评分、历史与训练建议"
        case .pro(.yearly):
            return "已解锁完整评分、历史与训练建议"
        }
    }
}

enum ResultLevel: String, Codable, Hashable {
    case excellent
    case good
    case fair
    case needsImprove = "needs_improve"
    case needsStrengthen = "needs_strengthen"
    case pendingConfirmation = "pending_confirmation"

    static func level(for score: Double) -> ResultLevel {
        switch score {
        case 90...:
            return .excellent
        case 75..<90:
            return .good
        case 60..<75:
            return .fair
        case 40..<60:
            return .needsImprove
        default:
            return .needsStrengthen
        }
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        let raw = (try? container.decode(String.self))?.lowercased() ?? ""
        switch raw {
        case "excellent":
            self = .excellent
        case "优秀":
            self = .excellent
        case "good":
            self = .good
        case "良好":
            self = .good
        case "fair":
            self = .fair
        case "一般":
            self = .fair
        case "needs_improve", "needs_improvement", "needs_work", "watch", "待提高":
            self = .needsImprove
        case "needs_strengthen", "needs_strengthening", "needs_correction", "focus", "需加强":
            self = .needsStrengthen
        case "pending_confirmation", "needs_confirmation", "uncertain", "待确认":
            self = .pendingConfirmation
        default:
            self = .needsImprove
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(rawValue)
    }

    var title: String {
        switch self {
        case .excellent:
            return "优秀"
        case .good:
            return "良好"
        case .fair:
            return "一般"
        case .needsImprove:
            return "待提高"
        case .needsStrengthen:
            return "需加强"
        case .pendingConfirmation:
            return "待确认"
        }
    }

    var description: String {
        switch self {
        case .excellent:
            return "动作结构成熟，可进入更高强度训练"
        case .good:
            return "主要动作质量不错，仍有少量可优化点"
        case .fair:
            return "完成度可接受，但关键环节还不够稳定"
        case .needsImprove:
            return "动作已经具备基础框架，但还有明显待提高的环节"
        case .needsStrengthen:
            return "当前主要问题较明显，建议先强化基础结构再提速"
        case .pendingConfirmation:
            return "当前结果置信度不足，建议补充更清晰视频后再判断"
        }
    }
}

enum MotionStage: String, Codable, Hashable {
    case setup
    case support
    case strike
    case followThrough

    var title: String {
        switch self {
        case .setup:
            return "准备阶段"
        case .support:
            return "支撑阶段"
        case .strike:
            return "触球发力阶段"
        case .followThrough:
            return "随挥收尾阶段"
        }
    }
}

enum ThumbnailStyle: String, Codable, Hashable {
    case stadiumBlue
    case trainingGreen
    case sunsetOrange
}

struct ScoreBreakdown: Codable, Hashable {
    let overall: Int
    let technique: Int
    let control: Int
    let safety: Int
    let levelCode: String
    let levelLabel: String
    let needsConfirmation: Bool
    let confidence: Double
    let confidenceGap: Double
    let actionLabel: String
    let actionDisplayName: String
    let actionCandidates: [ActionCandidate]
    let uncertaintyReasons: [String]

    init(
        overall: Int,
        technique: Int,
        control: Int,
        safety: Int,
        levelCode: String = "",
        levelLabel: String = "",
        needsConfirmation: Bool = false,
        confidence: Double = 0.0,
        confidenceGap: Double = 0.0,
        actionLabel: String = "",
        actionDisplayName: String = "",
        actionCandidates: [ActionCandidate] = [],
        uncertaintyReasons: [String] = []
    ) {
        self.overall = overall
        self.technique = technique
        self.control = control
        self.safety = safety
        self.levelCode = levelCode
        self.levelLabel = levelLabel
        self.needsConfirmation = needsConfirmation
        self.confidence = confidence
        self.confidenceGap = confidenceGap
        self.actionLabel = actionLabel
        self.actionDisplayName = actionDisplayName
        self.actionCandidates = actionCandidates
        self.uncertaintyReasons = uncertaintyReasons
    }

    var level: ResultLevel {
        let normalizedLevelCode = levelCode.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        if needsConfirmation || normalizedLevelCode == "pending_confirmation" || normalizedLevelCode == "needs_confirmation" || normalizedLevelCode == "uncertain" {
            return .pendingConfirmation
        }

        switch normalizedLevelCode {
        case "excellent":
            return .excellent
        case "优秀":
            return .excellent
        case "good":
            return .good
        case "良好":
            return .good
        case "fair":
            return .fair
        case "一般":
            return .fair
        case "needs_improve", "needs_work", "watch", "待提高":
            return .needsImprove
        case "needs_improvement", "needs_strengthen", "needs_strengthening", "needs_correction", "focus", "需加强":
            return Double(overall) < 40.0 ? .needsStrengthen : .needsImprove
        case "待确认":
            return .pendingConfirmation
        default:
            return ResultLevel.level(for: Double(overall))
        }
    }

    enum CodingKeys: String, CodingKey {
        case overall
        case technique = "technical_execution"
        case control = "control_stability"
        case safety = "action_safety"
        case levelCode = "level_code"
        case levelLabel = "level_label"
        case needsConfirmation = "needs_confirmation"
        case confidence
        case confidenceGap = "confidence_gap"
        case actionLabel = "action_label"
        case actionDisplayName = "action_display_name"
        case actionCandidates = "action_candidates"
        case uncertaintyReasons = "uncertainty_reasons"
    }
}

struct AnalysisIssue: Identifiable, Codable, Hashable {
    let id: UUID
    let stage: MotionStage
    let title: String
    let detail: String
    let impact: String
    let time: String?
}

struct DrillRecommendation: Identifiable, Codable, Hashable {
    let id: UUID
    let name: String
    let dosage: String
    let cue: String
}

struct TrainingSuggestion: Identifiable, Codable, Hashable {
    let id: UUID
    let title: String
    let summary: String
    let drill: DrillRecommendation
    let proOnly: Bool
}

struct PremiumInsight: Identifiable, Codable, Hashable {
    let id: UUID
    let title: String
    let detail: String
}

struct AnalysisRecord: Identifiable, Codable, Hashable {
    let id: UUID
    let createdAt: Date
    let athleteLabel: String
    let clipName: String
    let durationSeconds: Double
    let goal: TrainingGoal
    let score: ScoreBreakdown
    let reportState: ResultReportState
    let qualityStatus: VideoQualityStatus
    let summary: String
    let positiveNote: String
    let targetZone: String
    let contactDescription: String
    let releaseDescription: String
    let thumbnailStyle: ThumbnailStyle
    let analysisMetrics: [AnalysisMetric]
    let triggeredRules: [RuleTriggerSummary]
    let failReasons: [String]
    let feedbackMessages: [String]
    let issues: [AnalysisIssue]
    let observations: [ResultObservation]
    let errorTimestamps: [ResultTimestamp]
    let suggestions: [TrainingSuggestion]
    let premiumInsights: [PremiumInsight]
    let sequenceResult: PassReceiveSequenceResult?
    let runtimeState: AnalysisRuntimeState

    init(
        id: UUID,
        createdAt: Date,
        athleteLabel: String,
        clipName: String,
        durationSeconds: Double,
        goal: TrainingGoal,
        score: ScoreBreakdown,
        reportState: ResultReportState = .readyToScore,
        qualityStatus: VideoQualityStatus = .good,
        summary: String,
        positiveNote: String,
        targetZone: String,
        contactDescription: String,
        releaseDescription: String,
        thumbnailStyle: ThumbnailStyle,
        analysisMetrics: [AnalysisMetric] = [],
        triggeredRules: [RuleTriggerSummary] = [],
        failReasons: [String] = [],
        feedbackMessages: [String] = [],
        issues: [AnalysisIssue],
        observations: [ResultObservation] = [],
        errorTimestamps: [ResultTimestamp] = [],
        suggestions: [TrainingSuggestion],
        premiumInsights: [PremiumInsight],
        sequenceResult: PassReceiveSequenceResult? = nil,
        runtimeState: AnalysisRuntimeState = AnalysisRuntimeState()
    ) {
        self.id = id
        self.createdAt = createdAt
        self.athleteLabel = athleteLabel
        self.clipName = clipName
        self.durationSeconds = durationSeconds
        self.goal = goal
        self.score = score
        self.reportState = reportState
        self.qualityStatus = qualityStatus
        self.summary = summary
        self.positiveNote = positiveNote
        self.targetZone = targetZone
        self.contactDescription = contactDescription
        self.releaseDescription = releaseDescription
        self.thumbnailStyle = thumbnailStyle
        self.analysisMetrics = analysisMetrics
        self.triggeredRules = triggeredRules
        self.failReasons = failReasons
        self.feedbackMessages = feedbackMessages
        self.issues = issues
        self.observations = observations
        self.errorTimestamps = errorTimestamps
        self.suggestions = suggestions
        self.premiumInsights = premiumInsights
        self.sequenceResult = sequenceResult
        self.runtimeState = runtimeState
    }

    var shouldShowFormalScore: Bool {
        runtimeState.analysisStatus != .failed && runtimeState.integrityState != .anomaly && reportState == .readyToScore && !score.needsConfirmation
    }

    var gradeTitle: String {
        if isAnalysisFailure {
            return failureReason?.title ?? analysisStatus.title
        }

        if isAnalysisAnomaly {
            return runtimeState.integrityState.title
        }

        if isAnalysisPartial, runtimeState.longVideoLocalized {
            return "自动定位"
        }

        if isAnalysisPartial, runtimeState.fastModeEnabled {
            return "快速分析"
        }

        if !shouldShowFormalScore {
            return reportState.title
        }
        if let sequenceResult {
            return sequenceResult.levelLabel
        }
        return score.level.title
    }

    var scoreSubtitle: String {
        if isAnalysisFailure || isAnalysisAnomaly {
            return failureMessageText
        }

        if runtimeState.longVideoLocalized {
            return "已自动定位动作片段进行分析。"
        }

        if isAnalysisPartial, runtimeState.fastModeEnabled {
            return "当前使用快速模式抽帧，结果偏保守。"
        }

        return shouldShowFormalScore ? score.level.description : reportState.subtitle
    }

    var displaySummary: String {
        if isAnalysisFailure || isAnalysisAnomaly {
            return failureMessageText
        }

        if isAnalysisPartial, let routeMessage = routeMismatchMessage, !routeMessage.isEmpty {
            return routeMessage
        }

        if shouldShowFormalScore {
            return summary
        }

        if reportState == .needsConfirmation {
            return summary
        }

        return reportState.subtitle
    }

    var problemSectionTitle: String {
        if isAnalysisFailure || isAnalysisAnomaly {
            return "异常说明"
        }

        switch reportState {
        case .readyToScore:
            return score.overall >= 85 ? "当前可优化点" : "核心问题"
        case .insufficientEvidence:
            return "当前检测到的观察结果"
        case .qualityFail:
            return "视频质量问题"
        case .needsConfirmation:
            return "待确认原因"
        }
    }

    var reportTagText: String {
        if isAnalysisFailure {
            return failureReason?.title ?? analysisStatus.title
        }

        if isAnalysisAnomaly {
            return runtimeState.integrityState.title
        }

        if isAnalysisPartial, runtimeState.longVideoLocalized {
            return "自动定位"
        }

        if isAnalysisPartial, runtimeState.fastModeEnabled {
            return "快速分析"
        }

        return shouldShowFormalScore ? score.level.title : reportState.title
    }

    var displayActionDisplayName: String {
        let selectedName = displayActionName(for: runtimeState.selectedAction)
        if !selectedName.isEmpty {
            return selectedName
        }

        let suggestionName = displayActionName(for: runtimeState.systemActionSuggestion)
        if !suggestionName.isEmpty {
            return suggestionName
        }

        let directName = score.actionDisplayName.trimmingCharacters(in: .whitespacesAndNewlines)
        if !directName.isEmpty {
            return directName
        }

        if let sequenceResult {
            let sequenceName = sequenceResult.actionDisplayName.trimmingCharacters(in: .whitespacesAndNewlines)
            if !sequenceName.isEmpty {
                return sequenceName
            }
        }

        return goal.displayTitle
    }

    var analysisStatus: AnalysisStatus {
        runtimeState.analysisStatus
    }

    var failureReason: AnalysisFailureReason? {
        runtimeState.failureReason
    }

    var failureMessageText: String {
        if let failureMessage = runtimeState.failureMessage?.trimmingCharacters(in: .whitespacesAndNewlines), !failureMessage.isEmpty {
            return failureMessage
        }

        if let routeMessage = runtimeState.routeMismatchMessage?.trimmingCharacters(in: .whitespacesAndNewlines), !routeMessage.isEmpty {
            return routeMessage
        }

        return runtimeState.failureReason?.message(durationSeconds: runtimeState.videoDurationSeconds) ?? ""
    }

    var routeMismatchMessage: String? {
        let text = runtimeState.routeMismatchMessage?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return text.isEmpty ? nil : text
    }

    var debugContext: AnalysisDebugContext? {
        runtimeState.debugContext
    }

    var analysisRoutedBy: String {
        runtimeState.analysisRoutedBy
    }

    var routedAnalyzer: String {
        runtimeState.routedAnalyzer
    }

    var selectedActionName: String {
        runtimeState.selectedAction
    }

    var systemActionSuggestionName: String {
        runtimeState.systemActionSuggestion
    }

    var isAnalysisFailure: Bool {
        runtimeState.analysisStatus == .failed
    }

    var isAnalysisPartial: Bool {
        runtimeState.analysisStatus == .partial
    }

    var isAnalysisAnomaly: Bool {
        runtimeState.integrityState == .anomaly
    }

    var hasRouteMismatchWarning: Bool {
        runtimeState.integrityState == .routeMismatch
    }

    var routeDebugText: String {
        var parts: [String] = []
        if !selectedActionName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            parts.append("selected_action=\(selectedActionName)")
        }
        if !systemActionSuggestionName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            parts.append("system_action_suggestion=\(systemActionSuggestionName)")
        }
        if !analysisRoutedBy.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            parts.append("analysis_routed_by=\(analysisRoutedBy)")
        }
        if !routedAnalyzer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            parts.append("routed_analyzer=\(routedAnalyzer)")
        }
        if let routeMismatchMessage, !routeMismatchMessage.isEmpty {
            parts.append("route_mismatch_message=\(routeMismatchMessage)")
        }
        if runtimeState.longVideoLocalized {
            parts.append("long_video_localized=true")
        }
        if runtimeState.candidateWindowCount > 0 {
            parts.append("candidate_window_count=\(runtimeState.candidateWindowCount)")
        }
        if let start = runtimeState.selectedWindowStartSeconds, let end = runtimeState.selectedWindowEndSeconds {
            parts.append(String(format: "selected_window_range=%.1fs-%.1fs", start, end))
        }
        return parts.joined(separator: " | ")
    }

    var failureReasonText: String {
        if let failureReason {
            return failureReason.title
        }
        if isAnalysisAnomaly {
            return runtimeState.integrityState.title
        }
        return analysisStatus.title
    }

    var analysisWindowText: String? {
        guard runtimeState.longVideoLocalized,
              let start = runtimeState.selectedWindowStartSeconds,
              let end = runtimeState.selectedWindowEndSeconds,
              let duration = runtimeState.selectedWindowDurationSeconds else {
            return nil
        }

        return String(format: "已自动定位动作片段 · 分析片段：%.1fs - %.1fs · 时长：%.1fs", start, end, duration)
    }

    var hasSequenceResult: Bool {
        sequenceResult != nil
    }

    private func displayActionName(for rawValue: String) -> String {
        let normalized = rawValue.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        switch normalized {
        case "pass":
            return "传球"
        case "shot":
            return "射门"
        case "pass_receive_sequence":
            return "传接球"
        case "receive", "receive_control", "first_touch":
            return "停球"
        case "":
            return ""
        default:
            return rawValue
        }
    }
}

struct UploadDraft: Identifiable, Hashable {
    let id = UUID()
    let clipName: String
    let durationSeconds: Double
    let goal: TrainingGoal
    let sourceLabel: String
    let demoClip: DemoClip
}

struct DemoClip: Identifiable, Hashable {
    let id = UUID()
    let title: String
    let subtitle: String
    let fileName: String
    let durationSeconds: Double
    let athleteLabel: String
    let style: ThumbnailStyle
}

struct OnboardingStep: Identifiable, Hashable {
    let id = UUID()
    let title: String
    let subtitle: String
    let detail: String
    let symbol: String
}

struct PaywallFeature: Identifiable, Hashable {
    let id = UUID()
    let icon: String
    let title: String
    let detail: String
}
