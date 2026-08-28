import SwiftUI
#if canImport(UIKit)
import UIKit
#endif

enum AppColors {
    static let background = Color(uiColor: UIColor.kickAdaptive(light: .systemBackground, darkHex: 0x0B111A))
    static let backgroundElevated = Color(uiColor: UIColor.kickAdaptive(light: .secondarySystemBackground, darkHex: 0x111827))
    static let backgroundSoft = Color(uiColor: UIColor.kickAdaptive(light: .tertiarySystemBackground, darkHex: 0x182133))
    static let card = Color(uiColor: UIColor.kickAdaptive(light: .secondarySystemBackground, darkHex: 0x111827))
    static let cardSecondary = Color(uiColor: UIColor.kickAdaptive(light: .tertiarySystemBackground, darkHex: 0x182133))
    static let stroke = Color(uiColor: UIColor.kickAdaptive(light: UIColor.separator.withAlphaComponent(0.22), darkHex: 0x334155, darkAlpha: 0.82))
    static let strongStroke = Color(uiColor: UIColor.kickAdaptive(light: UIColor.separator.withAlphaComponent(0.42), darkHex: 0x475569, darkAlpha: 0.94))
    static let textPrimary = Color(uiColor: .label)
    static let textSecondary = Color(uiColor: .secondaryLabel)
    static let textTertiary = Color(uiColor: .tertiaryLabel)
    static let accent = Color(uiColor: UIColor.kickAdaptive(lightHex: 0x1E2D46, darkHex: 0x7FA2E8))
    static let accentMuted = Color(uiColor: UIColor.kickAdaptive(lightHex: 0x516580, darkHex: 0x8EA7D6))
    static let onAccent = Color(uiColor: UIColor.kickAdaptive(light: .white, darkHex: 0x08101C))
    static let positive = Color(hex: 0x84D0B6)
    static let warning = Color(hex: 0xE1B46E)
    static let critical = Color(hex: 0xE07E7B)
    static let reference = Color(hex: 0x87A0C6)
    static let pitchGreen = Color(hex: 0x3FAE7A)
    static let matchBlue = Color(hex: 0x2F6BFF)
    static let energyGold = Color(hex: 0xF0B85A)
    static let recoveryMint = Color(hex: 0x7FD8C6)
    static let overlay = Color.black.opacity(0.48)
}

extension Color {
    init(hex: UInt, opacity: Double = 1) {
        let red = Double((hex >> 16) & 0xFF) / 255
        let green = Double((hex >> 8) & 0xFF) / 255
        let blue = Double(hex & 0xFF) / 255
        self.init(.sRGB, red: red, green: green, blue: blue, opacity: opacity)
    }
}

#if canImport(UIKit)
private extension UIColor {
    convenience init(kickHex: UInt, alpha: CGFloat = 1) {
        let red = CGFloat((kickHex >> 16) & 0xFF) / 255
        let green = CGFloat((kickHex >> 8) & 0xFF) / 255
        let blue = CGFloat(kickHex & 0xFF) / 255
        self.init(red: red, green: green, blue: blue, alpha: alpha)
    }

    static func kickAdaptive(
        light: UIColor,
        darkHex: UInt,
        darkAlpha: CGFloat = 1
    ) -> UIColor {
        UIColor { traits in
            if traits.userInterfaceStyle == .dark {
                return UIColor(kickHex: darkHex, alpha: darkAlpha)
            }
            return light
        }
    }

    static func kickAdaptive(
        lightHex: UInt,
        darkHex: UInt,
        lightAlpha: CGFloat = 1,
        darkAlpha: CGFloat = 1
    ) -> UIColor {
        UIColor { traits in
            if traits.userInterfaceStyle == .dark {
                return UIColor(kickHex: darkHex, alpha: darkAlpha)
            }
            return UIColor(kickHex: lightHex, alpha: lightAlpha)
        }
    }
}
#endif
