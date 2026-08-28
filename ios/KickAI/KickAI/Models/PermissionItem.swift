import Foundation

struct PermissionItem: Identifiable, Hashable {
    let id: UUID
    let iconName: String
    let title: String
    let detail: String

    init(id: UUID = UUID(), iconName: String, title: String, detail: String) {
        self.id = id
        self.iconName = iconName
        self.title = title
        self.detail = detail
    }
}
