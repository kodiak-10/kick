import SwiftUI

enum AppTypography {
    static let hero = Font.system(size: 42, weight: .bold, design: .rounded)
    static let pageTitle = Font.system(size: 30, weight: .bold, design: .rounded)
    static let sectionTitle = Font.system(size: 22, weight: .semibold, design: .rounded)
    static let cardTitle = Font.system(size: 18, weight: .semibold, design: .rounded)
    static let headline = Font.system(size: 17, weight: .semibold, design: .rounded)
    static let body = Font.system(size: 16, weight: .regular, design: .rounded)
    static let bodyMedium = Font.system(size: 15, weight: .medium, design: .rounded)
    static let caption = Font.system(size: 13, weight: .regular, design: .rounded)
    static let captionMedium = Font.system(size: 12, weight: .medium, design: .rounded)
    static let metric = Font.system(size: 34, weight: .bold, design: .rounded)
    static let monospacedMetric = Font.system(size: 28, weight: .bold, design: .rounded).monospacedDigit()
}
