import SwiftUI

struct UploadVideoView: View {
    @EnvironmentObject private var appState: AppState
    @State private var selectedGoal: TrainingGoal = .shooting
    @State private var selectedClipID: DemoClip.ID?

    private var selectedClip: DemoClip? {
        MockData.demoClips.first(where: { $0.id == selectedClipID }) ?? MockData.demoClips.first
    }

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 24) {
                SectionLabel(
                    title: "上传视频",
                    subtitle: "第一版先用演示视频跑完整产品流程"
                )

                FrostedCard {
                    Text("分析目标")
                        .font(.headline)
                    ForEach(TrainingGoal.allCases) { goal in
                        Button {
                            selectedGoal = goal
                        } label: {
                            HStack(alignment: .top, spacing: 14) {
                                Image(systemName: selectedGoal == goal ? "largecircle.fill.circle" : "circle")
                                    .foregroundStyle(selectedGoal == goal ? AppTheme.accent : AppTheme.muted)
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(goal.title)
                                        .font(.subheadline.weight(.semibold))
                                    Text(goal.subtitle)
                                        .font(.caption)
                                        .foregroundStyle(AppTheme.muted)
                                }
                                Spacer()
                            }
                        }
                        .buttonStyle(.plain)
                    }
                }

                SectionLabel(
                    title: "选择演示视频",
                    subtitle: "后续替换成真实视频选择器时，这一层逻辑可以直接复用"
                )

                VStack(spacing: 14) {
                    ForEach(MockData.demoClips) { clip in
                        Button {
                            selectedClipID = clip.id
                        } label: {
                            ThumbnailCard(
                                title: clip.title,
                                subtitle: clip.subtitle,
                                style: clip.style,
                                isSelected: selectedClipID == clip.id || (selectedClipID == nil && clip.id == MockData.demoClips.first?.id)
                            )
                        }
                        .buttonStyle(.plain)
                    }
                }

                if let clip = selectedClip {
                    FrostedCard {
                        SectionLabel(
                            title: clip.durationSeconds > 30.0 ? "当前视频时长过长" : "当前视频时长",
                            subtitle: durationSubtitle(for: clip.durationSeconds)
                        )

                        HStack(alignment: .top, spacing: 12) {
                            Image(systemName: clip.durationSeconds > 30.0 ? "exclamationmark.triangle.fill" : (clip.durationSeconds > 8.0 ? "clock.arrow.circlepath" : "clock.fill"))
                                .foregroundStyle(clip.durationSeconds > 30.0 ? AppTheme.warning : (clip.durationSeconds > 8.0 ? AppTheme.success : AppTheme.accent))
                                .frame(width: 28, height: 28)
                                .background(Circle().fill((clip.durationSeconds > 30.0 ? AppTheme.warning : (clip.durationSeconds > 8.0 ? AppTheme.success : AppTheme.accent)).opacity(0.16)))

                            VStack(alignment: .leading, spacing: 6) {
                                Text(String(format: "当前视频为 %.1f 秒。", clip.durationSeconds))
                                    .font(.subheadline.weight(.semibold))
                                Text(durationHint(for: clip.durationSeconds))
                                    .font(.caption)
                                    .foregroundStyle(AppTheme.muted)
                            }

                            Spacer(minLength: 0)

                            StatusPill(
                                text: String(format: "%.1fs", clip.durationSeconds),
                                tint: clip.durationSeconds > 30.0 ? AppTheme.warning : (clip.durationSeconds > 8.0 ? AppTheme.success : AppTheme.accent)
                            )
                        }
                    }
                }

                PrimaryButton(title: "开始分析", subtitle: "进入处理中页面") {
                    if let clip = selectedClip {
                        logAnalyzeRequest(clip: clip)
                        appState.submitUpload(demoClip: clip, goal: selectedGoal)
                    }
                }
            }
            .padding(20)
            .padding(.bottom, 32)
        }
        .background(AppTheme.background.ignoresSafeArea())
        .navigationTitle("上传视频")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            selectedGoal = appState.selectedGoal
            selectedClipID = MockData.demoClips.first?.id
        }
    }

    private func logAnalyzeRequest(clip: DemoClip) {
        let log: [String: Any] = [
            "selected_action": selectedGoal.backendActionName,
            "selectedAction": selectedGoal.backendActionName,
            "action": selectedGoal.backendActionName,
            "system_action_suggestion": "",
            "analysis_routed_by": "user_selected",
            "routed_analyzer": selectedGoal.backendActionName,
            "goal_display_title": selectedGoal.displayTitle,
            "video_duration": clip.durationSeconds,
            "frame_count": 0,
            "sampled_frame_count": 0,
            "failure_reason": "",
            "warnings": clip.durationSeconds > 30.0 ? ["video_too_long"] : (clip.durationSeconds > 8.0 ? ["auto_localize_enabled"] : []),
        ]

        if let data = try? JSONSerialization.data(withJSONObject: log, options: [.sortedKeys]),
           let text = String(data: data, encoding: .utf8) {
            print("KICK_UPLOAD_REQUEST = \(text)")
            print("KICK_FRONTEND_ANALYZE_REQUEST = \(text)")
        } else {
            print("KICK_UPLOAD_REQUEST = \(log)")
            print("KICK_FRONTEND_ANALYZE_REQUEST = \(log)")
        }
    }

    private func durationHint(for seconds: Double) -> String {
        if seconds > 30.0 {
            return "当前版本支持 30 秒以内视频自动分析。"
        }
        if seconds > 8.0 {
            return "系统会先定位主动作窗口，再裁剪 4–6 秒片段进行分析。"
        }
        return "当前长度适合快速分析，结果会更稳定。"
    }

    private func durationSubtitle(for seconds: Double) -> String {
        if seconds > 30.0 {
            return "当前版本支持 30 秒以内视频自动分析"
        }
        if seconds > 8.0 {
            return "将自动定位主动作片段并分析"
        }
        return "当前长度适合快速分析"
    }
}
