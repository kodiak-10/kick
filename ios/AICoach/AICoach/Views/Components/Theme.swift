import SwiftUI

enum AppTheme {
    static let background = LinearGradient(
        colors: [
            Color(red: 0.03, green: 0.06, blue: 0.14),
            Color(red: 0.02, green: 0.03, blue: 0.08),
            Color(red: 0.00, green: 0.01, blue: 0.04)
        ],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    static let cardFill = Color.white.opacity(0.08)
    static let cardStrong = Color.white.opacity(0.12)
    static let cardStroke = Color.white.opacity(0.12)
    static let accent = Color(red: 0.22, green: 0.82, blue: 0.97)
    static let success = Color(red: 0.37, green: 0.90, blue: 0.58)
    static let warning = Color(red: 1.00, green: 0.60, blue: 0.19)
    static let caution = Color(red: 0.98, green: 0.78, blue: 0.24)
    static let danger = Color(red: 1.00, green: 0.35, blue: 0.40)
    static let muted = Color.white.opacity(0.62)
    static let text = Color.white

    static func resultColor(for level: ResultLevel) -> Color {
        switch level {
        case .excellent:
            return success
        case .good:
            return accent
        case .fair:
            return warning
        case .needsImprove:
            return caution
        case .needsStrengthen:
            return danger
        case .pendingConfirmation:
            return warning
        }
    }

    static func thumbnailGradient(for style: ThumbnailStyle) -> LinearGradient {
        switch style {
        case .stadiumBlue:
            return LinearGradient(
                colors: [Color(red: 0.10, green: 0.23, blue: 0.50), Color(red: 0.13, green: 0.71, blue: 0.96)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        case .trainingGreen:
            return LinearGradient(
                colors: [Color(red: 0.08, green: 0.29, blue: 0.19), Color(red: 0.38, green: 0.90, blue: 0.58)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        case .sunsetOrange:
            return LinearGradient(
                colors: [Color(red: 0.72, green: 0.27, blue: 0.14), Color(red: 1.00, green: 0.58, blue: 0.18)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        }
    }
}
