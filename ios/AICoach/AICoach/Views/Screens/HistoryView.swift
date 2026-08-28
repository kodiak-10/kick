import SwiftUI

struct HistoryView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 22) {
                SectionLabel(
                    title: "历史记录",
                    subtitle: appState.isPro ? "完整保存每一次分析结果" : "基础版默认展示最近 3 次结果"
                )

                if appState.visibleHistory.isEmpty {
                    FrostedCard {
                        Text("还没有历史记录")
                            .font(.headline)
                        Text("完成一次分析后，这里会自动保存结果。")
                            .font(.subheadline)
                            .foregroundStyle(AppTheme.muted)
                    }
                } else {
                    VStack(spacing: 14) {
                        ForEach(appState.visibleHistory) { record in
                            Button {
                                appState.showRecord(record.id)
                            } label: {
                                FrostedCard {
                                    HStack(spacing: 16) {
                                        previewBlock(record)

                                        VStack(alignment: .leading, spacing: 8) {
                                            Text(record.displayActionDisplayName)
                                                .font(.headline.weight(.semibold))
                                            Text(record.shouldShowFormalScore ? record.summary : record.scoreSubtitle)
                                                .font(.subheadline)
                                                .foregroundStyle(AppTheme.muted)
                                                .lineLimit(2)
                                            Text(record.clipName)
                                                .font(.caption)
                                                .foregroundStyle(.white.opacity(0.72))
                                        }
                                        Spacer()
                                    }
                                }
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }

                if !appState.isPro && appState.lockedHistoryCount > 0 {
                    LockedFeatureCard(
                        title: "还有 \(appState.lockedHistoryCount) 条记录等待解锁",
                        detail: "升级到 Pro 后，可以查看完整训练历史与后续趋势能力。"
                    ) {
                        appState.openPaywall(from: .history)
                    }
                }
            }
            .padding(20)
            .padding(.bottom, 32)
        }
        .background(AppTheme.background.ignoresSafeArea())
    }

    @ViewBuilder
    private func previewBlock(_ record: AnalysisRecord) -> some View {
        RoundedRectangle(cornerRadius: 18, style: .continuous)
            .fill(AppTheme.thumbnailGradient(for: record.thumbnailStyle))
            .frame(width: 96, height: 96)
            .overlay(
                VStack(alignment: .leading, spacing: 6) {
                    if record.shouldShowFormalScore {
                        Text("\(record.score.overall)")
                            .font(.title.weight(.bold))
                        Text(record.gradeTitle)
                            .font(.caption.weight(.medium))
                    } else {
                        Image(systemName: record.reportState.symbol)
                            .font(.headline)
                        Text(record.gradeTitle)
                            .font(.caption.weight(.medium))
                        Text(record.qualityStatus.title)
                            .font(.caption2)
                            .foregroundStyle(.white.opacity(0.82))
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .bottomLeading)
                .padding(12)
            )
    }
}
