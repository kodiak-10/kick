import Foundation

enum ResultFindingCategory: String, Hashable, Codable {
    case improve
    case pending

    var displayTitle: String {
        switch self {
        case .improve:
            return "需改进"
        case .pending:
            return "低置信参考"
        }
    }

    var systemImage: String {
        switch self {
        case .improve:
            return "exclamationmark.triangle.fill"
        case .pending:
            return "questionmark.circle.fill"
        }
    }
}

enum ResultTriggerKind: String, Hashable, Codable {
    case fail
    case poor
    case lowConfidence = "low_confidence"
    case unknown

    var category: ResultFindingCategory {
        switch self {
        case .lowConfidence:
            return .pending
        case .fail, .poor, .unknown:
            return .improve
        }
    }

    var summaryBadgeTitle: String {
        switch self {
        case .lowConfidence:
            return "低置信参考"
        case .fail, .poor:
            return "需改进项"
        case .unknown:
            return "结果摘要"
        }
    }

    var displayLabel: String {
        switch self {
        case .fail:
            return "fail"
        case .poor:
            return "poor"
        case .lowConfidence:
            return "low_confidence"
        case .unknown:
            return "unknown"
        }
    }
}

enum ResultConfidenceLevel: String, Hashable, Codable {
    case high
    case low

    var displayLabel: String {
        switch self {
        case .high:
            return "高置信度"
        case .low:
            return "低置信度"
        }
    }
}

enum ResultMetricGroup: String, CaseIterable, Hashable, Codable {
    case pass
    case receive
    case sequence
    case shot

    var displayTitle: String {
        switch self {
        case .pass:
            return "传球表现"
        case .receive:
            return "接球表现"
        case .sequence:
            return "序列衔接"
        case .shot:
            return "射门表现"
        }
    }

    var subtitle: String {
        switch self {
        case .pass:
            return "关注出球落点与执行节奏"
        case .receive:
            return "关注控制区命中、稳定用时与修正触球"
        case .sequence:
            return "关注传接间隔与下一动作准备度"
        case .shot:
            return "关注球门目标、出球速度、支撑脚和发力稳定"
        }
    }

    var systemImage: String {
        switch self {
        case .pass:
            return "paperplane.fill"
        case .receive:
            return "hand.raised.fill"
        case .sequence:
            return "link"
        case .shot:
            return "figure.soccer"
        }
    }
}

enum ResultMetricKey: String, CaseIterable, Hashable, Codable {
    case passEndpointErrorM = "pass_endpoint_error_m"
    case passExecutionTimeS = "pass_execution_time_s"
    case receiveControlZoneSuccessRate = "receive_control_zone_success_rate"
    case receiveStabilizationTimeS = "receive_stabilization_time_s"
    case receiveCorrectiveTouchCount = "receive_corrective_touch_count"
    case passReceiveGapS = "pass_receive_gap_s"
    case sequenceContinuityScore = "sequence_continuity_score"
    case nextActionReadiness = "next_action_readiness"
    case shotTargetZoneHit = "target_zone_hit"
    case shotMaxBallSpeedMPS = "max_ball_speed_mps"
    case shotMaxBallSpeedProxyMPS = "max_ball_speed_proxy_mps"
    case shotConsistencyCVPercent = "shot_consistency_cv_pct"
    case supportFootLateralOffsetCM = "support_foot_lateral_offset_cm"
    case supportFootAPOffsetCM = "support_foot_ap_offset_cm"
    case trunkLeanDegAtImpactProxy = "trunk_lean_deg_at_impact_proxy"

    var displayTitle: String {
        switch self {
        case .passEndpointErrorM:
            return "传球落点误差"
        case .passExecutionTimeS:
            return "传球执行时间"
        case .receiveControlZoneSuccessRate:
            return "接球控制区成功率"
        case .receiveStabilizationTimeS:
            return "接球稳定用时"
        case .receiveCorrectiveTouchCount:
            return "接球修正触球数"
        case .passReceiveGapS:
            return "传接间隔"
        case .sequenceContinuityScore:
            return "序列连贯度"
        case .nextActionReadiness:
            return "下一动作准备度"
        case .shotTargetZoneHit:
            return "球门目标区"
        case .shotMaxBallSpeedMPS:
            return "出球速度"
        case .shotMaxBallSpeedProxyMPS:
            return "出球速度趋势"
        case .shotConsistencyCVPercent:
            return "射门稳定性"
        case .supportFootLateralOffsetCM:
            return "支撑脚横向距离"
        case .supportFootAPOffsetCM:
            return "支撑脚前后距离"
        case .trunkLeanDegAtImpactProxy:
            return "触球身体后仰"
        }
    }

    var englishSubtitle: String {
        switch self {
        case .passEndpointErrorM:
            return "pass endpoint error"
        case .passExecutionTimeS:
            return "pass execution time"
        case .receiveControlZoneSuccessRate:
            return "receive control success rate"
        case .receiveStabilizationTimeS:
            return "receive stabilization time"
        case .receiveCorrectiveTouchCount:
            return "receive corrective touch count"
        case .passReceiveGapS:
            return "pass receive gap"
        case .sequenceContinuityScore:
            return "sequence continuity score"
        case .nextActionReadiness:
            return "next action readiness"
        case .shotTargetZoneHit:
            return "shot target zone"
        case .shotMaxBallSpeedMPS:
            return "max ball speed"
        case .shotMaxBallSpeedProxyMPS:
            return "ball speed proxy"
        case .shotConsistencyCVPercent:
            return "shot consistency"
        case .supportFootLateralOffsetCM:
            return "support foot lateral offset"
        case .supportFootAPOffsetCM:
            return "support foot forward offset"
        case .trunkLeanDegAtImpactProxy:
            return "trunk lean at impact"
        }
    }

    var group: ResultMetricGroup {
        switch self {
        case .passEndpointErrorM, .passExecutionTimeS:
            return .pass
        case .receiveControlZoneSuccessRate, .receiveStabilizationTimeS, .receiveCorrectiveTouchCount:
            return .receive
        case .passReceiveGapS, .sequenceContinuityScore, .nextActionReadiness:
            return .sequence
        case .shotTargetZoneHit,
             .shotMaxBallSpeedMPS,
             .shotMaxBallSpeedProxyMPS,
             .shotConsistencyCVPercent,
             .supportFootLateralOffsetCM,
             .supportFootAPOffsetCM,
             .trunkLeanDegAtImpactProxy:
            return .shot
        }
    }

    var defaultConfidence: ResultConfidenceLevel {
        switch self {
        case .passReceiveGapS,
             .nextActionReadiness,
             .shotMaxBallSpeedProxyMPS,
             .shotConsistencyCVPercent,
             .trunkLeanDegAtImpactProxy:
            return .low
        case .passEndpointErrorM,
             .passExecutionTimeS,
             .receiveControlZoneSuccessRate,
             .receiveStabilizationTimeS,
             .receiveCorrectiveTouchCount,
             .sequenceContinuityScore,
             .shotTargetZoneHit,
             .shotMaxBallSpeedMPS,
             .supportFootLateralOffsetCM,
             .supportFootAPOffsetCM:
            return .high
        }
    }

    var isShotMetric: Bool {
        group == .shot
    }
}

struct ResultMetric: Identifiable, Hashable, Codable {
    let key: ResultMetricKey
    let currentValue: String
    let band: String
    let confidence: ResultConfidenceLevel

    var id: String { key.rawValue }
}

struct ResultPerformanceCard: Identifiable, Hashable, Codable {
    let group: ResultMetricGroup
    let title: String
    let subtitle: String
    let metrics: [ResultMetric]

    var id: String { group.rawValue }
}

struct ResultFinding: Identifiable, Hashable, Codable {
    let id: String
    let trigger: ResultTriggerKind
    let title: String
    let detail: String

    var category: ResultFindingCategory { trigger.category }

    init(trigger: ResultTriggerKind, title: String, detail: String) {
        self.id = "\(trigger.rawValue)-\(title)-\(detail)"
        self.trigger = trigger
        self.title = title
        self.detail = detail
    }
}

struct ResultDebugSnapshot: Hashable, Codable {
    var matchedKey: [String]
    var weight: [String]
    var sourceClass: [String]
    var rawActionCandidates: [String]
    var candidateScores: [String]
    var sequenceUpgradeReason: String
    var metricDebug: [String]
    var qualityGate: [String]
}

struct ResultReport: Hashable, Codable {
    let actionName: String
    let totalScore: Int
    let grade: String
    let summaryTag: String
    let summary: String
    let trainingSuggestions: [String]
    let performanceCards: [ResultPerformanceCard]
    let improvementFindings: [ResultFinding]
    let pendingFindings: [ResultFinding]
    let metrics: [ResultMetric]
    let debug: ResultDebugSnapshot
}

struct AnalysisReportPayload: Hashable, Codable {
    var actionName: String?
    var totalScore: Int?
    var grade: String?
    var summaryTag: String?
    var summary: String?
    var summaryTrigger: ResultTriggerKind?
    var performanceCards: [ResultPerformanceCard]?
    var improvementFindings: [ResultFinding]?
    var pendingFindings: [ResultFinding]?
    var metrics: [ResultMetric]?
    var debug: ResultDebugSnapshot?
}

enum ResultReportFactory {
    static func make(from result: AnalysisResult, payload: AnalysisReportPayload? = nil) -> ResultReport {
        let fallbackMetrics = makeFallbackMetrics(from: result)
        let metrics = resolveMetrics(payload?.metrics, fallback: fallbackMetrics)
        let performanceCards = payload?.performanceCards ?? makePerformanceCards(from: metrics)
        let improvementFindings = payload?.improvementFindings ?? makeImprovementFindings(from: result)
        let pendingFindings = payload?.pendingFindings ?? makePendingFindings(from: metrics)
        let summaryTag = resolveSummaryTag(result: result, payload: payload, improvementFindings: improvementFindings, pendingFindings: pendingFindings)
        let debug = payload?.debug ?? makeFallbackDebug(from: result, metrics: metrics)

        return ResultReport(
            actionName: payload?.actionName ?? result.motionType,
            totalScore: payload?.totalScore ?? result.score,
            grade: payload?.grade ?? gradeLabel(for: result.score),
            summaryTag: summaryTag,
            summary: payload?.summary ?? result.summary,
            trainingSuggestions: result.trainingSuggestions,
            performanceCards: performanceCards,
            improvementFindings: improvementFindings,
            pendingFindings: pendingFindings,
            metrics: metrics,
            debug: debug
        )
    }

    private static func resolveMetrics(_ payloadMetrics: [ResultMetric]?, fallback: [ResultMetric]) -> [ResultMetric] {
        guard let payloadMetrics, !payloadMetrics.isEmpty else {
            return fallback
        }

        let fallbackByKey = Dictionary(fallback.map { ($0.key, $0) }, uniquingKeysWith: { first, _ in first })
        let payloadByKey = Dictionary(payloadMetrics.map { ($0.key, $0) }, uniquingKeysWith: { first, _ in first })

        return ResultMetricKey.allCases.compactMap { key in
            payloadByKey[key] ?? fallbackByKey[key]
        }
    }

    private static func resolveSummaryTag(
        result: AnalysisResult,
        payload: AnalysisReportPayload?,
        improvementFindings: [ResultFinding],
        pendingFindings: [ResultFinding]
    ) -> String {
        let normalizedSummary = result.summary.trimmingCharacters(in: .whitespacesAndNewlines)
        if normalizedSummary.localizedCaseInsensitiveContains("异常") ||
            result.freeIssues.contains(where: { $0.title.localizedCaseInsensitiveContains("异常") }) {
            return "结果异常"
        }

        if let summaryTag = payload?.summaryTag, !summaryTag.isEmpty {
            return summaryTag
        }

        if let trigger = payload?.summaryTrigger {
            return trigger.summaryBadgeTitle
        }

        if result.score < 75 {
            return "低置信参考"
        }

        if !improvementFindings.isEmpty {
            return "需改进项"
        }

        if !pendingFindings.isEmpty {
            return "低置信参考"
        }

        return "结果摘要"
    }

    private static func makeFallbackMetrics(from result: AnalysisResult) -> [ResultMetric] {
        ResultMetricKey.allCases.map { key in
            makeFallbackMetric(for: key, result: result)
        }
    }

    private static func makeFallbackMetric(for key: ResultMetricKey, result: AnalysisResult) -> ResultMetric {
        let score = Double(result.score)
        let issueCount = Double(result.freeIssues.count)
        let reviewCount = Double(result.videoReviewData.issues.count)

        switch key {
        case .passEndpointErrorM:
            let value = 0.12 + (100 - score) * 0.004
            return ResultMetric(
                key: key,
                currentValue: formatMeters(value),
                band: bandForLowerBetter(value, thresholds: [0.22, 0.32], labels: ["稳定", "可控", "偏高"]),
                confidence: key.defaultConfidence
            )
        case .passExecutionTimeS:
            let value = 0.68 + (100 - score) * 0.0035 + reviewCount * 0.02
            return ResultMetric(
                key: key,
                currentValue: formatSeconds(value),
                band: bandForLowerBetter(value, thresholds: [0.85, 1.05], labels: ["流畅", "正常", "偏慢"]),
                confidence: key.defaultConfidence
            )
        case .receiveControlZoneSuccessRate:
            let value = max(58, min(96, score + 5 - issueCount * 2))
            return ResultMetric(
                key: key,
                currentValue: formatPercent(value),
                band: bandForHigherBetter(value, thresholds: [88, 76], labels: ["优秀", "稳定", "需提升"]),
                confidence: key.defaultConfidence
            )
        case .receiveStabilizationTimeS:
            let value = 0.48 + issueCount * 0.16
            return ResultMetric(
                key: key,
                currentValue: formatSeconds(value),
                band: bandForLowerBetter(value, thresholds: [0.65, 0.85], labels: ["快速", "正常", "偏慢"]),
                confidence: key.defaultConfidence
            )
        case .receiveCorrectiveTouchCount:
            let value = max(0, Int((issueCount / 2.0).rounded(.up)))
            let band: String
            switch value {
            case 0:
                band = "理想"
            case 1:
                band = "可控"
            default:
                band = "偏多"
            }
            return ResultMetric(
                key: key,
                currentValue: "\(value) 次",
                band: band,
                confidence: key.defaultConfidence
            )
        case .passReceiveGapS:
            let value = 0.24 + reviewCount * 0.045
            return ResultMetric(
                key: key,
                currentValue: formatSeconds(value),
                band: bandForLowerBetter(value, thresholds: [0.32, 0.44], labels: ["紧凑", "可接受", "偏大"]),
                confidence: key.defaultConfidence
            )
        case .sequenceContinuityScore:
            let value = max(54, min(96, score - 1 + issueCount * 2))
            return ResultMetric(
                key: key,
                currentValue: "\(Int(value)) / 100",
                band: bandForHigherBetter(value, thresholds: [85, 72], labels: ["稳定", "正常", "需修正"]),
                confidence: key.defaultConfidence
            )
        case .nextActionReadiness:
            let value: String
            let band: String

            if score >= 85 && issueCount <= 1 {
                value = "高"
                band = "可执行"
            } else if score >= 75 {
                value = "中"
                band = "观察中"
            } else {
                value = "低置信"
                band = "低置信"
            }

            return ResultMetric(
                key: key,
                currentValue: value,
                band: band,
                confidence: key.defaultConfidence
            )
        case .shotTargetZoneHit:
            let value = score >= 70 ? "命中" : "未命中"
            return ResultMetric(
                key: key,
                currentValue: value,
                band: score >= 85 ? "优秀" : score >= 70 ? "良好" : "需提升",
                confidence: key.defaultConfidence
            )
        case .shotMaxBallSpeedMPS:
            let value = max(8, min(28, 9 + score * 0.18))
            return ResultMetric(
                key: key,
                currentValue: String(format: "%.1f m/s", value),
                band: bandForHigherBetter(value, thresholds: [21, 16], labels: ["强劲", "稳定", "偏弱"]),
                confidence: key.defaultConfidence
            )
        case .shotMaxBallSpeedProxyMPS:
            let value = max(4, min(22, 6 + score * 0.12))
            return ResultMetric(
                key: key,
                currentValue: String(format: "%.1f", value),
                band: bandForHigherBetter(value, thresholds: [16, 11], labels: ["强劲", "稳定", "偏弱"]),
                confidence: key.defaultConfidence
            )
        case .shotConsistencyCVPercent:
            let value = max(8, min(48, 48 - score * 0.34 + issueCount * 2))
            return ResultMetric(
                key: key,
                currentValue: String(format: "%.0f%%", value),
                band: bandForLowerBetter(value, thresholds: [18, 30], labels: ["稳定", "可控", "波动大"]),
                confidence: key.defaultConfidence
            )
        case .supportFootLateralOffsetCM:
            let value = max(12, min(55, 18 + (100 - score) * 0.28))
            return ResultMetric(
                key: key,
                currentValue: String(format: "%.0f cm", value),
                band: bandForLowerBetter(value, thresholds: [30, 42], labels: ["稳定", "可控", "偏远"]),
                confidence: key.defaultConfidence
            )
        case .supportFootAPOffsetCM:
            let value = max(-12, min(28, 2 + (100 - score) * 0.18))
            return ResultMetric(
                key: key,
                currentValue: String(format: "%.0f cm", value),
                band: abs(value) <= 12 ? "稳定" : abs(value) <= 20 ? "可控" : "需调整",
                confidence: key.defaultConfidence
            )
        case .trunkLeanDegAtImpactProxy:
            let value = max(-8, min(28, 2 + (100 - score) * 0.20))
            return ResultMetric(
                key: key,
                currentValue: String(format: "%.0f°", value),
                band: bandForLowerBetter(abs(value), thresholds: [10, 18], labels: ["稳定", "可控", "后仰明显"]),
                confidence: key.defaultConfidence
            )
        }
    }

    private static func makePerformanceCards(from metrics: [ResultMetric]) -> [ResultPerformanceCard] {
        let grouped = Dictionary(grouping: metrics, by: { $0.key.group })

        return ResultMetricGroup.allCases.map { group in
            ResultPerformanceCard(
                group: group,
                title: group.displayTitle,
                subtitle: group.subtitle,
                metrics: grouped[group] ?? []
            )
        }
    }

    private static func makeImprovementFindings(from result: AnalysisResult) -> [ResultFinding] {
        let sourceIssues = result.freeIssues.isEmpty
            ? [
                AnalysisIssue(
                    title: "动作稳定性低置信",
                    detail: "当前分析需要更多视频样本确认动作中的关键节点。",
                    severityLabel: "重点关注"
                )
            ]
            : result.freeIssues

        return Array(sourceIssues.prefix(2).enumerated()).map { indexedIssue in
            let (index, issue) = indexedIssue

            return ResultFinding(
                trigger: index == 0 ? .fail : .poor,
                title: issue.title,
                detail: issue.detail
            )
        }
    }

    private static func makePendingFindings(from metrics: [ResultMetric]) -> [ResultFinding] {
        guard let lowConfidenceMetric = metrics.first(where: { $0.confidence == .low }) else {
            return []
        }

        switch lowConfidenceMetric.key {
        case .passReceiveGapS:
            return [
                ResultFinding(
                    trigger: .lowConfidence,
                    title: "传接间隔仅作参考",
                    detail: "当前传接间隔更适合结合更长片段确认，避免把短时波动当成稳定结论。"
                )
            ]
        case .nextActionReadiness:
            return [
                ResultFinding(
                    trigger: .lowConfidence,
                    title: "下一动作准备度仅作参考",
                    detail: "当前准备度判断更偏向整体趋势，建议结合更多样本重新判断。"
                )
            ]
        default:
            return [
                ResultFinding(
                    trigger: .lowConfidence,
                    title: "\(lowConfidenceMetric.key.displayTitle)低置信",
                    detail: "该指标当前置信度偏低，建议结合更多视频重新判断。"
                )
            ]
        }
    }

    private static func makeFallbackDebug(from result: AnalysisResult, metrics: [ResultMetric]) -> ResultDebugSnapshot {
        let continuityScore = metrics.first(where: { $0.key == .sequenceContinuityScore })?.currentValue ?? "--"

        return ResultDebugSnapshot(
            matchedKey: [],
            weight: [],
            sourceClass: [],
            rawActionCandidates: [result.motionType, "pass_receive_sequence"],
            candidateScores: [
                "\(result.motionType): \(result.score)",
                "sequence_continuity_score: \(continuityScore)"
            ],
            sequenceUpgradeReason: result.summary,
            metricDebug: metrics.map {
                "\($0.key.rawValue)=\($0.currentValue) | band=\($0.band) | confidence=\($0.confidence.displayLabel)"
            },
            qualityGate: [
                "score_gate=\(result.score >= 80 ? "pass" : "review")",
                "confidence_gate=\(metrics.contains(where: { $0.confidence == .low }) ? "low_confidence" : "high_confidence")"
            ]
        )
    }

    private static func gradeLabel(for score: Int) -> String {
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

    private static func bandForHigherBetter(_ value: Double, thresholds: [Double], labels: [String]) -> String {
        guard thresholds.count == 2, labels.count == 3 else {
            return labels.first ?? ""
        }

        if value >= thresholds[0] {
            return labels[0]
        }
        if value >= thresholds[1] {
            return labels[1]
        }
        return labels[2]
    }

    private static func bandForLowerBetter(_ value: Double, thresholds: [Double], labels: [String]) -> String {
        guard thresholds.count == 2, labels.count == 3 else {
            return labels.first ?? ""
        }

        if value <= thresholds[0] {
            return labels[0]
        }
        if value <= thresholds[1] {
            return labels[1]
        }
        return labels[2]
    }

    private static func formatMeters(_ value: Double) -> String {
        String(format: "%.2f m", value)
    }

    private static func formatSeconds(_ value: Double) -> String {
        String(format: "%.2f s", value)
    }

    private static func formatPercent(_ value: Double) -> String {
        String(format: "%.0f%%", value)
    }
}
