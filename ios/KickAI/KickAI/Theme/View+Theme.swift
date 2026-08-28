import SwiftUI

extension View {
    func kickScreenBackground() -> some View {
        background(ScreenBackground())
    }

    func kickNavigationBar() -> some View {
        toolbarBackground(AppColors.background.opacity(0.92), for: .navigationBar)
    }
}
