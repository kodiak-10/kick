import PhotosUI
import SwiftUI

struct UploadView: View {
    @EnvironmentObject private var sessionManager: SessionManager
    @StateObject private var viewModel = VideoAnalysisFlowViewModel()

    @State private var pickerItem: PhotosPickerItem?
    @State private var showResult = false
    @State private var analysisResponse: VideoAnalysisResponse?
    @State private var showPaywall = false
    #if DEBUG
    @State private var showDebugDetails = false
    #endif

    private let requirements = [
        "先选择动作类型，再上传本地视频",
        "只支持视频，不支持图片",
        "建议侧面拍摄，确保全程入镜",
        "动作过程尽量完整",
        "文件越清晰，分析越稳定"
    ]

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: AppSpacing.sectionGap) {
                header
                if viewModel.selectedAction == nil {
                    actionSelectionSection
                } else {
                    selectedActionBanner
                    importCard
                    statusCard
                    actionCard
                    debugCard
                    guidanceCard
                }
            }
            .padding(.horizontal, AppSpacing.screenPadding)
            .padding(.top, 12)
            .padding(.bottom, 28)
        }
        .kickScreenBackground()
        .navigationTitle(viewModel.selectedAction == nil ? "选择动作类型" : "上传视频")
        .navigationBarTitleDisplayMode(.inline)
        .kickNavigationBar()
        .onChange(of: pickerItem) { _, newValue in
            guard let newValue else { return }
            pickerItem = nil
            analysisResponse = nil

            Task {
                await viewModel.loadVideo(from: newValue)
            }
        }
        .navigationDestination(isPresented: $showResult) {
            if let response = analysisResponse {
                VideoAnalysisResultView(
                    response: response,
                    selectedAction: viewModel.selectedAction,
                    videoURL: viewModel.selectedVideo?.url,
                    videoDuration: viewModel.selectedVideo?.durationSeconds,
                    videoLabel: viewModel.selectedVideo?.fileName,
                    hasProAccess: sessionManager.latestResultHasProfessionalAccess,
                    onRestart: {
                        resetFlow()
                    },
                    onOpenPaywall: {
                        showPaywall = true
                    }
                )
            } else {
                EmptyStateView(
                    title: "结果暂不可用",
                    subtitle: "请重新选择视频后再试一次。",
                    systemImage: "exclamationmark.triangle.fill"
                )
            }
        }
        .navigationDestination(isPresented: $showPaywall) {
            PaywallView()
        }
    }

    private var header: some View {
        HStack(alignment: .top, spacing: 12) {
            VStack(alignment: .leading, spacing: 10) {
                Text(viewModel.selectedAction == nil ? "先选择动作类型" : "上传本地视频")
                    .font(AppTypography.pageTitle)
                    .foregroundStyle(AppColors.textPrimary)

                Text(viewModel.selectedAction == nil
                     ? "先定动作，再导入本地视频。"
                     : "已选动作：\(viewModel.selectedAction?.displayTitle ?? "未选择")，再导入本地视频开始分析。")
                    .font(AppTypography.body)
                    .foregroundStyle(AppColors.textSecondary)
            }

            Spacer()

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
    }

    @ViewBuilder
    private var importCard: some View {
        if let selectedVideo = viewModel.selectedVideo {
            DarkCard {
                VStack(alignment: .leading, spacing: 18) {
                    HStack(alignment: .top, spacing: 16) {
                        thumbnailView(for: selectedVideo)

                        VStack(alignment: .leading, spacing: 8) {
                            Text("已选择视频")
                                .font(AppTypography.captionMedium)
                                .foregroundStyle(AppColors.textSecondary)

                            Text(selectedVideo.fileName)
                                .font(AppTypography.cardTitle)
                                .foregroundStyle(AppColors.textPrimary)
                                .lineLimit(2)

                            Text("\(selectedVideo.fileSizeLabel) · \(selectedVideo.durationLabel)")
                                .font(AppTypography.body)
                                .foregroundStyle(AppColors.textSecondary)
                        }
                    }
                }
            }
        } else {
            DarkCard {
                VStack(alignment: .leading, spacing: 14) {
                    EmptyStateView(
                        title: "还没有导入视频",
                        subtitle: "点击下面按钮，从本地相册导入一个视频文件。",
                        systemImage: "video.badge.plus"
                    )

                    videoPickerButton(title: "选择本地视频", systemImage: "video.badge.plus", inverted: true)
                }
            }
        }
    }

    @ViewBuilder
    private var debugCard: some View {
        #if DEBUG
        DarkCard {
            DisclosureGroup(isExpanded: $showDebugDetails) {
                VStack(alignment: .leading, spacing: 10) {
                    debugRow(title: "request_url", value: viewModel.debugState.requestURL ?? "未生成")
                    debugRow(
                        title: "request_timeout",
                        value: formattedRequestTimeout(
                            viewModel.debugState.requestTimeoutSeconds ?? viewModel.requestTimeoutSeconds
                        )
                    )
                    debugRow(
                        title: "multipart_field_names",
                        value: debugList(viewModel.debugState.multipartFieldNames)
                    )
                    debugRow(title: "filename", value: viewModel.debugState.filename ?? "未生成")
                    debugRow(title: "mime_type", value: viewModel.debugState.mimeType ?? "未生成")
                    debugRow(
                        title: "request_body_size",
                        value: formattedRequestBodySize(viewModel.debugState.requestBodySize)
                    )
                    debugRow(title: "upload_started", value: boolText(viewModel.debugState.uploadStarted))
                    debugRow(title: "upload_finished", value: boolText(viewModel.debugState.uploadFinished))
                    debugRow(title: "response_received", value: boolText(viewModel.debugState.responseReceived))
                    debugRow(
                        title: "response_status_code",
                        value: viewModel.debugState.responseStatusCode.map(String.init) ?? "未返回"
                    )
                    debugRow(
                        title: "response_text_preview",
                        value: viewModel.debugState.responseTextPreview ?? "未返回"
                    )
                    debugRow(title: "error_message", value: viewModel.debugState.errorMessage ?? "无")
                    if viewModel.debugState.errorMessage != nil {
                        debugRow(
                            title: "current_request_url",
                            value: viewModel.debugState.requestURL ?? "未生成"
                        )
                    }
                }
                .padding(.top, 10)
            } label: {
                VStack(alignment: .leading, spacing: 4) {
                    Text("开发调试信息")
                        .font(AppTypography.cardTitle)
                        .foregroundStyle(AppColors.textPrimary)

                    Text("仅在 DEBUG 构建中显示，用于排查上传与分析链路。")
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textSecondary)
                }
            }
            .tint(AppColors.textPrimary)
        }
        #endif
    }

    @ViewBuilder
    private var statusCard: some View {
        switch viewModel.stage {
        case .idle, .ready:
            EmptyView()
        case .loadingSelection:
            statusInfoCard(
                systemImage: "doc.badge.gearshape",
                title: viewModel.statusTitle,
                subtitle: viewModel.statusSubtitle
            )
        case .analyzing:
            statusProgressCard(
                systemImage: "waveform.badge.magnifyingglass",
                title: viewModel.statusTitle,
                subtitle: viewModel.statusSubtitle,
                accentColor: AppColors.accent
            )
        case .slowProcessing:
            statusProgressCard(
                systemImage: "hourglass",
                title: viewModel.statusTitle,
                subtitle: viewModel.statusSubtitle,
                accentColor: AppColors.warning
            )
        case .timeoutFailed:
            statusInfoCard(
                systemImage: "exclamationmark.triangle.fill",
                title: viewModel.statusTitle,
                subtitle: viewModel.statusSubtitle,
                accentColor: AppColors.critical
            )
        case .failed(let message):
            statusInfoCard(
                systemImage: "exclamationmark.triangle.fill",
                title: viewModel.statusTitle,
                subtitle: message,
                accentColor: AppColors.critical
            )
        }
    }

    @ViewBuilder
    private var actionCard: some View {
        switch viewModel.stage {
        case .idle:
            EmptyView()
        case .loadingSelection:
            EmptyView()
        case .ready:
            if viewModel.selectedVideo != nil {
                actionReadyCard
            } else {
                EmptyView()
            }
        case .analyzing:
            EmptyView()
        case .slowProcessing:
            DarkCard {
                VStack(alignment: .leading, spacing: 14) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("当前视频已保留")
                            .font(AppTypography.cardTitle)
                            .foregroundStyle(AppColors.textPrimary)

                        Text("分析还在继续尝试，不需要重新选视频。你可以先等一会儿，或者直接取消这次等待。")
                            .font(AppTypography.caption)
                            .foregroundStyle(AppColors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    SecondaryButton(title: "取消等待", systemImage: "xmark.circle") {
                        viewModel.cancelAnalysis()
                    }
                }
            }
        case .timeoutFailed:
            timeoutFailedActionCard
        case .failed:
            failureActionCard
        }
    }

    private var actionReadyCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 14) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("可以开始分析")
                        .font(AppTypography.cardTitle)
                        .foregroundStyle(AppColors.textPrimary)

                    Text(viewModel.selectedAction == nil
                         ? "当前视频已就绪，直接开始分析即可。"
                         : "当前视频已就绪，按你选择的“\(viewModel.selectedAction?.displayTitle ?? "本次动作")”开始分析。")
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                HStack(spacing: 12) {
                    PrimaryButton(title: "开始分析", systemImage: "arrow.up.circle.fill") {
                        startAnalysis()
                    }

                    videoPickerButton(title: "更换视频", systemImage: "arrow.clockwise")
                }
            }
        }
    }

    private func statusInfoCard(
        systemImage: String,
        title: String,
        subtitle: String,
        accentColor: Color = AppColors.accent
    ) -> some View {
        DarkCard {
            HStack(alignment: .top, spacing: 12) {
                Image(systemName: systemImage)
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(accentColor)

                VStack(alignment: .leading, spacing: 6) {
                    Text(title)
                        .font(AppTypography.headline)
                        .foregroundStyle(AppColors.textPrimary)

                    Text(subtitle)
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                Spacer(minLength: 0)
            }
        }
    }

    private func statusProgressCard(
        systemImage: String,
        title: String,
        subtitle: String,
        accentColor: Color
    ) -> some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .top, spacing: 12) {
                    ProgressView()
                        .tint(accentColor)

                    Image(systemName: systemImage)
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundStyle(accentColor)

                    VStack(alignment: .leading, spacing: 6) {
                        Text(title)
                            .font(AppTypography.headline)
                            .foregroundStyle(AppColors.textPrimary)

                        Text(subtitle)
                            .font(AppTypography.caption)
                            .foregroundStyle(AppColors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    Spacer(minLength: 0)
                }

                VStack(alignment: .leading, spacing: 8) {
                    ForEach(VideoAnalysisProgressPhase.allCases, id: \.self) { phase in
                        progressRow(for: phase)
                    }
                }
            }
        }
    }

    private func progressRow(for phase: VideoAnalysisProgressPhase) -> some View {
        let currentRaw = viewModel.analysisPhase.rawValue
        let phaseRaw = phase.rawValue
        let isCurrent = phaseRaw == currentRaw
        let isCompleted = phaseRaw < currentRaw
        let color: Color = isCurrent ? AppColors.accent : isCompleted ? AppColors.positive : AppColors.textTertiary

        return HStack(alignment: .center, spacing: 10) {
            Circle()
                .fill(isCurrent ? color.opacity(0.22) : Color.clear)
                .frame(width: isCurrent ? 14 : 12, height: isCurrent ? 14 : 12)
                .overlay(
                    Circle()
                        .stroke(color.opacity(isCurrent ? 0.95 : 0.45), lineWidth: isCurrent ? 2 : 1)
                )

            VStack(alignment: .leading, spacing: 2) {
                Text(phase.title)
                    .font(AppTypography.captionMedium)
                    .foregroundStyle(isCurrent ? AppColors.textPrimary : AppColors.textSecondary)

                Text(phase.detail)
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Spacer(minLength: 0)

            if isCurrent {
                TrainingFeedbackTag(text: "当前")
            } else if isCompleted {
                Image(systemName: "checkmark")
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundStyle(AppColors.positive)
            }
        }
    }

    @ViewBuilder
    private var selectedActionBanner: some View {
        if let selectedAction = viewModel.selectedAction {
            DarkCard {
                VStack(alignment: .leading, spacing: 14) {
                    HStack(alignment: .top, spacing: 12) {
                        ZStack {
                            RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                                .fill(AppColors.accentMuted.opacity(0.18))
                                .frame(width: 44, height: 44)

                            Image(systemName: selectedAction.iconName)
                                .font(.system(size: 18, weight: .semibold))
                                .foregroundStyle(AppColors.accent)
                        }

                        VStack(alignment: .leading, spacing: 5) {
                            Text("已选动作")
                                .font(AppTypography.captionMedium)
                                .foregroundStyle(AppColors.textSecondary)

                            Text(selectedAction.displayTitle)
                                .font(AppTypography.cardTitle)
                                .foregroundStyle(AppColors.textPrimary)

                            Text("动作类型已选定，可以继续上传视频。")
                                .font(AppTypography.caption)
                                .foregroundStyle(AppColors.textSecondary)
                                .fixedSize(horizontal: false, vertical: true)
                        }

                        Spacer(minLength: 0)
                    }

                    if viewModel.stage.isBusy {
                        Text("分析进行中，暂时不能更换动作。")
                            .font(AppTypography.caption)
                            .foregroundStyle(AppColors.textTertiary)
                    } else {
                        SecondaryButton(title: "重新选择动作", systemImage: "arrow.uturn.left") {
                            Haptics.selection()
                            analysisResponse = nil
                            showResult = false
                            viewModel.clearActionSelection()
                        }
                    }
                }
            }
        }
    }

    private var actionSelectionSection: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 16) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("选择分析动作")
                        .font(AppTypography.cardTitle)
                        .foregroundStyle(AppColors.textPrimary)

                    Text("先选动作，再上传视频开始分析。")
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                VStack(spacing: 12) {
                    actionChoiceButton(for: .pass)
                    actionChoiceButton(for: .shot)
                }

                fullMatchAnalysisCard

                if viewModel.selectedVideo != nil {
                    Text("上次导入的视频会保留，重新选动作后可以继续分析。")
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }

    private func actionChoiceButton(for choice: AnalysisActionChoice) -> some View {
        let isSelected = viewModel.selectedAction == choice

        return Button {
            Haptics.selection()
            analysisResponse = nil
            showResult = false
            viewModel.selectAction(choice)
        } label: {
            HStack(alignment: .center, spacing: 14) {
                ZStack {
                    RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                        .fill(isSelected ? AppColors.accentMuted.opacity(0.18) : AppColors.cardSecondary)
                        .frame(width: 46, height: 46)

                    Image(systemName: choice.iconName)
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundStyle(isSelected ? AppColors.accent : AppColors.textSecondary)
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text(choice.displayTitle)
                        .font(AppTypography.cardTitle)
                        .foregroundStyle(AppColors.textPrimary)

                    Text(choice.subtitle)
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                Spacer(minLength: 0)

                Image(systemName: isSelected ? "checkmark.circle.fill" : "chevron.right")
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(isSelected ? AppColors.accent : AppColors.textSecondary)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 13)
            .background(isSelected ? AppColors.backgroundSoft : AppColors.cardSecondary)
            .overlay(
                RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                    .stroke(isSelected ? AppColors.accent.opacity(0.55) : AppColors.stroke, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
        }
        .buttonStyle(.plain)
    }

    private var fullMatchAnalysisCard: some View {
        let isSelected = viewModel.selectedAction == .fullMatch

        return Button {
            Haptics.selection()
            analysisResponse = nil
            showResult = false
            viewModel.selectAction(.fullMatch)
        } label: {
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .top, spacing: 12) {
                    ZStack {
                        RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                            .fill(isSelected ? AppColors.pitchGreen.opacity(0.2) : AppColors.cardSecondary)
                            .frame(width: 46, height: 46)

                        Image(systemName: "sportscourt.fill")
                            .font(.system(size: 18, weight: .semibold))
                            .foregroundStyle(isSelected ? AppColors.pitchGreen : AppColors.accent)
                    }

                    VStack(alignment: .leading, spacing: 6) {
                        HStack(spacing: 8) {
                            Text("单一球员长视频")
                                .font(AppTypography.cardTitle)
                                .foregroundStyle(AppColors.textPrimary)

                            TrainingFeedbackTag(text: "Beta")
                        }

                        Text("适合最长 140 分钟视频。先锁定目标球员，再拆解传球、射门、接球、带球和关键动作窗口。")
                            .font(AppTypography.caption)
                            .foregroundStyle(AppColors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    Spacer(minLength: 0)

                    Image(systemName: isSelected ? "checkmark.circle.fill" : "chevron.right")
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundStyle(isSelected ? AppColors.pitchGreen : AppColors.textSecondary)
                }

                VStack(alignment: .leading, spacing: 8) {
                    fullMatchCapability("锁定：框选目标球员，补球衣颜色、号码和惯用脚")
                    fullMatchCapability("事件：传球、射门、接球、触球和带球时间线")
                    fullMatchCapability("换人：标记上场/换下时间后，只分析该球员真实片段")
                }

                Text("上传后先生成球员锁定流程；未锁定前不输出跑动距离和传射次数，避免伪结果。")
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(10)
                    .background(AppColors.backgroundSoft)
                    .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.small, style: .continuous))
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 13)
            .background(
                LinearGradient(
                    colors: isSelected
                        ? [AppColors.pitchGreen.opacity(0.16), AppColors.cardSecondary]
                        : [AppColors.cardSecondary, AppColors.backgroundSoft.opacity(0.72)],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            )
            .overlay(
                RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                    .stroke(isSelected ? AppColors.pitchGreen.opacity(0.55) : AppColors.stroke, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
        }
        .buttonStyle(.plain)
    }

    private func fullMatchCapability(_ text: String) -> some View {
        HStack(alignment: .top, spacing: 8) {
            Circle()
                .fill(AppColors.accent)
                .frame(width: 6, height: 6)
                .padding(.top, 7)

            Text(text)
                .font(AppTypography.captionMedium)
                .foregroundStyle(AppColors.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var timeoutFailedActionCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 14) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("当前视频还在")
                        .font(AppTypography.cardTitle)
                        .foregroundStyle(AppColors.textPrimary)

                    Text("当前视频较长或分析较复杂，建议等待更久，或换 5-8 秒的单一动作视频")
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                HStack(spacing: 12) {
                    PrimaryButton(title: "继续重试", systemImage: "arrow.clockwise") {
                        startAnalysis()
                    }

                    videoPickerButton(title: "更换视频", systemImage: "arrow.clockwise")
                }
            }
        }
    }

    private var failureActionCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 14) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("视频已保留")
                        .font(AppTypography.cardTitle)
                        .foregroundStyle(AppColors.textPrimary)

                    Text("这次还没有完成，你可以继续重试当前视频，或者换一段更清晰的视频再试。")
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                HStack(spacing: 12) {
                    PrimaryButton(title: "继续重试", systemImage: "arrow.clockwise") {
                        startAnalysis()
                    }

                    videoPickerButton(title: "更换视频", systemImage: "arrow.clockwise")
                }
            }
        }
    }

    private func startAnalysis() {
        guard sessionManager.canStartAnalysis else {
            showPaywall = true
            return
        }

        guard let selectedAction = viewModel.selectedAction else {
            viewModel.requireActionSelection()
            return
        }

        analysisResponse = nil
        showResult = false

        #if DEBUG
        print("KICK_SELECTED_ACTION_REQUEST = \(selectedAction)")
        #endif

        Task {
            do {
                let response = try await viewModel.analyze(selectedAction: selectedAction)
                sessionManager.recordAnalysis(
                    response: response,
                    video: viewModel.selectedVideo,
                    selectedAction: selectedAction
                )
                sessionManager.prepareForAnalysis()
                analysisResponse = response
                showResult = true
            } catch {
                // 状态已经由 viewModel 更新，这里只保留当前页。
            }
        }
    }

    private func videoPickerButton(title: String, systemImage: String, inverted: Bool = false) -> some View {
        PhotosPicker(selection: $pickerItem, matching: .videos, photoLibrary: .shared()) {
            HStack(spacing: 10) {
                Image(systemName: systemImage)
                    .font(.system(size: 14, weight: .semibold))

                Text(title)
                    .font(AppTypography.headline)
            }
            .foregroundStyle(inverted ? AppColors.onAccent : AppColors.textPrimary)
            .frame(maxWidth: .infinity)
            .frame(height: 52)
            .background(inverted ? AppColors.accent : AppColors.cardSecondary)
            .overlay(
                RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                    .stroke(inverted ? Color.clear : AppColors.stroke, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
        }
        .buttonStyle(.plain)
        .disabled(viewModel.stage.isBusy)
    }

    private var guidanceCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 14) {
                Text("上传建议")
                    .font(AppTypography.cardTitle)
                    .foregroundStyle(AppColors.textPrimary)

                ForEach(requirements, id: \.self) { item in
                    HStack(alignment: .top, spacing: 10) {
                        Circle()
                            .fill(AppColors.accent)
                            .frame(width: 6, height: 6)
                            .padding(.top, 8)

                        Text(item)
                            .font(AppTypography.body)
                            .foregroundStyle(AppColors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)

                        Spacer()
                    }
                }
            }
        }
    }

    @ViewBuilder
    private func thumbnailView(for video: ImportedVideo) -> some View {
        ZStack {
            RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [AppColors.backgroundSoft, AppColors.cardSecondary],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .frame(width: 108, height: 108)

            if let thumbnailImage = video.thumbnailImage {
                Image(uiImage: thumbnailImage)
                    .resizable()
                    .scaledToFill()
                    .frame(width: 108, height: 108)
                    .clipped()
                    .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
            } else {
                VStack(spacing: 8) {
                    Image(systemName: "video")
                        .font(.system(size: 26, weight: .medium))
                        .foregroundStyle(AppColors.textSecondary)

                    Text("视频预览")
                        .font(AppTypography.captionMedium)
                        .foregroundStyle(AppColors.textSecondary)
                }
            }
        }
        .overlay(
            RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                .stroke(AppColors.stroke, lineWidth: 1)
        )
    }

    private func debugRow(title: String, value: String) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Text(title)
                .font(.system(size: 12, weight: .semibold, design: .monospaced))
                .foregroundStyle(AppColors.textSecondary)
                .frame(width: 150, alignment: .leading)

            Text(value)
                .font(.system(size: 12, weight: .regular, design: .monospaced))
                .foregroundStyle(AppColors.textPrimary)
                .frame(maxWidth: .infinity, alignment: .leading)
                .textSelection(.enabled)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private func boolText(_ value: Bool) -> String {
        value ? "true" : "false"
    }

    private func debugList(_ values: [String]) -> String {
        guard !values.isEmpty else {
            return "未生成"
        }
        return values.joined(separator: ", ")
    }

    private func formattedRequestBodySize(_ value: Int64?) -> String {
        guard let value else {
            return "未生成"
        }
        return "\(value) bytes"
    }

    private func formattedRequestTimeout(_ value: TimeInterval?) -> String {
        guard let value else {
            return "未生成"
        }

        if value.rounded(.towardZero) == value {
            return "\(Int(value)) 秒"
        }

        return String(format: "%.1f 秒", value)
    }

    private func resetFlow() {
        analysisResponse = nil
        showResult = false
        viewModel.resetSelection()
    }
}
