import SwiftUI

/// Root of the app: decides between onboarding and the main tab shell.
struct RootView: View {
    @Environment(AppModel.self) private var app

    var body: some View {
        NavigationStack {
            if app.showOnboarding {
                OnboardingContainerView()
            } else {
                MainTabView()
            }
        }
        .task { app.bootstrap() }
    }
}
