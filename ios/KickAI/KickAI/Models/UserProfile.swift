import Foundation

enum MembershipTier: String, Codable {
    case free = "基础版"
    case pro = "专业版"
}

struct UserProfile: Identifiable, Codable {
    let id: UUID
    var name: String
    var email: String
    var avatarSymbolName: String
    var tier: MembershipTier
}
