import Foundation
import SwiftUI

struct VideoAnalysisResultView: View {
    let response: VideoAnalysisResponse
    let selectedAction: AnalysisActionChoice?
    let videoURL: URL?
    let videoDuration: Double?
    let videoLabel: String?
    let hasProAccess: Bool
    let onRestart: () -> Void
    let onOpenPaywall: () -> Void

    private var viewModel: TrainingFeedbackViewModel {
        TrainingFeedbackViewModel(
            response: response,
            selectedAction: selectedAction,
            videoDuration: videoDuration
        )
    }

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: AppSpacing.sectionGap) {
                if viewModel.routeMismatchMessage == nil {
                    TrainingFeedbackContentView(
                        viewModel: viewModel,
                        hasProAccess: hasProAccess,
                        videoURL: videoURL,
                        videoLabel: videoLabel
                    )
                }
                actionSection
            }
            .padding(.horizontal, AppSpacing.screenPadding)
            .padding(.top, 12)
            .padding(.bottom, 28)
        }
        .kickScreenBackground()
        .navigationTitle("训练反馈")
        .navigationBarTitleDisplayMode(.inline)
        .kickNavigationBar()
    }

    private var actionSection: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 14) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(viewModel.routeMismatchMessage != nil ? "当前分析没有按你选择的动作类型执行" : viewModel.isResultAnomalous ? "本次结果存在异常" : "这次已经记住了")
                        .font(AppTypography.cardTitle)
                        .foregroundStyle(AppColors.textPrimary)

                    if viewModel.routeMismatchMessage != nil {
                        Text("本次分析动作：\(viewModel.actionName)")
                            .font(AppTypography.captionMedium)
                            .foregroundStyle(AppColors.textSecondary)
                    }

                    Text(viewModel.routeMismatchMessage != nil
                         ? "请重新按“传球 / 射门”按钮发起分析。"
                         : viewModel.isResultAnomalous
                         ? "当前结果已避免展示错误组合，建议直接重新分析当前视频。"
                         : "已自动保存到历史记录，稍后去历史页按日历继续复盘。")
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textSecondary)
                }

                PrimaryButton(
                    title: viewModel.routeMismatchMessage != nil ? "重新分析" : viewModel.isResultAnomalous ? "重新分析" : "再练一次",
                    systemImage: "arrow.clockwise"
                ) {
                    onRestart()
                }

#if DEBUG
                if viewModel.routeMismatchMessage != nil {
                    Text(viewModel.routeDebugText)
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textTertiary)
                        .fixedSize(horizontal: false, vertical: true)
                }
#endif

                if !hasProAccess && !viewModel.isResultAnomalous && viewModel.routeMismatchMessage == nil {
                    SecondaryButton(title: "升级专业版", systemImage: "crown.fill") {
                        onOpenPaywall()
                    }
                }
            }
        }
    }

}
