import Foundation
import SwiftUI

enum MainTab: Hashable {
    case home
    case history
    case profile
}

enum PaywallSource: String, Hashable {
    case home
    case result
    case history
    case profile
    case quotaExhausted
}

enum AppRoute: Hashable {
    case upload
    case processing
    case result(UUID)
    case paywall(PaywallSource)
}

@MainActor
final class AppState: ObservableObject {
    private enum StorageKey {
        static let onboarding = "ai_coach_has_seen_onboarding"
    }

    @Published var path = NavigationPath()
    @Published var selectedTab: MainTab = .home
    @Published var selectedGoal: TrainingGoal = .shooting
    @Published var subscription: SubscriptionState = .free
    @Published var remainingFreeAnalyses = 2
    @Published var cameraStatus: CameraSystemStatus = .warning
    @Published var draft: UploadDraft?
    @Published var analysisHistory: [AnalysisRecord]
    @Published var hasSeenOnboarding: Bool

    init() {
        hasSeenOnboarding = UserDefaults.standard.bool(forKey: StorageKey.onboarding)
        analysisHistory = MockData.sampleHistory.sorted(by: { $0.createdAt > $1.createdAt })
    }

    var isPro: Bool {
        subscription.isPro
    }

    var canStartAnalysis: Bool {
        isPro || remainingFreeAnalyses > 0
    }

    var recentRecord: AnalysisRecord? {
        analysisHistory.first
    }

    var visibleHistory: [AnalysisRecord] {
        isPro ? analysisHistory : Array(analysisHistory.prefix(3))
    }

    var lockedHistoryCount: Int {
        max(0, analysisHistory.count - visibleHistory.count)
    }

    func completeOnboarding() {
        hasSeenOnboarding = true
        UserDefaults.standard.set(true, forKey: StorageKey.onboarding)
    }

    func resetOnboarding() {
        hasSeenOnboarding = false
        UserDefaults.standard.set(false, forKey: StorageKey.onboarding)
    }

    func resetDemoData() {
        subscription = .free
        remainingFreeAnalyses = 2
        selectedGoal = .shooting
        cameraStatus = .warning
        draft = nil
        analysisHistory = MockData.sampleHistory.sorted(by: { $0.createdAt > $1.createdAt })
        path = NavigationPath()
        selectedTab = .home
    }

    func startAnalysisFlow() {
        guard canStartAnalysis else {
            openPaywall(from: .quotaExhausted)
            return
        }

        path.append(AppRoute.upload)
    }

    func openPaywall(from source: PaywallSource) {
        path.append(AppRoute.paywall(source))
    }

    func dismissTopRoute() {
        guard path.count > 0 else { return }
        path.removeLast()
    }

    func dismissToHome() {
        path = NavigationPath()
        selectedTab = .home
    }

    func submitUpload(demoClip: DemoClip, goal: TrainingGoal) {
        selectedGoal = goal
        draft = UploadDraft(
            clipName: demoClip.title,
            durationSeconds: demoClip.durationSeconds,
            goal: goal,
            sourceLabel: "演示视频",
            demoClip: demoClip
        )
        path.append(AppRoute.processing)
    }

    func commitAnalysis(_ record: AnalysisRecord, preserveDraft: Bool = false, consumeQuota: Bool = true) {
        analysisHistory.insert(record, at: 0)
        if !preserveDraft {
            draft = nil
        }
        selectedGoal = record.goal
        if consumeQuota && !isPro && remainingFreeAnalyses > 0 {
            remainingFreeAnalyses -= 1
        }
        path = NavigationPath()
        path.append(AppRoute.result(record.id))
    }

    @discardableResult
    func finishProcessing() -> AnalysisRecord? {
        guard let draft else { return nil }

        let record = MockData.generateRecord(
            from: draft,
            existingCount: analysisHistory.count
        )
        commitAnalysis(record)

        return record
    }

    func retryCurrentAnalysis() {
        guard draft != nil else { return }
        path = NavigationPath()
        path.append(AppRoute.processing)
    }

    func reselectVideo() {
        path = NavigationPath()
        path.append(AppRoute.upload)
    }

    func record(for id: UUID) -> AnalysisRecord? {
        analysisHistory.first(where: { $0.id == id })
    }

    func showRecord(_ id: UUID) {
        path.append(AppRoute.result(id))
    }

    func visibleIssues(for record: AnalysisRecord) -> [AnalysisIssue] {
        isPro ? record.issues : Array(record.issues.prefix(1))
    }

    func visibleSuggestions(for record: AnalysisRecord) -> [TrainingSuggestion] {
        isPro ? record.suggestions : Array(record.suggestions.prefix(1))
    }

    func visibleInsights(for record: AnalysisRecord) -> [PremiumInsight] {
        isPro ? record.premiumInsights : []
    }

    func upgrade(to plan: ProPlan) {
        subscription = .pro(plan)
        dismissTopRoute()
    }

    func restorePurchases() {
        subscription = .pro(.monthly)
    }

    func switchToFree() {
        subscription = .free
    }

    func quotaText() -> String {
        isPro ? "Pro 无限制分析" : "本周剩余 \(remainingFreeAnalyses) 次免费分析"
    }
}
