import SwiftUI

/// Design tokens ported 1:1 from the Android app's resources.
///
/// The Android UI is **not** built on a single palette. Two visual languages
/// coexist, and this file mirrors both faithfully rather than tidying them up:
///
/// * ``Palette`` — the Material 3 theme from `res/values/colors.xml` and
///   `res/values-night/colors.xml`. Used by login, leaderboard, profile and the
///   bottom navigation. Adapts to light/dark.
/// * ``Ink`` — the custom dark palette hardcoded throughout
///   `activity_dashboard.xml` (~148 literal hex values), also used by
///   `activity_test_mode.xml`, `activity_referral.xml`,
///   `activity_predict_college.xml`, and `activity_accuracy.xml`. Fixed
///   regardless of system appearance, exactly as on Android.
enum AppTheme {

    // MARK: - Material 3 theme (colors.xml / values-night/colors.xml)

    /// Appearance-adaptive colours matching Android's day/night `colors.xml`.
    enum Palette {

        static func adaptive(light: Color, dark: Color) -> Color {
            Color(UIColor { traits in
                traits.userInterfaceStyle == .dark ? UIColor(dark) : UIColor(light)
            })
        }

        // PRIMARY
        /// `colorPrimary` — #5C6BC0 day / #B8C0FF night.
        static let primary = adaptive(light: Color(hex: 0x5C6BC0), dark: Color(hex: 0xB8C0FF))
        /// `colorPrimaryVariant` — #3949AB day / #8C9EFF night.
        static let primaryVariant = adaptive(light: Color(hex: 0x3949AB), dark: Color(hex: 0x8C9EFF))
        /// `colorPrimaryContainer` — #E8EAF6 day / #2A325F night.
        static let primaryContainer = adaptive(light: Color(hex: 0xE8EAF6), dark: Color(hex: 0x2A325F))
        /// `colorOnPrimaryContainer` — #1A237E day / #E8EAF6 night.
        static let onPrimaryContainer = adaptive(light: Color(hex: 0x1A237E), dark: Color(hex: 0xE8EAF6))
        /// `colorOnPrimary` — #FFFFFF day / #0F1115 night.
        static let onPrimary = adaptive(light: Color(hex: 0xFFFFFF), dark: Color(hex: 0x0F1115))

        // SECONDARY
        /// `colorSecondary` — #FFD54F both appearances.
        static let secondary = Color(hex: 0xFFD54F)
        /// `colorSecondaryVariant` — #FFA000 day / #FFC107 night.
        static let secondaryVariant = adaptive(light: Color(hex: 0xFFA000), dark: Color(hex: 0xFFC107))
        /// `colorOnSecondary` — #212121 day / #0F1115 night.
        static let onSecondary = adaptive(light: Color(hex: 0x212121), dark: Color(hex: 0x0F1115))

        // BACKGROUND & SURFACE
        /// `colorBackground` — #F6F8FC day / #121212 night.
        static let background = adaptive(light: Color(hex: 0xF6F8FC), dark: Color(hex: 0x121212))
        /// `colorSurface` — #FFFFFF day / #1E1E1E night.
        static let surface = adaptive(light: Color(hex: 0xFFFFFF), dark: Color(hex: 0x1E1E1E))
        /// `card_bg` — #FFFFFF day / #242424 night.
        static let cardBackground = adaptive(light: Color(hex: 0xFFFFFF), dark: Color(hex: 0x242424))
        /// `colorOutline` — #D0D7E2 day / #4A4A4A night.
        static let outline = adaptive(light: Color(hex: 0xD0D7E2), dark: Color(hex: 0x4A4A4A))
        /// `divider` — #1F000000 day (12% black) / #383838 night.
        static let divider = adaptive(light: Color(hex: 0x1F000000), dark: Color(hex: 0x383838))

        // TEXT
        /// `colorOnBackground` — #1A1C2E day / #F5F5F5 night.
        static let textPrimary = adaptive(light: Color(hex: 0x1A1C2E), dark: Color(hex: 0xFFFFFF))
        /// `text_secondary` — #5F6368 day / #C7C7C7 night.
        static let textSecondary = adaptive(light: Color(hex: 0x5F6368), dark: Color(hex: 0xC7C7C7))

        /// `primary_dark` — #3949AB day / #5C6BC0 night.
        static let primaryDark = adaptive(light: Color(hex: 0x3949AB), dark: Color(hex: 0x5C6BC0))

        // STATUS
        /// `success` — #43A047 day / #81C784 night.
        static let success = adaptive(light: Color(hex: 0x43A047), dark: Color(hex: 0x81C784))
        /// `error` — #E53935 day / #EF5350 night.
        static let error = adaptive(light: Color(hex: 0xE53935), dark: Color(hex: 0xEF5350))
        /// `warning` — #FB8C00 day / #FFB74D night.
        static let warning = adaptive(light: Color(hex: 0xFB8C00), dark: Color(hex: 0xFFB74D))
        /// Alias of ``error`` for destructive affordances.
        static let danger = error
        /// Informational blue — #2196F3 day / #4FC3F7 night (matches
        /// `option_card_stroke_selected` and the dashboard icon accents).
        static let info = adaptive(light: Color(hex: 0x2196F3), dark: Color(hex: 0x4FC3F7))
        /// Alias of the primary green used by the newsletter/messenger accents.
        static let accent = adaptive(light: Color(hex: 0x00A884), dark: Color(hex: 0x48D6C8))

        // CHROME
        /// `toolbar_bg` — #FFFFFF day / #121212 night.
        static let toolbar = adaptive(light: Color(hex: 0xFFFFFF), dark: Color(hex: 0x121212))
        /// `bottom_nav_bg` — #FFFFFF day / #1A1A1A night.
        static let bottomNav = adaptive(light: Color(hex: 0xFFFFFF), dark: Color(hex: 0x1A1A1A))

        // WHATSAPP-COMPATIBLE MESSENGER PALETTE
        /// `whatsapp_chat_bg` — #E5DDD5 day / #0B141A night.
        static let chatBackground = adaptive(light: Color(hex: 0xE5DDD5), dark: Color(hex: 0x0B141A))
        /// `whatsapp_bubble_sent` — #D9FDD3 day / #005C4B night.
        static let bubbleSent = adaptive(light: Color(hex: 0xD9FDD3), dark: Color(hex: 0x005C4B))
        /// `whatsapp_bubble_received` — #FFFFFF day / #202C33 night.
        static let bubbleReceived = adaptive(light: Color(hex: 0xFFFFFF), dark: Color(hex: 0x202C33))
        /// `message_input_bg` — #F1F3F5 day / #1E2C33 night.
        static let messageInput = adaptive(light: Color(hex: 0xF1F3F5), dark: Color(hex: 0x1E2C33))

        // MCQ OPTION CARDS (option_card_* tokens)
        /// `option_card_bg_default` — #FFFFFF day / #1E2C33 night.
        static let optionBackground = adaptive(light: Color(hex: 0xFFFFFF), dark: Color(hex: 0x1E2C33))
        /// `option_card_stroke_default` — #E0E0E0 day / #303E46 night.
        static let optionStroke = adaptive(light: Color(hex: 0xE0E0E0), dark: Color(hex: 0x303E46))
        /// `option_card_bg_selected` — #E3F2FD day / #074439 night.
        static let optionSelectedBackground = adaptive(light: Color(hex: 0xE3F2FD), dark: Color(hex: 0x074439))
        /// `option_card_stroke_selected` — #2196F3 day / #00A884 night.
        static let optionSelectedStroke = adaptive(light: Color(hex: 0x2196F3), dark: Color(hex: 0x00A884))

        /// Subject grid accents, replacing the Android `subjectColors` literals.
        static let accents: [Color] = [
            Color(hex: 0x5C6BC0),
            Color(hex: 0x43A047),
            Color(hex: 0xFFA000),
            Color(hex: 0xE53935),
            Color(hex: 0x8E44AD),
            Color(hex: 0x00ACC1),
        ]

        static func accent(for index: Int) -> Color {
            guard !accents.isEmpty else { return primary }
            return accents[abs(index) % accents.count]
        }

        /// Legacy spelling of ``accent(for:)`` kept so existing call sites keep
        /// compiling; new code should use ``accent(for:)``.
        static func color(for index: Int) -> Color {
            accent(for: index)
        }
    }

    // MARK: - Dashboard "ink" palette
    //
    // Hardcoded in activity_dashboard.xml and friends. Intentionally NOT
    // adaptive: the Android dashboard is dark in both day and night mode.

    enum Ink {
        /// `#07111F` — screen background.
        static let background = Color(hex: 0x07111F)
        /// `#0D1A2B` — search field and stats card.
        static let surface = Color(hex: 0x0D1A2B)
        /// `#0C2036` — profile summary card.
        static let profileCard = Color(hex: 0x0C2036)
        /// `#132238` — quick-action tiles.
        static let tile = Color(hex: 0x132238)
        /// `#111A31` — rank / battle card.
        static let rankCard = Color(hex: 0x111A31)
        /// `#0F2429` — AI predicted rank inset.
        static let predictionCard = Color(hex: 0x0F2429)
        /// `#102F4A` — avatar backdrop.
        static let avatarBackdrop = Color(hex: 0x102F4A)
        /// `#253954` — generic elevated surface.
        static let elevated = Color(hex: 0x253954)

        /// `#48D6C8` — teal accent (messenger icon, search stroke, progress).
        static let teal = Color(hex: 0x48D6C8)
        /// `#F4C95D` — gold (XP text, avatar stroke, badges).
        static let gold = Color(hex: 0xF4C95D)
        /// `#2B80E7` — profile card stroke.
        static let blue = Color(hex: 0x2B80E7)
        /// `#2648D6` — ripple / deep blue.
        static let deepBlue = Color(hex: 0x2648D6)
        /// `#39537A` — rank card stroke.
        static let slate = Color(hex: 0x39537A)

        // TEXT
        /// `#F2F6FC` — primary text.
        static let textPrimary = Color(hex: 0xF2F6FC)
        /// `#9FB1C7` — secondary text.
        static let textSecondary = Color(hex: 0x9FB1C7)
        /// `#8FA3BD` — hint / search placeholder.
        static let textHint = Color(hex: 0x8FA3BD)
        /// `#B7C2D3` — tertiary text.
        static let textTertiary = Color(hex: 0xB7C2D3)
        /// `#DDE7F5` — top bar icon tint.
        static let iconTint = Color(hex: 0xDDE7F5)

        // STATUS
        /// `#62E49D` — success / correct.
        static let success = Color(hex: 0x62E49D)
        /// `#FF1744` — error / wrong.
        static let error = Color(hex: 0xFF1744)
        /// `#00E5FF` — cyan accent.
        static let cyan = Color(hex: 0x00E5FF)

        // BATTLE MODE CARDS (distinct tint per mode)
        /// `#251B45` — Ranked battle.
        static let ranked = Color(hex: 0x251B45)
        /// `#0F332C` — Challenge friends.
        static let friends = Color(hex: 0x0F332C)
        /// `#3C1820` — Rapid fire.
        static let rapidFire = Color(hex: 0x3C1820)
        /// `#15325A` — Test mode.
        static let testMode = Color(hex: 0x15325A)
        /// `#34240F` — Custom battle.
        static let custom = Color(hex: 0x34240F)

        // CARDS
        /// `#2B1B18` — daily streak card.
        static let streakCard = Color(hex: 0x2B1B18)
        /// `#2D2341` — challenge invitation card.
        static let invitation = Color(hex: 0x2D2341)
    }

    // MARK: - Corner radii (from themes.xml / layouts)

    /// Card corner radii, matching `AppMaterialCardView` (18dp) and
    /// `DashboardCardStyle` (20dp).
    enum Radius {
        /// 12dp — `option_selector_rounded` MCQ options.
        static let option: CGFloat = 12
        /// 14dp — dashboard search field.
        static let field: CGFloat = 14
        /// 16dp — dashboard rank / battle cards.
        static let card: CGFloat = 16
        /// 18dp — `AppMaterialCardView` default.
        static let materialCard: CGFloat = 18
        /// 20dp — `DashboardCardStyle`.
        static let dashboardCard: CGFloat = 20
        /// 24dp — `AppMaterialButton`.
        static let button: CGFloat = 24
        /// 26dp — `SubmitButtonStyle`.
        static let submitButton: CGFloat = 26
        /// 50% — circular avatars.
        static let pill: CGFloat = 999

        // Legacy scale retained for the screens not yet migrated to the exact
        // Android dp values above.
        /// 8dp
        static let sm: CGFloat = 8
        /// 14dp
        static let md: CGFloat = 14
        /// 20dp
        static let lg: CGFloat = 20
        /// 48dp
        static let xxlLegacy: CGFloat = 48
    }

    // MARK: - Spacing (dp values used across the layouts)

    enum Spacing {
        /// 4dp
        static let xxs: CGFloat = 4
        /// 6dp
        static let xs: CGFloat = 6
        /// 7dp — dashboard split-card gutter.
        static let split: CGFloat = 7
        /// 8dp
        static let sm: CGFloat = 8
        /// 14dp — dashboard card stacking gap.
        static let md: CGFloat = 14
        /// 16dp — screen padding, card padding.
        static let lg: CGFloat = 16
        /// 20dp — `activity_main` padding.
        static let xl: CGFloat = 20
        /// 24dp
        static let xxl: CGFloat = 24
    }

    // MARK: - Typography (sp values used across the layouts)

    enum Font {
        /// 34sp bold — screen titles (splash, login header).
        static let largeTitle = SwiftUI.Font.system(size: 34, weight: .bold)
        /// 34sp — dashboard badge emoji.
        static let display = SwiftUI.Font.system(size: 34, weight: .bold)
        /// 22sp bold — dashboard user name.
        static let title = SwiftUI.Font.system(size: 22, weight: .bold)
        /// 22sp — dashboard stat values.
        static let statValue = SwiftUI.Font.system(size: 22, weight: .bold, design: .rounded)
        /// 21sp — AI predicted rank value.
        static let prediction = SwiftUI.Font.system(size: 21, weight: .bold, design: .rounded)
        /// 20sp — battle mode card titles.
        static let headline = SwiftUI.Font.system(size: 20, weight: .bold)
        /// 18sp — section headers ("Battle Modes ⚔️").
        static let section = SwiftUI.Font.system(size: 18, weight: .bold)
        /// 16sp — body copy.
        static let body = SwiftUI.Font.system(size: 16)
        /// 15sp — `DashboardCardTextStyle`.
        static let cardTitle = SwiftUI.Font.system(size: 15, weight: .bold)
        /// 14sp — invitation titles.
        static let callout = SwiftUI.Font.system(size: 14, weight: .medium)
        /// 13sp — dashboard streak line.
        static let subheadline = SwiftUI.Font.system(size: 13)
        /// 12sp — labels and captions.
        static let caption = SwiftUI.Font.system(size: 12)
        /// 12sp bold — XP text and mode tags.
        static let captionBold = SwiftUI.Font.system(size: 12, weight: .bold)
        /// 11sp — stat tile labels.
        static let micro = SwiftUI.Font.system(size: 11)
        /// Legacy spelling of ``micro``.
        static let statLabel = micro
    }

    // MARK: - Elevation

    enum Elevation {
        /// 2dp — default card shadow radius.
        static let card: CGFloat = 2
        /// 3dp — dashboard cards.
        static let dashboardCard: CGFloat = 3
        /// 12dp — bottom navigation elevation.
        static let bottomNav: CGFloat = 12
    }
}

// MARK: - Hex colour support

extension Color {
    /// Builds a colour from a packed `0xRRGGBB` / `0xAARRGGBB` literal, or from
    /// a `#RRGGBB` string. Topic colours arrive as hex strings from the backend.
    init(hex: UInt64) {
        let hasAlpha = hex > 0xFFFFFF
        let a: Double = hasAlpha ? Double((hex & 0xFF00_0000) >> 24) / 255 : 1
        let r: Double = Double((hex & 0x00FF_0000) >> 16) / 255
        let g: Double = Double((hex & 0x0000_FF00) >> 8) / 255
        let b: Double = Double(hex & 0x0000_00FF) / 255
        self.init(.sRGB, red: r, green: g, blue: b, opacity: a)
    }

    /// Fallback for hex strings coming from the backend.
    init(hex string: String, fallback: Color = AppTheme.Palette.primary) {
        var cleaned = string.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        if cleaned.hasPrefix("#") { cleaned.removeFirst() }
        guard cleaned.count == 6 || cleaned.count == 8, let value = UInt64(cleaned, radix: 16) else {
            self = fallback
            return
        }
        // 6 digits is RRGGBB, 8 is AARRGGBB — both handled by the packed init.
        self.init(hex: value)
    }
}
