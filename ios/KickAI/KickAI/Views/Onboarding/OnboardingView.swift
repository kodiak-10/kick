import SwiftUI

struct OnboardingView: View {
    @EnvironmentObject private var sessionManager: SessionManager
    @State private var currentPage = 0

    private let pages = AppMockData.onboardingPages

    var body: some View {
        ZStack {
            ScreenBackground()

            VStack(spacing: 0) {
                HStack {
                    Text("Kick")
                        .font(AppTypography.headline)
                        .foregroundStyle(AppColors.textSecondary)

                    Spacer()

                    Button("跳过") {
                        sessionManager.completeOnboarding()
                    }
                    .font(AppTypography.bodyMedium)
                    .foregroundStyle(AppColors.textSecondary)
                }
                .padding(.horizontal, AppSpacing.screenPadding)
                .padding(.top, 18)

                TabView(selection: $currentPage) {
                    ForEach(Array(pages.enumerated()), id: \.offset) { index, page in
                        VStack(spacing: 26) {
                            Spacer()

                            ZStack {
                                RoundedRectangle(cornerRadius: 36, style: .continuous)
                                    .fill(
                                        LinearGradient(
                                            colors: [
                                                AppColors.cardSecondary,
                                                AppColors.backgroundSoft
                                            ],
                                            startPoint: .topLeading,
                                            endPoint: .bottomTrailing
                                        )
                                    )
                                    .frame(width: 280, height: 280)
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 36, style: .continuous)
                                            .stroke(AppColors.stroke, lineWidth: 1)
                                    )

                                Circle()
                                    .fill(AppColors.textPrimary.opacity(0.06))
                                    .frame(width: 160, height: 160)

                                Image(systemName: page.iconName)
                                    .font(.system(size: 72, weight: .medium))
                                    .foregroundStyle(AppColors.accent)
                            }

                            VStack(spacing: 14) {
                                Text(page.title)
                                    .font(AppTypography.pageTitle)
                                    .foregroundStyle(AppColors.textPrimary)

                                Text(page.subtitle)
                                    .font(AppTypography.body)
                                    .foregroundStyle(AppColors.textSecondary)
                                    .multilineTextAlignment(.center)
                                    .padding(.horizontal, 28)
                            }

                            Spacer()
                        }
                        .padding(.horizontal, AppSpacing.screenPadding)
                        .tag(index)
                    }
                }
                .tabViewStyle(.page(indexDisplayMode: .never))

                VStack(spacing: 20) {
                    HStack(spacing: 8) {
                        ForEach(0..<pages.count, id: \.self) { index in
                            Capsule()
                            .fill(index == currentPage ? AppColors.accent : AppColors.textPrimary.opacity(0.14))
                            .frame(width: index == currentPage ? 26 : 8, height: 8)
                        }
                    }

                    HStack(spacing: 12) {
                        SecondaryButton(title: "下一步") {
                            if currentPage < pages.count - 1 {
                                withAnimation(.easeInOut(duration: 0.25)) {
                                    currentPage += 1
                                }
                            } else {
                                sessionManager.completeOnboarding()
                            }
                        }

                        PrimaryButton(title: currentPage == pages.count - 1 ? "开始使用" : "继续") {
                            if currentPage < pages.count - 1 {
                                withAnimation(.easeInOut(duration: 0.25)) {
                                    currentPage += 1
                                }
                            } else {
                                sessionManager.completeOnboarding()
                            }
                        }
                    }
                }
                .padding(.horizontal, AppSpacing.screenPadding)
                .padding(.bottom, 26)
            }
        }
    }
}
