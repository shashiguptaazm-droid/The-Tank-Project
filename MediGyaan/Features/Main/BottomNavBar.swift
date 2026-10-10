import SwiftUI

/// Ports `AppBottomNavigation`: the labelled five-item bottom bar, its per-item
/// drawables and colour states, the ripple feedback, the 12dp elevation, and the
/// distinct "reselect" callback Android wires to re-launching the target
/// activity.
///
/// Ported from `AppBottomNavigation.kt` together with `layout_navigation.xml`
/// and `menu/bottom_nav_menu.xml`.
///
/// | id | title | icon | Android id |
/// |---|---|---|---|
/// | 0 | Home | `ic_home` | `nav_home` |
/// | 1 | AI Chat | `ic_comment` | `nav_reels` |
/// | 2 | Search | `ic_search` | `nav_search` |
/// | 3 | History | `ic_feed` | `nav_feed` |
/// | 4 | Messages | `ic_message` | `nav_messages` |
///
/// Styling carried across verbatim:
///
/// * `labelVisibilityMode = LABEL_VISIBILITY_LABELED` — icon and caption are
///   always visible, never the collapsing M3 variant.
/// * `isItemHorizontalTranslationEnabled = false` — items do not shift sideways
///   as the selection moves; only the active indicator travels.
/// * `itemIconTint` / `itemTextColor` = `@color/bottom_nav_colors`, surfaced as
///   ``NavigationTint``: `colorPrimary` when checked, `colorOnSurface` by
///   default, literal `#9E9E9E` when disabled.
/// * `itemRippleColor` = `@color/bottom_nav_ripple` (`#335C6BC0`, 20% primary).
/// * `background` = `@color/colorSurface`, `elevation` = 12dp.
/// * `fitsSystemWindows = true` + a `navigationBars` inset on the bottom
///   padding: the fill runs under the home indicator while the items stay
///   clear of it. Achieved with `ignoresSafeArea(edges: .bottom)` on the fill.
///
/// `AppBottomNavigation.selectedItemIdFor(activity)` — the 30-way table mapping
/// every Android activity back onto its owning nav item — has no SwiftUI
/// counterpart: iOS keeps the selection inside `TabView`, and pushed screens
/// inherit the tab they were pushed from.
public struct BottomNavBar: View {

    /// One `<item>` from `res/menu/bottom_nav_menu.xml`.
    public struct Item: Identifiable, Hashable {
        /// The item's position, used as `selection`.
        public let id: Int
        /// `android:title`.
        public let title: String
        /// `android:icon`, as a ported drawable.
        public let asset: AndroidAsset
        /// The `state_enabled="false"` arm of `bottom_nav_colors`. No menu item
        /// ships disabled, but hosts that gate a tab (locked, offline, or
        /// feature-flagged) can use it.
        public var isEnabled: Bool

        public init(id: Int, title: String, asset: AndroidAsset, isEnabled: Bool = true) {
            self.id = id
            self.title = title
            self.asset = asset
            self.isEnabled = isEnabled
        }
    }

    /// `res/menu/bottom_nav_menu.xml`, in declaration order. Indices match
    /// `AppTabView.Tab.allCases` so `selection` can be wired straight to a
    /// `TabView` tag.
    public static let items: [Item] = [
        Item(id: 0, title: "Home", asset: .ic_home),
        Item(id: 1, title: "AI Chat", asset: .ic_comment),
        Item(id: 2, title: "Search", asset: .ic_search),
        Item(id: 3, title: "History", asset: .ic_feed),
        Item(id: 4, title: "Messages", asset: .ic_message),
    ]

    /// Material 3 `NavigationBar` active indicator, 64 x 32dp.
    private static let indicatorWidth: CGFloat = 64
    private static let indicatorHeight: CGFloat = 32
    /// Android's own bar is 80dp tall with `labelVisibilityMode="labeled"`.
    private static let barHeight: CGFloat = 80
    private static let indicatorID = "bottomNavIndicator"

    /// Index into ``items``.
    @Binding private var selection: Int
    /// `setOnItemReselectedListener` — fired when the already-selected item is
    /// tapped again. Android re-launches the target activity here; iOS hosts
    /// typically scroll their list to top or pop to root instead.
    private let onReselect: (Int) -> Void

    @Namespace private var indicator

    public init(selection: Binding<Int>, onReselect: @escaping (Int) -> Void = { _ in }) {
        self._selection = selection
        self.onReselect = onReselect
    }

    /// Android resolves the checked item defensively (`findItem(...) != null`)
    /// and falls back to `0` when the caller's id matches nothing. Anything not
    /// in the menu renders as "nothing selected".
    private var selectedId: Int {
        items.contains { $0.id == selection.wrappedValue } ? selection.wrappedValue : -1
    }

    public var body: some View {
        HStack(spacing: 0) {
            ForEach(BottomNavBar.items) { item in
                button(for: item)
            }
        }
        .frame(height: Self.barHeight)
        .padding(.top, AppTheme.Spacing.xs)
        .background(
            AppTheme.Palette.surface
                .ignoresSafeArea(edges: .bottom)
        )
        .shadow(
            color: .black.opacity(0.08),
            radius: AppTheme.Elevation.bottomNav,
            y: AppTheme.Spacing.xxs
        )
    }

    // MARK: - Item

    private func button(for item: Item) -> some View {
        let isSelected = item.id == selectedId

        return Button {
            handleTap(item)
        } label: {
            VStack(spacing: AppTheme.Spacing.xxs) {
                ZStack {
                    if isSelected {
                        Capsule()
                            .fill(AppTheme.Palette.primary.opacity(0.12))
                            .frame(width: Self.indicatorWidth, height: Self.indicatorHeight)
                            .matchedGeometryEffect(id: Self.indicatorID, in: indicator)
                    }
                    AndroidIcon(item.asset, size: 24, tint: tint(for: item))
                }
                .frame(height: Self.indicatorHeight)

                Text(item.title)
                    .font(labelFont(isSelected: isSelected))
                    .foregroundStyle(tint(for: item))
                    .lineLimit(1)
                    .minimumScaleFactor(0.8)
            }
            .frame(maxWidth: .infinity)
            .contentShape(Rectangle())
        }
        .buttonStyle(BottomNavRippleStyle())
        .disabled(!item.isEnabled)
        .opacity(item.isEnabled ? 1 : 0.6)
        .accessibilityLabel(item.title)
        .accessibilityAddTraits(
            isSelected ? AccessibilityTraits.isSelected : AccessibilityTraits()
        )
    }

    /// `state_checked` -> `colorPrimary`, default -> `colorOnSurface`,
    /// `state_enabled="false"` -> `#9E9E9E`.
    private func tint(for item: Item) -> Color {
        if !item.isEnabled { return NavigationTint.disabled }
        return item.id == selectedId ? NavigationTint.selected : NavigationTint.unselected
    }

    private func labelFont(isSelected: Bool) -> Font {
        isSelected
            ? AppTheme.Font.caption.weight(.medium)
            : AppTheme.Font.caption
    }

    /// `setOnItemSelectedListener` returns early when the item is already
    /// checked, so the two listeners never both fire for one tap.
    private func handleTap(_ item: Item) {
        if item.id == selectedId {
            onReselect(item.id)
            return
        }
        withAnimation(.easeInOut(duration: 0.2)) {
            selection.wrappedValue = item.id
        }
    }
}

/// `app:itemRippleColor="@color/bottom_nav_ripple"` — `#335C6BC0`, i.e. 20%
/// of `colorPrimary`. Material's unbounded ripple has no SwiftUI analogue, so
/// this is the pressed-state wash behind the whole item.
private struct BottomNavRippleStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .background(
                RoundedRectangle(
                    cornerRadius: AppTheme.Radius.card,
                    style: .continuous
                )
                .fill(AppTheme.Palette.primary.opacity(configuration.isPressed ? 0.20 : 0))
            )
            .animation(.easeOut(duration: 0.12), value: configuration.isPressed)
    }
}

#Preview {
    BottomNavBarPreview()
}

private struct BottomNavBarPreview: View {
    @State private var selection = 0

    var body: some View {
        VStack {
            Spacer()
            BottomNavBar(selection: $selection) { index in
                print("reselected tab \(index)")
            }
        }
    }
}