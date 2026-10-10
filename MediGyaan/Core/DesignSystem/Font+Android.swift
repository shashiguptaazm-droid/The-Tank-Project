import SwiftUI

extension AppTheme.Font {

    /// Material 3 typography ported from the Android `ui/theme/Type.kt`.
    ///
    /// `Type.kt` is 34 lines long and overrides exactly one slot — `bodyLarge`
    /// (16sp, Normal, 24sp line height, 0.5sp letter spacing) — while carrying
    /// `titleLarge` and `labelSmall` as commented-out templates. Every other
    /// slot therefore resolves to the Material 3 baseline scale baked into
    /// `androidx.compose.material3.Typography`, which is what the Android app
    /// actually renders. Both groups are transcribed below and each doc comment
    /// says which group a slot came from, so a baseline value is never mistaken
    /// for one `Type.kt` states outright.
    ///
    /// These tokens are namespaced under `Android` instead of sitting beside the
    /// layout-derived tokens in ``AppTheme/Font``: that enum is sourced from the
    /// XML layouts and `res/values`, this one from the Compose theme, and the
    /// two sets must not collide.
    ///
    /// `FontFamily.Default` is Roboto on Android. The app ships no `res/font`
    /// directory, so there is no custom family to bundle — these use the iOS
    /// system face (SF Pro), which occupies the same neutral grotesque slot and
    /// is what every other token in this design system already uses.
    ///
    /// Sp values are transcribed as points, per the project-wide 1sp ≈ 1pt
    /// mapping. Compose's `letterSpacing` is absolute (sp), not a ratio of the
    /// font size, so it is carried verbatim rather than converted to em.
    enum Android {

        /// One ported Compose `TextStyle`: the four values `TextStyle` carries.
        ///
        /// `SwiftUI.Font` has no line-height slot, so line height lives here and
        /// is applied by ``SwiftUI/View/androidMaterialType(_:)``.
        struct TextStyleToken {

            /// `fontSize`, in points.
            let size: CGFloat
            /// `fontWeight`.
            let weight: SwiftUI.Font.Weight
            /// `lineHeight`, in points.
            let lineHeight: CGFloat
            /// `letterSpacing`, in points.
            let tracking: CGFloat

            init(size: CGFloat, weight: SwiftUI.Font.Weight, lineHeight: CGFloat, tracking: CGFloat) {
                self.size = size
                self.weight = weight
                self.lineHeight = lineHeight
                self.tracking = tracking
            }

            /// The `Font` half of the style. Letter spacing is not part of
            /// `Font` in SwiftUI — it is a `View` modifier, so `tracking` is
            /// applied by ``SwiftUI/View/androidMaterialType(_:)`` instead.
            var font: SwiftUI.Font {
                SwiftUI.Font.system(size: size, weight: weight, design: .default)
            }

            /// Extra leading SwiftUI needs to reach Android's `lineHeight`.
            ///
            /// `lineSpacing` adds to SwiftUI's own implicit leading rather than
            /// setting an absolute line height, so the default is approximated as
            /// 1.2× the point size. Exact parity is not reachable through
            /// `Font` alone.
            var lineSpacing: CGFloat {
                max(0, lineHeight - size * 1.2)
            }
        }

        // MARK: - Slots stated by Type.kt

        /// Ports `Type.kt` `bodyLarge` — 16sp, Normal, 24sp line height,
        /// 0.5sp letter spacing. The one slot `Type.kt` actually overrides.
        static let bodyLarge = TextStyleToken(size: 16, weight: .regular, lineHeight: 24, tracking: 0.5)

        /// Ports `Type.kt` `titleLarge` — 22sp, Normal, 28sp line height,
        /// 0.sp letter spacing. Commented out in the Kotlin source and identical
        /// to the M3 baseline, so it is retained as a template, not an override.
        static let titleLarge = TextStyleToken(size: 22, weight: .regular, lineHeight: 28, tracking: 0)

        /// Ports `Type.kt` `labelSmall` — 11sp, Medium, 16sp line height,
        /// 0.5sp letter spacing. Also commented out in the Kotlin source and
        /// identical to the M3 baseline.
        static let labelSmall = TextStyleToken(size: 11, weight: .medium, lineHeight: 16, tracking: 0.5)

        // MARK: - Material 3 baseline (not overridden in Type.kt)

        /// M3 `displayLarge` — 57sp, Normal, 64sp line height, -0.25sp tracking.
        static let displayLarge = TextStyleToken(size: 57, weight: .regular, lineHeight: 64, tracking: -0.25)

        /// M3 `displayMedium` — 45sp, Normal, 52sp line height, 0sp tracking.
        static let displayMedium = TextStyleToken(size: 45, weight: .regular, lineHeight: 52, tracking: 0)

        /// M3 `displaySmall` — 36sp, Normal, 44sp line height, 0sp tracking.
        static let displaySmall = TextStyleToken(size: 36, weight: .regular, lineHeight: 44, tracking: 0)

        /// M3 `headlineLarge` — 32sp, Normal, 40sp line height, 0sp tracking.
        static let headlineLarge = TextStyleToken(size: 32, weight: .regular, lineHeight: 40, tracking: 0)

        /// M3 `headlineMedium` — 28sp, Normal, 36sp line height, 0sp tracking.
        static let headlineMedium = TextStyleToken(size: 28, weight: .regular, lineHeight: 36, tracking: 0)

        /// M3 `headlineSmall` — 24sp, Normal, 32sp line height, 0sp tracking.
        static let headlineSmall = TextStyleToken(size: 24, weight: .regular, lineHeight: 32, tracking: 0)

        /// M3 `titleMedium` — 16sp, Medium, 24sp line height, 0.15sp tracking.
        static let titleMedium = TextStyleToken(size: 16, weight: .medium, lineHeight: 24, tracking: 0.15)

        /// M3 `titleSmall` — 14sp, Medium, 20sp line height, 0.1sp tracking.
        static let titleSmall = TextStyleToken(size: 14, weight: .medium, lineHeight: 20, tracking: 0.1)

        /// M3 `bodyMedium` — 14sp, Normal, 20sp line height, 0.25sp tracking.
        static let bodyMedium = TextStyleToken(size: 14, weight: .regular, lineHeight: 20, tracking: 0.25)

        /// M3 `bodySmall` — 12sp, Normal, 16sp line height, 0.4sp tracking.
        static let bodySmall = TextStyleToken(size: 12, weight: .regular, lineHeight: 16, tracking: 0.4)

        /// M3 `labelLarge` — 14sp, Medium, 20sp line height, 0.1sp tracking.
        static let labelLarge = TextStyleToken(size: 14, weight: .medium, lineHeight: 20, tracking: 0.1)

        /// M3 `labelMedium` — 12sp, Medium, 16sp line height, 0.5sp tracking.
        static let labelMedium = TextStyleToken(size: 12, weight: .medium, lineHeight: 16, tracking: 0.5)
    }
}

extension View {

    /// Applies a ported Material 3 text style, including the Android
    /// `lineHeight` that `SwiftUI.Font` cannot express on its own.
    ///
    /// Android resolves its styles through `MaterialTheme.typography`; on iOS the
    /// equivalent is `.font(style.font)` plus the token's `lineSpacing` and
    /// `tracking`, which SwiftUI exposes as `View` modifiers rather than
    /// `Font` members.
    func androidMaterialType(_ style: AppTheme.Font.Android.TextStyleToken) -> some View {
        font(style.font)
            .lineSpacing(style.lineSpacing)
            .tracking(style.tracking)
    }
}