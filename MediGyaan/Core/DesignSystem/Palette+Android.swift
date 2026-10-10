import SwiftUI

// Ports `ui/theme/Color.kt` — the twenty-four fixed Jetpack Compose
// `Color(0xFF…)` constants that `Theme.kt` feeds into `lightColorScheme(…)` and
// `darkColorScheme(…)`.
//
// `Color.kt` declares plain top-level `val`s: every one is a single literal
// with no light/dark branching, and the appearance switch lives one file up in
// `Theme.kt`. ``AppTheme/Palette`` therefore already folds most of them into
// adaptive `light:/dark:` pairs — but folding is lossy in one direction, since
// no token can hand back the literal it was built from. These members keep the
// untouched source values addressable, which is what a fixed-brand swatch, a
// design-token audit, or a check against the Android build needs.
//
// Colour space: Android ARGB is sRGB, and `Color(hex:)` builds `.sRGB` from the
// raw bytes divided by 255. No Display P3 transform is applied, matching the
// Kotlin literals exactly. Every constant here is fully opaque, but the
// `0xFF…` alpha byte is kept so each line is a byte-for-byte transcription of
// its Kotlin original.
//
// Naming: every member carries an `android` prefix. The unqualified Kotlin
// names (`IndigoPrimary`, `DarkBackground`, `SuccessGreen`, …) would collide
// with the adaptive tokens above, and a redeclaration inside the same type is a
// compile error. The prefix follows the convention `Theme+Android.swift`
// established for `AppTheme/Radius`.
//
// Where a member has an adaptive counterpart it is named in the doc comment, so
// the relationship is readable without cross-referencing the Kotlin.

extension AppTheme.Palette {

    // MARK: - Light scheme

    // The first block of `Color.kt`, feeding `LightColorScheme` in `Theme.kt`.

    /// Ports `Color.kt` `IndigoPrimary` (#5C6BC0) — `LightColorScheme.primary`.
    /// Adaptive counterpart: ``AppTheme/Palette/primary``.
    static let androidIndigoPrimary = Color(hex: 0xFF5C6BC0)

    /// Ports `Color.kt` `IndigoDark` (#3949AB) — `primary_dark` in
    /// `res/values/colors.xml`. Adaptive counterpart:
    /// ``AppTheme/Palette/primaryVariant`` and ``AppTheme/Palette/primaryDark``.
    static let androidIndigoDark = Color(hex: 0xFF3949AB)

    /// Ports `Color.kt` `IndigoLight` (#E8EAF6) —
    /// `LightColorScheme.primaryContainer`. Adaptive counterpart:
    /// ``AppTheme/Palette/primaryContainer``.
    static let androidIndigoLight = Color(hex: 0xFFE8EAF6)

    /// Ports `Color.kt` `AmberSecondary` (#FFD54F) — `secondary` in both
    /// schemes. Adaptive counterpart: ``AppTheme/Palette/secondary``.
    static let androidAmberSecondary = Color(hex: 0xFFFFD54F)

    /// Ports `Color.kt` `AmberDark` (#FFA000) — `secondary_variant` in
    /// `res/values/colors.xml`. Adaptive counterpart:
    /// ``AppTheme/Palette/secondaryVariant``.
    static let androidAmberDark = Color(hex: 0xFFFFA000)

    /// Ports `Color.kt` `LightBackground` (#F6F8FC) —
    /// `LightColorScheme.background`. Adaptive counterpart:
    /// ``AppTheme/Palette/background``.
    static let androidLightBackground = Color(hex: 0xFFF6F8FC)

    /// Ports `Color.kt` `LightSurface` (#FFFFFF) — `LightColorScheme.surface`.
    /// Adaptive counterpart: ``AppTheme/Palette/surface``.
    static let androidLightSurface = Color(hex: 0xFFFFFFFF)

    /// Ports `Color.kt` `LightTextPrimary` (#1A1C2E) —
    /// `onBackground` and `onSurface` in the light scheme. Adaptive
    /// counterpart: ``AppTheme/Palette/textPrimary``.
    static let androidLightTextPrimary = Color(hex: 0xFF1A1C2E)

    /// Ports `Color.kt` `LightTextSecondary` (#5F6368) — `text_secondary` in
    /// `res/values/colors.xml`. Adaptive counterpart:
    /// ``AppTheme/Palette/textSecondary``.
    static let androidLightTextSecondary = Color(hex: 0xFF5F6368)

    /// Ports `Color.kt` `LightOutline` (#D0D7E2) — `LightColorScheme.outline`.
    /// Adaptive counterpart: ``AppTheme/Palette/outline``.
    static let androidLightOutline = Color(hex: 0xFFD0D7E2)

    // MARK: - Dark scheme

    // The second block of `Color.kt`, feeding `DarkColorScheme` in `Theme.kt`.

    /// Ports `Color.kt` `DarkPrimary` (#B8C0FF) — `DarkColorScheme.primary`.
    /// Adaptive counterpart: ``AppTheme/Palette/primary``.
    static let androidDarkPrimary = Color(hex: 0xFFB8C0FF)

    /// Ports `Color.kt` `DarkPrimaryVariant` (#8C9EFF) —
    /// `primary_variant` in `res/values-night/colors.xml`. Adaptive
    /// counterpart: ``AppTheme/Palette/primaryVariant``.
    static let androidDarkPrimaryVariant = Color(hex: 0xFF8C9EFF)

    /// Ports `Color.kt` `DarkBackground` (#121212) —
    /// `DarkColorScheme.background`. Adaptive counterpart:
    /// ``AppTheme/Palette/background``.
    static let androidDarkBackground = Color(hex: 0xFF121212)

    /// Ports `Color.kt` `DarkSurface` (#1E1E1E) — `DarkColorScheme.surface`.
    /// Adaptive counterpart: ``AppTheme/Palette/surface``.
    static let androidDarkSurface = Color(hex: 0xFF1E1E1E)

    /// Ports `Color.kt` `DarkCardBg` (#242424) — `card_bg` in
    /// `res/values-night/colors.xml`. Adaptive counterpart:
    /// ``AppTheme/Palette/cardBackground``.
    static let androidDarkCardBackground = Color(hex: 0xFF242424)

    /// Ports `Color.kt` `DarkTextPrimary` (#FFFFFF) — `DarkColorScheme.onSurface`.
    /// Adaptive counterpart: ``AppTheme/Palette/textPrimary``.
    ///
    /// Note this is the scheme's `onSurface`, not its `onBackground`, which
    /// `Theme.kt` sets to `#F5F5F5`.
    static let androidDarkTextPrimary = Color(hex: 0xFFFFFFFF)

    /// Ports `Color.kt` `DarkTextSecondary` (#C7C7C7) — `text_secondary` in
    /// `res/values-night/colors.xml`. Adaptive counterpart:
    /// ``AppTheme/Palette/textSecondary``.
    static let androidDarkTextSecondary = Color(hex: 0xFFC7C7C7)

    /// Ports `Color.kt` `DarkOutline` (#4A4A4A) — `DarkColorScheme.outline`.
    /// Adaptive counterpart: ``AppTheme/Palette/outline``.
    static let androidDarkOutline = Color(hex: 0xFF4A4A4A)

    // MARK: - Semantic

    // The final block of `Color.kt`, shared by both schemes. `Theme.kt` wires
    // `ErrorRed` / `ErrorRedDark` into the schemes' `error` role; the remaining
    // four are referenced directly by the Compose screens.

    /// Ports `Color.kt` `SuccessGreen` (#43A047) — the light-scheme `success`
    /// resource. Adaptive counterpart: ``AppTheme/Palette/success``.
    static let androidSuccessGreen = Color(hex: 0xFF43A047)

    /// Ports `Color.kt` `ErrorRed` (#E53935) — `LightColorScheme.error`.
    /// Adaptive counterpart: ``AppTheme/Palette/error``.
    static let androidErrorRed = Color(hex: 0xFFE53935)

    /// Ports `Color.kt` `WarningOrange` (#FB8C00) — the light-scheme `warning`
    /// resource. Adaptive counterpart: ``AppTheme/Palette/warning``.
    static let androidWarningOrange = Color(hex: 0xFFFB8C00)

    /// Ports `Color.kt` `SuccessGreenDark` (#81C784) — the night `success`
    /// resource. Adaptive counterpart: ``AppTheme/Palette/success``.
    static let androidSuccessGreenDark = Color(hex: 0xFF81C784)

    /// Ports `Color.kt` `ErrorRedDark` (#EF5350) — `DarkColorScheme.error`.
    /// Adaptive counterpart: ``AppTheme/Palette/error``.
    static let androidErrorRedDark = Color(hex: 0xFFEF5350)

    /// Ports `Color.kt` `WarningOrangeDark` (#FFB74D) — the night `warning`
    /// resource. Adaptive counterpart: ``AppTheme/Palette/warning``.
    static let androidWarningOrangeDark = Color(hex: 0xFFFFB74D)
}