import AVFoundation
import AVKit
import Combine
import SwiftUI
import UIKit

struct TrainingFeedbackVideoModule: View {
    let viewModel: TrainingFeedbackViewModel
    let videoURL: URL?
    let videoLabel: String?
    @StateObject private var controller: TrainingFeedbackVideoPlaybackController
    @State private var selectedMarkerID: String
    @State private var selectedKeyframeID: String

    init(viewModel: TrainingFeedbackViewModel, videoURL: URL?, videoLabel: String?) {
        self.viewModel = viewModel
        self.videoURL = videoURL
        self.videoLabel = videoLabel
        _controller = StateObject(
            wrappedValue: TrainingFeedbackVideoPlaybackController(
                videoURL: videoURL,
                duration: viewModel.videoEvidence.duration
            )
        )
        _selectedMarkerID = State(
            initialValue: viewModel.videoEvidence.markers.first(where: { $0.isPriority })?.id
                ?? viewModel.videoEvidence.markers.first?.id
                ?? ""
        )
        _selectedKeyframeID = State(
            initialValue: viewModel.videoEvidence.primaryKeyframeID.nonEmpty
                ?? viewModel.videoEvidence.keyframes.first(where: { $0.isPrimary })?.id
                ?? viewModel.videoEvidence.keyframes.first?.id
                ?? ""
        )
    }

    private var selectedMarker: TrainingFeedbackTimelineMarker? {
        viewModel.videoEvidence.markers.first(where: { $0.id == selectedMarkerID })
            ?? viewModel.videoEvidence.markers.first
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            if videoURL != nil {
                TrainingFeedbackVideoSurface(
                    controller: controller,
                    videoLabel: videoLabel,
                    evidence: viewModel.videoEvidence,
                    selectedMarker: selectedMarker,
                    showsPlaybackControls: true,
                    onResetToStart: resetToStart
                )
            } else {
                TrainingFeedbackVideoSurface(
                    controller: controller,
                    videoLabel: videoLabel,
                    evidence: viewModel.videoEvidence,
                    selectedMarker: selectedMarker,
                    showsPlaybackControls: false,
                    onResetToStart: resetToStart
                )
            }

            TrainingFeedbackTimelineView(
                markers: viewModel.videoEvidence.markers,
                duration: viewModel.videoEvidence.duration,
                currentTime: controller.currentTime,
                selectedMarkerID: selectedMarkerID,
                allowsSeeking: true,
                onSelect: { marker in
                    selectMarker(marker, haptic: .medium)
                },
                onSnapToMarker: { marker in
                    selectMarker(marker, haptic: .selection)
                },
                onScrubTime: { time in
                    controller.seek(to: time)
                }
            )

            TrainingFeedbackTrajectorySimulationCard(viewModel: viewModel)

            TrainingFeedbackKeyframeSection(
                keyframes: viewModel.videoEvidence.keyframes,
                videoURL: videoURL,
                selectedKeyframeID: $selectedKeyframeID,
                onSelectKeyframe: { spec in
                    selectKeyframe(spec)
                },
                onJumpToTime: { time in
                    controller.seek(to: time)
                }
            )
        }
        .onChange(of: controller.currentTime) { _, newValue in
            syncSelection(for: newValue)
        }
    }

    private func selectMarker(_ marker: TrainingFeedbackTimelineMarker, haptic: HapticStyle) {
        switch haptic {
        case .light:
            Haptics.light()
        case .medium:
            Haptics.medium()
        case .selection:
            Haptics.selection()
        }

        withAnimation(.easeOut(duration: 0.18)) {
            selectedMarkerID = marker.id
        }
        controller.seek(to: marker.time)

        if let nearestKeyframe = nearestKeyframe(for: marker.time) {
            withAnimation(.easeOut(duration: 0.18)) {
                selectedKeyframeID = nearestKeyframe.id
            }
        }
    }

    private func selectKeyframe(_ spec: TrainingFeedbackKeyframeSpec) {
        if spec.isPrimary {
            Haptics.light()
        } else {
            Haptics.medium()
        }

        withAnimation(.easeOut(duration: 0.18)) {
            selectedKeyframeID = spec.id
        }
        controller.seek(to: spec.time)

        if let nearestMarker = nearestMarker(for: spec.time) {
            withAnimation(.easeOut(duration: 0.18)) {
                selectedMarkerID = nearestMarker.id
            }
        }
    }

    private func syncSelection(for time: Double) {
        if let nearestMarker = nearestMarker(for: time), abs(nearestMarker.time - time) < 0.35 {
            selectedMarkerID = nearestMarker.id
        }

        if let nearestKeyframe = nearestKeyframe(for: time), abs(nearestKeyframe.time - time) < 0.45 {
            selectedKeyframeID = nearestKeyframe.id
        }
    }

    private func nearestMarker(for time: Double) -> TrainingFeedbackTimelineMarker? {
        viewModel.videoEvidence.markers.min { lhs, rhs in
            abs(lhs.time - time) < abs(rhs.time - time)
        }
    }

    private func nearestKeyframe(for time: Double) -> TrainingFeedbackKeyframeSpec? {
        viewModel.videoEvidence.keyframes.min { lhs, rhs in
            abs(lhs.time - time) < abs(rhs.time - time)
        }
    }

    private func resetToStart() {
        controller.seek(to: 0)
        withAnimation(.easeOut(duration: 0.18)) {
            if let firstMarker = viewModel.videoEvidence.markers.first {
                selectedMarkerID = firstMarker.id
            }
            if let primaryKeyframe = viewModel.videoEvidence.keyframes.first(where: { $0.isPrimary })
                ?? viewModel.videoEvidence.keyframes.first {
                selectedKeyframeID = primaryKeyframe.id
            }
        }
    }

    private enum HapticStyle {
        case light
        case medium
        case selection
    }
}

private struct TrainingFeedbackVideoSurface: View {
    let controller: TrainingFeedbackVideoPlaybackController
    let videoLabel: String?
    let evidence: TrainingFeedbackVideoEvidence
    let selectedMarker: TrainingFeedbackTimelineMarker?
    let showsPlaybackControls: Bool
    let onResetToStart: () -> Void

    private var currentTimeLabel: String {
        String(format: "%.1fs", controller.currentTime)
    }

    private var hasVideo: Bool {
        controller.hasVideo
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top, spacing: 10) {
                VStack(alignment: .leading, spacing: 5) {
                    Text(videoLabel?.nonEmpty ?? "原视频回放")
                        .font(AppTypography.cardTitle)
                        .foregroundStyle(AppColors.textPrimary)

                    Text(hasVideo ? "点击时间点或拖动时间轴可跳到关键时刻" : "当前结果没有原视频，只能先看关键时刻。")
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textSecondary)
                }

                Spacer(minLength: 0)

                VStack(alignment: .trailing, spacing: 6) {
                    Text("\(currentTimeLabel) / \(evidence.durationText)")
                        .font(AppTypography.captionMedium)
                        .foregroundStyle(AppColors.textSecondary)

                    TrainingFeedbackTag(text: selectedMarker?.kind.displayLabel ?? "接球")
                }
            }

            ZStack(alignment: .topLeading) {
                if hasVideo {
                    VideoPlayer(player: controller.player)
                        .frame(maxWidth: .infinity)
                        .frame(height: 220)
                        .background(AppColors.backgroundSoft)
                        .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
                } else {
                    RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                        .fill(
                            LinearGradient(
                                colors: [
                                    AppColors.backgroundSoft,
                                    AppColors.cardSecondary,
                                    AppColors.background
                                ],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .frame(height: 220)
                        .overlay(
                            VStack(spacing: 12) {
                                Image(systemName: "video")
                                    .font(.system(size: 30, weight: .semibold))
                                    .foregroundStyle(AppColors.textSecondary)

                                Text("暂无原视频")
                                    .font(AppTypography.headline)
                                    .foregroundStyle(AppColors.textPrimary)

                                Text("回放、跳转和关键帧提取需要原视频文件。")
                                    .font(AppTypography.caption)
                                    .foregroundStyle(AppColors.textSecondary)
                            }
                            .padding(16)
                        )
                }

                LinearGradient(
                    colors: [
                        Color.black.opacity(0.55),
                        Color.clear
                    ],
                    startPoint: .top,
                    endPoint: .center
                )
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
                .allowsHitTesting(false)

                VStack(alignment: .leading, spacing: 8) {
                    if let selectedMarker {
                        TrainingFeedbackTag(text: selectedMarker.title)

                        Text(selectedMarker.detail)
                            .font(AppTypography.caption)
                            .foregroundStyle(Color.white.opacity(0.9))
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    Spacer(minLength: 0)

                    if showsPlaybackControls {
                        HStack(spacing: 10) {
                            playbackControlButton(
                                systemImage: controller.isPlaying ? "pause.fill" : "play.fill"
                            ) {
                                controller.togglePlayPause()
                            }

                        playbackControlButton(systemImage: "backward.end.fill") {
                            onResetToStart()
                        }

                            Spacer(minLength: 0)
                        }
                    }
                }
                .padding(14)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            }
            .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
        }
    }

    private func playbackControlButton(systemImage: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: systemImage)
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(AppColors.textPrimary)
                .frame(width: 34, height: 34)
                .background(Color.white.opacity(0.08))
                .clipShape(Circle())
        }
        .buttonStyle(.plain)
    }
}

private struct TrainingFeedbackTimelineView: View {
    let markers: [TrainingFeedbackTimelineMarker]
    let duration: Double
    let currentTime: Double
    let selectedMarkerID: String
    let allowsSeeking: Bool
    let onSelect: (TrainingFeedbackTimelineMarker) -> Void
    let onSnapToMarker: (TrainingFeedbackTimelineMarker) -> Void
    let onScrubTime: (Double) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    Capsule()
                        .fill(AppColors.backgroundSoft)
                        .frame(height: 6)
                        .offset(y: 16)
                        .gesture(trackDragGesture(width: geometry.size.width))

                    Capsule()
                        .fill(AppColors.accent)
                        .frame(width: progressWidth(in: geometry.size.width), height: 6)
                        .offset(y: 16)

                    ForEach(markers) { marker in
                        let x = xPosition(for: marker, width: geometry.size.width)

                        Button {
                            if allowsSeeking {
                                onSelect(marker)
                            }
                        } label: {
                            VStack(spacing: 4) {
                                Circle()
                                    .fill(dotColor(for: marker))
                                    .frame(width: selectedMarkerID == marker.id ? 12 : 10,
                                           height: selectedMarkerID == marker.id ? 12 : 10)
                                    .overlay(
                                        Circle()
                                            .stroke(Color.white.opacity(selectedMarkerID == marker.id ? 0.65 : 0.18), lineWidth: 1)
                                    )

                                Text(marker.timeLabel)
                                    .font(AppTypography.captionMedium)
                                    .foregroundStyle(AppColors.textSecondary)
                            }
                        }
                        .buttonStyle(.plain)
                        .position(x: x, y: 22)
                    }
                }
            }
            .frame(height: 46)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(markers) { marker in
                        TrainingFeedbackMarkerChip(
                            marker: marker,
                            isSelected: selectedMarkerID == marker.id
                        ) {
                            onSelect(marker)
                        }
                    }
                }
                .padding(.vertical, 2)
            }

            HStack(spacing: 8) {
                Text("当前时间 \(formattedTime(currentTime))")
                    .font(AppTypography.captionMedium)
                    .foregroundStyle(AppColors.textSecondary)

                Spacer(minLength: 0)

                Text("总时长 \(formattedTime(duration))")
                    .font(AppTypography.captionMedium)
                    .foregroundStyle(AppColors.textSecondary)
            }
        }
    }

    private func xPosition(for marker: TrainingFeedbackTimelineMarker, width: CGFloat) -> CGFloat {
        guard duration > 0 else { return 12 }
        let ratio = min(max(marker.time / duration, 0), 1)
        return max(12, min(width - 12, width * CGFloat(ratio)))
    }

    private func time(for x: CGFloat, width: CGFloat) -> Double {
        guard duration > 0 else { return 0 }
        let ratio = min(max(x / width, 0), 1)
        return duration * Double(ratio)
    }

    private func progressWidth(in width: CGFloat) -> CGFloat {
        guard duration > 0 else { return 0 }
        let ratio = min(max(currentTime / duration, 0), 1)
        return max(4, width * CGFloat(ratio))
    }

    private func trackDragGesture(width: CGFloat) -> some Gesture {
        DragGesture(minimumDistance: 0)
            .onChanged { value in
                guard allowsSeeking else { return }
                let time = time(for: value.location.x, width: width)
                onScrubTime(time)
            }
            .onEnded { value in
                guard allowsSeeking else { return }
                let time = time(for: value.location.x, width: width)
                if let nearest = nearestMarker(for: time), abs(nearest.time - time) < snapThreshold {
                    onSnapToMarker(nearest)
                } else {
                    onScrubTime(time)
                }
            }
    }

    private func dotColor(for marker: TrainingFeedbackTimelineMarker) -> Color {
        if selectedMarkerID == marker.id {
            return AppColors.accent
        }

        switch marker.status {
        case .excellent:
            return AppColors.positive
        case .good:
            return AppColors.accentMuted
        case .needsWork:
            return AppColors.warning
        case .reference:
            return AppColors.textTertiary
        }
    }

    private func formattedTime(_ value: Double) -> String {
        String(format: "%.1fs", max(value, 0))
    }

    private func nearestMarker(for time: Double) -> TrainingFeedbackTimelineMarker? {
        markers.min { lhs, rhs in
            abs(lhs.time - time) < abs(rhs.time - time)
        }
    }

    private var snapThreshold: Double {
        max(0.18, duration * 0.06)
    }
}

private struct TrainingFeedbackMarkerChip: View {
    let marker: TrainingFeedbackTimelineMarker
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 7) {
                Image(systemName: marker.kind.symbolName)
                    .font(.system(size: 11, weight: .semibold))
                Text("\(marker.kind.displayLabel) · \(marker.timeLabel)")
                    .font(AppTypography.captionMedium)
            }
            .foregroundStyle(isSelected ? AppColors.textPrimary : AppColors.textSecondary)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(isSelected ? AppColors.backgroundElevated : AppColors.backgroundSoft)
            .overlay(
                Capsule()
                    .stroke(isSelected ? AppColors.strongStroke : AppColors.stroke, lineWidth: 1)
            )
            .clipShape(Capsule())
        }
        .buttonStyle(.plain)
    }
}

struct TrainingFeedbackKeyframeSection: View {
    let keyframes: [TrainingFeedbackKeyframeSpec]
    let videoURL: URL?
    @Binding var selectedKeyframeID: String
    let onSelectKeyframe: (TrainingFeedbackKeyframeSpec) -> Void
    let onJumpToTime: (Double) -> Void

    @StateObject private var loader: TrainingFeedbackFrameLoader
    init(
        keyframes: [TrainingFeedbackKeyframeSpec],
        videoURL: URL?,
        selectedKeyframeID: Binding<String>,
        onSelectKeyframe: @escaping (TrainingFeedbackKeyframeSpec) -> Void,
        onJumpToTime: @escaping (Double) -> Void
    ) {
        self.keyframes = keyframes
        self.videoURL = videoURL
        _selectedKeyframeID = selectedKeyframeID
        self.onSelectKeyframe = onSelectKeyframe
        self.onJumpToTime = onJumpToTime
        _loader = StateObject(
            wrappedValue: TrainingFeedbackFrameLoader(
                videoURL: videoURL,
                keyframes: keyframes
            )
        )
    }

    private var primaryKeyframe: TrainingFeedbackKeyframeSpec? {
        keyframes.first(where: { $0.isPrimary }) ?? keyframes.first
    }

    private var supportingKeyframes: [TrainingFeedbackKeyframeSpec] {
        guard let primaryKeyframe else { return keyframes }
        return keyframes.filter { $0.id != primaryKeyframe.id }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            TrainingFeedbackSectionHeader(
                title: "关键帧反馈",
                subtitle: "先看本次最关键帧，再横向切换其他帧。当前不叠加不稳定的位置圈选，避免误导。"
            )

            if let primaryKeyframe {
                TrainingFeedbackKeyframePreviewCard(
                    spec: primaryKeyframe,
                    image: loader.image(for: primaryKeyframe.id),
                    isLoading: loader.isLoading,
                    isPrimary: true,
                    isSelected: selectedKeyframeID == primaryKeyframe.id || selectedKeyframeID.isEmpty
                ) {
                    openKeyframe(primaryKeyframe)
                }
            }

            if !supportingKeyframes.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(alignment: .top, spacing: 12) {
                        ForEach(supportingKeyframes, id: \.id) { spec in
                            TrainingFeedbackKeyframePreviewCard(
                                spec: spec,
                                image: loader.image(for: spec.id),
                                isLoading: loader.isLoading,
                                isPrimary: false,
                                isSelected: selectedKeyframeID == spec.id
                            ) {
                                openKeyframe(spec)
                            }
                            .frame(width: 274)
                        }
                    }
                    .padding(.vertical, 2)
                }
            }

            keyframeLegend
        }
    }

    private func openKeyframe(_ spec: TrainingFeedbackKeyframeSpec) {
        selectedKeyframeID = spec.id
        onSelectKeyframe(spec)
        onJumpToTime(spec.time)
    }

    private var keyframeLegend: some View {
        HStack(spacing: 10) {
            legendItem(color: AppColors.positive, text: "做得对")
            legendItem(color: AppColors.warning, text: "需注意")
            legendItem(color: AppColors.critical, text: "明显问题")
        }
        .font(AppTypography.captionMedium)
        .foregroundStyle(AppColors.textSecondary)
    }

    private func legendItem(color: Color, text: String) -> some View {
        HStack(spacing: 6) {
            Circle()
                .fill(color)
                .frame(width: 8, height: 8)
            Text(text)
        }
    }
}

private struct TrainingFeedbackKeyframePreviewCard: View {
    let spec: TrainingFeedbackKeyframeSpec
    let image: UIImage?
    let isLoading: Bool
    let isPrimary: Bool
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            TrainingFeedbackMiniCard(padding: 0) {
                VStack(alignment: .leading, spacing: 0) {
                    ZStack(alignment: .topLeading) {
                        TrainingFeedbackKeyframeFrameSurface(
                            spec: spec,
                            image: image,
                            isLoading: isLoading,
                            height: isPrimary ? 230 : 176
                        )

                        VStack(alignment: .leading, spacing: 10) {
                            HStack(alignment: .top, spacing: 8) {
                                TrainingFeedbackTag(text: spec.title)

                                if isPrimary {
                                    TrainingFeedbackTag(text: "本次最关键帧")
                                }

                                Spacer(minLength: 0)

                                Text(String(format: "%.1fs", spec.time))
                                    .font(AppTypography.captionMedium)
                                    .foregroundStyle(Color.white.opacity(0.9))
                            }

                            Spacer(minLength: 0)

                            if isPrimary {
                                Text(spec.conclusion)
                                    .font(AppTypography.bodyMedium)
                                    .foregroundStyle(Color.white.opacity(0.96))
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                        .padding(14)
                        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                    }
                    .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))

                    keyframeFocusStrip

                    VStack(alignment: .leading, spacing: 10) {
                        keyframeLine(label: "本帧结论", value: spec.conclusion, emphasize: true)
                        keyframeLine(label: mainPointLabel, value: spec.mainPoint, emphasize: true)
                        keyframeLine(label: "为什么重要", value: spec.whyImportant, emphasize: false)
                        keyframeLine(label: "怎么改", value: spec.howToChange, emphasize: false)

                        HStack(spacing: 8) {
                            TrainingFeedbackTag(text: spec.status.displayLabel)
                            TrainingFeedbackTag(text: spec.confidence.displayLabel)
                            Spacer(minLength: 0)
                            Text(isSelected ? "当前选中" : "点击切换")
                                .font(AppTypography.captionMedium)
                                .foregroundStyle(isSelected ? AppColors.textPrimary : AppColors.textSecondary)
                        }

                        Text(spec.confidenceNote)
                            .font(AppTypography.caption)
                            .foregroundStyle(AppColors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .padding(.horizontal, AppSpacing.cardPadding)
                    .padding(.vertical, AppSpacing.compactPadding)
                }
            }
        }
        .buttonStyle(.plain)
        .overlay(
            RoundedRectangle(cornerRadius: AppCornerRadius.large, style: .continuous)
                .stroke(isSelected ? AppColors.strongStroke : AppColors.stroke, lineWidth: isSelected ? 1.2 : 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.large, style: .continuous))
    }

    private var keyframeFocusStrip: some View {
        HStack(alignment: .center, spacing: 8) {
            Label("教练看点", systemImage: "scope")
                .font(AppTypography.captionMedium)
                .foregroundStyle(AppColors.textPrimary)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 6) {
                    ForEach(focusLabels, id: \.self) { label in
                        Text(label)
                            .font(AppTypography.captionMedium)
                            .foregroundStyle(AppColors.textSecondary)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 5)
                            .background(AppColors.backgroundSoft)
                            .clipShape(Capsule())
                    }
                }
            }
        }
        .padding(.horizontal, AppSpacing.cardPadding)
        .padding(.vertical, 10)
        .background(AppColors.cardSecondary)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(AppColors.stroke)
                .frame(height: 1)
        }
    }

    private var focusLabels: [String] {
        let labels = spec.visibleAnnotations.map { $0.kind.displayLabel }
        if !labels.isEmpty {
            return Array(labels.prefix(3))
        }

        return [spec.moment.displayTitle, spec.status.displayLabel]
    }

    private func keyframeLine(label: String, value: String, emphasize: Bool) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(AppTypography.captionMedium)
                .foregroundStyle(AppColors.textSecondary)

            Text(value)
                .font(emphasize ? AppTypography.bodyMedium : AppTypography.body)
                .foregroundStyle(AppColors.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var mainPointLabel: String {
        if spec.status == .reference {
            return "参考点"
        }

        return spec.status.isPositive ? "主亮点" : "主问题"
    }
}

private struct TrainingFeedbackKeyframeFrameSurface: View {
    let spec: TrainingFeedbackKeyframeSpec
    let image: UIImage?
    let isLoading: Bool
    let height: CGFloat
    let selectedAnnotationID: String?
    let onSelectAnnotation: ((TrainingFeedbackFrameAnnotation) -> Void)?

    init(
        spec: TrainingFeedbackKeyframeSpec,
        image: UIImage?,
        isLoading: Bool,
        height: CGFloat,
        selectedAnnotationID: String? = nil,
        onSelectAnnotation: ((TrainingFeedbackFrameAnnotation) -> Void)? = nil
    ) {
        self.spec = spec
        self.image = image
        self.isLoading = isLoading
        self.height = height
        self.selectedAnnotationID = selectedAnnotationID
        self.onSelectAnnotation = onSelectAnnotation
    }

    var body: some View {
        ZStack(alignment: .topLeading) {
            frameBackground

            if let image {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFill()
                    .frame(maxWidth: .infinity)
                    .frame(height: height)
                    .clipped()
            } else {
                framePlaceholder
            }

            LinearGradient(
                colors: [
                    Color.black.opacity(0.68),
                    Color.clear
                ],
                startPoint: .bottom,
                endPoint: .center
            )
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .allowsHitTesting(false)

        }
        .frame(height: height)
    }

    private var frameBackground: some View {
        RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
            .fill(
                LinearGradient(
                    colors: [
                        AppColors.backgroundSoft,
                        AppColors.cardSecondary,
                        AppColors.background
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            )
    }

    private var framePlaceholder: some View {
        VStack(spacing: 12) {
            if isLoading {
                ProgressView()
                    .tint(AppColors.accent)
            } else {
                Image(systemName: "video")
                    .font(.system(size: 28, weight: .semibold))
                    .foregroundStyle(AppColors.textSecondary)
            }

            Text("关键帧")
                .font(AppTypography.headline)
                .foregroundStyle(AppColors.textPrimary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

private struct TrainingFeedbackConfidenceBanner: View {
    let note: String

    var body: some View {
        VStack {
            Spacer(minLength: 0)

            HStack {
                Text(note)
                    .font(AppTypography.captionMedium)
                    .foregroundStyle(Color.white.opacity(0.92))
                    .fixedSize(horizontal: false, vertical: true)

                Spacer(minLength: 0)
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 8)
            .background(Color.black.opacity(0.42))
            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        }
    }
}

private struct TrainingFeedbackTrajectorySimulationCard: View {
    let viewModel: TrainingFeedbackViewModel
    @State private var animateBall = false

    private var focus: TrainingFeedbackPriorityFocus {
        viewModel.priorityFocus
    }

    private var metricKey: ResultMetricKey {
        focus.metricKey
    }

    private var isShot: Bool {
        viewModel.selectedAction == .shot ||
            viewModel.actionName.localizedCaseInsensitiveContains("射门") ||
            viewModel.actionName.localizedCaseInsensitiveContains("shot")
    }

    var body: some View {
        TrainingFeedbackMiniCard(padding: AppSpacing.compactPadding) {
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .top, spacing: 10) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("教练示意图")
                            .font(AppTypography.bodyMedium)
                            .foregroundStyle(AppColors.textPrimary)

                        Text(simulationSubtitle)
                            .font(AppTypography.caption)
                            .foregroundStyle(AppColors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    Spacer(minLength: 0)

                    TrainingFeedbackTag(text: focus.title)
                }

                GeometryReader { proxy in
                    ZStack {
                        RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                            .fill(
                                LinearGradient(
                                    colors: [
                                        AppColors.backgroundElevated,
                                        AppColors.backgroundSoft
                                    ],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )
                            .overlay(fieldLines)

                        simulationContent(width: proxy.size.width, height: proxy.size.height)
                    }
                }
                .frame(height: 168)
                .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
                .onAppear {
                    guard !animateBall else { return }
                    withAnimation(.easeInOut(duration: 1.4).repeatForever(autoreverses: true)) {
                        animateBall = true
                    }
                }

                Text("说明：这是根据本次优先指标生成的训练结构图，不是视频里的精确标注；深色线表示建议动作路径，橙色表示需要注意的偏差。")
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var simulationSubtitle: String {
        switch metricKey {
        case .passEndpointErrorM:
            return "这次重点看传球落点：理想线路要穿过目标门，偏差越大越需要先降速校准。"
        case .passExecutionTimeS:
            return "这次重点看接球到出脚的节奏：停顿越长，传球越容易和下一动作脱节。"
        case .receiveControlZoneSuccessRate:
            return "这次重点看第一脚控制区：第一脚要把球带到下一步能处理的位置。"
        case .receiveStabilizationTimeS, .receiveCorrectiveTouchCount:
            return "这次重点看接球后的回稳和补救触球：少调整、快站稳，下一脚才更顺。"
        case .passReceiveGapS, .sequenceContinuityScore, .nextActionReadiness:
            return "这次重点看动作链路：接球、出脚和下一步移动要连起来。"
        case .shotTargetZoneHit:
            return "这次重点看射门目标区：先明确打近角/远角，再看是否进门和进门位置。"
        case .shotMaxBallSpeedMPS, .shotMaxBallSpeedProxyMPS:
            return "这次重点看发力链：髋部带大腿、大腿带小腿，脚踝锁定后再加速。"
        case .shotConsistencyCVPercent:
            return "这次重点看射门重复性：同一距离和目标下，支撑脚和收尾要尽量一致。"
        case .supportFootLateralOffsetCM, .supportFootAPOffsetCM:
            return "这次重点看支撑脚：支撑脚应落在球侧后方，脚尖指向目标线，触球脚才能稳定摆过球。"
        case .trunkLeanDegAtImpactProxy:
            return "这次重点看身体角度：髋部不要提前打开，躯干略向前压，球路会更低更稳。"
        }
    }

    @ViewBuilder
    private func simulationContent(width: CGFloat, height: CGFloat) -> some View {
        switch metricKey {
        case .passEndpointErrorM:
            passLandingSimulation(width: width, height: height)
        case .passExecutionTimeS:
            timingSimulation(width: width, height: height)
        case .receiveControlZoneSuccessRate, .receiveStabilizationTimeS, .receiveCorrectiveTouchCount:
            receiveSimulation(width: width, height: height)
        case .passReceiveGapS, .sequenceContinuityScore, .nextActionReadiness:
            sequenceSimulation(width: width, height: height)
        case .shotTargetZoneHit:
            shotTargetSimulation(width: width, height: height)
        case .shotMaxBallSpeedMPS, .shotMaxBallSpeedProxyMPS, .shotConsistencyCVPercent:
            shotPowerSimulation(width: width, height: height)
        case .supportFootLateralOffsetCM, .supportFootAPOffsetCM, .trunkLeanDegAtImpactProxy:
            supportSimulation(width: width, height: height)
        }
    }

    private func passLandingSimulation(width: CGFloat, height: CGFloat) -> some View {
        let start = CGPoint(x: width * 0.18, y: height * 0.68)
        let idealEnd = CGPoint(x: width * 0.80, y: height * 0.42)
        let actualEnd = CGPoint(x: width * 0.74, y: focus.status == .needsWork ? height * 0.62 : height * 0.48)
        let control = CGPoint(x: width * 0.48, y: height * 0.32)

        return ZStack {
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(AppColors.textPrimary.opacity(0.35), lineWidth: 2)
                .frame(width: width * 0.16, height: height * 0.26)
                .position(idealEnd)

            Text("目标门")
                .font(AppTypography.captionMedium)
                .foregroundStyle(AppColors.textSecondary)
                .position(x: idealEnd.x, y: height * 0.24)

            path(from: start, to: idealEnd, control: control)
                .stroke(AppColors.accent, style: StrokeStyle(lineWidth: 4, lineCap: .round, dash: [8, 7]))

            path(from: start, to: actualEnd, control: CGPoint(x: width * 0.46, y: height * 0.58))
                .trim(from: 0, to: animateBall ? 1 : 0.12)
                .stroke(Color.orange, style: StrokeStyle(lineWidth: 5, lineCap: .round))

            ball(at: animateBall ? actualEnd : start)

            label("理想线路", at: CGPoint(x: width * 0.48, y: height * 0.26), color: AppColors.accent)
            label(focus.status == .needsWork ? "本次偏差" : "落点可控", at: CGPoint(x: width * 0.55, y: height * 0.66), color: Color.orange)
        }
    }

    private func timingSimulation(width: CGFloat, height: CGFloat) -> some View {
        let points = [
            CGPoint(x: width * 0.22, y: height * 0.56),
            CGPoint(x: width * 0.50, y: height * 0.56),
            CGPoint(x: width * 0.78, y: height * 0.56)
        ]
        let labels = ["接球", "支撑脚到位", "出脚"]

        return ZStack {
            Path { path in
                path.move(to: points[0])
                path.addLine(to: points[2])
            }
            .stroke(AppColors.stroke, style: StrokeStyle(lineWidth: 4, lineCap: .round))

            if focus.status == .needsWork || focus.status == .reference {
                Capsule()
                    .fill(Color.orange.opacity(0.22))
                    .frame(width: width * 0.25, height: 28)
                    .position(x: width * 0.36, y: height * 0.38)
                label(focus.status == .needsWork ? "停顿偏长" : "节奏待确认", at: CGPoint(x: width * 0.36, y: height * 0.38), color: Color.orange)
            }

            ForEach(Array(points.enumerated()), id: \.offset) { index, point in
                VStack(spacing: 8) {
                    Circle()
                        .fill(index == 2 && animateBall ? AppColors.accent : AppColors.textPrimary)
                        .frame(width: 18, height: 18)

                    Text(labels[index])
                        .font(AppTypography.captionMedium)
                        .foregroundStyle(AppColors.textPrimary)
                }
                .position(point)
            }
        }
    }

    private func receiveSimulation(width: CGFloat, height: CGFloat) -> some View {
        let entry = CGPoint(x: width * 0.18, y: height * 0.45)
        let target = CGPoint(x: width * 0.55, y: height * 0.56)
        let actual = CGPoint(x: focus.status == .needsWork ? width * 0.72 : width * 0.58, y: focus.status == .needsWork ? height * 0.70 : height * 0.58)

        return ZStack {
            Circle()
                .stroke(AppColors.accent.opacity(0.72), lineWidth: 4)
                .frame(width: width * 0.28, height: width * 0.28)
                .position(target)

            label("第一脚控制区", at: CGPoint(x: target.x, y: target.y - width * 0.18), color: AppColors.accent)

            path(from: entry, to: actual, control: CGPoint(x: width * 0.38, y: height * 0.36))
                .trim(from: 0, to: animateBall ? 1 : 0.18)
                .stroke(focus.status == .needsWork ? Color.orange : AppColors.accent, style: StrokeStyle(lineWidth: 5, lineCap: .round))

            ball(at: animateBall ? actual : entry)
            label(focus.status == .needsWork ? "第一脚跑出区" : "第一脚入区", at: CGPoint(x: actual.x, y: actual.y + 30), color: focus.status == .needsWork ? Color.orange : AppColors.accent)
        }
    }

    private func sequenceSimulation(width: CGFloat, height: CGFloat) -> some View {
        let nodes = [
            CGPoint(x: width * 0.20, y: height * 0.60),
            CGPoint(x: width * 0.50, y: height * 0.42),
            CGPoint(x: width * 0.80, y: height * 0.60)
        ]
        let labels = ["接球", "传出", "下一步"]

        return ZStack {
            path(from: nodes[0], to: nodes[1], control: CGPoint(x: width * 0.35, y: height * 0.32))
                .stroke(AppColors.accent, style: StrokeStyle(lineWidth: 4, lineCap: .round))

            path(from: nodes[1], to: nodes[2], control: CGPoint(x: width * 0.65, y: height * 0.32))
                .trim(from: 0, to: animateBall ? 1 : 0.20)
                .stroke(focus.status == .needsWork ? Color.orange : AppColors.accent, style: StrokeStyle(lineWidth: 5, lineCap: .round, dash: focus.status == .needsWork ? [7, 6] : []))

            ForEach(Array(nodes.enumerated()), id: \.offset) { index, point in
                VStack(spacing: 7) {
                    Circle()
                        .fill(index == 2 && animateBall ? AppColors.accent : AppColors.textPrimary)
                        .frame(width: 17, height: 17)
                    Text(labels[index])
                        .font(AppTypography.captionMedium)
                        .foregroundStyle(AppColors.textPrimary)
                }
                .position(point)
            }

            label(focus.status == .needsWork ? "中间断点" : "链路连贯", at: CGPoint(x: width * 0.62, y: height * 0.24), color: focus.status == .needsWork ? Color.orange : AppColors.accent)
        }
    }

    private func shotTargetSimulation(width: CGFloat, height: CGFloat) -> some View {
        let start = CGPoint(x: width * 0.18, y: height * 0.70)
        let target = CGPoint(x: width * 0.80, y: height * 0.34)

        return ZStack {
            goalFrame(width: width * 0.24, height: height * 0.46)
                .position(x: width * 0.80, y: height * 0.40)

            RoundedRectangle(cornerRadius: 5, style: .continuous)
                .fill(AppColors.accent.opacity(0.22))
                .frame(width: width * 0.10, height: height * 0.16)
                .position(target)

            path(from: start, to: target, control: CGPoint(x: width * 0.50, y: height * 0.22))
                .trim(from: 0, to: animateBall ? 1 : 0.12)
                .stroke(AppColors.accent, style: StrokeStyle(lineWidth: 5, lineCap: .round))

            ball(at: animateBall ? target : start)
            label("先选目标区", at: CGPoint(x: width * 0.40, y: height * 0.24), color: AppColors.accent)
        }
    }

    private func shotPowerSimulation(width: CGFloat, height: CGFloat) -> some View {
        let hip = CGPoint(x: width * 0.28, y: height * 0.48)
        let knee = CGPoint(x: width * 0.45, y: height * 0.58)
        let foot = CGPoint(x: width * 0.62, y: height * 0.48)
        let ballPoint = CGPoint(x: width * 0.78, y: height * 0.42)

        return ZStack {
            Path { path in
                path.move(to: hip)
                path.addLine(to: knee)
                path.addLine(to: foot)
                path.addLine(to: ballPoint)
            }
            .trim(from: 0, to: animateBall ? 1 : 0.25)
            .stroke(AppColors.accent, style: StrokeStyle(lineWidth: 6, lineCap: .round, lineJoin: .round))

            ball(at: ballPoint)
            label("髋部", at: CGPoint(x: hip.x, y: hip.y - 28), color: AppColors.textPrimary)
            label("大腿", at: CGPoint(x: knee.x, y: knee.y + 30), color: AppColors.textPrimary)
            label("小腿摆出", at: CGPoint(x: foot.x, y: foot.y - 30), color: AppColors.accent)
            label(focus.status == .needsWork ? "发力未串起" : "发力链稳定", at: CGPoint(x: width * 0.52, y: height * 0.22), color: focus.status == .needsWork ? Color.orange : AppColors.accent)
        }
    }

    private func supportSimulation(width: CGFloat, height: CGFloat) -> some View {
        let ballPoint = CGPoint(x: width * 0.56, y: height * 0.50)
        let idealSupport = CGPoint(x: width * 0.42, y: height * 0.66)
        let actualSupport = CGPoint(x: focus.status == .needsWork ? width * 0.32 : width * 0.43, y: focus.status == .needsWork ? height * 0.74 : height * 0.66)

        return ZStack {
            Path { path in
                path.move(to: CGPoint(x: width * 0.12, y: ballPoint.y))
                path.addLine(to: CGPoint(x: width * 0.88, y: ballPoint.y))
                path.move(to: CGPoint(x: ballPoint.x, y: height * 0.14))
                path.addLine(to: CGPoint(x: ballPoint.x, y: height * 0.86))
            }
            .stroke(AppColors.stroke.opacity(0.72), style: StrokeStyle(lineWidth: 1.2, lineCap: .round))

            Path { path in
                path.move(to: ballPoint)
                path.addLine(to: CGPoint(x: width * 0.82, y: height * 0.34))
            }
            .stroke(AppColors.textPrimary, style: StrokeStyle(lineWidth: 3.2, lineCap: .round))

            Circle()
                .fill(AppColors.textPrimary)
                .frame(width: 18, height: 18)
                .position(ballPoint)

            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(AppColors.accent, style: StrokeStyle(lineWidth: 3, dash: [6, 5]))
                .frame(width: width * 0.18, height: height * 0.14)
                .position(idealSupport)

            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .fill((focus.status == .needsWork ? Color.orange : AppColors.accent).opacity(0.22))
                .frame(width: width * 0.18, height: height * 0.14)
                .position(actualSupport)

            ArrowShape()
                .stroke(AppColors.accent, style: StrokeStyle(lineWidth: 4, lineCap: .round, lineJoin: .round))
                .frame(width: width * 0.26, height: height * 0.18)
                .position(x: width * 0.70, y: height * 0.34)

            label("球", at: CGPoint(x: ballPoint.x, y: ballPoint.y - 26), color: AppColors.textPrimary)
            label("目标线", at: CGPoint(x: width * 0.77, y: height * 0.26), color: AppColors.textPrimary)
            label("支撑脚：球侧后方", at: CGPoint(x: idealSupport.x, y: idealSupport.y + 34), color: AppColors.accent)
            label(focus.status == .needsWork ? "本次落点偏离" : "支撑落点稳定", at: CGPoint(x: actualSupport.x, y: actualSupport.y - 32), color: focus.status == .needsWork ? Color.orange : AppColors.accent)
        }
    }

    private func path(from start: CGPoint, to end: CGPoint, control: CGPoint) -> Path {
        Path { path in
            path.move(to: start)
            path.addQuadCurve(to: end, control: control)
        }
    }

    private func ball(at point: CGPoint) -> some View {
        Circle()
            .fill(AppColors.textPrimary)
            .frame(width: 14, height: 14)
            .overlay(Circle().stroke(AppColors.background, lineWidth: 2))
            .position(point)
    }

    private func label(_ text: String, at point: CGPoint, color: Color) -> some View {
        Text(text)
            .font(AppTypography.captionMedium)
            .foregroundStyle(color)
            .padding(.horizontal, 9)
            .padding(.vertical, 5)
            .background(AppColors.background.opacity(0.86))
            .clipShape(Capsule())
            .position(point)
    }

    private func goalFrame(width: CGFloat, height: CGFloat) -> some View {
        ZStack {
            RoundedRectangle(cornerRadius: 5, style: .continuous)
                .stroke(AppColors.textPrimary.opacity(0.42), lineWidth: 2)

            Path { path in
                path.move(to: CGPoint(x: width * 0.50, y: 0))
                path.addLine(to: CGPoint(x: width * 0.50, y: height))
                path.move(to: CGPoint(x: 0, y: height * 0.50))
                path.addLine(to: CGPoint(x: width, y: height * 0.50))
            }
            .stroke(AppColors.textPrimary.opacity(0.24), lineWidth: 1)
        }
        .frame(width: width, height: height)
    }

    private var fieldLines: some View {
        GeometryReader { proxy in
            let width = proxy.size.width
            let height = proxy.size.height

            Path { path in
                path.move(to: CGPoint(x: width * 0.08, y: height * 0.76))
                path.addLine(to: CGPoint(x: width * 0.92, y: height * 0.76))
                path.move(to: CGPoint(x: width * 0.50, y: height * 0.12))
                path.addLine(to: CGPoint(x: width * 0.50, y: height * 0.90))
            }
            .stroke(AppColors.stroke.opacity(0.7), lineWidth: 1)
        }
        .allowsHitTesting(false)
    }
}

private struct ArrowShape: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        path.move(to: CGPoint(x: rect.minX, y: rect.maxY))
        path.addQuadCurve(
            to: CGPoint(x: rect.maxX * 0.86, y: rect.minY + rect.height * 0.28),
            control: CGPoint(x: rect.midX, y: rect.minY + rect.height * 0.12)
        )
        path.move(to: CGPoint(x: rect.maxX * 0.86, y: rect.minY + rect.height * 0.28))
        path.addLine(to: CGPoint(x: rect.maxX * 0.64, y: rect.minY + rect.height * 0.22))
        path.move(to: CGPoint(x: rect.maxX * 0.86, y: rect.minY + rect.height * 0.28))
        path.addLine(to: CGPoint(x: rect.maxX * 0.78, y: rect.minY + rect.height * 0.48))
        return path
    }
}

private struct TrainingFeedbackKeyframeFrameOverlay: View {
    let spec: TrainingFeedbackKeyframeSpec
    let selectedAnnotationID: String?
    let onSelectAnnotation: ((TrainingFeedbackFrameAnnotation) -> Void)?

    init(
        spec: TrainingFeedbackKeyframeSpec,
        selectedAnnotationID: String? = nil,
        onSelectAnnotation: ((TrainingFeedbackFrameAnnotation) -> Void)? = nil
    ) {
        self.spec = spec
        self.selectedAnnotationID = selectedAnnotationID
        self.onSelectAnnotation = onSelectAnnotation
    }

    var body: some View {
        GeometryReader { geometry in
            ZStack {
                ForEach(spec.visibleAnnotations, id: \.id) { annotation in
                    let isPrimary = annotation.id == spec.primaryVisibleAnnotation?.id
                    let isSelected = selectedAnnotationID == annotation.id

                    Group {
                        if let onSelectAnnotation {
                            Button {
                                onSelectAnnotation(annotation)
                            } label: {
                                markerView(
                                    for: annotation,
                                    isPrimary: isPrimary,
                                    isSelected: isSelected
                                )
                            }
                            .buttonStyle(.plain)
                        } else {
                            markerView(
                                for: annotation,
                                isPrimary: isPrimary,
                                isSelected: isSelected
                            )
                        }
                    }
                    .position(
                        x: geometry.size.width * annotation.x,
                        y: geometry.size.height * annotation.y
                    )
                }
            }
        }
    }

    private func markerView(
        for annotation: TrainingFeedbackFrameAnnotation,
        isPrimary: Bool,
        isSelected: Bool
    ) -> some View {
        let color = markerColor(for: annotation)
        let displayColor = isSelected ? AppColors.accent : color

        return Group {
            if annotation.kind.isArrow {
                VStack(spacing: 4) {
                    HStack(spacing: 4) {
                        Capsule(style: .continuous)
                            .fill(displayColor.opacity(isPrimary ? 0.28 : 0.18))
                            .frame(width: isPrimary ? 18 : 14, height: 2)

                        Image(systemName: "arrow.up.right")
                            .font(.system(size: isPrimary ? 13 : 11, weight: .semibold))
                            .foregroundStyle(displayColor.opacity(isPrimary ? 0.95 : 0.82))
                            .rotationEffect(.degrees(annotation.angle))
                    }
                    .padding(.horizontal, 7)
                    .padding(.vertical, 5)
                    .background(displayColor.opacity(0.14))
                    .overlay(
                        Capsule(style: .continuous)
                            .stroke(displayColor.opacity(isPrimary ? 0.52 : 0.38), lineWidth: isSelected ? 1.4 : 1)
                    )
                    .clipShape(Capsule())

                    markerLabel(annotation.kind.visualLabel)
                }
            } else {
                HStack(spacing: 5) {
                    Image(systemName: "scope")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundStyle(displayColor)

                    Text(annotation.kind.displayLabel)
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundStyle(AppColors.textPrimary)
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 5)
                .background(.ultraThinMaterial)
                .overlay(
                    Capsule(style: .continuous)
                        .stroke(displayColor.opacity(isSelected ? 0.72 : 0.38), lineWidth: isSelected ? 1.4 : 1)
                )
                .clipShape(Capsule())
            }
        }
    }

    private func markerLabel(_ text: String) -> some View {
        Text(text)
            .font(.system(size: 10, weight: .semibold))
            .foregroundStyle(Color.white.opacity(0.92))
            .padding(.horizontal, 6)
            .padding(.vertical, 3)
            .background(Color.black.opacity(0.42))
            .clipShape(Capsule())
    }

    private func regionSize(
        for annotation: TrainingFeedbackFrameAnnotation,
        isPrimary: Bool,
        isSelected: Bool
    ) -> CGFloat {
        let base = CGFloat(max(34, min(64, annotation.radius * 260)))
        let primaryScale: CGFloat = isPrimary ? 1.08 : 1.0
        let selectedScale: CGFloat = isSelected ? 1.06 : 1.0
        return base * primaryScale * selectedScale
    }

    private func markerColor(for annotation: TrainingFeedbackFrameAnnotation) -> Color {
        switch spec.status {
        case .excellent:
            return AppColors.positive
        case .good:
            return annotation.kind.isArrow ? AppColors.warning : AppColors.positive
        case .needsWork:
            switch annotation.kind {
            case .ball, .supportFoot, .touchFoot:
                return AppColors.critical
            case .bodyDirection, .ballDirection:
                return AppColors.warning
            }
        case .reference:
            return AppColors.textTertiary
        }
    }
}

private struct TrainingFeedbackKeyframeDetailSheet: View {
    let spec: TrainingFeedbackKeyframeSpec
    let image: UIImage?
    let isLoading: Bool
    let onJumpToTime: () -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var selectedAnnotationID: String

    init(
        spec: TrainingFeedbackKeyframeSpec,
        image: UIImage?,
        isLoading: Bool,
        onJumpToTime: @escaping () -> Void
    ) {
        self.spec = spec
        self.image = image
        self.isLoading = isLoading
        self.onJumpToTime = onJumpToTime
        _selectedAnnotationID = State(
            initialValue: spec.visibleAnnotations.first?.id ?? ""
        )
    }

    private var selectedAnnotation: TrainingFeedbackFrameAnnotation? {
        spec.visibleAnnotations.first(where: { $0.id == selectedAnnotationID })
            ?? spec.visibleAnnotations.first
    }

    var body: some View {
        NavigationStack {
            content
            .background(AppColors.background)
            .navigationTitle(spec.title)
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    private var content: some View {
        ScrollView(.vertical, showsIndicators: false) {
            scrollContent
        }
    }

    @ViewBuilder
    private var scrollContent: some View {
        VStack(alignment: .leading, spacing: 16) {
            headerBlock
            headerActions

            frameSection

            annotationNoteCard

            keyframeDetailLegend

            detailSections
        }
        .padding(.horizontal, AppSpacing.screenPadding)
        .padding(.top, 12)
        .padding(.bottom, 24)
    }

    private var frameSection: some View {
        let visibleAnnotations = spec.visibleAnnotations
        let selectedID = selectedAnnotationID.nonEmpty
        let onSelectAnnotation: ((TrainingFeedbackFrameAnnotation) -> Void)?
        if visibleAnnotations.isEmpty {
            onSelectAnnotation = nil
        } else {
            onSelectAnnotation = selectAnnotation
        }

        return TrainingFeedbackKeyframeFrameSurface(
            spec: spec,
            image: image,
            isLoading: isLoading,
            height: 260,
            selectedAnnotationID: selectedID,
            onSelectAnnotation: onSelectAnnotation
        )
    }

    @ViewBuilder
    private var annotationNoteCard: some View {
        if spec.visibleAnnotations.isEmpty {
            TrainingFeedbackMiniCard {
                VStack(alignment: .leading, spacing: 6) {
                    Text(spec.confidence.displayLabel)
                        .font(AppTypography.captionMedium)
                        .foregroundStyle(AppColors.textSecondary)

                    Text(spec.confidenceNote)
                        .font(AppTypography.body)
                        .foregroundStyle(AppColors.textPrimary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        } else {
            TrainingFeedbackMiniCard {
                VStack(alignment: .leading, spacing: 6) {
                    Text("点开标记看说明")
                        .font(AppTypography.captionMedium)
                        .foregroundStyle(AppColors.textSecondary)

                    Text(selectedAnnotation?.note ?? spec.confidenceNote)
                        .font(AppTypography.body)
                        .foregroundStyle(AppColors.textPrimary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }

    private var detailSections: some View {
        VStack(alignment: .leading, spacing: 12) {
            detailBlock(label: "本帧结论", value: spec.conclusion)
            detailBlock(label: mainPointLabel, value: spec.mainPoint)
            detailBlock(label: "为什么重要", value: spec.whyImportant)
            detailBlock(label: "怎么改", value: spec.howToChange)
        }
    }

    private var headerBlock: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top, spacing: 10) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(spec.title)
                        .font(AppTypography.cardTitle)
                        .foregroundStyle(AppColors.textPrimary)

                    Text(spec.conclusion)
                        .font(AppTypography.bodyMedium)
                        .foregroundStyle(AppColors.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                Spacer(minLength: 0)

                VStack(alignment: .trailing, spacing: 6) {
                    TrainingFeedbackTag(text: spec.status.displayLabel)
                    TrainingFeedbackTag(text: spec.confidence.displayLabel)
                    Text(String(format: "%.1fs", spec.time))
                        .font(AppTypography.captionMedium)
                        .foregroundStyle(AppColors.textSecondary)
                }
            }

            Text(spec.confidenceNote)
                .font(AppTypography.caption)
                .foregroundStyle(AppColors.textSecondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private func selectAnnotation(_ annotation: TrainingFeedbackFrameAnnotation) {
        Haptics.light()
        selectedAnnotationID = annotation.id
    }

    private var headerActions: some View {
        VStack(spacing: 10) {
            SecondaryButton(
                title: "关闭",
                systemImage: "xmark",
                action: { dismiss() }
            )

            PrimaryButton(
                title: "跳到这一帧",
                systemImage: "arrow.right.circle.fill",
                action: jumpToFrame
            )
        }
    }

    private func jumpToFrame() {
        Haptics.medium()
        onJumpToTime()
    }

    private func detailBlock(label: String, value: String) -> some View {
        TrainingFeedbackMiniCard {
            VStack(alignment: .leading, spacing: 6) {
                Text(label)
                    .font(AppTypography.captionMedium)
                    .foregroundStyle(AppColors.textSecondary)

                Text(value)
                    .font(AppTypography.body)
                    .foregroundStyle(AppColors.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var mainPointLabel: String {
        if spec.status == .reference {
            return "参考点"
        }

        return spec.status.isPositive ? "主亮点" : "主问题"
    }

    private var keyframeDetailLegend: some View {
        TrainingFeedbackMiniCard {
            VStack(alignment: .leading, spacing: 10) {
                Text("视觉标记说明")
                    .font(AppTypography.captionMedium)
                    .foregroundStyle(AppColors.textSecondary)

                Text("区域 = 关注范围，不是像素级点位；箭头 = 方向趋势，不代表绝对角度。")
                    .font(AppTypography.body)
                    .foregroundStyle(AppColors.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)

                Text(spec.confidence.needsCautionBanner ? spec.confidenceNote : "当前这帧的区域判断相对更稳，但仍然建议结合整段视频看。")
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)

                HStack(spacing: 10) {
                    legendPill(color: AppColors.positive, text: "做得对")
                    legendPill(color: AppColors.warning, text: "需注意")
                    legendPill(color: AppColors.critical, text: "明显问题")
                }
            }
        }
    }

    private func legendPill(color: Color, text: String) -> some View {
        HStack(spacing: 6) {
            Circle()
                .fill(color)
                .frame(width: 8, height: 8)
            Text(text)
        }
        .font(AppTypography.captionMedium)
        .foregroundStyle(AppColors.textSecondary)
    }
}

@MainActor
final class TrainingFeedbackVideoPlaybackController: ObservableObject {
    let player: AVPlayer
    let hasVideo: Bool

    @Published var currentTime: Double = 0
    @Published var isPlaying = false

    private var timeObserver: Any?
    private var endObserver: NSObjectProtocol?
    private let duration: Double

    init(videoURL: URL?, duration: Double) {
        self.player = videoURL.map { AVPlayer(url: $0) } ?? AVPlayer()
        self.hasVideo = videoURL != nil
        self.duration = max(duration, 0.1)
        if hasVideo {
            observe()
        }
    }

    deinit {
        if let timeObserver {
            player.removeTimeObserver(timeObserver)
        }

        if let endObserver {
            NotificationCenter.default.removeObserver(endObserver)
        }
    }

    func togglePlayPause() {
        guard hasVideo else { return }

        if isPlaying {
            player.pause()
            isPlaying = false
            return
        }

        if currentTime >= duration - 0.05 {
            seek(to: 0)
        }

        player.play()
        isPlaying = true
    }

    func seek(to time: Double) {
        let clamped = min(max(time, 0), duration)
        guard hasVideo else {
            currentTime = clamped
            return
        }

        let cmTime = CMTime(seconds: clamped, preferredTimescale: 600)
        player.seek(to: cmTime, toleranceBefore: .zero, toleranceAfter: .zero)
        currentTime = clamped
    }

    private func observe() {
        let interval = CMTime(seconds: 0.1, preferredTimescale: 600)
        timeObserver = player.addPeriodicTimeObserver(forInterval: interval, queue: .main) { [weak self] time in
            let currentTime = time.seconds
            DispatchQueue.main.async { [weak self] in
                self?.currentTime = currentTime
            }
        }

        let duration = self.duration
        endObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemDidPlayToEndTime,
            object: player.currentItem,
            queue: .main
        ) { [weak self] _ in
            DispatchQueue.main.async { [weak self] in
                self?.isPlaying = false
                self?.currentTime = duration
            }
        }
    }
}

@MainActor
final class TrainingFeedbackFrameLoader: ObservableObject {
    @Published private(set) var images: [String: UIImage] = [:]
    @Published private(set) var isLoading = true

    private let videoURL: URL?
    private let keyframes: [TrainingFeedbackKeyframeSpec]

    init(videoURL: URL?, keyframes: [TrainingFeedbackKeyframeSpec]) {
        self.videoURL = videoURL
        self.keyframes = keyframes

        Task {
            await loadFrames()
        }
    }

    func image(for specID: String) -> UIImage? {
        images[specID]
    }

    private func loadFrames() async {
        guard let videoURL, !keyframes.isEmpty else {
            isLoading = false
            return
        }

        let loaded = await Task.detached(priority: .userInitiated) { [videoURL, keyframes] in
            let asset = AVAsset(url: videoURL)
            let generator = AVAssetImageGenerator(asset: asset)
            generator.appliesPreferredTrackTransform = true
            generator.maximumSize = CGSize(width: 1080, height: 1080)
            generator.requestedTimeToleranceBefore = .zero
            generator.requestedTimeToleranceAfter = .zero

            var imageMap: [String: UIImage] = [:]

            for spec in keyframes {
                let time = CMTime(seconds: spec.time, preferredTimescale: 600)
                if let cgImage = try? generator.copyCGImage(at: time, actualTime: nil) {
                    imageMap[spec.id] = UIImage(cgImage: cgImage)
                }
            }

            return imageMap
        }.value

        images = loaded
        isLoading = false
    }
}
