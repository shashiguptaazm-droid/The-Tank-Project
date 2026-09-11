import SwiftUI

/// Application entry point.
///
/// Replaces the Android `EduLabsApplication` + `SplashActivity` pairing: the
/// session is restored synchronously from the Keychain/`UserDefaults`, so the
/// splash screen only needs to cover the brief branding beat.
@main
struct MediGyaanApp: App {

    @StateObject private var session = SessionStore()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(session)
                .environment(\.api, .live)
                .tint(AppTheme.Palette.primary)
        }
    }
}
