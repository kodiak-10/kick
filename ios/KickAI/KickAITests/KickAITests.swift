import Foundation
import Testing
@testable import KickAI

struct KickTests {
    @Test func liveConfigurationTargetsLocalAnalyzeEndpoint() {
        #expect(VideoAnalysisServiceConfiguration.live.baseURL.absoluteString == "http://127.0.0.1:8000")
        #expect(VideoAnalysisServiceConfiguration.live.endpointPath == "analyze_video")
        #expect(VideoAnalysisServiceConfiguration.live.videoFieldName == "video_file")
        #expect(VideoAnalysisServiceConfiguration.live.timeout == 60)
    }

    @Test func unknownExtensionFallsBackToVideoMp4MimeType() throws {
        let service = VideoAnalysisService(configuration: .live)
        let fileURL = try makeTempFile(name: "sample.unknown", data: Data([0x00]))
        defer { try? FileManager.default.removeItem(at: fileURL) }

        #expect(service.mimeType(for: fileURL) == "video/mp4")
    }

    @Test func multipartBodyUsesSelectedActionFieldsAndIncludesBinaryPayload() throws {
        let service = VideoAnalysisService(configuration: .live)
        let sourceData = Data([0x00, 0x01, 0x02, 0xFF, 0x10, 0x20])
        let sourceURL = try makeTempFile(name: "传球.mp4", data: sourceData)
        defer { try? FileManager.default.removeItem(at: sourceURL) }

        let bodyInfo = try service.buildMultipartBody(
            boundary: "Boundary-Test",
            textFields: [
                MultipartFormField(name: "selected_action", value: AnalysisActionChoice.pass.selectedActionValue),
                MultipartFormField(name: "analysis_template", value: AnalysisActionChoice.pass.analysisTemplateValue)
            ],
            fileURL: sourceURL,
            fieldName: "video_file",
            fileName: "传球.mp4",
            mimeType: "video/mp4"
        )
        defer { try? FileManager.default.removeItem(at: bodyInfo.bodyURL) }

        let bodyData = try Data(contentsOf: bodyInfo.bodyURL)
        let bodyText = String(decoding: bodyData, as: UTF8.self)

        #expect(bodyInfo.fieldNames == ["selected_action", "analysis_template", "video_file"])
        #expect(bodyInfo.fileName == "传球.mp4")
        #expect(bodyInfo.mimeType == "video/mp4")
        #expect(bodyInfo.bodySizeBytes > Int64(sourceData.count))
        #expect(bodyData.range(of: sourceData) != nil)
        #expect(bodyText.contains("name=\"selected_action\""))
        #expect(bodyText.contains("name=\"analysis_template\""))
        #expect(bodyText.contains("name=\"video_file\""))
        #expect(bodyText.contains("filename=\"传球.mp4\""))
        #expect(bodyText.contains("Content-Type: video/mp4"))
        #expect(bodyText.contains("--Boundary-Test"))
    }

    @Test func passReceiveSelectedActionUsesSequenceValue() {
        #expect(AnalysisActionChoice.passReceive.selectedActionValue == "pass_receive_sequence")
    }

    @Test func missingVideoFileServerErrorUsesSpecificMessage() {
        let error = VideoAnalysisServiceError.server(statusCode: 400, body: "missing_video_file")
        #expect(error.localizedDescription == "上传字段名错误或视频文件未成功附加到请求体")
    }

    @Test func trainingFeedbackViewModelBuildsPrimaryKeyframeAndUserFacingText() throws {
        let report = ResultReportFactory.make(from: AppMockData.latestAnalysis)
        let viewModel = TrainingFeedbackViewModel(report: report, videoDuration: 2.4)

        #expect(viewModel.videoEvidence.keyframes.count == 3)
        #expect(viewModel.videoEvidence.keyframes.contains(where: { $0.isPrimary }))

        let primary = try #require(viewModel.videoEvidence.keyframes.first(where: { $0.isPrimary }))
        #expect(viewModel.videoEvidence.primaryKeyframeID == primary.id)
        #expect(primary.conclusion.isEmpty == false)
        #expect(primary.mainPoint.isEmpty == false)
        #expect(primary.whyImportant.isEmpty == false)
        #expect(primary.howToChange.isEmpty == false)
    }

    @Test func responseScoreAndLevelConflictIsBlocked() throws {
        let response = try makeResponse(
            [
                "action_name": "short_pass",
                "action_display_name": "传球",
                "overall_score": 38,
                "level_label": "优秀",
                "summary": "本次结果存在冲突",
                "feedback_messages": ["请重新分析"]
            ]
        )
        let viewModel = TrainingFeedbackViewModel(response: response, videoDuration: 2.4)

        #expect(viewModel.isResultAnomalous)
        #expect(viewModel.actionName == "传球")
        #expect(viewModel.gradeText == "异常")
        #expect(viewModel.headline == "本次结果存在异常，请重新分析")
        #expect(viewModel.integrityReasons.contains(where: { $0.contains("总分和等级不匹配") }))
    }

    @Test func responseActionMismatchUsesMainActionDisplay() throws {
        let response = try makeResponse(
            [
                "action_name": "pass_receive_sequence",
                "action_display_name": "射门",
                "resolved_action_name": "pass_receive_sequence",
                "recommended_template": "pass_receive_sequence",
                "detected_action": "pass_receive_sequence",
                "overall_score": 82,
                "level_label": "良好",
                "summary": "传接球"
            ]
        )
        let viewModel = TrainingFeedbackViewModel(response: response, videoDuration: 2.4)

        #expect(viewModel.isResultAnomalous)
        #expect(viewModel.actionName == "传接球")
        #expect(viewModel.headline == "本次结果存在异常，请重新分析")
        #expect(viewModel.integrityReasons.contains(where: { $0.contains("动作类型和模板信息不一致") }))
    }

    @Test func selectedActionOverridesBackendActionDisplayAndKeepsSuggestion() throws {
        let response = try makeResponse(
            [
                "action_name": "pass_receive_sequence",
                "action_display_name": "射门",
                "resolved_action_name": "pass_receive_sequence",
                "recommended_template": "pass_receive_sequence",
                "detected_action": "pass_receive_sequence",
                "selected_action": "pass",
                "analysis_routed_by": "user_selected",
                "routed_analyzer": "pass",
                "overall_score": 82,
                "level_label": "良好",
                "summary": "传接球"
            ]
        )
        let viewModel = TrainingFeedbackViewModel(
            response: response,
            selectedAction: .pass,
            videoDuration: 2.4
        )

        #expect(!viewModel.isResultAnomalous)
        #expect(viewModel.actionName == "传球")
        #expect(viewModel.headline.contains("传球"))
        #expect(viewModel.systemActionSuggestion?.contains("系统建议") == true)
        #expect(viewModel.systemActionSuggestion?.contains("射门") == true)
    }

    @Test func selectedActionAndRoutedAnalyzerMatchKeepsRouteClean() throws {
        let response = try makeResponse(
            [
                "selected_action": "pass",
                "analysis_routed_by": "user_selected",
                "routed_analyzer": "pass",
                "action_name": "pass",
                "overall_score": 84,
                "level_label": "良好",
                "summary": "传球"
            ]
        )
        let viewModel = TrainingFeedbackViewModel(
            response: response,
            selectedAction: .pass,
            videoDuration: 2.4
        )

        #expect(viewModel.routeMismatchMessage == nil)
        #expect(viewModel.isResultAnomalous == false)
        #expect(viewModel.actionName == "传球")
    }

    @Test func selectedActionAndRoutedAnalyzerMismatchShowsDirectRouteMessage() throws {
        let response = try makeResponse(
            [
                "selected_action": "shot",
                "analysis_routed_by": "automatic",
                "routed_analyzer": "shot",
                "action_name": "shot",
                "overall_score": 84,
                "level_label": "良好",
                "summary": "射门"
            ]
        )
        let viewModel = TrainingFeedbackViewModel(
            response: response,
            selectedAction: .pass,
            videoDuration: 2.4
        )

        #expect(viewModel.routeMismatchMessage == "当前链路未按用户选择动作分析")
        #expect(viewModel.headline == "当前链路未按用户选择动作分析")
        #expect(viewModel.actionName == "传球")
    }

    @Test func missingSelectedActionTriggersDirectRouteMessage() throws {
        let response = try makeResponse(
            [
                "analysis_routed_by": "user_selected",
                "routed_analyzer": "pass",
                "action_name": "pass",
                "overall_score": 84,
                "level_label": "良好",
                "summary": "传球"
            ]
        )
        let viewModel = TrainingFeedbackViewModel(
            response: response,
            selectedAction: .pass,
            videoDuration: 2.4
        )

        #expect(viewModel.routeMismatchMessage == "当前分析没有按你选择的动作类型执行")
        #expect(viewModel.headline == "当前分析没有按你选择的动作类型执行")
    }

    @Test func anomalyHistorySummaryTagStaysAsResultAnomaly() {
        let anomalyResult = AnalysisResult(
            date: .now,
            motionType: "传球",
            score: 38,
            summary: "本次结果存在异常，请重新分析",
            freeIssues: [
                AnalysisIssue(
                    title: "结果存在异常",
                    detail: "动作类型和分数暂时不一致。",
                    severityLabel: "需重试"
                )
            ],
            videoReviewData: VideoReviewData(duration: 2.4, freeIssueLimit: 1, issues: []),
            premiumInsights: [],
            trainingSuggestions: ["本次结果存在异常，请重新分析"],
            trendSummary: "本次结果存在异常，请重新分析"
        )

        let report = ResultReportFactory.make(from: anomalyResult)
        #expect(report.summaryTag == "结果异常")
        #expect(report.summary == "本次结果存在异常，请重新分析")
    }

    private func makeTempFile(name: String, data: Data) throws -> URL {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("kickai-test-\(UUID().uuidString)-\(name)")
        try data.write(to: url, options: .atomic)
        return url
    }

    private func makeResponse(_ payload: [String: Any]) throws -> VideoAnalysisResponse {
        let data = try JSONSerialization.data(withJSONObject: payload, options: [])
        return try JSONDecoder().decode(VideoAnalysisResponse.self, from: data)
    }
}
