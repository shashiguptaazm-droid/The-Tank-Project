import SwiftUI

// Ports the Android resource types that are neither drawables in the asset
// catalog nor colour tokens in `Theme.swift`:
//
//   res/anim/*.xml     -> `Anim` + the `.shake()` modifier
//   res/color/*.xml    -> `NavigationTint`
//   res/menu/*.xml     -> `NavigationMenu`
//   res/values/strings -> `L10n`
//
// `res/dimens.xml` holds a single dimen (`bottom_nav_elevation`, 12dp), already
// represented by `AppTheme.Elevation.bottomNav`.

// MARK: - res/anim

/// `res/anim/pulse.xml` and `res/anim/shake.xml`.
enum Anim {

    /// `pulse.xml` — alpha 1.0 → 0.2, 800 ms, `repeatMode="reverse"` with an
    /// infinite repeat count. Used for in-progress/loading affordances.
    static let pulse = Animation.easeInOut(duration: 0.8).repeatForever(autoreverses: true)

    /// `shake.xml` — a 70 ms translate, repeated. Scale-free so it composes with
    /// the token below.
    static let shake = Animation.easeInOut(duration: 0.07)

    /// `pulse.xml`'s target alpha, for callers that animate opacity directly.
    static let pulseMinOpacity: Double = 0.2
}

/// Ports the `res/anim/shake.xml` `<translate>`: a horizontal wobble of ±5%,
/// which is the wrong-answer feedback on the quiz screen.
struct ShakeEffect: GeometryEffect {
    /// Peak horizontal travel. Android expresses `fromXDelta`/`toXDelta` as ±5%
    /// of the view width; pass a concrete value here.
    var travel: CGFloat = 10
    /// Number of full left/right oscillations.
    var shakes: CGFloat = 3
    var animatableData: CGFloat

    func effectValue(size: CGSize) -> ProjectionTransform {
        let dx = travel * sin(animatableData * .pi * 2 * shakes)
        return ProjectionTransform(CGAffineTransform(translationX: dx, y: 0))
    }
}

extension View {
    /// Runs the Android shake animation whenever `trigger` changes. Increment the
    /// trigger to replay it (for example on each wrong answer).
    func shake(trigger: Int, travel: CGFloat = 10, shakes: CGFloat = 3) -> some View {
        modifier(ShakeModifier(trigger: trigger, travel: travel, shakes: shakes))
    }
}

private struct ShakeModifier: ViewModifier {
    let trigger: Int
    let travel: CGFloat
    let shakes: CGFloat

    @State private var progress: CGFloat = 0

    func body(content: Content) -> some View {
        content
            .modifier(ShakeEffect(travel: travel, shakes: shakes, animatableData: progress))
            .onChange(of: trigger) { _ in
                // Reset without animation, then run the wobble once.
                progress = 0
                withAnimation(Anim.shake) { progress += 1 }
            }
    }
}

// MARK: - res/color

/// `res/color/bottom_nav_colors.xml` and `res/color/nav_item_color.xml`.
///
/// Both are `ColorStateList`s selecting the same three tints; iOS applies them
/// through `.tint(selected)` on the `TabView`, with the platform supplying the
/// unselected colour.
enum NavigationTint {
    /// `state_checked="true"` -> `@color/colorPrimary`.
    static let selected = AppTheme.Palette.primary
    /// Default -> `@color/colorOnSurface`.
    static let unselected = AppTheme.Palette.textPrimary
    /// `state_enabled="false"` -> the literal `#9E9E9E`.
    static let disabled = Color(hex: 0x9E9E9E)
}

// MARK: - res/menu

/// One `<item>` from an Android `res/menu/*.xml` file.
struct MenuEntry: Identifiable, Hashable {
    /// The `android:id`, e.g. `side_profile`.
    let id: String
    let title: String
    /// `nil` where the Android icon is a dead resource — `nav_logout` points at
    /// `@drawable/ic_logout`, which is an empty `<selector/>` and therefore never
    /// renders on Android either.
    let icon: AndroidAsset?
}

/// A titled `<item>` wrapping a nested `<menu>`, or the leading ungrouped list.
struct MenuSection: Identifiable, Hashable {
    /// `nil` for the leading ungrouped group in `sidebar_menu.xml`.
    let title: String?
    let entries: [MenuEntry]

    var id: String { title ?? "_root" }
}

/// The navigation-drawer menus. `sidebar_menu.xml` is the superset; the other
/// two are older variants still referenced by some activities.
enum NavigationMenu {

    /// `res/menu/sidebar_menu.xml`.
    static let sidebar: [MenuSection] = [
        MenuSection(title: nil, entries: [
            MenuEntry(id: "side_profile", title: "My Profile", icon: .ic_person),
            MenuEntry(id: "side_pdfs", title: "Shared Questions", icon: .ic_pdf_library),
            MenuEntry(id: "side_scores", title: "My Quizzes", icon: .ic_score),
        ]),
        MenuSection(title: "Preferences", entries: [
            MenuEntry(id: "side_settings", title: "Settings", icon: .ic_settings),
            MenuEntry(id: "side_contact", title: "Contact Us", icon: .ic_help),
            MenuEntry(id: "side_help", title: "Help & Support", icon: .ic_help),
            MenuEntry(id: "nav_logout", title: "Logout", icon: nil),
        ]),
    ]

    /// `res/menu/side_menu.xml`.
    static let side: [MenuSection] = [
        MenuSection(title: nil, entries: [
            MenuEntry(id: "side_profile", title: "My Profile", icon: .ic_person),
            MenuEntry(id: "side_pdfs", title: "Shared Questions", icon: .ic_pdf_library),
            MenuEntry(id: "side_scores", title: "My Quizzes", icon: .ic_score),
        ]),
        MenuSection(title: "Preferences", entries: [
            MenuEntry(id: "side_settings", title: "Settings", icon: .ic_settings),
            MenuEntry(id: "side_help", title: "Help & Support", icon: .ic_help),
        ]),
    ]

    /// `res/menu/drawer_menu.xml`.
    static let drawer: [MenuSection] = [
        MenuSection(title: nil, entries: [
            MenuEntry(id: "side_profile", title: "My Profile", icon: .ic_person),
            MenuEntry(id: "side_scores", title: "My Scores", icon: .ic_score),
            MenuEntry(id: "side_pdfs", title: "Study Materials", icon: .ic_description),
        ]),
        MenuSection(title: "Communicate", entries: [
            MenuEntry(id: "side_messenger", title: "Messenger", icon: .ic_send),
            MenuEntry(id: "side_settings", title: "Settings", icon: .ic_settings),
        ]),
        MenuSection(title: "Account", entries: [
            MenuEntry(id: "nav_logout", title: "Logout", icon: nil),
        ]),
    ]
}

// MARK: - res/values/strings.xml

/// `res/values/strings.xml`. The Android app hardcodes nearly all of its copy
/// inside the layout files; these four are the only externalised strings.
/// (`strings.xml` also declares seven `type="id"` items — view ids, not copy.)
enum L10n {
    /// `app_name`
    static let appName = "MediGyaan"
    /// `contact_us`
    static let contactUs = "Contact Us"
    /// `challenge_friends`
    static let challengeFriends = "Challenge Friends"
    /// `search_friends`
    static let searchFriends = "Search friends..."
}
