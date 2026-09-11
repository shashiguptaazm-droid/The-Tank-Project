import SwiftUI

/// Home tab — a faithful port of `activity_dashboard.xml`.
///
/// The Android dashboard does **not** use the Material theme: it hardcodes its
/// own dark "ink" palette (~148 literal hex values), a 68dp top bar, a 14dp-radius
/// search field, a profile summary card, a two-up rank row, a four-up stats card,
/// five battle-mode cards, four quick tiles, a streak card and an invite card.
/// All of that is reproduced here against `AppTheme.Ink`.
struct DashboardView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @AppStorage("mg.darkMode") private var darkMode = false

    @StateObject private var viewModel = DashboardViewModel()
    @State private var hasConfigured = false
    @State private var searchText = ""
    @State private var isShowingSearch = false
    @State private var isShowingMenu = false

    private var stats: DashboardStats { viewModel.state.value ?? .empty }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                topBar
                content
            }
            .inkBackground()
            .toolbar(.hidden, for: .navigationBar)
            .navigationDestination(isPresented: $isShowingSearch) { GlobalSearchView() }
            .sheet(isPresented: $isShowingMenu) { drawer }
            .task {
                guard !hasConfigured else { return }
                hasConfigured = true
                await reload()
            }
        }
    }

    // MARK: - Top bar (68dp, ids: menuBtn / logoImage / btnMessenger / btnThemeToggle)

    private var topBar: some View {
        HStack(spacing: 0) {
            Button { isShowingMenu = true } label: {
                Image(systemName: "line.3.horizontal")
                    .font(.system(size: 18, weight: .medium))
                    .frame(width: 42, height: 42)
                    .foregroundStyle(AppTheme.Ink.iconTint)
            }

            // 116x38 logo slot.
            HStack(spacing: AppTheme.Spacing.xs) {
                Image(systemName: "cross.case.fill")
                    .font(.system(size: 22, weight: .semibold))
                    .foregroundStyle(AppTheme.Ink.teal)
                Text("MediGyaan")
                    .font(.system(size: 19, weight: .bold))
                    .foregroundStyle(AppTheme.Ink.textPrimary)
            }
            .frame(height: 38)
            .padding(.leading, 10)

            Spacer()

            NavigationLink { MessengerView() } label: {
                Image(systemName: "bubble.left.and.bubble.right.fill")
                    .font(.system(size: 17))
                    .frame(width: 44, height: 44)
                    .foregroundStyle(AppTheme.Ink.teal)
            }
            .padding(.trailing, 6)

            Button { darkMode.toggle() } label: {
                Image(systemName: darkMode ? "sun.max.fill" : "moon.fill")
                    .font(.system(size: 17))
                    .frame(width: 44, height: 44)
                    .foregroundStyle(AppTheme.Ink.iconTint)
            }
        }
        .padding(.horizontal, AppTheme.Spacing.lg)
        .frame(height: 68)
    }

    // MARK: - Scroll content

    private var content: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.md) {
                searchField
                profileSummaryCard
                rankRow
                detailsCard
                battleModes
                quickTiles
                streakCard
                invitationCard
            }
            .padding(.horizontal, AppTheme.Spacing.lg)
            .padding(.bottom, 112)
        }
        .refreshable { await reload() }
    }

    /// Hint "Search questions, topics, users", `#0D1A2B` box, `#48D6C8` stroke,
    /// 14dp radius. Android makes it non-focusable so it navigates on tap.
    private var searchField: some View {
        Button { isShowingSearch = true } label: {
            HStack(spacing: AppTheme.Spacing.sm) {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(AppTheme.Ink.textHint)
                Text("Search questions, topics, users")
                    .font(AppTheme.Font.body)
                    .foregroundStyle(AppTheme.Ink.textHint)
                Spacer()
            }
            .padding(.horizontal, AppTheme.Spacing.lg)
            .frame(height: 52)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.field, style: .continuous)
                    .fill(AppTheme.Ink.surface)
            )
            .overlay(
                RoundedRectangle(cornerRadius: AppTheme.Radius.field, style: .continuous)
                    .stroke(AppTheme.Ink.teal, lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
        .padding(.top, AppTheme.Spacing.xs)
    }

    /// `#0C2036` card, 18dp radius, `#2B80E7` stroke, 76dp gold-ringed avatar.
    private var profileSummaryCard: some View {
        InkCard(
            fill: AppTheme.Ink.profileCard,
            stroke: AppTheme.Ink.blue,
            radius: AppTheme.Radius.materialCard
        ) {
            HStack(spacing: 14) {
                AvatarView(
                    url: session.currentUser?.avatarURL,
                    name: session.currentUser?.name ?? "Aspirant",
                    size: 76,
                    strokeColor: AppTheme.Ink.gold,
                    strokeWidth: 2,
                    backdrop: AppTheme.Ink.avatarBackdrop
                )
                .padding(2)

                VStack(alignment: .leading, spacing: 2) {
                    Text("🌱 \(displayName)")
                        .font(AppTheme.Font.title)
                        .foregroundStyle(AppTheme.Ink.textPrimary)
                        .lineLimit(1)

                    Text("\(stats.streak) Days Active")
                        .font(AppTheme.Font.subheadline)
                        .foregroundStyle(AppTheme.Ink.textSecondary)
                        .padding(.top, 2)

                    Text("\(xpEarned) / \(xpGoal) XP")
                        .font(AppTheme.Font.captionBold)
                        .foregroundStyle(AppTheme.Ink.gold)
                        .padding(.top, 4)
                }

                Spacer(minLength: 0)
            }
        }
    }

    /// Two 166dp cards: "Current Rank ⚡" and the AI predicted rank inset.
    private var rankRow: some View {
        HStack(spacing: AppTheme.Spacing.split) {
            InkCard(
                fill: AppTheme.Ink.rankCard,
                stroke: AppTheme.Ink.slate,
                radius: AppTheme.Radius.card
            ) {
                VStack(spacing: AppTheme.Spacing.xs) {
                    Text("Current Rank ⚡")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Ink.textSecondary)

                    ZStack {
                        Circle()
                            .fill(AppTheme.Ink.elevated.opacity(0.6))
                            .frame(width: 54, height: 54)
                        Text(rankBadge)
                            .font(AppTheme.Font.display)
                    }

                    Text(stats.rank > 0 ? "#\(stats.rank)" : "—")
                        .font(AppTheme.Font.headline)
                        .foregroundStyle(AppTheme.Ink.textPrimary)

                    NavigationLink { LeaderboardView() } label: {
                        Text("Details")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Ink.teal)
                    }
                }
                .frame(maxWidth: .infinity)
                .frame(height: 166 - (AppTheme.Spacing.lg * 2))
            }

            InkCard(
                fill: AppTheme.Ink.predictionCard,
                radius: AppTheme.Radius.card
            ) {
                VStack(spacing: AppTheme.Spacing.xs) {
                    Text("AI Predicted Rank")
                        .font(AppTheme.Font.subheadline)
                        .foregroundStyle(AppTheme.Ink.textSecondary)

                    Text(stats.rank > 0 ? "#\(max(1, stats.rank - 25))" : "--")
                        .font(AppTheme.Font.prediction)
                        .foregroundStyle(AppTheme.Ink.cyan)

                    Text(stats.accuracy > 0 ? "Confidence stable" : "Confidence pending")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Ink.textSecondary)
                        .multilineTextAlignment(.center)

                    NavigationLink { PredictorView() } label: {
                        Text("Details")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Ink.teal)
                    }
                }
                .frame(maxWidth: .infinity)
                .frame(height: 166 - (AppTheme.Spacing.lg * 2))
            }
        }
    }

    /// `#0D1A2B` card with Wins / Accuracy / Streak / Battles.
    private var detailsCard: some View {
        InkCard(fill: AppTheme.Ink.surface, radius: AppTheme.Radius.card) {
            HStack(spacing: 0) {
                InkStatTile(value: "\(stats.correct)", label: "Wins ✅")
                divider
                InkStatTile(value: String(format: "%.0f%%", percentileAccuracy), label: "Accuracy 🎯")
                divider
                InkStatTile(value: "\(stats.streak)", label: "Streak")
                divider
                InkStatTile(value: "\(max(stats.attempted, stats.totalTests))", label: "Battles 🏆")
            }
        }
    }

    private var divider: some View {
        Rectangle()
            .fill(AppTheme.Ink.slate.opacity(0.5))
            .frame(width: 1, height: 34)
    }

    /// "Battle Modes ⚔️" + five tinted mode cards.
    private var battleModes: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
            VStack(alignment: .leading, spacing: 2) {
                Text("Battle Modes ⚔️")
                    .font(AppTheme.Font.section)
                    .foregroundStyle(AppTheme.Ink.textPrimary)
                Text("Choose your run")
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Ink.textSecondary)
            }

            LazyVGrid(
                columns: [
                    GridItem(.flexible(), spacing: AppTheme.Spacing.split),
                    GridItem(.flexible(), spacing: AppTheme.Spacing.split),
                ],
                spacing: AppTheme.Spacing.split
            ) {
                NavigationLink { MatchmakingView() } label: {
                    BattleModeCard(
                        tag: "⚔️ RANKED",
                        emoji: "🧭",
                        title: "Find Match ⚔️",
                        subtitle: "Climb with live opponents",
                        fill: AppTheme.Ink.ranked
                    )
                }
                .buttonStyle(.plain)

                NavigationLink { TopicChallengePickerView(mode: .challenge) } label: {
                    BattleModeCard(
                        tag: "👥 FRIENDS",
                        emoji: "🤝",
                        title: "Challenge",
                        subtitle: "Invite your close friends",
                        fill: AppTheme.Ink.friends
                    )
                }
                .buttonStyle(.plain)

                NavigationLink { TopicChallengePickerView(mode: .solo) } label: {
                    BattleModeCard(
                        tag: "⚡ FAST",
                        emoji: "🚀",
                        title: "Rapid Fire",
                        subtitle: "Practice one MCQ at a time",
                        fill: AppTheme.Ink.rapidFire
                    )
                }
                .buttonStyle(.plain)

                NavigationLink { TopicsView() } label: {
                    BattleModeCard(
                        tag: "🎮 TEST",
                        emoji: "🏁",
                        title: "Test Mode",
                        subtitle: "Subject-wise scoring run",
                        fill: AppTheme.Ink.testMode
                    )
                }
                .buttonStyle(.plain)

                NavigationLink { ChallengeListView() } label: {
                    BattleModeCard(
                        tag: "🛡️ CUSTOM",
                        emoji: "🛡️",
                        title: "Create Room",
                        subtitle: "Host a private battle",
                        fill: AppTheme.Ink.custom
                    )
                }
                .buttonStyle(.plain)
            }
        }
    }

    /// Four `#132238` tiles with 30sp emoji.
    private var quickTiles: some View {
        LazyVGrid(
            columns: [
                GridItem(.flexible(), spacing: AppTheme.Spacing.split),
                GridItem(.flexible(), spacing: AppTheme.Spacing.split),
            ],
            spacing: AppTheme.Spacing.split
        ) {
            NavigationLink { LeaderboardView() } label: {
                QuickTile(emoji: "🏆", title: "Leaderboard")
            }
            .buttonStyle(.plain)

            NavigationLink { HistoryView() } label: {
                QuickTile(emoji: "📜", title: "History")
            }
            .buttonStyle(.plain)

            NavigationLink { TopicsView() } label: {
                QuickTile(emoji: "📚", title: "Subjects")
            }
            .buttonStyle(.plain)

            NavigationLink { ReferralView() } label: {
                QuickTile(emoji: "💌", title: "Referral")
            }
            .buttonStyle(.plain)
        }
    }

    /// `#2B1B18` streak card.
    private var streakCard: some View {
        InkCard(fill: AppTheme.Ink.streakCard, radius: AppTheme.Radius.card) {
            HStack(spacing: AppTheme.Spacing.md) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("🔥 Daily Learning Streak")
                        .font(AppTheme.Font.cardTitle)
                        .foregroundStyle(AppTheme.Ink.textPrimary)
                    Text("\(stats.streak) Days Active")
                        .font(AppTheme.Font.subheadline)
                        .foregroundStyle(AppTheme.Ink.textSecondary)
                    if stats.todayAttempted > 0 {
                        Text("\(stats.todayCorrect)/\(stats.todayAttempted) correct today")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Ink.success)
                    }
                }
                Spacer()
            }
        }
    }

    /// `#2D2341` invite card, shown once there is something to act on.
    @ViewBuilder
    private var invitationCard: some View {
        if stats.streak == 0, stats.attempted == 0 {
            InkCard(fill: AppTheme.Ink.invitation, radius: AppTheme.Radius.card) {
                VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
                    Text("Battle invite ⚔️")
                        .font(AppTheme.Font.callout)
                        .foregroundStyle(AppTheme.Ink.textPrimary)
                    Text("Take your first test to unlock live battles with friends.")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Ink.textSecondary)
                    NavigationLink { TopicsView() } label: {
                        Text("Start now")
                            .font(AppTheme.Font.captionBold)
                            .foregroundStyle(AppTheme.Ink.teal)
                    }
                }
            }
        }
    }

    // MARK: - Drawer

    private var drawer: some View {
        NavigationStack {
            List {
                Section {
                    NavigationLink("Leaderboard") { LeaderboardView() }
                    NavigationLink("Thesis Studio") { ThesisHomeView() }
                    NavigationLink("Rank Predictor") { PredictorView() }
                    NavigationLink("Referral") { ReferralView() }
                    NavigationLink("Poster Studio") { PosterStudioView() }
                }
                Section {
                    NavigationLink("Profile") { ProfileView() }
                    NavigationLink("Settings") { SettingsView() }
                    NavigationLink("Help & support") { HelpView() }
                }
            }
            .navigationTitle("Menu")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { isShowingMenu = false }
                }
            }
        }
    }

    // MARK: - Derived values

    private var displayName: String {
        let name = session.currentUser?.name ?? ""
        return name.isEmpty ? "Aspirant" : name.split(separator: " ").first.map(String.init) ?? name
    }

    /// Android shows "0 / 1000 XP" — points roll over every 1000.
    private var xpGoal: Int { 1000 }
    private var xpEarned: Int { stats.points % xpGoal }

    /// `accuracy` may arrive as a fraction (0–1) or a percentage (0–100).
    private var percentileAccuracy: Double {
        guard stats.accuracy > 0 else { return 0 }
        return stats.accuracy > 1 ? stats.accuracy : stats.accuracy * 100
    }

    /// Badge emoji by rank tier, replacing `ivBadgeBg` / `txtBadgeEmoji`.
    private var rankBadge: String {
        switch stats.rank {
        case 0: return "🪄"
        case 1 ... 3: return "👑"
        case 4 ... 10: return "🥇"
        case 11 ... 50: return "🥈"
        case 51 ... 200: return "🥉"
        default: return "🎖️"
        }
    }

    // MARK: - Loading

    private func reload() async {
        await viewModel.load(api: api, userId: session.userId)
    }
}

// MARK: - Dashboard sub-views

/// A tinted battle-mode card: uppercase tag, 34sp emoji, 20sp title, 12sp subtitle.
struct BattleModeCard: View {
    let tag: String
    let emoji: String
    let title: String
    let subtitle: String
    let fill: Color

    var body: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
            Text(tag)
                .font(AppTheme.Font.captionBold)
                .foregroundStyle(AppTheme.Ink.textTertiary)

            Text(emoji)
                .font(AppTheme.Font.display)

            Text(title)
                .font(AppTheme.Font.headline)
                .foregroundStyle(AppTheme.Ink.textPrimary)
                .lineLimit(2)

            Text(subtitle)
                .font(AppTheme.Font.caption)
                .foregroundStyle(AppTheme.Ink.textSecondary)
                .lineLimit(2)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .frame(height: 150)
        .padding(AppTheme.Spacing.lg)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous).fill(fill)
        )
    }
}

/// A `#132238` quick tile with a 30sp emoji.
struct QuickTile: View {
    let emoji: String
    let title: String

    var body: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            Text(emoji).font(.system(size: 30))
            Text(title)
                .font(AppTheme.Font.cardTitle)
                .foregroundStyle(AppTheme.Ink.textPrimary)
                .lineLimit(1)
            Spacer(minLength: 0)
        }
        .padding(AppTheme.Spacing.lg)
        .frame(height: 66)
        .frame(maxWidth: .infinity)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AppTheme.Ink.tile)
        )
    }
}

#Preview {
    DashboardView()
        .environmentObject(SessionStore())
        .environment(\.api, .live)
}
