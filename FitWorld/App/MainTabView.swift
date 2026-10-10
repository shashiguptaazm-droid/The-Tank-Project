import SwiftUI

/// Main navigation shell with the four primary tabs.
struct MainTabView: View {
    @Environment(AppModel.self) private var app

    var body: some View {
        TabView {
            HomeView()
                .tabItem { Label("Home", systemImage: "house.fill") }

            TrainView()
                .tabItem { Label("Train", systemImage: "figure.run") }

            LibraryView()
                .tabItem { Label("Library", systemImage: "books.vertical.fill") }

            MeView()
                .tabItem { Label("Me", systemImage: "person.crop.circle.fill") }
        }
    }
}
