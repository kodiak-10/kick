import SwiftUI

struct ResultReportScreen: View {
    let report: ResultReport
    let videoDuration: Double?
    let videoURL: URL?
    let videoLabel: String?
    let hasProAccess: Bool
    let isCurrentLatestResult: Bool
    let onOpenUpload: () -> Void
    let onOpenHistory: () -> Void
    let onOpenPaywall: () -> Void
    let onOpenPlaybackCoach: () -> Void

    private var viewModel: TrainingFeedbackViewModel {
        TrainingFeedbackViewModel(report: report, videoDuration: videoDuration)
    }

    private var isAnomalousResult: Bool {
        report.summary.localizedCaseInsensitiveContains("异常") ||
            report.summaryTag.localizedCaseInsensitiveContains("异常") ||
            report.improvementFindings.contains(where: { $0.title.localizedCaseInsensitiveContains("异常") })
    }

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: AppSpacing.sectionGap) {
                TrainingFeedbackContentView(
                    viewModel: viewModel,
                    hasProAccess: hasProAccess,
                    videoURL: videoURL,
                    videoLabel: videoLabel,
                    isCurrentLatestResult: isCurrentLatestResult
                )
                actionSection
            }
            .padding(.horizontal, AppSpacing.screenPadding)
            .padding(.top, 12)
            .padding(.bottom, 28)
        }
        .kickScreenBackground()
    }

    private var actionSection: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 14) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(isAnomalousResult ? "本次结果存在异常" : "这次已经记住了")
                        .font(AppTypography.cardTitle)
                        .foregroundStyle(AppColors.textPrimary)

                    Text(isAnomalousResult ? "当前记录已避免展示错误组合，建议直接重新分析当前视频。" : (isCurrentLatestResult ? "已自动保存到历史记录，回到历史页就能按月历继续对比。" : "这是历史中的一次训练反馈，也可以继续回到分析页再练一次。"))
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textSecondary)
                }

                PrimaryButton(
                    title: isAnomalousResult ? "重新分析" : "再练一次",
                    systemImage: "arrow.clockwise"
                ) {
                    onOpenUpload()
                }

                SecondaryButton(title: "查看历史记录", systemImage: "clock.arrow.circlepath") {
                    onOpenHistory()
                }

                if hasProAccess {
                    SecondaryButton(title: "查看完整回看指导", systemImage: "play.rectangle.fill") {
                        onOpenPlaybackCoach()
                    }
                } else {
                    SecondaryButton(title: "升级专业版", systemImage: "crown.fill") {
                        onOpenPaywall()
                    }
                }
            }
        }
    }
}
