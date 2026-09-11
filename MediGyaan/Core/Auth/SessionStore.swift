import Foundation

/// App-wide authentication state.
///
/// Replaces the Android pattern of writing `user_id`/`name`/`email` straight
/// into `SharedPreferences`: the token lives in the Keychain, and the
/// non-sensitive profile fields are mirrored to `UserDefaults` so the UI can
/// render immediately on launch.
@MainActor
final class SessionStore: ObservableObject {

    @Published private(set) var currentUser: User?
    @Published private(set) var isAuthenticated: Bool = false
    @Published var lastErrorMessage: String?

    private let secretStore: SecretStore
    private let defaults: UserDefaults

    private enum DefaultsKey {
        static let userId = "mg.user_id"
        static let name = "mg.name"
        static let email = "mg.email"
    }

    init(secretStore: SecretStore = KeychainStore.shared, defaults: UserDefaults = .standard) {
        self.secretStore = secretStore
        self.defaults = defaults
        restore()
    }

    /// Token sent as a bearer header on authenticated requests.
    ///
    /// `nil` is expected on an unsigned simulator build, where the Keychain is
    /// unavailable; the app tolerates that because the backend authenticates on
    /// `user_id` rather than a bearer token.
    var authToken: String? {
        secretStore.get(.authToken)
    }

    var userId: Int {
        currentUser?.id ?? 0
    }

    // MARK: - Persistence

    /// Rehydrates a previous session, letting the user straight into the app.
    private func restore() {
        let token = secretStore.get(.authToken)
        let storedId = defaults.integer(forKey: DefaultsKey.userId)

        guard token?.isEmpty == false || storedId > 0 else {
            isAuthenticated = false
            return
        }

        currentUser = User(
            id: storedId,
            name: defaults.string(forKey: DefaultsKey.name) ?? "",
            email: defaults.string(forKey: DefaultsKey.email) ?? ""
        )
        isAuthenticated = storedId > 0
    }

    /// Records a successful sign-in.
    func signIn(userId: Int, name: String, email: String, token: String? = nil) {
        let user = User(id: userId, name: name, email: email)
        currentUser = user
        isAuthenticated = userId > 0

        defaults.set(userId, forKey: DefaultsKey.userId)
        defaults.set(name, forKey: DefaultsKey.name)
        defaults.set(email, forKey: DefaultsKey.email)

        if let token, !token.isEmpty {
            secretStore.set(token, for: .authToken)
        }
        secretStore.set(String(userId), for: .userId)
        secretStore.set(email, for: .email)
    }

    /// Replaces the cached profile after a `get_profilev1.php` refresh.
    func updateProfile(_ user: User) {
        currentUser = user
        defaults.set(user.id, forKey: DefaultsKey.userId)
        defaults.set(user.name, forKey: DefaultsKey.name)
        defaults.set(user.email, forKey: DefaultsKey.email)
    }

    /// Clears every trace of the session.
    func signOut() {
        currentUser = nil
        isAuthenticated = false
        lastErrorMessage = nil

        defaults.removeObject(forKey: DefaultsKey.userId)
        defaults.removeObject(forKey: DefaultsKey.name)
        defaults.removeObject(forKey: DefaultsKey.email)
        secretStore.removeAll()
    }

    /// Stores the Firebase-style push token reported to `api/update_fcmv2.php`.
    func storePushToken(_ token: String) {
        secretStore.set(token, for: .fcmToken)
    }

    var pushToken: String? {
        secretStore.get(.fcmToken)
    }
}
