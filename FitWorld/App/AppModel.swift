import SwiftUI
import Observation

/// Central app-wide model. Holds cross-feature state and service handles.
@Observable
final class AppModel {
    let theme = Theme()
    let profileStore: ProfileStore
    let contentStore: ContentStore
    let authService: AuthService

    var showOnboarding: Bool

    init() {
        let bundleSeed = BundledContentLoader(bundle: .main)
        self.contentStore = ContentStore(loader: bundleSeed)
        let keychain = KeychainTokenStore()
        self.authService = AuthService(apiClient: APIClient(baseURL: APIConfig.baseURL,
                                                           tokenStore: keychain),
                                       tokenStore: keychain)
        self.profileStore = ProfileStore()
        // Show onboarding until a profile has been created at least once.
        self.showOnboarding = !profileStore.hasCompletedOnboarding
        self.sessionStore = nil // created on main actor in bootstrap()
    }

    private(set) var sessionStore: SessionStore?

    /// Called once from the root view's .task (main actor): load bundled seed
    /// content and create the SwiftData session container.
    func bootstrap() {
        if !exercisesLoaded {
            try? contentStore.loadBundledContent()
            exercisesLoaded = true
        }
        if sessionStore == nil, let container = try? SessionStore.makeContainer() {
            let store = SessionStore(container: container)
            store.prime()
            sessionStore = store
        }
    }

    private var exercisesLoaded = false

    func completeOnboarding() {
        profileStore.markOnboardingComplete()
        showOnboarding = false
    }

    func resetOnboarding() {
        showOnboarding = true
    }
}
