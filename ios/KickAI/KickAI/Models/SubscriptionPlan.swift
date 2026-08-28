import Foundation

struct SubscriptionPlan: Identifiable, Hashable {
    let id: String
    let title: String
    let price: String
    let note: String
    let description: String
    let badge: String?
}
