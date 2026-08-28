import SwiftUI

struct RootView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        Group {
            if appState.hasSeenOnboarding {
                MainShellView()
            } else {
                OnboardingView()
            }
        }
        .background(AppTheme.background.ignoresSafeArea())
    }
}

private struct MainShellView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        VStack(spacing: 0) {
            SystemStatusBar(status: appState.cameraStatus)
                .padding(.horizontal, 16)
                .padding(.top, 12)

            NavigationStack(path: $appState.path) {
                TabView(selection: $appState.selectedTab) {
                    HomeView()
                        .tag(MainTab.home)
                        .tabItem {
                            Label("首页", systemImage: "house.fill")
                        }

                    HistoryView()
                        .tag(MainTab.history)
                        .tabItem {
                            Label("历史", systemImage: "clock.arrow.circlepath")
                        }

                    ProfileView()
                        .tag(MainTab.profile)
                        .tabItem {
                            Label("我的", systemImage: "person.crop.circle")
                        }
                }
                .toolbarBackground(.visible, for: .tabBar)
                .navigationDestination(for: AppRoute.self) { route in
                    switch route {
                    case .upload:
                        UploadVideoView()
                    case .processing:
                        ProcessingView()
                    case let .result(id):
                        ResultView(recordID: id)
                    case let .paywall(source):
                        PaywallView(source: source)
                    }
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }
}
