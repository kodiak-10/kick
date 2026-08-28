import SwiftUI

struct ProfileView: View {
    @EnvironmentObject private var appState: AppState
    @State private var showPrivacy = false

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 22) {
                FrostedCard {
                    HStack(alignment: .top) {
                        VStack(alignment: .leading, spacing: 10) {
                            Text("个人中心")
                                .font(.system(size: 28, weight: .bold, design: .rounded))
                            Text(appState.subscription.title)
                                .font(.headline)
                                .foregroundStyle(appState.isPro ? AppTheme.success : AppTheme.warning)
                            Text(appState.subscription.subtitle)
                                .font(.subheadline)
                                .foregroundStyle(AppTheme.muted)
                        }
                        Spacer()
                        Image(systemName: appState.isPro ? "person.crop.circle.badge.checkmark" : "person.crop.circle")
                            .font(.system(size: 38))
                            .foregroundStyle(AppTheme.accent)
                    }
                }

                FrostedCard {
                    SectionLabel(title: "订阅与权益", subtitle: "第一版先用 mock 订阅逻辑演示")

                    VStack(spacing: 12) {
                        if appState.isPro {
                            PrimaryButton(title: "当前已是 Pro", subtitle: "你可以继续演示完整内容") {}
                            SecondaryButton(title: "切回基础版演示") {
                                appState.switchToFree()
                            }
                        } else {
                            PrimaryButton(title: "升级到 Pro", subtitle: "解锁完整报告与历史记录") {
                                appState.openPaywall(from: .profile)
                            }
                        }

                        HStack(spacing: 12) {
                            SecondaryButton(title: "恢复购买") {
                                appState.restorePurchases()
                            }
                            SecondaryButton(title: "查看隐私政策") {
                                showPrivacy = true
                            }
                        }
                    }
                }

                FrostedCard {
                    SectionLabel(title: "演示控制", subtitle: "便于在 Xcode 里快速切换场景")
                    VStack(spacing: 12) {
                        row(title: "剩余免费次数", value: appState.isPro ? "不限" : "\(appState.remainingFreeAnalyses) 次")
                        row(title: "当前分析目标", value: appState.selectedGoal.title)
                        SecondaryButton(title: "重置演示数据") {
                            appState.resetDemoData()
                        }
                    }
                }

                FrostedCard {
                    SectionLabel(title: "App Store 上架准备", subtitle: "第一版建议继续补充这些能力")
                    VStack(alignment: .leading, spacing: 8) {
                        Text("• 接入真实视频选择器与上传流程")
                        Text("• 用 StoreKit 2 替换 mock 订阅状态")
                        Text("• 添加真实用户协议、隐私政策与客服入口")
                        Text("• 接入真实 AI 分析任务与报告导出")
                    }
                    .font(.subheadline)
                    .foregroundStyle(AppTheme.muted)
                }
            }
            .padding(20)
            .padding(.bottom, 32)
        }
        .background(AppTheme.background.ignoresSafeArea())
        .sheet(isPresented: $showPrivacy) {
            PrivacySheet()
                .presentationDetents([.medium, .large])
                .preferredColorScheme(.dark)
        }
    }

    private func row(title: String, value: String) -> some View {
        HStack {
            Text(title)
                .font(.subheadline)
            Spacer()
            Text(value)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.white)
        }
    }
}

private struct PrivacySheet: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text("隐私政策（演示版）")
                        .font(.title2.weight(.bold))
                    Text("本版本仅用于产品演示，不会真的上传视频到远端服务，也不会触发真实扣费。后续准备上架 App Store 时，需要补充正式隐私政策、用户协议、订阅条款和数据删除说明。")
                        .font(.body)
                        .foregroundStyle(.secondary)
                    Text("建议正式版本补充：")
                        .font(.headline)
                    Text("1. 上传视频数据用途与保存时长\n2. 订阅自动续费条款\n3. 用户申请删除数据的方式\n4. 第三方服务说明与联系方式")
                        .foregroundStyle(.secondary)
                }
                .padding(20)
            }
            .navigationTitle("隐私政策")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("完成") {
                        dismiss()
                    }
                }
            }
        }
    }
}
