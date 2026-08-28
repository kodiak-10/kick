import Foundation
import SwiftUI

struct TrainingFeedbackContentView: View {
    let viewModel: TrainingFeedbackViewModel
    let hasProAccess: Bool
    let videoURL: URL?
    let videoLabel: String?
    let isCurrentLatestResult: Bool

    @State private var revealStage: TrainingFeedbackRevealStage = .conclusion
    @State private var showAllMetrics = false
    @State private var showAllSuggestions = false

    init(
        viewModel: TrainingFeedbackViewModel,
        hasProAccess: Bool = false,
        videoURL: URL? = nil,
        videoLabel: String? = nil,
        isCurrentLatestResult: Bool = true
    ) {
        self.viewModel = viewModel
        self.hasProAccess = hasProAccess
        self.videoURL = videoURL
        self.videoLabel = videoLabel
        self.isCurrentLatestResult = isCurrentLatestResult
    }

    var body: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sectionGap) {
            if let matchAnalysis = viewModel.matchAnalysis {
                FullMatchAnalysisContentView(report: matchAnalysis)
            } else if let routeMismatchMessage = viewModel.routeMismatchMessage {
                routeMismatchCard(message: routeMismatchMessage)
            } else if viewModel.isResultAnomalous {
                integrityWarningCard
            } else {
                revealRail
                activeStageSection
            }
        }
        .animation(.easeInOut(duration: 0.24), value: revealStage)
    }

    @ViewBuilder
    private var activeStageSection: some View {
        switch revealStage {
        case .conclusion:
            conclusionSection
        case .evidence:
            evidenceSection
        case .execution:
            executionSection
        case .recap:
            recapSection
        }
    }

    private var conclusionSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sectionGap) {
            headlineCard
            summaryCard
            priorityFocusCard
        }
    }

    private var integrityWarningCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .top, spacing: 12) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundStyle(AppColors.warning)

                    VStack(alignment: .leading, spacing: 6) {
                        Text("本次结果存在异常，请重新分析")
                            .font(AppTypography.cardTitle)
                            .foregroundStyle(AppColors.textPrimary)
                            .fixedSize(horizontal: false, vertical: true)

                        Text("动作类型、总分和等级当前不一致，系统已先拦住这次结果。")
                            .font(AppTypography.caption)
                            .foregroundStyle(AppColors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    Spacer(minLength: 0)
                }

#if DEBUG
                Text(viewModel.routeDebugText)
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textTertiary)
                    .fixedSize(horizontal: false, vertical: true)
#endif

                VStack(alignment: .leading, spacing: 8) {
                    Text("当前视频已保留，可以直接重新分析。")
                        .font(AppTypography.body)
                        .foregroundStyle(AppColors.textPrimary)

                    if !viewModel.integrityReasons.isEmpty {
                        ForEach(Array(viewModel.integrityReasons.prefix(2)), id: \.self) { reason in
                            TrainingFeedbackBulletRow(text: reason)
                        }
                    }
                }

                TrainingFeedbackTag(text: "已拦截异常结果")
            }
        }
    }

    private var evidenceSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sectionGap) {
            if hasProAccess {
                videoEvidenceCard
            } else {
                proUpsellCard
            }

            metricsCard
        }
    }

    private var executionSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sectionGap) {
            if hasProAccess {
                problemCardsCard
                pendingCardsCard
            }

            trainingPlanCard
        }
    }

    private var recapSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sectionGap) {
            takeawayCard
            saveStatusCard
            credibilityCard
        }
    }

    private var headlineCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 12) {
                Text("本次分析动作：\(viewModel.actionName)")
                    .font(AppTypography.captionMedium)
                    .foregroundStyle(AppColors.textSecondary)

                Text("一句话结论")
                    .font(AppTypography.captionMedium)
                    .foregroundStyle(AppColors.textSecondary)

                Text(viewModel.headline)
                    .font(AppTypography.sectionTitle)
                    .foregroundStyle(AppColors.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var summaryCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 16) {
                TrainingFeedbackSectionHeader(
                    title: "总分摘要",
                    subtitle: "动作类型、总分、等级和三个关键标签。"
                )

                HStack(alignment: .top, spacing: 14) {
                    TrainingFeedbackStatBlock(
                        label: "动作类型",
                        value: viewModel.actionName
                    )

                    TrainingFeedbackStatBlock(
                        label: "总分",
                        value: scoreDisplayText
                    )

                    TrainingFeedbackStatBlock(
                        label: "等级",
                        value: viewModel.gradeText
                    )
                }

                HStack(spacing: 8) {
                    ForEach(viewModel.summaryTags, id: \.id) { tag in
                        TrainingFeedbackTag(text: "\(tag.title) · \(tag.status.displayLabel)")
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)

            }
        }
    }

    private func routeMismatchCard(message: String) -> some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .top, spacing: 12) {
                    Image(systemName: "arrow.triangle.branch")
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundStyle(AppColors.warning)

                    VStack(alignment: .leading, spacing: 6) {
                        Text("当前分析没有按你选择的动作类型执行")
                            .font(AppTypography.cardTitle)
                            .foregroundStyle(AppColors.textPrimary)
                            .fixedSize(horizontal: false, vertical: true)

                        Text(message)
                            .font(AppTypography.caption)
                            .foregroundStyle(AppColors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    Spacer(minLength: 0)
                }

                Text("本次分析动作：\(viewModel.actionName)")
                    .font(AppTypography.captionMedium)
                    .foregroundStyle(AppColors.textSecondary)

                Text("请重新按“传球 / 射门”按钮发起分析。")
                    .font(AppTypography.body)
                    .foregroundStyle(AppColors.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)

#if DEBUG
                Text(viewModel.routeDebugText)
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textTertiary)
                    .fixedSize(horizontal: false, vertical: true)
#endif
            }
        }
    }

    private var priorityFocusCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 16) {
                TrainingFeedbackSectionHeader(
                    title: "本次优先改 1 点",
                    subtitle: "只看一个最值得先处理的动作点，不分散注意力。"
                )

                VStack(alignment: .leading, spacing: 12) {
                    HStack(alignment: .top, spacing: 12) {
                        VStack(alignment: .leading, spacing: 6) {
                            Text(viewModel.priorityFocus.title)
                                .font(AppTypography.cardTitle)
                                .foregroundStyle(AppColors.textPrimary)
                                .fixedSize(horizontal: false, vertical: true)

                            Text(viewModel.priorityFocus.reason)
                                .font(AppTypography.body)
                                .foregroundStyle(AppColors.textSecondary)
                                .fixedSize(horizontal: false, vertical: true)
                        }

                        Spacer(minLength: 0)

                        TrainingFeedbackTag(text: viewModel.priorityFocus.status.displayLabel)
                    }

                    Divider()
                        .overlay(AppColors.stroke)

                    TrainingFeedbackLabeledTextBlock(
                        label: "下一次训练先做什么",
                        value: viewModel.priorityFocus.nextStep
                    )
                }
            }
        }
    }

    private var revealRail: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("点击切换")
                .font(AppTypography.captionMedium)
                .foregroundStyle(AppColors.textSecondary)

            HStack(spacing: 8) {
                ForEach(TrainingFeedbackRevealStage.allCases, id: \.self) { stage in
                    Button {
                        if stage != revealStage {
                            Haptics.selection()
                            revealStage = stage
                        }
                    } label: {
                        Text(stage.title)
                            .font(AppTypography.captionMedium)
                            .foregroundStyle(stage == revealStage ? AppColors.textPrimary : AppColors.textSecondary)
                            .padding(.horizontal, 11)
                            .padding(.vertical, 7)
                            .background(stage == revealStage ? AppColors.backgroundElevated : AppColors.backgroundSoft)
                            .overlay(
                                Capsule()
                                    .stroke(stage == revealStage ? AppColors.strongStroke : AppColors.stroke, lineWidth: 1)
                            )
                            .clipShape(Capsule())
                    }
                    .buttonStyle(.plain)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var takeawayCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 16) {
                TrainingFeedbackSectionHeader(
                    title: "这轮最值得带走的 3 个信息",
                    subtitle: "把稳定优势、优先改点和下一次练什么一次记住。"
                )

                VStack(alignment: .leading, spacing: 12) {
                    TrainingFeedbackTakeawayRow(
                        title: "稳定优势",
                        text: viewModel.goodObservations.first ?? "本次整体动作完成度比较稳。"
                    )

                    TrainingFeedbackTakeawayRow(
                        title: "优先改点",
                        text: "\(viewModel.priorityFocus.title)：\(viewModel.priorityFocus.reason)"
                    )

                    TrainingFeedbackTakeawayRow(
                        title: "下一次练",
                        text: viewModel.trainingSuggestions.first ?? viewModel.priorityFocus.nextStep
                    )
                }
            }
        }
    }

    private var saveStatusCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 10) {
                HStack(alignment: .top, spacing: 10) {
                    Image(systemName: isCurrentLatestResult ? "checkmark.seal.fill" : "clock.arrow.circlepath")
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(isCurrentLatestResult ? AppColors.positive : AppColors.textSecondary)

                    VStack(alignment: .leading, spacing: 4) {
                        Text(isCurrentLatestResult ? "已保存到历史记录" : "这次结果已沉淀在历史里")
                            .font(AppTypography.cardTitle)
                            .foregroundStyle(AppColors.textPrimary)

                        Text(isCurrentLatestResult ? "下次再练时，可以直接回到历史页和这次做对比。" : "你可以把这次训练当作一次复盘样本继续回看。")
                            .font(AppTypography.caption)
                            .foregroundStyle(AppColors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }

                if isCurrentLatestResult {
                    TrainingFeedbackTag(text: "自动保存完成")
                }
            }
        }
    }

    private var videoEvidenceCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 16) {
                TrainingFeedbackSectionHeader(
                    title: "视频回放与关键帧",
                    subtitle: videoURL == nil ? "当前结果没有原视频可回放，只能先看关键时刻。" : "可回放上传的视频，时间点和关键帧都能跳转。"
                )

                TrainingFeedbackVideoModule(
                    viewModel: viewModel,
                    videoURL: videoURL,
                    videoLabel: videoLabel
                )
            }
        }
    }

    private var problemCardsCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 16) {
                TrainingFeedbackSectionHeader(
                    title: "问题定位",
                    subtitle: "只说明哪里出了问题、为什么影响动作质量。"
                )

                VStack(alignment: .leading, spacing: 12) {
                    if viewModel.problemCards.isEmpty {
                        TrainingFeedbackMiniCard {
                            Text("本次没有明确需要改进的问题点。")
                                .font(AppTypography.body)
                                .foregroundStyle(AppColors.textPrimary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    } else {
                        ForEach(viewModel.problemCards, id: \.id) { card in
                            TrainingFeedbackProblemCardView(card: card)
                        }
                    }
                }
            }
        }
    }

    private var pendingCardsCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 16) {
                TrainingFeedbackSectionHeader(
                    title: "这次先参考的",
                    subtitle: "置信度较低的项只作参考，不纳入正式扣分。"
                )

                VStack(alignment: .leading, spacing: 12) {
                    if viewModel.pendingCards.isEmpty {
                        TrainingFeedbackMiniCard {
                            Text("当前没有低置信项，说明主要结论相对更稳定。")
                                .font(AppTypography.body)
                                .foregroundStyle(AppColors.textPrimary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    } else {
                        ForEach(viewModel.pendingCards, id: \.id) { card in
                            TrainingFeedbackPendingCardView(card: card)
                        }
                    }
                }
            }
        }
    }

    private var metricsCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 16) {
                TrainingFeedbackSectionHeader(
                    title: "关键指标",
                    subtitle: "先看最关键的一项，再看辅助指标；低置信指标只帮助理解趋势。"
                )

                if let primaryMetric {
                    TrainingFeedbackMetricHeroCardView(metric: primaryMetric)

                    LazyVGrid(
                        columns: [
                            GridItem(.flexible(), spacing: 12),
                            GridItem(.flexible(), spacing: 12)
                        ],
                        spacing: 12
                    ) {
                        ForEach(displayedSecondaryMetrics, id: \.id) { metric in
                            TrainingFeedbackMetricCardView(metric: metric)
                        }
                    }
                } else {
                    Text("当前没有可展示的关键指标。")
                        .font(AppTypography.body)
                        .foregroundStyle(AppColors.textSecondary)
                }

                if !additionalMetrics.isEmpty {
                    if hasProAccess {
                        Button {
                            Haptics.selection()
                            withAnimation(.easeInOut(duration: 0.2)) {
                                showAllMetrics.toggle()
                            }
                        } label: {
                            HStack(spacing: 8) {
                                Text(showAllMetrics ? "收起辅助指标" : "查看其余 \(additionalMetrics.count) 项")
                                    .font(AppTypography.captionMedium)

                                Image(systemName: showAllMetrics ? "chevron.up" : "chevron.down")
                                    .font(.system(size: 11, weight: .semibold))
                            }
                            .foregroundStyle(AppColors.textPrimary)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 10)
                            .background(AppColors.backgroundSoft)
                            .overlay(
                                RoundedRectangle(cornerRadius: AppCornerRadius.small, style: .continuous)
                                    .stroke(AppColors.stroke, lineWidth: 1)
                            )
                            .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.small, style: .continuous))
                        }
                        .buttonStyle(.plain)
                    } else {
                        Text("专业版可展开其余 \(additionalMetrics.count) 项指标，继续看完整趋势。")
                            .font(AppTypography.caption)
                            .foregroundStyle(AppColors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }
        }
    }

    private var trainingPlanCard: some View {
        Button {
            Haptics.light()
            withAnimation(.spring(response: 0.34, dampingFraction: 0.88)) {
                showAllSuggestions.toggle()
            }
        } label: {
            DarkCard {
                VStack(alignment: .leading, spacing: 16) {
                    HStack(alignment: .top, spacing: 12) {
                        VStack(alignment: .leading, spacing: 6) {
                            TrainingFeedbackSectionHeader(
                                title: "训练计划",
                                subtitle: "按目标、组数和动作提示执行，先练 1-2 个重点。"
                            )
                        }

                        Spacer(minLength: 0)

                        Image(systemName: showAllSuggestions ? "chevron.up" : "chevron.down")
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundStyle(AppColors.textTertiary)
                    }

                    if showAllSuggestions {
                        ForEach(trainingDrills) { drill in
                            TrainingFeedbackDrillPlanCard(drill: drill)
                        }

                        TrainingFeedbackLabeledListBlock(
                            title: "训练依据",
                            items: trainingPrincipleItems
                        )

                        TrainingFeedbackLabeledListBlock(
                            title: "建议执行顺序",
                            items: trainingSessionStructure
                        )
                    } else {
                        TrainingFeedbackMiniCard(padding: AppSpacing.compactPadding) {
                            VStack(alignment: .leading, spacing: 6) {
                                Text("点开看完整训练安排")
                                    .font(AppTypography.captionMedium)
                                    .foregroundStyle(AppColors.textSecondary)

                                Text(trainingSuggestionItems.first ?? viewModel.priorityFocus.nextStep)
                                    .font(AppTypography.body)
                                    .foregroundStyle(AppColors.textPrimary)
                                    .fixedSize(horizontal: false, vertical: true)

                                Text("依据：先稳触球质量，再加扫描、移动和对抗。")
                                    .font(AppTypography.caption)
                                    .foregroundStyle(AppColors.textSecondary)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                    }
                }
            }
        }
        .buttonStyle(.plain)
    }

    private var proUpsellCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .top, spacing: 12) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("专业版可展开更细证据")
                            .font(AppTypography.cardTitle)
                            .foregroundStyle(AppColors.textPrimary)

                        Text("把错误定位到具体时刻，再看关键帧和更细的改法、练法。")
                            .font(AppTypography.caption)
                            .foregroundStyle(AppColors.textSecondary)
                    }

                    Spacer(minLength: 0)

                    ProBadge(title: "PRO")
                }

                TrainingFeedbackLabeledListBlock(
                    title: "升级后可看",
                    items: [
                        "错误时刻标记和视频时间轴回看",
                        "关键帧分析，直接看哪一瞬间最值得改",
                        "更细的“问题—改法—练法”",
                        "历史对比与重复问题追踪"
                    ]
                )
            }
        }
    }

    private var credibilityCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 16) {
                TrainingFeedbackSectionHeader(
                    title: "这次结果是否可信",
                    subtitle: "哪些结论更稳、哪些需要补拍、下次怎么拍更准。"
                )

                TrainingFeedbackConfidenceReviewCard(
                    review: viewModel.confidenceReview,
                    hasVideoSource: videoURL != nil
                )
            }
        }
    }

    private var scoreDisplayText: String {
        if let scoreValue = viewModel.scoreValue {
            return "\(scoreValue) / 100"
        }
        return viewModel.scoreText
    }

    private var visibleMetrics: [TrainingFeedbackMetricItem] {
        Array(viewModel.metrics.prefix(4))
    }

    private var additionalMetrics: [TrainingFeedbackMetricItem] {
        Array(viewModel.metrics.dropFirst(4))
    }

    private var primaryMetric: TrainingFeedbackMetricItem? {
        visibleMetrics.first
    }

    private var displayedSecondaryMetrics: [TrainingFeedbackMetricItem] {
        let secondary = Array(visibleMetrics.dropFirst())
        return showAllMetrics ? secondary + additionalMetrics : secondary
    }

    private var trainingSuggestionItems: [String] {
        var seen = Set<String>()
        let candidates = [viewModel.priorityFocus.nextStep] + viewModel.trainingSuggestions
        let suggestions = candidates.compactMap { item -> String? in
            let trimmed = item.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !trimmed.isEmpty, !seen.contains(trimmed) else {
                return nil
            }

            seen.insert(trimmed)
            return trimmed
        }

        return Array(suggestions.prefix(3))
    }

    private var trainingPrincipleItems: [String] {
        if isShotFeedback {
            return [
                "力量链：髋部先带动大腿，再带小腿摆出，脚踝锁定，主要练大腿前侧、髋部和小腿末端控制。",
                "支撑底座：支撑脚稳定决定射门方向和高度，重点练脚踝稳定、单腿平衡和核心压球。",
                "目标迁移：先固定距离命中目标区，再加入助跑、不同角度和轻对抗，让射门接近比赛。"
            ]
        }

        return [
            "触球质量：支撑脚指向、脚踝锁定、触球面稳定，主要练脚踝控制和小腿末端精度。",
            "身体协调：接球前扫描，第一脚把球带向下一步方向，练髋部转向、核心稳定和节奏感。",
            "比赛迁移：从无压力到有限对抗，逐步加入移动、时间限制和左右脚变化。"
        ]
    }

    private var trainingSessionStructure: [String] {
        if isShotFeedback {
            return [
                "热身 6-8 分钟：动态踝膝髋活动、单腿平衡和低速摆腿，让支撑脚先醒过来。",
                "专项 14-20 分钟：目标区射门 + 支撑脚定位 + 发力链射门，只练 1-2 个重点。",
                "情境 8-12 分钟：加入 2-3 步助跑、横向来球或轻防守干扰，检验能不能进门和控制角度。"
            ]
        }

        return [
            "热身 6-8 分钟：低强度带球、传接球和动态活动，让身体进入节奏。",
            "专项 12-18 分钟：只练本次优先改点，按计划完成组数，质量下降就降速。",
            "情境 8-12 分钟：加入移动目标或防守干扰，把动作放回接近比赛的场景。"
        ]
    }

    private var trainingDrills: [TrainingFeedbackTrainingDrill] {
        var orderedMetricKeys = [viewModel.priorityFocus.metricKey]
        orderedMetricKeys.append(contentsOf: viewModel.problemCards.map(\.metricKey))
        orderedMetricKeys.append(contentsOf: viewModel.pendingCards.map(\.metricKey))
        orderedMetricKeys.append(contentsOf: isShotFeedback ? shotComplementaryMetricKeys : passComplementaryMetricKeys)

        var seen = Set<ResultMetricKey>()
        return orderedMetricKeys.compactMap { key in
            guard !seen.contains(key) else { return nil }
            seen.insert(key)
            return drill(for: key)
        }
        .prefix(3)
        .map { $0 }
    }

    private var isShotFeedback: Bool {
        viewModel.selectedAction == .shot ||
            viewModel.actionName.localizedCaseInsensitiveContains("射门") ||
            viewModel.actionName.localizedCaseInsensitiveContains("shot")
    }

    private var passComplementaryMetricKeys: [ResultMetricKey] {
        [
            .passEndpointErrorM,
            .passExecutionTimeS,
            .receiveControlZoneSuccessRate,
            .passReceiveGapS,
            .sequenceContinuityScore,
            .nextActionReadiness
        ]
    }

    private var shotComplementaryMetricKeys: [ResultMetricKey] {
        [
            .shotTargetZoneHit,
            .shotMaxBallSpeedMPS,
            .supportFootLateralOffsetCM,
            .shotConsistencyCVPercent,
            .trunkLeanDegAtImpactProxy
        ]
    }

    private func drill(for metricKey: ResultMetricKey) -> TrainingFeedbackTrainingDrill {
        switch metricKey {
        case .passEndpointErrorM:
            return TrainingFeedbackTrainingDrill(
                title: "目标门落点校准",
                trains: "脚踝锁定、小腿末端精度、支撑脚指向和传球线路",
                dosage: "4 组 x 10 球，左右脚各做；组间休息 45-60 秒",
                steps: [
                    "用两个标志盘摆一个 1.5 米目标门，距离先放 6-8 米。",
                    "每球出脚前先看目标门，支撑脚脚尖对准目标，脚内侧触球面保持平。",
                    "记录每组 10 球穿过目标门的次数，低于 6 次先降速度，不加距离。"
                ],
                cue: "这组主要练落点，不追求大力；球偏左偏右时先看支撑脚朝向。"
            )
        case .passExecutionTimeS:
            return TrainingFeedbackTrainingDrill(
                title: "两触限时出球",
                trains: "出脚节奏、接球前扫描、支撑脚提前到位和协调性",
                dosage: "4 组 x 8 次，每次接球到传出控制在 2 秒内",
                steps: [
                    "同伴传球前先抬头看目标，身体提前半侧身。",
                    "第一脚把球带到下一步传球方向，第二脚完成传球。",
                    "如果需要第三脚以上才能处理，下一次降低来球速度重新做。"
                ],
                cue: "这组练节奏感，不是练花动作；关键是接球前已经知道传向哪里。"
            )
        case .receiveControlZoneSuccessRate:
            return TrainingFeedbackTrainingDrill(
                title: "第一脚入区控制",
                trains: "脚踝缓冲、髋部转向、核心稳定和第一脚方向控制",
                dosage: "4 组 x 10 次；每次第一脚必须停进 1.5 米控制区",
                steps: [
                    "在身体前侧半步到一步放一个控制区，来球前先侧身打开。",
                    "第一脚触球时脚踝放松缓冲，把球带向下一脚传球方向。",
                    "球停到身后或身体正下方就算失败，重新调整站位再做。"
                ],
                cue: "接球问题通常不是脚下慢，而是身体太晚打开，第一脚没有方向。"
            )
        case .receiveStabilizationTimeS:
            return TrainingFeedbackTrainingDrill(
                title: "接球后一步回稳",
                trains: "重心回收、脚踝稳定、核心控制和小步调整质量",
                dosage: "3 组 x 10 次；每次接球后 1 步内站稳",
                steps: [
                    "接球后只允许一步调整，身体重心收回到两脚之间。",
                    "站稳后再完成下一脚传球，不要边失衡边急着出脚。",
                    "每组统计需要两步以上才站稳的次数，目标逐组减少。"
                ],
                cue: "回稳慢会拖慢下一动作；先稳住底盘，再谈提速。"
            )
        case .receiveCorrectiveTouchCount:
            return TrainingFeedbackTrainingDrill(
                title: "两脚内处理",
                trains: "第一脚质量、减少补救触球、节奏控制和处理效率",
                dosage: "4 组 x 8 次；一次接球最多两脚完成传出",
                steps: [
                    "第一脚只做方向处理，不停死球。",
                    "第二脚必须传出，不能继续用小碎步补救。",
                    "如果连续失败，先把来球速度降到 70%，再逐步恢复比赛速度。"
                ],
                cue: "补救触球多，通常说明第一脚太保守或方向错了。"
            )
        case .passReceiveGapS:
            return TrainingFeedbackTrainingDrill(
                title: "传接间隔压缩",
                trains: "接球前预判、节奏衔接、髋部转向和下一脚准备",
                dosage: "5 轮 x 90 秒；每轮目标是连续完成 8 次接传",
                steps: [
                    "接球前先喊出下一传目标，让大脑先做决定。",
                    "第一脚带向目标方向，第二脚立刻传出，减少中间停顿。",
                    "每轮只统计连续成功次数，断掉后从 1 重新开始。"
                ],
                cue: "这组专门解决接到球后空一下的问题，练的是连续处理。"
            )
        case .sequenceContinuityScore:
            return TrainingFeedbackTrainingDrill(
                title: "三动作串联",
                trains: "传球、接球、下一步移动的整体连贯性和比赛节奏",
                dosage: "4 组 x 6 个循环；每个循环包含接球、传球、前插/回撤",
                steps: [
                    "从标志盘 A 接球，第二脚传向目标门。",
                    "传完立刻移动到标志盘 B，模拟比赛里传后接应。",
                    "每个循环不中断才算成功，动作散掉就降低速度。"
                ],
                cue: "单个动作好不够，传完能不能进入下一位置才接近比赛。"
            )
        case .nextActionReadiness:
            return TrainingFeedbackTrainingDrill(
                title: "扫描后下一步",
                trains: "接球前观察、决策速度、重心预备和方向选择",
                dosage: "4 组 x 8 次；每次来球前必须完成一次抬头扫描",
                steps: [
                    "同伴传球前举起不同颜色标志，你先喊颜色再接球。",
                    "第一脚按颜色指定方向带出，第二脚完成传球或带球。",
                    "如果接球后才抬头，算一次失败。"
                ],
                cue: "下一动作准备不是脚快，而是球到之前已经完成观察和决定。"
            )
        case .shotTargetZoneHit:
            return TrainingFeedbackTrainingDrill(
                title: "四区命中射门",
                trains: "射门目标选择、脚面控制、进门位置和方向稳定",
                dosage: "5 组 x 4 球；左下、右下、左上、右上轮换",
                steps: [
                    "每球起脚前先说出目标区，不允许临时改方向。",
                    "支撑脚脚尖朝目标侧，触球后收尾继续朝目标区送出。",
                    "记录是否进门、是否命中目标区，命中率低于 50% 先降力量。"
                ],
                cue: "射门不能只看动作姿势，要同时看进门结果和进门位置。"
            )
        case .shotMaxBallSpeedMPS, .shotMaxBallSpeedProxyMPS:
            return TrainingFeedbackTrainingDrill(
                title: "髋部带动发力",
                trains: "髋部转动、大腿前侧发力、小腿摆速和脚踝锁定",
                dosage: "3 组无球摆腿 8 次 + 4 组有球射门 5 次",
                steps: [
                    "无球先慢速做髋部带动大腿、大腿带小腿，脚背绷紧。",
                    "有球时先用 70% 力量，触球后脚背继续向目标方向送出。",
                    "每次射完保持平衡 1 秒，再开始下一球。"
                ],
                cue: "不要只甩小腿，髋部和大腿带起来后，球速才会稳定。"
            )
        case .shotConsistencyCVPercent:
            return TrainingFeedbackTrainingDrill(
                title: "同模板连续射",
                trains: "动作重复性、支撑脚落点、收尾方向和节奏稳定",
                dosage: "4 组 x 6 球；同距离同目标，组间休息 60 秒",
                steps: [
                    "每球支撑脚都踩在同一标志盘旁，助跑步数保持一致。",
                    "每组只瞄准一个目标区，不随意换角度。",
                    "记录球路高度和方向，连续两球差异大就降低力量。"
                ],
                cue: "重复性稳定后，再去追求更大力量和更刁钻角度。"
            )
        case .supportFootLateralOffsetCM, .supportFootAPOffsetCM:
            return TrainingFeedbackTrainingDrill(
                title: "支撑脚定点射门",
                trains: "脚踝稳定、膝髋支撑、身体压球和射门方向控制",
                dosage: "4 组 x 6 球；每球都检查支撑脚位置",
                steps: [
                    "在球侧约一脚距离放标志盘，支撑脚落在标志盘旁。",
                    "脚尖略朝目标，身体重心压在球上方，不要落在球后。",
                    "先用 70% 力量射门，稳定后再提高速度。"
                ],
                cue: "球偏高或偏歪时，优先查支撑脚，不要只怪摆腿。"
            )
        case .trunkLeanDegAtImpactProxy:
            return TrainingFeedbackTrainingDrill(
                title: "压球收尾射门",
                trains: "核心控制、躯干前压、触球高度和射门压低能力",
                dosage: "4 组 x 5 球；每组只要求球不过目标横杆高度",
                steps: [
                    "触球瞬间胸口略压住球，眼睛看球到触球完成。",
                    "射完身体继续向前走一步，避免立刻后仰收脚。",
                    "如果连续打高，减少助跑速度，重新找身体前压感觉。"
                ],
                cue: "身体角度决定球是否飘，高球多时先解决后仰。"
            )
        }
    }
}

private enum TrainingFeedbackRevealStage: Int, CaseIterable {
    case conclusion
    case evidence
    case execution
    case recap

    var title: String {
        switch self {
        case .conclusion:
            return "结论"
        case .evidence:
            return "证据"
        case .execution:
            return "执行"
        case .recap:
            return "复盘"
        }
    }
}

private struct TrainingFeedbackTrainingDrill: Identifiable {
    let id = UUID()
    let title: String
    let trains: String
    let dosage: String
    let steps: [String]
    let cue: String
}

struct TrainingFeedbackSectionHeader: View {
    let title: String
    let subtitle: String

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(AppTypography.cardTitle)
                .foregroundStyle(AppColors.textPrimary)

            Text(subtitle)
                .font(AppTypography.caption)
                .foregroundStyle(AppColors.textSecondary)
        }
    }
}

private struct TrainingFeedbackDrillPlanCard: View {
    let drill: TrainingFeedbackTrainingDrill

    var body: some View {
        TrainingFeedbackMiniCard(padding: AppSpacing.compactPadding) {
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .top, spacing: 10) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(drill.title)
                            .font(AppTypography.bodyMedium)
                            .foregroundStyle(AppColors.textPrimary)

                        Text("练什么：\(drill.trains)")
                            .font(AppTypography.caption)
                            .foregroundStyle(AppColors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    Spacer(minLength: 0)

                    TrainingFeedbackTag(text: drill.dosage)
                }

                VStack(alignment: .leading, spacing: 8) {
                    Text("怎么做")
                        .font(AppTypography.captionMedium)
                        .foregroundStyle(AppColors.textSecondary)

                    ForEach(Array(drill.steps.enumerated()), id: \.offset) { index, step in
                        HStack(alignment: .top, spacing: 10) {
                            Text("\(index + 1)")
                                .font(AppTypography.captionMedium)
                                .foregroundStyle(AppColors.onAccent)
                                .frame(width: 22, height: 22)
                                .background(AppColors.accent)
                                .clipShape(Circle())

                            Text(step)
                                .font(AppTypography.body)
                                .foregroundStyle(AppColors.textPrimary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }

                Text("教练提示：\(drill.cue)")
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(10)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(AppColors.backgroundSoft)
                    .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.small, style: .continuous))
            }
        }
    }
}

private struct TrainingFeedbackDrillDemoCard: View {
    let actionName: String
    @State private var isAnimating = false

    private var isShot: Bool {
        actionName.localizedCaseInsensitiveContains("射门") ||
            actionName.localizedCaseInsensitiveContains("shot")
    }

    var body: some View {
        TrainingFeedbackMiniCard(padding: AppSpacing.compactPadding) {
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .top, spacing: 10) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("AI模拟动作演示")
                            .font(AppTypography.bodyMedium)
                            .foregroundStyle(AppColors.textPrimary)

                        Text(isShot ? "看支撑脚、摆腿发力和球门目标区。" : "看支撑脚、触球面和传球线路。")
                            .font(AppTypography.caption)
                            .foregroundStyle(AppColors.textSecondary)
                    }

                    Spacer(minLength: 0)

                    TrainingFeedbackTag(text: isShot ? "射门" : "传球")
                }

                GeometryReader { proxy in
                    let width = proxy.size.width
                    let height = proxy.size.height
                    let ballStartX = isShot ? width * 0.28 : width * 0.22
                    let ballStartY = height * 0.68
                    let ballEndX = isShot ? width * 0.78 : width * 0.74
                    let ballEndY = isShot ? height * 0.34 : height * 0.44

                    ZStack {
                        RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                            .fill(
                                LinearGradient(
                                    colors: [
                                        AppColors.backgroundElevated,
                                        AppColors.backgroundSoft
                                    ],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )
                            .overlay(
                                RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                                    .stroke(AppColors.stroke, lineWidth: 1)
                            )

                        if isShot {
                            RoundedRectangle(cornerRadius: 5, style: .continuous)
                                .stroke(AppColors.strongStroke, lineWidth: 2)
                                .frame(width: width * 0.2, height: height * 0.34)
                                .position(x: width * 0.84, y: height * 0.34)

                            Text("球门目标区")
                                .font(AppTypography.captionMedium)
                                .foregroundStyle(AppColors.textSecondary)
                                .position(x: width * 0.78, y: height * 0.14)
                        } else {
                            Circle()
                                .stroke(AppColors.strongStroke, lineWidth: 2)
                                .frame(width: 38, height: 38)
                                .position(x: width * 0.78, y: height * 0.44)

                            Text("接球队友")
                                .font(AppTypography.captionMedium)
                                .foregroundStyle(AppColors.textSecondary)
                                .position(x: width * 0.78, y: height * 0.24)
                        }

                        Capsule()
                            .fill(AppColors.textTertiary.opacity(0.45))
                            .frame(width: isAnimating ? width * 0.48 : width * 0.18, height: 4)
                            .rotationEffect(.degrees(isShot ? -23 : -12))
                            .position(x: width * 0.5, y: isShot ? height * 0.5 : height * 0.55)

                        Circle()
                            .fill(AppColors.accent.opacity(0.28))
                            .frame(width: 48, height: 48)
                            .position(x: width * 0.24, y: height * 0.66)

                        Circle()
                            .fill(AppColors.textPrimary)
                            .frame(width: 12, height: 12)
                            .position(x: isAnimating ? ballEndX : ballStartX, y: isAnimating ? ballEndY : ballStartY)

                        Text(isShot ? "支撑脚踩实" : "支撑脚指向目标")
                            .font(AppTypography.captionMedium)
                            .foregroundStyle(AppColors.textPrimary)
                            .padding(.horizontal, 9)
                            .padding(.vertical, 5)
                            .background(AppColors.background.opacity(0.78))
                            .clipShape(Capsule())
                            .position(x: width * 0.28, y: height * 0.86)

                        Text(isShot ? "髋部带动摆腿" : "触球面朝目标")
                            .font(AppTypography.captionMedium)
                            .foregroundStyle(AppColors.textPrimary)
                            .padding(.horizontal, 9)
                            .padding(.vertical, 5)
                            .background(AppColors.background.opacity(0.78))
                            .clipShape(Capsule())
                            .position(x: width * 0.46, y: height * 0.34)
                    }
                }
                .frame(height: 154)
                .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
                .onAppear {
                    guard !isAnimating else { return }
                    withAnimation(.easeInOut(duration: 1.35).repeatForever(autoreverses: true)) {
                        isAnimating = true
                    }
                }

                Text(isShot
                     ? "先慢速做对支撑和收尾，再逐步加大力量；目标是进门方向和球速一起稳定。"
                     : "先慢速做对支撑和触球面，再逐步加入扫描、移动和对抗。")
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }
}

private struct TrainingFeedbackStatBlock: View {
    let label: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(label)
                .font(AppTypography.captionMedium)
                .foregroundStyle(AppColors.textSecondary)

            Text(value)
                .font(AppTypography.bodyMedium)
                .foregroundStyle(AppColors.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 2)
    }
}

struct TrainingFeedbackTag: View {
    let text: String

    var body: some View {
        Text(text)
            .font(AppTypography.captionMedium)
            .foregroundStyle(AppColors.textPrimary)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(AppColors.backgroundSoft)
            .overlay(
                Capsule()
                    .stroke(AppColors.stroke, lineWidth: 1)
            )
            .clipShape(Capsule())
    }
}

private struct TrainingFeedbackBulletRow: View {
    let text: String

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Circle()
                .fill(AppColors.textSecondary)
                .frame(width: 6, height: 6)
                .padding(.top, 7)

            Text(text)
                .font(AppTypography.body)
                .foregroundStyle(AppColors.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

private struct TrainingFeedbackTakeawayRow: View {
    let title: String
    let text: String

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 8) {
                Circle()
                    .fill(AppColors.accent)
                    .frame(width: 7, height: 7)

                Text(title)
                    .font(AppTypography.captionMedium)
                    .foregroundStyle(AppColors.textSecondary)
            }

            Text(text)
                .font(AppTypography.body)
                .foregroundStyle(AppColors.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(12)
        .background(AppColors.backgroundSoft)
        .overlay(
            RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                .stroke(AppColors.stroke, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
    }
}

private struct TrainingFeedbackProblemCardView: View {
    let card: TrainingFeedbackProblemCard
    @State private var isExpanded = false

    var body: some View {
        Button {
            Haptics.light()
            withAnimation(.spring(response: 0.34, dampingFraction: 0.88)) {
                isExpanded.toggle()
            }
        } label: {
            TrainingFeedbackMiniCard {
                VStack(alignment: .leading, spacing: 12) {
                    HStack(alignment: .top, spacing: 10) {
                        VStack(alignment: .leading, spacing: 6) {
                            HStack(spacing: 8) {
                                TrainingFeedbackTag(text: card.markerKind.displayLabel)
                                Text(card.timeLabel)
                                    .font(AppTypography.captionMedium)
                                    .foregroundStyle(AppColors.textSecondary)
                            }

                            Text(card.topic)
                                .font(AppTypography.bodyMedium)
                                .foregroundStyle(AppColors.textPrimary)
                                .fixedSize(horizontal: false, vertical: true)

                            Text(isExpanded ? card.issue : "问题：\(card.issue)")
                                .font(AppTypography.caption)
                                .foregroundStyle(AppColors.textSecondary)
                                .fixedSize(horizontal: false, vertical: true)
                                .lineLimit(isExpanded ? nil : 2)
                        }

                        Spacer(minLength: 0)

                        TrainingFeedbackTag(text: card.status.displayLabel)
                    }

                    Divider()
                        .overlay(AppColors.stroke)

                    if isExpanded {
                        VStack(alignment: .leading, spacing: 10) {
                            TrainingFeedbackLabeledTextBlock(
                                label: "为什么重要",
                                value: card.whyImportant
                            )

                            TrainingFeedbackLabeledTextBlock(
                                label: "怎么改",
                                value: card.fix
                            )

                        }
                    } else {
                        HStack {
                            Text("点开看原因和改法")
                                .font(AppTypography.captionMedium)
                                .foregroundStyle(AppColors.textSecondary)

                            Spacer()

                            Image(systemName: "chevron.down")
                                .font(.system(size: 11, weight: .semibold))
                                .foregroundStyle(AppColors.textTertiary)
                        }
                    }
                }
            }
        }
        .buttonStyle(.plain)
    }
}

private struct TrainingFeedbackPendingCardView: View {
    let card: TrainingFeedbackPendingCard
    @State private var isExpanded = false

    var body: some View {
        Button {
            Haptics.light()
            withAnimation(.spring(response: 0.34, dampingFraction: 0.88)) {
                isExpanded.toggle()
            }
        } label: {
            TrainingFeedbackMiniCard {
                VStack(alignment: .leading, spacing: 12) {
                    HStack(alignment: .top, spacing: 10) {
                        VStack(alignment: .leading, spacing: 6) {
                            HStack(spacing: 8) {
                                TrainingFeedbackTag(text: card.markerKind.displayLabel)
                                Text(card.timeLabel)
                                    .font(AppTypography.captionMedium)
                                    .foregroundStyle(AppColors.textSecondary)
                            }

                            Text(card.topic)
                                .font(AppTypography.bodyMedium)
                                .foregroundStyle(AppColors.textPrimary)
                                .fixedSize(horizontal: false, vertical: true)

                            Text(isExpanded ? card.reason : "低置信原因：\(card.reason)")
                                .font(AppTypography.caption)
                                .foregroundStyle(AppColors.textSecondary)
                                .fixedSize(horizontal: false, vertical: true)
                                .lineLimit(isExpanded ? nil : 2)
                        }

                        Spacer(minLength: 0)

                        TrainingFeedbackTag(text: card.status.displayLabel)
                    }

                    Divider()
                        .overlay(AppColors.stroke)

                    if isExpanded {
                        VStack(alignment: .leading, spacing: 10) {
                            TrainingFeedbackLabeledTextBlock(
                                label: "为什么暂时不稳定",
                                value: card.reason
                            )

                            TrainingFeedbackLabeledTextBlock(
                                label: "下次怎么拍更准",
                                value: card.captureAdvice
                            )

                            TrainingFeedbackLabeledTextBlock(
                                label: "扣分说明",
                                value: card.note
                            )
                        }
                    } else {
                        HStack {
                            Text("点开看低置信原因")
                                .font(AppTypography.captionMedium)
                                .foregroundStyle(AppColors.textSecondary)

                            Spacer()

                            Image(systemName: "chevron.down")
                                .font(.system(size: 11, weight: .semibold))
                                .foregroundStyle(AppColors.textTertiary)
                        }
                    }
                }
            }
        }
        .buttonStyle(.plain)
    }
}

private struct TrainingFeedbackLabeledTextBlock: View {
    let label: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(AppTypography.captionMedium)
                .foregroundStyle(AppColors.textSecondary)

            Text(value)
                .font(AppTypography.body)
                .foregroundStyle(AppColors.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

private struct TrainingFeedbackMetricCardView: View {
    let metric: TrainingFeedbackMetricItem

    var body: some View {
        TrainingFeedbackMiniCard {
            VStack(alignment: .leading, spacing: 12) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(metric.title)
                        .font(AppTypography.bodyMedium)
                        .foregroundStyle(AppColors.textPrimary)

                    Text(displayValue)
                        .font(AppTypography.headline)
                        .foregroundStyle(AppColors.textPrimary)
                        .monospacedDigit()

                    Text(displayExplanation)
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                TrainingFeedbackTag(text: metric.status.displayLabel)
            }
        }
    }

    private var displayValue: String {
        TrainingFeedbackMetricDisplay.value(for: metric)
    }

    private var displayExplanation: String {
        TrainingFeedbackMetricDisplay.explanation(for: metric)
    }
}

private struct TrainingFeedbackMetricHeroCardView: View {
    let metric: TrainingFeedbackMetricItem

    var body: some View {
        TrainingFeedbackMiniCard(padding: AppSpacing.compactPadding) {
            HStack(alignment: .top, spacing: 14) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("本次最关键指标")
                        .font(AppTypography.captionMedium)
                        .foregroundStyle(AppColors.textSecondary)

                    Text(metric.title)
                        .font(AppTypography.cardTitle)
                        .foregroundStyle(AppColors.textPrimary)

                    Text(TrainingFeedbackMetricDisplay.explanation(for: metric))
                        .font(AppTypography.body)
                        .foregroundStyle(AppColors.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                Spacer(minLength: 0)

                VStack(alignment: .trailing, spacing: 8) {
                    Text(TrainingFeedbackMetricDisplay.value(for: metric))
                        .font(AppTypography.metric)
                        .foregroundStyle(AppColors.textPrimary)
                        .monospacedDigit()

                    TrainingFeedbackTag(text: metric.status.displayLabel)
                }
            }
        }
    }
}

private enum TrainingFeedbackMetricDisplay {
    static func value(for metric: TrainingFeedbackMetricItem) -> String {
        guard metric.key == .shotTargetZoneHit else {
            return metric.valueText
        }

        let normalized = metric.valueText
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()

        if normalized.contains("未") || normalized == "0" || normalized.hasPrefix("0/") {
            return "未命中"
        }

        if normalized.contains("命中") || normalized.contains("yes") || normalized.contains("true") {
            return "命中"
        }

        if let first = normalized.split(separator: "/").first,
           let firstNumber = Double(first.trimmingCharacters(in: .whitespacesAndNewlines)) {
            return firstNumber > 0 ? "命中" : "未命中"
        }

        return metric.status.isPositive ? "命中" : "待判定"
    }

    static func explanation(for metric: TrainingFeedbackMetricItem) -> String {
        if metric.key == .shotTargetZoneHit {
            return "按这一脚射门的球门方向、落点和是否进目标区判断，不按多脚计数。"
        }

        if metric.status == .reference {
            return "这项置信度偏低，只帮助理解趋势，不作为正式扣分依据。"
        }

        return metric.explanation
    }
}

private struct TrainingFeedbackConfidenceReviewCard: View {
    let review: TrainingFeedbackConfidenceReview
    let hasVideoSource: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(review.summary)
                .font(AppTypography.body)
                .foregroundStyle(AppColors.textPrimary)
                .fixedSize(horizontal: false, vertical: true)

            if !review.trustedPoints.isEmpty {
                TrainingFeedbackLabeledListBlock(
                    title: "哪些结论更可信",
                    items: review.trustedPoints
                )
            }

            if !review.uncertainPoints.isEmpty {
                TrainingFeedbackLabeledListBlock(
                    title: "哪些只是低置信参考",
                    items: review.uncertainPoints
                )
            }

            VStack(alignment: .leading, spacing: 8) {
                Text("当前机位")
                    .font(AppTypography.captionMedium)
                    .foregroundStyle(AppColors.textSecondary)

                Text(hasVideoSource ? "当前视频可回放，机位基本够这次判断。" : "当前结果没有带入原视频，先参考分析结论。")
                    .font(AppTypography.body)
                    .foregroundStyle(AppColors.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            TrainingFeedbackLabeledListBlock(
                title: "下次怎么拍",
                items: review.shootingAdvice
            )
        }
    }
}

private struct TrainingFeedbackLabeledListBlock: View {
    let title: String
    let items: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(AppTypography.captionMedium)
                .foregroundStyle(AppColors.textSecondary)

            VStack(alignment: .leading, spacing: 8) {
                ForEach(items, id: \.self) { item in
                    TrainingFeedbackBulletRow(text: item)
                }
            }
        }
    }
}

private struct TrainingFeedbackDebugFieldBlock: View {
    let title: String
    let values: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(AppTypography.captionMedium)
                .foregroundStyle(AppColors.textSecondary)

            TrainingFeedbackMiniCard(padding: AppSpacing.compactPadding) {
                VStack(alignment: .leading, spacing: 6) {
                    if values.isEmpty {
                        Text("—")
                            .font(.system(size: 12, weight: .regular, design: .monospaced))
                            .foregroundStyle(AppColors.textTertiary)
                    } else {
                        ForEach(values, id: \.self) { value in
                            Text(value)
                                .font(.system(size: 12, weight: .regular, design: .monospaced))
                                .foregroundStyle(AppColors.textSecondary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
            }
        }
    }
}

struct TrainingFeedbackMiniCard<Content: View>: View {
    var padding: CGFloat = AppSpacing.compactPadding
    @ViewBuilder var content: Content

    init(padding: CGFloat = AppSpacing.compactPadding, @ViewBuilder content: () -> Content) {
        self.padding = padding
        self.content = content()
    }

    var body: some View {
        content
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(AppColors.cardSecondary)
            .overlay(
                RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                    .stroke(AppColors.stroke, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
    }
}

private enum FullMatchReportTab: String, CaseIterable {
    case overview
    case playerLock
    case outputs
    case reliability

    var title: String {
        switch self {
        case .overview:
            return "总览"
        case .playerLock:
            return "锁定"
        case .outputs:
            return "产出"
        case .reliability:
            return "可信度"
        }
    }
}

private struct FullMatchAnalysisContentView: View {
    let report: VideoAnalysisResponse.MatchAnalysisSnapshot
    @State private var selectedTab: FullMatchReportTab = .overview

    var body: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sectionGap) {
            heroCard
            tabSwitcher
            activeSection
        }
        .animation(.easeInOut(duration: 0.22), value: selectedTab)
    }

    private var heroCard: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack(alignment: .top, spacing: 14) {
                ZStack {
                    Circle()
                        .fill(AppColors.pitchGreen.opacity(0.18))
                        .frame(width: 54, height: 54)

                    Image(systemName: "sportscourt.fill")
                        .font(.system(size: 22, weight: .bold))
                        .foregroundStyle(AppColors.pitchGreen)
                }

                VStack(alignment: .leading, spacing: 6) {
                    Text(report.title)
                        .font(AppTypography.sectionTitle)
                        .foregroundStyle(AppColors.textPrimary)
                        .fixedSize(horizontal: false, vertical: true)

                    Text(report.summary.nonEmpty ?? "视频已读取。下一步先锁定目标球员，系统才会把传球、射门、接球和换人片段归属到同一个人。")
                        .font(AppTypography.body)
                        .foregroundStyle(AppColors.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }

            LazyVGrid(
                columns: [
                    GridItem(.flexible(), spacing: 10),
                    GridItem(.flexible(), spacing: 10),
                    GridItem(.flexible(), spacing: 10)
                ],
                spacing: 10
            ) {
                FullMatchMiniStat(title: "视频时长", value: report.durationText, tint: AppColors.matchBlue)
                FullMatchMiniStat(title: "分析方式", value: "先锁定球员", tint: AppColors.pitchGreen)
                FullMatchMiniStat(title: "视频上限", value: "140 分钟", tint: AppColors.energyGold)
            }
        }
        .padding(AppSpacing.cardPadding)
        .background(
            LinearGradient(
                colors: [
                    AppColors.pitchGreen.opacity(0.15),
                    AppColors.matchBlue.opacity(0.09),
                    AppColors.cardSecondary
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        )
        .overlay(
            RoundedRectangle(cornerRadius: AppCornerRadius.large, style: .continuous)
                .stroke(AppColors.pitchGreen.opacity(0.28), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.large, style: .continuous))
    }

    private var tabSwitcher: some View {
        HStack(spacing: 8) {
            ForEach(FullMatchReportTab.allCases, id: \.self) { tab in
                Button {
                    guard selectedTab != tab else { return }
                    Haptics.selection()
                    selectedTab = tab
                } label: {
                    Text(tab.title)
                        .font(AppTypography.captionMedium)
                        .foregroundStyle(selectedTab == tab ? AppColors.onAccent : AppColors.textSecondary)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                        .background(selectedTab == tab ? AppColors.accent : AppColors.backgroundSoft)
                        .clipShape(Capsule())
                }
                .buttonStyle(.plain)
            }
        }
    }

    @ViewBuilder
    private var activeSection: some View {
        switch selectedTab {
        case .overview:
            overviewSection
        case .playerLock:
            playerLockSection
        case .outputs:
            outputsSection
        case .reliability:
            reliabilitySection
        }
    }

    private var overviewSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sectionGap) {
            FullMatchCard(title: "当前状态", subtitle: "这不是比赛运动监测，而是长视频里锁定单一球员做技术分析。") {
                FullMatchList(items: [
                    "视频元数据已读取，下一步需要框选目标球员。",
                    "没有球员锁定前，不展示跑动距离、传球次数、射门次数等伪结果。",
                    "锁定后，系统会把关键传球、射门、接球和带球片段归属到同一个 player_id。"
                ])
            }

            FullMatchCard(title: "为什么必须先锁定", subtitle: "长视频里有队友、对手、裁判和镜头切换，不能靠画面中央默认目标。") {
                FullMatchList(items: [
                    "用第一帧或清晰帧框选整个人，避免把队友或背景行人计入目标球员。",
                    "补充球衣颜色、号码和惯用脚，帮助跨镜头重识别。",
                    "如果存在换人，标记上场和换下时间后，结果只按真实在场片段统计。"
                ])
            }
        }
    }

    private var playerLockSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sectionGap) {
            FullMatchCard(title: "锁定目标球员", subtitle: "下一版交互应该先让用户完成这三步，再正式出报告。") {
                FullMatchNumberedList(items: [
                    "框选目标球员：在目标球员清晰出现的画面框住整个人。",
                    "补充身份线索：填写球衣颜色、号码、左右脚和位置。",
                    "标记换人时间：如果不是踢满全场，标出上场、换下和中场节点。"
                ])
            }

            FullMatchCard(title: "长视频注意事项", subtitle: "最长 140 分钟，但越长越需要人工锚点。") {
                FullMatchList(items: [
                    "单镜头长片段优先；频繁切镜的视频需要多次补框。",
                    "人群拥挤或球员离镜头太远时，只输出参考级结论。",
                    "需要跑动距离时必须做球场尺度标定，否则只做技术事件和关键动作窗口。"
                ])
            }
        }
    }

    private var outputsSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sectionGap) {
            FullMatchCard(title: "锁定后会输出", subtitle: "只做和上传视频分析直接相关的内容。") {
                FullMatchList(items: [
                    "传球：出球脚、支撑脚、线路、接球队友关系和下一动作准备度。",
                    "射门：支撑脚、髋膝踝发力链、出球速度、射正/进门和目标区。",
                    "接球/带球：第一脚控制区、回稳时间、连续触球和变向质量。",
                    "时间线：按分钟列出该球员的关键传球、射门、丢球、抢断和换人节点。"
                ])
            }

            FullMatchCard(title: "生物力学口径", subtitle: "只在清晰关键动作窗口输出，避免普通模板冒充专业分析。") {
                FullMatchList(items: report.biomechanics.isEmpty ? [
                    "射门看支撑脚位置、髋-膝-踝发力链、躯干前压、触球部位和出球结果。",
                    "传球看支撑脚指向、触球面稳定、出球线路、接球队友关系和下一动作准备度。",
                    "跑动只在可追踪和可标定时输出，重点看加减速、变向角度和疲劳后动作变形。"
                ] : report.biomechanics)
            }
        }
    }

    private var reliabilitySection: some View {
        FullMatchCard(title: "可靠性说明", subtitle: "哪些能直接看，哪些必须补齐球员锁定和场地标定。") {
            FullMatchList(items: report.reliabilityNotes.isEmpty ? [
                "尚未锁定目标球员时，不输出正式统计结果。",
                "没有球场标定时，不输出精确米制跑动距离。",
                "事件统计会由目标球员轨迹、球轨迹和触球时序共同确认。"
            ] : report.reliabilityNotes)
        }
    }

    private func statsSection(title: String, subtitle: String, stats: [VideoAnalysisResponse.MatchStat], emptyText: String) -> some View {
        FullMatchCard(title: title, subtitle: subtitle) {
            if stats.isEmpty {
                Text(emptyText)
                    .font(AppTypography.body)
                    .foregroundStyle(AppColors.textSecondary)
            } else {
                LazyVGrid(
                    columns: [
                        GridItem(.flexible(), spacing: 12),
                        GridItem(.flexible(), spacing: 12)
                    ],
                    spacing: 12
                ) {
                    ForEach(stats) { stat in
                        FullMatchStatCard(stat: stat)
                    }
                }
            }
        }
    }
}

private struct FullMatchCard<Content: View>: View {
    let title: String
    let subtitle: String
    @ViewBuilder var content: Content

    var body: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 16) {
                TrainingFeedbackSectionHeader(title: title, subtitle: subtitle)
                content
            }
        }
    }
}

private struct FullMatchMiniStat: View {
    let title: String
    let value: String
    let tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Circle()
                .fill(tint)
                .frame(width: 7, height: 7)

            Text(title)
                .font(AppTypography.captionMedium)
                .foregroundStyle(AppColors.textSecondary)

            Text(value)
                .font(AppTypography.bodyMedium)
                .foregroundStyle(AppColors.textPrimary)
                .lineLimit(2)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(AppColors.background.opacity(0.62))
        .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
    }
}

private struct FullMatchStatCard: View {
    let stat: VideoAnalysisResponse.MatchStat

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(stat.title)
                .font(AppTypography.captionMedium)
                .foregroundStyle(AppColors.textSecondary)

            Text(stat.value)
                .font(AppTypography.cardTitle)
                .foregroundStyle(AppColors.textPrimary)
                .fixedSize(horizontal: false, vertical: true)

            if !stat.detail.isEmpty {
                Text(stat.detail)
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            if !stat.status.isEmpty {
                TrainingFeedbackTag(text: statusText(stat.status))
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, minHeight: 154, alignment: .topLeading)
        .background(AppColors.backgroundSoft)
        .overlay(
            RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                .stroke(AppColors.stroke, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
    }

    private func statusText(_ status: String) -> String {
        if status.contains("requires") {
            return "待补齐"
        }
        return status
    }
}

private struct FullMatchSegmentRow: View {
    let segment: VideoAnalysisResponse.MatchSegment

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(segment.title)
                    .font(AppTypography.bodyMedium)
                    .foregroundStyle(AppColors.textPrimary)

                Spacer(minLength: 0)

                TrainingFeedbackTag(text: segment.minutes)
            }

            if !segment.summary.isEmpty {
                Text(segment.summary)
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(14)
        .background(AppColors.backgroundSoft)
        .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
    }
}

private struct FullMatchTimelineRow: View {
    let item: VideoAnalysisResponse.MatchTimelineItem

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Text(item.minute)
                .font(AppTypography.captionMedium)
                .foregroundStyle(AppColors.onAccent)
                .padding(.horizontal, 9)
                .padding(.vertical, 6)
                .background(AppColors.accent)
                .clipShape(Capsule())

            VStack(alignment: .leading, spacing: 4) {
                Text(item.label)
                    .font(AppTypography.bodyMedium)
                    .foregroundStyle(AppColors.textPrimary)

                Text(item.detail)
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }
}

private struct FullMatchList: View {
    let items: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            if items.isEmpty {
                Text("暂无可展示内容。")
                    .font(AppTypography.body)
                    .foregroundStyle(AppColors.textSecondary)
            } else {
                ForEach(items, id: \.self) { item in
                    TrainingFeedbackBulletRow(text: item)
                }
            }
        }
    }
}

private struct FullMatchNumberedList: View {
    let items: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            ForEach(Array(items.enumerated()), id: \.offset) { index, item in
                HStack(alignment: .top, spacing: 10) {
                    Text("\(index + 1)")
                        .font(AppTypography.captionMedium)
                        .foregroundStyle(AppColors.onAccent)
                        .frame(width: 24, height: 24)
                        .background(AppColors.accent)
                        .clipShape(Circle())

                    Text(item)
                        .font(AppTypography.body)
                        .foregroundStyle(AppColors.textPrimary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }
}
