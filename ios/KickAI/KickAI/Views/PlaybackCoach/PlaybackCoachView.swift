import SwiftUI

struct PlaybackCoachView: View {
    @EnvironmentObject private var sessionManager: SessionManager
    let result: AnalysisResult
    let videoURL: URL?
    let hasProfessionalAccessOverride: Bool?

    @State private var selectedIssueID: UUID?
    @State private var showPaywall = false

    init(
        result: AnalysisResult,
        videoURL: URL? = nil,
        hasProfessionalAccessOverride: Bool? = nil
    ) {
        self.result = result
        self.videoURL = videoURL
        self.hasProfessionalAccessOverride = hasProfessionalAccessOverride
    }

    private var hasProfessionalAccess: Bool {
        hasProfessionalAccessOverride ?? sessionManager.hasProfessionalAccess(for: result.id)
    }

    private var playbackIssues: [PlaybackIssue] {
        result.videoReviewData.issues.isEmpty
            ? PlaybackIssue.fallbackIssues(for: result)
            : result.videoReviewData.issues
    }

    private var selectedIssue: PlaybackIssue? {
        let issues = playbackIssues
        guard !issues.isEmpty else { return nil }

        if let selectedIssueID,
           let issue = issues.first(where: { $0.id == selectedIssueID }),
           !isLocked(issue, index: issueIndex(for: issue)) {
            return issue
        }

        return issues.first(where: { !isLocked($0, index: issueIndex(for: $0)) }) ?? issues.first
    }

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: AppSpacing.sectionGap) {
                introCard

                PlaybackCoachContent(
                    result: result,
                    hasProAccess: hasProfessionalAccess,
                    videoURL: videoURL,
                    selectedIssueID: $selectedIssueID,
                    showsOpenCoachButton: false,
                    onLockedIssueTap: { showPaywall = true }
                )

                if let selectedIssue {
                    deepDiveCard(issue: selectedIssue)
                } else {
                    EmptyStateView(
                        title: "暂无可展开的问题点",
                        subtitle: "当前视频回看暂无可用时间点。",
                        systemImage: "play.rectangle"
                    )
                }

                if hasProfessionalAccess {
                    proSummaryCard
                } else {
                    upgradeCard
                }
            }
            .padding(.horizontal, AppSpacing.screenPadding)
            .padding(.top, 12)
            .padding(.bottom, 28)
        }
        .kickScreenBackground()
        .navigationTitle("动作回看指导")
        .navigationBarTitleDisplayMode(.inline)
        .kickNavigationBar()
        .navigationDestination(isPresented: $showPaywall) {
            PaywallView()
        }
    }

    private var introCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("逐段纠错")
                            .font(AppTypography.pageTitle)
                            .foregroundStyle(AppColors.textPrimary)

                        Text("按时间点回看每个动作节点，定位问题并理解为什么会影响动作表现。")
                            .font(AppTypography.body)
                            .foregroundStyle(AppColors.textSecondary)
                    }

                    Spacer()

                    if hasProfessionalAccess {
                        ProBadge(title: "PRO")
                    } else {
                        Text("免费版")
                            .font(AppTypography.captionMedium)
                            .foregroundStyle(AppColors.textSecondary)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(AppColors.backgroundSoft)
                            .clipShape(Capsule())
                    }
                }

                HStack(spacing: 14) {
                    StatPill(
                        title: "关键时间点",
                        value: "\(playbackIssues.count)"
                    )

                    StatPill(
                        title: "可见问题点",
                        value: hasProfessionalAccess ? "全部" : "1"
                    )

                    StatPill(
                        title: "原视频",
                        value: "\(String(format: "%.1fs", result.videoReviewData.duration))"
                    )
                }
            }
        }
    }

    private func deepDiveCard(issue: PlaybackIssue) -> some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("问题拆解")
                            .font(AppTypography.cardTitle)
                            .foregroundStyle(AppColors.textPrimary)

                        Text("选中时间点后，这里会同步切换具体说明。")
                            .font(AppTypography.caption)
                            .foregroundStyle(AppColors.textSecondary)
                    }

                    Spacer()

                    Text(issue.timeLabel)
                        .font(AppTypography.captionMedium)
                        .foregroundStyle(AppColors.onAccent)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background(AppColors.accent)
                        .clipShape(Capsule())
                }

                DetailSection(
                    title: "问题名称",
                    value: issue.title
                )

                DetailSection(
                    title: "出现阶段",
                    value: issue.phase.displayName
                )

                DetailBlock(
                    title: "为什么会影响动作表现",
                    text: issue.explanation
                )

                DetailBlock(
                    title: "应该如何调整",
                    text: issue.fixAdvice
                )

                DetailBlock(
                    title: "建议训练内容",
                    text: issue.trainingAdvice
                )
            }
        }
    }

    private var proSummaryCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("专业版已解锁完整回看")
                            .font(AppTypography.cardTitle)
                            .foregroundStyle(AppColors.textPrimary)

                        Text("上方时间点可自由切换，点击任意节点即可查看对应深度拆解。")
                            .font(AppTypography.body)
                            .foregroundStyle(AppColors.textSecondary)
                    }

                    Spacer()

                    ProBadge(title: "PRO")
                }
            }
        }
    }

    private var upgradeCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("解锁完整逐段回看指导")
                            .font(AppTypography.cardTitle)
                            .foregroundStyle(AppColors.textPrimary)

                        Text("专业版可解锁全部关键时间点、深度纠错说明和训练建议。")
                            .font(AppTypography.body)
                            .foregroundStyle(AppColors.textSecondary)
                    }

                    Spacer()

                    ProBadge()
                }

                PrimaryButton(title: "升级专业版", systemImage: "crown.fill") {
                    showPaywall = true
                }
            }
        }
    }

    private func issueIndex(for issue: PlaybackIssue) -> Int {
        playbackIssues.firstIndex(where: { $0.id == issue.id }) ?? 0
    }

    private func isLocked(_ issue: PlaybackIssue, index: Int) -> Bool {
        !hasProfessionalAccess && (index >= result.videoReviewData.freeIssueLimit || issue.isProOnly)
    }
}

private struct StatPill: View {
    let title: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(AppTypography.caption)
                .foregroundStyle(AppColors.textSecondary)

            Text(value)
                .font(AppTypography.bodyMedium)
                .foregroundStyle(AppColors.textPrimary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(AppColors.backgroundSoft)
        .overlay(
            RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                .stroke(AppColors.stroke, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
    }
}

private struct DetailSection: View {
    let title: String
    let value: String

    var body: some View {
        HStack(alignment: .top, spacing: 14) {
            Text(title)
                .font(AppTypography.captionMedium)
                .foregroundStyle(AppColors.textSecondary)
                .frame(width: 72, alignment: .leading)

            Text(value)
                .font(AppTypography.bodyMedium)
                .foregroundStyle(AppColors.textPrimary)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

private struct DetailBlock: View {
    let title: String
    let text: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(AppTypography.captionMedium)
                .foregroundStyle(AppColors.textSecondary)

            Text(text)
                .font(AppTypography.body)
                .foregroundStyle(AppColors.textSecondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}
