import Foundation

struct HistoryMetricSnapshot: Identifiable, Hashable, Codable {
    let key: ResultMetricKey
    let title: String
    let valueText: String
    let status: TrainingFeedbackStatus

    var id: String { key.rawValue }
}

struct HistoryItem: Identifiable, Hashable, Codable {
    let id: UUID
    let date: Date
    let motionType: String
    let score: Int
    let summary: String
    let priorityFocusTitle: String
    let priorityFocusReason: String
    let priorityFocusNextStep: String
    let metricSnapshots: [HistoryMetricSnapshot]
    let thumbnailData: Data?
    let videoFileName: String?
    let professionalAccessGranted: Bool?
    var isFavorite: Bool
    var note: String?
    let result: AnalysisResult

    init(
        id: UUID = UUID(),
        date: Date = Date(),
        motionType: String,
        score: Int,
        summary: String,
        priorityFocusTitle: String = "",
        priorityFocusReason: String = "",
        priorityFocusNextStep: String = "",
        metricSnapshots: [HistoryMetricSnapshot] = [],
        thumbnailData: Data? = nil,
        videoFileName: String? = nil,
        professionalAccessGranted: Bool? = nil,
        isFavorite: Bool = false,
        note: String? = nil,
        result: AnalysisResult
    ) {
        self.id = id
        self.date = date
        self.motionType = motionType
        self.score = score
        self.summary = summary
        self.priorityFocusTitle = priorityFocusTitle
        self.priorityFocusReason = priorityFocusReason
        self.priorityFocusNextStep = priorityFocusNextStep
        self.metricSnapshots = metricSnapshots
        self.thumbnailData = thumbnailData
        self.videoFileName = videoFileName
        self.professionalAccessGranted = professionalAccessGranted
        self.isFavorite = isFavorite
        self.note = note
        self.result = result
    }

    init(
        result: AnalysisResult,
        thumbnailData: Data? = nil,
        videoFileName: String? = nil,
        professionalAccessGranted: Bool? = nil,
        isFavorite: Bool = false,
        note: String? = nil
    ) {
        let report = ResultReportFactory.make(from: result)
        let metrics = report.metrics.map { metric in
            HistoryMetricSnapshot(
                key: metric.key,
                title: metric.key.displayTitle,
                valueText: metric.currentValue,
                status: Self.status(for: metric.band, confidence: metric.confidence)
            )
        }

        self.init(
            id: result.id,
            date: result.date,
            motionType: result.motionType,
            score: result.score,
            summary: result.summary,
            priorityFocusTitle: result.freeIssues.first?.title ?? result.motionType,
            priorityFocusReason: result.freeIssues.first?.detail ?? result.summary,
            priorityFocusNextStep: result.trainingSuggestions.first ?? "先做完整动作练习，每组 5 次。",
            metricSnapshots: metrics,
            thumbnailData: thumbnailData,
            videoFileName: videoFileName,
            professionalAccessGranted: professionalAccessGranted,
            isFavorite: isFavorite,
            note: note,
            result: result
        )
    }

    private static func status(for band: String, confidence: ResultConfidenceLevel) -> TrainingFeedbackStatus {
        if confidence == .low {
            return .reference
        }

        let normalized = band
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()

        if normalized.contains("excellent") || normalized.contains("优秀") || normalized.contains("理想") {
            return .excellent
        }

        if normalized.contains("good") || normalized.contains("良好") || normalized.contains("稳定") || normalized.contains("流畅") {
            return .good
        }

        if normalized.contains("needs_work") || normalized.contains("poor") || normalized.contains("需") || normalized.contains("偏") {
            return .needsWork
        }

        return .good
    }
}

#if canImport(UIKit)
import UIKit

extension HistoryItem {
    var videoURL: URL? {
        guard let videoFileName, !videoFileName.isEmpty else { return nil }
        let url = Self.videoStorageDirectory.appendingPathComponent(videoFileName)
        return FileManager.default.fileExists(atPath: url.path) ? url : nil
    }

    var thumbnailImage: UIImage? {
        guard let thumbnailData else { return nil }
        return UIImage(data: thumbnailData)
    }

    var formattedDateTime: String {
        Self.dateTimeFormatter.string(from: date)
    }

    private static let dateTimeFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        formatter.dateFormat = "M 月 d 日 HH:mm"
        return formatter
    }()

    static var videoStorageDirectory: URL {
        let documents = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first
        let root = documents ?? FileManager.default.temporaryDirectory
        return root.appendingPathComponent("AnalysisVideos", isDirectory: true)
    }
}
#endif
