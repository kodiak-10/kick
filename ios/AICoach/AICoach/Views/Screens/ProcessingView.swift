import SwiftUI

struct ProcessingView: View {
    @EnvironmentObject private var appState: AppState

    @State private var progress: Double = 0.14
    @State private var stepIndex = 0
    @State private var startedDraftID: UUID?
    @State private var errorMessage: String?
    @State private var backendAvailable = false
    @State private var backendHealthStatus: String?
    @State private var debugInfo = AnalysisDebugInfo(
        requestURL: AnalysisBackendConfig.analyzeVideoURL,
        healthCheckURL: AnalysisBackendConfig.healthCheckURL
    )

    private let steps = [
        "正在检查后端健康状态",
        "正在准备 multipart 上传",
        "正在上传 video_file",
        "正在解析返回 JSON"
    ]

    private let analysisService = AnalysisService.shared

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(spacing: 24) {
                Spacer(minLength: 18)

                progressRing

                VStack(spacing: 10) {
                    Text(errorMessage == nil ? "分析处理中" : "分析失败")
                        .font(.title2.weight(.semibold))

                    Text(currentStatusText)
                        .font(.subheadline)
                        .foregroundStyle(AppTheme.muted)
                        .multilineTextAlignment(.center)

                    if let draft = appState.draft {
                        Text("\(draft.clipName) · \(Int(draft.durationSeconds)) 秒")
                            .font(.footnote.weight(.medium))
                            .foregroundStyle(AppTheme.text.opacity(0.78))
                    }

                    HStack(spacing: 10) {
                        let healthStatusLabel = errorMessage == nil ? (backendHealthStatus.map { "health \($0)" } ?? "health pending") : "health failed"
                        let healthTint: Color = errorMessage == nil ? ((backendAvailable && backendHealthStatus == "ok") ? AppTheme.success : AppTheme.warning) : AppTheme.danger
                        StatusPill(
                            text: healthStatusLabel,
                            tint: healthTint
                        )
                        StatusPill(text: debugInfo.uploadFieldName, tint: AppTheme.accent)
                    }
                }

                analysisDebugCard

                if let errorMessage {
                    errorCard(message: errorMessage)
                    SecondaryButton(title: "返回上传页") {
                        appState.dismissTopRoute()
                    }
                }

                Spacer(minLength: 18)
            }
            .padding(20)
            .padding(.bottom, 28)
        }
        .background(AppTheme.background.ignoresSafeArea())
        .navigationBarBackButtonHidden(true)
        .task(id: appState.draft?.id) {
            await startAnalysisIfNeeded()
        }
    }

    private var currentStatusText: String {
        if let errorMessage {
            return errorMessage
        }

        let index = min(stepIndex, steps.count - 1)
        return steps[index]
    }

    private var progressRing: some View {
        ZStack {
            Circle()
                .stroke(Color.white.opacity(0.10), lineWidth: 16)
                .frame(width: 150, height: 150)

            Circle()
                .trim(from: 0, to: progress)
                .stroke(
                    AngularGradient(
                        colors: [AppTheme.accent, AppTheme.success, AppTheme.accent],
                        center: .center
                    ),
                    style: StrokeStyle(lineWidth: 16, lineCap: .round)
                )
                .rotationEffect(.degrees(-90))
                .frame(width: 150, height: 150)

            VStack(spacing: 6) {
                Text("\(Int(progress * 100))%")
                    .font(.system(size: 30, weight: .bold, design: .rounded))
                Text("后端请求")
                    .font(.footnote.weight(.medium))
                    .foregroundStyle(AppTheme.muted)
            }
        }
    }

    private var analysisDebugCard: some View {
        FrostedCard {
            SectionLabel(
                title: "开发调试信息",
                subtitle: "request / response / route / failure"
            )

            VStack(alignment: .leading, spacing: 12) {
                debugRow(label: "request_url", value: debugInfo.requestURL)
                debugRow(label: "health_check_url", value: debugInfo.healthCheckURL)
                debugRow(label: "upload_field_name", value: debugInfo.uploadFieldName)
                debugRow(label: "selected_action", value: debugInfo.selectedAction ?? "—")
                debugRow(label: "system_action_suggestion", value: debugInfo.systemActionSuggestion ?? "—")
                debugRow(label: "analysis_routed_by", value: debugInfo.analysisRoutedBy ?? "—")
                debugRow(label: "routed_analyzer", value: debugInfo.routedAnalyzer ?? "—")
                debugRow(label: "analysis_status", value: debugInfo.analysisStatus ?? "—")
                debugRow(label: "failure_reason", value: debugInfo.failureReason ?? "—")
                debugRow(label: "integrity_state", value: debugInfo.integrityState ?? "—")
                debugRow(label: "health_status", value: backendHealthStatus ?? "—")
                debugRow(label: "video_duration_s", value: debugInfo.videoDurationSeconds.map { String(format: "%.1f", $0) } ?? "—")
                debugRow(label: "frame_count", value: debugInfo.frameCount.map(String.init) ?? "—")
                debugRow(label: "sampled_frame_count", value: debugInfo.sampledFrameCount.map(String.init) ?? "—")
                debugRow(label: "fast_mode_enabled", value: debugInfo.fastModeEnabled.map { $0 ? "true" : "false" } ?? "—")
                debugRow(label: "long_video_localized", value: debugInfo.longVideoLocalized.map { $0 ? "true" : "false" } ?? "—")
                debugRow(label: "candidate_window_count", value: debugInfo.candidateWindowCount.map(String.init) ?? "—")
                debugRow(label: "selected_window_index", value: debugInfo.selectedWindowIndex.map(String.init) ?? "—")
                debugRow(
                    label: "selected_window_range",
                    value: selectedWindowRangeText
                )
                debugRow(label: "processing_time_s", value: debugInfo.processingTimeSeconds.map { String(format: "%.3f", $0) } ?? "—")
                debugRow(
                    label: "response_status_code",
                    value: debugInfo.responseStatusCode.map(String.init) ?? "—"
                )
                debugRow(
                    label: "error_message",
                    value: debugInfo.errorMessage ?? "—"
                )
                debugRow(
                    label: "route_mismatch_message",
                    value: debugInfo.routeMismatchMessage ?? "—"
                )
                debugRow(
                    label: "warnings",
                    value: debugInfo.warnings?.joined(separator: " · ") ?? "—"
                )

                VStack(alignment: .leading, spacing: 8) {
                    Text("raw_response_snippet")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(AppTheme.muted)

                    Text(debugInfo.rawResponseSnippet ?? "等待后端返回 JSON 响应")
                        .font(.system(size: 12, design: .monospaced))
                        .foregroundStyle(.white.opacity(0.92))
                        .lineLimit(10)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(12)
                        .background(
                            RoundedRectangle(cornerRadius: 16, style: .continuous)
                                .fill(Color.white.opacity(0.05))
                        )
                }
            }
        }
    }

    private func errorCard(message: String) -> some View {
        FrostedCard {
            HStack(alignment: .top, spacing: 12) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundStyle(AppTheme.danger)
                    .frame(width: 30, height: 30)
                    .background(Circle().fill(AppTheme.danger.opacity(0.16)))

                VStack(alignment: .leading, spacing: 6) {
                    Text("后端分析失败")
                        .font(.headline.weight(.semibold))
                    Text(message)
                        .font(.subheadline)
                        .foregroundStyle(AppTheme.muted)
                }

                Spacer(minLength: 0)
            }
        }
    }

    private func debugRow(label: String, value: String) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Text(label)
                .font(.caption.weight(.semibold))
                .foregroundStyle(AppTheme.muted)
                .frame(width: 150, alignment: .leading)
            Text(value)
                .font(.caption)
                .foregroundStyle(.white.opacity(0.92))
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var selectedWindowRangeText: String {
        if let start = debugInfo.selectedWindowStartSeconds, let end = debugInfo.selectedWindowEndSeconds {
            return String(format: "%.1fs - %.1fs", start, end)
        }

        if let duration = debugInfo.selectedWindowDurationSeconds {
            return String(format: "%.1fs", duration)
        }

        return "—"
    }

    @MainActor
    private func startAnalysisIfNeeded() async {
        guard let draft = appState.draft else {
            errorMessage = "缺少上传草稿，无法开始分析。"
            progress = 1.0
            return
        }

        guard startedDraftID != draft.id else {
            return
        }
        startedDraftID = draft.id

        errorMessage = nil
        backendAvailable = false
        backendHealthStatus = nil
        stepIndex = 0
        progress = 0.14
        debugInfo = AnalysisDebugInfo(
            requestURL: AnalysisBackendConfig.analyzeVideoURL,
            healthCheckURL: AnalysisBackendConfig.healthCheckURL
        )

        await advanceProgress(to: 0.22, step: 0)
        let health = await analysisService.healthCheck()
        debugInfo.responseStatusCode = health.responseStatusCode
        debugInfo.errorMessage = health.errorMessage
        debugInfo.rawResponseSnippet = health.rawResponseSnippet
        backendAvailable = health.isAvailable
        backendHealthStatus = health.status
        stepIndex = 0
        progress = 0.30

        guard health.isAvailable else {
            errorMessage = health.errorMessage ?? "健康检查未通过，后端暂时不可用。"
            progress = 1.0
            return
        }

        await advanceProgress(to: 0.48, step: 1)
        await advanceProgress(to: 0.66, step: 2)

        do {
            let outcome = try await analysisService.analyze(draft: draft)
            debugInfo.responseStatusCode = outcome.debugInfo.responseStatusCode
            debugInfo.errorMessage = outcome.debugInfo.errorMessage
            debugInfo.rawResponseSnippet = outcome.debugInfo.rawResponseSnippet
            debugInfo.selectedAction = outcome.debugInfo.selectedAction
            debugInfo.systemActionSuggestion = outcome.debugInfo.systemActionSuggestion
            debugInfo.analysisRoutedBy = outcome.debugInfo.analysisRoutedBy
            debugInfo.routedAnalyzer = outcome.debugInfo.routedAnalyzer
            debugInfo.analysisStatus = outcome.debugInfo.analysisStatus
            debugInfo.failureReason = outcome.debugInfo.failureReason
            debugInfo.failureMessage = outcome.debugInfo.failureMessage
            debugInfo.integrityState = outcome.debugInfo.integrityState
            debugInfo.routeMismatchMessage = outcome.debugInfo.routeMismatchMessage
            debugInfo.videoDurationSeconds = outcome.debugInfo.videoDurationSeconds
            debugInfo.frameCount = outcome.debugInfo.frameCount
            debugInfo.sampledFrameCount = outcome.debugInfo.sampledFrameCount
            debugInfo.fastModeEnabled = outcome.debugInfo.fastModeEnabled
            debugInfo.processingTimeSeconds = outcome.debugInfo.processingTimeSeconds
            debugInfo.warnings = outcome.debugInfo.warnings
            backendAvailable = true
            stepIndex = 3
            progress = 1.0

            try? await Task.sleep(for: .milliseconds(450))
            appState.commitAnalysis(
                outcome.record,
                preserveDraft: outcome.response.isFailure,
                consumeQuota: !outcome.response.isFailure
            )
        } catch let failure as AnalysisServiceFailure {
            debugInfo = failure.debugInfo
            errorMessage = failure.message
            progress = 1.0
        } catch {
            debugInfo.errorMessage = error.localizedDescription
            errorMessage = error.localizedDescription
            progress = 1.0
        }
    }

    @MainActor
    private func advanceProgress(to value: Double, step: Int) async {
        withAnimation(.easeInOut(duration: 0.35)) {
            progress = value
            stepIndex = step
        }

        try? await Task.sleep(for: .milliseconds(140))
    }
}
