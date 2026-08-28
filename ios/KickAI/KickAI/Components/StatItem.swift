import SwiftUI

struct StatItem: View {
    let value: String
    let label: String
    var trend: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(value)
                .font(AppTypography.metric)
                .foregroundStyle(AppColors.textPrimary)

            Text(label)
                .font(AppTypography.caption)
                .foregroundStyle(AppColors.textSecondary)

            if let trend {
                Text(trend)
                    .font(AppTypography.captionMedium)
                    .foregroundStyle(AppColors.positive)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
