import SwiftUI

@main
struct FitWorldApp: App {
    @State private var appModel = AppModel()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(appModel)
                .environment(appModel.theme)
                .environment(appModel.profileStore)
                .environment(appModel.contentStore)
                .tint(appModel.theme.accent)
        }
    }
}
