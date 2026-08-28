import Combine
import Foundation

@MainActor
final class PurchaseManager: ObservableObject {
    @Published var isPurchasing = false
    @Published var purchaseNotice: String?

    func purchaseSelectedPlan(subscriptionManager: SubscriptionManager, sessionManager: SessionManager) {
        guard let plan = subscriptionManager.selectedPlan, !isPurchasing else { return }
        isPurchasing = true
        purchaseNotice = nil

        Task {
            try? await Task.sleep(nanoseconds: 900_000_000)
            sessionManager.unlockPro()
            Haptics.success()
            purchaseNotice = "已开通\(plan.title)"
            isPurchasing = false
        }
    }

    func restore(sessionManager: SessionManager) {
        guard !isPurchasing else { return }
        isPurchasing = true
        purchaseNotice = nil

        Task {
            try? await Task.sleep(nanoseconds: 700_000_000)
            sessionManager.restorePurchases()
            Haptics.success()
            purchaseNotice = "已恢复专业版状态"
            isPurchasing = false
        }
    }
}
