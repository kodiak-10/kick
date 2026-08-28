import SwiftUI

struct HomeView: View {
    @EnvironmentObject private var sessionManager: SessionManager
    @State private var showPaywall = false
    @State private var showLatestResult = false

    private var greeting: String {
        let hour = Calendar.current.component(.hour, from: Date())
        switch hour {
        case 0..<6:
            return "夜深了"
        case 6..<12:
            return "早上好"
        case 12..<18:
            return "下午好"
        default:
            return "晚上好"
        }
    }

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: AppSpacing.sectionGap) {
                topHeader
                heroCard
                footballAIIntroCard
                footballEcosystemCard
                latestResultCard
                progressCard
                proCard
            }
            .padding(.horizontal, AppSpacing.screenPadding)
            .padding(.top, 12)
            .padding(.bottom, 30)
        }
        .kickScreenBackground()
        .navigationDestination(isPresented: $showPaywall) {
            PaywallView()
        }
        .navigationDestination(isPresented: $showLatestResult) {
            ResultView(
                result: sessionManager.latestResult,
                source: .home,
                videoURL: sessionManager.latestResultVideoURL,
                videoLabel: sessionManager.latestResultVideoLabel,
                professionalAccessOverride: sessionManager.latestResultHasProfessionalAccess
            )
        }
        .toolbar(.hidden, for: .navigationBar)
    }

    private var topHeader: some View {
        HStack(alignment: .top) {
            VStack(alignment: .leading, spacing: 10) {
                Text("\(greeting)，\(sessionManager.userProfile.name)")
                    .font(AppTypography.pageTitle)
                    .foregroundStyle(AppColors.textPrimary)

                Text("今天继续优化你的足球动作")
                    .font(AppTypography.body)
                    .foregroundStyle(AppColors.textSecondary)
            }

            Spacer()

            Button {
                sessionManager.selectedTab = .profile
            } label: {
                ZStack {
                    Circle()
                        .fill(AppColors.cardSecondary)
                        .frame(width: 48, height: 48)

                    Image(systemName: sessionManager.userProfile.avatarSymbolName)
                        .font(.system(size: 20, weight: .medium))
                        .foregroundStyle(AppColors.textPrimary)
                }
                .overlay(
                    Circle()
                        .stroke(AppColors.stroke, lineWidth: 1)
                )
            }
            .buttonStyle(.plain)
        }
    }

    private var heroCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 20) {
                HStack {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("开始新一次分析")
                            .font(AppTypography.sectionTitle)
                            .foregroundStyle(AppColors.textPrimary)

                        Text("上传传球、射门或长视频，Kick 会先做动作路由，再输出可执行的训练反馈。")
                            .font(AppTypography.body)
                            .foregroundStyle(AppColors.textSecondary)
                    }

                    Spacer(minLength: 0)

                    if sessionManager.hasProAccess {
                        ProBadge(title: "专业版")
                    } else {
                        Text("普通 \(sessionManager.remainingFreeAnalyses) 次 · 专业体验 \(sessionManager.remainingFreeProAnalyses) 次")
                            .font(AppTypography.captionMedium)
                            .foregroundStyle(AppColors.textSecondary)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                            .background(AppColors.backgroundSoft)
                            .clipShape(Capsule())
                    }
                }

                ZStack(alignment: .topTrailing) {
                    RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                        .fill(
                            LinearGradient(
                                colors: [
                                    AppColors.backgroundSoft,
                                    AppColors.cardSecondary
                                ],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .frame(height: 160)
                        .overlay(
                            RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                                .stroke(AppColors.strongStroke, lineWidth: 1)
                        )

                    Circle()
                        .fill(AppColors.accentMuted.opacity(0.15))
                        .frame(width: 110, height: 110)
                        .blur(radius: 20)
                        .offset(x: 18, y: -20)

                    VStack(alignment: .leading, spacing: 12) {
                        Text("AI 足球教练")
                            .font(AppTypography.captionMedium)
                            .foregroundStyle(AppColors.textSecondary)

                        Text("你只管踢球，剩下交给 Kick 分析。")
                            .font(AppTypography.cardTitle)
                            .foregroundStyle(AppColors.textPrimary)

                        Text("先看动作是否可信，再看关键帧、问题点和下一组训练。")
                            .font(AppTypography.caption)
                            .foregroundStyle(AppColors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .padding(18)
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
                }

                PrimaryButton(
                    title: sessionManager.canStartAnalysis ? "进入分析页" : "升级后继续分析",
                    systemImage: sessionManager.canStartAnalysis ? "arrow.up.circle.fill" : "crown.fill"
                ) {
                    if sessionManager.canStartAnalysis {
                        sessionManager.resetAnalysisNavigation()
                    } else {
                        showPaywall = true
                    }
                }
            }
        }
    }

    private var footballAIIntroCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 16) {
                Text("我们为足球做的")
                    .font(AppTypography.cardTitle)
                    .foregroundStyle(AppColors.textPrimary)

                VStack(spacing: 12) {
                    HomeFeatureRow(
                        icon: "figure.soccer",
                        title: "动作专项分析",
                        subtitle: "传球、射门和传接衔接分开分析，不混用模板。"
                    )
                    HomeFeatureRow(
                        icon: "video.badge.waveform",
                        title: "关键帧复盘",
                        subtitle: "只解释和问题相关的窗口，减少看不懂的视觉噪音。"
                    )
                    HomeFeatureRow(
                        icon: "person.crop.rectangle.stack",
                        title: "长视频单一球员",
                        subtitle: "先锁定目标球员，再输出属于他的技术事件。"
                    )
                }
            }
        }
    }

    private var footballEcosystemCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 16) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("发现球友、球场和私教")
                            .font(AppTypography.cardTitle)
                            .foregroundStyle(AppColors.textPrimary)

                        Text("社交圈先围绕训练反馈讨论，后续再扩展同城约球、球场发现和一对一教练服务。")
                            .font(AppTypography.body)
                            .foregroundStyle(AppColors.textSecondary)
                    }

                    Spacer()

                    Image(systemName: "mappin.and.ellipse")
                        .font(.system(size: 22, weight: .bold))
                        .foregroundStyle(AppColors.pitchGreen)
                        .frame(width: 46, height: 46)
                        .background(AppColors.pitchGreen.opacity(0.14))
                        .clipShape(Circle())
                }

                HStack(spacing: 10) {
                    HomeEcosystemPill(title: "球友圈", icon: "bubble.left.and.bubble.right")
                    HomeEcosystemPill(title: "发现球场", icon: "sportscourt")
                    HomeEcosystemPill(title: "私教", icon: "person.2.wave.2")
                }

                SecondaryButton(title: "进入发现", systemImage: "arrow.right.circle.fill") {
                    sessionManager.selectedTab = .discover
                }
            }
        }
    }

    private var latestResultCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 18) {
                HStack {
                    Text("最近一次分析")
                        .font(AppTypography.cardTitle)
                        .foregroundStyle(AppColors.textPrimary)

                    Spacer()

                        Text("动作：\(sessionManager.latestResult.motionType)")
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textSecondary)
                }

                HStack(alignment: .center, spacing: 16) {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("评分")
                            .font(AppTypography.caption)
                            .foregroundStyle(AppColors.textSecondary)

                        Text("\(sessionManager.latestResult.score)")
                            .font(AppTypography.metric)
                            .foregroundStyle(AppColors.textPrimary)

                        Text("主要问题：\(sessionManager.latestResult.freeIssues.first?.title ?? "动作稳定性待提升")")
                            .font(AppTypography.body)
                            .foregroundStyle(AppColors.textSecondary)
                    }

                    Spacer()

                    ZStack {
                        Circle()
                            .stroke(AppColors.textPrimary.opacity(0.08), lineWidth: 10)

                        Circle()
                            .trim(from: 0, to: CGFloat(sessionManager.latestResult.score) / 100)
                            .stroke(
                                AppColors.accent,
                                style: StrokeStyle(lineWidth: 10, lineCap: .round)
                            )
                            .rotationEffect(.degrees(-90))

                        Text("\(sessionManager.latestResult.score)")
                            .font(AppTypography.cardTitle)
                            .foregroundStyle(AppColors.textPrimary)
                    }
                    .frame(width: 92, height: 92)
                }

                SecondaryButton(title: "查看详情", systemImage: "chevron.right") {
                    showLatestResult = true
                }
            }
        }
    }

    private var progressCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 18) {
                Text("进步追踪")
                    .font(AppTypography.cardTitle)
                    .foregroundStyle(AppColors.textPrimary)

                HStack(spacing: 14) {
                    StatItem(value: "\(sessionManager.weeklyAnalysisCount)", label: "本周分析次数")
                    StatItem(value: "\(sessionManager.weeklyAverageScore)", label: "平均得分")
                    StatItem(
                        value: sessionManager.weeklyChange >= 0 ? "+\(sessionManager.weeklyChange)" : "\(sessionManager.weeklyChange)",
                        label: "相比上周",
                        trend: sessionManager.weeklyChange >= 0 ? "保持提升" : "继续训练"
                    )
                }
            }
        }
    }

    private var proCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    Text("升级专业版")
                        .font(AppTypography.cardTitle)
                        .foregroundStyle(AppColors.textPrimary)

                    Spacer()

                    ProBadge()
                }

                Text("解锁错误时刻标记、关键帧分析和历史对比。")
                    .font(AppTypography.body)
                    .foregroundStyle(AppColors.textSecondary)

                SecondaryButton(title: sessionManager.hasProAccess ? "专业版已激活" : "立即升级", systemImage: "crown.fill") {
                    showPaywall = true
                }
            }
        }
    }
}

private struct HomeFeatureRow: View {
    let icon: String
    let title: String
    let subtitle: String

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 18, weight: .semibold))
                .foregroundStyle(AppColors.onAccent)
                .frame(width: 42, height: 42)
                .background(AppColors.accent)
                .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.small, style: .continuous))

            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(AppTypography.headline)
                    .foregroundStyle(AppColors.textPrimary)
                Text(subtitle)
                    .font(AppTypography.body)
                    .foregroundStyle(AppColors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Spacer(minLength: 0)
        }
    }
}

private struct HomeEcosystemPill: View {
    let title: String
    let icon: String

    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: icon)
                .font(.system(size: 12, weight: .bold))
            Text(title)
                .font(AppTypography.captionMedium)
        }
        .foregroundStyle(AppColors.textSecondary)
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .frame(maxWidth: .infinity)
        .background(AppColors.backgroundSoft)
        .clipShape(Capsule())
    }
}
