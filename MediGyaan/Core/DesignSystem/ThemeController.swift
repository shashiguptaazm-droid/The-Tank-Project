import SwiftUI
import Combine
import UIKit

/// Ports `AppThemeController.kt`'s theme mode.
///
/// The Kotlin file models appearance as a single boolean in
/// `SharedPreferences("MY_APP")` under `KEY_DARK_MODE = "dark_mode_enabled"`,
/// and `applySavedAppTheme` maps it onto exactly two `AppCompatDelegate`
/// constants:
///
/// ```kotlin
/// AppCompatDelegate.setDefaultNightMode(
///     if (isAppDarkModeEnabled(context)) AppCompatDelegate.MODE_NIGHT_YES
///     else AppCompatDelegate.MODE_NIGHT_NO
/// )
/// ```
///
/// `MODE_NIGHT_FOLLOW_SYSTEM` is never used upstream — with the flag absent the
/// app forces `MODE_NIGHT_NO`, so a device in dark mode still renders light.
/// `light` and `dark` below are those two states.
///
/// `system` is an **iOS-only addition**: it has no Android counterpart in this
/// file and is opt-in. It is deliberately not the default, so an install with
/// no stored value still behaves exactly like Android — forced light.
enum ThemeMode: String, CaseIterable, Identifiable {

    /// `AppCompatDelegate.MODE_NIGHT_NO`, and the value implied by Android's
    /// `getBoolean(KEY_DARK_MODE, false)` default.
    case light

    /// `AppCompatDelegate.MODE_NIGHT_YES`.
    case dark

    /// Follows the system appearance. Not reachable from the Android build.
    case system

    var id: String { rawValue }

    /// The `ColorScheme` a view should be forced into, or `nil` to let the
    /// system decide.
    ///
    /// iOS has no process-wide `setDefaultNightMode`. `AppTheme.Palette`
    /// resolves every token through `UIColor { traits in … }`, so setting the
    /// scheme at the root of the scene recolours the whole app — the reason
    /// `nil` (rather than a computed `.light`/`.dark`) is the correct spelling
    /// for `.system`.
    var colorScheme: ColorScheme? {
        switch self {
        case .light: return .light
        case .dark: return .dark
        case .system: return nil
        }
    }

    /// `true` when this mode forces the dark appearance.
    var isDark: Bool { self == .dark }

    /// The boolean this mode writes back to `AppPreferences.darkMode`.
    ///
    /// `nil` for `.system`, which has no boolean spelling. Returning `nil` keeps
    /// that mode out of the mirrored flag instead of flattening it to a stale
    /// boolean.
    var legacyFlag: Bool? {
        switch self {
        case .light: return false
        case .dark: return true
        case .system: return nil
        }
    }

    /// Short label for a settings row.
    var title: String {
        switch self {
        case .light: return "Light"
        case .dark: return "Dark"
        case .system: return "System"
        }
    }
}

/// Ports `AppThemeController`: persisted light/dark mode applied at runtime,
/// owned by one observable object instead of a process-wide
/// `AppCompatDelegate` static.
///
/// The Kotlin file is three top-level functions over a `Context`. This is the
/// same state with an explicit owner:
///
/// | Kotlin | Here |
/// |---|---|
/// | `isAppDarkModeEnabled(context)` | ``isDarkModeEnabled`` |
/// | `applySavedAppTheme(context)` | ``applySavedTheme()``, called once at launch by `MediGyaanApp` |
/// | `setAppDarkMode(context, enabled)` | ``setDarkModeEnabled(_:)`` |
/// | `AppCompatDelegate.setDefaultNightMode(…)` | `.preferredColorScheme(_:)` applied at the scene root |
/// | `prefs.edit().clear()` in `DashboardActivity.logout()` | ``reset()``, narrowed to the two theme keys |
///
/// **Storage.** Android persists a boolean under `dark_mode_enabled` inside
/// `SharedPreferences("MY_APP")`. iOS needs a string, because one boolean
/// cannot express `.system`, so the canonical value lives under
/// ``storageKey``. The boolean is kept in sync under
/// `AppPreferences.darkMode` because `SettingsView` and `DashboardView` bind
/// `@AppStorage` to it directly — that binding predates this type and is not
/// being rewritten in this port.
///
/// **Two-way sync.** Writing through this type updates both keys. Writing
/// through either pre-existing `@AppStorage` toggle is observed and folded
/// back in, so an explicit toggle always wins — including out of `.system`.
///
/// The appearance itself still lives in `AppTheme`; this type only decides
/// *which* scheme is forced. For the window chrome, feed ``isDarkModeEnabled``
/// to `materialThemeFromPreferences(isDarkModeEnabled:)` and
/// `androidWindowChrome(darkTheme:)`, both from `Theme+Android.swift`.
@MainActor
final class ThemeController: ObservableObject {

    /// `UserDefaults` key holding the ``ThemeMode`` raw value.
    ///
    /// Distinct from `AppPreferences.darkMode` because the boolean cannot
    /// represent `.system`.
    static let storageKey = "mg.themeMode"

    /// Process-wide instance, for the launch-time application seam.
    static let shared = ThemeController()

    private static let logTag = "ThemeController"

    /// The mode currently being forced. Set through ``set(_:)``,
    /// ``setDarkModeEnabled(_:)`` or ``toggle()``.
    @Published private(set) var mode: ThemeMode

    private let store: UserDefaults

    /// Last value this type wrote to `AppPreferences.darkMode`, so a change that
    /// originated here is not mistaken for one that came from a view.
    private var mirroredLegacyFlag: Bool

    private let defaultsObserver: NSObjectProtocol?

    init(store: UserDefaults = .standard) {
        self.store = store

        // No access to `mode` in here: `mode` is a `@Published` property whose
        // accessor reads `self._mode` before two-phase initialization is
        // complete. Read the raw persisted value directly instead.
        mirroredLegacyFlag =
            store.object(forKey: AppPreferences.darkMode) as? Bool ?? false

        if let raw = store.string(forKey: Self.storageKey),
           let persisted = ThemeMode(rawValue: raw) {
            mode = persisted
        } else if store.object(forKey: AppPreferences.darkMode) != nil {
            mode = store.bool(forKey: AppPreferences.darkMode) ? .dark : .light
        } else {
            mode = .light
        }

        defaultsObserver = NotificationCenter.default.addObserver(
            forName: UserDefaults.didChangeNotification,
            object: store,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor [weak self] in
                self?.syncLegacyFlag()
            }
        }
    }

    deinit {
        if let defaultsObserver {
            NotificationCenter.default.removeObserver(defaultsObserver)
        }
    }

    // MARK: - Reading

    /// Ports `isAppDarkModeEnabled(context)` — what `ui/theme/Theme.kt` passes
    /// to `darkTheme = isAppDarkModeEnabled(context)`.
    ///
    /// The raw stored flag is deliberately **not** returned for `.system`;
    /// consumers that need a concrete boolean want the appearance actually in
    /// effect.
    var isDarkModeEnabled: Bool {
        switch mode {
        case .light: return false
        case .dark: return true
        case .system: return UITraitCollection.current.userInterfaceStyle == .dark
        }
    }

    /// The scheme to force at the root of the scene, or `nil` for `.system`.
    var colorScheme: ColorScheme? { mode.colorScheme }

    /// Ports `applySavedAppTheme(context)`, which `EduLabsApplication.onCreate()`
    /// and `EditProfileActivity`/`GoalActivity`/`ProfileActivity`/
    /// `ThesisAnalyzerActivity` call before they draw.
    ///
    /// Re-reads the store rather than trusting `init`, so a write that landed
    /// between construction and the first frame is still picked up, and logs the
    /// applied mode the way the Android `Log`/`RemoteLogger` pairing does.
    func applySavedTheme() {
        if let raw = store.string(forKey: Self.storageKey),
           let persisted = ThemeMode(rawValue: raw) {
            if let flag = persisted.legacyFlag {
                mirroredLegacyFlag = flag
            }
            if persisted != mode {
                mode = persisted
            }
        }
        RemoteLogger.log(
            tag: Self.logTag,
            message: "Applied saved theme \(mode.rawValue) (dark: \(isDarkModeEnabled))"
        )
    }

    /// Combine view of ``mode`` for observers outside a view hierarchy.
    var modePublisher: AnyPublisher<ThemeMode, Never> {
        $mode.removeDuplicates().eraseToAnyPublisher()
    }

    // MARK: - Writing

    /// Ports `setAppDarkMode(context, enabled)`.
    func setDarkModeEnabled(_ enabled: Bool) {
        set(enabled ? .dark : .light)
    }

    /// Ports the `val next = !darkModeEnabled; setAppDarkMode(this, next)`
    /// toggle in `ThesisAnalyzerActivity` and the dashboard's theme button.
    ///
    /// Toggling out of `.system` lands on the opposite of the appearance
    /// currently shown, which is what a user pressing the button means.
    func toggle() {
        set(isDarkModeEnabled ? .light : .dark)
    }

    /// Sets and persists the mode. No-op when already in `newMode`, so a
    /// repeated toggle cannot churn `UserDefaults`.
    func set(_ newMode: ThemeMode) {
        guard newMode != mode else { return }
        mode = newMode

        if let flag = newMode.legacyFlag {
            mirroredLegacyFlag = flag
            store.set(flag, forKey: AppPreferences.darkMode)
        }
        store.set(newMode.rawValue, forKey: Self.storageKey)
    }

    /// Ports the `prefs.edit().clear().apply()` that `DashboardActivity.logout()`
    /// runs, which wipes `dark_mode_enabled` along with everything else in
    /// `MY_APP`.
    ///
    /// Narrowed to the two theme keys: iOS has one flat `UserDefaults` domain,
    /// so a literal port would sign the user out of every preference the app
    /// owns. Returns to the ``ThemeMode/light`` default, matching Android's
    /// `getBoolean(KEY_DARK_MODE, false)`.
    func reset() {
        store.removeObject(forKey: Self.storageKey)
        store.removeObject(forKey: AppPreferences.darkMode)
        mirroredLegacyFlag = false
        mode = .light
    }

    // MARK: - Legacy key bridge

    /// Folds a change made through the pre-existing
    /// `@AppStorage(AppPreferences.darkMode)` bindings in `SettingsView` and
    /// `DashboardView` back into ``mode`` — the role `setAppDarkMode` played on
    /// Android when a screen owned the toggle.
    ///
    /// A write this type made is skipped by comparing against
    /// ``mirroredLegacyFlag`` first, which is what keeps the two keys from
    /// driving each other in a loop.
    private func syncLegacyFlag() {
        guard let stored = store.object(forKey: AppPreferences.darkMode) as? Bool else { return }
        guard stored != mirroredLegacyFlag else { return }
        set(stored ? .dark : .light)
    }
}

// MARK: - SwiftUI seam

/// Installs ``ThemeController/colorScheme`` on a subtree.
///
/// Replaces the `.preferredColorScheme(darkMode ? .dark : .light)` that
/// `MediGyaanApp` applies today: the scheme is read from the controller's
/// published `mode` instead of a second `@AppStorage` copy, so a toggle and
/// the applied appearance cannot disagree.
private struct AppColorSchemeModifier: ViewModifier {

    @EnvironmentObject private var theme: ThemeController

    func body(content: Content) -> some View {
        content.preferredColorScheme(theme.colorScheme)
    }
}

extension View {

    /// Applies the mode from the `ThemeController` in the environment.
    ///
    /// ```swift
    /// RootView()
    ///     .environmentObject(theme)
    ///     .appColorScheme()
    /// ```
    ///
    /// Naming differs from SwiftUI's own `preferredColorScheme(_:)` so the two
    /// overloads never meet at a call site.
    func appColorScheme() -> some View {
        modifier(AppColorSchemeModifier())
    }
}