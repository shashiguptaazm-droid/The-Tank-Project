import SwiftUI

/// Root navigation gate.
///
/// Mirrors the Android `SplashActivity` → `LoginActivity` / `DashboardActivity`
/// hand-off, driven by `SessionStore.isAuthenticated`.
struct RootView: View {

    @EnvironmentObject private var session: SessionStore
    @State private var isShowingSplash = true

    var body: some View {
        ZStack {
            if isShowingSplash {
                SplashView()
                    .transition(.opacity)
            } else if session.isAuthenticated {
                AppTabView()
                    .transition(.opacity)
            } else {
                LoginView()
                    .transition(.opacity)
            }
        }
        .animation(.easeInOut(duration: 0.25), value: isShowingSplash)
        .animation(.easeInOut(duration: 0.25), value: session.isAuthenticated)
        .task {
            // Let the branding beat play, then route based on restored session.
            try? await Task.sleep(nanoseconds: 1_100_000_000)
            isShowingSplash = false
        }
    }
}

#Preview {
    RootView()
        .environmentObject(SessionStore())
        .environment(\.api, .live)
}
