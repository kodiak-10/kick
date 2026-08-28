import Foundation

struct OnboardingPage: Identifiable, Hashable {
    let id: UUID
    let iconName: String
    let title: String
    let subtitle: String

    init(id: UUID = UUID(), iconName: String, title: String, subtitle: String) {
        self.id = id
        self.iconName = iconName
        self.title = title
        self.subtitle = subtitle
    }
}
