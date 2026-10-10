import SwiftUI

// MARK: - MaterialTheme text styles

/// Ports a Compose `TextStyle` from `ui/theme/Type.kt` — the payload that
/// `Theme.kt` forwards to `MaterialTheme` as `typography = Typography`.
///
/// `FontFamily.Default` + `FontWeight.Normal` + `fontSize` collapse into a
/// single ``SwiftUI/Font`` on iOS, so only `lineHeight` and `letterSpacing`
/// need to travel alongside it.
struct AndroidTextStyle: Equatable {

    /// Resolved `fontFamily` / `fontWeight` / `fontSize`.
    let font: Font
    /// `TextStyle.lineHeight` — 24sp.
    let lineHeight: CGFloat
    /// `TextStyle.letterSpacing` — 0.5sp.
    let tracking: CGFloat

    /// `Typography.bodyLarge` — the only style `Type.kt` overrides.
    static let bodyLarge = AndroidTextStyle(
        font: AppTheme.Font.body,
        lineHeight: 24,
        tracking: 0.5
    )
}

// MARK: - MaterialTheme colour roles

/// Ports the `darkColorScheme(...)` and `lightColorScheme(...)` literals from
/// Android's `ui/theme/Theme.kt` — the two `ColorScheme`s that
/// `EduLabsRTMTheme` passes straight into Compose's `MaterialTheme`.
///
/// This is deliberately a *separate* value type from `AppTheme.Palette`: the
/// Android app reads its day/night colours from two different places
/// (`res/values*/colors.xml` for the XML themes, and the Kotlin `ColorScheme`
/// for every Compose screen), and the two disagree in places — most visibly
/// `onBackground`, which is `#F5F5F5` in the Compose dark scheme but
/// `#FFFFFF` in `colors-night.xml`. Collapsing them would silently recolour one
/// of the two, so both remain addressable.
///
/// Only the thirteen roles `Theme.kt` actually assigns are modelled. Every
/// other Material 3 role (surface variants, tertiary, inverse, error
/// containers) is left unset there and falls back to the Compose baseline.
struct AndroidMaterialColors: Equatable {

    // MARK: Primary

    /// `primary` — `#B8C0FF` night / `#5C6BC0` day (`DarkPrimary` / `IndigoPrimary`).
    let primary: Color
    /// `onPrimary` — `#0F1115` night / `#FFFFFF` day.
    let onPrimary: Color
    /// `primaryContainer` — `#2A325F` night / `#E8EAF6` day (`IndigoLight`).
    let primaryContainer: Color
    /// `onPrimaryContainer` — `#E8EAF6` night / `#1A237E` day.
    let onPrimaryContainer: Color

    // MARK: Secondary

    /// `secondary` — `#FFD54F` in both appearances (`AmberSecondary`).
    let secondary: Color
    /// `onSecondary` — `#0F1115` night / `#212121` day.
    let onSecondary: Color

    // MARK: Background & surface

    /// `background` — `#121212` night / `#F6F8FC` day.
    let background: Color
    /// `onBackground` — `#F5F5F5` night / `#1A1C2E` day.
    ///
    /// Note the night value: the Compose scheme is `#F5F5F5`, whereas
    /// `colors-night.xml`'s `colorOnBackground` is `#FFFFFF`.
    let onBackground: Color
    /// `surface` — `#1E1E1E` night / `#FFFFFF` day.
    let surface: Color
    /// `onSurface` — `#FFFFFF` night / `#1A1C2E` day.
    let onSurface: Color

    // MARK: Outline & error

    /// `outline` — `#4A4A4A` night / `#D0D7E2` day.
    let outline: Color
    /// `error` — `#EF5350` night / `#E53935` day (`ErrorRedDark` / `ErrorRed`).
    let error: Color
    /// `onError` — `#FFFFFF` in both appearances.
    let onError: Color

    /// `true` for the scheme produced from `darkColorScheme(...)`.
    let isDark: Bool

    init(
        primary: Color,
        onPrimary: Color,
        primaryContainer: Color,
        onPrimaryContainer: Color,
        secondary: Color,
        onSecondary: Color,
        background: Color,
        onBackground: Color,
        surface: Color,
        onSurface: Color,
        outline: Color,
        error: Color,
        onError: Color,
        isDark: Bool
    ) {
        self.primary = primary
        self.onPrimary = onPrimary
        self.primaryContainer = primaryContainer
        self.onPrimaryContainer = onPrimaryContainer
        self.secondary = secondary
        self.onSecondary = onSecondary
        self.background = background
        self.onBackground = onBackground
        self.surface = surface
        self.onSurface = onSurface
        self.outline = outline
        self.error = error
        self.onError = onError
        self.isDark = isDark
    }
}

extension AndroidMaterialColors {
    static var dark: AndroidMaterialColors { AppTheme.AndroidScheme.dark }
    static var light: AndroidMaterialColors { AppTheme.AndroidScheme.light }
}

extension AppTheme {

    /// Ports the `MaterialTheme` composition from `ui/theme/Theme.kt`: the
    /// `DarkColorScheme` / `LightColorScheme` pair and the `when` block in
    /// `EduLabsRTMTheme` that picks between them.
    ///
    /// Android exposes this through the ambient `MaterialTheme.colorScheme`
    /// CompositionLocal. SwiftUI has no equivalent ambient, so this namespace
    /// supplies the values and `View.materialTheme(darkTheme:dynamicColor:)`
    /// injects them into the environment (see `\.androidScheme`).
    enum AndroidScheme {

        /// Ports `DarkColorScheme`.
        static let dark = AndroidMaterialColors(
            primary: Color(hex: 0xB8C0FF),
            onPrimary: Color(hex: 0x0F1115),
            primaryContainer: Color(hex: 0x2A325F),
            onPrimaryContainer: Color(hex: 0xE8EAF6),
            secondary: Color(hex: 0xFFD54F),
            onSecondary: Color(hex: 0x0F1115),
            background: Color(hex: 0x121212),
            onBackground: Color(hex: 0xF5F5F5),
            surface: Color(hex: 0x1E1E1E),
            onSurface: Color(hex: 0xFFFFFF),
            outline: Color(hex: 0x4A4A4A),
            error: Color(hex: 0xEF5350),
            onError: Color(hex: 0xFFFFFF),
            isDark: true
        )

        /// Ports `LightColorScheme`.
        static let light = AndroidMaterialColors(
            primary: Color(hex: 0x5C6BC0),
            onPrimary: Color(hex: 0xFFFFFF),
            primaryContainer: Color(hex: 0xE8EAF6),
            onPrimaryContainer: Color(hex: 0x1A237E),
            secondary: Color(hex: 0xFFD54F),
            onSecondary: Color(hex: 0x212121),
            background: Color(hex: 0xF6F8FC),
            onBackground: Color(hex: 0x1A1C2E),
            surface: Color(hex: 0xFFFFFF),
            onSurface: Color(hex: 0x1A1C2E),
            outline: Color(hex: 0xD0D7E2),
            error: Color(hex: 0xE53935),
            onError: Color(hex: 0xFFFFFF),
            isDark: false
        )

        /// `dynamicColor` is honoured on Android only when
        /// `Build.VERSION.SDK_INT >= S` and it resolves through
        /// `dynamicDarkColorScheme` / `dynamicLightColorScheme`, which derive
        /// the scheme from the OS wallpaper palette. iOS has no equivalent
        /// source, and both Kotlin composables already default the flag to
        /// `false` — "Keep it false to enforce our customized brand guidelines
        /// consistently" — so the brand scheme is always returned and the flag
        /// is recorded rather than acted on.
        static let supportsDynamicColor = false

        /// Ports the `when` block in `EduLabsRTMTheme`: the scheme used for a
        /// given appearance.
        static func resolve(darkTheme: Bool, dynamicColor: Bool = false) -> AndroidMaterialColors {
            darkTheme ? .dark : .light
        }
    }

    /// Ports the `typography = Typography` argument that `Theme.kt` hands to
    /// `MaterialTheme`, i.e. the single `Typography` value built in
    /// `ui/theme/Type.kt`.
    ///
    /// `Type.kt` overrides exactly one style — `bodyLarge` at 16sp / 24sp line
    /// height / 0.5sp tracking in the platform default family — and leaves
    /// every other Material 3 style at its baseline. Those baselines are the
    /// M3 scale that ``AppTheme/Font`` already covers for screen copy, so only
    /// the overridden style is mirrored here.
    enum AndroidTypography {

        /// `Typography.bodyLarge` — 16sp, `FontWeight.Normal`,
        /// `FontFamily.Default`, 24sp line height, 0.5sp tracking.
        static let bodyLargeStyle = AndroidTextStyle.bodyLarge

        /// Applies `Typography.bodyLarge` — size and tracking — to body copy,
        /// the way `MaterialTheme` does for unstyled `Text`.
        static func bodyLargeText(_ text: String) -> some View {
            Text(text)
                .font(bodyLargeStyle.font)
                .tracking(bodyLargeStyle.tracking)
        }
    }
}

// MARK: - Compose Shapes() defaults

extension AppTheme.Radius {

    // `Theme.kt` passes no `shapes` argument to `MaterialTheme`, so every
    // Compose surface keeps the Material 3 baseline. The tokens below are those
    // defaults, kept under `android…` names so they cannot be confused with the
    // screen-level radii above (note `Radius.lg` is 20dp while the Compose
    // "large" shape is 16dp — different scales).

    /// 4dp — Compose `Shapes.extraSmall`, unchanged by `Theme.kt`.
    static let androidExtraSmall: CGFloat = 4
    /// 8dp — Compose `Shapes.small`.
    static let androidSmall: CGFloat = 8
    /// 12dp — Compose `Shapes.medium`.
    static let androidMedium: CGFloat = 12
    /// 16dp — Compose `Shapes.large`.
    static let androidLarge: CGFloat = 16
    /// 28dp — Compose `Shapes.extraLarge`.
    static let androidExtraLarge: CGFloat = 28
}

// MARK: - Environment bridge

private struct AndroidMaterialColorsKey: EnvironmentKey {
    static var defaultValue: AndroidMaterialColors { .light }
}

private struct AndroidTypographyKey: EnvironmentKey {
    static var defaultValue: AndroidTextStyle { .bodyLarge }
}

extension EnvironmentValues {

    /// The Compose `MaterialTheme.colorScheme` that `Theme.kt` composes,
    /// installed by `View.materialTheme(darkTheme:dynamicColor:)`.
    ///
    /// Defaults to the light scheme, mirroring Compose's own behaviour for a
    /// subtree that is not wrapped in `MaterialTheme`.
    var androidScheme: AndroidMaterialColors {
        get { self[AndroidMaterialColorsKey.self] }
        set { self[AndroidMaterialColorsKey.self] = newValue }
    }

    /// The Compose `MaterialTheme.typography` that `Theme.kt` passes through,
    /// i.e. `Type.kt`'s single overridden style.
    ///
    /// The remaining Material 3 styles are untouched compile-time constants on
    /// Android, so the environment carries only ``AndroidTextStyle/bodyLarge``.
    var androidTypography: AndroidTextStyle {
        get { self[AndroidTypographyKey.self] }
        set { self[AndroidTypographyKey.self] = newValue }
    }
}

// MARK: - MaterialTheme modifier

private struct AndroidMaterialThemeModifier: ViewModifier {

    @Environment(\.colorScheme) private var systemScheme

    /// `nil` reproduces the Kotlin default `darkTheme: Boolean = isSystemInDarkTheme()`.
    let darkTheme: Bool?
    let dynamicColor: Bool

    func body(content: Content) -> some View {
        let isDark = darkTheme ?? (systemScheme == .dark)
        return content
            .environment(\.androidScheme, AppTheme.AndroidScheme.resolve(darkTheme: isDark, dynamicColor: dynamicColor))
            .environment(\.androidTypography, AppTheme.AndroidTypography.bodyLargeStyle)
    }
}

extension View {

    /// Ports `EduLabsRTMTheme`: installs the `MaterialTheme` colour scheme from
    /// `Theme.kt` into the SwiftUI environment as `\.androidScheme`.
    ///
    /// * `darkTheme` — pass `nil` (the default) to keep Compose's
    ///   `isSystemInDarkTheme()` behaviour and follow the system appearance;
    ///   pass a value to force it, as `EduLabsRTMThemeFromPreferences` does
    ///   with `isAppDarkModeEnabled(context)`.
    /// * `dynamicColor` — kept for signature parity with the Kotlin parameter.
    ///   See ``AppTheme/AndroidScheme/supportsDynamicColor``.
    func materialTheme(darkTheme: Bool? = nil, dynamicColor: Bool = false) -> some View {
        modifier(AndroidMaterialThemeModifier(darkTheme: darkTheme, dynamicColor: dynamicColor))
    }

    /// Ports `EduLabsRTMThemeFromPreferences`, whose `darkTheme` comes from the
    /// `dark_mode_enabled` SharedPreference (`AppThemeController.kt`) rather
    /// than the system. Callers read the flag — on iOS,
    /// `@AppStorage(AppPreferences.darkMode)` — and pass it in; Android's
    /// `Context.getSharedPreferences` has no SwiftUI counterpart.
    func materialThemeFromPreferences(
        isDarkModeEnabled: Bool,
        dynamicColor: Bool = false
    ) -> some View {
        materialTheme(darkTheme: isDarkModeEnabled, dynamicColor: dynamicColor)
    }

    /// Ports the window chrome that `res/values/themes.xml` and
    /// `res/values-night/themes.xml` set on the Activity theme:
    /// `android:statusBarColor` = `?colorBackground`,
    /// `android:navigationBarColor` = `?colorSurface`, and
    /// `android:windowLightStatusBar` / `android:windowLightNavigationBar`
    /// flipped between day and night.
    ///
    /// iOS owns the status bar and has no navigation bar, so the background
    /// colour moves onto the navigation/tab bar and the light-vs-dark icon
    /// decision is expressed through `toolbarColorScheme`.
    func androidWindowChrome(darkTheme: Bool) -> some View {
        let colors = AppTheme.AndroidScheme.resolve(darkTheme: darkTheme)
        return background(colors.background.ignoresSafeArea())
            .toolbarBackground(colors.background, for: .navigationBar, .tabBar)
            .toolbarColorScheme(darkTheme ? .dark : .light, for: .navigationBar, .tabBar)
    }
}