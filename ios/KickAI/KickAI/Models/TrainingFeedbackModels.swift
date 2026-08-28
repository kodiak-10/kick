import Foundation

enum TrainingFeedbackStatus: Int, Hashable, Codable, Comparable {
    case excellent = 3
    case good = 2
    case needsWork = 1
    case reference = 0

    static func < (lhs: TrainingFeedbackStatus, rhs: TrainingFeedbackStatus) -> Bool {
        lhs.rawValue < rhs.rawValue
    }

    var displayLabel: String {
        switch self {
        case .excellent:
            return "优秀"
        case .good:
            return "良好"
        case .needsWork:
            return "需加强"
        case .reference:
            return "低置信"
        }
    }

    var isPositive: Bool {
        self == .excellent || self == .good
    }

    var isAttention: Bool {
        !isPositive
    }

    /// Lower values are more urgent.
    var attentionRank: Int {
        switch self {
        case .needsWork:
            return 0
        case .reference:
            return 1
        case .good:
            return 2
        case .excellent:
            return 3
        }
    }
}

struct TrainingFeedbackSummaryTag: Hashable {
    let title: String
    let status: TrainingFeedbackStatus

    var id: String { title }
}

struct TrainingFeedbackMetricItem: Hashable {
    let key: ResultMetricKey
    let title: String
    let valueText: String
    let status: TrainingFeedbackStatus
    let explanation: String
    let numericValue: Double?
    let urgencyScore: Double

    var id: String { key.rawValue }
}

enum TrainingFeedbackTimelineMarkerKind: Hashable {
    case receive
    case strike
    case returnTouch
    case stable
    case problem
    case pending

    var displayLabel: String {
        switch self {
        case .receive:
            return "接球"
        case .strike:
            return "出脚"
        case .returnTouch:
            return "接触回传"
        case .stable:
            return "稳定状态"
        case .problem:
            return "问题点"
        case .pending:
            return "低置信点"
        }
    }

    var symbolName: String {
        switch self {
        case .receive:
            return "circle.fill"
        case .strike:
            return "bolt.fill"
        case .returnTouch:
            return "arrow.uturn.right"
        case .stable:
            return "checkmark.circle.fill"
        case .problem:
            return "exclamationmark.triangle.fill"
        case .pending:
            return "questionmark.circle.fill"
        }
    }
}

enum TrainingFeedbackKeyframeMoment: Hashable {
    case preReceive
    case strike
    case stable

    var displayTitle: String {
        switch self {
        case .preReceive:
            return "接球前"
        case .strike:
            return "出脚瞬间"
        case .stable:
            return "接球稳定瞬间"
        }
    }
}

enum TrainingFeedbackKeyframeConfidence: Hashable {
    case high
    case medium
    case low

    var displayLabel: String {
        switch self {
        case .high:
            return "高置信"
        case .medium:
            return "辅助参考"
        case .low:
            return "低置信帧"
        }
    }

    var note: String {
        switch self {
        case .high:
            return "当前关注区域可以作为动作趋势参考。"
        case .medium:
            return "当前点位仅作辅助参考，不建议做精确位置判断。"
        case .low:
            return "本帧更适合参考整体节奏，不建议做精确位置判断。"
        }
    }

    var allowsRegionHighlights: Bool {
        self == .high
    }

    var needsCautionBanner: Bool {
        self != .high
    }
}

enum TrainingFeedbackFrameAnnotationKind: Hashable {
    case ball
    case supportFoot
    case touchFoot
    case bodyDirection
    case ballDirection

    var displayLabel: String {
        switch self {
        case .ball:
            return "球"
        case .supportFoot:
            return "支撑脚"
        case .touchFoot:
            return "触球脚"
        case .bodyDirection:
            return "身体朝向"
        case .ballDirection:
            return "球方向"
        }
    }

    var visualLabel: String {
        switch self {
        case .ball:
            return "球"
        case .supportFoot:
            return "支撑脚"
        case .touchFoot:
            return "触球脚"
        case .bodyDirection:
            return "身体朝向"
        case .ballDirection:
            return "球路方向"
        }
    }

    var isArrow: Bool {
        self == .bodyDirection || self == .ballDirection
    }
}

struct TrainingFeedbackFrameAnnotation: Hashable {
    let id: String
    let kind: TrainingFeedbackFrameAnnotationKind
    let x: Double
    let y: Double
    let angle: Double
    let radius: Double
    let note: String
}

struct TrainingFeedbackTimelineMarker: Hashable, Identifiable {
    let id: String
    let title: String
    let detail: String
    let time: Double
    let kind: TrainingFeedbackTimelineMarkerKind
    let status: TrainingFeedbackStatus
    let isPriority: Bool

    var timeLabel: String {
        String(format: "%.1fs", time)
    }
}

struct TrainingFeedbackKeyframeSpec: Hashable, Identifiable {
    let id: String
    let moment: TrainingFeedbackKeyframeMoment
    let time: Double
    let title: String
    let conclusion: String
    let mainPoint: String
    let whyImportant: String
    let howToChange: String
    let status: TrainingFeedbackStatus
    let confidence: TrainingFeedbackKeyframeConfidence
    let confidenceNote: String
    let focusAnnotationKinds: [TrainingFeedbackFrameAnnotationKind]
    let isPrimary: Bool
    let annotations: [TrainingFeedbackFrameAnnotation]

    var visibleAnnotations: [TrainingFeedbackFrameAnnotation] {
        guard confidence.allowsRegionHighlights else {
            return []
        }

        return focusAnnotationKinds.compactMap { focusKind in
            annotations.first(where: { $0.kind == focusKind })
        }
    }

    var primaryVisibleAnnotation: TrainingFeedbackFrameAnnotation? {
        visibleAnnotations.first
    }
}

struct TrainingFeedbackProblemCard: Hashable {
    let metricKey: ResultMetricKey
    let topic: String
    let issue: String
    let whyImportant: String
    let fix: String
    let practice: String
    let status: TrainingFeedbackStatus
    let time: Double
    let markerKind: TrainingFeedbackTimelineMarkerKind

    var id: String {
        "\(metricKey.rawValue)-\(topic)-\(issue)-\(fix)-\(practice)"
    }

    var timeLabel: String {
        String(format: "%.1fs", time)
    }
}

struct TrainingFeedbackPendingCard: Hashable {
    let metricKey: ResultMetricKey
    let topic: String
    let reason: String
    let captureAdvice: String
    let note: String
    let status: TrainingFeedbackStatus
    let time: Double
    let markerKind: TrainingFeedbackTimelineMarkerKind

    var id: String {
        "\(metricKey.rawValue)-\(topic)-\(reason)-\(captureAdvice)-\(note)"
    }

    var timeLabel: String {
        String(format: "%.1fs", time)
    }
}

struct TrainingFeedbackPriorityFocus: Hashable {
    let metricKey: ResultMetricKey
    let keyframeMoment: TrainingFeedbackKeyframeMoment
    let title: String
    let reason: String
    let nextStep: String
    let status: TrainingFeedbackStatus
    let time: Double
    let markerKind: TrainingFeedbackTimelineMarkerKind
}

struct TrainingFeedbackConfidenceReview: Hashable {
    let summary: String
    let trustedPoints: [String]
    let uncertainPoints: [String]
    let shootingAdvice: [String]
}

struct TrainingFeedbackVideoEvidence: Hashable {
    let duration: Double
    let durationText: String
    let markers: [TrainingFeedbackTimelineMarker]
    let keyframes: [TrainingFeedbackKeyframeSpec]
    let primaryKeyframeID: String
}

struct TrainingFeedbackDebugSnapshot: Hashable {
    let matchedKey: [String]
    let weight: [String]
    let sourceClass: [String]
    let metricDebug: [String]
    let candidateScores: [String]
    let rawActionCandidates: [String]
}

struct TrainingFeedbackResultIntegrityState: Hashable {
    let shouldBlockDisplay: Bool
    let summary: String
    let reasons: [String]
    let safeActionDisplayName: String
    let safeLevelLabelText: String

    static let clean = TrainingFeedbackResultIntegrityState(
        shouldBlockDisplay: false,
        summary: "",
        reasons: [],
        safeActionDisplayName: "",
        safeLevelLabelText: ""
    )
}

struct TrainingFeedbackViewModel: Hashable {
    let actionName: String
    let selectedAction: AnalysisActionChoice?
    let selectedActionValue: String?
    let analysisRoutedBy: String?
    let routedAnalyzer: String?
    let systemActionSuggestion: String?
    let routeMismatchMessage: String?
    let scoreText: String
    let scoreValue: Int?
    let gradeText: String
    let headline: String
    let summaryTags: [TrainingFeedbackSummaryTag]
    let goodObservations: [String]
    let attentionObservations: [String]
    let trainingSuggestions: [String]
    let problemCards: [TrainingFeedbackProblemCard]
    let pendingCards: [TrainingFeedbackPendingCard]
    let priorityFocus: TrainingFeedbackPriorityFocus
    let metrics: [TrainingFeedbackMetricItem]
    let confidenceReview: TrainingFeedbackConfidenceReview
    let videoEvidence: TrainingFeedbackVideoEvidence
    let debug: TrainingFeedbackDebugSnapshot
    let integrityState: TrainingFeedbackResultIntegrityState
    let matchAnalysis: VideoAnalysisResponse.MatchAnalysisSnapshot?

    var isResultAnomalous: Bool {
        integrityState.shouldBlockDisplay
    }

    var integritySummary: String {
        integrityState.summary
    }

    var integrityReasons: [String] {
        integrityState.reasons
    }

    var routeDebugText: String {
        [
            "selected_action: \(selectedActionValue?.nonEmpty ?? "nil")",
            "analysis_routed_by: \(analysisRoutedBy?.nonEmpty ?? "nil")",
            "routed_analyzer: \(routedAnalyzer?.nonEmpty ?? "nil")"
        ]
        .joined(separator: "\n")
    }

    init(report: ResultReport, videoDuration: Double? = nil) {
        let metricItems = Self.makeMetricItems(from: report.metrics)
        let scoreValue = report.totalScore
        let integrityState = Self.integrityState(for: report)
        let debug = TrainingFeedbackDebugSnapshot(
            matchedKey: report.debug.matchedKey,
            weight: report.debug.weight,
            sourceClass: report.debug.sourceClass,
            metricDebug: report.debug.metricDebug,
            candidateScores: report.debug.candidateScores,
            rawActionCandidates: report.debug.rawActionCandidates
        )

        self.init(
            actionName: report.actionName,
            selectedAction: nil,
            selectedActionValue: nil,
            analysisRoutedBy: nil,
            routedAnalyzer: nil,
            systemActionSuggestion: nil,
            routeMismatchMessage: nil,
            scoreText: "\(report.totalScore)",
            scoreValue: scoreValue,
            gradeText: report.grade,
            trainingSuggestions: integrityState.shouldBlockDisplay
                ? [integrityState.summary]
                : report.trainingSuggestions,
            metricItems: metricItems,
            videoDuration: videoDuration,
            debug: debug,
            integrityState: integrityState,
            matchAnalysis: nil
        )
    }

    init(
        response: VideoAnalysisResponse,
        selectedAction: AnalysisActionChoice? = nil,
        videoDuration: Double? = nil
    ) {
        let metricItems = Self.makeMetricItems(from: response)
        let scoreValue = response.overallScoreValue
        let integrityState = response.resolvedIntegrityState(selectedAction: selectedAction)
        let routeMismatchMessage = response.routeMismatchMessage(selectedAction: selectedAction)
        let debug = TrainingFeedbackDebugSnapshot(
            matchedKey: response.debug.matchedKey,
            weight: response.debug.weight,
            sourceClass: response.debug.sourceClass,
            metricDebug: response.debug.metricDebug,
            candidateScores: response.debug.candidateScores,
            rawActionCandidates: response.debug.rawActionCandidates
        )
        let resolvedActionName = selectedAction?.displayTitle
            ?? integrityState.safeActionDisplayName.nonEmpty
            ?? response.backendActionDisplayNameText
        let actionHint = response.actionSuggestionText(selectedAction: selectedAction)

        self.init(
            actionName: resolvedActionName,
            selectedAction: selectedAction,
            selectedActionValue: response.selectedActionValue,
            analysisRoutedBy: response.analysisRoutedBy,
            routedAnalyzer: response.routedAnalyzer,
            systemActionSuggestion: actionHint,
            routeMismatchMessage: routeMismatchMessage,
            scoreText: response.overallScoreText,
            scoreValue: scoreValue,
            gradeText: integrityState.safeLevelLabelText.nonEmpty ?? response.backendLevelLabelText,
            trainingSuggestions: integrityState.shouldBlockDisplay
                ? [integrityState.summary]
                : response.trainingSuggestions,
            metricItems: metricItems,
            videoDuration: videoDuration,
            debug: debug,
            integrityState: integrityState,
            matchAnalysis: response.matchAnalysis
        )
    }

    private init(
        actionName: String,
        selectedAction: AnalysisActionChoice?,
        selectedActionValue: String?,
        analysisRoutedBy: String?,
        routedAnalyzer: String?,
        systemActionSuggestion: String?,
        routeMismatchMessage: String?,
        scoreText: String,
        scoreValue: Int?,
        gradeText: String,
        trainingSuggestions: [String],
        metricItems: [TrainingFeedbackMetricItem],
        videoDuration: Double?,
        debug: TrainingFeedbackDebugSnapshot,
        integrityState: TrainingFeedbackResultIntegrityState,
        matchAnalysis: VideoAnalysisResponse.MatchAnalysisSnapshot?
    ) {
        self.actionName = actionName.nonEmpty ?? "未命名动作"
        self.selectedAction = selectedAction
        self.selectedActionValue = selectedActionValue
        self.analysisRoutedBy = analysisRoutedBy
        self.routedAnalyzer = routedAnalyzer
        self.systemActionSuggestion = systemActionSuggestion
        self.routeMismatchMessage = routeMismatchMessage
        self.scoreText = scoreText.nonEmpty ?? "—"
        self.scoreValue = scoreValue
        self.gradeText = gradeText.nonEmpty ?? "未评分"
        self.trainingSuggestions = trainingSuggestions
        self.debug = debug
        self.matchAnalysis = matchAnalysis

        let feedbackDomains = FeedbackDomain.domains(
            for: selectedAction,
            actionName: self.actionName
        )
        let domainMetricKeys = Self.orderedMetricKeys(for: feedbackDomains)
        self.metrics = metricItems.filter { domainMetricKeys.contains($0.key) }

        let metricLookup = Dictionary(uniqueKeysWithValues: self.metrics.map { ($0.key, $0) })

        let tags = feedbackDomains.map { domain in
            TrainingFeedbackSummaryTag(
                title: domain.summaryTitle,
                status: Self.domainStatus(for: domain, metricLookup: metricLookup)
            )
        }
        summaryTags = tags

        let sortedProblemCards = Self.buildProblemCards(
            domains: feedbackDomains,
            metricLookup: metricLookup,
            trainingSuggestions: trainingSuggestions
        )
        problemCards = sortedProblemCards

        let sortedPendingCards = Self.buildPendingCards(
            domains: feedbackDomains,
            metricLookup: metricLookup
        )
        pendingCards = sortedPendingCards

        priorityFocus = Self.buildPriorityFocus(
            domains: feedbackDomains,
            problemCards: sortedProblemCards,
            pendingCards: sortedPendingCards,
            metricLookup: metricLookup,
            trainingSuggestions: trainingSuggestions
        )

        let goodCandidates = Self.buildGoodObservationCandidates(
            summaryTags: tags,
            problemCards: sortedProblemCards,
            pendingCards: sortedPendingCards
        )
        let attentionCandidates = Self.buildAttentionObservationCandidates(
            summaryTags: tags,
            problemCards: sortedProblemCards,
            pendingCards: sortedPendingCards
        )
        let selectedObservations = Self.selectObservations(
            goodCandidates: goodCandidates,
            attentionCandidates: attentionCandidates
        )
        goodObservations = selectedObservations.good
        attentionObservations = selectedObservations.attention

        let resolvedDuration = Self.resolveVideoDuration(videoDuration)
        videoEvidence = Self.buildVideoEvidence(
            duration: resolvedDuration,
            metricLookup: metricLookup,
            problemCards: sortedProblemCards,
            pendingCards: sortedPendingCards,
            priorityFocus: priorityFocus
        )
        confidenceReview = Self.buildConfidenceReview(
            summaryTags: tags,
            problemCards: sortedProblemCards,
            pendingCards: sortedPendingCards,
            priorityFocus: priorityFocus
        )
        self.integrityState = integrityState

        if let routeMismatchMessage {
            headline = routeMismatchMessage
        } else if integrityState.shouldBlockDisplay {
            headline = integrityState.summary
        } else {
            headline = Self.buildHeadline(
                actionName: self.actionName,
                scoreValue: scoreValue,
                summaryTags: tags,
                problemCards: sortedProblemCards,
                pendingCards: sortedPendingCards,
                priorityFocus: priorityFocus
            )
        }
    }

    private static func makeMetricItems(from metrics: [ResultMetric]) -> [TrainingFeedbackMetricItem] {
        let lookup = Dictionary(uniqueKeysWithValues: metrics.map { ($0.key, $0) })
        return orderedMetricKeys.compactMap { key in
            guard let metric = lookup[key] else { return nil }
            let valueText = metric.currentValue.nonEmpty ?? "—"
            let status = status(forBand: metric.band, confidence: metric.confidence)
            let numericValue = numericValue(from: valueText)
            return TrainingFeedbackMetricItem(
                key: key,
                title: friendlyTitle(for: key),
                valueText: valueText,
                status: status,
                explanation: metricExplanation(for: key, status: status),
                numericValue: numericValue,
                urgencyScore: urgencyScore(for: key, status: status, numericValue: numericValue)
            )
        }
    }

    private static func makeMetricItems(from response: VideoAnalysisResponse) -> [TrainingFeedbackMetricItem] {
        orderedMetricKeys.compactMap { key in
            guard let snapshot = response.metricSnapshot(for: key) else { return nil }
            let status = status(forBand: snapshot.band, confidence: snapshot.confidence)
            let valueText = snapshot.value.nonEmpty ?? "—"
            let numericValue = numericValue(from: valueText)
            return TrainingFeedbackMetricItem(
                key: key,
                title: friendlyTitle(for: key),
                valueText: valueText,
                status: status,
                explanation: metricExplanation(for: key, status: status),
                numericValue: numericValue,
                urgencyScore: urgencyScore(for: key, status: status, numericValue: numericValue)
            )
        }
    }

    private static func integrityState(for report: ResultReport) -> TrainingFeedbackResultIntegrityState {
        let normalizedSummary = report.summary.trimmingCharacters(in: .whitespacesAndNewlines)
        let hasAnomalySignal = normalizedSummary.localizedCaseInsensitiveContains("异常") ||
            report.summaryTag.localizedCaseInsensitiveContains("异常") ||
            report.improvementFindings.contains(where: { $0.title.localizedCaseInsensitiveContains("异常") })

        if hasAnomalySignal {
            return TrainingFeedbackResultIntegrityState(
                shouldBlockDisplay: true,
                summary: "本次结果存在异常，请重新分析",
                reasons: ["历史结果已标记为异常，已避免展示错误组合。"],
                safeActionDisplayName: report.actionName,
                safeLevelLabelText: "异常"
            )
        }

        return .clean
    }

    private static func friendlyTitle(for key: ResultMetricKey) -> String {
        switch key {
        case .passEndpointErrorM:
            return "传球精度"
        case .passExecutionTimeS:
            return "出脚节奏"
        case .receiveControlZoneSuccessRate:
            return "接球控制"
        case .receiveStabilizationTimeS:
            return "接球稳定速度"
        case .receiveCorrectiveTouchCount:
            return "补救触球数"
        case .passReceiveGapS:
            return "传接间隔"
        case .sequenceContinuityScore:
            return "衔接流畅度"
        case .nextActionReadiness:
            return "下一动作准备度"
        case .shotTargetZoneHit:
            return "射门目标区"
        case .shotMaxBallSpeedMPS:
            return "出球速度"
        case .shotMaxBallSpeedProxyMPS:
            return "出球速度趋势"
        case .shotConsistencyCVPercent:
            return "射门稳定性"
        case .supportFootLateralOffsetCM:
            return "支撑脚位置"
        case .supportFootAPOffsetCM:
            return "支撑脚前后距离"
        case .trunkLeanDegAtImpactProxy:
            return "触球身体角度"
        }
    }

    private static let orderedMetricKeys: [ResultMetricKey] = [
        .passEndpointErrorM,
        .passExecutionTimeS,
        .receiveControlZoneSuccessRate,
        .receiveStabilizationTimeS,
        .receiveCorrectiveTouchCount,
        .passReceiveGapS,
        .sequenceContinuityScore,
        .nextActionReadiness,
        .shotTargetZoneHit,
        .shotMaxBallSpeedMPS,
        .shotMaxBallSpeedProxyMPS,
        .shotConsistencyCVPercent,
        .supportFootLateralOffsetCM,
        .supportFootAPOffsetCM,
        .trunkLeanDegAtImpactProxy
    ]

    private static func orderedMetricKeys(for domains: [FeedbackDomain]) -> [ResultMetricKey] {
        var seen = Set<ResultMetricKey>()
        return domains.flatMap(\.metricKeys).filter { key in
            if seen.contains(key) {
                return false
            }
            seen.insert(key)
            return true
        }
    }

    private static func status(forBand band: String?, confidence: ResultConfidenceLevel) -> TrainingFeedbackStatus {
        if confidence == .low {
            return .reference
        }

        let normalized = band?
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()

        guard let normalized, !normalized.isEmpty else {
            return .good
        }

        if containsAny(normalized, tokens: excellentTokens) {
            return .excellent
        }

        if containsAny(normalized, tokens: needsWorkTokens) {
            return .needsWork
        }

        if containsAny(normalized, tokens: goodTokens) {
            return .good
        }

        return .good
    }

    private static func containsAny(_ text: String, tokens: [String]) -> Bool {
        tokens.contains { text.contains($0) }
    }

    private static func numericValue(from text: String) -> Double? {
        var token = ""
        var hasDigit = false

        for character in text {
            if character.isNumber || character == "." || (character == "-" && token.isEmpty) {
                token.append(character)
                if character.isNumber {
                    hasDigit = true
                }
            } else if hasDigit {
                break
            } else {
                token = ""
            }
        }

        guard hasDigit else { return nil }
        return Double(token)
    }

    private static func urgencyScore(
        for key: ResultMetricKey,
        status: TrainingFeedbackStatus,
        numericValue: Double?
    ) -> Double {
        let base: Double
        switch status {
        case .needsWork:
            base = 80
        case .reference:
            base = 55
        case .good:
            base = 18
        case .excellent:
            base = 4
        }

        return base + metricSeverity(for: key, numericValue: numericValue) * 20
    }

    private static func metricSeverity(for key: ResultMetricKey, numericValue: Double?) -> Double {
        guard let value = numericValue, value.isFinite else {
            return 0
        }

        func clamped(_ value: Double) -> Double {
            min(1, max(0, value))
        }

        func normalizedRatio(_ value: Double) -> Double {
            value > 1 ? value / 100 : value
        }

        switch key {
        case .passEndpointErrorM:
            return clamped(value / 1.2)
        case .passExecutionTimeS:
            return clamped(value / 3.4)
        case .receiveControlZoneSuccessRate:
            return clamped(1 - normalizedRatio(value))
        case .receiveStabilizationTimeS:
            return clamped(value / 2.0)
        case .receiveCorrectiveTouchCount:
            return clamped(value / 4.0)
        case .passReceiveGapS:
            return clamped(value / 1.6)
        case .sequenceContinuityScore, .nextActionReadiness:
            return clamped(1 - normalizedRatio(value))
        case .shotTargetZoneHit:
            return clamped((3.0 - value) / 3.0)
        case .shotMaxBallSpeedMPS:
            return clamped((20.0 - value) / 20.0)
        case .shotMaxBallSpeedProxyMPS:
            return clamped((12.0 - value) / 12.0)
        case .shotConsistencyCVPercent:
            return clamped(value / 55.0)
        case .supportFootLateralOffsetCM, .supportFootAPOffsetCM:
            return clamped(abs(value) / 45.0)
        case .trunkLeanDegAtImpactProxy:
            return clamped(abs(value) / 35.0)
        }
    }

    private static let excellentTokens = [
        "excellent",
        "优秀",
        "理想",
        "顺畅",
        "可执行"
    ]

    private static let goodTokens = [
        "good",
        "良好",
        "稳定",
        "流畅",
        "正常",
        "可控",
        "快速",
        "可接受",
        "平稳",
        "基础",
        "合格"
    ]

    private static let needsWorkTokens = [
        "needs_work",
        "poor",
        "需提升",
        "需加强",
        "需修正",
        "偏高",
        "偏慢",
        "偏大",
        "偏多",
        "观察中",
        "低置信",
        "待优化",
        "review"
    ]

    private static func domainStatus(
        for domain: FeedbackDomain,
        metricLookup: [ResultMetricKey: TrainingFeedbackMetricItem]
    ) -> TrainingFeedbackStatus {
        let statuses = domain.metricKeys.compactMap { metricLookup[$0]?.status }

        guard !statuses.isEmpty else {
            return .reference
        }

        if statuses.contains(.needsWork) {
            return .needsWork
        }

        if statuses.contains(.reference) {
            return .reference
        }

        if statuses.allSatisfy({ $0 == .excellent }) {
            return .excellent
        }

        return .good
    }

    private static func buildGoodObservationCandidates(
        summaryTags: [TrainingFeedbackSummaryTag],
        problemCards: [TrainingFeedbackProblemCard],
        pendingCards: [TrainingFeedbackPendingCard]
    ) -> [String] {
        let positiveTags = summaryTags
            .filter { $0.status.isPositive }
            .sorted { lhs, rhs in
                if lhs.status == rhs.status {
                    return lhs.title < rhs.title
                }
                return lhs.status > rhs.status
            }

        var candidates = positiveTags.map { tag in
            observationText(for: tag.title, status: tag.status)
        }

        if candidates.isEmpty, let fallback = summaryTags.max(by: { $0.status.attentionRank < $1.status.attentionRank }) {
            candidates = [fallbackGoodFallbackText(for: fallback)]
        }

        if candidates.isEmpty, let fallback = problemCards.first {
            candidates = ["\(fallback.topic)的基础完成度还在，继续稳住动作节奏。"]
        }

        if candidates.isEmpty, let fallback = pendingCards.first {
            candidates = ["\(fallback.topic)当前只作参考，下一次把画面拍完整。"]
        }

        return candidates
    }

    private static func buildAttentionObservationCandidates(
        summaryTags: [TrainingFeedbackSummaryTag],
        problemCards: [TrainingFeedbackProblemCard],
        pendingCards: [TrainingFeedbackPendingCard]
    ) -> [String] {
        let attentionCards = problemCards
            .filter { $0.status == .needsWork }
            .sorted { lhs, rhs in
                if lhs.status == rhs.status {
                    return lhs.topic < rhs.topic
                }
                return lhs.status > rhs.status
            }

        var candidates = attentionCards.map { card in
            "\(card.topic) \(card.issue)"
        }

        if candidates.isEmpty, let fallback = pendingCards.first {
            candidates = ["\(fallback.topic) 当前仅作参考"]
        }

        if candidates.isEmpty, let fallback = summaryTags.min(by: { $0.status.attentionRank < $1.status.attentionRank }) {
            candidates = [fallbackAttentionFallbackText(for: fallback)]
        }

        if candidates.isEmpty, let fallback = problemCards.first {
            candidates = ["\(fallback.topic)需要继续关注稳定性。"]
        }

        return candidates
    }

    private static func selectObservations(
        goodCandidates: [String],
        attentionCandidates: [String]
    ) -> (good: [String], attention: [String]) {
        let trimmedGoodCandidates = Array(goodCandidates.prefix(3))
        let trimmedAttentionCandidates = Array(attentionCandidates.prefix(3))

        guard !trimmedGoodCandidates.isEmpty else {
            return ([], Array(trimmedAttentionCandidates.prefix(3)))
        }

        let goodCount = min(2, trimmedGoodCandidates.count)
        var good = Array(trimmedGoodCandidates.prefix(goodCount))

        var remainingSlots = 3 - good.count
        let attention = Array(trimmedAttentionCandidates.prefix(remainingSlots))
        remainingSlots -= attention.count

        if remainingSlots > 0 {
            let extraGood = trimmedGoodCandidates.dropFirst(good.count).prefix(remainingSlots)
            good.append(contentsOf: extraGood)
        }

        return (good, attention)
    }

    private static func observationText(for title: String, status: TrainingFeedbackStatus) -> String {
        switch title {
        case "传球精度":
            switch status {
            case .excellent:
                return "传球精度表现很稳"
            case .good:
                return "传球精度比较稳定"
            case .needsWork:
                return "传球精度还可以再准一点"
            case .reference:
                return "传球精度先作为趋势参考"
            }
        case "接球控制":
            switch status {
            case .excellent:
                return "接球控制表现很稳"
            case .good:
                return "接球控制整体正常"
            case .needsWork:
                return "接球控制还可以再稳"
            case .reference:
                return "接球控制先作为趋势参考"
            }
        case "衔接流畅度":
            switch status {
            case .excellent:
                return "衔接流畅度很顺"
            case .good:
                return "衔接流畅度基本顺畅"
            case .needsWork:
                return "衔接流畅度还可以再紧凑"
            case .reference:
                return "衔接流畅度先作为趋势参考"
            }
        case "射门目标":
            switch status {
            case .excellent:
                return "射门目标选择很清楚"
            case .good:
                return "射门方向整体可控"
            case .needsWork:
                return "射门目标还需要更明确"
            case .reference:
                return "射门目标先作为趋势参考"
            }
        case "射门发力":
            switch status {
            case .excellent:
                return "射门发力链很顺"
            case .good:
                return "射门发力整体稳定"
            case .needsWork:
                return "射门发力还可以更集中"
            case .reference:
                return "射门发力先作为趋势参考"
            }
        case "支撑稳定":
            switch status {
            case .excellent:
                return "支撑脚和身体稳定性很好"
            case .good:
                return "支撑稳定整体正常"
            case .needsWork:
                return "支撑脚稳定性还需要加强"
            case .reference:
                return "支撑稳定先作为趋势参考"
            }
        default:
            return "\(title)整体表现\(status.displayLabel)"
        }
    }

    private static func fallbackGoodFallbackText(for tag: TrainingFeedbackSummaryTag) -> String {
        switch tag.title {
        case "传球精度":
            return "传球精度基础完成度还在，继续稳住落点。"
        case "接球控制":
            return "接球控制基础完成度还在，继续保持第一脚触球。"
        case "衔接流畅度":
            return "衔接流畅度基础完成度还在，继续把动作连起来。"
        case "射门目标":
            return "射门目标基础完成度还在，继续把球门目标区看清。"
        case "射门发力":
            return "射门发力基础完成度还在，继续稳住摆腿和收尾。"
        case "支撑稳定":
            return "支撑稳定基础完成度还在，继续把支撑脚踩实。"
        default:
            return "\(tag.title)基础完成度还在，继续保持。"
        }
    }

    private static func fallbackAttentionFallbackText(for tag: TrainingFeedbackSummaryTag) -> String {
        if tag.status.isPositive {
            switch tag.title {
            case "传球精度":
                return "传球精度可以继续保持稳定。"
            case "接球控制":
                return "接球控制可以继续保持稳定。"
            case "衔接流畅度":
                return "衔接流畅度可以继续保持稳定。"
            case "射门目标":
                return "射门目标可以继续保持清晰。"
            case "射门发力":
                return "射门发力可以继续保持稳定。"
            case "支撑稳定":
                return "支撑脚和身体稳定性可以继续保持。"
            default:
                return "\(tag.title)可以继续保持稳定。"
            }
        }

        switch tag.title {
        case "传球精度":
            return "传球精度仍需要继续关注。"
        case "接球控制":
            return "接球控制仍需要继续关注。"
        case "衔接流畅度":
            return "衔接流畅度仍需要继续关注。"
        case "射门目标":
            return "射门目标仍需要继续关注。"
        case "射门发力":
            return "射门发力仍需要继续关注。"
        case "支撑稳定":
            return "支撑稳定仍需要继续关注。"
        default:
            return "\(tag.title)仍需要继续关注。"
        }
    }

    private static func buildProblemCards(
        domains: [FeedbackDomain],
        metricLookup: [ResultMetricKey: TrainingFeedbackMetricItem],
        trainingSuggestions: [String]
    ) -> [TrainingFeedbackProblemCard] {
        var cards: [TrainingFeedbackProblemCard] = []

        for domain in domains {
            guard let metric = chooseProblemMetric(for: domain, in: metricLookup) else {
                continue
            }

            cards.append(
                buildProblemCard(
                    for: metric.key,
                    status: metric.status,
                    practiceOverride: nil
                )
            )
        }

        return cards.sorted { lhs, rhs in
            if lhs.status == rhs.status {
                let lhsUrgency = metricLookup[lhs.metricKey]?.urgencyScore ?? 0
                let rhsUrgency = metricLookup[rhs.metricKey]?.urgencyScore ?? 0
                if lhsUrgency == rhsUrgency {
                    return domainOrderIndex(for: lhs.topic) < domainOrderIndex(for: rhs.topic)
                }
                return lhsUrgency > rhsUrgency
            }
            return lhs.status > rhs.status
        }
    }

    private static func buildPendingCards(
        domains: [FeedbackDomain],
        metricLookup: [ResultMetricKey: TrainingFeedbackMetricItem]
    ) -> [TrainingFeedbackPendingCard] {
        var cards: [TrainingFeedbackPendingCard] = []

        for domain in domains {
            guard let metric = choosePendingMetric(for: domain, in: metricLookup) else {
                continue
            }

            cards.append(buildPendingCard(for: metric.key, status: metric.status))
        }

        return cards.sorted { lhs, rhs in
            if lhs.status == rhs.status {
                let lhsUrgency = metricLookup[lhs.metricKey]?.urgencyScore ?? 0
                let rhsUrgency = metricLookup[rhs.metricKey]?.urgencyScore ?? 0
                if lhsUrgency == rhsUrgency {
                    return domainOrderIndex(for: lhs.topic) < domainOrderIndex(for: rhs.topic)
                }
                return lhsUrgency > rhsUrgency
            }
            return lhs.status > rhs.status
        }
    }

    private static func chooseProblemMetric(
        for domain: FeedbackDomain,
        in metricLookup: [ResultMetricKey: TrainingFeedbackMetricItem]
    ) -> TrainingFeedbackMetricItem? {
        let candidates = domain.metricKeys.compactMap { metricLookup[$0] }
            .filter { $0.status == .needsWork }

        guard !candidates.isEmpty else {
            return nil
        }

        return candidates.sorted { lhs, rhs in
            if lhs.urgencyScore != rhs.urgencyScore {
                return lhs.urgencyScore > rhs.urgencyScore
            }

            guard let lhsIndex = domain.metricKeys.firstIndex(of: lhs.key),
                  let rhsIndex = domain.metricKeys.firstIndex(of: rhs.key) else {
                return lhs.key.rawValue < rhs.key.rawValue
            }
            return lhsIndex < rhsIndex
        }.first
    }

    private static func choosePendingMetric(
        for domain: FeedbackDomain,
        in metricLookup: [ResultMetricKey: TrainingFeedbackMetricItem]
    ) -> TrainingFeedbackMetricItem? {
        let candidates = domain.metricKeys.compactMap { metricLookup[$0] }
            .filter { $0.status == .reference }

        guard !candidates.isEmpty else {
            return nil
        }

        return candidates.sorted { lhs, rhs in
            if lhs.urgencyScore != rhs.urgencyScore {
                return lhs.urgencyScore > rhs.urgencyScore
            }

            guard let lhsIndex = domain.metricKeys.firstIndex(of: lhs.key),
                  let rhsIndex = domain.metricKeys.firstIndex(of: rhs.key) else {
                return lhs.key.rawValue < rhs.key.rawValue
            }
            return lhsIndex < rhsIndex
        }.first
    }

    private static func buildProblemCard(
        for key: ResultMetricKey,
        status: TrainingFeedbackStatus,
        practiceOverride: String?
    ) -> TrainingFeedbackProblemCard {
        let title = friendlyTitle(for: key)
        let issue = issueText(for: key, status: status)
        let whyImportant = priorityReasonText(for: key, status: status)
        let fix = fixText(for: key, status: status)
        let practice = practiceOverride?.nonEmpty ?? practiceText(for: key, status: status)
        let (kind, time) = markerForMetric(key)

        return TrainingFeedbackProblemCard(
            metricKey: key,
            topic: title,
            issue: issue,
            whyImportant: whyImportant,
            fix: fix,
            practice: practice,
            status: status,
            time: time,
            markerKind: kind
        )
    }

    private static func buildPendingCard(
        for key: ResultMetricKey,
        status: TrainingFeedbackStatus
    ) -> TrainingFeedbackPendingCard {
        let title = friendlyTitle(for: key)
        let (_, time) = markerForMetric(key)

        return TrainingFeedbackPendingCard(
            metricKey: key,
            topic: title,
            reason: pendingReasonText(for: key),
            captureAdvice: pendingCaptureAdvice(for: key),
            note: "暂不纳入正式扣分",
            status: status,
            time: time,
            markerKind: .pending
        )
    }

    private static func buildPriorityFocus(
        domains: [FeedbackDomain],
        problemCards: [TrainingFeedbackProblemCard],
        pendingCards: [TrainingFeedbackPendingCard],
        metricLookup: [ResultMetricKey: TrainingFeedbackMetricItem],
        trainingSuggestions: [String]
    ) -> TrainingFeedbackPriorityFocus {
        if let problem = problemCards.first {
            return TrainingFeedbackPriorityFocus(
                metricKey: problem.metricKey,
                keyframeMoment: keyframeMoment(for: problem.metricKey),
                title: problem.topic,
                reason: priorityReasonText(for: problem.metricKey, status: problem.status),
                nextStep: problem.practice,
                status: problem.status,
                time: problem.time,
                markerKind: problem.markerKind
            )
        }

        if let pending = pendingCards.first {
            return TrainingFeedbackPriorityFocus(
                metricKey: pending.metricKey,
                keyframeMoment: keyframeMoment(for: pending.metricKey),
                title: pending.topic,
                reason: priorityPendingReasonText(for: pending.metricKey),
                nextStep: pending.captureAdvice,
                status: pending.status,
                time: pending.time,
                markerKind: pending.markerKind
            )
        }

        let fallbackMetricKeys = orderedMetricKeys(for: domains)
        if let fallbackMetric = fallbackMetricKeys.compactMap({ metricLookup[$0] }).sorted(by: { lhs, rhs in
            if lhs.status.attentionRank == rhs.status.attentionRank {
                if lhs.urgencyScore != rhs.urgencyScore {
                    return lhs.urgencyScore > rhs.urgencyScore
                }

                let lhsIndex = fallbackMetricKeys.firstIndex(of: lhs.key) ?? .max
                let rhsIndex = fallbackMetricKeys.firstIndex(of: rhs.key) ?? .max
                return lhsIndex < rhsIndex
            }
            return lhs.status.attentionRank < rhs.status.attentionRank
        }).first {
            let practice = trainingSuggestions.first?.nonEmpty ?? practiceText(for: fallbackMetric.key, status: fallbackMetric.status)
            return TrainingFeedbackPriorityFocus(
                metricKey: fallbackMetric.key,
                keyframeMoment: keyframeMoment(for: fallbackMetric.key),
                title: fallbackMetric.title,
                reason: "当前没有明显扣分问题，先把这项继续稳住。",
                nextStep: practice,
                status: fallbackMetric.status,
                time: markerForMetric(fallbackMetric.key).1,
                markerKind: markerForMetric(fallbackMetric.key).0
            )
        }

        return TrainingFeedbackPriorityFocus(
            metricKey: fallbackMetricKeys.first ?? .passExecutionTimeS,
            keyframeMoment: .strike,
            title: fallbackMetricKeys.first.map { friendlyTitle(for: $0) } ?? "整体节奏",
            reason: domains.contains(where: \.isShotDomain)
                ? "本次先从射门支撑、触球和收尾稳定性开始看。"
                : "本次先从动作连贯性开始看，避免一次改太多细节。",
            nextStep: trainingSuggestions.first?.nonEmpty ?? (domains.contains(where: \.isShotDomain) ? "先做 3 组原地摆腿到射门收尾练习，每组 8 次。" : "先做完整动作练习，每组 5 次。"),
            status: .reference,
            time: 0,
            markerKind: .pending
        )
    }

    private static func buildVideoEvidence(
        duration: Double,
        metricLookup: [ResultMetricKey: TrainingFeedbackMetricItem],
        problemCards: [TrainingFeedbackProblemCard],
        pendingCards: [TrainingFeedbackPendingCard],
        priorityFocus: TrainingFeedbackPriorityFocus
    ) -> TrainingFeedbackVideoEvidence {
        let markers = buildTimelineMarkers(
            duration: duration,
            problemCards: problemCards,
            pendingCards: pendingCards,
            priorityFocus: priorityFocus
        )
        let keyframes = buildKeyframeSpecs(
            duration: duration,
            metricLookup: metricLookup,
            priorityFocus: priorityFocus
        )
        let primaryKeyframeID = keyframes.first(where: { $0.isPrimary })?.id ?? keyframes.first?.id ?? ""

        return TrainingFeedbackVideoEvidence(
            duration: duration,
            durationText: duration > 0 ? String(format: "%.1f 秒", duration) : "时长未知",
            markers: markers,
            keyframes: keyframes,
            primaryKeyframeID: primaryKeyframeID
        )
    }

    private static func buildConfidenceReview(
        summaryTags: [TrainingFeedbackSummaryTag],
        problemCards: [TrainingFeedbackProblemCard],
        pendingCards: [TrainingFeedbackPendingCard],
        priorityFocus: TrainingFeedbackPriorityFocus
    ) -> TrainingFeedbackConfidenceReview {
        let trustedPoints = summaryTags
            .filter { $0.status.isPositive }
            .prefix(2)
            .map { observationText(for: $0.title, status: $0.status) }

        let uncertainPoints = pendingCards.prefix(2).map { card in
            "\(card.topic) 先作为参考"
        }

        let focusSentence = problemCards.isEmpty && pendingCards.isEmpty
            ? "当前优先看的是\(priorityFocus.title)。"
            : ""

        let trustedSummary: String
        if trustedPoints.isEmpty {
            trustedSummary = "本次结论以整体趋势为主，当前没有特别强的正向项。\(focusSentence)"
        } else {
            trustedSummary = "本次结论里，\(trustedPoints.joined(separator: "；"))。\(focusSentence)"
        }

        let maybeAdvice = [
            "保持侧面固定机位，尽量拍到接球前 1 秒和出脚后 1 秒。",
            "不要只拍脚下，身体上半身和支撑脚要同时入镜。",
            "如果有低置信指标，下一次请把完整传接段拍足。"
        ]

        let focusedAdvice: [String]
        if let firstPending = pendingCards.first {
            focusedAdvice = [
                firstPending.captureAdvice,
                "把镜头固定住，避免手持抖动影响判断。"
            ]
        } else if let firstProblem = problemCards.first {
            focusedAdvice = [
                firstProblem.practice,
                "保留完整动作前后文，方便看清节奏变化。"
            ]
        } else {
            focusedAdvice = maybeAdvice
        }

        return TrainingFeedbackConfidenceReview(
            summary: trustedSummary,
            trustedPoints: trustedPoints,
            uncertainPoints: uncertainPoints,
            shootingAdvice: focusedAdvice
        )
    }

    private static func buildTimelineMarkers(
        duration: Double,
        problemCards: [TrainingFeedbackProblemCard],
        pendingCards: [TrainingFeedbackPendingCard],
        priorityFocus: TrainingFeedbackPriorityFocus
    ) -> [TrainingFeedbackTimelineMarker] {
        let markers: [TrainingFeedbackTimelineMarker] = [
            timelineMarker(
                id: "receive",
                title: "接球",
                detail: "先看第一脚触球前身体是否已经准备好。",
                time: timelineTime(for: duration, ratio: 0.18),
                kind: .receive,
                status: .good,
                isPriority: false
            ),
            timelineMarker(
                id: "strike",
                title: "出脚",
                detail: "看出脚瞬间的节奏和支撑脚是否稳定。",
                time: timelineTime(for: duration, ratio: 0.5),
                kind: .strike,
                status: .good,
                isPriority: false
            ),
            timelineMarker(
                id: "return-touch",
                title: "接触回传",
                detail: "看球从触球到传出后的连贯程度。",
                time: timelineTime(for: duration, ratio: 0.66),
                kind: .returnTouch,
                status: .good,
                isPriority: false
            ),
            timelineMarker(
                id: "stable",
                title: "稳定状态",
                detail: "看第一脚之后是否能够快速回稳。",
                time: timelineTime(for: duration, ratio: 0.82),
                kind: .stable,
                status: .good,
                isPriority: false
            )
        ]

        let issueMarkers = problemCards.map { card in
            timelineMarker(
                id: "problem-\(card.metricKey.rawValue)",
                title: card.topic,
                detail: card.issue,
                time: card.time,
                kind: .problem,
                status: card.status,
                isPriority: abs(card.time - priorityFocus.time) < 0.0001 && card.topic == priorityFocus.title
            )
        }

        let pendingMarkers = pendingCards.map { card in
            timelineMarker(
                id: "pending-\(card.metricKey.rawValue)",
                title: card.topic,
                detail: card.reason,
                time: card.time,
                kind: .pending,
                status: card.status,
                isPriority: abs(card.time - priorityFocus.time) < 0.0001 && card.topic == priorityFocus.title
            )
        }

        return (markers + issueMarkers + pendingMarkers).sorted { lhs, rhs in
            if abs(lhs.time - rhs.time) < 0.0001 {
                return lhs.kind.displayLabel < rhs.kind.displayLabel
            }
            return lhs.time < rhs.time
        }
    }

    private static func buildKeyframeSpecs(
        duration: Double,
        metricLookup: [ResultMetricKey: TrainingFeedbackMetricItem],
        priorityFocus: TrainingFeedbackPriorityFocus
    ) -> [TrainingFeedbackKeyframeSpec] {
        let safeDuration = resolveVideoDuration(duration)
        let preReceiveTime = timelineTime(for: safeDuration, ratio: 0.16)
        let strikeTime = timelineTime(for: safeDuration, ratio: 0.5)
        let stableTime = timelineTime(for: safeDuration, ratio: 0.82)

        return [
            buildKeyframeSpec(
                moment: .preReceive,
                time: preReceiveTime,
                metricLookup: metricLookup,
                priorityFocus: priorityFocus
            ),
            buildKeyframeSpec(
                moment: .strike,
                time: strikeTime,
                metricLookup: metricLookup,
                priorityFocus: priorityFocus
            ),
            buildKeyframeSpec(
                moment: .stable,
                time: stableTime,
                metricLookup: metricLookup,
                priorityFocus: priorityFocus
            )
        ]
    }

    private static func buildKeyframeSpec(
        moment: TrainingFeedbackKeyframeMoment,
        time: Double,
        metricLookup: [ResultMetricKey: TrainingFeedbackMetricItem],
        priorityFocus: TrainingFeedbackPriorityFocus
    ) -> TrainingFeedbackKeyframeSpec {
        let primaryMetricKey = keyframePrimaryMetricKey(for: moment, metricLookup: metricLookup)
        let status = keyframeStatus(for: moment, metricLookup: metricLookup)
        let confidence = keyframeConfidence(for: status)
        let focusAnnotationKinds = keyframeFocusAnnotationKinds(
            metricKey: primaryMetricKey,
            confidence: confidence
        )
        let isPrimary = priorityFocus.keyframeMoment == moment

        return TrainingFeedbackKeyframeSpec(
            id: keyframeID(for: moment),
            moment: moment,
            time: time,
            title: moment.displayTitle,
            conclusion: keyframeConclusion(for: moment, status: status),
            mainPoint: keyframeMainPoint(
                for: moment,
                metricKey: primaryMetricKey,
                status: status
            ),
            whyImportant: keyframeWhyImportant(
                for: moment,
                metricKey: primaryMetricKey,
                status: status
            ),
            howToChange: keyframeHowToChange(
                for: moment,
                metricKey: primaryMetricKey,
                status: status
            ),
            status: status,
            confidence: confidence,
            confidenceNote: confidence.note,
            focusAnnotationKinds: focusAnnotationKinds,
            isPrimary: isPrimary,
            annotations: keyframeAnnotations(
                for: moment,
                metricKey: primaryMetricKey,
                confidence: confidence
            )
        )
    }

    private static func keyframeID(for moment: TrainingFeedbackKeyframeMoment) -> String {
        switch moment {
        case .preReceive:
            return "pre-receive"
        case .strike:
            return "strike"
        case .stable:
            return "stable"
        }
    }

    private static func keyframePrimaryMetricKey(
        for moment: TrainingFeedbackKeyframeMoment,
        metricLookup: [ResultMetricKey: TrainingFeedbackMetricItem]
    ) -> ResultMetricKey {
        let candidates: [ResultMetricKey]
        switch moment {
        case .preReceive:
            candidates = [.receiveControlZoneSuccessRate]
        case .strike:
            candidates = [
                .shotTargetZoneHit,
                .shotMaxBallSpeedMPS,
                .shotMaxBallSpeedProxyMPS,
                .supportFootLateralOffsetCM,
                .supportFootAPOffsetCM,
                .trunkLeanDegAtImpactProxy,
                .passExecutionTimeS,
                .passEndpointErrorM,
                .passReceiveGapS
            ]
        case .stable:
            candidates = [
                .shotConsistencyCVPercent,
                .receiveStabilizationTimeS,
                .receiveCorrectiveTouchCount,
                .sequenceContinuityScore,
                .nextActionReadiness
            ]
        }

        let scoredCandidates = candidates.compactMap { key -> (ResultMetricKey, TrainingFeedbackStatus)? in
            guard let metric = metricLookup[key] else { return nil }
            return (key, metric.status)
        }

        if let primary = scoredCandidates.sorted(by: { lhs, rhs in
            if lhs.1.attentionRank == rhs.1.attentionRank {
                return lhs.0.rawValue < rhs.0.rawValue
            }
            return lhs.1.attentionRank < rhs.1.attentionRank
        }).first?.0 {
            return primary
        }

        return candidates.first ?? .passExecutionTimeS
    }

    private static func keyframeStatus(
        for moment: TrainingFeedbackKeyframeMoment,
        metricLookup: [ResultMetricKey: TrainingFeedbackMetricItem]
    ) -> TrainingFeedbackStatus {
        let keys: [ResultMetricKey]
        switch moment {
        case .preReceive:
            keys = [.receiveControlZoneSuccessRate]
        case .strike:
            keys = [
                .shotTargetZoneHit,
                .shotMaxBallSpeedMPS,
                .shotMaxBallSpeedProxyMPS,
                .supportFootLateralOffsetCM,
                .supportFootAPOffsetCM,
                .trunkLeanDegAtImpactProxy,
                .passExecutionTimeS,
                .passEndpointErrorM,
                .passReceiveGapS
            ]
        case .stable:
            keys = [
                .shotConsistencyCVPercent,
                .receiveStabilizationTimeS,
                .receiveCorrectiveTouchCount,
                .sequenceContinuityScore,
                .nextActionReadiness
            ]
        }

        let statuses = keys.compactMap { metricLookup[$0]?.status }
        return statuses.min(by: { lhs, rhs in
            if lhs.attentionRank == rhs.attentionRank {
                return lhs.rawValue < rhs.rawValue
            }
            return lhs.attentionRank < rhs.attentionRank
        }) ?? .reference
    }

    private static func keyframeConfidence(for status: TrainingFeedbackStatus) -> TrainingFeedbackKeyframeConfidence {
        switch status {
        case .excellent, .good:
            return .high
        case .needsWork:
            return .medium
        case .reference:
            return .low
        }
    }

    private static func keyframeConclusion(
        for moment: TrainingFeedbackKeyframeMoment,
        status: TrainingFeedbackStatus
    ) -> String {
        switch moment {
        case .preReceive:
            switch status {
            case .excellent:
                return "接球前准备很到位"
            case .good:
                return "接球前准备基本到位"
            case .needsWork:
                return "接球前准备还可以再提前一点"
            case .reference:
                return "接球前这一帧先作为参考"
            }
        case .strike:
            switch status {
            case .excellent:
                return "出脚这一下比较干净"
            case .good:
                return "出脚节奏比较顺"
            case .needsWork:
                return "出脚前还有一点停顿"
            case .reference:
                return "出脚这一帧先作为参考"
            }
        case .stable:
            switch status {
            case .excellent:
                return "接球后很快回到稳定状态"
            case .good:
                return "接球后回稳速度比较快"
            case .needsWork:
                return "接球后回稳还可以更快"
            case .reference:
                return "接球后这一帧先作为参考"
            }
        }
    }

    private static func keyframeMainPoint(
        for moment: TrainingFeedbackKeyframeMoment,
        metricKey: ResultMetricKey,
        status: TrainingFeedbackStatus
    ) -> String {
        if status == .reference {
            switch moment {
            case .preReceive:
                return "现在还不能把接球前准备完全定死，先看机位是否足够稳定。"
            case .strike:
                return "这一帧更适合先作为节奏参考，不要只看单一瞬间。"
            case .stable:
                return "这一帧更适合先作为回稳参考，等完整片段再判断。"
            }
        }

        switch metricKey {
        case .receiveControlZoneSuccessRate:
            return status == .needsWork ? "支撑脚先落稳，身体提前对准来球" : "身体已经提前进入接球准备位"
        case .passExecutionTimeS:
            return status == .needsWork ? "减少出脚前的停顿，让动作一气呵成" : "出脚和支撑脚的衔接比较顺"
        case .passEndpointErrorM:
            return status == .needsWork ? "把出球方向和支撑脚对齐，落点会更稳" : "出球线路和目标方向比较一致"
        case .passReceiveGapS:
            return status == .needsWork ? "接球后别空一下，直接连到出脚" : "传接之间的衔接比较紧凑"
        case .receiveStabilizationTimeS:
            return status == .needsWork ? "先把重心收回来，再继续处理" : "第一脚后能较快回到稳定状态"
        case .receiveCorrectiveTouchCount:
            return status == .needsWork ? "少做补救触球，让第一脚更干净" : "第一脚处理比较干净，补救很少"
        case .sequenceContinuityScore:
            return status == .needsWork ? "把传、接、下一步动作连成一条线" : "动作链路比较顺，没有明显断点"
        case .nextActionReadiness:
            return status == .needsWork ? "接球后尽快进入下一步，不要拖太久" : "接球后能较快进入下一步处理状态"
        case .shotTargetZoneHit:
            return status == .needsWork ? "先明确球门目标区，再完成触球" : "射门目标区选择比较清楚"
        case .shotMaxBallSpeedMPS, .shotMaxBallSpeedProxyMPS:
            return status == .needsWork ? "摆腿发力还不够集中，出球速度可以更强" : "摆腿发力和出球速度整体稳定"
        case .shotConsistencyCVPercent:
            return status == .needsWork ? "射门动作波动偏大，先稳住重复性" : "射门动作重复性整体可控"
        case .supportFootLateralOffsetCM, .supportFootAPOffsetCM:
            return status == .needsWork ? "支撑脚位置需要更接近理想发力区" : "支撑脚位置整体有利于发力"
        case .trunkLeanDegAtImpactProxy:
            return status == .needsWork ? "触球时身体后仰偏明显，容易把球打高" : "触球时身体角度整体稳定"
        }
    }

    private static func keyframeWhyImportant(
        for moment: TrainingFeedbackKeyframeMoment,
        metricKey: ResultMetricKey,
        status: TrainingFeedbackStatus
    ) -> String {
        if metricKey.isShotMetric {
            switch metricKey {
            case .shotTargetZoneHit:
                return status == .needsWork
                    ? "目标区不清楚时，射门很容易只剩发力，方向和门框结果都会波动。"
                    : "目标区清楚后，发力、触球面和收尾动作更容易统一。"
            case .shotMaxBallSpeedMPS, .shotMaxBallSpeedProxyMPS:
                return status == .needsWork
                    ? "出球速度不足通常说明摆腿、髋部带动或触球质量没有串起来。"
                    : "速度稳定说明发力链基本顺，后续可以再加目标区控制。"
            case .shotConsistencyCVPercent:
                return status == .needsWork
                    ? "重复性差会让一次好球变成偶然，训练时要先稳定动作模板。"
                    : "重复性稳定后，射门质量更容易在不同距离和角度下保持。"
            case .supportFootLateralOffsetCM, .supportFootAPOffsetCM:
                return status == .needsWork
                    ? "支撑脚偏远或偏前后，会直接影响髋部打开、触球部位和射门高度。"
                    : "支撑脚踩稳后，摆腿和身体收尾会更自然。"
            case .trunkLeanDegAtImpactProxy:
                return status == .needsWork
                    ? "身体后仰会让触球点变低，球更容易飘高或失去力量。"
                    : "身体角度稳定能帮助把力量压向目标方向。"
            default:
                break
            }
        }

        switch moment {
        case .preReceive:
            return status == .needsWork
                ? "接球前准备不到位，第一脚更容易跑出控制区。"
                : "接球前准备越早，第一脚越容易收进可控范围。"
        case .strike:
            return status == .needsWork
                ? "出脚节奏一乱，传球精度和衔接都会一起受影响。"
                : "出脚节奏稳住后，整段动作会更顺、更容易控制。"
        case .stable:
            return status == .needsWork
                ? "回稳慢会拖慢下一动作，整段处理会显得卡。"
                : "回稳越快，下一动作准备就越早，整体会更主动。"
        }
    }

    private static func keyframeHowToChange(
        for moment: TrainingFeedbackKeyframeMoment,
        metricKey: ResultMetricKey,
        status: TrainingFeedbackStatus
    ) -> String {
        if metricKey.isShotMetric {
            switch metricKey {
            case .shotTargetZoneHit:
                return "起脚前先选球门目标区，支撑脚指向目标侧，触球后继续朝目标收尾。"
            case .shotMaxBallSpeedMPS, .shotMaxBallSpeedProxyMPS:
                return "用髋部带动大腿，再带小腿摆出，触球后不要立刻收脚。"
            case .shotConsistencyCVPercent:
                return "先用 70% 力量连续射 6-8 脚，保证支撑脚和收尾动作每次相同。"
            case .supportFootLateralOffsetCM, .supportFootAPOffsetCM:
                return "支撑脚落在球侧约一脚距离，脚尖略指向目标，身体重心压在球上方。"
            case .trunkLeanDegAtImpactProxy:
                return "触球瞬间胸口略压住球，身体不要过早后仰，收尾方向朝目标。"
            default:
                break
            }
        }

        switch moment {
        case .preReceive:
            return status == .needsWork
                ? "接球前先踩稳支撑脚，身体提前对准来球，不要等球到了才调整。"
                : "继续保持支撑脚和身体朝向提前到位，第一脚会更稳。"
        case .strike:
            return status == .needsWork
                ? "把接球后的停顿压到最短，支撑脚先到位再出脚。"
                : "继续保持出脚和支撑脚的连贯感，不要把动作拆开。"
        case .stable:
            return status == .needsWork
                ? "接球后少做补救触球，控住后尽快回到平衡状态。"
                : "继续把球收稳后尽快进入下一步处理，节奏会更顺。"
        }
    }

    private static func keyframeAnnotations(
        for moment: TrainingFeedbackKeyframeMoment,
        metricKey: ResultMetricKey,
        confidence: TrainingFeedbackKeyframeConfidence
    ) -> [TrainingFeedbackFrameAnnotation] {
        let templates: [(TrainingFeedbackFrameAnnotationKind, Double, Double, Double)] = {
            switch moment {
            case .preReceive:
                return [
                    (.ball, 0.56, 0.33, 0),
                    (.supportFoot, 0.33, 0.79, 0),
                    (.touchFoot, 0.49, 0.73, 0),
                    (.bodyDirection, 0.42, 0.55, 18),
                    (.ballDirection, 0.71, 0.28, -4)
                ]
            case .strike:
                return [
                    (.ball, 0.61, 0.39, 0),
                    (.supportFoot, 0.30, 0.80, 0),
                    (.touchFoot, 0.52, 0.72, 0),
                    (.bodyDirection, 0.44, 0.54, 24),
                    (.ballDirection, 0.74, 0.26, 14)
                ]
            case .stable:
                return [
                    (.ball, 0.63, 0.54, 0),
                    (.supportFoot, 0.34, 0.80, 0),
                    (.touchFoot, 0.56, 0.76, 0),
                    (.bodyDirection, 0.47, 0.53, 10),
                    (.ballDirection, 0.74, 0.50, 0)
                ]
            }
        }()

        return templates.map { template in
            let kind = template.0
            return TrainingFeedbackFrameAnnotation(
                id: "\(moment.displayTitle)-\(kind.displayLabel)",
                kind: kind,
                x: template.1,
                y: template.2,
                angle: template.3,
                radius: keyframeAnnotationRadius(for: kind, confidence: confidence),
                note: keyframeAnnotationNote(
                    for: kind,
                    moment: moment,
                    metricKey: metricKey,
                    confidence: confidence
                )
            )
        }
    }

    private static func keyframeAnnotationRadius(
        for kind: TrainingFeedbackFrameAnnotationKind,
        confidence: TrainingFeedbackKeyframeConfidence
    ) -> Double {
        let base: Double
        switch kind {
        case .ball:
            base = 0.18
        case .supportFoot:
            base = 0.20
        case .touchFoot:
            base = 0.19
        case .bodyDirection:
            base = 0.22
        case .ballDirection:
            base = 0.22
        }

        switch confidence {
        case .high:
            return base
        case .medium:
            return base * 0.9
        case .low:
            return base * 0.85
        }
    }

    private static func keyframeAnnotationNote(
        for kind: TrainingFeedbackFrameAnnotationKind,
        moment: TrainingFeedbackKeyframeMoment,
        metricKey: ResultMetricKey,
        confidence: TrainingFeedbackKeyframeConfidence
    ) -> String {
        if !confidence.allowsRegionHighlights {
            return switch confidence {
            case .medium:
                "当前更适合观察动作节奏，不建议只盯这个位置。"
            case .low:
                "本帧更适合参考整体节奏，不建议做精确位置判断。"
            case .high:
                "当前关注区域较稳，可以作为趋势参考。"
            }
        }

        switch kind {
        case .ball:
            switch moment {
            case .preReceive:
                return "这里看球进入处理区域的趋势，不是像素级落点。"
            case .strike:
                return "这里看触球后球路的趋势，不是绝对落点。"
            case .stable:
                return "这里看球是否已经回到可控范围。"
            }
        case .supportFoot:
            return metricKey == .receiveControlZoneSuccessRate || metricKey == .receiveStabilizationTimeS
                ? "这里更像是支撑脚落稳的区域，不用盯脚尖像素。"
                : "这里看的是支撑脚是否先落稳，不是绝对落点。"
        case .touchFoot:
            return metricKey == .passExecutionTimeS || metricKey == .passReceiveGapS
                ? "这里看触球脚出脚是否连贯，不必追求像素级接触点。"
                : "这里看触球脚是否完成了干净处理。"
        case .bodyDirection:
            return "身体朝向看的是趋势，不是绝对角度。"
        case .ballDirection:
            return "球方向看的是整体线路，不是精确像素点。"
        }
    }

    private static func keyframeFocusAnnotationKinds(
        metricKey: ResultMetricKey,
        confidence: TrainingFeedbackKeyframeConfidence
    ) -> [TrainingFeedbackFrameAnnotationKind] {
        guard confidence.allowsRegionHighlights else {
            return []
        }

        switch metricKey {
        case .receiveControlZoneSuccessRate:
            return [.supportFoot, .bodyDirection]
        case .passExecutionTimeS:
            return [.touchFoot, .bodyDirection]
        case .passEndpointErrorM:
            return [.ballDirection, .touchFoot]
        case .passReceiveGapS:
            return [.touchFoot, .bodyDirection]
        case .receiveStabilizationTimeS:
            return [.ball, .bodyDirection]
        case .receiveCorrectiveTouchCount:
            return [.ball, .touchFoot]
        case .sequenceContinuityScore:
            return [.bodyDirection, .ballDirection]
        case .nextActionReadiness:
            return [.bodyDirection, .supportFoot]
        case .shotTargetZoneHit:
            return [.ballDirection, .touchFoot]
        case .shotMaxBallSpeedMPS, .shotMaxBallSpeedProxyMPS:
            return [.touchFoot, .bodyDirection]
        case .shotConsistencyCVPercent:
            return [.bodyDirection, .supportFoot]
        case .supportFootLateralOffsetCM, .supportFootAPOffsetCM:
            return [.supportFoot, .bodyDirection]
        case .trunkLeanDegAtImpactProxy:
            return [.bodyDirection, .touchFoot]
        }
    }

    private static func keyframeMoment(for key: ResultMetricKey) -> TrainingFeedbackKeyframeMoment {
        switch key {
        case .receiveControlZoneSuccessRate:
            return .preReceive
        case .passEndpointErrorM, .passExecutionTimeS, .passReceiveGapS:
            return .strike
        case .receiveStabilizationTimeS, .receiveCorrectiveTouchCount, .sequenceContinuityScore, .nextActionReadiness:
            return .stable
        case .shotTargetZoneHit,
             .shotMaxBallSpeedMPS,
             .shotMaxBallSpeedProxyMPS,
             .supportFootLateralOffsetCM,
             .supportFootAPOffsetCM,
             .trunkLeanDegAtImpactProxy:
            return .strike
        case .shotConsistencyCVPercent:
            return .stable
        }
    }

    private static func timelineMarker(
        id: String,
        title: String,
        detail: String,
        time: Double,
        kind: TrainingFeedbackTimelineMarkerKind,
        status: TrainingFeedbackStatus,
        isPriority: Bool
    ) -> TrainingFeedbackTimelineMarker {
        TrainingFeedbackTimelineMarker(
            id: id,
            title: title,
            detail: detail,
            time: max(time, 0),
            kind: kind,
            status: status,
            isPriority: isPriority
        )
    }

    private static func markerForMetric(_ key: ResultMetricKey) -> (TrainingFeedbackTimelineMarkerKind, Double) {
        switch key {
        case .passEndpointErrorM, .passExecutionTimeS:
            return (.strike, 0.5)
        case .receiveControlZoneSuccessRate:
            return (.receive, 0.18)
        case .receiveStabilizationTimeS, .receiveCorrectiveTouchCount:
            return (.stable, 0.82)
        case .passReceiveGapS, .sequenceContinuityScore:
            return (.returnTouch, 0.66)
        case .nextActionReadiness:
            return (.stable, 0.9)
        case .shotTargetZoneHit:
            return (.strike, 0.62)
        case .shotMaxBallSpeedMPS, .shotMaxBallSpeedProxyMPS:
            return (.strike, 0.66)
        case .shotConsistencyCVPercent:
            return (.stable, 0.82)
        case .supportFootLateralOffsetCM, .supportFootAPOffsetCM:
            return (.strike, 0.55)
        case .trunkLeanDegAtImpactProxy:
            return (.strike, 0.68)
        }
    }

    private static func timelineTime(for duration: Double, ratio: Double) -> Double {
        let safeDuration = max(duration, 1.4)
        let value = safeDuration * ratio
        let lowerBound = min(safeDuration * 0.95, 0.12)
        let upperBound = max(safeDuration - 0.12, lowerBound)
        return min(max(value, lowerBound), upperBound)
    }

    private static func resolveVideoDuration(_ videoDuration: Double?) -> Double {
        guard let videoDuration, videoDuration.isFinite, videoDuration > 0 else {
            return 2.2
        }

        return videoDuration
    }

    private static func metricExplanation(for key: ResultMetricKey, status: TrainingFeedbackStatus) -> String {
        switch key {
        case .passEndpointErrorM:
            switch status {
            case .excellent:
                return "落点接近目标，说明出球方向控制较稳。"
            case .good:
                return "落点总体可控，继续保持支撑脚和出脚方向一致。"
            case .needsWork:
                return "球的落点偏差较明显，优先修正支撑脚与出脚线路。"
            case .reference:
                return "这一项当前更容易受拍摄角度影响，先作为参考。"
            }
        case .passExecutionTimeS:
            switch status {
            case .excellent:
                return "出脚节奏很干净，动作连贯。"
            case .good:
                return "出脚没有明显拖慢，节奏基本稳定。"
            case .needsWork:
                return "接球后到出脚之间略有停顿，动作还可以更连贯。"
            case .reference:
                return "当前样本下节奏判断还不够稳定，先参考。"
            }
        case .receiveControlZoneSuccessRate:
            switch status {
            case .excellent:
                return "第一脚触球后，球基本保持在可继续处理范围内。"
            case .good:
                return "第一脚触球总体能收进控制区，继续保持即可。"
            case .needsWork:
                return "第一脚触球后球还容易跑出控制区，需要更稳的第一脚。"
            case .reference:
                return "这一项当前更适合结合更多画面重新判断。"
            }
        case .receiveStabilizationTimeS:
            switch status {
            case .excellent:
                return "接球后能很快进入稳定状态。"
            case .good:
                return "接球后稳定速度较快，动作回收正常。"
            case .needsWork:
                return "接球后稳定得偏慢，动作还可以更紧凑。"
            case .reference:
                return "这一项当前容易受片段长度影响，先参考。"
            }
        case .receiveCorrectiveTouchCount:
            switch status {
            case .excellent:
                return "补救触球很少，第一脚处理比较干净。"
            case .good:
                return "补救触球控制得还不错，继续减少多余修正。"
            case .needsWork:
                return "补救触球偏多，说明第一脚控制还不够稳。"
            case .reference:
                return "这一项更适合结合更多连续片段判断。"
            }
        case .passReceiveGapS:
            switch status {
            case .excellent:
                return "传接之间的衔接很紧凑，没有明显停顿。"
            case .good:
                return "传接衔接较快，动作没有明显停顿。"
            case .needsWork:
                return "传接之间还有一点空档，动作可以更紧。"
            case .reference:
                return "这一项当前更适合结合完整回放确认。"
            }
        case .sequenceContinuityScore:
            switch status {
            case .excellent:
                return "动作从传到接再到下一步都很顺。"
            case .good:
                return "整体衔接比较顺，动作节奏稳定。"
            case .needsWork:
                return "动作链路里还有断点，连续性可以再加强。"
            case .reference:
                return "这一项当前更像整体趋势，先参考。"
            }
        case .nextActionReadiness:
            switch status {
            case .excellent:
                return "接球后能很快进入下一步处理状态。"
            case .good:
                return "接球后能较快进入下一动作准备。"
            case .needsWork:
                return "接球后进入下一动作的速度还不够快。"
            case .reference:
                return "这一项当前样本较少，先作为参考。"
            }
        case .shotTargetZoneHit:
            switch status {
            case .excellent:
                return "射门目标区清楚，方向和门框结果更容易稳定。"
            case .good:
                return "射门方向总体可控，可以继续增加角度和压力。"
            case .needsWork:
                return "目标区命中不足，优先把支撑脚和触球面朝向目标。"
            case .reference:
                return "当前缺少完整球门或球路证据，目标区先作为参考。"
            }
        case .shotMaxBallSpeedMPS, .shotMaxBallSpeedProxyMPS:
            switch status {
            case .excellent:
                return "出球速度强，说明摆腿和触球质量比较集中。"
            case .good:
                return "出球速度稳定，继续保持髋部带动和完整收尾。"
            case .needsWork:
                return "出球速度偏弱，优先检查支撑脚、摆腿幅度和触球部位。"
            case .reference:
                return "当前速度是视频估计值，先看趋势，不作绝对测速。"
            }
        case .shotConsistencyCVPercent:
            switch status {
            case .excellent:
                return "射门重复性好，动作模板比较稳定。"
            case .good:
                return "射门波动可控，可以继续增加不同角度练习。"
            case .needsWork:
                return "射门波动偏大，需要先把支撑、摆腿和收尾固定下来。"
            case .reference:
                return "当前样本数量有限，重复性先作为参考。"
            }
        case .supportFootLateralOffsetCM, .supportFootAPOffsetCM:
            switch status {
            case .excellent:
                return "支撑脚位置稳定，有利于把力量传到球上。"
            case .good:
                return "支撑脚整体可控，继续保持脚尖指向和距离。"
            case .needsWork:
                return "支撑脚位置偏离理想发力区，会影响射门方向和高度。"
            case .reference:
                return "当前支撑脚判断受机位影响，先作为趋势参考。"
            }
        case .trunkLeanDegAtImpactProxy:
            switch status {
            case .excellent:
                return "触球时身体角度稳定，有利于压住球路。"
            case .good:
                return "身体后仰不明显，射门方向整体更可控。"
            case .needsWork:
                return "触球时身体后仰偏明显，容易把球打高或打飘。"
            case .reference:
                return "身体角度来自视频估计，先结合关键帧一起看。"
            }
        }
    }

    private static func pendingReasonText(for key: ResultMetricKey) -> String {
        switch key {
        case .passReceiveGapS:
            return "这段节奏容易受短时波动影响，单次样本不足以稳定判断。"
        case .nextActionReadiness:
            return "准备度更依赖连续动作和完整机位，当前片段还不够稳。"
        default:
            return "这一项当前置信度偏低，先作为参考，不要当成正式问题。"
        }
    }

    private static func priorityPendingReasonText(for key: ResultMetricKey) -> String {
        switch key {
        case .passReceiveGapS:
            return "传接间隔当前样本还不够稳定，先补齐完整片段再判断。"
        case .nextActionReadiness:
            return "下一动作准备度更依赖连续动作，先把接球后的完整过程拍进去。"
        default:
            return pendingReasonText(for: key)
        }
    }

    private static func pendingCaptureAdvice(for key: ResultMetricKey) -> String {
        switch key {
        case .passReceiveGapS:
            return "下次把传球前后各多拍 1 秒，完整保留接球与下一步动作。"
        case .nextActionReadiness:
            return "下次把接球后的 1-2 步也拍进去，不要只截住触球瞬间。"
        default:
            return "保持侧面固定机位，完整拍到动作前后文，再重新判断。"
        }
    }

    private static func priorityReasonText(for key: ResultMetricKey, status: TrainingFeedbackStatus) -> String {
        switch key {
        case .passEndpointErrorM:
            return status == .needsWork
                ? "落点偏差会直接影响后续处理，先把出球线路稳住。"
                : "落点是整个动作最容易被放大的细节，继续保持能让后续更稳。"
        case .passExecutionTimeS:
            return status == .needsWork
                ? "出脚节奏一乱，传球精度和衔接流畅度都会跟着波动。"
                : "出脚节奏稳住后，后面的衔接会更容易看清。"
        case .receiveControlZoneSuccessRate:
            return status == .needsWork
                ? "第一脚触球是后续动作的起点，先把球收进可控范围。"
                : "第一脚触球够稳，后面的动作自然会更顺。"
        case .receiveStabilizationTimeS:
            return status == .needsWork
                ? "接球后稳定慢，会把下一步动作拖慢。"
                : "更快稳定下来，就能更早进入下一步处理。"
        case .receiveCorrectiveTouchCount:
            return status == .needsWork
                ? "补救触球一多，动作节奏会被打断，先把第一脚做干净。"
                : "少补救就意味着动作更干净，继续保持。"
        case .passReceiveGapS:
            return status == .needsWork
                ? "传接间隔一长，动作连贯性就会变弱。"
                : "传接衔接越紧，整体节奏越容易维持。"
        case .sequenceContinuityScore:
            return status == .needsWork
                ? "动作链路里有断点，先把这条线连起来。"
                : "连续性稳住后，细节提升会更明显。"
        case .nextActionReadiness:
            return status == .needsWork
                ? "下一动作准备得越晚，后续处理越容易卡顿。"
                : "准备得更早，动作会更主动。"
        case .shotTargetZoneHit:
            return status == .needsWork
                ? "目标区不稳会让射门只剩大力起脚，先进门方向要优先锁定。"
                : "目标区稳定后，可以再提高球速和角度难度。"
        case .shotMaxBallSpeedMPS, .shotMaxBallSpeedProxyMPS:
            return status == .needsWork
                ? "球速偏弱通常来自发力链断开，先把髋部、摆腿和脚踝锁定串起来。"
                : "球速稳定说明发力链可用，继续保持完整随摆。"
        case .shotConsistencyCVPercent:
            return status == .needsWork
                ? "重复性不稳会让射门质量忽高忽低，先练固定动作模板。"
                : "重复性稳定后，射门训练才更容易迁移到比赛。"
        case .supportFootLateralOffsetCM, .supportFootAPOffsetCM:
            return status == .needsWork
                ? "支撑脚是射门发力的底座，偏远或偏前后都会影响方向和高度。"
                : "支撑脚稳定能让摆腿更顺，触球更干净。"
        case .trunkLeanDegAtImpactProxy:
            return status == .needsWork
                ? "身体后仰会让球更容易上飘，先学会把胸口压在球上方。"
                : "身体角度稳定后，射门高度和方向更可控。"
        }
    }

    private static func buildHeadline(
        actionName: String,
        scoreValue: Int?,
        summaryTags: [TrainingFeedbackSummaryTag],
        problemCards: [TrainingFeedbackProblemCard],
        pendingCards: [TrainingFeedbackPendingCard],
        priorityFocus: TrainingFeedbackPriorityFocus
    ) -> String {
        let tone = overallToneText(for: scoreValue)
        let positiveTexts = summaryTags
            .filter { $0.status.isPositive }
            .prefix(2)
            .map { observationText(for: $0.title, status: $0.status) }

        let positivePart: String
        if positiveTexts.isEmpty {
            positivePart = "动作基础完成度还在，后续可以继续打磨"
        } else {
            positivePart = positiveTexts.joined(separator: "，")
        }

        let issueLead: String
        if !problemCards.isEmpty {
            issueLead = "当前最需要优先改的是"
        } else if !pendingCards.isEmpty {
            issueLead = "当前主要低置信项是"
        } else {
            issueLead = "当前最值得继续保持的是"
        }

        return "\(headlineSubjectText(for: actionName))整体表现\(tone)，\(positivePart)。\(issueLead)\(priorityFocus.title)。"
    }

    private static func headlineSubjectText(for actionName: String) -> String {
        let normalized = actionName.trimmingCharacters(in: .whitespacesAndNewlines)
        if normalized.isEmpty ||
            normalized.localizedCaseInsensitiveContains("其他") ||
            normalized.localizedCaseInsensitiveContains("不确定") ||
            normalized.localizedCaseInsensitiveContains("待确认") {
            return "本次动作"
        }

        return "本次\(normalized)"
    }

    private static func issueText(for key: ResultMetricKey, status: TrainingFeedbackStatus) -> String {
        switch key {
        case .passEndpointErrorM:
            switch status {
            case .excellent:
                return "落点控制稳定"
            case .good:
                return "落点偏差可控"
            case .needsWork:
                return "落点误差偏大"
            case .reference:
                return "当前先作参考"
            }
        case .passExecutionTimeS:
            switch status {
            case .excellent:
                return "出球节奏连贯"
            case .good:
                return "出球准备较顺"
            case .needsWork:
                return "出球准备偏慢"
            case .reference:
                return "当前先作参考"
            }
        case .receiveControlZoneSuccessRate:
            switch status {
            case .excellent:
                return "第一脚控制稳定"
            case .good:
                return "第一脚方向基本可控"
            case .needsWork:
                return "第一脚触球偏散"
            case .reference:
                return "当前先作参考"
            }
        case .receiveStabilizationTimeS:
            switch status {
            case .excellent:
                return "接球后回稳快"
            case .good:
                return "接球后回稳较顺"
            case .needsWork:
                return "接球后回稳偏慢"
            case .reference:
                return "当前先作参考"
            }
        case .receiveCorrectiveTouchCount:
            switch status {
            case .excellent:
                return "补救触球少"
            case .good:
                return "补救触球可控"
            case .needsWork:
                return "补救触球数偏多"
            case .reference:
                return "当前先作参考"
            }
        case .passReceiveGapS:
            switch status {
            case .excellent:
                return "传接间隔已经比较紧凑"
            case .good:
                return "传接间隔基本顺畅"
            case .needsWork:
                return "传接间隔偏长"
            case .reference:
                return "当前先作参考"
            }
        case .sequenceContinuityScore:
            switch status {
            case .excellent:
                return "动作链路连续"
            case .good:
                return "动作链路基本连续"
            case .needsWork:
                return "动作链路有断点"
            case .reference:
                return "当前先作参考"
            }
        case .nextActionReadiness:
            switch status {
            case .excellent:
                return "下一动作准备主动"
            case .good:
                return "下一动作准备较早"
            case .needsWork:
                return "下一动作准备偏晚"
            case .reference:
                return "当前先作参考"
            }
        case .shotTargetZoneHit:
            switch status {
            case .excellent:
                return "目标区命中清楚"
            case .good:
                return "射门方向可控"
            case .needsWork:
                return "射门目标不稳"
            case .reference:
                return "目标区先作参考"
            }
        case .shotMaxBallSpeedMPS, .shotMaxBallSpeedProxyMPS:
            switch status {
            case .excellent:
                return "出球速度强"
            case .good:
                return "出球速度稳定"
            case .needsWork:
                return "出球速度偏弱"
            case .reference:
                return "速度趋势先作参考"
            }
        case .shotConsistencyCVPercent:
            switch status {
            case .excellent:
                return "射门重复性稳定"
            case .good:
                return "射门波动可控"
            case .needsWork:
                return "射门波动偏大"
            case .reference:
                return "重复性先作参考"
            }
        case .supportFootLateralOffsetCM, .supportFootAPOffsetCM:
            switch status {
            case .excellent:
                return "支撑脚位置稳定"
            case .good:
                return "支撑脚位置可控"
            case .needsWork:
                return "支撑脚偏离发力区"
            case .reference:
                return "支撑脚先作参考"
            }
        case .trunkLeanDegAtImpactProxy:
            switch status {
            case .excellent:
                return "身体角度稳定"
            case .good:
                return "后仰控制正常"
            case .needsWork:
                return "触球时后仰明显"
            case .reference:
                return "身体角度先作参考"
            }
        }
    }

    private static func fixText(for key: ResultMetricKey, status: TrainingFeedbackStatus) -> String {
        switch key {
        case .passEndpointErrorM:
            switch status {
            case .excellent, .good:
                return "继续保持支撑脚方向一致，击球面朝向目标，落点会更稳。"
            case .needsWork:
                return "出脚前先对准目标点，减少身体横向晃动，提升落点一致性。"
            case .reference:
                return "先把支撑脚和触球面稳定住，再观察落点变化。"
            }
        case .passExecutionTimeS:
            switch status {
            case .excellent, .good:
                return "减少接球后的停顿，支撑脚提前到位，出脚会更连贯。"
            case .needsWork:
                return "减少接球后的停顿，支撑脚提前到位，出脚更连贯。"
            case .reference:
                return "先缩短接球后的停顿，再看出脚节奏是否更稳定。"
            }
        case .receiveControlZoneSuccessRate:
            switch status {
            case .excellent, .good:
                return "第一脚触球尽量落在身体前侧，先稳住再继续推进。"
            case .needsWork:
                return "第一脚触球尽量落在身体前侧，减少大幅修正。"
            case .reference:
                return "先把第一脚触球控制在身体前侧，再确认控制区表现。"
            }
        case .receiveStabilizationTimeS:
            switch status {
            case .excellent, .good:
                return "接球后尽快收回重心，减少额外小步调整。"
            case .needsWork:
                return "接球后尽量缩短调整步数，让身体更快稳定下来。"
            case .reference:
                return "先观察接球后重心收回的速度，再做细化调整。"
            }
        case .receiveCorrectiveTouchCount:
            switch status {
            case .excellent, .good:
                return "第一脚触球时就把球控制到位，减少二次修正。"
            case .needsWork:
                return "把第一脚触球做得更干净，尽量减少补救触球。"
            case .reference:
                return "先把第一脚触球做稳，再确认是否还需要补救。"
            }
        case .passReceiveGapS:
            switch status {
            case .excellent, .good:
                return "接球前先预判下一步方向，动作会更紧凑。"
            case .needsWork:
                return "接球前先预判下一步方向，缩短停顿，动作更连贯。"
            case .reference:
                return "先把接球和下一步动作连起来，再观察间隔变化。"
            }
        case .sequenceContinuityScore:
            switch status {
            case .excellent, .good:
                return "把传球、接球和下一动作的节奏连成一条线。"
            case .needsWork:
                return "把传球、接球和下一动作的节奏连成一条线，减少断点。"
            case .reference:
                return "先看整体衔接是否顺，再做节奏细化。"
            }
        case .nextActionReadiness:
            switch status {
            case .excellent, .good:
                return "接球前先想好下一步动作，身体重心提前跟上。"
            case .needsWork:
                return "接球前先确定下一步动作，身体重心提前跟上。"
            case .reference:
                return "先把下一步动作想清楚，再确认准备度。"
            }
        case .shotTargetZoneHit:
            return "每次起脚前先选近角或远角目标区，支撑脚脚尖和触球面都朝目标收尾。"
        case .shotMaxBallSpeedMPS, .shotMaxBallSpeedProxyMPS:
            return "先用 70% 力量完成髋部带动、脚踝锁定和完整随摆，再逐步加速。"
        case .shotConsistencyCVPercent:
            return "用同一距离连续射 6-8 脚，要求支撑脚落点和收尾方向每次一致。"
        case .supportFootLateralOffsetCM, .supportFootAPOffsetCM:
            return "支撑脚落在球侧约一脚距离，脚尖指向目标，重心不要落在球后。"
        case .trunkLeanDegAtImpactProxy:
            return "触球瞬间胸口略压住球，头和身体不要过早向后抬。"
        }
    }

    private static func practiceText(for key: ResultMetricKey, status: TrainingFeedbackStatus) -> String {
        switch key {
        case .passEndpointErrorM:
            switch status {
            case .excellent, .good:
                return "定点传球：左右各 3 组 x 12 球，支撑脚指向目标，触球面保持正对目标区。"
            case .needsWork:
                return "目标门传球：设 1.5 米宽目标门，4 组 x 10 球，先求落点稳定，再逐步加快出球。"
            case .reference:
                return "慢速对墙传球：3 组 x 15 球，先看支撑脚、摆腿线路和球速是否稳定。"
            }
        case .passExecutionTimeS:
            switch status {
            case .excellent, .good:
                return "两触球节奏：接球 1 脚调整、下一脚传出，4 组 x 12 次，每次都提前看目标。"
            case .needsWork:
                return "一停一传限时：接球后 2 秒内传出，4 组 x 10 次，重点减少停顿和多余调整。"
            case .reference:
                return "分节奏传球：慢速 2 组、比赛节奏 2 组，每组 10 次，比较节奏是否更连贯。"
            }
        case .receiveControlZoneSuccessRate:
            switch status {
            case .excellent, .good:
                return "第一脚触球入区：设 2 米控制区，4 组 x 10 次，第一脚把球带向下一传方向。"
            case .needsWork:
                return "接球缓冲练习：4 组 x 10 次，脚踝放松，第一脚把球停在身体前侧半步到一步。"
            case .reference:
                return "第一脚方向练习：3 组 x 12 次，每次接球后必须朝下一动作方向带出。"
            }
        case .receiveStabilizationTimeS:
            switch status {
            case .excellent, .good:
                return "接球后启动：3 组 x 8 轮，接球后 1 步内完成重心回收并准备下一脚。"
            case .needsWork:
                return "接球回稳练习：4 组 x 8 轮，接球后先稳重心，再传向第二目标点。"
            case .reference:
                return "慢速接球回稳：3 组 x 8 轮，先减少多余小步，再逐步加快。"
            }
        case .receiveCorrectiveTouchCount:
            switch status {
            case .excellent, .good:
                return "少触球控制：3 组 x 10 次，接球后最多 2 脚完成控制和传出。"
            case .needsWork:
                return "两脚内处理：4 组 x 8 轮，第一脚控制、第二脚传出，超过两脚就重新开始。"
            case .reference:
                return "单脚触球控制：3 组 x 10 次，先让第一脚质量稳定，再加速度。"
            }
        case .passReceiveGapS:
            switch status {
            case .excellent, .good:
                return "接球即转移：3 组 x 8 轮，接球前先看下一目标，接球后 2 秒内转移。"
            case .needsWork:
                return "传接衔接压缩：4 组 x 8 轮，限制两触球，重点缩短接球到下一脚的间隔。"
            case .reference:
                return "完整传接串联：3 组 x 6 轮，保留接球前后节奏，先看动作是否连起来。"
            }
        case .sequenceContinuityScore:
            switch status {
            case .excellent, .good:
                return "三动作串联：接球、传球、再移动，3 组 x 6 轮，保持每轮节奏一致。"
            case .needsWork:
                return "传接移动串联：4 组 x 6 轮，每轮完成接球、传出、跟进移动，减少中间断点。"
            case .reference:
                return "低速串联练习：3 组 x 6 轮，先把动作顺序连清楚，再加快速度。"
            }
        case .nextActionReadiness:
            switch status {
            case .excellent, .good:
                return "接球前扫描：3 组 x 10 次，传球来前先看目标，接球后立即进入下一动作。"
            case .needsWork:
                return "预判转移练习：4 组 x 8 次，接球前喊出下一目标，接球后直接传或带。"
            case .reference:
                return "慢速预判练习：3 组 x 8 次，先明确下一步选择，再逐步提高节奏。"
            }
        case .shotTargetZoneHit:
            return "目标区射门：球门分近角/远角/中路 3 区，4 组 x 6 球，先命中目标区再加力量。"
        case .shotMaxBallSpeedMPS, .shotMaxBallSpeedProxyMPS:
            return "发力链射门：原地摆腿 2 组 x 8 次，再 3 步助跑射门 4 组 x 5 球，重点髋部带动和脚踝锁定。"
        case .shotConsistencyCVPercent:
            return "重复模板射门：同一点连续 6 球为 1 组，做 4 组，每组只改一个变量，保持支撑脚和收尾一致。"
        case .supportFootLateralOffsetCM, .supportFootAPOffsetCM:
            return "支撑脚定位：在球侧放标志碟，4 组 x 6 球，支撑脚踩到标志旁再射门。"
        case .trunkLeanDegAtImpactProxy:
            return "压球射门：中低速 4 组 x 6 球，要求触球后身体继续向目标前方收尾，避免后仰。"
        }
    }

    private static func overallToneText(for scoreValue: Int?) -> String {
        guard let scoreValue else {
            return "尚可"
        }

        switch scoreValue {
        case 90...:
            return "优秀"
        case 80..<90:
            return "良好"
        case 70..<80:
            return "尚可"
        default:
            return "需加强"
        }
    }

    private static func domainOrderIndex(for title: String) -> Int {
        switch title {
        case "传球精度":
            return 0
        case "接球控制":
            return 1
        case "衔接流畅度":
            return 2
        case "射门目标":
            return 0
        case "射门发力":
            return 1
        case "支撑稳定":
            return 2
        default:
            return 99
        }
    }
}

private enum FeedbackDomain: CaseIterable {
    case pass
    case receive
    case sequence
    case shotTarget
    case shotPower
    case shotSupport

    var summaryTitle: String {
        switch self {
        case .pass:
            return "传球精度"
        case .receive:
            return "接球控制"
        case .sequence:
            return "衔接流畅度"
        case .shotTarget:
            return "射门目标"
        case .shotPower:
            return "射门发力"
        case .shotSupport:
            return "支撑稳定"
        }
    }

    var metricKeys: [ResultMetricKey] {
        switch self {
        case .pass:
            return [.passEndpointErrorM, .passExecutionTimeS]
        case .receive:
            return [.receiveControlZoneSuccessRate, .receiveStabilizationTimeS, .receiveCorrectiveTouchCount]
        case .sequence:
            return [.passReceiveGapS, .sequenceContinuityScore, .nextActionReadiness]
        case .shotTarget:
            return [.shotTargetZoneHit]
        case .shotPower:
            return [.shotMaxBallSpeedMPS, .shotMaxBallSpeedProxyMPS, .shotConsistencyCVPercent]
        case .shotSupport:
            return [.supportFootLateralOffsetCM, .supportFootAPOffsetCM, .trunkLeanDegAtImpactProxy]
        }
    }

    var isShotDomain: Bool {
        switch self {
        case .shotTarget, .shotPower, .shotSupport:
            return true
        case .pass, .receive, .sequence:
            return false
        }
    }

    static func domains(
        for selectedAction: AnalysisActionChoice?,
        actionName: String
    ) -> [FeedbackDomain] {
        if selectedAction == .shot || actionName.localizedCaseInsensitiveContains("射门") || actionName.localizedCaseInsensitiveContains("shot") {
            return [.shotTarget, .shotPower, .shotSupport]
        }

        if selectedAction == .receive || actionName.localizedCaseInsensitiveContains("接球") || actionName.localizedCaseInsensitiveContains("receive") {
            return [.receive]
        }

        if selectedAction == .passReceive ||
            actionName.localizedCaseInsensitiveContains("传接") ||
            actionName.localizedCaseInsensitiveContains("sequence") {
            return [.pass, .receive, .sequence]
        }

        return [.pass, .receive, .sequence]
    }
}

private extension Array {
    subscript(safe index: Int) -> Element? {
        guard indices.contains(index) else { return nil }
        return self[index]
    }
}
