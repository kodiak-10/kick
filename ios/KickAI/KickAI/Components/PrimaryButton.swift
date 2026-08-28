import SwiftUI

struct PrimaryButton: View {
    let title: String
    var systemImage: String?
    var isDisabled = false
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 10) {
                if let systemImage {
                    Image(systemName: systemImage)
                        .font(.system(size: 14, weight: .semibold))
                }

                Text(title)
                    .font(AppTypography.headline)
            }
            .foregroundStyle(AppColors.onAccent)
            .frame(maxWidth: .infinity)
            .frame(height: 56)
            .background(isDisabled ? AppColors.textSecondary.opacity(0.3) : AppColors.accent)
            .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
        }
        .buttonStyle(.plain)
        .disabled(isDisabled)
        .opacity(isDisabled ? 0.6 : 1)
    }
}
