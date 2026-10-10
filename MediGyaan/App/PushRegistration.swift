import Foundation
import UIKit
import UserNotifications

extension Notification.Name {
    /// Republished by ``PushRegistration`` every time the user taps a chat
    /// notification. Carries the raw payload under the `"payload"` key.
    ///
    /// Android reads the equivalent off the `Intent` inside `MainActivity`
    /// (`intent.getStringExtra("SENDER_ID") ?: getStringExtra("sender_id")`).
    /// iOS has no `Intent` and no `UIApplicationDelegate` method for the tap,
    /// so the only consumer is a SwiftUI view — hence a notification instead of
    /// a return value.
    ///
    /// Wire-up lives in `AppShellView`:
    ///
    /// ```swift
    /// .onReceive(NotificationCenter.default.publisher(for: PushRegistration.pushTappedNotification)) {
    ///     model.handle(notificationUserInfo: $0.userInfo?["payload"] as? [AnyHashable: Any])
    /// }
    /// ```
    static let medigyaanPushTapped = Notification.Name("com.corp.medigyaan.pushTapped")
}

/// Ports the launch-time half of Android's push pipeline — the part that
/// `EduLabsApplication.onCreate()` owns on iOS because SwiftUI has no
/// `Application` class to do it in.
///
/// On Android the ordering is: `EduLabsApplication.onCreate()` runs first, then
/// `SplashActivity`, then `MainActivity.onCreate()` reads
/// `FirebaseMessaging.getInstance().token` and the launch `Intent` extras. iOS
/// has the opposite problem — ``AppDelegateBootstrap``'s
/// `didFinishLaunchingWithOptions` and the APNs token callback routinely fire
/// **before** the first SwiftUI scene mounts a shell. Anything they receive is
/// therefore held here until somebody drains it, which is the one thing the
/// Android boot order made unnecessary.
///
/// Deliberately **not** ported, because ``AppShellViewModel`` already owns it:
///
/// | Kotlin | iOS owner |
/// |---|---|
/// | `createNotificationChannel()` — `chat_notifications`, `IMPORTANCE_HIGH` | `AppShellViewModel.registerChatCategory()` |
/// | `askNotificationPermission()` — `POST_NOTIFICATIONS` | `AppShellViewModel.requestNotificationAuthorization()` |
/// | `registerForRemoteNotifications()` | `AppShellViewModel.registerForRemoteNotifications()` |
/// | `updateFcmTokenToServer()` → `POST Neurons/api/update_fcmv2.php` | `AppShellViewModel.syncPushToken(api:session:)` |
///
/// This type therefore never calls `UIApplication.shared.registerForRemote-
/// Notifications()`; there is exactly one owner of APNs registration.
///
/// Thread safety: the launch payload arrives on the main thread, but
/// `application(_:didReceiveRemoteNotification:fetchCompletionHandler:)` may be
/// invoked on a background queue for a silent push. State is guarded by
/// ``lock`` rather than actor isolation, which keeps this type free of the
/// `@MainActor` annotation that would complicate the `UNUserNotificationCenter`
/// delegate witnesses in ``AppDelegateBootstrap``.
final class PushRegistration: NSObject {

    /// Posted whenever a running app receives a chat-notification tap. The raw
    /// `UNNotification.request.content.userInfo` sits under the `"payload"` key.
    ///
    /// Exposed here rather than on `Notification.Name` so consumers do not have
    /// to import the extension to find it.
    static let pushTappedNotification = Notification.Name.medigyaanPushTapped

    /// The iOS counterpart of `EduLabsApplication.Companion.instance`.
    ///
    /// A singleton because `@UIApplicationDelegateAdaptor` constructs its own
    /// delegate instance, so per-instance state would not be visible to both the
    /// delegate and the SwiftUI shell.
    static let shared = PushRegistration()

    private static let logTag = "PushRegistration"

    private let lock = NSLock()
    private var storedLaunchPayload: [AnyHashable: Any]?
    private var storedDeviceToken: Data?
    private var storedSilentPushPayload: [AnyHashable: Any]?

    private override init() {
        super.init()
    }

    // MARK: - Ingress

    /// Ports the launch-`Intent` read in `MainActivity.onCreate()`.
    ///
    /// `UIApplication.LaunchOptionsKey.remoteNotification` carries the payload a
    /// push delivered while the app was not running, which is iOS's equivalent
    /// of Android handing the notification `Intent` to the launcher activity.
    func configure(launchOptions: [UIApplication.LaunchOptionsKey: Any]?) {
        guard let payload = launchOptions?[.remoteNotification] as? [AnyHashable: Any] else { return }

        lock.lock()
        storedLaunchPayload = payload
        lock.unlock()

        RemoteLogger.log(tag: Self.logTag, message: "Launched from a notification; payload buffered for the shell")
    }

    /// Ports `FirebaseMessaging.getInstance().token` acquisition.
    ///
    /// APNs hands the token over through a delegate callback instead of a
    /// blocking getter, and it lands well before the shell exists, so it is
    /// held rather than pushed straight at the backend.
    func capture(deviceToken: Data) {
        lock.lock()
        storedDeviceToken = deviceToken
        lock.unlock()

        RemoteLogger.log(tag: Self.logTag, message: "Buffered APNs token (\(deviceToken.count) bytes) pending shell bootstrap")
    }

    /// Ports the data-only delivery path of `MyFirebaseMessagingService`.
    ///
    /// Retained for inspection rather than acted on: no iOS surface consumes
    /// data-only pushes today, and inventing a consumer here would be guesswork
    /// about behaviour that does not exist yet. Android's counterpart is a
    /// background `Service`, which iOS has no analogue for.
    var silentPushPayload: [AnyHashable: Any]? {
        lock.lock()
        defer { lock.unlock() }
        return storedSilentPushPayload
    }

    func capture(silentPush userInfo: [AnyHashable: Any]) {
        lock.lock()
        storedSilentPushPayload = userInfo
        lock.unlock()

        let keys = userInfo.keys.map { String(describing: $0) }.sorted().joined(separator: ",")
        RemoteLogger.log(tag: Self.logTag, message: "Received silent push with keys: \(keys)")
    }

    /// Ports the notification-tap half of `MainActivity.onCreate()`'s
    /// `SENDER_ID` read, but **only** for taps that arrive while the app is
    /// already running.
    ///
    /// Cold-start taps go through ``configure(launchOptions:)`` instead and are
    /// replayed by ``drainLaunchNotificationPayload()``.
    func handle(notificationResponse: UNNotificationResponse) {
        let payload = response.notification.request.content.userInfo
        RemoteLogger.log(tag: Self.logTag, message: "Notification tapped; republishing payload to the shell")
        NotificationCenter.default.post(
            name: Self.pushTappedNotification,
            object: nil,
            userInfo: ["payload": payload]
        )
    }

    // MARK: - Egress

    /// Returns the cold-start notification payload exactly once, then clears it.
    ///
    /// One-shot by design: replaying a launch tap a second time would re-open
    /// the chat cover over whatever the user navigated to instead.
    func drainLaunchNotificationPayload() -> [AnyHashable: Any]? {
        lock.lock()
        defer { lock.unlock() }
        let payload = storedLaunchPayload
        storedLaunchPayload = nil
        return payload
    }

    /// Returns the APNs device token exactly once, then clears it.
    ///
    /// Feeds `AppShellViewModel.ingest(deviceToken:session:api:)`, which hex-
    /// encodes it and pushes it to `api/update_fcmv2.php`.
    func drainDeviceToken() -> Data? {
        lock.lock()
        defer { lock.unlock() }
        let token = storedDeviceToken
        storedDeviceToken = nil
        return token
    }
}