import SwiftUI

struct PermissionView: View {
    @EnvironmentObject private var sessionManager: SessionManager

    var body: some View {
        ZStack {
            ScreenBackground()

            VStack(alignment: .leading, spacing: 22) {
                Spacer(minLength: 20)

                VStack(alignment: .leading, spacing: 12) {
                    Text("开启拍摄与上传权限")
                        .font(AppTypography.pageTitle)
                        .foregroundStyle(AppColors.textPrimary)

                    Text("为了完成视频分析，我们需要访问你的相机与相册，用于拍摄或上传训练视频。")
                        .font(AppTypography.body)
                        .foregroundStyle(AppColors.textSecondary)
                }

                VStack(spacing: 14) {
                    ForEach(AppMockData.permissionItems) { item in
                        DarkCard {
                            HStack(spacing: 14) {
                                ZStack {
                                    RoundedRectangle(cornerRadius: AppCornerRadius.small, style: .continuous)
                                        .fill(AppColors.backgroundSoft)
                                        .frame(width: 54, height: 54)

                                    Image(systemName: item.iconName)
                                        .font(.system(size: 20, weight: .semibold))
                                        .foregroundStyle(AppColors.accent)
                                }

                                VStack(alignment: .leading, spacing: 6) {
                                    Text(item.title)
                                        .font(AppTypography.cardTitle)
                                        .foregroundStyle(AppColors.textPrimary)

                                    Text(item.detail)
                                        .font(AppTypography.body)
                                        .foregroundStyle(AppColors.textSecondary)
                                }
                            }
                        }
                    }
                }

                DarkCard {
                    Text("后续接入真实权限请求时，这里会衔接系统的相机与相册授权弹窗。")
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textSecondary)
                }

                Spacer()

                PrimaryButton(title: "继续") {
                    // Placeholder for future system permission requests.
                    sessionManager.completePermissionIntro()
                }
                .padding(.bottom, 24)
            }
            .padding(.horizontal, AppSpacing.screenPadding)
        }
    }
}
