import SwiftUI

struct FrostedCard<Content: View>: View {
    let padding: CGFloat
    @ViewBuilder let content: Content

    init(padding: CGFloat = 18, @ViewBuilder content: () -> Content) {
        self.padding = padding
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            content
        }
        .padding(padding)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .fill(AppTheme.cardFill)
                .overlay(
                    RoundedRectangle(cornerRadius: 24, style: .continuous)
                        .stroke(AppTheme.cardStroke, lineWidth: 1)
                )
        )
    }
}

struct PrimaryButton: View {
    let title: String
    let subtitle: String?
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 4) {
                Text(title)
                    .font(.headline)
                    .fontWeight(.semibold)
                if let subtitle {
                    Text(subtitle)
                        .font(.footnote)
                        .foregroundStyle(.white.opacity(0.82))
                }
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 16)
            .background(
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .fill(
                        LinearGradient(
                            colors: [AppTheme.accent, Color(red: 0.27, green: 0.56, blue: 1.00)],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
            )
            .foregroundStyle(.white)
        }
        .buttonStyle(.plain)
    }
}

struct SecondaryButton: View {
    let title: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.subheadline.weight(.semibold))
                .padding(.vertical, 12)
                .frame(maxWidth: .infinity)
                .background(
                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                        .fill(Color.white.opacity(0.06))
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                        .stroke(Color.white.opacity(0.10), lineWidth: 1)
                )
        }
        .buttonStyle(.plain)
        .foregroundStyle(.white)
    }
}

struct StatusPill: View {
    let text: String
    let tint: Color

    var body: some View {
        Text(text)
            .font(.caption.weight(.semibold))
            .lineLimit(1)
            .foregroundStyle(tint)
            .padding(.horizontal, 12)
            .padding(.vertical, 7)
            .background(
                Capsule()
                    .fill(tint.opacity(0.14))
            )
    }
}

struct ScoreRingView: View {
    let score: Int
    let level: ResultLevel
    let labelOverride: String?

    init(score: Int, level: ResultLevel, labelOverride: String? = nil) {
        self.score = score
        self.level = level
        self.labelOverride = labelOverride
    }

    var body: some View {
        ZStack {
            Circle()
                .stroke(Color.white.opacity(0.10), lineWidth: 14)
            Circle()
                .trim(from: 0, to: CGFloat(score) / 100.0)
                .stroke(
                    AppTheme.resultColor(for: level),
                    style: StrokeStyle(lineWidth: 14, lineCap: .round)
                )
                .rotationEffect(.degrees(-90))
            VStack(spacing: 4) {
                Text("\(score)")
                    .font(.system(size: 34, weight: .bold, design: .rounded))
                Text(labelOverride ?? level.title)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(AppTheme.resultColor(for: level))
            }
        }
        .frame(width: 110, height: 110)
    }
}

struct MetricBar: View {
    let title: String
    let value: Int
    let tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(title)
                    .font(.subheadline.weight(.medium))
                Spacer()
                Text("\(value)")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(tint)
            }
            GeometryReader { proxy in
                ZStack(alignment: .leading) {
                    Capsule()
                        .fill(Color.white.opacity(0.10))
                    Capsule()
                        .fill(tint)
                        .frame(width: proxy.size.width * CGFloat(value) / 100.0)
                }
            }
            .frame(height: 8)
        }
    }
}

struct SectionLabel: View {
    let title: String
    let subtitle: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.title3.weight(.semibold))
            if let subtitle {
                Text(subtitle)
                    .font(.subheadline)
                    .foregroundStyle(AppTheme.muted)
            }
        }
    }
}

struct LockedFeatureCard: View {
    let title: String
    let detail: String
    let action: () -> Void

    var body: some View {
        FrostedCard {
            HStack(alignment: .top, spacing: 14) {
                Image(systemName: "lock.fill")
                    .font(.headline)
                    .foregroundStyle(AppTheme.warning)
                    .frame(width: 34, height: 34)
                    .background(Circle().fill(AppTheme.warning.opacity(0.16)))
                VStack(alignment: .leading, spacing: 8) {
                    Text(title)
                        .font(.headline.weight(.semibold))
                    Text(detail)
                        .font(.subheadline)
                        .foregroundStyle(AppTheme.muted)
                    Button("升级到 Pro") {
                        action()
                    }
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(AppTheme.accent)
                }
            }
        }
    }
}

struct ThumbnailCard: View {
    let title: String
    let subtitle: String
    let style: ThumbnailStyle
    let isSelected: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(AppTheme.thumbnailGradient(for: style))
                .frame(height: 128)
                .overlay(
                    VStack(alignment: .leading, spacing: 8) {
                        Image(systemName: "figure.soccer")
                            .font(.title2)
                        Spacer()
                        Text(title)
                            .font(.headline.weight(.semibold))
                        Text(subtitle)
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.82))
                    }
                    .padding(16)
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
                )

            HStack {
                Text(title)
                    .font(.subheadline.weight(.semibold))
                Spacer()
                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(AppTheme.success)
                }
            }
        }
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 22, style: .continuous)
                .fill(isSelected ? AppTheme.cardStrong : AppTheme.cardFill)
                .overlay(
                    RoundedRectangle(cornerRadius: 22, style: .continuous)
                        .stroke(isSelected ? AppTheme.accent : AppTheme.cardStroke, lineWidth: 1)
                )
        )
    }
}

struct SystemStatusBar: View {
    let status: CameraSystemStatus

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: status.symbol)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(tint)
                .frame(width: 30, height: 30)
                .background(
                    Circle()
                        .fill(tint.opacity(0.16))
                )

            VStack(alignment: .leading, spacing: 2) {
                Text(status.title)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(AppTheme.text)
                Text(status.subtitle)
                    .font(.caption)
                    .foregroundStyle(AppTheme.muted)
                    .lineLimit(1)
            }

            Spacer(minLength: 12)

            StatusPill(text: status.rawValue, tint: tint)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(AppTheme.cardFill)
                .overlay(
                    RoundedRectangle(cornerRadius: 18, style: .continuous)
                        .stroke(AppTheme.cardStroke, lineWidth: 1)
                )
        )
    }

    private var tint: Color {
        switch status {
        case .ready:
            return AppTheme.success
        case .warning:
            return AppTheme.warning
        case .error:
            return AppTheme.danger
        }
    }
}

struct TrainingTemplateCard: View {
    let goal: TrainingGoal
    let isSelected: Bool

    var body: some View {
        FrostedCard(padding: 16) {
            HStack(alignment: .top, spacing: 14) {
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .fill(AppTheme.thumbnailGradient(for: goal.templateStyle))
                    .frame(width: 84, height: 108)
                    .overlay(
                        VStack(alignment: .leading, spacing: 6) {
                            Image(systemName: "figure.soccer")
                                .font(.headline)
                            Spacer()
                            Text(goal.displayTitle)
                                .font(.headline.weight(.semibold))
                            Text(goal.englishTitle)
                                .font(.caption2)
                                .foregroundStyle(.white.opacity(0.82))
                        }
                        .padding(12)
                        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
                    )

                VStack(alignment: .leading, spacing: 10) {
                    HStack(alignment: .top) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(goal.displayTitle)
                                .font(.title3.weight(.semibold))
                            Text(goal.englishTitle)
                                .font(.caption.weight(.medium))
                                .foregroundStyle(AppTheme.muted)
                        }
                        Spacer()
                        if isSelected {
                            StatusPill(text: "已选中", tint: AppTheme.success)
                        }
                    }

                    Text(goal.purpose)
                        .font(.subheadline)
                        .foregroundStyle(.white.opacity(0.92))
                        .lineLimit(2)

                    HStack(spacing: 8) {
                        ForEach(goal.coreMetrics.prefix(3), id: \.self) { metric in
                            StatusPill(text: metric, tint: AppTheme.accent)
                        }
                    }
                    .lineLimit(1)
                }
            }
        }
        .overlay(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .stroke(isSelected ? AppTheme.accent : AppTheme.cardStroke, lineWidth: isSelected ? 1.6 : 1)
        )
        .shadow(color: isSelected ? AppTheme.accent.opacity(0.14) : .clear, radius: 14, x: 0, y: 6)
    }
}

struct ResultSubscoreCard: View {
    let title: String
    let value: Int?
    let tint: Color
    let note: String
    let badgeText: String?

    var body: some View {
        FrostedCard(padding: 16) {
            VStack(alignment: .leading, spacing: 10) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(title)
                            .font(.subheadline.weight(.semibold))
                        Text(valueText)
                            .font(.system(size: value == nil ? 28 : 30, weight: .bold, design: .rounded))
                            .foregroundStyle(value == nil ? AppTheme.muted : tint)
                    }

                    Spacer()

                    if let badgeText {
                        StatusPill(text: badgeText, tint: tint)
                    }
                }

                Text(note)
                    .font(.caption)
                    .foregroundStyle(AppTheme.muted)
                    .lineLimit(2)

                if let value {
                    MetricBar(title: title, value: value, tint: tint)
                } else {
                    Capsule()
                        .fill(Color.white.opacity(0.08))
                        .frame(height: 8)
                        .overlay(
                            Capsule()
                                .stroke(Color.white.opacity(0.06), lineWidth: 1)
                        )
                }
            }
        }
    }

    private var valueText: String {
        if let value {
            return "\(value)"
        }
        return "—"
    }
}
