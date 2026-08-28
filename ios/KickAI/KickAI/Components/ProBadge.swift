import SwiftUI

struct ProBadge: View {
    var title = "PRO"

    var body: some View {
        Text(title)
            .font(AppTypography.captionMedium)
            .foregroundStyle(AppColors.onAccent)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(AppColors.accent)
            .clipShape(Capsule())
    }
}
