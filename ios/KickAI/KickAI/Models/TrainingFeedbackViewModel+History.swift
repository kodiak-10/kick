import Foundation

extension TrainingFeedbackViewModel {
    func makeHistoryResult(date: Date = Date()) -> AnalysisResult {
        if isResultAnomalous {
            let anomalySummary = integritySummary.isEmpty ? "本次结果存在异常，请重新分析" : integritySummary
            let anomalyDetail = integrityReasons.isEmpty
                ? "动作类型、总分和等级当前不一致，系统已避免展示错误组合。"
                : integrityReasons.joined(separator: "；")

            return AnalysisResult(
                date: date,
                motionType: actionName,
                score: scoreValue ?? 0,
                summary: anomalySummary,
                freeIssues: [
                    AnalysisIssue(
                        title: "结果存在异常",
                        detail: anomalyDetail,
                        severityLabel: "需重试"
                    )
                ],
                videoReviewData: VideoReviewData(
                    duration: videoEvidence.duration,
                    freeIssueLimit: 1,
                    issues: []
                ),
                premiumInsights: AppMockData.premiumFeatures,
                trainingSuggestions: [anomalySummary],
                trendSummary: anomalySummary
            )
        }

        return AnalysisResult(
            date: date,
            motionType: actionName,
            score: scoreValue ?? 0,
            summary: headline,
            freeIssues: makeHistoryIssues(),
            videoReviewData: VideoReviewData(
                duration: videoEvidence.duration,
                freeIssueLimit: 1,
                issues: makePlaybackIssues()
            ),
            premiumInsights: AppMockData.premiumFeatures,
            trainingSuggestions: trainingSuggestions.isEmpty ? [priorityFocus.nextStep] : trainingSuggestions,
            trendSummary: confidenceReview.summary
        )
    }

    private func makeHistoryIssues() -> [AnalysisIssue] {
        if !problemCards.isEmpty {
            return Array(problemCards.prefix(2)).map { card in
                AnalysisIssue(
                    title: card.topic,
                    detail: "\(card.issue) \(card.fix)",
                    severityLabel: card.status.displayLabel
                )
            }
        }

        if !pendingCards.isEmpty {
            return Array(pendingCards.prefix(2)).map { card in
                AnalysisIssue(
                    title: card.topic,
                    detail: "\(card.reason) \(card.captureAdvice)",
                    severityLabel: card.status.displayLabel
                )
            }
        }

        return [
            AnalysisIssue(
                title: priorityFocus.title,
                detail: priorityFocus.reason,
                severityLabel: priorityFocus.status.displayLabel
            )
        ]
    }

    private func makePlaybackIssues() -> [PlaybackIssue] {
        let combinedIssues = problemCards.map { card in
            PlaybackIssue(
                time: card.time,
                title: card.topic,
                phase: card.markerKind.motionPhase,
                shortHint: card.issue,
                explanation: card.issue,
                fixAdvice: card.fix,
                trainingAdvice: card.practice,
                isProOnly: false
            )
        } + pendingCards.map { card in
            PlaybackIssue(
                time: card.time,
                title: card.topic,
                phase: card.markerKind.motionPhase,
                shortHint: card.reason,
                explanation: card.reason,
                fixAdvice: card.captureAdvice,
                trainingAdvice: card.note,
                isProOnly: true
            )
        }

        let ordered = combinedIssues.sorted { lhs, rhs in
            lhs.time < rhs.time
        }

        return ordered.enumerated().map { index, issue in
            PlaybackIssue(
                id: issue.id,
                time: issue.time,
                title: issue.title,
                phase: issue.phase,
                shortHint: issue.shortHint,
                explanation: issue.explanation,
                fixAdvice: issue.fixAdvice,
                trainingAdvice: issue.trainingAdvice,
                isProOnly: index >= 1
            )
        }
    }
}

extension TrainingFeedbackTimelineMarkerKind {
    var motionPhase: MotionPhase {
        switch self {
        case .receive:
            return .support
        case .strike:
            return .strike
        case .returnTouch, .stable:
            return .followThrough
        case .problem, .pending:
            return .approach
        }
    }
}
