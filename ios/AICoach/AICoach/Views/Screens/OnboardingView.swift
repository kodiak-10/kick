import SwiftUI

struct OnboardingView: View {
    @EnvironmentObject private var appState: AppState
    @State private var selection = 0

    var body: some View {
        VStack(spacing: 24) {
            HStack {
                Text("AI Coach")
                    .font(.largeTitle.weight(.bold))
                Spacer()
                Button("跳过") {
                    appState.completeOnboarding()
                }
                .foregroundStyle(AppTheme.muted)
            }
            .padding(.horizontal, 24)
            .padding(.top, 12)

            TabView(selection: $selection) {
                ForEach(Array(MockData.onboardingSteps.enumerated()), id: \.offset) { index, step in
                    VStack(alignment: .leading, spacing: 28) {
                        RoundedRectangle(cornerRadius: 32, style: .continuous)
                            .fill(
                                LinearGradient(
                                    colors: [AppTheme.cardStrong, AppTheme.cardFill],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )
                            .frame(height: 320)
                            .overlay(
                                VStack(alignment: .leading, spacing: 22) {
                                    Image(systemName: step.symbol)
                                        .font(.system(size: 42))
                                        .foregroundStyle(AppTheme.accent)
                                        .frame(width: 84, height: 84)
                                        .background(Circle().fill(AppTheme.accent.opacity(0.14)))
                                    Spacer()
                                    Text(step.title)
                                        .font(.system(size: 34, weight: .bold, design: .rounded))
                                    Text(step.subtitle)
                                        .font(.title3.weight(.medium))
                                        .foregroundStyle(AppTheme.text.opacity(0.92))
                                    Text(step.detail)
                                        .font(.body)
                                        .foregroundStyle(AppTheme.muted)
                                }
                                .padding(28)
                                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
                            )
                            .padding(.horizontal, 24)
                            .tag(index)

                        Spacer()
                    }
                }
            }
            .tabViewStyle(.page(indexDisplayMode: .always))

            VStack(spacing: 12) {
                PrimaryButton(
                    title: selection == MockData.onboardingSteps.count - 1 ? "进入应用" : "继续",
                    subtitle: selection == MockData.onboardingSteps.count - 1 ? "开始第一次射门视频演示分析" : nil
                ) {
                    if selection == MockData.onboardingSteps.count - 1 {
                        appState.completeOnboarding()
                    } else {
                        withAnimation(.easeInOut) {
                            selection += 1
                        }
                    }
                }
            }
            .padding(.horizontal, 24)
            .padding(.bottom, 28)
        }
        .background(AppTheme.background.ignoresSafeArea())
    }
}
