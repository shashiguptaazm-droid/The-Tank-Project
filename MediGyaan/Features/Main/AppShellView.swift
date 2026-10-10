import SwiftUI

/// Ports `MainActivity` — the Android hub that every cold start passes through
/// before handing off to the first real screen.
///
/// The Kotlin activity sets `activity_main` (a splash that never actually binds
/// its views), initialises PDFBox, creates the `chat_notifications` channel,
/// prompts for `POST_NOTIFICATIONS`, syncs the FCM token to
/// `api/update_fcmv2.php`, then starts **one** of three destinations:
///
/// ```text
/// user_id == 0                      -> LoginActivity
/// user_id != 0, SENDER_ID extra set -> MessengerActivity(SENDER_ID)   // notification tap
/// user_id != 0                      -> DashboardActivity
/// ```
///
/// On iOS the destination switch itself already lives in `RootView`
/// (`SplashView` → `LoginView` / `AppTabView`), so this shell owns only what
/// `RootView` has no place for: notification registration, push-token sync and
/// the notification-tap chat hand-off. See ``AppShellViewModel`` for the
/// line-by-line mapping.
///
/// Wire-up: `RootView` should render `AppShellView()` where it currently
/// renders `AppTabView()`.
struct AppShellView: View {

    @Environment(\.api) private var api
    @EnvironmentObject private var session: SessionStore
    @Environment(\.scenePhase) private var scenePhase

    @StateObject private var model = AppShellViewModel()

    var body: some View {
        AppTabView()
            .screenBackground()
            .onReceive(NotificationCenter.default.publisher(for: PushRegistration.pushTappedNotification)) { note in
                model.handle(notificationUserInfo: note.userInfo?["payload"] as? [AnyHashable: Any])
            }
            .task {
                await model.bootstrap(api: api, session: session)
                if let payload = PushRegistration.shared.drainLaunchNotificationPayload() {
                    model.handle(notificationUserInfo: payload)
                }
                if let token = PushRegistration.shared.drainDeviceToken() {
                    await model.ingest(deviceToken: token, session: session, api: api)
                }
            }
            .onChange(of: scenePhase) { phase in
                guard phase == .active else { return }
                Task { await model.applicationDidBecomeActive(api: api, session: session) }
            }
            .onOpenURL { url in
                model.handle(url: url)
            }
            .fullScreenCover(
                isPresented: Binding(
                    get: { model.pendingChatSenderId != nil },
                    set: { if !$0 { model.dismissChat() } }
                )
            ) {
                NavigationStack { MessengerView() }
            }
    }
}

#Preview {
    AppShellView()
        .environmentObject(SessionStore())
        .environment(\.api, .live)
}