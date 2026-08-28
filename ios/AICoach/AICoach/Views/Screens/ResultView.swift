import SwiftUI

struct ResultView: View {
    @EnvironmentObject private var appState: AppState
    let recordID: UUID

    private var record: AnalysisRecord? {
        appState.record(for: recordID)
    }

    var body: some View {
        Group {
            if let record {
                ScrollView(showsIndicators: false) {
                    resultContent(for: record)
                    .padding(20)
                    .padding(.bottom, 40)
                }
            } else {
                VStack(spacing: 16) {
                    Text("未找到分析记录")
                        .font(.title3.weight(.semibold))
                    SecondaryButton(title: "返回首页") {
                        appState.dismissToHome()
                    }
                    .padding(.horizontal, 24)
                }
            }
        }
        .background(AppTheme.background.ignoresSafeArea())
        .navigationTitle("分析结果")
        .navigationBarTitleDisplayMode(.inline)
    }

    @ViewBuilder
    private func resultContent(for record: AnalysisRecord) -> some View {
        if record.isAnalysisAnomaly {
            anomalyResultLayout(record)
        } else if record.isAnalysisFailure {
            failureResultLayout(record)
        } else if record.score.needsConfirmation || record.reportState == .needsConfirmation {
            confirmationResultLayout(record)
        } else if let sequenceResult = record.sequenceResult {
            sequenceResultLayout(record, result: sequenceResult)
        } else {
            legacyResultLayout(record)
        }
    }

    private func confirmationResultLayout(_ record: AnalysisRecord) -> some View {
        VStack(alignment: .leading, spacing: 22) {
            headerSection(record)
            analysisNoticeSection(record)
            confirmationOverviewSection(record)
            confirmationCandidatesSection(record)
            confirmationReasonsSection(record)
            summarySection(record)
            qualitySection(record)
            actionSection
        }
    }

    private func legacyResultLayout(_ record: AnalysisRecord) -> some View {
        VStack(alignment: .leading, spacing: 22) {
            headerSection(record)
            analysisNoticeSection(record)
            scoreOverviewSection(record)
            metricsSection(record)
            summarySection(record)
            findingsSection(record)
            suggestionsSection(record)
            timestampsSection(record)
            qualitySection(record)
            actionSection
        }
    }

    private func sequenceResultLayout(_ record: AnalysisRecord, result: PassReceiveSequenceResult) -> some View {
        VStack(alignment: .leading, spacing: 18) {
            headerSection(record)
            analysisNoticeSection(record)
            sequenceSummarySection(record, result: result)

            VStack(spacing: 14) {
                sequenceModuleCard(
                    title: "传球表现",
                    subtitle: "Pass",
                    metrics: result.passMetrics
                )

                sequenceModuleCard(
                    title: "接球表现",
                    subtitle: "Receive",
                    metrics: result.receiveMetrics
                )

                sequenceModuleCard(
                    title: "序列衔接",
                    subtitle: "Sequence",
                    metrics: result.sequenceMetrics
                )
            }

            sequencePromptSection(result)

            #if DEBUG
            sequenceDebugSection(result)
            #endif

            actionSection
        }
    }

    private func failureResultLayout(_ record: AnalysisRecord) -> some View {
        VStack(alignment: .leading, spacing: 22) {
            headerSection(record)
            failureCard(record)
            #if DEBUG
            debugStatusCard(record)
            #endif
            failureActionSection(record)
        }
    }

    private func anomalyResultLayout(_ record: AnalysisRecord) -> some View {
        VStack(alignment: .leading, spacing: 22) {
            headerSection(record)
            anomalyCard(record)
            #if DEBUG
            debugStatusCard(record)
            #endif
            failureActionSection(record)
        }
    }

    private func confirmationOverviewSection(_ record: AnalysisRecord) -> some View {
        FrostedCard(padding: 20) {
            SectionLabel(
                title: "结果待确认",
                subtitle: "当前动作类型仍待确认，先展示候选与原因"
            )

            HStack(alignment: .top, spacing: 16) {
                Image(systemName: record.score.needsConfirmation ? "questionmark.circle.fill" : record.reportState.symbol)
                    .font(.title2.weight(.semibold))
                    .foregroundStyle(AppTheme.warning)
                    .frame(width: 46, height: 46)
                    .background(
                        Circle()
                            .fill(AppTheme.warning.opacity(0.16))
                    )

                VStack(alignment: .leading, spacing: 10) {
                    HStack(alignment: .top) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("当前结果先作为参考")
                                .font(.title3.weight(.semibold))
                            Text("动作候选已输出，但暂不展示正式等级。")
                                .font(.subheadline)
                                .foregroundStyle(AppTheme.muted)
                        }

                        Spacer()

                        StatusPill(text: "待确认", tint: AppTheme.warning)
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        ForEach(confirmationBullets(for: record), id: \.self) { bullet in
                            HStack(alignment: .top, spacing: 10) {
                                Circle()
                                    .fill(AppTheme.warning)
                                    .frame(width: 6, height: 6)
                                    .padding(.top, 6)
                                Text(bullet)
                                    .font(.subheadline)
                                    .foregroundStyle(.white.opacity(0.94))
                            }
                        }
                    }
                }
            }
        }
    }

    private func confirmationBullets(for record: AnalysisRecord) -> [String] {
        let reasonBullets = record.score.uncertaintyReasons.map { uncertaintyReasonText($0) }
        if !reasonBullets.isEmpty {
            return Array(reasonBullets.prefix(3))
        }

        return [
            "候选动作接近",
            "置信度不足",
            "建议补充更清晰视频"
        ]
    }

    private func confirmationCandidatesSection(_ record: AnalysisRecord) -> some View {
        FrostedCard {
            SectionLabel(
                title: "候选动作",
                subtitle: "当前不直接下结论，先展示更接近的候选"
            )

            if record.score.actionCandidates.isEmpty {
                Text("当前没有稳定的候选动作。")
                    .font(.subheadline)
                    .foregroundStyle(AppTheme.muted)
            } else {
                VStack(spacing: 10) {
                    ForEach(Array(record.score.actionCandidates.prefix(3))) { candidate in
                        HStack(alignment: .top, spacing: 12) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(candidate.title)
                                    .font(.headline.weight(.semibold))
                                Text(candidate.template.isEmpty ? candidate.action : candidate.template)
                                    .font(.caption)
                                    .foregroundStyle(AppTheme.muted)
                            }

                            Spacer(minLength: 12)

                            VStack(alignment: .trailing, spacing: 6) {
                                StatusPill(text: String(format: "%.0f%%", candidate.score * 100.0), tint: AppTheme.accent)
                                Text(candidate.sources.joined(separator: " · "))
                                    .font(.caption2)
                                    .foregroundStyle(AppTheme.muted)
                                    .multilineTextAlignment(.trailing)
                            }
                        }
                        .padding(16)
                        .background(
                            RoundedRectangle(cornerRadius: 18, style: .continuous)
                                .fill(Color.white.opacity(0.05))
                        )
                    }
                }
            }
        }
    }

    private func confirmationReasonsSection(_ record: AnalysisRecord) -> some View {
        FrostedCard {
            SectionLabel(
                title: "不确定原因",
                subtitle: "为什么当前先不强判"
            )

            if record.score.uncertaintyReasons.isEmpty {
                Text("当前没有明显的不确定原因。")
                    .font(.subheadline)
                    .foregroundStyle(AppTheme.muted)
            } else {
                VStack(alignment: .leading, spacing: 10) {
                    ForEach(record.score.uncertaintyReasons, id: \.self) { reason in
                        HStack(alignment: .top, spacing: 10) {
                            Circle()
                                .fill(AppTheme.warning)
                                .frame(width: 7, height: 7)
                                .padding(.top, 7)
                            Text(uncertaintyReasonText(reason))
                                .font(.subheadline)
                                .foregroundStyle(.white.opacity(0.92))
                        }
                        .padding(14)
                        .background(
                            RoundedRectangle(cornerRadius: 16, style: .continuous)
                                .fill(Color.white.opacity(0.05))
                        )
                    }
                }
            }
        }
    }

    @ViewBuilder
    private func analysisNoticeSection(_ record: AnalysisRecord) -> some View {
        if record.isAnalysisPartial || record.routeMismatchMessage != nil || record.analysisWindowText != nil {
            FrostedCard {
                HStack(alignment: .top, spacing: 12) {
                    Image(systemName: record.analysisWindowText != nil ? "viewfinder" : (record.isAnalysisPartial ? "clock.arrow.circlepath" : "exclamationmark.triangle.fill"))
                        .foregroundStyle(record.analysisWindowText != nil ? AppTheme.success : (record.isAnalysisPartial ? AppTheme.accent : AppTheme.warning))
                        .frame(width: 30, height: 30)
                        .background(Circle().fill((record.analysisWindowText != nil ? AppTheme.success : (record.isAnalysisPartial ? AppTheme.accent : AppTheme.warning)).opacity(0.16)))

                    VStack(alignment: .leading, spacing: 6) {
                        Text(record.analysisWindowText != nil ? "已自动定位动作片段" : (record.isAnalysisPartial ? "快速分析" : "路由提示"))
                            .font(.headline.weight(.semibold))
                        Text(record.analysisWindowText ?? record.routeMismatchMessage ?? "本次分析采用了快速模式，结果会更保守。")
                            .font(.subheadline)
                            .foregroundStyle(AppTheme.muted)
                        if let routeMessage = record.routeMismatchMessage, record.analysisWindowText != nil {
                            Text(routeMessage)
                                .font(.footnote)
                                .foregroundStyle(.white.opacity(0.88))
                        }
                    }

                    Spacer(minLength: 0)
                }
            }
        }
    }

    private func failureCard(_ record: AnalysisRecord) -> some View {
        FrostedCard {
            HStack(alignment: .top, spacing: 14) {
                Image(systemName: record.failureReason == .analysisTimeout ? "clock.badge.exclamationmark" : (record.failureReason == .videoTooLong ? "timer.square.fill" : "exclamationmark.triangle.fill"))
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(failureTint(for: record))
                    .frame(width: 46, height: 46)
                    .background(
                        Circle()
                            .fill(failureTint(for: record).opacity(0.16))
                    )

                VStack(alignment: .leading, spacing: 10) {
                    HStack(alignment: .top) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(failureTitle(for: record))
                                .font(.title3.weight(.semibold))
                            Text(failureBody(for: record))
                                .font(.subheadline)
                                .foregroundStyle(AppTheme.muted)
                        }

                        Spacer()

                        StatusPill(text: record.failureReasonText, tint: failureTint(for: record))
                    }

                    if let routeMessage = record.routeMismatchMessage, !routeMessage.isEmpty {
                        Text(routeMessage)
                            .font(.footnote)
                            .foregroundStyle(.white.opacity(0.88))
                            .padding(12)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(
                                RoundedRectangle(cornerRadius: 14, style: .continuous)
                                    .fill(Color.white.opacity(0.05))
                            )
                    }
                }
            }
        }
    }

    private func anomalyCard(_ record: AnalysisRecord) -> some View {
        FrostedCard {
            HStack(alignment: .top, spacing: 14) {
                Image(systemName: "exclamationmark.shield.fill")
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(AppTheme.warning)
                    .frame(width: 46, height: 46)
                    .background(
                        Circle()
                            .fill(AppTheme.warning.opacity(0.16))
                    )

                VStack(alignment: .leading, spacing: 10) {
                    HStack(alignment: .top) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("本次结果存在异常，请重新分析")
                                .font(.title3.weight(.semibold))
                            Text(record.failureMessageText.isEmpty ? "后端路由或结果一致性检测未通过。" : record.failureMessageText)
                                .font(.subheadline)
                                .foregroundStyle(AppTheme.muted)
                        }

                        Spacer()

                        StatusPill(text: "结果异常", tint: AppTheme.warning)
                    }

                    if let routeMessage = record.routeMismatchMessage, !routeMessage.isEmpty {
                        Text(routeMessage)
                            .font(.footnote)
                            .foregroundStyle(.white.opacity(0.88))
                            .padding(12)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(
                                RoundedRectangle(cornerRadius: 14, style: .continuous)
                                    .fill(Color.white.opacity(0.05))
                            )
                    }
                }
            }
        }
    }

    private func failureActionSection(_ record: AnalysisRecord) -> some View {
        VStack(spacing: 12) {
            PrimaryButton(title: "继续重试当前视频", subtitle: "保持当前选择重新分析") {
                appState.retryCurrentAnalysis()
            }

            SecondaryButton(title: "重新选择视频") {
                appState.reselectVideo()
            }

            SecondaryButton(title: "返回首页") {
                appState.dismissToHome()
            }
        }
    }

    #if DEBUG
    private func debugStatusCard(_ record: AnalysisRecord) -> some View {
        FrostedCard {
            SectionLabel(
                title: "调试信息",
                subtitle: "routeDebugText / failureReasonText / debugContext"
            )

            VStack(alignment: .leading, spacing: 10) {
                debugKeyValue("analysisStatus", record.analysisStatus.rawValue)
                debugKeyValue("integrityState", record.runtimeState.integrityState.rawValue)
                debugKeyValue("failureReasonText", record.failureReasonText)
                debugKeyValue("routeDebugText", record.routeDebugText)
                debugKeyValue("failureMessage", record.failureMessageText)
                debugKeyValue("selectedAction", record.selectedActionName)
                debugKeyValue("systemActionSuggestion", record.systemActionSuggestionName)
                debugKeyValue("analysisRoutedBy", record.analysisRoutedBy)
                debugKeyValue("routedAnalyzer", record.routedAnalyzer)
                debugKeyValue("videoDurationSeconds", String(format: "%.1f", record.runtimeState.videoDurationSeconds))
                debugKeyValue("frameCount", "\(record.runtimeState.frameCount)")
                debugKeyValue("sampledFrameCount", "\(record.runtimeState.sampledFrameCount)")
                debugKeyValue("fastModeEnabled", record.runtimeState.fastModeEnabled ? "true" : "false")
                debugKeyValue("longVideoLocalized", record.runtimeState.longVideoLocalized ? "true" : "false")
                debugKeyValue("candidateWindowCount", "\(record.runtimeState.candidateWindowCount)")
                debugKeyValue("selectedWindowIndex", record.runtimeState.selectedWindowIndex.map(String.init) ?? "—")
                if let start = record.runtimeState.selectedWindowStartSeconds, let end = record.runtimeState.selectedWindowEndSeconds {
                    debugKeyValue("selectedWindowRange", String(format: "%.1fs - %.1fs", start, end))
                }

                if let debugContext = record.debugContext {
                    debugKeyValue("warnings", debugContext.warnings.joined(separator: " · "))
                }
            }
        }
    }
#endif

    private func sequenceSummarySection(_ record: AnalysisRecord, result: PassReceiveSequenceResult) -> some View {
        FrostedCard(padding: 20) {
            SectionLabel(
                title: "结果摘要",
                subtitle: "Score overview"
            )

            HStack(alignment: .top, spacing: 16) {
                VStack(alignment: .leading, spacing: 12) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(result.actionDisplayName)
                            .font(.title2.weight(.bold))
                        HStack(spacing: 8) {
                            StatusPill(text: "\(Int(round(result.overallScore))) 分", tint: AppTheme.resultColor(for: record.score.level))
                            StatusPill(text: result.levelLabel, tint: AppTheme.resultColor(for: record.score.level))
                        }
                    }

                    Text(result.summary)
                        .font(.body)
                        .foregroundStyle(.white.opacity(0.94))
                        .lineLimit(4)
                }

                Spacer(minLength: 10)

                ScoreRingView(
                    score: Int(round(result.overallScore)),
                    level: record.score.level,
                    labelOverride: result.levelLabel
                )
            }
        }
    }

    private func sequenceModuleCard(
        title: String,
        subtitle: String,
        metrics: [SequenceMetricSummary]
    ) -> some View {
        FrostedCard {
            SectionLabel(title: title, subtitle: subtitle)

            VStack(spacing: 12) {
                ForEach(metrics) { metric in
                    sequenceMetricRow(metric)
                }
            }
        }
    }

    private func sequenceMetricRow(_ metric: SequenceMetricSummary) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top, spacing: 10) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(metric.title)
                        .font(.subheadline.weight(.semibold))
                    Text(metric.detail)
                        .font(.caption)
                        .foregroundStyle(AppTheme.muted)
                        .lineLimit(2)
                }

                Spacer(minLength: 0)

                StatusPill(
                    text: sequenceBadgeText(for: metric),
                    tint: sequenceBadgeTint(for: metric)
                )
            }

            Text(metric.valueText)
                .font(.system(size: 24, weight: .bold, design: .rounded))
                .foregroundStyle(sequenceMetricTint(for: metric))
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(Color.white.opacity(0.05))
        )
    }

    private func sequencePromptSection(_ result: PassReceiveSequenceResult) -> some View {
        let confirmationItems = sequenceConfirmationItems(from: result)

        return ViewThatFits(in: .horizontal) {
            HStack(alignment: .top, spacing: 14) {
                sequenceConfirmationCard(items: confirmationItems)
                sequenceAdviceCard(messages: result.feedbackMessages)
            }

            VStack(alignment: .leading, spacing: 14) {
                sequenceConfirmationCard(items: confirmationItems)
                sequenceAdviceCard(messages: result.feedbackMessages)
            }
        }
    }

    private func sequenceConfirmationCard(items: [SequenceMetricSummary]) -> some View {
        FrostedCard {
            SectionLabel(
                title: "待确认项",
                subtitle: "低置信度结果先放这里，不当作错误"
            )

            if items.isEmpty {
                Text("当前没有待确认项。")
                    .font(.subheadline)
                    .foregroundStyle(AppTheme.muted)
            } else {
                VStack(alignment: .leading, spacing: 12) {
                    ForEach(items) { metric in
                        VStack(alignment: .leading, spacing: 6) {
                            HStack {
                                Text(metric.title)
                                    .font(.subheadline.weight(.semibold))
                                Spacer()
                                StatusPill(text: "低置信度", tint: AppTheme.warning)
                            }
                            Text(metric.detail)
                                .font(.caption)
                                .foregroundStyle(AppTheme.muted)
                        }
                        .padding(14)
                        .background(
                            RoundedRectangle(cornerRadius: 16, style: .continuous)
                                .fill(Color.white.opacity(0.05))
                        )
                    }
                }
            }
        }
    }

    private func sequenceAdviceCard(messages: [String]) -> some View {
        FrostedCard {
            SectionLabel(
                title: "训练建议",
                subtitle: "feedback_messages"
            )

            if messages.isEmpty {
                Text("当前没有训练建议。")
                    .font(.subheadline)
                    .foregroundStyle(AppTheme.muted)
            } else {
                VStack(alignment: .leading, spacing: 12) {
                    ForEach(Array(messages.enumerated()), id: \.offset) { _, message in
                        HStack(alignment: .top, spacing: 10) {
                            Circle()
                                .fill(AppTheme.accent)
                                .frame(width: 7, height: 7)
                                .padding(.top, 7)
                            Text(message)
                                .font(.subheadline)
                                .foregroundStyle(.white.opacity(0.92))
                        }
                        .padding(14)
                        .background(
                            RoundedRectangle(cornerRadius: 16, style: .continuous)
                                .fill(Color.white.opacity(0.05))
                        )
                    }
                }
            }
        }
    }

#if DEBUG
    @State private var debugExpanded = false

    private func sequenceDebugSection(_ result: PassReceiveSequenceResult) -> some View {
        DisclosureGroup(isExpanded: $debugExpanded) {
            VStack(alignment: .leading, spacing: 14) {
                debugBlock(
                    title: "raw_action_candidates",
                    subtitle: "候选动作与来源",
                    content: AnyView(
                        VStack(spacing: 10) {
                            ForEach(result.rawActionCandidates) { candidate in
                                VStack(alignment: .leading, spacing: 8) {
                                    HStack(alignment: .top) {
                                        Text(candidate.action)
                                            .font(.subheadline.weight(.semibold))
                                        Spacer()
                                        StatusPill(
                                            text: String(format: "%.3f", candidate.score),
                                            tint: AppTheme.accent
                                        )
                                    }
                                    Text(candidate.sources.joined(separator: " · "))
                                        .font(.caption)
                                        .foregroundStyle(AppTheme.muted)
                                }
                                .padding(14)
                                .background(
                                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                                        .fill(Color.white.opacity(0.05))
                                )
                            }
                        }
                    )
                )

                debugBlock(
                    title: "candidate_scores",
                    subtitle: "候选得分",
                    content: AnyView(
                        LazyVGrid(
                            columns: [
                                GridItem(.flexible(), spacing: 12),
                                GridItem(.flexible(), spacing: 12)
                            ],
                            spacing: 12
                        ) {
                            ForEach(result.candidateScores.sorted(by: { $0.key < $1.key }), id: \.key) { item in
                                VStack(alignment: .leading, spacing: 6) {
                                    Text(item.key)
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(AppTheme.muted)
                                    Text(String(format: "%.3f", item.value))
                                        .font(.headline.weight(.bold))
                                }
                                .padding(14)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(
                                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                                        .fill(Color.white.opacity(0.05))
                                )
                            }
                        }
                    )
                )

                debugBlock(
                    title: "metric_debug",
                    subtitle: "关键指标调试信息",
                    content: AnyView(
                        VStack(spacing: 10) {
                            ForEach(result.metricDebug.keys.sorted(), id: \.self) { key in
                                if let field = result.metricDebug[key] {
                                    debugMetricCard(key: key, field: field)
                                }
                            }
                        }
                    )
                )

                debugBlock(
                    title: "quality_gate",
                    subtitle: "质量门控",
                    content: AnyView(
                        sequenceQualityGateCard(result.qualityGate)
                    )
                )
            }
            .padding(.top, 12)
        } label: {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("开发调试")
                        .font(.headline.weight(.semibold))
                    Text("raw_action_candidates / candidate_scores / metric_debug / quality_gate")
                        .font(.caption)
                        .foregroundStyle(AppTheme.muted)
                }

                Spacer()

                StatusPill(text: "DEBUG", tint: AppTheme.warning)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(18)
        .background(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .fill(AppTheme.cardFill)
                .overlay(
                    RoundedRectangle(cornerRadius: 24, style: .continuous)
                        .stroke(AppTheme.cardStroke, lineWidth: 1)
                )
        )
    }

    private func debugBlock(title: String, subtitle: String, content: AnyView) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.subheadline.weight(.semibold))
                Text(subtitle)
                    .font(.caption)
                    .foregroundStyle(AppTheme.muted)
            }

            content
        }
    }

    private func debugMetricCard(key: String, field: SequenceMetricDebugField) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(key)
                    .font(.subheadline.weight(.semibold))
                Spacer()
                if let resolved = field.resolved {
                    StatusPill(text: resolved ? "resolved" : "unresolved", tint: resolved ? AppTheme.success : AppTheme.warning)
                }
            }

            VStack(alignment: .leading, spacing: 6) {
                if let value = field.value {
                    debugKeyValue("value", formatDouble(value))
                }
                if let lowConfidence = field.lowConfidence {
                    debugKeyValue("lowConfidence", lowConfidence ? "true" : "false")
                }
                if let confidence = field.confidence {
                    debugKeyValue("confidence", formatDouble(confidence))
                }
                if let startTime = field.startTime {
                    debugKeyValue("startTime", formatDouble(startTime))
                }
                if let endTime = field.endTime {
                    debugKeyValue("endTime", formatDouble(endTime))
                }
                if let startEvent = field.startEvent {
                    debugKeyValue("startEvent", startEvent)
                }
                if let endEvent = field.endEvent {
                    debugKeyValue("endEvent", endEvent)
                }
                if let eventSource = field.eventSource {
                    debugKeyValue("eventSource", eventSource)
                }
                if let fallbackToVideoEnd = field.fallbackToVideoEnd {
                    debugKeyValue("fallbackToVideoEnd", fallbackToVideoEnd ? "true" : "false")
                }
                if let rawValue = field.rawValue {
                    debugKeyValue("rawValue", formatDouble(rawValue))
                }
                if let score = field.score {
                    debugKeyValue("score", formatDouble(score))
                }
                if let band = field.band {
                    debugKeyValue("band", band)
                }
                if let direction = field.direction {
                    debugKeyValue("direction", direction)
                }
                if let thresholds = field.thresholds, !thresholds.isEmpty {
                    debugKeyValue("thresholds", thresholds.map { "\($0.key)=\(formatDouble($0.value))" }.sorted().joined(separator: ", "))
                }
                if let logic = field.logic, !logic.isEmpty {
                    debugKeyValue("logic", logic.map { logicStepText($0) }.joined(separator: " | "))
                }
                if let contactDetected = field.contactDetected {
                    debugKeyValue("contactDetected", contactDetected ? "true" : "false")
                }
                if let receiveContactDetected = field.receiveContactDetected {
                    debugKeyValue("receiveContactDetected", receiveContactDetected ? "true" : "false")
                }
                if let stabilizationDetected = field.stabilizationDetected {
                    debugKeyValue("stabilizationDetected", stabilizationDetected ? "true" : "false")
                }
                if let usedProxyLocalWindow = field.usedProxyLocalWindow {
                    debugKeyValue("usedProxyLocalWindow", usedProxyLocalWindow ? "true" : "false")
                }
                if let usedVideoEndTime = field.usedVideoEndTime {
                    debugKeyValue("usedVideoEndTime", usedVideoEndTime ? "true" : "false")
                }
                if let passExecutionLowConfidence = field.passExecutionLowConfidence {
                    debugKeyValue("passExecutionLowConfidence", passExecutionLowConfidence ? "true" : "false")
                }
                if let passReceiveGapLowConfidence = field.passReceiveGapLowConfidence {
                    debugKeyValue("passReceiveGapLowConfidence", passReceiveGapLowConfidence ? "true" : "false")
                }
                if let receiveStabilizationLowConfidence = field.receiveStabilizationLowConfidence {
                    debugKeyValue("receiveStabilizationLowConfidence", receiveStabilizationLowConfidence ? "true" : "false")
                }
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(Color.white.opacity(0.05))
        )
    }

    private func sequenceQualityGateCard(_ qualityGate: SequenceQualityGate) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(qualityGate.actionName)
                        .font(.headline.weight(.semibold))
                    Text(qualityGate.reshootHint)
                        .font(.caption)
                        .foregroundStyle(AppTheme.muted)
                }

                Spacer()

                StatusPill(text: qualityGate.passed ? "passed" : "failed", tint: qualityGate.passed ? AppTheme.success : AppTheme.danger)
            }

            HStack(spacing: 8) {
                StatusPill(text: "quality_status: \(qualityGate.qualityStatus)", tint: AppTheme.accent)
                StatusPill(text: qualityGate.shouldReshoot ? "should_reshoot" : "no_reshoot", tint: qualityGate.shouldReshoot ? AppTheme.warning : AppTheme.success)
            }

            debugKeyValue("allowMicroTechniqueScore", qualityGate.allowMicroTechniqueScore ? "true" : "false")
            debugKeyValue("hideMicroTechniqueScore", qualityGate.hideMicroTechniqueScore ? "true" : "false")

            if !qualityGate.thresholds.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("thresholds")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(AppTheme.muted)
                    Text(qualityGate.thresholds.map { "\($0.key)=\(formatDouble($0.value))" }.sorted().joined(separator: ", "))
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.9))
                }
            }

            if !qualityGate.observed.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("observed")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(AppTheme.muted)
                    LazyVGrid(
                        columns: [
                            GridItem(.flexible(), spacing: 10),
                            GridItem(.flexible(), spacing: 10)
                        ],
                        spacing: 10
                    ) {
                        ForEach(qualityGate.observed.sorted(by: { $0.key < $1.key }), id: \.key) { item in
                            VStack(alignment: .leading, spacing: 4) {
                                Text(item.key)
                                    .font(.caption2.weight(.semibold))
                                    .foregroundStyle(AppTheme.muted)
                                Text(formatDouble(item.value))
                                    .font(.subheadline.weight(.semibold))
                            }
                            .padding(12)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(
                                RoundedRectangle(cornerRadius: 14, style: .continuous)
                                    .fill(Color.white.opacity(0.04))
                            )
                        }
                    }
                }
            }

            if !qualityGate.triggeredRules.isEmpty {
                debugKeyValue("triggeredRules", qualityGate.triggeredRules.joined(separator: ", "))
            }
            if !qualityGate.failReasons.isEmpty {
                debugKeyValue("failReasons", qualityGate.failReasons.joined(separator: " | "))
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(Color.white.opacity(0.05))
        )
    }

    private func debugKeyValue(_ key: String, _ value: String) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Text(key)
                .font(.caption.weight(.semibold))
                .foregroundStyle(AppTheme.muted)
                .frame(width: 150, alignment: .leading)
            Text(value)
                .font(.caption)
                .foregroundStyle(.white.opacity(0.90))
            Spacer(minLength: 0)
        }
    }
#endif

    private func headerSection(_ record: AnalysisRecord) -> some View {
        FrostedCard(padding: 20) {
            SectionLabel(
                title: record.isAnalysisFailure ? "分析失败" : (record.isAnalysisAnomaly ? "结果异常" : "结果回顾"),
                subtitle: record.isAnalysisFailure ? "Analysis Failure" : (record.isAnalysisAnomaly ? "Integrity Check" : "Result Review")
            )

            HStack(alignment: .top, spacing: 14) {
                VStack(alignment: .leading, spacing: 8) {
                    Text(record.displayActionDisplayName)
                        .font(.title2.weight(.bold))
                    Text(record.goal.englishTitle)
                        .font(.subheadline)
                        .foregroundStyle(AppTheme.muted)
                    Text(record.clipName)
                        .font(.caption)
                        .foregroundStyle(AppTheme.muted)
                }

                Spacer(minLength: 12)

                VStack(alignment: .trailing, spacing: 8) {
                    StatusPill(
                        text: record.isAnalysisFailure || record.isAnalysisAnomaly ? record.failureReasonText : record.reportTagText,
                        tint: record.isAnalysisFailure ? failureTint(for: record) : (record.isAnalysisAnomaly ? AppTheme.warning : mainTint(for: record.reportState))
                    )
                    Text(record.isAnalysisFailure || record.isAnalysisAnomaly ? record.failureMessageText : (record.analysisWindowText != nil ? "已自动定位动作片段进行分析。" : record.reportState.subtitle))
                        .font(.caption)
                        .foregroundStyle(AppTheme.muted)
                        .multilineTextAlignment(.trailing)
                }
            }
        }
    }

    private func scoreOverviewSection(_ record: AnalysisRecord) -> some View {
        ViewThatFits(in: .horizontal) {
            HStack(alignment: .top, spacing: 14) {
                mainOutcomeCard(record)
                subscoreColumn(record)
            }

            VStack(alignment: .leading, spacing: 14) {
                mainOutcomeCard(record)
                subscoreColumn(record)
            }
        }
    }

    private func mainOutcomeCard(_ record: AnalysisRecord) -> some View {
        FrostedCard(padding: 20) {
            if record.shouldShowFormalScore {
                HStack(alignment: .top, spacing: 16) {
                    ScoreRingView(score: record.score.overall, level: record.score.level)

                    VStack(alignment: .leading, spacing: 10) {
                        HStack(alignment: .top) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("正式总分")
                                    .font(.subheadline.weight(.semibold))
                                Text("\(record.score.overall)")
                                    .font(.system(size: 30, weight: .bold, design: .rounded))
                                    .foregroundStyle(AppTheme.resultColor(for: record.score.level))
                            }

                            Spacer()

                            StatusPill(text: record.gradeTitle, tint: AppTheme.resultColor(for: record.score.level))
                        }

                        Text(record.scoreSubtitle)
                            .font(.subheadline)
                            .foregroundStyle(AppTheme.muted)
                            .lineLimit(2)

                        Text(record.summary)
                            .font(.body)
                            .foregroundStyle(.white.opacity(0.94))
                            .lineLimit(3)
                    }
                }
            } else {
                HStack(alignment: .top, spacing: 16) {
                    Image(systemName: record.reportState.symbol)
                        .font(.title2.weight(.semibold))
                        .foregroundStyle(mainTint(for: record.reportState))
                        .frame(width: 46, height: 46)
                        .background(
                            Circle()
                                .fill(mainTint(for: record.reportState).opacity(0.16))
                        )

                    VStack(alignment: .leading, spacing: 10) {
                        HStack(alignment: .top) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(record.reportState.title)
                                    .font(.title3.weight(.semibold))
                                Text(record.reportState.subtitle)
                                    .font(.subheadline)
                                    .foregroundStyle(AppTheme.muted)
                            }

                            Spacer()

                            StatusPill(text: record.reportTagText, tint: mainTint(for: record.reportState))
                        }

                        VStack(alignment: .leading, spacing: 8) {
                            ForEach(record.reportState.bullets, id: \.self) { bullet in
                                HStack(alignment: .top, spacing: 10) {
                                    Circle()
                                        .fill(mainTint(for: record.reportState))
                                        .frame(width: 6, height: 6)
                                        .padding(.top, 6)
                                    Text(bullet)
                                        .font(.subheadline)
                                        .foregroundStyle(.white.opacity(0.94))
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    private func subscoreColumn(_ record: AnalysisRecord) -> some View {
        VStack(spacing: 14) {
            ResultSubscoreCard(
                title: "技术执行",
                value: record.shouldShowFormalScore ? record.score.technique : nil,
                tint: scoreTint(for: .technique, record: record),
                note: record.shouldShowFormalScore ? "触球、发力和收尾的整体质量" : record.reportState.subtitle,
                badgeText: record.shouldShowFormalScore ? nil : record.reportTagText
            )

            ResultSubscoreCard(
                title: "控制稳定",
                value: record.shouldShowFormalScore ? record.score.control : nil,
                tint: scoreTint(for: .control, record: record),
                note: record.shouldShowFormalScore ? "身体控制与出球一致性" : record.reportState.subtitle,
                badgeText: record.shouldShowFormalScore ? nil : record.reportTagText
            )

            ResultSubscoreCard(
                title: "动作安全",
                value: record.shouldShowFormalScore ? record.score.safety : nil,
                tint: scoreTint(for: .safety, record: record),
                note: record.shouldShowFormalScore ? "动作舒展与稳定释放" : record.reportState.subtitle,
                badgeText: record.shouldShowFormalScore ? nil : record.reportTagText
            )
        }
    }

    private func summarySection(_ record: AnalysisRecord) -> some View {
        FrostedCard {
            SectionLabel(
                title: "一句话总结",
                subtitle: "Summary"
            )
            Text(record.displaySummary)
                .font(.body)
                .foregroundStyle(.white.opacity(0.95))
        }
    }

    private func metricsSection(_ record: AnalysisRecord) -> some View {
        FrostedCard {
            SectionLabel(
                title: "阈值指标",
                subtitle: "Triggered metrics"
            )

            VStack(alignment: .leading, spacing: 14) {
                if record.analysisMetrics.isEmpty {
                    Text("当前没有可展示的阈值指标。")
                        .font(.subheadline)
                        .foregroundStyle(AppTheme.muted)
                } else {
                    LazyVGrid(
                        columns: [
                            GridItem(.flexible(), spacing: 12),
                            GridItem(.flexible(), spacing: 12)
                        ],
                        spacing: 12
                    ) {
                        ForEach(record.analysisMetrics) { metric in
                            metricCard(metric)
                        }
                    }
                }

                if !record.triggeredRules.isEmpty {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("triggered_rules")
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(AppTheme.text)
                        VStack(spacing: 10) {
                            ForEach(record.triggeredRules) { rule in
                                ruleRow(rule)
                            }
                        }
                    }
                }

                if !record.failReasons.isEmpty {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("fail_reasons")
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(AppTheme.text)
                        VStack(alignment: .leading, spacing: 8) {
                            ForEach(Array(record.failReasons.enumerated()), id: \.offset) { _, reason in
                                HStack(alignment: .top, spacing: 8) {
                                    Circle()
                                        .fill(AppTheme.warning)
                                        .frame(width: 6, height: 6)
                                        .padding(.top, 7)
                                    Text(reason)
                                        .font(.subheadline)
                                        .foregroundStyle(AppTheme.muted)
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    private func findingsSection(_ record: AnalysisRecord) -> some View {
        FrostedCard {
            SectionLabel(
                title: record.problemSectionTitle,
                subtitle: record.shouldShowFormalScore ? "优先看最影响结果的几个问题" : "先看当前能确认的观察结果"
            )

            VStack(spacing: 12) {
                if record.shouldShowFormalScore {
                    ForEach(record.issues) { issue in
                        issueRow(issue)
                    }
                } else {
                    ForEach(record.observations) { observation in
                        observationRow(observation, state: record.reportState)
                    }
                }
            }
        }
    }

    private func suggestionsSection(_ record: AnalysisRecord) -> some View {
        FrostedCard {
            SectionLabel(
                title: suggestionTitle(for: record),
                subtitle: record.shouldShowFormalScore ? "下一步建议" : "先补证据或重拍，再进入正式评分"
            )

            VStack(spacing: 12) {
                ForEach(Array(record.suggestions.prefix(3))) { item in
                    VStack(alignment: .leading, spacing: 8) {
                        Text(item.title)
                            .font(.headline)
                        Text(item.summary)
                            .font(.subheadline)
                            .foregroundStyle(AppTheme.muted)
                        HStack(alignment: .top) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(item.drill.name)
                                    .font(.subheadline.weight(.semibold))
                                Text(item.drill.dosage)
                                    .font(.caption)
                                    .foregroundStyle(AppTheme.accent)
                            }
                            Spacer()
                            Text(item.drill.cue)
                                .font(.caption)
                                .foregroundStyle(.white.opacity(0.80))
                                .multilineTextAlignment(.trailing)
                        }
                    }
                    .padding(16)
                    .background(
                        RoundedRectangle(cornerRadius: 18, style: .continuous)
                            .fill(Color.white.opacity(0.05))
                    )
                }
            }
        }
    }

    private func timestampsSection(_ record: AnalysisRecord) -> some View {
        FrostedCard {
            SectionLabel(
                title: "错误时间点",
                subtitle: "Replay markers"
            )

            if record.errorTimestamps.isEmpty {
                Text("本次没有明确的错误时间点。")
                    .font(.subheadline)
                    .foregroundStyle(AppTheme.muted)
            } else {
                VStack(spacing: 10) {
                    ForEach(record.errorTimestamps) { timestamp in
                        HStack(alignment: .top, spacing: 12) {
                            StatusPill(text: timestamp.rangeText, tint: AppTheme.warning)
                            VStack(alignment: .leading, spacing: 4) {
                                Text(timestamp.label)
                                    .font(.subheadline.weight(.semibold))
                                Text(timestamp.detail)
                                    .font(.caption)
                                    .foregroundStyle(AppTheme.muted)
                            }
                            Spacer(minLength: 0)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
            }
        }
    }

    private func qualitySection(_ record: AnalysisRecord) -> some View {
        FrostedCard {
            SectionLabel(
                title: "本次视频质量状态",
                subtitle: "Video quality"
            )

            HStack(alignment: .top, spacing: 12) {
                Image(systemName: record.qualityStatus.symbol)
                    .font(.headline.weight(.semibold))
                    .foregroundStyle(qualityTint(for: record.qualityStatus))
                    .frame(width: 32, height: 32)
                    .background(
                        Circle()
                            .fill(qualityTint(for: record.qualityStatus).opacity(0.16))
                    )

                VStack(alignment: .leading, spacing: 4) {
                    Text(record.qualityStatus.title)
                        .font(.headline.weight(.semibold))
                    Text(record.qualityStatus.subtitle)
                        .font(.subheadline)
                        .foregroundStyle(AppTheme.muted)
                }

                Spacer(minLength: 0)
            }
        }
    }

    private var actionSection: some View {
        PrimaryButton(title: "返回首页继续训练", subtitle: "回到模板选择并开始下一次分析") {
            appState.dismissToHome()
        }
    }

    private func issueRow(_ issue: AnalysisIssue) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top) {
                StatusPill(text: issue.stage.title, tint: AppTheme.warning)
                if let time = issue.time {
                    StatusPill(text: time, tint: AppTheme.accent)
                }
                Spacer(minLength: 0)
            }

            Text(issue.title)
                .font(.headline)
            Text(issue.detail)
                .font(.subheadline)
                .foregroundStyle(AppTheme.muted)
            Text("影响：\(issue.impact)")
                .font(.footnote)
                .foregroundStyle(.white.opacity(0.82))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(Color.white.opacity(0.05))
        )
    }

    private func observationRow(_ observation: ResultObservation, state: ResultReportState) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top) {
                StatusPill(text: observation.phase.title, tint: mainTint(for: state))
                StatusPill(text: observation.time, tint: AppTheme.accent)
                Spacer(minLength: 0)
            }

            Text(observation.title)
                .font(.headline)
            Text(observation.detail)
                .font(.subheadline)
                .foregroundStyle(AppTheme.muted)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(Color.white.opacity(0.05))
        )
    }

    private func suggestionTitle(for record: AnalysisRecord) -> String {
        switch record.reportState {
        case .readyToScore:
            return "下一步建议"
        case .insufficientEvidence, .qualityFail, .needsConfirmation:
            return "重拍建议"
        }
    }

    private func sequenceConfirmationItems(from result: PassReceiveSequenceResult) -> [SequenceMetricSummary] {
        result.passMetrics
            .filter { $0.lowConfidence }
        + result.receiveMetrics.filter { $0.lowConfidence }
        + result.sequenceMetrics.filter { $0.lowConfidence }
    }

    private func sequenceBadgeText(for metric: SequenceMetricSummary) -> String {
        if metric.lowConfidence {
            return "低置信度"
        }

        switch metric.tone {
        case .good:
            return "亮点"
        case .watch:
            return "可关注"
        case .warn:
            return "需优化"
        case .fail:
            return "需修正"
        case .neutral:
            return "待确认"
        }
    }

    private func sequenceBadgeTint(for metric: SequenceMetricSummary) -> Color {
        if metric.lowConfidence {
            return AppTheme.warning
        }
        return metricTint(for: metric.tone)
    }

    private func sequenceMetricTint(for metric: SequenceMetricSummary) -> Color {
        if metric.lowConfidence {
            return AppTheme.warning
        }
        return metricTint(for: metric.tone)
    }

    private func formatDouble(_ value: Double) -> String {
        if value.rounded() == value {
            return String(Int(value))
        }

        let absolute = abs(value)
        if absolute >= 10 {
            return String(format: "%.2f", value)
        }
        return String(format: "%.3f", value)
    }

    private func logicStepText(_ step: SequenceBandLogicStep) -> String {
        if let condition = step.condition, let band = step.band {
            return "\(condition) => \(band)"
        }
        if let otherwise = step.otherwise {
            return "otherwise => \(otherwise)"
        }
        return "unmapped"
    }

    private func metricCard(_ metric: AnalysisMetric) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top, spacing: 10) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(metric.title)
                        .font(.subheadline.weight(.semibold))
                    Text(metric.key)
                        .font(.caption2)
                        .foregroundStyle(AppTheme.muted)
                }

                Spacer(minLength: 0)

                StatusPill(text: toneLabel(for: metric.tone), tint: metricTint(for: metric.tone))
            }

            Text(metric.valueText)
                .font(.system(size: 24, weight: .bold, design: .rounded))
                .foregroundStyle(metricTint(for: metric.tone))

            Text(metric.detail)
                .font(.caption)
                .foregroundStyle(AppTheme.muted)
                .lineLimit(2)
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(Color.white.opacity(0.05))
        )
    }

    private func ruleRow(_ rule: RuleTriggerSummary) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top, spacing: 10) {
                StatusPill(text: rule.phase.title, tint: phaseTint(for: rule.phase))
                StatusPill(text: rule.key, tint: AppTheme.accent)
                Spacer(minLength: 0)
            }

            Text(rule.title)
                .font(.subheadline.weight(.semibold))
            Text(rule.detail)
                .font(.caption)
                .foregroundStyle(AppTheme.muted)
        }
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(Color.white.opacity(0.05))
        )
    }

    private func mainTint(for state: ResultReportState) -> Color {
        switch state {
        case .readyToScore:
            return AppTheme.success
        case .insufficientEvidence:
            return AppTheme.warning
        case .qualityFail:
            return AppTheme.danger
        case .needsConfirmation:
            return AppTheme.warning
        }
    }

    private func failureTint(for record: AnalysisRecord) -> Color {
        guard let reason = record.failureReason else {
            return AppTheme.danger
        }

        switch reason {
        case .videoTooLong, .analysisTimeout:
            return AppTheme.warning
        case .routeMismatch, .unsupportedAction:
            return AppTheme.danger
        case .noActionWindowFound, .lowMotionSignal, .poseEvidenceLow, .ballEvidenceLow, .contactNotDetected, .analysisResultEmpty:
            return AppTheme.warning
        case .videoOpenFailed, .mediapipePoseInitFailed, .mediapipePoseRuntimeFailed, .unknownError:
            return AppTheme.danger
        }
    }

    private func failureTitle(for record: AnalysisRecord) -> String {
        record.failureReason?.title ?? (record.isAnalysisAnomaly ? "结果异常" : "分析失败")
    }

    private func failureBody(for record: AnalysisRecord) -> String {
        if let reason = record.failureReason {
            return reason.message(durationSeconds: record.runtimeState.videoDurationSeconds)
        }

        if record.isAnalysisAnomaly {
            return record.routeMismatchMessage ?? "本次结果存在异常，请重新分析。"
        }

        return record.failureMessageText.isEmpty ? "本次分析未完成，请重试。" : record.failureMessageText
    }

    private func phaseTint(for phase: MotionStage) -> Color {
        switch phase {
        case .setup:
            return AppTheme.accent
        case .support:
            return AppTheme.success
        case .strike:
            return AppTheme.warning
        case .followThrough:
            return AppTheme.danger
        }
    }

    private func toneLabel(for tone: AnalysisSignalTone) -> String {
        switch tone {
        case .good:
            return "正常"
        case .watch:
            return "注意"
        case .warn:
            return "警告"
        case .fail:
            return "失败"
        case .neutral:
            return "待定"
        }
    }

    private func metricTint(for tone: AnalysisSignalTone) -> Color {
        switch tone {
        case .good:
            return AppTheme.success
        case .watch:
            return AppTheme.accent
        case .warn:
            return AppTheme.warning
        case .fail:
            return AppTheme.danger
        case .neutral:
            return AppTheme.muted
        }
    }

    private func qualityTint(for status: VideoQualityStatus) -> Color {
        switch status {
        case .good:
            return AppTheme.success
        case .limited:
            return AppTheme.warning
        case .poor:
            return AppTheme.danger
        }
    }

    private func uncertaintyReasonText(_ reason: String) -> String {
        switch reason.lowercased() {
        case "no_pose":
            return "人体姿态没有稳定检测到"
        case "target_unstable":
            return "目标跟踪不稳定"
        case "ball_unstable":
            return "球轨迹不稳定"
        case "goal_not_visible":
            return "画面里没有稳定检测到球门"
        case "low_confidence":
            return "当前置信度偏低"
        case "ambiguous_pass_shot":
            return "传球和射门之间仍然比较接近"
        case "short_clip":
            return "视频片段过短，时序证据不够"
        default:
            return reason
        }
    }

    private enum SubscoreKind {
        case technique
        case control
        case safety
    }

    private func scoreTint(for kind: SubscoreKind, record: AnalysisRecord) -> Color {
        guard record.shouldShowFormalScore else {
            return mainTint(for: record.reportState)
        }

        switch kind {
        case .technique:
            return AppTheme.accent
        case .control:
            return AppTheme.success
        case .safety:
            return AppTheme.warning
        }
    }
}
