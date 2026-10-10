import SwiftUI

/// Application entry point.
///
/// Replaces the Android `EduLabsApplication` + `SplashActivity` pairing:
/// `AppDelegateBootstrap` ports `EduLabsApplication.onCreate()`, and the
/// session is restored synchronously from the Keychain/`UserDefaults`, so the
/// splash screen only needs to cover the branding beat.
@main
struct MediGyaanApp: App {

    /// Ports `EduLabsApplication.onCreate()`: notification-centre wiring, the
    /// off-main `ModelRotator` prewarm, the debug startup audit, and the APNs
    /// registration/token callbacks.
    @UIApplicationDelegateAdaptor(AppDelegateBootstrap.self) private var appDelegate

    @StateObject private var session = SessionStore()

    /// Owns the persisted light/dark/system mode ported from
    /// `AppThemeController.kt`.
    ///
    /// Applied at the window level rather than per screen: `AppTheme.Palette`
    /// resolves every token through `UIColor { traits in … }`, so flipping the
    /// preferred scheme recolours the whole app from this one modifier.
    @StateObject private var theme = ThemeController()

    @Environment(\.scenePhase) private var scenePhase

    init() {
        RemoteLogger.initializeCrashReporting()
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(session)
                .environmentObject(theme)
                .environment(\.api, .live)
                .tint(AppTheme.Palette.primary)
                .appColorScheme()
                .onChange(of: scenePhase) { newPhase in
                    RemoteLogger.log(tag: "AppLifecycle", message: "Scene phase changed to: \(newPhase)")
                }
        }
    }
}
