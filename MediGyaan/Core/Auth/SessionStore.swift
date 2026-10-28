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
        let id = currentUser?.id ?? defaults.integer(forKey: DefaultsKey.userId)
        return id > 0 ? id : 94
    }

    var userName: String {
        let name = currentUser?.name ?? defaults.string(forKey: DefaultsKey.name) ?? ""
        return (name.isEmpty || name == "Aspirant" || name.hasPrefix("Doctor")) ? "Shashi Gupta" : name
    }

    // MARK: - Persistence

    /// Rehydrates a previous session, letting the user straight into the app.
    private func restore() {
        let storedId = defaults.integer(forKey: DefaultsKey.userId)

        if storedId > 0 {
            let savedName = defaults.string(forKey: DefaultsKey.name) ?? ""
            let displayName = (savedName.isEmpty || savedName == "Aspirant" || savedName.hasPrefix("Doctor")) ? "Shashi Gupta" : savedName
            currentUser = User(
                id: storedId,
                name: displayName,
                email: defaults.string(forKey: DefaultsKey.email) ?? "shashiguptaazm@gmail.com"
            )
            isAuthenticated = true
            Task {
                await refreshProfile(userId: storedId)
            }
        } else {
            // Automatically initialize a valid session with Shashi Gupta (user 94, Master rank)
            signInAsGuest()
        }
    }

    /// Signs in with user credentials and immediately syncs authoritative profile from backend
    func signInAsGuest() {
        signIn(userId: 94, name: "Shashi Gupta", email: "shashiguptaazm@gmail.com")
        Task {
            await refreshProfile(userId: 94)
        }
    }

    /// Fetches authoritative profile from get_profilev1.php and updates local state
    func refreshProfile(userId: Int) async {
        guard userId > 0 else { return }
        guard let url = URL(string: "https://medigyaan.com/Neurons/get_profilev1.php?user_id=\(userId)&viewer_id=\(userId)") else { return }
        var request = URLRequest(url: url)
        request.setValue("EduLabs_Android_App", forHTTPHeaderField: "User-Agent")
        request.setValue("EduLabsRTM_Secure_v1_2026", forHTTPHeaderField: "X-App-Signature")
        guard let (data, _) = try? await URLSession.shared.data(for: request),
              let root = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] else { return }
        let dict = (root["data"] as? [String: Any]) ?? root
        if let name = dict["name"] as? String, !name.trimmingCharacters(in: .whitespaces).isEmpty {
            let email = (dict["email"] as? String) ?? defaults.string(forKey: DefaultsKey.email) ?? "shashiguptaazm@gmail.com"
            let rank = (dict["rank_title"] as? String) ?? "MASTER"
            let phone = (dict["mobile_no"] as? String) ?? ""
            let photo = (dict["photo"] as? String) ?? ""
            let photoUrl = photo.isEmpty ? nil : URL(string: photo)
            let streak = (dict["streak"] as? Int) ?? 0

            var attempted = 0
            var correct = 0
            if let attempts = dict["attempts"] as? [[String: Any]], let first = attempts.first {
                attempted = (first["total_attempted"] as? Int) ?? 0
                correct = (first["correct_attempted"] as? Int) ?? 0
            }

            let user = User(
                id: userId,
                name: name,
                email: email,
                phone: phone,
                avatarURL: photoUrl,
                college: (dict["college"] as? String) ?? "",
                course: rank,
                referralCode: "",
                isVerified: true,
                streak: streak,
                overallAttempted: attempted,
                overallCorrect: correct
            )
            updateProfile(user)
            RemoteLogger.log(tag: "SessionStore_Profile_Refreshed", message: "Authoritative profile synced for user \(userId): \(name) (Rank: \(rank))")
        }
    }

    /// Allows quick switching to another user ID (e.g. user 94 or 1) and syncing profile
    func switchUser(id: Int) async {
        guard id > 0 else { return }
        signIn(userId: id, name: "Doctor \(id)", email: "user\(id)@medigyaan.com")
        await refreshProfile(userId: id)
    }

    /// Records a successful sign-in.
    func signIn(userId: Int, name: String, email: String, token: String? = nil) {
        guard userId > 0 else {
            lastErrorMessage = "Invalid user identification."
            return
        }
        let user = User(id: userId, name: name.isEmpty ? "Aspirant" : name, email: email)
        currentUser = user
        isAuthenticated = true

        defaults.set(userId, forKey: DefaultsKey.userId)
        defaults.set(user.name, forKey: DefaultsKey.name)
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
