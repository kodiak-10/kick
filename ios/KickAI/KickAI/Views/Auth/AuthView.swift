import SwiftUI

struct AuthView: View {
    @EnvironmentObject private var sessionManager: SessionManager

    var body: some View {
        ZStack {
            ScreenBackground()

            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 28) {
                    Spacer(minLength: 36)

                    VStack(alignment: .leading, spacing: 12) {
                        Text("Kick")
                            .font(AppTypography.headline)
                            .foregroundStyle(AppColors.textSecondary)

                        Text("欢迎回来")
                            .font(AppTypography.hero)
                            .foregroundStyle(AppColors.textPrimary)

                        Text("上传足球训练视频，查看动作评分、问题诊断与训练建议。")
                            .font(AppTypography.body)
                            .foregroundStyle(AppColors.textSecondary)
                    }

                    DarkCard {
                        VStack(alignment: .leading, spacing: 22) {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("进入你的训练空间")
                                    .font(AppTypography.sectionTitle)
                                    .foregroundStyle(AppColors.textPrimary)

                                Text("当前版本先使用本地体验流程，登录后会直接进入权限说明。")
                                    .font(AppTypography.caption)
                                    .foregroundStyle(AppColors.textSecondary)
                            }

                            VStack(spacing: 12) {
                                PrimaryButton(title: "使用 Apple 登录", systemImage: "apple.logo") {
                                    sessionManager.signIn(with: "Apple")
                                }

                                SecondaryButton(title: "使用手机号登录", systemImage: "phone.fill") {
                                    sessionManager.signIn(with: "手机号")
                                }

                                SecondaryButton(title: "使用邮箱登录", systemImage: "envelope.fill") {
                                    sessionManager.signIn(with: "邮箱")
                                }
                            }
                        }
                    }

                    DarkCard {
                        VStack(alignment: .leading, spacing: 10) {
                            Text("为什么先登录？")
                                .font(AppTypography.cardTitle)
                                .foregroundStyle(AppColors.textPrimary)

                            Text("用于保存你的分析历史、同步专业版权益，以及后续接入真实账号体系。")
                                .font(AppTypography.body)
                                .foregroundStyle(AppColors.textSecondary)
                        }
                    }

                    Spacer(minLength: 12)

                    Text("登录即代表你同意《用户协议》和《隐私政策》")
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textTertiary)
                        .frame(maxWidth: .infinity, alignment: .center)
                        .padding(.bottom, 18)
                }
                .padding(.horizontal, AppSpacing.screenPadding)
            }
        }
    }
}
