import SwiftUI

extension AppTheme {

    /// The Thesis Extractor's own Material 3 palette, ported verbatim from the
    /// Android `ui/theme/ThesisExtractorTheme.kt`.
    ///
    /// This is a **second, independent** scheme rather than a variant of
    /// ``Palette``: the Android extractor wraps its subtree in its own
    /// `MaterialTheme(ThesisExtractorTheme)`, so the thesis screens render in a
    /// blue/teal/plum palette that shares no colour with the indigo/amber app
    /// theme. Merging the two would recolour the thesis screens away from the
    /// Android design, so the palettes stay split — exactly as upstream.
    ///
    /// Android pairs the scheme with the shared `Typography`; on iOS that is
    /// ``AppTheme/Font``.
    enum ExtractorPalette {

        /// Resolves a colour from its day/night pair.
        static func adaptive(light: Color, dark: Color) -> Color {
            Palette.adaptive(light: light, dark: dark)
        }

        // MARK: Primary

        /// `#0F5B92` day / `#8DB7FF` night.
        static let primary = adaptive(light: Color(hex: 0x0F5B92), dark: Color(hex: 0x8DB7FF))
        /// `#FFFFFF` day / `#00325B` night.
        static let onPrimary = adaptive(light: Color(hex: 0xFFFFFF), dark: Color(hex: 0x00325B))
        /// `#D0E4FF` day / `#174A79` night.
        static let primaryContainer = adaptive(light: Color(hex: 0xD0E4FF), dark: Color(hex: 0x174A79))
        /// `#001D33` day / `#D4E3FF` night.
        static let onPrimaryContainer = adaptive(light: Color(hex: 0x001D33), dark: Color(hex: 0xD4E3FF))

        // MARK: Secondary

        /// `#2F6B5C` day / `#93D5C2` night.
        static let secondary = adaptive(light: Color(hex: 0x2F6B5C), dark: Color(hex: 0x93D5C2))
        /// `#FFFFFF` day / `#00382D` night.
        static let onSecondary = adaptive(light: Color(hex: 0xFFFFFF), dark: Color(hex: 0x00382D))
        /// `#B3E7D5` day / `#1D5145` night.
        static let secondaryContainer = adaptive(light: Color(hex: 0xB3E7D5), dark: Color(hex: 0x1D5145))
        /// `#002018` day / `#AFEEDC` night.
        static let onSecondaryContainer = adaptive(light: Color(hex: 0x002018), dark: Color(hex: 0xAFEEDC))

        // MARK: Tertiary

        /// `#8B4A63` day / `#E7B6CC` night.
        static let tertiary = adaptive(light: Color(hex: 0x8B4A63), dark: Color(hex: 0xE7B6CC))
        /// `#FFFFFF` day / `#492435` night.
        static let onTertiary = adaptive(light: Color(hex: 0xFFFFFF), dark: Color(hex: 0x492435))

        // MARK: Background & surface

        /// `#F7F9FC` day / `#101417` night.
        static let background = adaptive(light: Color(hex: 0xF7F9FC), dark: Color(hex: 0x101417))
        /// `#181C20` day / `#E0E3E7` night.
        static let onBackground = adaptive(light: Color(hex: 0x181C20), dark: Color(hex: 0xE0E3E7))
        /// `#FFFFFF` day / `#181C20` night.
        static let surface = adaptive(light: Color(hex: 0xFFFFFF), dark: Color(hex: 0x181C20))
        /// `#181C20` day / `#E0E3E7` night.
        static let onSurface = adaptive(light: Color(hex: 0x181C20), dark: Color(hex: 0xE0E3E7))
        /// `#E0E7EF` day / `#40484F` night.
        static let surfaceVariant = adaptive(light: Color(hex: 0xE0E7EF), dark: Color(hex: 0x40484F))
        /// `#40484F` day / `#C0C7CE` night.
        static let onSurfaceVariant = adaptive(light: Color(hex: 0x40484F), dark: Color(hex: 0xC0C7CE))

        // MARK: Outline

        /// `#70787F` day / `#8A9299` night.
        static let outline = adaptive(light: Color(hex: 0x70787F), dark: Color(hex: 0x8A9299))
        /// `#C0C7CE` day / `#40484F` night.
        static let outlineVariant = adaptive(light: Color(hex: 0xC0C7CE), dark: Color(hex: 0x40484F))

        // MARK: Error

        /// `#BA1A1A` day / `#FFB4AB` night.
        static let error = adaptive(light: Color(hex: 0xBA1A1A), dark: Color(hex: 0xFFB4AB))
        /// `#FFFFFF` day / `#690005` night.
        static let onError = adaptive(light: Color(hex: 0xFFFFFF), dark: Color(hex: 0x690005))
    }
}