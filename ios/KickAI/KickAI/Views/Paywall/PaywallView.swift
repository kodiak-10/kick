import SwiftUI

struct PaywallView: View {
    @EnvironmentObject private var sessionManager: SessionManager
    @EnvironmentObject private var subscriptionManager: SubscriptionManager
    @EnvironmentObject private var purchaseManager: PurchaseManager
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: AppSpacing.sectionGap) {
                heroSection
                featureSection
                planSection
                actionSection
            }
            .padding(.horizontal, AppSpacing.screenPadding)
            .padding(.top, 12)
            .padding(.bottom, 28)
        }
        .kickScreenBackground()
        .navigationTitle("专业版")
        .navigationBarTitleDisplayMode(.inline)
        .kickNavigationBar()
    }

    private var heroSection: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 18) {
                HStack {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("升级 Kick 专业版，获得更细的动作诊断")
                            .font(AppTypography.pageTitle)
                            .foregroundStyle(AppColors.textPrimary)

                        Text("解锁错误时刻标记、关键帧分析、更细反馈、训练建议与历史对比。")
                            .font(AppTypography.body)
                            .foregroundStyle(AppColors.textSecondary)
                    }

                    Spacer(minLength: 0)

                    ProBadge(title: "PRO")
                }

                ZStack(alignment: .bottomLeading) {
                    RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
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
                        .frame(height: 170)
                        .overlay(
                            RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                                .stroke(AppColors.strongStroke, lineWidth: 1)
                        )

                    Circle()
                        .fill(AppColors.accentMuted.opacity(0.15))
                        .frame(width: 120, height: 120)
                        .blur(radius: 24)
                        .offset(x: 160, y: -40)

                    VStack(alignment: .leading, spacing: 12) {
                        Text("Kick Pro")
                            .font(AppTypography.captionMedium)
                            .foregroundStyle(AppColors.textSecondary)

                        Text("更像一套训练系统，而不是一次性结果页。")
                            .font(AppTypography.sectionTitle)
                            .foregroundStyle(AppColors.textPrimary)

                        Text(sessionManager.hasProAccess ? "当前账号已处于专业版状态" : "建议长期训练用户直接选择年付方案")
                            .font(AppTypography.body)
                            .foregroundStyle(AppColors.textSecondary)
                    }
                    .padding(18)
                }
            }
        }
    }

    private var featureSection: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 16) {
                Text("权益列表")
                    .font(AppTypography.cardTitle)
                    .foregroundStyle(AppColors.textPrimary)

                ForEach(AppMockData.premiumFeatures) { feature in
                    FeatureRow(feature: feature)
                }
            }
        }
    }

    private var planSection: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 16) {
                Text("订阅方案")
                    .font(AppTypography.cardTitle)
                    .foregroundStyle(AppColors.textPrimary)

                ForEach(subscriptionManager.plans) { plan in
                    Button {
                        subscriptionManager.select(plan)
                    } label: {
                        VStack(alignment: .leading, spacing: 10) {
                            HStack {
                                VStack(alignment: .leading, spacing: 6) {
                                    Text(plan.title)
                                        .font(AppTypography.headline)
                                        .foregroundStyle(AppColors.textPrimary)

                                    Text(plan.description)
                                        .font(AppTypography.caption)
                                        .foregroundStyle(AppColors.textSecondary)
                                }

                                Spacer()

                                if let badge = plan.badge {
                                    Text(badge)
                                        .font(AppTypography.captionMedium)
                                        .foregroundStyle(AppColors.onAccent)
                                        .padding(.horizontal, 10)
                                        .padding(.vertical, 6)
                                        .background(AppColors.accent)
                                        .clipShape(Capsule())
                                }
                            }

                            HStack {
                                Text(plan.price)
                                    .font(AppTypography.sectionTitle)
                                    .foregroundStyle(AppColors.textPrimary)

                                Spacer()

                                Image(systemName: subscriptionManager.selectedPlanID == plan.id ? "checkmark.circle.fill" : "circle")
                                    .font(.system(size: 20, weight: .semibold))
                                    .foregroundStyle(subscriptionManager.selectedPlanID == plan.id ? AppColors.accent : AppColors.textTertiary)
                            }

                            Text(plan.note)
                                .font(AppTypography.caption)
                                .foregroundStyle(AppColors.textSecondary)
                        }
                        .padding(16)
                        .background(AppColors.cardSecondary)
                        .overlay(
                            RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                                .stroke(subscriptionManager.selectedPlanID == plan.id ? AppColors.strongStroke : AppColors.stroke, lineWidth: 1)
                        )
                        .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private var actionSection: some View {
        VStack(spacing: 12) {
            PrimaryButton(
                title: sessionManager.hasProAccess ? "专业版已开通" : (purchaseManager.isPurchasing ? "正在开通..." : "立即开通专业版"),
                systemImage: "crown.fill",
                isDisabled: sessionManager.hasProAccess || purchaseManager.isPurchasing
            ) {
                purchaseManager.purchaseSelectedPlan(
                    subscriptionManager: subscriptionManager,
                    sessionManager: sessionManager
                )
            }

            if let purchaseNotice = purchaseManager.purchaseNotice {
                Text(purchaseNotice)
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.positive)
            }

            SecondaryButton(title: "恢复购买", systemImage: "arrow.counterclockwise") {
                purchaseManager.restore(sessionManager: sessionManager)
            }

            SecondaryButton(title: "稍后再说", systemImage: "xmark") {
                dismiss()
            }
        }
    }
}
