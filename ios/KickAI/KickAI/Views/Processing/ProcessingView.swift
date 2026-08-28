import SwiftUI

struct ProcessingView: View {
    @EnvironmentObject private var sessionManager: SessionManager
    @StateObject private var viewModel = ProcessingViewModel()
    @State private var showResult = false
    @State private var shouldSpin = false

    var body: some View {
        VStack(spacing: 28) {
            Spacer(minLength: 24)

            ZStack {
                Circle()
                    .stroke(AppColors.textPrimary.opacity(0.08), lineWidth: 14)
                    .frame(width: 150, height: 150)

                Circle()
                    .trim(from: 0, to: max(viewModel.progress, 0.08))
                    .stroke(
                        AppColors.accent,
                        style: StrokeStyle(lineWidth: 14, lineCap: .round)
                    )
                    .rotationEffect(.degrees(shouldSpin ? 360 : -90))
                    .frame(width: 150, height: 150)
                    .animation(.linear(duration: 3).repeatForever(autoreverses: false), value: shouldSpin)

                VStack(spacing: 8) {
                    Text("\(Int(viewModel.progress * 100))%")
                        .font(AppTypography.metric)
                        .foregroundStyle(AppColors.textPrimary)

                    Text("分析进行中")
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textSecondary)
                }
            }

            VStack(spacing: 12) {
                Text("正在生成你的动作报告")
                    .font(AppTypography.pageTitle)
                    .foregroundStyle(AppColors.textPrimary)

                Text("系统正在逐步处理视频、识别动作阶段并整理结果。")
                    .font(AppTypography.body)
                    .foregroundStyle(AppColors.textSecondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 24)
            }

            DarkCard {
                VStack(spacing: 18) {
                    ForEach(Array(viewModel.steps.enumerated()), id: \.element.id) { index, step in
                        HStack(spacing: 14) {
                            stepIndicator(for: viewModel.status(for: index))

                            VStack(alignment: .leading, spacing: 6) {
                                Text(step.title)
                                    .font(AppTypography.headline)
                                    .foregroundStyle(AppColors.textPrimary)

                                Text(step.subtitle)
                                    .font(AppTypography.caption)
                                    .foregroundStyle(AppColors.textSecondary)
                            }

                            Spacer()
                        }
                    }
                }
            }

            Spacer()
        }
        .padding(.horizontal, AppSpacing.screenPadding)
        .padding(.bottom, 28)
        .kickScreenBackground()
        .navigationTitle("分析中")
        .navigationBarBackButtonHidden(true)
        .kickNavigationBar()
        .navigationDestination(isPresented: $showResult) {
            ResultView(
                result: sessionManager.latestResult,
                source: .home,
                videoURL: sessionManager.latestResultVideoURL,
                videoLabel: sessionManager.latestResultVideoLabel,
                professionalAccessOverride: sessionManager.latestResultHasProfessionalAccess
            )
        }
        .task {
            shouldSpin = true
            await viewModel.start()
            sessionManager.finishProcessing()
            showResult = true
        }
    }

    @ViewBuilder
    private func stepIndicator(for status: ProcessingViewModel.StepStatus) -> some View {
        switch status {
        case .completed:
            ZStack {
                Circle()
                    .fill(AppColors.accent)
                    .frame(width: 30, height: 30)

                Image(systemName: "checkmark")
                    .font(.system(size: 13, weight: .bold))
                    .foregroundStyle(AppColors.onAccent)
            }
        case .current:
            ZStack {
                Circle()
                    .stroke(AppColors.accent, lineWidth: 2)
                    .frame(width: 30, height: 30)

                Circle()
                    .fill(AppColors.accent)
                    .frame(width: 12, height: 12)
            }
        case .upcoming:
            Circle()
                .stroke(AppColors.stroke, lineWidth: 2)
                .frame(width: 30, height: 30)
                .overlay(
                    Circle()
                        .fill(AppColors.textTertiary)
                        .frame(width: 8, height: 8)
                )
        }
    }
}
