import Combine
import Foundation

#if canImport(UIKit)
import UIKit
#endif

@MainActor
final class SessionManager: ObservableObject {
    enum RootStep {
        case splash
        case onboarding
        case auth
        case permission
        case main
    }

    private enum StorageKey {
        static let sessionState = "kickai.session.state.v1"
    }

    private struct PersistedSessionState: Codable {
        var hasSeenSplash: Bool
        var hasCompletedOnboarding: Bool
        var isAuthenticated: Bool
        var hasCompletedPermissionIntro: Bool
        var hasProAccess: Bool
        var remainingFreeAnalyses: Int
        var remainingFreeProAnalyses: Int?
        var userProfile: UserProfile
        var historyItems: [HistoryItem]
        var lastLoginMethod: String?
    }

    @Published private(set) var hasSeenSplash = false
    @Published private(set) var hasCompletedOnboarding = false
    @Published private(set) var isAuthenticated = false
    @Published private(set) var hasCompletedPermissionIntro = false
    @Published private(set) var hasProAccess = false
    @Published private(set) var remainingFreeAnalyses = 3
    @Published private(set) var remainingFreeProAnalyses = 2
    @Published var selectedTab: AppTab = .home
    @Published var homeNavigationResetID = UUID()
    @Published var analysisNavigationResetID = UUID()
    @Published var historyNavigationResetID = UUID()
    @Published private(set) var userProfile: UserProfile = AppMockData.userProfile
    @Published private(set) var latestResult: AnalysisResult = AppMockData.latestAnalysis
    @Published private(set) var historyItems: [HistoryItem] = AppMockData.historyItems
    @Published var currentUploadSource: VideoSource?
    @Published private(set) var lastLoginMethod: String?

    init() {
        if let snapshot = Self.loadPersistedState() {
            apply(snapshot)
        } else {
            historyItems = AppMockData.historyItems
            latestResult = AppMockData.latestAnalysis
        }
    }

    var currentRoot: RootStep {
        if !hasSeenSplash {
            return .splash
        }
        if !hasCompletedOnboarding {
            return .onboarding
        }
        if !isAuthenticated {
            return .auth
        }
        if !hasCompletedPermissionIntro {
            return .permission
        }
        return .main
    }

    var canStartAnalysis: Bool {
        hasProAccess || remainingFreeAnalyses > 0
    }

    var latestResultVideoURL: URL? {
        #if canImport(UIKit)
        latestHistoryItem?.videoURL
        #else
        nil
        #endif
    }

    var latestResultVideoLabel: String? {
        latestHistoryItem?.videoFileName
    }

    var latestResultHasProfessionalAccess: Bool {
        hasProfessionalAccess(for: latestResult.id)
    }

    var weeklyAnalysisCount: Int {
        let calendar = Calendar.current
        let weekAgo = calendar.date(byAdding: .day, value: -7, to: Date()) ?? Date()
        return historyItems.filter { $0.date >= weekAgo }.count
    }

    var weeklyAverageScore: Int {
        let calendar = Calendar.current
        let weekAgo = calendar.date(byAdding: .day, value: -7, to: Date()) ?? Date()
        let scores = historyItems.filter { $0.date >= weekAgo }.map(\.score)
        guard !scores.isEmpty else { return latestResult.score }
        return scores.reduce(0, +) / scores.count
    }

    var weeklyChange: Int {
        let calendar = Calendar.current
        let now = Date()
        let currentWeekStart = calendar.date(byAdding: .day, value: -7, to: now) ?? now
        let previousWeekStart = calendar.date(byAdding: .day, value: -14, to: now) ?? now

        let currentScores = historyItems.filter { $0.date >= currentWeekStart }.map(\.score)
        let previousScores = historyItems.filter { $0.date >= previousWeekStart && $0.date < currentWeekStart }.map(\.score)

        let currentAverage = currentScores.isEmpty ? latestResult.score : currentScores.reduce(0, +) / currentScores.count
        let previousAverage = previousScores.isEmpty ? max(currentAverage - 6, 0) : previousScores.reduce(0, +) / previousScores.count

        return currentAverage - previousAverage
    }

    func completeSplash() {
        hasSeenSplash = true
        persistSessionState()
    }

    func completeOnboarding() {
        hasCompletedOnboarding = true
        persistSessionState()
    }

    func signIn(with method: String) {
        lastLoginMethod = method
        isAuthenticated = true
        persistSessionState()
    }

    func completePermissionIntro() {
        hasCompletedPermissionIntro = true
        persistSessionState()
    }

    func selectVideoSource(_ source: VideoSource) {
        currentUploadSource = source
    }

    func prepareForAnalysis() {
        guard canStartAnalysis else { return }
        if !hasProAccess {
            remainingFreeAnalyses = max(remainingFreeAnalyses - 1, 0)
        }
        persistSessionState()
    }

    func recordAnalysis(
        response: VideoAnalysisResponse,
        video: ImportedVideo?,
        selectedAction: AnalysisActionChoice? = nil
    ) {
        let professionalAccessGranted = hasProAccess || remainingFreeProAnalyses > 0
        let feedbackViewModel = TrainingFeedbackViewModel(
            response: response,
            selectedAction: selectedAction,
            videoDuration: video?.durationSeconds
        )

        let thumbnailData = video?.thumbnailImage?.jpegData(compressionQuality: 0.82)
        let videoFileName = copyVideoIntoHistoryStorage(video?.url)
        let result = feedbackViewModel.makeHistoryResult(date: Date())
        latestResult = result

        let item = HistoryItem(
            result: result,
            thumbnailData: thumbnailData,
            videoFileName: videoFileName,
            professionalAccessGranted: professionalAccessGranted
        )

        if historyItems == AppMockData.historyItems {
            historyItems = [item]
        } else {
            historyItems.insert(item, at: 0)
        }
        Haptics.success()
        currentUploadSource = nil
        if !hasProAccess && remainingFreeProAnalyses > 0 {
            remainingFreeProAnalyses = max(remainingFreeProAnalyses - 1, 0)
        }
        persistSessionState()
    }

    func finishProcessing() {
        let nextResult = AppMockData.makeAnalysisResult(index: historyItems.count + 1)
        latestResult = nextResult
        let professionalAccessGranted = hasProAccess || remainingFreeProAnalyses > 0
        let item = HistoryItem(
            result: nextResult,
            professionalAccessGranted: professionalAccessGranted
        )
        if historyItems == AppMockData.historyItems {
            historyItems = [item]
        } else {
            historyItems.insert(item, at: 0)
        }
        Haptics.success()
        currentUploadSource = nil
        if !hasProAccess && remainingFreeProAnalyses > 0 {
            remainingFreeProAnalyses = max(remainingFreeProAnalyses - 1, 0)
        }
        persistSessionState()
        selectedTab = .home
    }

    func toggleFavorite(for itemID: UUID) {
        guard let index = historyItems.firstIndex(where: { $0.id == itemID }) else {
            return
        }

        historyItems[index].isFavorite.toggle()
        persistSessionState()
    }

    func deleteHistoryItem(id: UUID) {
        guard let index = historyItems.firstIndex(where: { $0.id == id }) else {
            return
        }

        let removedLatest = historyItems[index].result.id == latestResult.id
        deleteStoredVideo(named: historyItems[index].videoFileName)
        historyItems.remove(at: index)

        if removedLatest {
            latestResult = historyItems.first?.result ?? AppMockData.latestAnalysis
        }

        persistSessionState()
    }

    func updateNote(for itemID: UUID, note: String?) {
        guard let index = historyItems.firstIndex(where: { $0.id == itemID }) else {
            return
        }

        let trimmedNote = note?.trimmingCharacters(in: .whitespacesAndNewlines)
        historyItems[index].note = trimmedNote?.nonEmpty
        persistSessionState()
    }

    func resetHomeNavigation() {
        selectedTab = .home
        homeNavigationResetID = UUID()
    }

    func resetAnalysisNavigation() {
        selectedTab = .analysis
        analysisNavigationResetID = UUID()
    }

    func resetHistoryNavigation() {
        selectedTab = .history
        historyNavigationResetID = UUID()
    }

    func unlockPro() {
        hasProAccess = true
        remainingFreeProAnalyses = 0
        userProfile.tier = .pro
        persistSessionState()
    }

    func restorePurchases() {
        unlockPro()
    }

    func hasProfessionalAccess(for resultID: UUID) -> Bool {
        if hasProAccess {
            return true
        }

        return historyItems.first(where: { $0.result.id == resultID })?.professionalAccessGranted == true
    }

    private func apply(_ snapshot: PersistedSessionState) {
        hasSeenSplash = snapshot.hasSeenSplash
        hasCompletedOnboarding = snapshot.hasCompletedOnboarding
        isAuthenticated = snapshot.isAuthenticated
        hasCompletedPermissionIntro = snapshot.hasCompletedPermissionIntro
        hasProAccess = snapshot.hasProAccess || snapshot.userProfile.tier == .pro
        remainingFreeAnalyses = max(snapshot.remainingFreeAnalyses, 0)
        remainingFreeProAnalyses = max(snapshot.remainingFreeProAnalyses ?? 2, 0)
        userProfile = snapshot.userProfile
        if hasProAccess {
            userProfile.tier = .pro
            remainingFreeProAnalyses = 0
        }
        historyItems = snapshot.historyItems.sorted { lhs, rhs in
            lhs.date > rhs.date
        }
        latestResult = historyItems.first?.result ?? AppMockData.latestAnalysis
        lastLoginMethod = snapshot.lastLoginMethod
    }

    private func persistSessionState() {
        let snapshot = PersistedSessionState(
            hasSeenSplash: hasSeenSplash,
            hasCompletedOnboarding: hasCompletedOnboarding,
            isAuthenticated: isAuthenticated,
            hasCompletedPermissionIntro: hasCompletedPermissionIntro,
            hasProAccess: hasProAccess,
            remainingFreeAnalyses: remainingFreeAnalyses,
            remainingFreeProAnalyses: remainingFreeProAnalyses,
            userProfile: userProfile,
            historyItems: historyItems,
            lastLoginMethod: lastLoginMethod
        )

        guard let data = try? JSONEncoder().encode(snapshot) else {
            return
        }

        UserDefaults.standard.set(data, forKey: StorageKey.sessionState)
    }

    private func copyVideoIntoHistoryStorage(_ sourceURL: URL?) -> String? {
        guard let sourceURL else { return nil }
        guard FileManager.default.fileExists(atPath: sourceURL.path) else { return nil }

        let directory = HistoryItem.videoStorageDirectory
        do {
            try FileManager.default.createDirectory(
                at: directory,
                withIntermediateDirectories: true
            )

            let fileExtension = sourceURL.pathExtension.nonEmpty ?? "mp4"
            let fileName = "\(UUID().uuidString).\(fileExtension)"
            let destinationURL = directory.appendingPathComponent(fileName)

            if FileManager.default.fileExists(atPath: destinationURL.path) {
                try FileManager.default.removeItem(at: destinationURL)
            }

            try FileManager.default.copyItem(at: sourceURL, to: destinationURL)
            return fileName
        } catch {
            print("[Kick][HistoryVideo] failed_to_copy_video source=\(sourceURL.path) error=\(error.localizedDescription)")
            return nil
        }
    }

    private func deleteStoredVideo(named fileName: String?) {
        guard let fileName, !fileName.isEmpty else { return }
        let url = HistoryItem.videoStorageDirectory.appendingPathComponent(fileName)
        guard FileManager.default.fileExists(atPath: url.path) else { return }

        do {
            try FileManager.default.removeItem(at: url)
        } catch {
            print("[Kick][HistoryVideo] failed_to_delete_video file=\(fileName) error=\(error.localizedDescription)")
        }
    }

    private var latestHistoryItem: HistoryItem? {
        historyItems.first(where: { $0.result.id == latestResult.id }) ?? historyItems.first
    }

    private static func loadPersistedState() -> PersistedSessionState? {
        guard let data = UserDefaults.standard.data(forKey: StorageKey.sessionState) else {
            return nil
        }

        return try? JSONDecoder().decode(PersistedSessionState.self, from: data)
    }
}
