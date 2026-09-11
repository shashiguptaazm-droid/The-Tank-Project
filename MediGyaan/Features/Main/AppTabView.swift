import SwiftUI

/// Root tab bar, porting `layout_navigation.xml` + `menu/bottom_nav_menu.xml`.
///
/// The Android bottom navigation is:
///
/// | id | title | icon |
/// |---|---|---|
/// | `nav_home` | Home | `ic_home` |
/// | `nav_reels` | Poster | `ic_description` |
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
        case poster
        case search
        case history
        case messages

        /// Title exactly as declared in `bottom_nav_menu.xml`.
        var title: String {
            switch self {
            case .home: return "Home"
            case .poster: return "Poster"
            case .search: return "Search"
            case .history: return "History"
            case .messages: return "Messages"
            }
        }

        /// SF Symbol closest to the Android drawable.
        var systemImage: String {
            switch self {
            case .home: return "house.fill"                 // ic_home
            case .poster: return "doc.text.image"           // ic_description
            case .search: return "magnifyingglass"          // ic_search
            case .history: return "clock.arrow.circlepath"  // ic_feed
            case .messages: return "bubble.left.and.bubble.right.fill" // ic_message
            }
        }
    }

    @State private var selection: Tab = .home

    var body: some View {
        TabView(selection: $selection) {
            ForEach(Tab.allCases, id: \.self) { tab in
                destination(for: tab)
                    .tag(tab)
                    .tabItem {
                        Label(tab.title, systemImage: tab.systemImage)
                    }
            }
        }
        .tint(AppTheme.Palette.primary)
    }

    /// Each tab maps to the Android activity that lived in the nav host.
    ///
    /// `DashboardView`, `PosterStudioView` and `GlobalSearchView` own their
    /// navigation stacks; the history and messenger screens are also pushed from
    /// the dashboard, so they deliberately do not, and get one here instead.
    @ViewBuilder
    private func destination(for tab: Tab) -> some View {
        switch tab {
        case .home:
            DashboardView()
        case .poster:
            PosterStudioView()
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
