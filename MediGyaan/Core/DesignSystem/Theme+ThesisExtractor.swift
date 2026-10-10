import SwiftUI

// MARK: - Concrete Compose colour schemes

extension AppTheme {

    /// Ports `ThesisExtractorTheme`'s two `lightColorScheme(...)` and
    /// `darkColorScheme(...)` calls as one concrete, non-adaptive snapshot.
    ///
    /// ``AppTheme/ExtractorPalette`` already carries the same twenty roles as
    /// appearance-adaptive colours; this is the other half of the port. Compose
    /// picks the branch once per composition from an explicit `darkTheme`
    /// boolean rather than from the ambient trait, so `ThesisAnalyzerActivity`
    /// can force the extractor screens dark while the system is light. SwiftUI
    /// has no ambient `MaterialTheme` to branch inside, so the concrete branch
    /// is carried through the environment by ``thesisExtractorTheme(dark:)``
    /// and read with `@Environment(\.thesisExtractorScheme)`.
    ///
    /// Every value is the Kotlin literal converted straight from sRGB — each
    /// channel divided by 255, no Display P3 transform.
    struct ThesisExtractorScheme {

        // MARK: Primary

        /// `primary` — #0F5B92 day / #8DB7FF night.
        let primary: Color
        /// `onPrimary` — #FFFFFF day / #00325B night.
        let onPrimary: Color
        /// `primaryContainer` — #D0E4FF day / #174A79 night.
        let primaryContainer: Color
        /// `onPrimaryContainer` — #001D33 day / #D4E3FF night.
        let onPrimaryContainer: Color

        // MARK: Secondary

        /// `secondary` — #2F6B5C day / #93D5C2 night.
        let secondary: Color
        /// `onSecondary` — #FFFFFF day / #00382D night.
        let onSecondary: Color
        /// `secondaryContainer` — #B3E7D5 day / #1D5145 night.
        let secondaryContainer: Color
        /// `onSecondaryContainer` — #002018 day / #AFEEDC night.
        let onSecondaryContainer: Color

        // MARK: Tertiary

        /// `tertiary` — #8B4A63 day / #E7B6CC night.
        let tertiary: Color
        /// `onTertiary` — #FFFFFF day / #492435 night.
        let onTertiary: Color

        // MARK: Background & surface

        /// `background` — #F7F9FC day / #101417 night.
        let background: Color
        /// `onBackground` — #181C20 day / #E0E3E7 night.
        let onBackground: Color
        /// `surface` — #FFFFFF day / #181C20 night.
        let surface: Color
        /// `onSurface` — #181C20 day / #E0E3E7 night.
        let onSurface: Color
        /// `surfaceVariant` — #E0E7EF day / #40484F night.
        let surfaceVariant: Color
        /// `onSurfaceVariant` — #40484F day / #C0C7CE night.
        let onSurfaceVariant: Color

        // MARK: Outline

        /// `outline` — #70787F day / #8A9299 night.
        let outline: Color
        /// `outlineVariant` — #C0C7CE day / #40484F night.
        let outlineVariant: Color

        // MARK: Error

        /// `error` — #BA1A1A day / #FFB4AB night.
        let error: Color
        /// `onError` — #FFFFFF day / #690005 night.
        let onError: Color

        /// The branch `lightColorScheme(...)` produced.
        static let light = ThesisExtractorScheme(
            primary: Color(hex: 0xFF0F5B92),
            onPrimary: Color(hex: 0xFFFFFFFF),
            primaryContainer: Color(hex: 0xFFD0E4FF),
            onPrimaryContainer: Color(hex: 0xFF001D33),
            secondary: Color(hex: 0xFF2F6B5C),
            onSecondary: Color(hex: 0xFFFFFFFF),
            secondaryContainer: Color(hex: 0xFFB3E7D5),
            onSecondaryContainer: Color(hex: 0xFF002018),
            tertiary: Color(hex: 0xFF8B4A63),
            onTertiary: Color(hex: 0xFFFFFFFF),
            background: Color(hex: 0xFFF7F9FC),
            onBackground: Color(hex: 0xFF181C20),
            surface: Color(hex: 0xFFFFFFFF),
            onSurface: Color(hex: 0xFF181C20),
            surfaceVariant: Color(hex: 0xFFE0E7EF),
            onSurfaceVariant: Color(hex: 0xFF40484F),
            outline: Color(hex: 0xFF70787F),
            outlineVariant: Color(hex: 0xFFC0C7CE),
            error: Color(hex: 0xFFBA1A1A),
            onError: Color(hex: 0xFFFFFFFF)
        )

        /// The branch `darkColorScheme(...)` produced.
        static let dark = ThesisExtractorScheme(
            primary: Color(hex: 0xFF8DB7FF),
            onPrimary: Color(hex: 0xFF00325B),
            primaryContainer: Color(hex: 0xFF174A79),
            onPrimaryContainer: Color(hex: 0xFFD4E3FF),
            secondary: Color(hex: 0xFF93D5C2),
            onSecondary: Color(hex: 0xFF00382D),
            secondaryContainer: Color(hex: 0xFF1D5145),
            onSecondaryContainer: Color(hex: 0xFFAFEEDC),
            tertiary: Color(hex: 0xFFE7B6CC),
            onTertiary: Color(hex: 0xFF492435),
            background: Color(hex: 0xFF101417),
            onBackground: Color(hex: 0xFFE0E3E7),
            surface: Color(hex: 0xFF181C20),
            onSurface: Color(hex: 0xFFE0E3E7),
            surfaceVariant: Color(hex: 0xFF40484F),
            onSurfaceVariant: Color(hex: 0xFFC0C7CE),
            outline: Color(hex: 0xFF8A9299),
            outlineVariant: Color(hex: 0xFF40484F),
            error: Color(hex: 0xFFFFB4AB),
            onError: Color(hex: 0xFF690005)
        )

        /// Picks the branch Compose would have taken for `colorScheme`, i.e. what
        /// the two activities passing `isSystemInDarkTheme()` render.
        static func adaptive(for colorScheme: ColorScheme) -> ThesisExtractorScheme {
            colorScheme == .dark ? .dark : .light
        }
    }

    /// The branch `ThesisExtractorTheme(darkTheme:)` would have selected.
    static func extractorScheme(dark: Bool) -> ThesisExtractorScheme {
        dark ? .dark : .light
    }

    /// Ports the default `Shapes` Compose hands to `MaterialTheme` inside
    /// `ThesisExtractorTheme`.
    ///
    /// The Kotlin file does not override `Shapes`, so these are Material 3's
    /// stock scale rather than a bespoke extractor scale. They are exposed so an
    /// extractor surface can be built without borrowing ``Radius``, which
    /// encodes the app-wide Material card radii.
    enum ThesisExtractorRadius {
        /// 4dp — `Shapes.extraSmall`.
        static let extraSmall: CGFloat = 4
        /// 8dp — `Shapes.small`.
        static let small: CGFloat = 8
        /// 12dp — `Shapes.medium`.
        static let medium: CGFloat = 12
        /// 16dp — `Shapes.large`.
        static let large: CGFloat = 16
        /// 28dp — `Shapes.extraLarge`.
        static let extraLarge: CGFloat = 28
    }
}

// MARK: - Ambient scheme

private struct ThesisExtractorSchemeKey: EnvironmentKey {
    static let defaultValue = AppTheme.ThesisExtractorScheme.light
}

extension EnvironmentValues {

    /// The concrete scheme ``thesisExtractorTheme(dark:)`` resolved for this
    /// subtree. Defaults to the light branch so a screen that forgets the
    /// modifier still renders on the extractor's day palette.
    var thesisExtractorScheme: AppTheme.ThesisExtractorScheme {
        get { self[ThesisExtractorSchemeKey.self] }
        set { self[ThesisExtractorSchemeKey.self] = newValue }
    }
}

// MARK: - The modifier

/// Ports the `MaterialTheme(colorScheme:typography:content:)` wrapper at the
/// bottom of `ThesisExtractorTheme`.
///
/// The wrapper did three things for its subtree: published the colour scheme,
/// published the shared `Typography`, and let the host `Scaffold` paint the
/// scheme's `background`. iOS keeps the first and third — the scheme goes into
/// the environment, the background and the control tint follow from it. There is
/// no typography to publish: the Kotlin passes the package-wide `Typography`
/// rather than a bespoke one, which is already ``AppTheme/Font`` here.
///
/// The modifier deliberately does **not** force `preferredColorScheme`. On
/// Android the extractor `MaterialTheme` nests *inside* the XML day/night theme,
/// so forcing the branch leaves the surrounding app chrome on the system
/// appearance; forcing it on iOS would drag the app-wide ``Palette`` along with
/// it.
struct ThesisExtractorThemeModifier: ViewModifier {

    @Environment(\.colorScheme) private var colorScheme

    /// `darkTheme = null` reproduces `isSystemInDarkTheme()`.
    let dark: Bool?

    func body(content: Content) -> some View {
        let scheme = dark.map { AppTheme.extractorScheme(dark: $0) }
            ?? .adaptive(for: colorScheme)

        content
            .environment(\.thesisExtractorScheme, scheme)
            .tint(scheme.primary)
            .background(scheme.background.ignoresSafeArea())
            .toolbarBackground(scheme.surface, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
    }
}

// MARK: - Call sites

extension View {

    /// Wraps a thesis / poster / PDF-extraction screen in the extractor theme.
    ///
    /// ```swift
    /// ExportThemeSelectionView()
    ///     .thesisExtractorTheme()
    /// ```
    ///
    /// - Parameter dark: Pass `true`/`false` where Android passed an explicit
    ///   `darkTheme` from a saved user preference; leave it `nil` where the
    ///   activity passed `isSystemInDarkTheme()`.
    func thesisExtractorTheme(dark: Bool? = nil) -> some View {
        modifier(ThesisExtractorThemeModifier(dark: dark))
    }
}