import SwiftUI

/// Root tab bar, porting `layout_navigation.xml` + `menu/bottom_nav_menu.xml`.
///
/// The Android bottom navigation is:
///
/// | id | title | icon |
/// |---|---|---|
/// | `nav_home` | Home | `ic_home` |
/// | `nav_reels` | Poster | `ic_comment` |
/// | `nav_search` | Search | `ic_search` |
/// | `nav_feed` | History | `ic_feed` |
/// | `nav_messages` | Messages | `ic_message` |
///
/// Tabs are *labelled* (`labelVisibilityMode="labeled"`) and tinted via
/// `@color/bottom_nav_colors`, with the bar painted `@color/colorSurface` and
/// elevated 12dp (`bottom_nav_elevation`).
struct AppTabView: View {

    enum Tab: Hashable, CaseIterable {
        case home
        case aiChat
        case search
        case history
        case messages

        /// Title exactly as declared in `bottom_nav_menu.xml`.
        var title: String {
            switch self {
            case .home: return "Home"
            case .aiChat: return "AI Chat"
            case .search: return "Search"
            case .history: return "History"
            case .messages: return "Messages"
            }
        }

        /// The exact vector drawable the Android menu item points at.
        var asset: AndroidAsset {
            switch self {
            case .home: return .ic_home
            case .aiChat: return .ic_comment
            case .search: return .ic_search
            case .history: return .ic_feed
            case .messages: return .ic_message
            }
        }

        /// SF Symbol equivalent, retained for contexts that cannot take an
        /// asset name (for example `Label` inside a `Menu`).
        var systemImage: String {
            switch self {
            case .home: return "house.fill"
            case .aiChat: return "bubble.left.and.bubble.right.fill"
            case .search: return "magnifyingglass"
            case .history: return "clock.arrow.circlepath"
            case .messages: return "bubble.left.and.bubble.right.fill"
            }
        }
    }

    @State private var selection: Tab = .home

    /// `BottomNavBar` is index-driven (`BottomNavBar.items` mirrors the menu
    /// order), so the enum selection is projected onto it in both directions.
    private var indexSelection: Binding<Int> {
        Binding(
            get: { Tab.allCases.firstIndex(of: selection) ?? 0 },
            set: { index in
                guard Tab.allCases.indices.contains(index) else { return }
                selection = Tab.allCases[index]
            }
        )
    }

    var body: some View {
        TabView(selection: $selection) {
            ForEach(Tab.allCases, id: \.self) { tab in
                destination(for: tab)
                    .tag(tab)
            }
        }
        .tint(AppTheme.Palette.primary)
        .safeAreaInset(edge: .bottom, spacing: 0) {
            BottomNavBar(selection: indexSelection)
        }
        .toolbar(.hidden, for: .tabBar)
        .onChange(of: selection) { newTab in
            RemoteLogger.log(tag: "Tab_Switch", message: "User selected tab: \(newTab.title)")
        }
    }

    /// Each tab maps to the Android activity that lived in the nav host.
    @ViewBuilder
    private func destination(for tab: Tab) -> some View {
        switch tab {
        case .home:
            DashboardView()
        case .aiChat:
            AiChatView()
        case .search:
            GlobalSearchView()
        case .history:
            NavigationStack { HistoryView() }
        case .messages:
            NavigationStack { MessengerView() }
        }
    }
}

#Preview {
    AppTabView()
        .environmentObject(SessionStore())
        .environment(\.api, .live)
}
