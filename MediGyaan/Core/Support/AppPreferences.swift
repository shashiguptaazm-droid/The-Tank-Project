import Foundation

/// Canonical `UserDefaults` keys shared across the app.
///
/// The keys were previously spelled out as bare string literals at each call
/// site. That is how the dark-mode toggle came to be **written but never
/// applied**: `SettingsView` and `DashboardView` both bound
/// `@AppStorage("mg.darkMode")`, while nothing read the key to change the
/// appearance, so flipping the switch did nothing visible.
///
/// Centralising them here means the value has a single spelling and a single
/// owner. `MediGyaanApp` is what applies ``darkMode`` app-wide.
///
/// Android equivalent: `SharedPreferences("MY_APP")`, where the theme flag is
/// `dark_mode_enabled` — see the Android `AppThemeController.kt`.
enum AppPreferences {

    /// Forces the app dark when `true` and light when `false`.
    ///
    /// `false` by default, matching Android's
    /// `getBoolean(KEY_DARK_MODE, false)`.
    ///
    /// Note this is a **forced** choice, not "follow the system": Android's
    /// `applySavedAppTheme` calls `AppCompatDelegate.setDefaultNightMode` with
    /// `MODE_NIGHT_NO` when the flag is off, so a device in dark mode still
    /// gets the light theme. The iOS wiring uses `.light` rather than `nil` for
    /// the same reason.
    static let darkMode = "mg.darkMode"

    /// Master switch for push notifications.
    static let notifications = "mg.notifications"

    /// Whether quiz/answer sound effects play.
    static let soundEffects = "mg.soundEffects"

    /// Whether quiz progress is pushed to `api/sync_user_cache.php`.
    static let autoSync = "mg.autoSync"

    /// JSON array of recent global-search terms.
    static let recentSearches = "mg.recentSearches"
}