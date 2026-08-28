import SwiftUI

struct ProfileView: View {
    @EnvironmentObject private var sessionManager: SessionManager
    @EnvironmentObject private var purchaseManager: PurchaseManager
    @State private var showPaywall = false
    @State private var infoMessage = "管理订阅、恢复购买与账号信息会显示在这里。"

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: AppSpacing.sectionGap) {
                profileHeader
                accountCard
                menuCard
                DarkCard {
                    Text(infoMessage)
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textSecondary)
                }
            }
            .padding(.horizontal, AppSpacing.screenPadding)
            .padding(.top, 12)
            .padding(.bottom, 28)
        }
        .kickScreenBackground()
        .navigationTitle("个人中心")
        .navigationBarTitleDisplayMode(.large)
        .kickNavigationBar()
        .navigationDestination(isPresented: $showPaywall) {
            PaywallView()
        }
    }

    private var profileHeader: some View {
        DarkCard {
            HStack(spacing: 18) {
                ZStack {
                    Circle()
                        .fill(AppColors.cardSecondary)
                        .frame(width: 72, height: 72)

                    Image(systemName: sessionManager.userProfile.avatarSymbolName)
                        .font(.system(size: 30, weight: .medium))
                        .foregroundStyle(AppColors.textPrimary)
                }

                VStack(alignment: .leading, spacing: 8) {
                    HStack(spacing: 10) {
                        Text(sessionManager.userProfile.name)
                            .font(AppTypography.sectionTitle)
                            .foregroundStyle(AppColors.textPrimary)

                        if sessionManager.hasProAccess {
                            ProBadge(title: "专业版")
                        }
                    }

                    Text(sessionManager.userProfile.email)
                        .font(AppTypography.body)
                        .foregroundStyle(AppColors.textSecondary)
                }

                Spacer()
            }
        }
    }

    private var accountCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 16) {
                Text("账户与权益")
                    .font(AppTypography.cardTitle)
                    .foregroundStyle(AppColors.textPrimary)

                HStack(spacing: 14) {
                    StatItem(value: sessionManager.userProfile.tier.rawValue, label: "当前版本")
                    StatItem(value: "\(sessionManager.remainingFreeAnalyses)", label: "剩余免费分析次数")
                }
            }
        }
    }

    private var menuCard: some View {
        DarkCard {
            VStack(spacing: 0) {
                ProfileMenuRow(title: "管理订阅", systemImage: "crown.fill") {
                    showPaywall = true
                }

                Divider().overlay(AppColors.stroke)

                ProfileMenuRow(title: "恢复购买", systemImage: "arrow.counterclockwise") {
                    purchaseManager.restore(sessionManager: sessionManager)
                    infoMessage = purchaseManager.purchaseNotice ?? "正在恢复购买状态..."
                }

                Divider().overlay(AppColors.stroke)

                ProfileMenuRow(title: "用户协议", systemImage: "doc.text") {
                    infoMessage = "用户协议页面将在后续版本接入正式文档。"
                }

                Divider().overlay(AppColors.stroke)

                ProfileMenuRow(title: "隐私政策", systemImage: "lock.doc") {
                    infoMessage = "隐私政策页面将在后续版本接入正式文档。"
                }

                Divider().overlay(AppColors.stroke)

                ProfileMenuRow(title: "关于我们", systemImage: "info.circle") {
                    infoMessage = "Kick 致力于把足球动作训练做得更可量化、更可复盘。"
                }
            }
        }
    }
}

private struct ProfileMenuRow: View {
    let title: String
    let systemImage: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 14) {
                Image(systemName: systemImage)
                    .font(.system(size: 17, weight: .semibold))
                    .foregroundStyle(AppColors.textPrimary)
                    .frame(width: 24)

                Text(title)
                    .font(AppTypography.body)
                    .foregroundStyle(AppColors.textPrimary)

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(AppColors.textTertiary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.vertical, 16)
        }
        .buttonStyle(.plain)
    }
}
