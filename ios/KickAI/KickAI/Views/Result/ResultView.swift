import SwiftUI

struct ResultView: View {
    @EnvironmentObject private var sessionManager: SessionManager
    let result: AnalysisResult
    let source: AnalysisFlowSource
    let reportPayload: AnalysisReportPayload?
    let videoURL: URL?
    let videoLabel: String?
    let professionalAccessOverride: Bool?

    @State private var showPaywall = false
    @State private var showPlaybackCoach = false

    init(
        result: AnalysisResult,
        source: AnalysisFlowSource,
        reportPayload: AnalysisReportPayload? = nil,
        videoURL: URL? = nil,
        videoLabel: String? = nil,
        professionalAccessOverride: Bool? = nil
    ) {
        self.result = result
        self.source = source
        self.reportPayload = reportPayload
        self.videoURL = videoURL
        self.videoLabel = videoLabel
        self.professionalAccessOverride = professionalAccessOverride
    }

    private var report: ResultReport {
        ResultReportFactory.make(from: result, payload: reportPayload)
    }

    private var isCurrentLatestResult: Bool {
        result.id == sessionManager.latestResult.id
    }

    private var effectiveProAccess: Bool {
        professionalAccessOverride ?? sessionManager.hasProfessionalAccess(for: result.id)
    }

    var body: some View {
        ResultReportScreen(
            report: report,
            videoDuration: result.videoReviewData.duration,
            videoURL: videoURL,
            videoLabel: videoLabel,
            hasProAccess: effectiveProAccess,
            isCurrentLatestResult: isCurrentLatestResult,
            onOpenUpload: {
                sessionManager.resetAnalysisNavigation()
            },
            onOpenHistory: {
                sessionManager.resetHistoryNavigation()
            },
            onOpenPaywall: {
                showPaywall = true
            },
            onOpenPlaybackCoach: {
                showPlaybackCoach = true
            }
        )
        .navigationTitle("训练反馈")
        .navigationBarTitleDisplayMode(.inline)
        .navigationBarBackButtonHidden(source == .home)
        .kickNavigationBar()
        .toolbar {
            if source == .home {
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        sessionManager.resetHomeNavigation()
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: "chevron.left")
                            Text("返回首页")
                        }
                        .font(AppTypography.bodyMedium)
                        .foregroundStyle(AppColors.textPrimary)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
        .navigationDestination(isPresented: $showPaywall) {
            PaywallView()
        }
        .navigationDestination(isPresented: $showPlaybackCoach) {
            PlaybackCoachView(
                result: result,
                videoURL: videoURL,
                hasProfessionalAccessOverride: effectiveProAccess
            )
        }
    }
}
