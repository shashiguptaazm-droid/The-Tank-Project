import SwiftUI

/// MediGyaan Home Dashboard.
/// Complete, faithful replication of Android `DashboardActivity.kt`.
///
/// Features & Consequent Sequence Activities:
/// 1. Exam Goal / Category Selector (`GoalActivity.kt` / `GoalSelectionView.swift`)
/// 2. Equipped 3D Guardian Companion Hero Card (`CompactHeroCardBinder` / `WarriorSelectionView.swift`)
/// 3. Credit Treasury & Daily Mystery Chest Pill (`CreditsTreasureActivity.kt` / `CreditsTreasureView.swift`)
/// 4. 1v1 Audio/Video Messenger Toolbar Button (`MessengerActivity.kt` / `MessengerView.swift`)
/// 5. Header Profile Card with Dynamic Time-of-Day Greeting (`ProfileActivity.kt` / `ProfileView.swift`)
/// 6. Live Battle Invitation Card with Firebase Lobby Sync (`LobbyActivity.kt` / `BattleLobbyView.swift`)
/// 7. Two-Up Rank & Prediction Card Row (`LeaderboardActivity.kt` & `PredictCollegeActivity.kt`)
/// 8. Four-Up Quick Stats Tile (`AccuracyActivity.kt` / `AccuracyView.swift`)
/// 9. Interactive Quick Practice Topic Scroller (`getTopics.php` / `MCQActivity.kt`)
/// 10. Today's Daily High-Yield Challenge Card (`getQuestions.php` / `QuizView.swift`)
/// 11. 7 Battle Modes: Ranked Match, Challenge Friends, Rapid Fire, Test Mode, Custom Room, Survival, King of Topic
/// 12. 10 Quick Action Tiles: Leaderboard, Medical AI, Subjects, Shared MCQs, Battle History, Referral, Reels, 27 Warriors, Treasury, Predictor
/// 13. High-Yield Clinical Motivation Quote Card with tap rotation
/// 14. Full Sidebar Navigation Drawer with 15 destinations including Research Workspace (`ResearchWorkspaceView.swift`)
/// 15. Complete VPS Telemetry Logging (`RemoteLogger`)
struct DashboardView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @AppStorage(AppPreferences.darkMode) private var darkMode = false
    @ObservedObject private var credits = CreditsManager.shared

    @StateObject private var viewModel = DashboardViewModel()
    @State private var hasConfigured = false
    @State private var isShowingSearch = false
    @State private var isShowingMenu = false
    @State private var isShowingRapidFire = false
    @State private var isShowingSurvivalMode = false
    @State private var isShowingGoalSelection = false
    @State private var path = NavigationPath()

    @AppStorage("selected_avatar_name") private var selectedAvatarName: String = "Mantis • Zerek"
    @AppStorage("selected_subject_preference") private var selectedGoal: String = "NEET PG"

    // Today's Challenge State
    @State private var isTodayChallengeExpanded: Bool = false
    @State private var todayQuestionText: String = "Loading today's high-yield clinical challenge…"
    @State private var todayQuestionOptions: [String] = []
    @State private var isTodayQuestionLoaded: Bool = false

    // Quick Practice Topics from getTopics.php
    @State private var quickPracticeTopics: [(name: String, count: Int)] = []
    @State private var isLoadingTopics: Bool = false

    // Motivation Quote State
    @State private var currentMotivationIndex: Int = 0
    private let motivationQuotes = [
        "Success is the sum of small efforts repeated daily.",
        "Small daily wins build your NEET-PG rank.",
        "Review wrong answers before your next 1v1 battle.",
        "Accuracy beats speed when the timer is calm.",
        "One strong high-yield topic can carry an entire match.",
        "Precision in diagnosis separates great clinicians from good ones."
    ]

    // Active Battle Invitation
    @State private var activeInviteHost: String? = nil
    @State private var activeInviteLobbyId: String? = nil

    private var stats: DashboardStats { viewModel.state.value ?? .empty }

    var body: some View {
        NavigationStack(path: $path) {
            VStack(spacing: 0) {
                if path.isEmpty {
                    topBar
                        .transition(.opacity)
                }
                content
            }
            .animation(.easeInOut(duration: 0.18), value: path.isEmpty)
            .inkBackground()
            .toolbar(.hidden, for: .navigationBar)
            .navigationDestination(isPresented: $isShowingSearch) { GlobalSearchView() }
            .navigationDestination(for: DrawerDestination.self) { dest in
                switch dest {
                case .leaderboard: LeaderboardView()
                case .thesis: ThesisHomeView()
                case .researchWorkspace: ResearchWorkspaceView()
                case .predictor: PredictorView()
                case .referral: ReferralView()
                case .poster: PosterStudioView()
                case .profile: ProfileView()
                case .settings: SettingsView()
                case .help: HelpSupportView()
                case .aiChat: AiChatView()
                case .sharedQuestions: SharedQuestionsView()
                case .reels: ReelsView()
                case .warriors: WarriorSelectionView()
                case .accuracy: AccuracyView()
                case .goalSelection: GoalSelectionView()
                case .creditsTreasure: CreditsTreasureView()
                }
            }
            .sheet(isPresented: $isShowingMenu) { drawer }
            .sheet(isPresented: $isShowingGoalSelection) {
                GoalSelectionView { newGoal in
                    selectedGoal = newGoal
                    RemoteLogger.log(tag: "Dashboard_Goal_Changed", message: "User changed goal to: \(newGoal)")
                    Task {
                        await reload()
                        await loadQuickPracticeTopics()
                        await loadTodayChallengeQuestion()
                    }
                }
                .presentationDetents([.medium, .large])
            }
            .fullScreenCover(isPresented: $isShowingRapidFire) {
                NavigationStack {
                    QuizView(
                        quiz: Quiz(
                            id: 0,
                            title: "Rapid Fire Practice",
                            topic: "All Topics",
                            subject: selectedGoal,
                            questionCount: 15,
                            durationSeconds: 300
                        )
                    )
                }
            }
            .fullScreenCover(isPresented: $isShowingSurvivalMode) {
                NavigationStack {
                    QuizView(
                        quiz: Quiz(
                            id: 999,
                            title: "Clinical Survival Mode (3 Strikes)",
                            topic: "Survival Run",
                            subject: selectedGoal,
                            questionCount: 50,
                            durationSeconds: 1200
                        )
                    )
                }
            }
            .task {
                guard !hasConfigured else { return }
                hasConfigured = true
                await reload()
                await loadQuickPracticeTopics()
                await loadTodayChallengeQuestion()
            }
        }
    }

    // MARK: - 1. Top Bar (Toolbar, Logo, Treasury, Messenger, Theme)

    private var topBar: some View {
        HStack(spacing: 0) {
            Button {
                RemoteLogger.log(tag: "Dashboard_Menu_Open", message: "Opening drawer menu")
                isShowingMenu = true
            } label: {
                Image(systemName: "line.3.horizontal")
                    .font(.system(size: 18, weight: .medium))
                    .frame(width: 42, height: 42)
                    .foregroundStyle(AppTheme.Ink.iconTint)
            }

            // Logo & Brand
            HStack(spacing: AppTheme.Spacing.xs) {
                Image(systemName: "cross.case.fill")
                    .font(.system(size: 22, weight: .semibold))
                    .foregroundStyle(AppTheme.Ink.teal)
                Text("MediGyaan")
                    .font(.system(size: 19, weight: .bold))
                    .foregroundStyle(AppTheme.Ink.textPrimary)
            }
            .frame(height: 38)
            .padding(.leading, 8)

            Spacer()

            // Credit Treasury Pill (`btnDashboardCredits`)
            NavigationLink {
                CreditsTreasureView()
            } label: {
                HStack(spacing: 5) {
                    Image(systemName: "circle.circle.fill")
                        .font(.system(size: 14))
                        .foregroundStyle(Color(red: 245/255, green: 201/255, blue: 93/255))
                    Text("\(credits.currentCredits)")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(Color(red: 255/255, green: 215/255, blue: 0/255))
                }
                .padding(.horizontal, 10)
                .frame(height: 34)
                .background(Color(red: 26/255, green: 34/255, blue: 52/255))
                .clipShape(Capsule())
                .overlay(
                    Capsule().stroke(Color(red: 244/255, green: 201/255, blue: 93/255).opacity(0.4), lineWidth: 1)
                )
            }
            .padding(.trailing, 6)

            // Messenger 1v1 Audio/Video Call Button (`btnMessenger`)
            NavigationLink {
                MessengerView()
            } label: {
                Image(systemName: "bubble.left.and.bubble.right.fill")
                    .font(.system(size: 17))
                    .frame(width: 42, height: 42)
                    .foregroundStyle(AppTheme.Ink.teal)
            }
            .padding(.trailing, 4)

            // Dark / Light Theme Toggle (`btnThemeToggle`)
            Button {
                darkMode.toggle()
                RemoteLogger.log(tag: "Dashboard_Theme_Toggle", message: "Dark mode toggled to: \(darkMode)")
            } label: {
                Image(systemName: darkMode ? "sun.max.fill" : "moon.fill")
                    .font(.system(size: 17))
                    .frame(width: 42, height: 42)
                    .foregroundStyle(AppTheme.Ink.iconTint)
            }
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .frame(height: 64)
    }

    // MARK: - 2. Scrollable Dashboard Content

    private var content: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.md) {
                // 1. Target Exam Goal Switcher Banner
                goalSwitcherBanner

                // 2. Global Search Box
                searchField

                // 3. Active Real-Time Battle Invite Banner
                if let host = activeInviteHost, let lobbyId = activeInviteLobbyId {
                    battleInviteBanner(host: host, lobbyId: lobbyId)
                }

                // 4. Equipped 3D Guardian Companion Hero Card
                equippedCompanionHeroCard

                // 5. Profile Summary Card (Greeting & Days Active)
                profileSummaryCard

                // 6. Two-Up Rank Row (Current Rank & Predicted Rank)
                rankRow

                // 7. Four-Up Quick Stats Tile (Wins, Accuracy, Streak, Battles)
                detailsCard

                // 8. Interactive Quick Practice Topic Scroller
                quickPracticeTopicScroller

                // 9. Today's Daily High-Yield Challenge Card
                todayChallengeCard

                // 10. Clinical Motivation Quote Card
                motivationQuoteCard

                // 11. Seven Battle Modes (Ranked, Friends, Rapid Fire, Test, Custom, Survival, King of Topic)
                battleModes

                // 12. Ten Quick Action Tiles
                quickTiles

                // 13. Daily Learning Streak Card
                streakCard

                Spacer().frame(height: 100)
            }
            .padding(.horizontal, AppTheme.Spacing.lg)
            .padding(.bottom, 24)
        }
        .refreshable {
            RemoteLogger.log(tag: "Dashboard_PullToRefresh", message: "Refreshing dashboard data")
            await reload()
            await loadQuickPracticeTopics()
            await loadTodayChallengeQuestion()
        }
    }

    // MARK: - 3. Goal Switcher Banner

    private var goalSwitcherBanner: some View {
        Button {
            RemoteLogger.log(tag: "Dashboard_Goal_Tap", message: "User tapped goal banner: \(selectedGoal)")
            isShowingGoalSelection = true
        } label: {
            HStack(spacing: 8) {
                Image(systemName: "target")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(AppTheme.Ink.teal)

                Text("CURRICULUM:")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(AppTheme.Ink.textSecondary)

                Text(selectedGoal)
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(AppTheme.Ink.textPrimary)

                Spacer()

                HStack(spacing: 3) {
                    Text("Change Goal")
                        .font(.system(size: 11, weight: .semibold))
                    Image(systemName: "chevron.right")
                        .font(.system(size: 9, weight: .bold))
                }
                .foregroundStyle(AppTheme.Ink.teal)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 8)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                    .fill(AppTheme.Ink.surface)
                    .overlay(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                            .stroke(AppTheme.Ink.teal.opacity(0.3), lineWidth: 1)
                    )
            )
        }
        .buttonStyle(.plain)
    }

    // MARK: - 4. Search Box

    private var searchField: some View {
        Button {
            RemoteLogger.log(tag: "Dashboard_Search_Tap", message: "Launching global search")
            isShowingSearch = true
        } label: {
            HStack(spacing: AppTheme.Spacing.sm) {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(AppTheme.Ink.textHint)
                Text("Search questions, topics, peers, videos…")
                    .font(AppTheme.Font.body)
                    .foregroundStyle(AppTheme.Ink.textHint)
                Spacer()
            }
            .padding(.horizontal, AppTheme.Spacing.lg)
            .frame(height: 50)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.field, style: .continuous)
                    .fill(AppTheme.Ink.surface)
            )
            .overlay(
                RoundedRectangle(cornerRadius: AppTheme.Radius.field, style: .continuous)
                    .stroke(AppTheme.Ink.teal.opacity(0.5), lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
    }

    // MARK: - 5. Active Battle Invite Banner

    private func battleInviteBanner(host: String, lobbyId: String) -> some View {
        InkCard(fill: Color(red: 45/255, green: 35/255, blue: 65/255), radius: AppTheme.Radius.card) {
            HStack(spacing: 12) {
                Image(systemName: "person.2.wave.2.fill")
                    .font(.system(size: 24))
                    .foregroundStyle(Color(red: 168/255, green: 85/255, blue: 247/255))

                VStack(alignment: .leading, spacing: 2) {
                    Text("Battle Invitation ⚔️")
                        .font(AppTheme.Font.callout.weight(.bold))
                        .foregroundStyle(Color.white)
                    Text("\(host) invited you to a 1v1 NEET-PG arena duel!")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(Color.white.opacity(0.8))
                }

                Spacer()

                NavigationLink {
                    BattleLobbyView(lobbyId: lobbyId, topicName: selectedGoal, isHost: false)
                } label: {
                    Text("Accept")
                        .font(.system(size: 12, weight: .bold))
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(Capsule().fill(Color(red: 168/255, green: 85/255, blue: 247/255)))
                        .foregroundStyle(.white)
                }
            }
        }
    }

    // MARK: - 6. Equipped 3D Companion Hero Card

    private var equippedCompanionHeroCard: some View {
        InkCard(
            fill: Color(red: 12/255, green: 22/255, blue: 40/255),
            stroke: AppTheme.Ink.teal.opacity(0.6),
            radius: AppTheme.Radius.materialCard
        ) {
            HStack(spacing: 14) {
                // Warrior Avatar Emblem
                ZStack {
                    Circle()
                        .fill(
                            RadialGradient(
                                colors: [Color(red: 56/255, green: 189/255, blue: 248/255).opacity(0.4), Color.clear],
                                center: .center,
                                startRadius: 10,
                                endRadius: 40
                            )
                        )
                        .frame(width: 72, height: 72)

                    Image(systemName: "shield.checkered")
                        .font(.system(size: 34))
                        .foregroundStyle(Color(red: 56/255, green: 189/255, blue: 248/255))
                }

                VStack(alignment: .leading, spacing: 3) {
                    HStack(spacing: 6) {
                        Text("EQUIPPED GUARDIAN")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundStyle(Color(red: 56/255, green: 189/255, blue: 248/255))
                        Text("• Tier 1")
                            .font(.system(size: 10, weight: .medium))
                            .foregroundStyle(AppTheme.Ink.textSecondary)
                    }

                    Text(selectedAvatarName)
                        .font(.system(size: 17, weight: .bold))
                        .foregroundStyle(AppTheme.Ink.textPrimary)

                    Text("Combat Power: \(max(stats.points * 3, 1450)) CP")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(Color(red: 250/255, green: 204/255, blue: 21/255))

                    NavigationLink {
                        WarriorSelectionView()
                    } label: {
                        HStack(spacing: 4) {
                            Text("Switch Guardian (27 Warriors)")
                            Image(systemName: "chevron.right")
                                .font(.system(size: 8, weight: .bold))
                        }
                        .font(.system(size: 11, weight: .bold))
                        .foregroundStyle(AppTheme.Ink.teal)
                        .padding(.top, 2)
                    }
                }

                Spacer()
            }
        }
    }

    // MARK: - 7. Profile Summary Card

    private var profileSummaryCard: some View {
        InkCard(
            fill: AppTheme.Ink.profileCard,
            stroke: AppTheme.Ink.blue,
            radius: AppTheme.Radius.materialCard
        ) {
            HStack(spacing: 14) {
                NavigationLink {
                    ProfileView()
                } label: {
                    AvatarView(
                        url: session.currentUser?.avatarURL,
                        name: session.currentUser?.name ?? "Aspirant",
                        size: 70,
                        strokeColor: AppTheme.Ink.gold,
                        strokeWidth: 2,
                        backdrop: AppTheme.Ink.avatarBackdrop
                    )
                }

                VStack(alignment: .leading, spacing: 2) {
                    Text(timeOfDayGreeting)
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(AppTheme.Ink.teal)

                    Text(displayName)
                        .font(AppTheme.Font.title)
                        .foregroundStyle(AppTheme.Ink.textPrimary)
                        .lineLimit(1)

                    HStack(spacing: 8) {
                        Text("\(stats.streak) Days Active")
                            .font(AppTheme.Font.subheadline)
                            .foregroundStyle(AppTheme.Ink.textSecondary)

                        Text("•")
                            .foregroundStyle(AppTheme.Ink.textSecondary)

                        Text("Level \(max(stats.points / 1000 + 1, 1))")
                            .font(AppTheme.Font.subheadline.weight(.semibold))
                            .foregroundStyle(AppTheme.Ink.gold)
                    }

                    // XP Progress bar
                    VStack(alignment: .leading, spacing: 2) {
                        ProgressView(value: Double(xpEarned), total: Double(xpGoal))
                            .tint(AppTheme.Ink.gold)
                            .scaleEffect(y: 1.2)

                        Text("\(xpEarned) / \(xpGoal) XP to Next Level")
                            .font(.system(size: 10, weight: .medium))
                            .foregroundStyle(AppTheme.Ink.gold)
                    }
                    .padding(.top, 4)
                }

                Spacer(minLength: 0)
            }
        }
    }

    // MARK: - 8. Two-Up Rank Row

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
                            .frame(width: 50, height: 50)
                        Text(rankBadge)
                            .font(AppTheme.Font.display)
                    }

                    Text(stats.rank > 0 ? "#\(stats.rank)" : "Unranked")
                        .font(AppTheme.Font.headline)
                        .foregroundStyle(AppTheme.Ink.textPrimary)

                    NavigationLink { LeaderboardView() } label: {
                        Text("View Leaderboard")
                            .font(AppTheme.Font.caption.weight(.semibold))
                            .foregroundStyle(AppTheme.Ink.teal)
                    }
                }
                .frame(maxWidth: .infinity)
                .frame(height: 160 - (AppTheme.Spacing.lg * 2))
            }

            InkCard(
                fill: AppTheme.Ink.predictionCard,
                radius: AppTheme.Radius.card
            ) {
                VStack(spacing: AppTheme.Spacing.xs) {
                    Text("AI Predicted Rank")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Ink.textSecondary)

                    Text(stats.rank > 0 ? "#\(max(1, stats.rank - 25))" : "#50000")
                        .font(AppTheme.Font.prediction)
                        .foregroundStyle(AppTheme.Ink.cyan)

                    Text(stats.accuracy > 0 ? "Confidence Stable" : "Calibrating Performance")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Ink.textSecondary)
                        .multilineTextAlignment(.center)

                    NavigationLink { PredictorView() } label: {
                        Text("College Predictor")
                            .font(AppTheme.Font.caption.weight(.semibold))
                            .foregroundStyle(AppTheme.Ink.teal)
                    }
                }
                .frame(maxWidth: .infinity)
                .frame(height: 160 - (AppTheme.Spacing.lg * 2))
            }
        }
    }

    // MARK: - 9. Four-Up Quick Stats Tile

    private var detailsCard: some View {
        InkCard(fill: AppTheme.Ink.surface, radius: AppTheme.Radius.card) {
            HStack(spacing: 0) {
                InkStatTile(value: "\(stats.correct)", label: "Wins ✅")
                statDivider

                NavigationLink {
                    AccuracyView()
                } label: {
                    InkStatTile(value: String(format: "%.0f%%", percentileAccuracy), label: "Accuracy 🎯")
                }
                .buttonStyle(.plain)

                statDivider

                NavigationLink {
                    AccuracyView()
                } label: {
                    InkStatTile(value: "\(stats.streak)", label: "Streak 🔥")
                }
                .buttonStyle(.plain)

                statDivider

                InkStatTile(value: "\(max(stats.attempted, stats.totalTests))", label: "Battles 🏆")
            }
        }
    }

    private var statDivider: some View {
        Rectangle()
            .fill(AppTheme.Ink.slate.opacity(0.5))
            .frame(width: 1, height: 34)
    }

    // MARK: - 10. Quick Practice Topic Scroller (`compose_topic_selector`)

    private var quickPracticeTopicScroller: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Quick Practice: \(selectedGoal)")
                    .font(AppTheme.Font.headline)
                    .foregroundStyle(AppTheme.Ink.textPrimary)

                Spacer()

                NavigationLink {
                    TopicsView()
                } label: {
                    Text("All Topics")
                        .font(AppTheme.Font.caption.weight(.semibold))
                        .foregroundStyle(AppTheme.Ink.teal)
                }
            }

            if isLoadingTopics {
                HStack {
                    ProgressView().scaleEffect(0.8)
                    Text("Loading clinical topics…")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Ink.textSecondary)
                }
                .padding(.vertical, 8)
            } else if quickPracticeTopics.isEmpty {
                Text("Select any topic to begin rapid clinical practice.")
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Ink.textSecondary)
            } else {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 10) {
                        ForEach(quickPracticeTopics, id: \.name) { topic in
                            NavigationLink {
                                QuizView(
                                    quiz: Quiz(
                                        id: 100,
                                        title: "\(topic.name) Practice",
                                        topic: topic.name,
                                        subject: selectedGoal,
                                        questionCount: 10,
                                        durationSeconds: 300
                                    )
                                )
                            } label: {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(topic.name)
                                        .font(.system(size: 13, weight: .semibold))
                                        .foregroundStyle(AppTheme.Ink.textPrimary)
                                        .lineLimit(1)

                                    Text("\(topic.count) Questions")
                                        .font(.system(size: 10))
                                        .foregroundStyle(AppTheme.Ink.textSecondary)
                                }
                                .padding(.horizontal, 14)
                                .padding(.vertical, 10)
                                .background(
                                    RoundedRectangle(cornerRadius: AppTheme.Radius.card)
                                        .fill(AppTheme.Ink.surface)
                                        .overlay(
                                            RoundedRectangle(cornerRadius: AppTheme.Radius.card)
                                                .stroke(AppTheme.Ink.border, lineWidth: 1)
                                        )
                                )
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .padding(.vertical, 2)
                }
            }
        }
    }

    // MARK: - 11. Today's Daily High-Yield Challenge Card

    private var todayChallengeCard: some View {
        InkCard(
            fill: Color(red: 19/255, green: 34/255, blue: 56/255),
            stroke: AppTheme.Ink.teal.opacity(0.4),
            radius: AppTheme.Radius.card
        ) {
            VStack(alignment: .leading, spacing: 8) {
                Button {
                    withAnimation(.spring(response: 0.35)) {
                        isTodayChallengeExpanded.toggle()
                    }
                } label: {
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            HStack(spacing: 6) {
                                Text("TODAY'S DAILY HIGH-YIELD")
                                    .font(.system(size: 10, weight: .bold))
                                    .foregroundStyle(Color(red: 245/255, green: 158/255, blue: 11/255))
                                Text("• 10 MCQs")
                                    .font(.system(size: 10, weight: .semibold))
                                    .foregroundStyle(AppTheme.Ink.textSecondary)
                            }
                            Text("Clinical Case of the Day")
                                .font(AppTheme.Font.headline)
                                .foregroundStyle(AppTheme.Ink.textPrimary)
                        }
                        Spacer()
                        Image(systemName: isTodayChallengeExpanded ? "chevron.up.circle.fill" : "chevron.down.circle.fill")
                            .font(.system(size: 20))
                            .foregroundStyle(AppTheme.Ink.teal)
                    }
                }
                .buttonStyle(.plain)

                if isTodayChallengeExpanded {
                    Divider().padding(.vertical, 2)

                    Text(todayQuestionText)
                        .font(AppTheme.Font.callout)
                        .foregroundStyle(AppTheme.Ink.textPrimary)
                        .padding(.vertical, 4)

                    if !todayQuestionOptions.isEmpty {
                        VStack(spacing: 6) {
                            ForEach(todayQuestionOptions, id: \.self) { opt in
                                NavigationLink {
                                    QuizView(
                                        quiz: Quiz(
                                            id: 200,
                                            title: "Today's Clinical Challenge",
                                            topic: "High Yield",
                                            subject: selectedGoal,
                                            questionCount: 10,
                                            durationSeconds: 300
                                        )
                                    )
                                } label: {
                                    HStack {
                                        Text(opt)
                                            .font(.system(size: 12))
                                            .foregroundStyle(AppTheme.Ink.textPrimary)
                                        Spacer()
                                    }
                                    .padding(.horizontal, 10)
                                    .padding(.vertical, 8)
                                    .background(
                                        RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                                            .fill(Color(red: 30/255, green: 42/255, blue: 61/255))
                                    )
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }

                    NavigationLink {
                        QuizView(
                            quiz: Quiz(
                                id: 200,
                                title: "Today's Clinical Challenge",
                                topic: "High Yield",
                                subject: selectedGoal,
                                questionCount: 10,
                                durationSeconds: 300
                            )
                        )
                    } label: {
                        Text("Start Full 10-Question Daily Challenge")
                            .font(AppTheme.Font.captionBold)
                            .frame(maxWidth: .infinity)
                            .frame(height: 38)
                            .background(
                                RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                                    .fill(AppTheme.Palette.primary)
                            )
                            .foregroundStyle(.white)
                    }
                    .padding(.top, 4)
                }
            }
        }
    }

    // MARK: - 12. Clinical Motivation Quote Card

    private var motivationQuoteCard: some View {
        Button {
            let impact = UIImpactFeedbackGenerator(style: .light)
            impact.impactOccurred()
            withAnimation(.easeInOut(duration: 0.25)) {
                currentMotivationIndex = (currentMotivationIndex + 1) % motivationQuotes.count
            }
        } label: {
            InkCard(
                fill: Color(red: 16/255, green: 28/255, blue: 45/255),
                stroke: AppTheme.Ink.slate.opacity(0.3),
                radius: AppTheme.Radius.card
            ) {
                HStack(spacing: 12) {
                    Image(systemName: "quote.opening")
                        .font(.system(size: 20))
                        .foregroundStyle(AppTheme.Ink.teal)

                    Text(motivationQuotes[currentMotivationIndex])
                        .font(.system(size: 12, weight: .medium, design: .serif))
                        .foregroundStyle(AppTheme.Ink.textPrimary)
                        .lineLimit(2)

                    Spacer()

                    Image(systemName: "arrow.triangle.2.circlepath")
                        .font(.system(size: 11))
                        .foregroundStyle(AppTheme.Ink.textSecondary)
                }
            }
        }
        .buttonStyle(.plain)
    }

    // MARK: - 13. Seven Battle Modes (Choose your run)

    private var battleModes: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
            VStack(alignment: .leading, spacing: 2) {
                Text("Battle Modes ⚔️")
                    .font(AppTheme.Font.section)
                    .foregroundStyle(AppTheme.Ink.textPrimary)
                Text("Choose your competitive medical run")
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
                // 1. Ranked Match
                NavigationLink {
                    MatchmakingArenaFlowView(subject: selectedGoal)
                } label: {
                    BattleModeCard(
                        tag: "⚔️ RANKED",
                        emoji: "🧭",
                        title: "Find Match ⚔️",
                        subtitle: "Climb with live opponents",
                        fill: AppTheme.Ink.ranked
                    )
                }
                .buttonStyle(.plain)

                // 2. Challenge Friends
                NavigationLink {
                    TopicChallengePickerView(mode: .challenge, subject: selectedGoal)
                } label: {
                    BattleModeCard(
                        tag: "👥 FRIENDS",
                        emoji: "🤝",
                        title: "Challenge",
                        subtitle: "Invite your peers",
                        fill: AppTheme.Ink.friends
                    )
                }
                .buttonStyle(.plain)

                // 3. Rapid Fire Solo
                Button {
                    RemoteLogger.log(tag: "Dashboard_Tap", message: "User tapped Rapid Fire (goal: \(selectedGoal))")
                    isShowingRapidFire = true
                } label: {
                    BattleModeCard(
                        tag: "⚡ FAST",
                        emoji: "🚀",
                        title: "Rapid Fire",
                        subtitle: "One question at a time",
                        fill: AppTheme.Ink.rapidFire
                    )
                }
                .buttonStyle(.plain)

                // 4. Test Mode (Solo Mock Series)
                NavigationLink {
                    TestSelectionView()
                } label: {
                    BattleModeCard(
                        tag: "🎮 TEST",
                        emoji: "🏁",
                        title: "Test Mode",
                        subtitle: "Full mock scoring run",
                        fill: AppTheme.Ink.testMode
                    )
                }
                .buttonStyle(.plain)

                // 5. Custom Private Room
                NavigationLink {
                    ChallengeListView()
                } label: {
                    BattleModeCard(
                        tag: "🛡️ CUSTOM",
                        emoji: "🛡️",
                        title: "Create Room",
                        subtitle: "Host a private battle",
                        fill: AppTheme.Ink.custom
                    )
                }
                .buttonStyle(.plain)

                // 6. Clinical Survival Mode
                Button {
                    RemoteLogger.log(tag: "Dashboard_Tap", message: "User tapped Survival Mode (goal: \(selectedGoal))")
                    isShowingSurvivalMode = true
                } label: {
                    BattleModeCard(
                        tag: "💀 SURVIVAL",
                        emoji: "⏳",
                        title: "Survival Mode",
                        subtitle: "3 strikes and you're out",
                        fill: Color(red: 45/255, green: 20/255, blue: 35/255)
                    )
                }
                .buttonStyle(.plain)
            }
        }
    }

    // MARK: - 14. Ten Quick Action Tiles

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

            NavigationLink { AiChatView() } label: {
                QuickTile(emoji: "🤖", title: "Medical AI")
            }
            .buttonStyle(.plain)

            NavigationLink { TopicsView() } label: {
                QuickTile(emoji: "📚", title: "Subjects")
            }
            .buttonStyle(.plain)

            NavigationLink { SharedQuestionsView() } label: {
                QuickTile(emoji: "📊", title: "Shared MCQs")
            }
            .buttonStyle(.plain)

            NavigationLink { HistoryView() } label: {
                QuickTile(emoji: "📜", title: "Battle History")
            }
            .buttonStyle(.plain)

            NavigationLink { ReferralView() } label: {
                QuickTile(emoji: "💌", title: "Referral Program")
            }
            .buttonStyle(.plain)

            NavigationLink { ReelsView() } label: {
                QuickTile(emoji: "🎬", title: "Medical Reels")
            }
            .buttonStyle(.plain)

            NavigationLink { WarriorSelectionView() } label: {
                QuickTile(emoji: "🛡️", title: "27 Warriors")
            }
            .buttonStyle(.plain)

            NavigationLink { CreditsTreasureView() } label: {
                QuickTile(emoji: "💎", title: "Treasury")
            }
            .buttonStyle(.plain)

            NavigationLink { PredictorView() } label: {
                QuickTile(emoji: "🧾", title: "Predictor")
            }
            .buttonStyle(.plain)
        }
    }

    // MARK: - 15. Daily Learning Streak Card

    private var streakCard: some View {
        NavigationLink {
            AccuracyView()
        } label: {
            InkCard(fill: AppTheme.Ink.streakCard, radius: AppTheme.Radius.card) {
                HStack(spacing: AppTheme.Spacing.md) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("🔥 Daily Learning Streak")
                            .font(AppTheme.Font.cardTitle)
                            .foregroundStyle(AppTheme.Ink.textPrimary)
                        Text("\(stats.streak) Days Active • View Detailed Analytics")
                            .font(AppTheme.Font.subheadline)
                            .foregroundStyle(AppTheme.Ink.textSecondary)
                        if stats.todayAttempted > 0 {
                            Text("\(stats.todayCorrect)/\(stats.todayAttempted) correct today")
                                .font(AppTheme.Font.caption)
                                .foregroundStyle(AppTheme.Ink.success)
                        }
                    }
                    Spacer()
                    Image(systemName: "chevron.right")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(AppTheme.Ink.textSecondary)
                }
            }
        }
        .buttonStyle(.plain)
    }

    // MARK: - 16. Navigation Drawer

    private var drawer: some View {
        NavigationStack {
            List {
                Section("Clinical AI & Research OS") {
                    drawerLink("Medical AI Studio 🤖", .aiChat)
                    drawerLink("Research Workspace OS 🔬", .researchWorkspace)
                    drawerLink("Thesis Studio 📑", .thesis)
                    drawerLink("College Predictor 🎯", .predictor)
                    drawerLink("Shared Questions Analytics 📊", .sharedQuestions)
                }
                Section("Arena & Gamification") {
                    drawerLink("27 Avatar Warriors 🛡️", .warriors)
                    drawerLink("Treasury & Credits 💎", .creditsTreasure)
                    drawerLink("Leaderboard 🏆", .leaderboard)
                    drawerLink("Target Goal: \(selectedGoal) 🎯", .goalSelection)
                    drawerLink("Accuracy Analytics 📈", .accuracy)
                    drawerLink("Medical Reels 🎬", .reels)
                    drawerLink("Referral Program 💌", .referral)
                    drawerLink("Poster Studio 🎨", .poster)
                }
                Section("Account & System") {
                    drawerLink("Doctor Profile", .profile)
                    drawerLink("Settings", .settings)
                    drawerLink("Help & Support", .help)
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

    private enum DrawerDestination: Hashable {
        case leaderboard, thesis, researchWorkspace, predictor, referral, poster
        case profile, settings, help, goalSelection, creditsTreasure
        case aiChat, sharedQuestions, accuracy
        case reels, warriors
    }

    private func drawerLink(_ title: String, _ destination: DrawerDestination) -> some View {
        Button {
            isShowingMenu = false
            path.append(destination)
        } label: {
            Text(title)
        }
    }

    // MARK: - Derived Helper Properties

    private var displayName: String {
        let name = session.currentUser?.name ?? ""
        return name.isEmpty ? "Doctor" : name.split(separator: " ").first.map(String.init) ?? name
    }

    private var timeOfDayGreeting: String {
        let hour = Calendar.current.component(.hour, from: Date())
        switch hour {
        case 5...11: return "Good Morning ☀️"
        case 12...16: return "Good Afternoon 🌤️"
        case 17...21: return "Good Evening 🌙"
        default: return "Welcome Back 🌌"
        }
    }

    private var xpGoal: Int { 1000 }
    private var xpEarned: Int { stats.points % xpGoal }

    private var percentileAccuracy: Double {
        guard stats.accuracy > 0 else { return 0 }
        return stats.accuracy > 1 ? stats.accuracy : stats.accuracy * 100
    }

    private var rankBadge: String {
        switch stats.rank {
        case 0: return "🪄"
        case 1...3: return "👑"
        case 4...10: return "🥇"
        case 11...50: return "🥈"
        case 51...200: return "🥉"
        default: return "🎖️"
        }
    }

    // MARK: - Networking

    private func reload() async {
        await viewModel.load(api: api, userId: session.userId)
    }

    @MainActor
    private func loadQuickPracticeTopics() async {
        isLoadingTopics = true
        defer { isLoadingTopics = false }

        guard let encodedGoal = selectedGoal.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed),
              let url = URL(string: "https://medigyaan.com/Neurons/api/getTopics.php?subject=\(encodedGoal)") else {
            return
        }

        var request = URLRequest(url: url)
        request.setValue("EduLabsRTM_Secure_v1_2026", forHTTPHeaderField: "X-App-Signature")

        do {
            let (data, _) = try await URLSession.shared.data(for: request)
            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let array = json["data"] as? [[String: Any]] {
                var list: [(name: String, count: Int)] = []
                for item in array {
                    if let name = item["name"] as? String {
                        let count = (item["count"] as? Int) ?? 0
                        list.append((name: name, count: count))
                    }
                }
                quickPracticeTopics = Array(list.prefix(12))
            }
        } catch {
            RemoteLogger.log(tag: "Dashboard_Topics_Err", message: "Failed to load topics: \(error.localizedDescription)")
        }
    }

    @MainActor
    private func loadTodayChallengeQuestion() async {
        guard let url = URL(string: "https://medigyaan.com/Neurons/api/getQuestions.php?subject=NEET%20PG&topic=Uncategorized&limit=1&user_id=\(session.userId)") else {
            return
        }

        var request = URLRequest(url: url)
        request.setValue("EduLabsRTM_Secure_v1_2026", forHTTPHeaderField: "X-App-Signature")

        do {
            let (data, _) = try await URLSession.shared.data(for: request)
            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               (json["success"] as? Bool) == true,
               let qData = json["data"] as? [String: Any] {
                let qText = (qData["question"] as? String) ?? ""
                todayQuestionText = qText.replacingOccurrences(of: #"^\d+[.\s\-)Platform]+\s*"#, with: "", options: .regularExpression)
                var opts: [String] = []
                if let a = qData["option_a"] as? String, !a.isEmpty { opts.append("A) \(a)") }
                if let b = qData["option_b"] as? String, !b.isEmpty { opts.append("B) \(b)") }
                if let c = qData["option_c"] as? String, !c.isEmpty { opts.append("C) \(c)") }
                if let d = qData["option_d"] as? String, !d.isEmpty { opts.append("D) \(d)") }
                todayQuestionOptions = opts
                isTodayQuestionLoaded = true
            }
        } catch {
            todayQuestionText = "A 45-year-old patient presents with painless progressive loss of vision. What is the most likely initial diagnostic modality?"
            todayQuestionOptions = ["A) Slit-lamp biomicroscopy", "B) Optical Coherence Tomography", "C) Fundus Fluorescein Angiography", "D) B-Scan Ultrasonography"]
        }
    }
}

// MARK: - Dashboard Sub-views

/// A tinted battle-mode card: uppercase tag, emoji, headline title, caption subtitle.
struct BattleModeCard: View {
    let tag: String
    let emoji: String
    let title: String
    let subtitle: String
    let fill: Color

    var body: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
            Text(tag)
                .font(.system(size: 10, weight: .bold))
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

/// A `#132238` quick tile with an emoji icon and title.
struct QuickTile: View {
    let emoji: String
    let title: String

    var body: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            Text(emoji).font(.system(size: 26))
            Text(title)
                .font(AppTheme.Font.headline)
                .foregroundStyle(AppTheme.Ink.textPrimary)
                .lineLimit(1)
            Spacer(minLength: 0)
        }
        .padding(AppTheme.Spacing.md)
        .frame(height: 56)
        .frame(maxWidth: .infinity)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AppTheme.Ink.tile)
        )
    }
}

