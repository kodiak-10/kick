import SwiftUI

struct FeatureRow: View {
    let feature: AppFeature
    var locked = false

    var body: some View {
        HStack(alignment: .top, spacing: 14) {
            ZStack {
                RoundedRectangle(cornerRadius: AppCornerRadius.small, style: .continuous)
                    .fill(AppColors.backgroundSoft)
                    .frame(width: 42, height: 42)

                Image(systemName: feature.iconName)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(locked ? AppColors.textTertiary : AppColors.accent)
            }

            VStack(alignment: .leading, spacing: 6) {
                Text(feature.title)
                    .font(AppTypography.headline)
                    .foregroundStyle(AppColors.textPrimary)

                Text(feature.detail)
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Spacer(minLength: 0)

            if locked {
                Image(systemName: "lock.fill")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(AppColors.textTertiary)
                    .padding(.top, 4)
            }
        }
    }
}
