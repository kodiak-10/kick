import SwiftUI

struct ScreenBackground: View {
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        ZStack {
            AppColors.background
                .ignoresSafeArea()

            LinearGradient(
                colors: [
                    AppColors.accent.opacity(colorScheme == .dark ? 0.12 : 0.05),
                    Color.clear,
                    AppColors.reference.opacity(colorScheme == .dark ? 0.08 : 0.03)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            Circle()
                .fill(AppColors.textPrimary.opacity(colorScheme == .dark ? 0.055 : 0.035))
                .frame(width: 240, height: 240)
                .blur(radius: 80)
                .offset(x: 120, y: -280)

            Circle()
                .fill(AppColors.accentMuted.opacity(colorScheme == .dark ? 0.16 : 0.08))
                .frame(width: 220, height: 220)
                .blur(radius: 90)
                .offset(x: -140, y: -320)
        }
    }
}
