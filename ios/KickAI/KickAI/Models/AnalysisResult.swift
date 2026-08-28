import Foundation

struct AnalysisIssue: Identifiable, Hashable, Codable {
    let id: UUID
    let title: String
    let detail: String
    let severityLabel: String

    init(id: UUID = UUID(), title: String, detail: String, severityLabel: String) {
        self.id = id
        self.title = title
        self.detail = detail
        self.severityLabel = severityLabel
    }
}

struct AnalysisResult: Identifiable, Hashable, Codable {
    let id: UUID
    let date: Date
    let motionType: String
    let score: Int
    let summary: String
    let freeIssues: [AnalysisIssue]
    let videoReviewData: VideoReviewData
    let premiumInsights: [AppFeature]
    let trainingSuggestions: [String]
    let trendSummary: String

    init(
        id: UUID = UUID(),
        date: Date,
        motionType: String,
        score: Int,
        summary: String,
        freeIssues: [AnalysisIssue],
        videoReviewData: VideoReviewData,
        premiumInsights: [AppFeature],
        trainingSuggestions: [String],
        trendSummary: String
    ) {
        self.id = id
        self.date = date
        self.motionType = motionType
        self.score = score
        self.summary = summary
        self.freeIssues = freeIssues
        self.videoReviewData = videoReviewData
        self.premiumInsights = premiumInsights
        self.trainingSuggestions = trainingSuggestions
        self.trendSummary = trendSummary
    }
}
