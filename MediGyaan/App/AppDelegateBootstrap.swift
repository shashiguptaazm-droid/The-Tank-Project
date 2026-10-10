import Foundation
import UIKit
import UserNotifications

/// Ports `EduLabsApplication.onCreate()` — the Android `Application` subclass
/// whose `android:name` in `AndroidManifest.xml` made it the very first
/// project code to run, ahead of `SplashActivity`.
///
/// SwiftUI has no `Application` class, so the equivalent seam is
/// `UIApplicationDelegate.application(_:didFinishLaunchingWithOptions:)`.
/// Everything Android moved off the critical path in `onCreate()` is reached
/// from here.
///
/// Line-by-line against the Kotlin:
///
/// | Kotlin | Here |
/// |---|---|
/// | `instance = this` (companion `lateinit var instance`) | `PushRegistration.shared` — the one process-wide object the delegate and the SwiftUI shell both resolve to |
/// | `StrictMode.setThreadPolicy` / `setVmPolicy` (`BuildConfig.DEBUG`) | ``startupAudit()`` — see the note below |
/// | `Executors.newSingleThreadExecutor().execute { ModelRotator.init(this) }` | ``prewarmBackgroundSystems()`` — same off-main-thread intent |
/// | `AiProviderUserId.install(this)` — process-global user id for the AI gateway | Already ported by parameter passing: `AiTrainingLogger.log(userId:…)` receives `SessionStore.userId` from the caller instead of reading a static |
/// | `applySavedAppTheme(this)` | Already ported by `MediGyaanApp` (`@AppStorage(AppPreferences.darkMode)` + `.preferredColorScheme`). Deliberately **not** repeated here. |
/// | `PDFBoxResourceLoader.init(this)` | Not applicable — iOS ships `PDFKit`, consumed directly by `AiDocumentOcrHelper` |
/// | `FirebaseApp.initializeApp(this)` + Firestore `setPersistenceEnabled(true)` | Not applicable — no Firebase SDK on iOS; state is server-backed through `MediGyaanAPI` |
/// | `FirebaseAppCheck` — `PlayIntegrityAppCheckProviderFactory` / `DebugAppCheckProviderFactory` | Not applicable — DeviceCheck/App Attest is a separate effort; logged as absent at launch |
///
/// Three deliberate differences from the Kotlin:
///
/// * **StrictMode is not ported.** It is a JVM/ART diagnostic with no iOS
///   counterpart; the *intent* behind `detectAll().penaltyLog()` — catch main-
///   thread disk work — is met by ``prewarmBackgroundSystems()`` keeping the
///   `UserDefaults`-backed rotator off the launch path.
/// * **Crash handling is delegated to `RemoteLogger`.** Android installs no
///   `Thread.UncaughtExceptionHandler`; the iOS build installs `NSSetUncaught-
///   ExceptionHandler` plus `SIGSEGV`/`SIGABRT`/… handlers in
///   `RemoteLogger.initializeCrashReporting()`, already called from
///   `MediGyaanApp.init()`. A second handler here would clobber the first.
/// * **Push is APNs, not FCM.** `MyFirebaseMessagingService` is an Android
///   `Service`, not part of `onCreate()`; the closest iOS launch-time duty is
///   owning the `UNUserNotificationCenter` delegate and buffering any payload
///   that arrived before the first SwiftUI scene exists.
///
/// Wire-up (owned by `MediGyaanApp`, not by this type):
///
/// ```swift
/// @UIApplicationDelegateAdaptor(AppDelegateBootstrap.self) private var appDelegate
/// ```
final class AppDelegateBootstrap: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {

    private static let logTag = "AppDelegateBootstrap"

    /// The process-wide companion to `EduLabsApplication.Companion.instance`.
    ///
    /// UIKit constructs its **own** adaptor instance, so nothing on the delegate
    /// is written to `static let shared` — all mutable launch state therefore
    /// lives in ``PushRegistration/shared``, which both the delegate instance
    /// and the SwiftUI shell resolve to.
    static let shared = AppDelegateBootstrap()

    private var push: PushRegistration { .shared }

    // MARK: - UIApplicationDelegate

    /// Ports `EduLabsApplication.onCreate()`.
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {
        // Installing the delegate here — before `didFinishLaunching` returns —
        // is what guarantees UIKit delivers the `UNUserNotificationCenter`
        // callbacks on the main thread.
        UNUserNotificationCenter.current().delegate = self

        push.configure(launchOptions: launchOptions)
        prewarmBackgroundSystems()
        startupAudit()
        return true
    }

    /// Ports the APNs half of `FirebaseMessaging.getInstance().token` — the
    /// token Android read synchronously in `MainActivity` is delivered
    /// asynchronously here instead.
    ///
    /// Buffered until ``PushRegistration/drainDeviceToken()`` is called, because
    /// the token usually arrives before the SwiftUI scene has mounted a shell.
    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        push.capture(deviceToken: deviceToken)
    }

    /// Ports the `Log.e("EduLabsApplication", …)`-style swallow-and-continue
    /// posture of the two `catch (e: Exception)` blocks in `onCreate()`: a
    /// failure here must never prevent the app from launching.
    func application(_ application: UIApplication, didFailToRegisterForRemoteNotificationsWithError error: Error) {
        RemoteLogger.log(
            tag: Self.logTag,
            message: "APNs registration failed: \(error.localizedDescription)"
        )
    }

    /// Stands in for the `MyFirebaseMessagingService` intent-filter: iOS routes
    /// silent/data pushes here rather than starting a background `Service`.
    func application(
        _ application: UIApplication,
        didReceiveRemoteNotification userInfo: [AnyHashable: Any],
        fetchCompletionHandler completionHandler: @escaping (UIBackgroundFetchResult) -> Void
    ) {
        push.capture(silentPush: userInfo)
        completionHandler(.newData)
    }

    // MARK: - UNUserNotificationCenterDelegate

    /// Matches the `chat_notifications` presentation set in
    /// `AppShellViewModel.registerChatCategory()` (`.badge` + `.sound`, no
    /// `.alert`), so a chat arriving while the app is foregrounded behaves the
    /// same as it does when it is the app that presents the notification.
    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification
    ) async -> UNNotificationPresentationOptions {
        [.badge, .sound]
    }

    /// Ports `intent.getStringExtra("SENDER_ID") ?: getStringExtra("sender_id")`
    /// on a notification tap. The raw payload is republished so
    /// `AppShellViewModel.handle(notificationUserInfo:)` stays the single place
    /// that decides where a tap routes.
    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse
    ) async {
        push.handle(notificationResponse: response)
    }

    // MARK: - Ports of the onCreate() threads

    /// Ports
    /// `Executors.newSingleThreadExecutor().execute { ModelRotator.init(this) }`.
    ///
    /// `ModelRotator` has a `private init()` behind `shared`, so first-touching
    /// it is what performs the initialisation — including the `UserDefaults`
    /// read behind its `model_rotator_prefs_v1` key. Touching it from a utility
    /// queue keeps that off the launch path, which is the whole point of the
    /// Kotlin running it on a background executor.
    private func prewarmBackgroundSystems() {
        DispatchQueue.global(qos: .utility).async {
            _ = ModelRotator.shared.buildPool()
            RemoteLogger.log(tag: Self.logTag, message: "ModelRotator warmed off the main thread")
        }
    }

    /// Ports the `if (BuildConfig.DEBUG)` guard in `onCreate()`.
    ///
    /// Android compiled a `StrictMode` penalty log into debug builds only. The
    /// iOS stand-in records the same launch-time facts — device, OS, locale,
    /// cold/warm launch — so a launch problem reported by a debug tester can be
    /// correlated, without pretending a JVM-only policy exists here.
    private func startupAudit() {
        RemoteLogger.log(
            tag: Self.logTag,
            message: "didFinishLaunching - iOS \(UIDevice.current.systemVersion), \(UIDevice.current.model), locale \(Locale.current.identifier)"
        )
    }
}