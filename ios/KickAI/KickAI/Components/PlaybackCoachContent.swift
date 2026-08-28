import AVKit
import SwiftUI

struct PlaybackCoachContent: View {
    let result: AnalysisResult
    let hasProAccess: Bool
    let videoURL: URL?
    @Binding var selectedIssueID: UUID?
    var showsOpenCoachButton: Bool = false
    var onOpenFullCoach: (() -> Void)?
    var onLockedIssueTap: (() -> Void)?

    private var reviewData: VideoReviewData {
        result.videoReviewData
    }

    private var issues: [PlaybackIssue] {
        reviewData.issues.isEmpty ? PlaybackIssue.fallbackIssues(for: result) : reviewData.issues
    }

    private var accessibleLimit: Int {
        hasProAccess ? issues.count : min(reviewData.freeIssueLimit, issues.count)
    }

    private var reviewDuration: Double {
        max(reviewData.duration, issues.last?.time ?? 0)
    }

    private var selectedIssue: PlaybackIssue? {
        if let selectedIssueID,
           let issue = issues.first(where: { $0.id == selectedIssueID }),
           !isLocked(issue, index: issueIndex(for: issue)) {
            return issue
        }

        return issues.first(where: { !isLocked($0, index: issueIndex(for: $0)) }) ?? issues.first
    }

    private var selectedIssueProgress: Double {
        guard let selectedIssue, reviewDuration > 0 else { return 0 }
        return min(max(selectedIssue.time / reviewDuration, 0), 1)
    }

    var body: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 18) {
                headerView

                    PlaybackVideoCard(
                        result: result,
                        selectedIssue: selectedIssue,
                        progress: selectedIssueProgress,
                        videoURL: videoURL
                    )

                PlaybackIssueRail(
                    issues: issues,
                    selectedIssueID: $selectedIssueID,
                    accessibleLimit: accessibleLimit,
                    hasProAccess: hasProAccess,
                    onLockedIssueTap: onLockedIssueTap
                )

                PlaybackIssueSummaryCard(
                    issue: selectedIssue,
                    hasProAccess: hasProAccess
                )

                if showsOpenCoachButton {
                    SecondaryButton(title: "查看完整回看指导", systemImage: "play.rectangle.fill") {
                        onOpenFullCoach?()
                    }
                }
            }
            .onAppear {
                if selectedIssueID == nil {
                    selectedIssueID = selectedIssue?.id
                }
            }
        }
    }

    private var headerView: some View {
        HStack(alignment: .top, spacing: 12) {
            VStack(alignment: .leading, spacing: 8) {
                Text("动作回看指导")
                    .font(AppTypography.cardTitle)
                    .foregroundStyle(AppColors.textPrimary)

                Text(hasProAccess ? "可逐段查看全部关键问题点" : "免费版仅开放 1 个关键问题点")
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textSecondary)
            }

            Spacer(minLength: 0)

            if hasProAccess {
                ProBadge(title: "PRO")
            } else {
                Text("1 / \(max(1, issues.count))")
                    .font(AppTypography.captionMedium)
                    .foregroundStyle(AppColors.textSecondary)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(AppColors.backgroundSoft)
                    .clipShape(Capsule())
            }
        }
    }

    private func issueIndex(for issue: PlaybackIssue) -> Int {
        issues.firstIndex(where: { $0.id == issue.id }) ?? 0
    }

    private func isLocked(_ issue: PlaybackIssue, index: Int) -> Bool {
        !hasProAccess && (index >= reviewData.freeIssueLimit || issue.isProOnly)
    }
}

private struct PlaybackVideoCard: View {
    let result: AnalysisResult
    let selectedIssue: PlaybackIssue?
    let progress: Double
    let videoURL: URL?

    @StateObject private var controller: TrainingFeedbackVideoPlaybackController

    init(
        result: AnalysisResult,
        selectedIssue: PlaybackIssue?,
        progress: Double,
        videoURL: URL?
    ) {
        self.result = result
        self.selectedIssue = selectedIssue
        self.progress = progress
        self.videoURL = videoURL
        _controller = StateObject(
            wrappedValue: TrainingFeedbackVideoPlaybackController(
                videoURL: videoURL,
                duration: result.videoReviewData.duration
            )
        )
    }

    private var stageLabel: String {
        selectedIssue?.phase.displayName ?? "待选择问题点"
    }

    private var issueLabel: String {
        selectedIssue?.title ?? "点击下方时间点定位问题"
    }

    var body: some View {
        ZStack {
            if controller.hasVideo {
                VideoPlayer(player: controller.player)
                    .overlay(alignment: .topLeading) {
                        videoHeader
                            .padding(14)
                    }
                    .overlay(alignment: .bottomLeading) {
                        videoFooter
                            .padding(14)
                    }
                    .onAppear {
                        seekToSelectedIssue()
                    }
                    .onChange(of: selectedIssue?.id) { _, _ in
                        seekToSelectedIssue()
                    }
            } else {
                placeholderSurface
            }
        }
        .frame(height: 230)
        .overlay(
            RoundedRectangle(cornerRadius: AppCornerRadius.large, style: .continuous)
                .stroke(AppColors.strongStroke, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.large, style: .continuous))
    }

    private var placeholderSurface: some View {
        ZStack {
            LinearGradient(
                colors: [
                    AppColors.backgroundSoft,
                    AppColors.cardSecondary,
                    AppColors.background
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            VStack(alignment: .leading, spacing: 14) {
                videoHeader

                Spacer(minLength: 0)

                HStack(alignment: .bottom) {
                    VStack(alignment: .leading, spacing: 10) {
                        HStack(spacing: 8) {
                            Image(systemName: selectedIssue?.phase.symbolName ?? "play.fill")
                                .font(.system(size: 14, weight: .semibold))
                            Text(stageLabel)
                                .font(AppTypography.headline)
                        }
                        .foregroundStyle(AppColors.textPrimary)

                        Text(issueLabel)
                            .font(AppTypography.body)
                            .foregroundStyle(AppColors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    Spacer()

                    Button {
                        controller.togglePlayPause()
                    } label: {
                        ZStack {
                            Circle()
                                .stroke(AppColors.textPrimary.opacity(0.08), lineWidth: 8)
                            Circle()
                                .trim(from: 0, to: max(progress, 0.08))
                                .stroke(
                                    AppColors.accent,
                                    style: StrokeStyle(lineWidth: 8, lineCap: .round)
                                )
                                .rotationEffect(.degrees(-90))
                            Image(systemName: "play.fill")
                                .font(.system(size: 18, weight: .semibold))
                                .foregroundStyle(AppColors.textPrimary)
                        }
                        .frame(width: 64, height: 64)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(18)
        }
    }

    private var videoHeader: some View {
        HStack {
            VStack(alignment: .leading, spacing: 6) {
                Text(result.motionType)
                    .font(AppTypography.captionMedium)
                    .foregroundStyle(controller.hasVideo ? Color.white.opacity(0.82) : AppColors.textSecondary)

                Text(controller.hasVideo ? "原视频回看" : "原视频未找到")
                    .font(AppTypography.sectionTitle)
                    .foregroundStyle(controller.hasVideo ? Color.white : AppColors.textPrimary)
            }

            Spacer()

            Text(selectedIssue?.timeLabel ?? "0.0s")
                .font(AppTypography.captionMedium)
                .foregroundStyle(AppColors.onAccent)
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(AppColors.accent)
                .clipShape(Capsule())
        }
    }

    private var videoFooter: some View {
        HStack(alignment: .bottom) {
            VStack(alignment: .leading, spacing: 8) {
                HStack(spacing: 8) {
                    Image(systemName: selectedIssue?.phase.symbolName ?? "play.fill")
                        .font(.system(size: 14, weight: .semibold))
                    Text(stageLabel)
                        .font(AppTypography.headline)
                }

                Text(issueLabel)
                    .font(AppTypography.body)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .foregroundStyle(Color.white)
            .padding(10)
            .background(Color.black.opacity(0.44))
            .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.small, style: .continuous))

            Spacer()
        }
    }

    private func seekToSelectedIssue() {
        guard let selectedIssue else { return }
        controller.seek(to: selectedIssue.time)
    }
}

private struct PlaybackIssueRail: View {
    let issues: [PlaybackIssue]
    @Binding var selectedIssueID: UUID?
    let accessibleLimit: Int
    let hasProAccess: Bool
    let onLockedIssueTap: (() -> Void)?

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 12) {
                ForEach(Array(issues.enumerated()), id: \.element.id) { index, issue in
                    PlaybackIssueChip(
                        issue: issue,
                        isSelected: selectedIssueID == issue.id,
                        isLocked: isLocked(index: index, issue: issue)
                    ) {
                        if isLocked(index: index, issue: issue) {
                            onLockedIssueTap?()
                        } else {
                            withAnimation(.easeInOut(duration: 0.2)) {
                                selectedIssueID = issue.id
                            }
                        }
                    }
                }
            }
            .padding(.vertical, 2)
        }
    }

    private func isLocked(index: Int, issue: PlaybackIssue) -> Bool {
        !hasProAccess && (index >= accessibleLimit || issue.isProOnly)
    }
}

private struct PlaybackIssueChip: View {
    let issue: PlaybackIssue
    let isSelected: Bool
    let isLocked: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Text(issue.timeLabel)
                        .font(AppTypography.captionMedium)
                        .foregroundStyle(isLocked ? AppColors.textTertiary : AppColors.onAccent)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(isLocked ? AppColors.backgroundElevated : AppColors.accent)
                        .clipShape(Capsule())

                    Spacer(minLength: 8)

                    if isLocked {
                        Image(systemName: "lock.fill")
                            .font(.system(size: 10, weight: .semibold))
                            .foregroundStyle(isSelected ? AppColors.textPrimary : AppColors.textSecondary)
                    }
                }

                Text(issue.title)
                    .font(AppTypography.bodyMedium)
                    .foregroundStyle(isLocked ? AppColors.textSecondary : AppColors.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)
                    .lineLimit(2)

                HStack(spacing: 6) {
                    Image(systemName: issue.phase.symbolName)
                        .font(.system(size: 10, weight: .semibold))
                    Text(issue.phase.displayName)
                        .font(AppTypography.caption)
                }
                .foregroundStyle(isLocked ? AppColors.textTertiary : AppColors.textSecondary)
            }
            .frame(width: 148, alignment: .leading)
            .padding(14)
            .background(
                LinearGradient(
                    colors: [
                        isSelected ? AppColors.cardSecondary : AppColors.backgroundSoft,
                        AppColors.card
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            )
            .overlay(
                RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                    .stroke(isSelected ? AppColors.strongStroke : AppColors.stroke, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
            .overlay {
                if isLocked {
                    RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                        .fill(Color.black.opacity(0.28))
                        .overlay {
                            VStack(spacing: 8) {
                                Image(systemName: "lock.fill")
                                    .font(.system(size: 18, weight: .semibold))
                                    .foregroundStyle(AppColors.textPrimary)

                                Text("PRO")
                                    .font(AppTypography.captionMedium)
                                    .foregroundStyle(AppColors.onAccent)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(AppColors.accent)
                                    .clipShape(Capsule())
                            }
                        }
                }
            }
        }
        .buttonStyle(.plain)
    }
}

private struct PlaybackIssueSummaryCard: View {
    let issue: PlaybackIssue?
    let hasProAccess: Bool

    var body: some View {
        DarkCard(padding: 16) {
            if let issue {
                VStack(alignment: .leading, spacing: 14) {
                    HStack {
                        Text("当前问题提示")
                            .font(AppTypography.cardTitle)
                            .foregroundStyle(AppColors.textPrimary)

                        Spacer()

                        if !hasProAccess && issue.isProOnly {
                            Text("专业版专属")
                                .font(AppTypography.captionMedium)
                                .foregroundStyle(AppColors.onAccent)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 5)
                                .background(AppColors.accent)
                                .clipShape(Capsule())
                        } else {
                            Text(issue.phase.displayName)
                                .font(AppTypography.captionMedium)
                                .foregroundStyle(AppColors.textSecondary)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 5)
                                .background(AppColors.backgroundSoft)
                                .clipShape(Capsule())
                        }
                    }

                    InfoRow(title: "问题名称", value: issue.title)
                    InfoRow(title: "所属阶段", value: issue.phase.displayName)

                    VStack(alignment: .leading, spacing: 8) {
                        Text("问题简述")
                            .font(AppTypography.captionMedium)
                            .foregroundStyle(AppColors.textSecondary)

                        Text(issue.shortHint)
                            .font(AppTypography.body)
                            .foregroundStyle(AppColors.textPrimary)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        Text("一句短指导")
                            .font(AppTypography.captionMedium)
                            .foregroundStyle(AppColors.textSecondary)

                        Text(issue.fixAdvice)
                            .font(AppTypography.body)
                            .foregroundStyle(AppColors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }
        }
    }
}

private struct InfoRow: View {
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
