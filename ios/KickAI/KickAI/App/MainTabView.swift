import SwiftUI

struct MainTabView: View {
    @EnvironmentObject private var sessionManager: SessionManager

    var body: some View {
        TabView(selection: $sessionManager.selectedTab) {
            NavigationStack {
                HomeView()
            }
            .id(sessionManager.homeNavigationResetID)
            .tag(AppTab.home)
            .tabItem {
                Label(AppTab.home.title, systemImage: AppTab.home.iconName)
            }

            NavigationStack {
                UploadView()
            }
            .id(sessionManager.analysisNavigationResetID)
            .tag(AppTab.analysis)
            .tabItem {
                Label(AppTab.analysis.title, systemImage: AppTab.analysis.iconName)
            }

            NavigationStack {
                DiscoverView()
            }
            .tag(AppTab.discover)
            .tabItem {
                Label(AppTab.discover.title, systemImage: AppTab.discover.iconName)
            }

            NavigationStack {
                HistoryView()
            }
            .id(sessionManager.historyNavigationResetID)
            .tag(AppTab.history)
            .tabItem {
                Label(AppTab.history.title, systemImage: AppTab.history.iconName)
            }

            NavigationStack {
                ProfileView()
            }
            .tag(AppTab.profile)
            .tabItem {
                Label(AppTab.profile.title, systemImage: AppTab.profile.iconName)
            }
        }
        .tint(AppColors.textPrimary)
        .background(AppColors.background.ignoresSafeArea())
    }
}
