import SwiftUI

struct SplashView: View {
    @EnvironmentObject private var sessionManager: SessionManager
    @State private var isVisible = false

    var body: some View {
        ZStack {
            ScreenBackground()

            VStack(spacing: 22) {
                ZStack {
                    Circle()
                        .fill(AppColors.textPrimary.opacity(0.06))
                        .frame(width: 120, height: 120)

                    Image(systemName: "figure.soccer")
                        .font(.system(size: 44, weight: .semibold))
                        .foregroundStyle(AppColors.accent)
                }

                VStack(spacing: 10) {
                    Text("Kick")
                        .font(AppTypography.hero)
                        .foregroundStyle(AppColors.textPrimary)

                    Text("让每一次训练更有依据")
                        .font(AppTypography.body)
                        .foregroundStyle(AppColors.textSecondary)
                }
            }
            .scaleEffect(isVisible ? 1 : 0.94)
            .opacity(isVisible ? 1 : 0.35)
        }
        .task {
            guard !sessionManager.hasSeenSplash else { return }
            withAnimation(.easeOut(duration: 0.6)) {
                isVisible = true
            }
            try? await Task.sleep(nanoseconds: 1_500_000_000)
            sessionManager.completeSplash()
        }
    }
}
