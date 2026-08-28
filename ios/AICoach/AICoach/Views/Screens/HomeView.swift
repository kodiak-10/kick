import SwiftUI

struct HomeView: View {
    @EnvironmentObject private var appState: AppState

    private let flowSteps: [(title: String, detail: String)] = [
        ("选择模板", "先挑选射门、传球或停球中的一个训练方向。"),
        ("开始分析", "进入上传页，继续使用当前模板完成单机位流程。"),
        ("查看结果", "回看总分、分项分、核心问题和错误时间点。"),
        ("复盘优化", "根据建议重拍，再对比下一次的变化。")
    ]

    private let shortcutTips: [String] = [
        "点击模板卡片即可切换当前训练方向。",
        "主按钮会带你进入上传与分析流程。",
        "结果页会优先展示可执行的纠正建议。"
    ]

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 22) {
                headerSection
                templateSection
                startSection
                flowSection
                footerSection
            }
            .padding(20)
            .padding(.bottom, 32)
        }
        .background(AppTheme.background.ignoresSafeArea())
    }

    private var headerSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Kick AI")
                .font(.system(size: 34, weight: .bold, design: .rounded))
                .foregroundStyle(AppTheme.text)

            Text("足球训练分析面板")
                .font(.headline)
                .foregroundStyle(AppTheme.muted)

            Text("先选模板，再开始单机位分析。")
                .font(.subheadline)
                .foregroundStyle(AppTheme.muted)
                .lineLimit(2)

            HStack(spacing: 10) {
                StatusPill(text: appState.selectedGoal.displayTitle, tint: AppTheme.accent)
                StatusPill(text: appState.quotaText(), tint: appState.isPro ? AppTheme.success : AppTheme.warning)
            }
        }
    }

    private var templateSection: some View {
        VStack(alignment: .leading, spacing: 14) {
            SectionLabel(
                title: "训练模板",
                subtitle: "Template selection"
            )

            VStack(spacing: 14) {
                ForEach(TrainingGoal.allCases) { goal in
                    Button {
                        appState.selectedGoal = goal
                    } label: {
                        TrainingTemplateCard(goal: goal, isSelected: appState.selectedGoal == goal)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private var startSection: some View {
        FrostedCard {
            SectionLabel(
                title: "开始分析",
                subtitle: "Main action"
            )

            PrimaryButton(
                title: appState.canStartAnalysis ? "开始分析当前模板" : "免费次数已用完",
                subtitle: appState.canStartAnalysis ? "当前模板：\(appState.selectedGoal.displayTitle)" : "升级 Pro 后可以继续分析"
            ) {
                appState.startAnalysisFlow()
            }
        }
    }

    private var flowSection: some View {
        FrostedCard {
            SectionLabel(
                title: "开始流程",
                subtitle: "最多 4 步"
            )

            VStack(alignment: .leading, spacing: 12) {
                ForEach(Array(flowSteps.enumerated()), id: \.offset) { index, step in
                    HStack(alignment: .top, spacing: 12) {
                        Text("\(index + 1)")
                            .font(.caption.weight(.bold))
                            .foregroundStyle(AppTheme.warning)
                            .frame(width: 24, height: 24)
                            .background(Circle().fill(AppTheme.warning.opacity(0.16)))

                        VStack(alignment: .leading, spacing: 4) {
                            Text(step.title)
                                .font(.subheadline.weight(.semibold))
                            Text(step.detail)
                                .font(.caption)
                                .foregroundStyle(AppTheme.muted)
                                .lineLimit(2)
                        }

                        Spacer(minLength: 0)
                    }
                }
            }
        }
    }

    private var footerSection: some View {
        LazyVGrid(
            columns: [
                GridItem(.flexible(), spacing: 14),
                GridItem(.flexible(), spacing: 14)
            ],
            spacing: 14
        ) {
            shortcutsCard
            lastSessionCard
        }
    }

    private var shortcutsCard: some View {
        FrostedCard {
            SectionLabel(
                title: "快捷键提示",
                subtitle: "Quick tips"
            )

            VStack(alignment: .leading, spacing: 10) {
                ForEach(Array(shortcutTips.enumerated()), id: \.offset) { index, tip in
                    HStack(alignment: .top, spacing: 10) {
                        Text("\(index + 1)")
                            .font(.caption.weight(.bold))
                            .foregroundStyle(AppTheme.accent)
                            .frame(width: 22, height: 22)
                            .background(Circle().fill(AppTheme.accent.opacity(0.16)))
                        Text(tip)
                            .font(.caption)
                            .foregroundStyle(AppTheme.muted)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }
        }
    }

    private var lastSessionCard: some View {
        Button {
            if let record = appState.recentRecord {
                appState.showRecord(record.id)
            }
        } label: {
            FrostedCard {
                SectionLabel(
                    title: "最近一次训练",
                    subtitle: "Last session"
                )

                if let record = appState.recentRecord {
                    HStack(alignment: .top, spacing: 14) {
                        sessionPreview(for: record)

                        VStack(alignment: .leading, spacing: 8) {
                            Text(record.displayActionDisplayName)
                                .font(.headline.weight(.semibold))
                            Text(record.shouldShowFormalScore ? record.summary : record.scoreSubtitle)
                                .font(.subheadline)
                                .foregroundStyle(AppTheme.muted)
                                .lineLimit(3)

                            HStack(spacing: 8) {
                                StatusPill(
                                    text: record.shouldShowFormalScore ? record.gradeTitle : record.reportTagText,
                                    tint: previewTint(for: record)
                                )
                                StatusPill(text: record.qualityStatus.title, tint: qualityTint(for: record))
                            }
                        }

                        Spacer(minLength: 0)
                    }
                } else {
                    Text("还没有分析结果")
                        .font(.headline)
                    Text("完成一次分析后，这里会展示你的最近一次训练。")
                        .font(.subheadline)
                        .foregroundStyle(AppTheme.muted)
                }
            }
        }
        .buttonStyle(.plain)
    }

    @ViewBuilder
    private func sessionPreview(for record: AnalysisRecord) -> some View {
        if record.shouldShowFormalScore {
            ScoreRingView(score: record.score.overall, level: record.score.level)
        } else {
            RoundedRectangle(cornerRadius: 22, style: .continuous)
                .fill(AppTheme.thumbnailGradient(for: record.thumbnailStyle))
                .frame(width: 110, height: 110)
                .overlay(
                    VStack(alignment: .leading, spacing: 8) {
                        Image(systemName: record.reportState.symbol)
                            .font(.headline)
                        Spacer()
                        Text(record.gradeTitle)
                            .font(.headline.weight(.semibold))
                        Text(record.scoreSubtitle)
                            .font(.caption2)
                            .foregroundStyle(.white.opacity(0.84))
                            .lineLimit(2)
                    }
                    .padding(12)
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
                )
        }
    }

    private func previewTint(for record: AnalysisRecord) -> Color {
        if record.shouldShowFormalScore {
            return AppTheme.resultColor(for: record.score.level)
        }

        switch record.reportState {
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

    private func qualityTint(for record: AnalysisRecord) -> Color {
        switch record.qualityStatus {
        case .good:
            return AppTheme.success
        case .limited:
            return AppTheme.warning
        case .poor:
            return AppTheme.danger
        }
    }
}
