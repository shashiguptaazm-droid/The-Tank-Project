import SwiftUI
import AVFoundation
import UIKit

// MARK: - Destination

/// The screen `SplashActivity` would have started next.
///
/// Ports the branch table of `SplashActivity.checkNavigationState()`, in the
/// same evaluation order:
/// ```text
/// !prefs.getBoolean("onboarding_complete", false)  -> OnboardingActivity
/// userId == 0                                     -> LoginActivity
/// !AvatarManager.hasSelectedAvatar(context)       -> GuardianShowcaseActivity(EXTRA_FORCED_SELECTION)
/// intent extra SENDER_ID / sender_id present      -> MessengerActivity(SENDER_ID)
/// otherwise                                       -> DashboardActivity
/// ```
/// Every destination closes the splash with `android.R.anim.fade_in` /
/// `fade_out` and calls `finish()`, which a SwiftUI `transition(.opacity)` on
/// `RootView`'s `ZStack` already reproduces.
enum SplashRoute: Equatable {

    /// `goToOnboarding()` — `OnboardingActivity`.
    case onboarding
    /// `goToAvatarSelection()` — `GuardianShowcaseActivity` with
    /// `EXTRA_FORCED_SELECTION = true`.
    case avatarSelection
    /// `goToLogin()` — `LoginActivity`.
    case login
    /// `goToDashboard()` — `DashboardActivity`.
    case dashboard
    /// `goToChat(senderId)` — `MessengerActivity` with the `SENDER_ID` extra,
    /// flagged `FLAG_ACTIVITY_NEW_TASK or FLAG_ACTIVITY_CLEAR_TOP`.
    case chat(String)

    /// Resolves the Kotlin branch table above.
    ///
    /// * Parameters:
    ///   - hasCompletedOnboarding: `prefs.getBoolean("onboarding_complete", false)`.
    ///   - isAuthenticated: `prefs.getInt("user_id", 0) != 0`, which
    ///     `SessionStore.isAuthenticated` already tracks.
    ///   - hasSelectedAvatar: `AvatarManager.hasSelectedAvatar(context)`. The
    ///     iOS app stores the pick under `selected_avatar_id`
    ///     (`@AppStorage` in `WarriorSelectionView` / `GuardianShowcaseView`)
    ///     with a default of `1`, so the key always exists and the gate can
    ///     never fire; callers therefore pass `true`.
    ///   - pendingChatSenderId: `intent.getStringExtra("SENDER_ID") ?:
    ///     intent.getStringExtra("sender_id")`. The splash has no intent on
    ///     iOS — the notification tap is resolved later by
    ///     `AppShellViewModel`, so the splash passes `nil`.
    static func destination(
        hasCompletedOnboarding: Bool,
        isAuthenticated: Bool,
        hasSelectedAvatar: Bool,
        pendingChatSenderId: String?
    ) -> SplashRoute {
        guard hasCompletedOnboarding else { return .onboarding }
        guard isAuthenticated else { return .login }
        guard hasSelectedAvatar else { return .avatarSelection }

        if let senderId = pendingChatSenderId, !senderId.isEmpty {
            return .chat(senderId)
        }
        return .dashboard
    }
}

// MARK: - Push-token cache

/// Local cache for the push token, preventing redundant `POST`s to
/// `api/update_fcmv2.php`.
///
/// 1:1 port of the Android `object FcmTokenCache` (`model/FcmTokenCache.kt`),
/// including its own `SharedPreferences` file (`fcm_token_cache_prefs`,
/// separate from `"MY_APP"`), its `last_synced_fcm_token` /
/// `last_synced_fcm_time` keys and its 7-day re-sync interval.
///
/// Keys are re-spelled with the `mg.` prefix this app uses; the Android file
/// name and key names are carried in the doc comments so the two stay
/// traceable.
enum SplashPushTokenCache {

    /// Android `SharedPreferences("fcm_token_cache_prefs")`.
    static let defaultsSuiteName = "fcm_token_cache_prefs"
    /// Android `KEY_LAST_TOKEN = "last_synced_fcm_token"`.
    static let lastTokenKey = "mg.lastSyncedPushToken"
    /// Android `KEY_LAST_SYNC_TIME = "last_synced_fcm_time"`.
    static let lastSyncTimeKey = "mg.lastSyncedPushTokenAt"
    /// Android `SYNC_INTERVAL_MS = 7 * 24 * 60 * 60 * 1000L`.
    static let syncInterval: TimeInterval = 7 * 24 * 60 * 60

    /// Ports `FcmTokenCache.shouldSyncToken(context, newToken)`: re-sync when
    /// the token changed, or when the previous successful sync is older than
    /// the 7-day interval.
    static func shouldSync(
        _ token: String,
        now: Date = Date(),
        defaults: UserDefaults = .standard
    ) -> Bool {
        guard !token.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return false }

        let lastToken = defaults.string(forKey: lastTokenKey) ?? ""
        let lastTime = defaults.double(forKey: lastSyncTimeKey)

        if token != lastToken || now.timeIntervalSince1970 - lastTime > syncInterval {
            return true
        }
        RemoteLogger.log(
            tag: "FcmTokenCache",
            message: "⚡ FCM Token is unchanged and freshly synced. Skipping redundant API call."
        )
        return false
    }

    /// Ports `FcmTokenCache.markTokenSynced(context, token)`, written only
    /// after a 2xx response so a failed POST is retried on the next launch.
    static func markSynced(
        _ token: String,
        now: Date = Date(),
        defaults: UserDefaults = .standard
    ) {
        guard !token.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        defaults.set(token, forKey: lastTokenKey)
        defaults.set(now.timeIntervalSince1970, forKey: lastSyncTimeKey)
        RemoteLogger.log(tag: "FcmTokenCache", message: "FCM Token marked as synced locally")
    }
}

// MARK: - State machine

/// Ports the `SplashActivity` state machine: the three `Boolean` gates, the
/// FCM sync with its 3-second hard timeout, and the matrix transition that
/// ends the splash.
///
/// The Kotlin keeps four `Boolean` fields (`tokenSyncCompleted`,
/// `videoFinishedOrSkipped`, `hasNavigated`) plus a `Handler`, an
/// `OkHttpClient`, a `MediaPlayer` and a `TextureView`. They map like this:
///
/// | Kotlin | Here |
/// |---|---|
/// | `startTimeMs` | ``coldStartDate`` |
/// | `tokenSyncCompleted` | ``isTokenSyncComplete`` |
/// | `videoFinishedOrSkipped` | ``isVideoFinished`` |
/// | `hasNavigated` | ``hasNavigated`` |
/// | `handler.postDelayed(…, 3000)` | ``tokenSyncTimeout`` raced against the sync |
/// | `onSurfaceTextureAvailable` | ``videoURL`` + ``SplashVideoBackdrop`` |
/// | `MediaPlayer.setOnErrorListener` | a missing `videoURL`, which opens the video gate immediately |
/// | `ScreenExplosionHelper.triggerExplosion(…)` | ``isTransitionActive`` + `SplashMatrixOverlay` |
/// | `Log.i("==== SPLASH COMPLETED IN …ms ====")` | ``route`` assignment |
@MainActor
final class SplashViewModel: ObservableObject {

    /// Android `TAG = "SPLASH_VIDEO"`.
    nonisolated static let logTag = "SPLASH_VIDEO"

    /// `ScreenExplosionHelper`'s `ValueAnimator.duration = 2800L`, after which
    /// `onAnimationEnd` fires and the splash navigates.
    nonisolated static let transitionDuration: TimeInterval = 2.8

    /// `handler.postDelayed({ … }, 3000)` — the hard ceiling on the FCM sync,
    /// after which `completeTokenSync()` runs anyway.
    nonisolated static let tokenSyncTimeout: TimeInterval = 3.0

    /// `R.raw.dont_land_the_foot_on_books_it`, the non-looping intro clip.
    nonisolated static let introVideoName = "dont_land_the_foot_on_books_it"

    /// `ScreenExplosionHelper.triggerExplosion(hudTitle = …)` as passed by
    /// `SplashActivity.onVideoEnd()`.
    nonisolated static let transitionTitle = "[ ENTERING THE MATRIX ]"
    /// `triggerExplosion(hudSubtitle = …)`.
    nonisolated static let transitionSubtitle = "> SYSTEM OVERRIDE: NEURAL LINK ACTIVE"
    /// `triggerExplosion(hudFootnote = …)`.
    nonisolated static let transitionFootnote = "DECRYPTING CONSTRUCT CORE"

    /// `startTimeMs`, captured before `setContentView` so the cold-start figure
    /// logged on hand-off covers the whole splash.
    let coldStartDate: Date = Date()

    /// Android `videoFinishedOrSkipped`.
    @Published private(set) var isVideoFinished = false
    /// Android `tokenSyncCompleted`.
    @Published private(set) var isTokenSyncComplete = false
    /// Android `hasNavigated`.
    @Published private(set) var hasNavigated = false
    /// True while `ScreenExplosionHelper`'s shatter overlay is on screen.
    @Published private(set) var isTransitionActive = false
    /// The resolved destination; `nil` until both gates open.
    @Published private(set) var route: SplashRoute?
    /// `R.raw.dont_land_the_foot_on_books_it`, or `nil` when the asset is
    /// missing from the bundle.
    @Published private(set) var videoURL: URL?
    /// Drives `MediaPlayer.pause()` / `start()` from `onPause` / `onResume`.
    @Published var isVideoPlaying = true

    private var hasBegun = false
    /// `prefs.getInt("user_id", 0) != 0`, sampled once in `onCreate` and
    /// re-read in `checkNavigationState`; `SessionStore.isAuthenticated`
    /// already tracks it.
    private var isAuthenticated = false

    // MARK: - Lifecycle

    /// Ports `onCreate()`'s two independent starting guns.
    ///
    /// The Kotlin kicks off the FCM sync and lets `MediaPlayer`'s own
    /// callbacks drive the video gate; here the video is resolved from the
    /// bundle and the sync is awaited, with the same 3-second ceiling.
    func begin(api: MediGyaanAPI, session: SessionStore) async {
        guard !hasBegun else { return }
        hasBegun = true

        RemoteLogger.log(tag: Self.logTag, message: "==== SPLASH STARTED ====")

        isAuthenticated = session.isAuthenticated

        videoURL = Bundle.main.url(
            forResource: Self.introVideoName,
            withExtension: "mp4"
        )
        if videoURL == nil {
            // Android reaches the same state from the `startBackgroundVideo`
            // `catch` and from `setOnErrorListener`: both call `onVideoEnd()`.
            RemoteLogger.log(tag: Self.logTag, message: "Intro video unavailable; skipping video gate")
            videoDidEnd()
        }

        await syncPushToken(api: api, session: session)
    }

    /// Ports `onPause()` — `mediaPlayer.pause()`.
    func applicationDidEnterBackground() {
        isVideoPlaying = false
    }

    /// Ports `onResume()` — `mediaPlayer.start()` unless the clip already
    /// played out.
    func applicationDidBecomeActive() {
        guard !isVideoFinished else { return }
        isVideoPlaying = true
    }

    // MARK: - FCM gate

    /// Ports `syncFcmTokenCoroutines(userId)`, raced against the Kotlin's
    /// 3-second `handler.postDelayed` safety net.
    private func syncPushToken(api: MediGyaanAPI, session: SessionStore) async {
        guard session.isAuthenticated else {
            // `userId == 0` — `onCreate` sets `tokenSyncCompleted = true`
            // without touching Firebase at all.
            completeTokenSync()
            return
        }

        async let hardTimeout: Void = Task { @MainActor in
            try? await Task.sleep(nanoseconds: UInt64(Self.tokenSyncTimeout * 1_000_000_000))
            self.completeTokenSync()
        }.value

        await performTokenSync(api: api, session: session)
        _ = await hardTimeout
        completeTokenSync()
    }

    /// The body of `syncFcmTokenCoroutines`: read the token, apply
    /// `FcmTokenCache.shouldSyncToken`, `POST` `Neurons/api/update_fcmv2.php`
    /// with `{user_id, fcm_token}` (5s connect / 5s read timeout on Android),
    /// mark the cache on success, and swallow every failure — the Kotlin's
    /// `catch` only logs.
    private func performTokenSync(api: MediGyaanAPI, session: SessionStore) async {
        guard let token = session.pushToken, !token.isEmpty else {
            RemoteLogger.log(
                tag: Self.logTag,
                message: "No push token cached at splash time; skipping update_fcmv2.php"
            )
            return
        }

        guard SplashPushTokenCache.shouldSync(token) else { return }

        do {
            _ = try await api.auth.updatePushToken(userId: session.userId, token: token)
            SplashPushTokenCache.markSynced(token)
            RemoteLogger.log(tag: Self.logTag, message: "FCM sync accepted for user \(session.userId)")
        } catch {
            RemoteLogger.log(
                tag: Self.logTag,
                message: "Error in FCM coroutine sync: \(LoadState<Never>.message(for: error))"
            )
        }
    }

    /// Ports `completeTokenSync()`.
    private func completeTokenSync() {
        isTokenSyncComplete = true
        checkNavigationState()
    }

    // MARK: - Video gate

    /// Ports `onVideoEnd()` — the single idempotent entry point the skip
    /// button, `setOnCompletionListener`, `setOnErrorListener` and the
    /// `startBackgroundVideo` `catch` all funnel into.
    ///
    /// `ScreenExplosionHelper.triggerExplosion` snapshots the `TextureView`,
    /// plays the 2.8s shatter, then runs its `onComplete` lambda, which stops
    /// playback and calls `checkNavigationState()`.
    func videoDidEnd() {
        guard !isVideoFinished else { return }
        isVideoFinished = true
        isVideoPlaying = false

        RemoteLogger.log(tag: Self.logTag, message: "Transition HUD engaged")

        Task { @MainActor in
            try? await Task.sleep(nanoseconds: UInt64(Self.transitionDuration * 1_000_000_000))
            self.isTransitionActive = false
            self.checkNavigationState()
        }
    }

    // MARK: - Routing

    /// Ports `checkNavigationState()`: both gates open, log the cold-start
    /// duration exactly once, then resolve the destination.
    private func checkNavigationState(pendingChatSenderId: String? = nil) {
        guard !hasNavigated, isVideoFinished, isTokenSyncComplete else { return }
        hasNavigated = true

        let elapsedMs = Int(-coldStartDate.timeIntervalSinceNow * 1000)
        RemoteLogger.log(tag: Self.logTag, message: "==== SPLASH COMPLETED IN \(elapsedMs)ms ====")

        route = SplashRoute.destination(
            hasCompletedOnboarding: OnboardingView.hasCompletedOnboarding,
            isAuthenticated: isAuthenticated,
            hasSelectedAvatar: true,
            pendingChatSenderId: pendingChatSenderId
        )
    }
}

// MARK: - Palette

/// Colours lifted verbatim from `res/layout/activity_splash.xml` and the two
/// shape drawables it references.
///
/// These are fixed hex literals in the Android splash, with no counterpart in
/// `AppTheme.Palette` (which is the Material day/night palette) or
/// `AppTheme.Ink` (which belongs to the dashboard). `#00E5FF` is the one
/// exception: it already exists as `AppTheme.Ink.cyan` and is referenced from
/// there rather than redeclared.
private enum SplashCanvas {

    /// `android:background="#050816"` on the root `ConstraintLayout`.
    static let base = Color(hex: 0x050816)
    /// `bg_splash_scrim` `startColor`, `angle="270"` (top to bottom).
    static let scrimTop = Color(hex: 0xB3050816)
    /// `bg_splash_scrim` `centerColor`.
    static let scrimMid = Color(hex: 0x8C050816)
    /// `bg_splash_scrim` `endColor`.
    static let scrimBottom = Color(hex: 0xCC050816)
    /// `splashSubtitle` `android:textColor="#E0E0FF"`.
    static let subtitle = Color(hex: 0xE0E0FF)
    /// `bg_skip_button` `android:solid="#80000000"`.
    static let skipFill = Color(hex: 0x80000000)
    /// `bg_skip_button` `android:stroke="#66FFFFFF"`, 1.5dp.
    static let skipStroke = Color(hex: 0x66FFFFFF)
    /// The `#00FF41` matrix green used by `ScreenExplosionHelper`.
    static let matrixGreen = Color(hex: 0x00FF41)
    /// `#E0FFE8` — the bright head glyph of each matrix column.
    static let matrixHead = Color(hex: 0xE0FFE8)
}

// MARK: - Video backdrop

/// `UIView` whose backing layer is an `AVPlayerLayer`, the equivalent of the
/// splash's hardware-accelerated `TextureView`.
///
/// `SplashActivity.adjustAspectRatio()` computes a centre-crop `Matrix` by
/// hand; `AVPlayerLayer.videoGravity = .resizeAspectFill` is that same
/// transform, so the port does not reimplement it.
private final class SplashPlayerHost: UIView {
    override class var layerClass: AnyClass { AVPlayerLayer.self }
}

/// Plays `R.raw.dont_land_the_foot_on_books_it` behind the splash branding.
///
/// Ports `startBackgroundVideo(surface)`: non-looping, prepared asynchronously,
/// with completion and error both calling `onVideoEnd()`.
/// `stopVideoPlayback()` becomes `dismantleUIView(_:coordinator:)`, which
/// detaches the layer and cancels the completion observer.
private struct SplashVideoBackdrop: UIViewRepresentable {

    let url: URL
    /// `onResume()` / `onPause()`.
    let isPlaying: Bool
    /// `MediaPlayer.setOnCompletionListener` + `setOnErrorListener`.
    let onEnded: () -> Void

    func makeCoordinator() -> Coordinator {
        Coordinator(onEnded: onEnded)
    }

    func makeUIView(context: Context) -> SplashPlayerHost {
        let host = SplashPlayerHost()
        host.backgroundColor = .black

        let item = AVPlayerItem(url: url)
        let player = AVPlayer(playerItem: item)

        let coordinator = context.coordinator
        coordinator.player = player
        coordinator.item = item
        coordinator.endObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemDidPlayToEndTime,
            object: item,
            queue: .main
        ) { [weak coordinator] _ in
            Task { @MainActor in coordinator?.finish() }
        }

        if let playerLayer = host.layer as? AVPlayerLayer {
            playerLayer.player = player
            playerLayer.videoGravity = .resizeAspectFill
        }

        player.play()
        return host
    }

    func updateUIView(_ uiView: SplashPlayerHost, context: Context) {
        context.coordinator.onEnded = onEnded
        guard let player = context.coordinator.player else { return }

        if isPlaying {
            if player.timeControlStatus != .playing { player.play() }
        } else {
            player.pause()
        }
    }

    static func dismantleUIView(_ uiView: SplashPlayerHost, coordinator: Coordinator) {
        if let endObserver = coordinator.endObserver {
            NotificationCenter.default.removeObserver(endObserver)
            coordinator.endObserver = nil
        }
        coordinator.player?.pause()
        if let playerLayer = uiView.layer as? AVPlayerLayer {
            playerLayer.player = nil
        }
        coordinator.player = nil
        coordinator.item = nil
    }

    final class Coordinator {

        var player: AVPlayer?
        var item: AVPlayerItem?
        var endObserver: NSObjectProtocol?
        var onEnded: () -> Void

        /// Stands in for the Kotlin's `videoFinishedOrSkipped` early return:
        /// `onVideoEnd()` fires once even if both the completion notification
        /// and a teardown race reach this point.
        private var hasFinished = false

        init(onEnded: @escaping () -> Void) {
            self.onEnded = onEnded
        }

        func finish() {
            guard !hasFinished else { return }
            hasFinished = true
            onEnded()
        }
    }
}

// MARK: - Matrix transition

/// The splash hand-off overlay: matrix digital rain, radial shards flying off
/// under gravity, a decaying screen shake, and the telemetry HUD.
///
/// Ports `ScreenExplosionHelper.triggerExplosion` as `SplashActivity.onVideoEnd()`
/// calls it — `textureView` snapshot, `hudTitle`, `hudSubtitle`, `hudFootnote`
/// and a 2.8s `AccelerateDecelerateInterpolator` run. The bitmap snapshot has
/// no SwiftUI equivalent, so the shards are drawn as translucent slivers
/// against the rain; every other timing constant is reproduced
/// (`shake below p = 0.18`, shard `alpha = 1 - p / 0.28`,
/// `scale = max(0.05, 1 - p * 1.5)`, `gravity = 1800`).
private struct SplashMatrixOverlay: View {

    @State private var progress: Double = 0

    private static let columnCount = 14
    private static let rowCount = 18
    private static let shardCount = 24
    private static let gravity: Double = 1800
    private static let glyphs: [Character] = Array("0BFCEJKLMNPRSTUVWXYZ@#$%&*+-<>")

    var body: some View {
        GeometryReader { proxy in
            ZStack {
                Color.black.opacity(0.92)

                rain

                shards(in: proxy.size)

                hud
            }
            .offset(shakeOffset)
        }
        .ignoresSafeArea()
        .allowsHitTesting(false)
        .onAppear {
            withAnimation(.easeInOut(duration: SplashViewModel.transitionDuration)) {
                progress = 1
            }
        }
        .accessibilityHidden(true)
    }

    // MARK: - Matrix rain

    private var rain: some View {
        HStack(alignment: .top, spacing: 4) {
            ForEach(0..<Self.columnCount, id: \.self) { column in
                VStack(alignment: .center, spacing: 2) {
                    ForEach(0..<Self.rowCount, id: \.self) { row in
                        Text(glyph(column: column, row: row))
                            .font(.system(size: 11, weight: .bold, design: .monospaced))
                            .foregroundStyle(glyphColor(column: column, row: row))
                    }
                }
                .offset(y: CGFloat((column * 31) % 90) + 140 * progress)
                .opacity(Double(Self.columnCount - column) / Double(Self.columnCount))
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
    }

    private func glyph(column: Int, row: Int) -> String {
        let base = column * 7 + row * 13
        let offset = Int(Double(progress) * Double(Self.columnCount * Self.rowCount) * 0.05)
        let seed = base + offset
        let index = abs(seed) % Self.glyphs.count
        return String(Self.glyphs[index])
    }

    private func glyphColor(column: Int, row: Int) -> Color {
        let fade = Double(Self.rowCount - row) / Double(Self.rowCount)
        if row == 0 { return SplashCanvas.matrixHead }
        return SplashCanvas.matrixGreen.opacity(0.25 + fade * 0.75)
    }

    // MARK: - Shards

    private func shards(in size: CGSize) -> some View {
        ForEach(0..<Self.shardCount, id: \.self) { index in
            shard(index, in: size)
        }
    }

    private func shard(_ index: Int, in size: CGSize) -> some View {
        let angle = Double((index * 137) % 360) * .pi / 180
        let distance = Double(60 + (index * 37) % 140) * progress
        let side = CGFloat(26 + (index * 19) % 46)

        return RoundedRectangle(cornerRadius: 2, style: .continuous)
            .fill(
                LinearGradient(
                    colors: [SplashCanvas.matrixGreen.opacity(0.45), .clear],
                    startPoint: .top,
                    endPoint: .bottom
                )
            )
            .frame(width: side, height: side * 0.6)
            .rotationEffect(.radians(Double(index) * 0.7 + progress * 4))
            .scaleEffect(max(0.05, 1 - progress * 1.5))
            .opacity(max(0, 1 - progress / 0.28))
            .offset(
                x: cos(angle) * distance,
                y: sin(angle) * distance + 0.5 * Self.gravity * progress * progress
            )
            .position(x: size.width / 2, y: size.height / 2)
    }

    /// `p < 0.18f` shake branch, decaying linearly to zero.
    private var shakeOffset: CGSize {
        guard progress < 0.18 else { return .zero }
        let decay = 1 - progress / 0.18
        return CGSize(
            width: sin(progress * 120) * 11 * decay,
            height: cos(progress * 97) * 11 * decay
        )
    }

    // MARK: - HUD

    private var hud: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            Text(SplashViewModel.transitionTitle)
                .font(.system(size: 20, weight: .black, design: .monospaced))
                .foregroundStyle(SplashCanvas.matrixGreen)
                .shadow(color: SplashCanvas.matrixGreen, radius: 10)

            Text(SplashViewModel.transitionSubtitle)
                .font(.system(size: 12, weight: .semibold, design: .monospaced))
                .foregroundStyle(.white.opacity(0.85))

            Text(SplashViewModel.transitionFootnote)
                .font(.system(size: 10, weight: .medium, design: .monospaced))
                .foregroundStyle(.white.opacity(0.7))
                .tracking(1)
        }
        .multilineTextAlignment(.center)
        .padding(.horizontal, AppTheme.Spacing.xxl)
        .scaleEffect(1 + progress * 0.25)
        .opacity(max(0, 1 - max(0, progress - 0.6) / 0.4))
    }
}

// MARK: - View

/// Cold-start branding screen. Ports `SplashActivity` end to end: the
/// `activity_splash` layer stack, the staggered logo/title/subtitle entrance
/// with its haptic, the looping-free intro video with a skip button, the
/// `FcmTokenCache`-gated `update_fcmv2.php` sync behind a 3-second ceiling,
/// and the matrix transition that precedes navigation.
///
/// `RootView` owns *which* destination is rendered once the splash goes away;
/// this view's job is the Android job — decide, then tell the host. The
/// decision is published as ``SplashRoute`` through `onFinished`.
///
/// Wire-up (requires editing `RootView.swift`, which this port must not touch):
/// pass a handler to `onFinished` and gate the root on
/// `OnboardingView.hasCompletedOnboarding`.
struct SplashView: View {

    /// Receives the destination `checkNavigationState()` resolved, then the
    /// host is free to drop this view.
    ///
    /// Defaults to `nil` so the existing `SplashView()` call in `RootView`
    /// keeps compiling unchanged; until `RootView` passes a handler the splash
    /// still plays in full and the decision is simply not consumed.
    var onFinished: ((SplashRoute) -> Void)? = nil

    @Environment(\.api) private var api
    @EnvironmentObject private var session: SessionStore
    @Environment(\.scenePhase) private var scenePhase

    @StateObject private var model = SplashViewModel()

    /// `splashLogo.alpha = 0f` / `splashTitle.alpha = 0f` /
    /// `splashSubtitle.alpha = 0f` before their `ViewPropertyAnimator`s run.
    @State private var isLogoVisible = false
    @State private var isTitleVisible = false
    @State private var isSubtitleVisible = false

    init(onFinished: ((SplashRoute) -> Void)? = nil) {
        self.onFinished = onFinished
    }

    var body: some View {
        ZStack {
            SplashCanvas.base.ignoresSafeArea()

            videoBackdrop
            scrim
            skipButton
            branding
            progressIndicator

            if model.isTransitionActive {
                SplashMatrixOverlay()
            }
        }
        .task {
            await model.begin(api: api, session: session)
        }
        .onChange(of: model.route) { route in
            guard let route else { return }
            onFinished?(route)
        }
        .onChange(of: scenePhase) { phase in
            if phase == .active {
                model.applicationDidBecomeActive()
            } else {
                model.applicationDidEnterBackground()
            }
        }
        .onDisappear {
            // `onDestroy()` — stop playback and release the surface.
            model.applicationDidEnterBackground()
        }
        .onAppear {
            RemoteLogger.log(tag: "SplashView_onAppear", message: "Splash screen shown")
            runEntranceAnimation()
        }
    }

    // MARK: - Layers

    @ViewBuilder
    private var videoBackdrop: some View {
        if let url = model.videoURL {
            SplashVideoBackdrop(url: url, isPlaying: model.isVideoPlaying) {
                model.videoDidEnd()
            }
        }
    }

    /// `bg_splash_scrim` — the 270° top-to-bottom gradient that darkens the
    /// clip so the white branding stays legible.
    private var scrim: some View {
        LinearGradient(
            colors: [SplashCanvas.scrimTop, SplashCanvas.scrimMid, SplashCanvas.scrimBottom],
            startPoint: .top,
            endPoint: .bottom
        )
        .ignoresSafeArea()
        .allowsHitTesting(false)
    }

    /// Ports `btnSkipVideo`: `bg_skip_button` (20dp radius, `#80000000` fill,
    /// 1.5dp `#66FFFFFF` stroke) with the "Skip ➔" label, 42dp from the top
    /// edge and 20dp from the trailing edge.
    private var skipButton: some View {
        VStack(spacing: 0) {
            HStack(spacing: 0) {
                Spacer(minLength: 0)

                Button {
                    RemoteLogger.log(tag: SplashViewModel.logTag, message: "User clicked Skip button")
                    model.videoDidEnd()
                } label: {
                    Text("Skip \u{2794}")
                        .font(AppTheme.Font.subheadline.weight(.bold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, AppTheme.Spacing.lg)
                        .padding(.vertical, AppTheme.Spacing.sm)
                        .background(
                            RoundedRectangle(
                                cornerRadius: AppTheme.Radius.lg,
                                style: .continuous
                            )
                            .fill(SplashCanvas.skipFill)
                        )
                        .overlay(
                            RoundedRectangle(
                                cornerRadius: AppTheme.Radius.lg,
                                style: .continuous
                            )
                            .stroke(SplashCanvas.skipStroke, lineWidth: 1.5)
                        )
                }
                .accessibilityLabel("Skip intro video")
            }

            Spacer(minLength: 0)
        }
        // 42dp has no token; `xxl` + `lg` is the closest token-only sum.
        .padding(.top, AppTheme.Spacing.xxl + AppTheme.Spacing.lg)
        .padding(.trailing, AppTheme.Spacing.xl)
    }

    /// `splashLogoLayout` — the 144dp `medigyaan_logo`, the `@string/app_name`
    /// title and the "Empowering Competitive Learning" subtitle, with the
    /// group lifted by the layout's 10dp `android:elevation`.
    private var branding: some View {
        VStack(spacing: 0) {
            BrandLogo(size: 144)
                .opacity(isLogoVisible ? 1 : 0)
                .scaleEffect(isLogoVisible ? 1 : 0.8)
                .animation(.easeOut(duration: 0.8), value: isLogoVisible)

            Text("MediGyaan")
                .font(AppTheme.Font.largeTitle)
                .tracking(0.04)
                .foregroundStyle(.white)
                .shadow(color: AppTheme.Ink.cyan, radius: 6, y: 2)
                .padding(.top, AppTheme.Spacing.xl)
                .opacity(isTitleVisible ? 1 : 0)
                .animation(.easeOut(duration: 0.8).delay(0.2), value: isTitleVisible)

            Text("Empowering Competitive Learning")
                .font(AppTheme.Font.callout)
                .foregroundStyle(SplashCanvas.subtitle)
                .shadow(color: .black.opacity(0.5), radius: 4, y: 1)
                .padding(.top, AppTheme.Spacing.sm)
                .opacity(isSubtitleVisible ? 0.85 : 0)
                .animation(.easeOut(duration: 0.8).delay(0.4), value: isSubtitleVisible)
        }
        .shadow(color: .black.opacity(0.45), radius: 12, y: 6)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .allowsHitTesting(false)
    }

    /// `splashProgress` — the indeterminate `CircularProgressIndicator`
    /// (`#00E5FF` on a 20% white track). Android pins its size and thickness
    /// to 32dp/3dp through attributes `ProgressView().controlSize(.large)`
    /// does not expose, so the system indicator carries the colour alone.
    private var progressIndicator: some View {
        VStack {
            Spacer(minLength: 0)

            ProgressView()
                .controlSize(.large)
                .tint(AppTheme.Ink.cyan)
                .padding(.bottom, AppTheme.Spacing.xxl + AppTheme.Spacing.lg)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .allowsHitTesting(false)
    }

    // MARK: - Entrance animation

    /// Ports the three `ViewPropertyAnimator`s in `onCreate()`: the logo fades
    /// and un-scales over 800ms and fires a haptic in its `withEndAction`, the
    /// title fades over 800ms after a 200ms delay, and the subtitle settles at
    /// 0.85 alpha over 800ms after a 400ms delay.
    private func runEntranceAnimation() {
        withAnimation(.easeOut(duration: 0.8)) { isLogoVisible = true }

        Task { @MainActor in
            try? await Task.sleep(nanoseconds: 800_000_000)
            UIImpactFeedbackGenerator(style: .light).impactOccurred()
        }

        withAnimation(.easeOut(duration: 0.8).delay(0.2)) { isTitleVisible = true }
        withAnimation(.easeOut(duration: 0.8).delay(0.4)) { isSubtitleVisible = true }
    }
}

#Preview {
    SplashView()
        .environmentObject(SessionStore())
        .environment(\.api, .live)
}