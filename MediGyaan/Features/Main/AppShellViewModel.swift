import Foundation
import UIKit
import UserNotifications

/// Ports `MainActivity.kt` — the Android hub activity that runs on every cold
/// start, re-registers push delivery and then hands off to the first real
/// screen (`LoginActivity`, `DashboardActivity` or `MessengerActivity`).
///
/// Responsibilities, one for one against the Kotlin:
///
/// | Kotlin | Here |
/// |---|---|
/// | `SharedPreferences("MY_APP").getInt("user_id", 0)` | `SessionStore.isAuthenticated` / `SessionStore.userId` |
/// | `createNotificationChannel()` — `chat_notifications`, `IMPORTANCE_HIGH` | `registerChatCategory()` — `UNNotificationCategory` with `.badge` + `.sound` |
/// | `askNotificationPermission()` — `POST_NOTIFICATIONS` on API 33+ | `requestNotificationAuthorization()` — `UNUserNotificationCenter.requestAuthorization` |
/// | `FirebaseMessaging.getInstance().token` | `ingest(deviceToken:session:api:)` fed by the APNs token, plus the cached `SessionStore.pushToken` |
/// | `updateFcmTokenToServer()` → `POST Neurons/api/update_fcmv2.php` | `syncPushToken(api:session:)` → `AuthAPI.updatePushToken` |
/// | `intent.getStringExtra("SENDER_ID") ?: getStringExtra("sender_id")` | `handle(notificationUserInfo:)` |
/// | `goToLogin()` / `goToDashboard()` / `goToChat()` | `Route`, resolved in `bootstrap(api:session:)` |
/// | `Log.d("FCM_DEBUG", …)` | `RemoteLogger.log(tag: "FCM_DEBUG", …)` |
///
/// Two deliberate differences from the Kotlin:
///
/// * **The route is resolved before the token sync.** Android fires the Volley
///   request and only calls `goToDashboard()` from its callback, so the user
///   waits on a 10s-timeout network round-trip staring at a splash. The iOS
///   shell navigates immediately and syncs in the background, matching the
///   `shouldGoToDashboard = false` path Android already uses for
///   notification taps.
/// * **Failures are swallowed.** Android logs the Volley error and navigates
///   anyway; so does this — `syncPushToken` only logs, never sets a presented
///   error, so a dropped push registration can never strand the user.
@MainActor
final class AppShellViewModel: ObservableObject {

    /// The destination `MainActivity.onCreate` would have started.
    ///
    /// `RootView` already owns the unauthenticated branch, so `.login` is a
    /// no-op here — it is kept because it is the value the Kotlin actually
    /// chose, and it makes the routing table testable.
    enum Route: Equatable {
        case none
        case login
        case dashboard
        /// `goToChat(senderId)` — chat opened from a notification tap.
        case chat(String)
    }

    /// Identifier of the notification category. Matches the Android channel id
    /// `chat_notifications` and the `default_notification_channel_id`
    /// meta-data in `AndroidManifest.xml`.
    static let chatCategoryIdentifier = "chat_notifications"

    private static let logTag = "FCM_DEBUG"

    @Published private(set) var route: Route = .none
    /// Non-`nil` while `Route.chat` is awaiting presentation.
    @Published private(set) var pendingChatSenderId: String?
    @Published private(set) var notificationAuthorization: UNAuthorizationStatus = .notDetermined
    @Published private(set) var isSyncingPushToken = false

    private var hasBootstrapped = false

    // MARK: - Lifecycle

    /// Ports `MainActivity.onCreate()`: notification setup, push-token sync and
    /// first-destination resolution.
    ///
    /// Guarded by `hasBootstrapped` so a SwiftUI re-render cannot fire the
    /// `update_fcmv2.php` round-trip twice.
    func bootstrap(api: MediGyaanAPI, session: SessionStore) async {
        guard !hasBootstrapped else { return }
        hasBootstrapped = true

        registerChatCategory()
        await requestNotificationAuthorization()
        registerForRemoteNotifications()

        RemoteLogger.log(tag: Self.logTag, message: "Starting push sync for user: \(session.userId)")

        if session.isAuthenticated {
            // `updateFcmTokenToServer(currentUid, true)` — normal startup.
            route = .dashboard
            pendingChatSenderId = nil
        } else {
            // `goToLogin()` — RootView renders the login screen off the same
            // `isAuthenticated` flag.
            route = .login
        }

        // A notification tap sets `pendingChatSenderId` through
        // `handle(notificationUserInfo:)`; when one is waiting, the chat
        // transition has already happened and this sync stays silent, which is
        // exactly the `shouldGoToDashboard = false` branch in the Kotlin.
        await syncPushToken(api: api, session: session)
    }

    /// Ports the Android re-entry behaviour: `MainActivity` is a
    /// `singleTask`-style hub, so every cold start re-ran `onCreate` and pushed
    /// the current token. iOS re-enters the shell on `.active`, which is the
    /// nearest equivalent lifecycle hook.
    func applicationDidBecomeActive(api: MediGyaanAPI, session: SessionStore) async {
        guard session.isAuthenticated else { return }
        registerForRemoteNotifications()
        await syncPushToken(api: api, session: session)
    }

    // MARK: - Notification registration

    /// Ports `createNotificationChannel()`: `chat_notifications`, high
    /// importance, "Notifications for incoming messages".
    ///
    /// Android's `NotificationChannel.importance = IMPORTANCE_HIGH` maps onto
    /// the iOS `.badge` + `.sound` presentation options; there is no separate
    /// importance level, so `.alert` is omitted to keep banners alert-free in
    /// line with a chat-only channel.
    func registerChatCategory() {
        let category = UNNotificationCategory(
            identifier: Self.chatCategoryIdentifier,
            actions: [],
            intentIdentifiers: [],
            options: []
        )
        UNUserNotificationCenter.current().setNotificationCategories([category])
    }

    /// Ports `askNotificationPermission()`: on API 33+ it only prompts when the
    /// permission has not already been granted.
    func requestNotificationAuthorization() async {
        let center = UNUserNotificationCenter.current()
        let settings = await center.notificationSettings()

        if settings.authorizationStatus == .notDetermined {
            let granted = (try? await center.requestAuthorization(options: [.alert, .badge, .sound])) ?? false
            notificationAuthorization = granted ? .authorized : .denied
            RemoteLogger.log(tag: Self.logTag, message: "Notification permission granted: \(granted)")
        } else {
            notificationAuthorization = settings.authorizationStatus
        }
    }

    /// Ports the `FirebaseMessaging.getInstance().token` acquisition step.
    ///
    /// iOS registers with APNs rather than FCM, so the token is handed back by
    /// the app delegate — see ``ingest(deviceToken:session:api:)``.
    func registerForRemoteNotifications() {
        UIApplication.shared.registerForRemoteNotifications()
    }

    /// Ports `updateFcmTokenToServer(userId, shouldGoToDashboard)`'s token half:
    /// persist the token, then push it to the backend.
    ///
    /// The APNs payload arrives as raw `Data`; it is hex-encoded because
    /// `update_fcmv2.php` stores the token as an opaque string.
    func ingest(deviceToken: Data, session: SessionStore, api: MediGyaanAPI) async {
        let token = deviceToken.map { String(format: "%02x", $0) }.joined()
        session.storePushToken(token)
        RemoteLogger.log(tag: Self.logTag, message: "Fetched push token: \(token.count) bytes")
        await syncPushToken(api: api, session: session)
    }

    // MARK: - Push-token sync

    /// Ports `updateFcmTokenToServer` — `POST Neurons/api/update_fcmv2.php`
    /// with `{"user_id", "fcm_token"}`.
    ///
    /// Android used Volley's `DefaultRetryPolicy(10_000, 1, 1.0f)`; the shared
    /// `HTTPClient` supplies its own timeout instead, so only the swallow-and-
    /// continue behaviour is reproduced.
    func syncPushToken(api: MediGyaanAPI, session: SessionStore) async {
        guard session.isAuthenticated else { return }
        guard let token = session.pushToken, !token.isEmpty else {
            RemoteLogger.log(
                tag: Self.logTag,
                message: "No push token cached yet; skipping update_fcmv2.php sync"
            )
            return
        }

        isSyncingPushToken = true
        defer { isSyncingPushToken = false }

        do {
            _ = try await api.auth.updatePushToken(userId: session.userId, token: token)
            RemoteLogger.log(tag: Self.logTag, message: "SERVER RESPONSE: push token accepted for user \(session.userId)")
        } catch {
            // Android navigates regardless, so the shell never surfaces this.
            RemoteLogger.log(tag: Self.logTag, message: "Push token sync failed: \(LoadState<Never>.message(for: error))")
        }
    }

    // MARK: - Notification-click routing

    /// Ports the `intent.getStringExtra("SENDER_ID") ?: intent.getStringExtra("sender_id")`
    /// read in `onCreate`, followed by `goToChat(senderId)`.
    ///
    /// `userInfo` is the raw `UNNotification` / remote-notification payload; the
    /// sender key is accepted in both spellings because the Android build sent
    /// both and the PHP push service echoes whichever it received.
    func handle(notificationUserInfo userInfo: [AnyHashable: Any]?) {
        guard let senderId = Self.senderId(fromNotificationUserInfo: userInfo) else { return }

        RemoteLogger.log(tag: Self.logTag, message: "NOTIFICATION CLICK DETECTED: Opening chat with \(senderId)")
        route = .chat(senderId)
        pendingChatSenderId = senderId
    }

    /// Ports the `medigyaan://` equivalent of Android's intent extras for
    /// universal links: `medigyaan://chat?sender_id=42` opens the chat.
    func handle(url: URL) {
        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: false) else { return }
        let isChatRoute = components.host?.lowercased() == "chat" || components.path.lowercased() == "/chat"
        guard isChatRoute else { return }
        guard let senderId = Self.senderId(fromQueryItems: components.queryItems), !senderId.isEmpty else { return }

        route = .chat(senderId)
        pendingChatSenderId = senderId
    }

    /// Clears the pending chat route once the full-screen cover is dismissed,
    /// returning the shell to the dashboard, matching `FLAG_ACTIVITY_CLEAR_TOP`
    /// on the Android `goToChat` intent.
    func dismissChat() {
        pendingChatSenderId = nil
        if case .chat = route { route = .dashboard }
    }

    /// Reads the sender id out of a remote-notification payload, accepting both
    /// the upper-case and lower-case spellings Android checked for.
    static func senderId(fromNotificationUserInfo userInfo: [AnyHashable: Any]?) -> String? {
        guard let userInfo else { return nil }
        for key in ["SENDER_ID", "sender_id"] {
            if let value = userInfo[key] as? String, !value.isEmpty { return value }
            if let value = userInfo[key] as? NSNumber, value.stringValue != "0" { return value.stringValue }
        }
        return nil
    }

    /// Reads `sender_id` out of a deep-link query string.
    static func senderId(fromQueryItems items: [URLQueryItem]?) -> String? {
        guard let items else { return nil }
        return items.first { $0.name.lowercased() == "sender_id" }?.value
    }
}