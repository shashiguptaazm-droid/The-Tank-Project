import SwiftUI

/// Root navigation gate.
///
/// Mirrors the Android `SplashActivity` → `OnboardingActivity` /
/// `LoginActivity` / `DashboardActivity` hand-off. The route itself is decided
/// by ``SplashView``, which ports `SplashActivity.checkNavigationState()` and
/// publishes the decision as a ``SplashRoute``.
struct RootView: View {

    @EnvironmentObject private var session: SessionStore
    @State private var isShowingSplash = true
    @State private var route: SplashRoute?

    var body: some View {
        ZStack {
            if isShowingSplash {
                SplashView { decided in
                    route = decided
                    isShowingSplash = false
                }
                .transition(.opacity)
            } else if route == .onboarding || !OnboardingView.hasCompletedOnboarding {
                OnboardingView {
                    route = .login
                }
                .transition(.opacity)
            } else if session.isAuthenticated {
                AppShellView()
                    .transition(.opacity)
            } else {
                LoginView()
                    .transition(.opacity)
            }
        }
        .animation(.easeInOut(duration: 0.25), value: isShowingSplash)
        .animation(.easeInOut(duration: 0.25), value: session.isAuthenticated)
        .animation(.easeInOut(duration: 0.25), value: route)
    }
}

#Preview {
    RootView()
        .environmentObject(SessionStore())
        .environment(\.api, .live)
}
