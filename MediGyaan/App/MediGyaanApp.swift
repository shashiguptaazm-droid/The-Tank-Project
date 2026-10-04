import SwiftUI

/// Application entry point.
///
/// Replaces the Android `EduLabsApplication` + `SplashActivity` pairing: the
/// session is restored synchronously from the Keychain/`UserDefaults`, so the
/// splash screen only needs to cover the brief branding beat.
@main
struct MediGyaanApp: App {

    @StateObject private var session = SessionStore()

    /// Port of Android's `applySavedAppTheme` (`AppThemeController.kt`), which
    /// pushes the persisted flag into `AppCompatDelegate.setDefaultNightMode`.
    ///
    /// Applied at the window level rather than per screen: `AppTheme.Palette`
    /// resolves every token through `UIColor { traits in … }`, so flipping the
    /// preferred scheme recolours the whole app from this one modifier.
    ///
    /// `.light` is used for the off state rather than `nil` because Android
    /// forces `MODE_NIGHT_NO` when the flag is off instead of deferring to the
    /// system.
    @AppStorage(AppPreferences.darkMode) private var darkMode = false

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(session)
                .environment(\.api, .live)
                .tint(AppTheme.Palette.primary)
                .preferredColorScheme(darkMode ? .dark : .light)
        }
    }
}
