import SwiftUI

// MARK: - Screen chrome

/// Which of the two Android visual languages a screen is painted in.
///
/// `BaseActivity` set no background of its own — every layout supplied one — so
/// this mirrors that split rather than picking a winner. See ``AppTheme`` for
/// why the two coexist.
enum BaseScreenStyle {
    /// `colorBackground` — login, leaderboard, messenger, profile, settings.
    case material
    /// `#07111F` — dashboard, referral, predictor, accuracy.
    case ink
}

/// Ports the `when (itemId)` table in `BaseActivity.handleNavigation`, keyed by
/// the `@+id` values it switches on in `menu/bottom_nav_menu.xml` and
/// `menu/sidebar_menu.xml`.
///
/// Raw values are the Android resource ids verbatim, so a log line, a
/// `MenuEntry.id` or the Kotlin source all line up one-to-one. Core cannot name
/// the SwiftUI screens these ids resolve to — `handleNavigation` returned
/// `Activity` classes — so each case carries the activity it used to start and
/// leaves the presentation to the call site.
enum BaseNavigationItem: String, CaseIterable, Hashable {

    // menu/bottom_nav_menu.xml
    case home = "nav_home"
    case aiChat = "nav_reels"
    case search = "nav_search"
    case history = "nav_feed"
    case messages = "nav_messages"

    // menu/sidebar_menu.xml
    case researchWorkspace = "side_research_workspace"
    case profile = "side_profile"
    case sharedQuestions = "side_pdfs"
    case quizzes = "side_scores"
    case referral = "side_referral"
    case settings = "side_settings"
    case editProfile = "side_edit_profile"
    case widgetSettings = "side_widget_settings"
    case goal = "side_goal"
    case contact = "side_contact"
    case help = "side_help"

    /// The five items that render in the bottom bar, as opposed to the drawer.
    var isTab: Bool {
        switch self {
        case .home, .aiChat, .search, .history, .messages: return true
        default: return false
        }
    }

    /// `android:title` exactly as declared in `menu/*.xml`.
    var title: String {
        switch self {
        case .home: return "Home"
        case .aiChat: return "AI Chat"
        case .search: return "Search"
        case .history: return "History"
        case .messages: return "Messages"
        case .researchWorkspace: return "Research Workspace"
        case .profile: return "My Profile"
        case .sharedQuestions: return "Shared Questions"
        case .quizzes: return "My Quizzes"
        case .referral: return "Refer & Earn XP"
        case .settings: return "Settings"
        case .editProfile: return "Edit Profile"
        case .widgetSettings: return "Widget Settings"
        case .goal: return "Goal"
        case .contact: return "Contact Us"
        case .help: return "Help & Support"
        }
    }

    /// `android:icon`. Only the bottom-nav items declare one — every
    /// `sidebar_menu.xml` entry is title-only — so the drawer cases return `nil`
    /// and render as plain text, exactly as Android does.
    var icon: AndroidAsset? {
        switch self {
        case .home: return .ic_home
        case .aiChat: return .ic_comment
        case .search: return .ic_search
        case .history: return .ic_feed
        case .messages: return .ic_message
        case .profile: return .ic_person
        case .sharedQuestions: return .ic_pdf_library
        case .quizzes: return .ic_score
        case .settings: return .ic_settings
        case .contact, .help: return .ic_help
        case .researchWorkspace, .referral, .editProfile, .widgetSettings, .goal: return nil
        }
    }

    /// The activity `handleNavigation` started for this id. `side_contact` routed
    /// to `SupportActivity` even though its title reads "Contact Us".
    var androidActivity: String {
        switch self {
        case .home: return "DashboardActivity"
        case .messages: return "MessengerActivity"
        case .history: return "ChallengeListActivity"
        case .aiChat: return "AiChatActivity"
        case .search: return "GlobalSearchActivity"
        case .profile: return "ProfileActivity"
        case .settings: return "SettingsActivity"
        case .editProfile: return "EditProfileActivity"
        case .sharedQuestions: return "SharedQuestionsActivity"
        case .quizzes: return "QuizManagerActivity"
        case .referral: return "ReferralActivity"
        case .widgetSettings: return "WidgetSettingsActivity"
        case .goal: return "GoalActivity"
        case .contact: return "SupportActivity"
        case .help: return "HelpActivity"
        case .researchWorkspace: return "ResearchWorkspaceActivity"
        }
    }

    /// `MenuEntry` carries the Android id verbatim, so a drawer row resolves
    /// straight through.
    static func item(for menuEntry: MenuEntry) -> BaseNavigationItem? {
        BaseNavigationItem(rawValue: menuEntry.id)
    }
}

// MARK: - Global battle invites

/// The three extras `BaseActivity`'s `inviteReceiver` read off a
/// `CHALLENGE_INVITE` broadcast: `lobby_id`, `host_name` and `timestamp`.
///
/// Narrower than ``ChallengeInvitation``, which needs the subject/topic/mode of
/// a specific challenge; the receiver never looked at those.
struct GlobalBattleInvite: Identifiable, Equatable {

    /// Substituted for a missing `host_name`, as in the Kotlin receiver.
    static let fallbackHost = "Friend"

    let lobbyID: String
    let hostName: String
    /// Derived from the millisecond `timestamp` extra.
    let sentAt: Date

    var id: String { lobbyID }

    init(lobbyID: String, hostName: String? = nil, sentAt: Date = Date()) {
        self.lobbyID = lobbyID
        self.hostName = hostName ?? Self.fallbackHost
        self.sentAt = sentAt
    }

    /// Mirrors `intent.getStringExtra("timestamp")?.toLongOrNull() ?: 0L`, where
    /// an absent or unparsable extra collapses to "too old to show".
    init?(lobbyID: String, hostName: String?, timestampMillis: String?) {
        guard !lobbyID.isEmpty else { return nil }
        guard let millis = timestampMillis.flatMap({ Double($0) }), millis > 0 else { return nil }
        self.init(
            lobbyID: lobbyID,
            hostName: hostName,
            sentAt: Date(timeIntervalSince1970: millis / 1000)
        )
    }
}

/// Ports the invite bookkeeping `BaseActivity` kept in `acceptedInvites` and
/// `shownInvites`, together with the five-minute freshness window its
/// `inviteReceiver` applied before surfacing anything.
///
/// Kotlin held those sets per activity, so a lobby id only deduplicated within
/// the screen that received it and a push redelivered on another screen popped
/// a second banner. One shared instance is the equivalent iOS arrangement: build
/// it once at the root and hand the same object to every screen.
///
/// Main-actor only — written from the push plumbing, read by
/// ``GlobalInviteFallbackModifier``.
final class GlobalInviteCenter: ObservableObject {

    /// Android ignored an invite older than `5 * 60 * 1000L`.
    static let freshnessWindow: TimeInterval = 5 * 60

    /// The invite being surfaced right now, cleared once dismissed.
    @Published private(set) var pending: GlobalBattleInvite?

    private var accepted: Set<String> = []
    private var shown: Set<String> = []

    /// Applies the receiver's guards in order — already accepted, already shown,
    /// older than ``freshnessWindow`` — and reports whether it surfaced.
    @discardableResult
    func receive(_ invite: GlobalBattleInvite) -> Bool {
        guard !accepted.contains(invite.lobbyID) else { return false }
        guard !shown.contains(invite.lobbyID) else { return false }
        guard Date().timeIntervalSince(invite.sentAt) <= Self.freshnessWindow else { return false }
        shown.insert(invite.lobbyID)
        pending = invite
        return true
    }

    /// Marks a lobby as taken so a redelivered push never re-prompts.
    func accept(lobbyID: String) {
        accepted.insert(lobbyID)
        if pending?.lobbyID == lobbyID { pending = nil }
    }

    /// Dismisses the banner without accepting. The invite stays suppressed
    /// because receiving it already added it to `shown`.
    func clear() {
        pending = nil
    }
}

// MARK: - The modifier

/// Ports `BaseActivity`: the chrome every screen inherits — Material or ink
/// background, the `Activity_Create` / `Activity_Resume` telemetry keyed on the
/// screen name, an optional navigation title, and the global-invite fallback
/// `showGlobalInvite` rendered as a Toast.
///
/// SwiftUI has no activity superclass, so the setup Kotlin funnelled through
/// `onCreate` becomes a modifier each screen applies once. Android's system back
/// button needs no counterpart here: `NavigationStack` already pops on the
/// interactive swipe, which is what `handleNavigation`'s
/// `FLAG_ACTIVITY_REORDER_TO_FRONT` existed to work around.
struct BaseScreenModifier: ViewModifier {

    @Environment(\.scenePhase) private var scenePhase

    /// `this::class.java.simpleName` on Android, kept verbatim so the two apps'
    /// telemetry lines read the same.
    let screen: String
    var style: BaseScreenStyle = .material
    var title: String?
    var navigationBarDisplayMode: NavigationBarItem.TitleDisplayMode = .inline
    /// Leave `nil` where the screen draws its own invite UI — `DashboardView`
    /// shows a banner with an Accept button rather than the Toast fallback.
    var inviteCenter: GlobalInviteCenter?

    @ViewBuilder
    func body(content: Content) -> some View {
        let base = titled(chrome(content))
            .onAppear {
                self.announce(tag: "Activity_Create", verb: "created")
                if self.scenePhase == .active { self.announce(tag: "Activity_Resume", verb: "resumed") }
            }
            .onChange(of: scenePhase) { phase in
                if phase == .active { self.announce(tag: "Activity_Resume", verb: "resumed") }
            }

        if let inviteCenter {
            base.modifier(GlobalInviteFallbackModifier(center: inviteCenter))
        } else {
            base
        }
    }

    @ViewBuilder
    private func chrome(_ view: Content) -> some View {
        switch style {
        case .material:
            view
                .screenBackground()
                .navigationBarTitleDisplayMode(navigationBarDisplayMode)
        case .ink:
            view
                .inkBackground()
                .navigationBarTitleDisplayMode(navigationBarDisplayMode)
        }
    }

    @ViewBuilder
    private func titled<V: View>(_ view: V) -> some View {
        if let title {
            view.navigationTitle(title)
        } else {
            view
        }
    }

    private func announce(tag: String, verb: String) {
        RemoteLogger.log(
            tag: tag,
            message: "\(screen) \(verb)",
            metadata: ["activity": screen]
        )
    }
}

/// Ports `showGlobalInvite` — the fallback `BaseActivity` used when no subclass
/// overrode it — as a banner that clears itself after roughly the
/// `Toast.LENGTH_LONG` window.
private struct GlobalInviteFallbackModifier: ViewModifier {

    /// `Toast.LENGTH_LONG` shows for about 3.5 seconds.
    private static let displayDuration: UInt64 = 3_500_000_000

    @ObservedObject var center: GlobalInviteCenter
    @State private var visibleInvite: GlobalBattleInvite?

    func body(content: Content) -> some View {
        content
            .overlay(alignment: .top) {
                if let visibleInvite {
                    GlobalInviteBanner(invite: visibleInvite)
                        .padding(.horizontal, AppTheme.Spacing.xl)
                        .padding(.top, AppTheme.Spacing.md)
                        .transition(.move(edge: .top).combined(with: .opacity))
                }
            }
            .animation(.easeOut(duration: 0.2), value: visibleInvite)
            .onAppear { self.present(self.center.pending) }
            .onChange(of: center.pending) { pending in self.present(pending) }
    }

    @MainActor
    private func present(_ pending: GlobalBattleInvite?) {
        guard let pending else {
            visibleInvite = nil
            return
        }
        visibleInvite = pending
        Task {
            try? await Task.sleep(nanoseconds: Self.displayDuration)
            if self.visibleInvite?.id == pending.id { self.visibleInvite = nil }
        }
    }
}

/// The `"⚔️ $host invited you!"` Toast, drawn as a capsule because iOS has no
/// Toast to fall back on.
private struct GlobalInviteBanner: View {

    let invite: GlobalBattleInvite

    var body: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            Image(systemName: "bolt.horizontal.circle.fill")
                .font(.system(size: 18, weight: .semibold))
                .foregroundStyle(AppTheme.Ink.gold)
            Text("⚔️ \(invite.hostName) invited you!")
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Ink.textPrimary)
                .lineLimit(2)
            Spacer(minLength: 0)
        }
        .padding(.horizontal, AppTheme.Spacing.lg)
        .padding(.vertical, AppTheme.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.materialCard, style: .continuous)
                .fill(AppTheme.Ink.elevated)
        )
        .shadow(color: .black.opacity(0.25), radius: AppTheme.Elevation.card, y: 2)
    }
}

/// Ports `BaseActivity.setupNavigation` / `handleNavigation`: route to the item's
/// destination unless the screen already *is* that destination.
private struct BaseNavigationModifier: ViewModifier {

    let item: BaseNavigationItem
    let current: BaseNavigationItem?
    let perform: () -> Void

    func body(content: Content) -> some View {
        Button {
            // Kotlin: `currentActivity != targetActivity`, which stopped the
            // REORDER_TO_FRONT intent from stacking the screen onto itself.
            guard current != item else { return }
            RemoteLogger.log(
                tag: "Navigation_Tap",
                message: "\(item.rawValue) -> \(item.androidActivity)",
                metadata: ["item": item.rawValue, "activity": item.androidActivity]
            )
            perform()
        } label: {
            content
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Call sites

extension View {

    /// Ports `BaseActivity`'s per-screen setup — see ``BaseScreenModifier``.
    ///
    /// ```swift
    /// ProfileView()
    ///     .baseScreen("ProfileActivity", title: "My Profile")
    /// ```
    func baseScreen(
        _ screen: String,
        style: BaseScreenStyle = .material,
        title: String? = nil,
        navigationBarDisplayMode: NavigationBarItem.TitleDisplayMode = .inline,
        invites: GlobalInviteCenter? = nil
    ) -> some View {
        modifier(
            BaseScreenModifier(
                screen: screen,
                style: style,
                title: title,
                navigationBarDisplayMode: navigationBarDisplayMode,
                inviteCenter: invites
            )
        )
    }

    /// Ports `setupNavigation` / `handleNavigation`: dismiss whatever chrome the
    /// item lives in, then route — skipping the hop when this screen already
    /// shows the destination. Apply to the tap target itself:
    ///
    /// ```swift
    /// Text("My Profile")
    ///     .baseNavigation(to: .profile, current: .home) { path.append(.profile) }
    /// ```
    func baseNavigation(
        to item: BaseNavigationItem,
        current: BaseNavigationItem? = nil,
        perform: @escaping () -> Void
    ) -> some View {
        modifier(BaseNavigationModifier(item: item, current: current, perform: perform))
    }
}