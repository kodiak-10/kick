import SwiftUI

struct PaywallView: View {
    @EnvironmentObject private var appState: AppState
    let source: PaywallSource

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 22) {
                FrostedCard(padding: 22) {
                    HStack(alignment: .top) {
                        VStack(alignment: .leading, spacing: 10) {
                            Text("升级到 AI Coach Pro")
                                .font(.system(size: 30, weight: .bold, design: .rounded))
                            Text("解锁完整足球动作评分、更多问题点、专项训练建议和历史记录。当前版本使用 mock 订阅逻辑，方便你先演示完整产品体验。")
                                .font(.subheadline)
                                .foregroundStyle(AppTheme.muted)
                        }
                        Spacer()
                        Image(systemName: "crown.fill")
                            .font(.title)
                            .foregroundStyle(AppTheme.warning)
                    }
                }

                FrostedCard {
                    SectionLabel(title: "为什么要升级", subtitle: sourceText)

                    VStack(spacing: 12) {
                        ForEach(MockData.paywallFeatures) { feature in
                            HStack(alignment: .top, spacing: 14) {
                                Image(systemName: feature.icon)
                                    .font(.headline)
                                    .foregroundStyle(AppTheme.accent)
                                    .frame(width: 34, height: 34)
                                    .background(Circle().fill(AppTheme.accent.opacity(0.14)))
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(feature.title)
                                        .font(.headline)
                                    Text(feature.detail)
                                        .font(.subheadline)
                                        .foregroundStyle(AppTheme.muted)
                                }
                            }
                        }
                    }
                }

                VStack(spacing: 14) {
                    ForEach(ProPlan.allCases) { plan in
                        Button {
                            appState.upgrade(to: plan)
                        } label: {
                            FrostedCard {
                                HStack {
                                    VStack(alignment: .leading, spacing: 8) {
                                        HStack(spacing: 8) {
                                            Text(plan.title)
                                                .font(.headline.weight(.semibold))
                                            StatusPill(text: plan.badge, tint: plan == .yearly ? AppTheme.success : AppTheme.accent)
                                        }
                                        Text(plan.price)
                                            .font(.title3.weight(.bold))
                                        Text("点击后直接进入 mock Pro 状态，不会触发真实扣费。")
                                            .font(.caption)
                                            .foregroundStyle(AppTheme.muted)
                                    }
                                    Spacer()
                                    Image(systemName: "arrow.up.right.circle.fill")
                                        .font(.title2)
                                        .foregroundStyle(AppTheme.accent)
                                }
                            }
                        }
                        .buttonStyle(.plain)
                    }
                }

                FrostedCard {
                    HStack(spacing: 12) {
                        SecondaryButton(title: "恢复购买") {
                            appState.restorePurchases()
                        }
                        SecondaryButton(title: "继续使用免费版") {
                            appState.dismissTopRoute()
                        }
                    }
                }
            }
            .padding(20)
            .padding(.bottom, 36)
        }
        .background(AppTheme.background.ignoresSafeArea())
        .navigationTitle("Pro 订阅")
        .navigationBarTitleDisplayMode(.inline)
    }

    private var sourceText: String {
        switch source {
        case .home:
            return "从首页升级，适合直接体验完整产品价值"
        case .result:
            return "从结果页升级，立即解锁完整报告内容"
        case .history:
            return "从历史页升级，查看更多历史训练记录"
        case .profile:
            return "从个人中心升级，管理订阅状态"
        case .quotaExhausted:
            return "免费次数已用完，升级后可继续无限分析"
        }
    }
}
