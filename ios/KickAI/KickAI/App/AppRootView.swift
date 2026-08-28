import SwiftUI

struct AppRootView: View {
    @EnvironmentObject private var sessionManager: SessionManager

    var body: some View {
        Group {
            switch sessionManager.currentRoot {
            case .splash:
                SplashView()
            case .onboarding:
                OnboardingView()
            case .auth:
                AuthView()
            case .permission:
                PermissionView()
            case .main:
                MainTabView()
            }
        }
        .animation(.easeInOut(duration: 0.35), value: sessionManager.currentRoot)
    }
}
