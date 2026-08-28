import Combine
import Foundation

@MainActor
final class SubscriptionManager: ObservableObject {
    @Published var plans: [SubscriptionPlan] = AppMockData.subscriptionPlans
    @Published var selectedPlanID: String = AppMockData.subscriptionPlans.last?.id ?? "yearly"

    var selectedPlan: SubscriptionPlan? {
        plans.first(where: { $0.id == selectedPlanID })
    }

    func select(_ plan: SubscriptionPlan) {
        selectedPlanID = plan.id
    }
}
