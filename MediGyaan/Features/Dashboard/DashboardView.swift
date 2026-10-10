import SwiftUI

/// MediGyaan Home Dashboard.
///
/// Ports `DashboardActivity.kt` end to end. Section numbering below follows the
/// order `onCreate` wires the screen up in.
///
/// Consequent screens, with their Android origins:
///
/// 1. Exam category switcher — `setupCategoryCards` / `handleCategorySelection` /
///    `showModeDialog` (`GoalActivity` → `GoalSelectionView`)
/// 2. Equipped guardian hero card — `CompactHeroCardBinder`
///    (`GuardianShowcaseActivity` → `GuardianShowcaseView`)
/// 3. Credit treasury pill — `btnDashboardCredits` (`CreditsTreasureActivity` →
///    `CreditsTreasureView`)
/// 4. 1v1 audio/video messenger button — `btnMessenger` (`MessengerActivity` →
///    `MessengerView`)
/// 5. Header profile card with dynamic greeting — `setupHeader`
///    (`ProfileActivity` → `ProfileView`)
/// 6. Live battle invitation banner — `checkActiveInvitations` /
///    `showInviteBanner` (`LobbyActivity` → `BattleLobbyView`)
/// 7. Rank progression sheet — `showRankInfoDialog` / `setupRankBadgeClick`
/// 8. AI predicted-rank card — `fetchPredictionFromServer` /
///    `loadPredictedRankFromServer`
/// 9. Four-up quick stats tile — `loadDashboardAccuracyStats`
///    (`AccuracyActivity` → `AccuracyView`)
/// 10. Quick practice topic scroller — `TopicSelectorList`
///     (`getTopics.php` → `MCQActivity`)
/// 11. Daily high-yield challenge card — `setupTodayChallenge` /
///     `loadTodayFirstQuestion` (`getQuestions.php` → `QuizView`)
/// 12. Clinical motivation quote — `setupMotivationCard`
/// 13. Battle modes — `setupBattleModeCards`: Ranked Match, Challenge Friends,
///     Rapid Fire, Test Mode, Custom Room, Survival, Subject Survival,
///     Custom Mode Battle, King of the Topic
/// 14. Quick action tiles — `setupQuickActionCards` / `setupDashboardNavigationCards`
/// 15. Daily learning streak card — `streakCard`
/// 16. Navigation drawer — `setupToolbarAndSidebar`'s `when (itemId)` table,
///     plus `confirmLogout` and `showDeleteAccountDialog`
/// 17. Mobile verification prompt — `checkAndPromptMobileVerification`
struct DashboardView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @AppStorage(AppPreferences.darkMode) private var darkMode = false
    @ObservedObject private var credits = CreditsManager.shared

    @StateObject private var viewModel = DashboardViewModel()
    @State private var hasConfigured = false
    @State private var isShowingSearch = false
    @State private var isShowingMenu = false
    @State private var isShowingRankProgression = false
    @State private var prompt: DashboardPrompt?
    @State private var isShowingRapidFire = false
    @State private var isShowingSurvivalMode = false
    @State private var isShowingGoalSelection = false
    @State private var path = NavigationPath()

    @AppStorage("selected_avatar_id") private var selectedAvatarId: Int = 1
    @AppStorage("selected_avatar_name") private var selectedAvatarName: String = "Mantis • Zerek"
    @AppStorage("selected_subject_preference") private var selectedGoal: String = "NEET PG"

    /// `cardTodayChallenge` expand/collapse.
    @State private var isTodayChallengeExpanded: Bool = false

    /// `txtMotivation`. Kotlin seeded the field with an accuracy-threshold line
    /// and only rotated to one of four quotes after the first tap, so `-1` is
    /// the "still showing the seeded line" state.
    @State private var currentMotivationIndex: Int = -1

    /// The four strings `setupMotivationCard` rotates through.
    private let motivationQuotes = [
        "Small daily wins build rank.",
        "Review wrong answers before the next battle.",
        "Accuracy beats speed when the timer is calm.",
        "One strong topic can carry a match.",
    ]

    /// `checkActiveInvitations`. iOS carries no Firebase Realtime Database
    /// binding, so a pushed invite is injected rather than observed.
    @State private var activeInviteHost: String? = nil
    @State private var activeInviteLobbyId: String? = nil

    private var stats: DashboardStats { viewModel.stats }

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
            .toolbar(.hidden, for: .navigationBar)
            .navigationDestination(isPresented: $isShowingSearch) { GlobalSearchView() }
            .navigationDestination(for: DrawerDestination.self) { destination in
                switch destination {
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
                case .ranked: MatchmakingArenaFlowView(subject: selectedGoal)
                case .challengeFriends: TopicChallengePickerView(mode: .challenge, subject: selectedGoal)
                case .myQuizzes: HistoryListView()
                case .editProfile: EditProfileView()
                case .widgetSettings: WidgetSettingsView()
                }
            }
            .sheet(isPresented: $isShowingMenu) { drawer }
            .sheet(isPresented: $isShowingRankProgression) {
                DashboardRankProgressionSheet(tier: viewModel.rankTier)
                    .presentationDetents([.medium])
            }
            .sheet(isPresented: verificationSheetBinding) {
                DashboardVerificationSheet()
                    .environmentObject(viewModel)
            }
            .sheet(isPresented: $isShowingGoalSelection) {
                GoalSelectionView { newGoal in
                    selectedGoal = newGoal
                    viewModel.persistCategory(newGoal)
                    RemoteLogger.log(tag: "Dashboard_Goal_Changed", message: "User changed goal to: \(newGoal)")
                    Task { await reload() }
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
            .confirmationDialog(
                promptTitle,
                isPresented: promptBinding,
                titleVisibility: .visible,
                actions: { promptActions },
                message: { Text(promptMessage) }
            )
            .errorAlert(message: $viewModel.errorMessage)
            .task {
                guard !hasConfigured else { return }
                hasConfigured = true
                await reload()
                await viewModel.checkMobileVerification(userId: session.userId)
            }
        }
        .baseScreen("DashboardActivity", style: .ink)
    }

    // MARK: - Lifecycle

    /// The `onCreate` + `onResume` half of the Kotlin lifecycle, condensed into
    /// the single hook SwiftUI gives us.
    private func reload() async {
        await viewModel.load(api: api, userId: session.userId, subject: selectedGoal)
    }

    private var verificationSheetBinding: Binding<Bool> {
        Binding(
            get: { viewModel.verification != .hidden },
            set: { isPresented in
                guard !isPresented else { return }
                // `showOtpConfirmationDialog` is `setCancelable(false)`; only the
                // phone prompt offers "SKIP FOR NOW".
                if case .otp = viewModel.verification { return }
                viewModel.dismissVerification()
            }
        )
    }

    // MARK: - Confirmations

    /// The three `AlertDialog`s the activity raises inline. One SwiftUI
    /// confirmation dialog drives all three so they cannot collide.
    private enum DashboardPrompt {
        /// `showModeDialog` — asked after a category switch.
        case modeChoice
        /// `confirmLogout`.
        case logout
        /// `showDeleteAccountDialog`.
        case deleteAccount
    }

    private var promptBinding: Binding<Bool> {
        Binding(
            get: { self.prompt != nil },
            set: { if !$0 { self.prompt = nil } }
        )
    }

    private var promptTitle: String {
        switch prompt {
        case .some(.modeChoice): return selectedGoal
        case .some(.logout): return "Logout"
        case .some(.deleteAccount): return "Delete Account"
        case .none: return ""
        }
    }

    private var promptHeading: String {
        switch prompt {
        case .some(.modeChoice): return "Choose your opening"
        case .some(.logout): return "Are you sure?"
        case .some(.deleteAccount): return "Are you sure you want to delete your account? This action cannot be undone."
        case .none: return ""
        }
    }

    private var promptMessage: String {
        prompt == .some(.modeChoice) ? "Kick off a run for \(selectedGoal)." : ""
    }

    @ViewBuilder
    private var promptActions: some View {
        switch prompt {
        case .some(.modeChoice):
            Button(L10n.challengeFriends) { prompt = nil; path.append(Destination.challengeFriends) }
            Button("Ranked Match") { prompt = nil; path.append(Destination.ranked) }
            Button("Cancel", role: .cancel) {}
        case .some(.logout):
            Button("Logout", role: .destructive) { prompt = nil; session.signOut() }
            Button("Stay", role: .cancel) {}
        case .some(.deleteAccount):
            Button("Delete", role: .destructive) {
                prompt = nil
                Task {
                    if await viewModel.deleteAccount(userId: session.userId) {
                        session.signOut()
                    }
                }
            }
            Button("Cancel", role: .cancel) {}
        case .none:
            Button("Cancel", role: .cancel) {}
        }
    }

    // MARK: - 1. Top bar (`topBar`, `btnThemeToggle`, `btnDashboardCredits`, `btnMessenger`)

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
            .buttonStyle(DashboardPressStyle())

            // `logoImage`
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

            // `btnDashboardCredits` / `tvDashboardCredits`
            NavigationLink {
                CreditsTreasureView()
            } label: {
                HStack(spacing: 5) {
                    Image(systemName: "circle.circle.fill")
                        .font(.system(size: 14))
                        .foregroundStyle(AppTheme.Ink.gold)
                    Text("\(credits.currentCredits)")
                        .font(AppTheme.Font.captionBold)
                        .foregroundStyle(AppTheme.Ink.gold)
                }
                .padding(.horizontal, AppTheme.Spacing.sm)
                .frame(height: 34)
                .background(AppTheme.Ink.surface)
                .clipShape(Capsule())
                .overlay(Capsule().stroke(AppTheme.Ink.gold.opacity(0.4), lineWidth: 1))
            }
            .padding(.trailing, 6)

            // `btnMessenger`
            NavigationLink {
                MessengerView()
            } label: {
                Image(systemName: "bubble.left.and.bubble.right.fill")
                    .font(.system(size: 17))
                    .frame(width: 42, height: 42)
                    .foregroundStyle(AppTheme.Ink.teal)
            }
            .padding(.trailing, 4)

            // `btnThemeToggle` — Android writes the pref then `recreate()`s the
            // activity; `MediGyaanApp` observes `AppPreferences.darkMode` instead.
            Button {
                darkMode.toggle()
                RemoteLogger.log(tag: "Dashboard_Theme_Toggle", message: "Dark mode toggled to: \(darkMode)")
            } label: {
                Image(systemName: darkMode ? "sun.max.fill" : "moon.fill")
                    .font(.system(size: 17))
                    .frame(width: 42, height: 42)
                    .foregroundStyle(AppTheme.Ink.iconTint)
            }
            .buttonStyle(DashboardPressStyle())
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .frame(height: 64)
    }

    // MARK: - 2. Scrollable dashboard content

    private var content: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.md) {
                goalSwitcherBanner.dashboardEntrance(0)
                categorySelector.dashboardEntrance(1)
                searchField.dashboardEntrance(2)

                if let host = activeInviteHost, let lobbyId = activeInviteLobbyId {
                    battleInviteBanner(host: host, lobbyId: lobbyId).dashboardEntrance(3)
                }

                equippedCompanionHeroCard.dashboardEntrance(4)
                profileSummaryCard.dashboardEntrance(5)
                rankRow.dashboardEntrance(6)
                detailsCard.dashboardEntrance(7)
                quickPracticeTopicScroller.dashboardEntrance(8)
                todayChallengeCard.dashboardEntrance(9)
                motivationQuoteCard.dashboardEntrance(10)
                battleModes.dashboardEntrance(11)
                quickTiles.dashboardEntrance(12)
                streakCard.dashboardEntrance(13)

                Spacer().frame(height: 100)
            }
            .padding(.horizontal, AppTheme.Spacing.lg)
            .padding(.bottom, AppTheme.Spacing.xxl)
        }
        .refreshable {
            RemoteLogger.log(tag: "Dashboard_PullToRefresh", message: "Refreshing dashboard data")
            await reload()
            await viewModel.checkMobileVerification(userId: session.userId)
        }
    }

    // MARK: - 3. Goal switcher banner (`cardSubjects`, `txtChangeGoal`)

    private var goalSwitcherBanner: some View {
        Button {
            RemoteLogger.log(tag: "Dashboard_Goal_Tap", message: "User tapped goal banner: \(selectedGoal)")
            isShowingGoalSelection = true
        } label: {
            HStack(spacing: AppTheme.Spacing.sm) {
                Image(systemName: "target")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(AppTheme.Ink.teal)

                Text("CURRICULUM:")
                    .font(AppTheme.Font.captionBold)
                    .foregroundStyle(AppTheme.Ink.textSecondary)

                Text(selectedGoal)
                    .font(AppTheme.Font.captionBold)
                    .foregroundStyle(AppTheme.Ink.textPrimary)

                Spacer()

                HStack(spacing: 3) {
                    Text("Change Goal")
                        .font(AppTheme.Font.micro.weight(.semibold))
                    Image(systemName: "chevron.right")
                        .font(.system(size: 9, weight: .bold))
                }
                .foregroundStyle(AppTheme.Ink.teal)
            }
            .padding(.horizontal, AppTheme.Spacing.md)
            .padding(.vertical, AppTheme.Spacing.sm)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                    .fill(AppTheme.Ink.surface)
                    .overlay(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                            .stroke(AppTheme.Ink.teal.opacity(0.3), lineWidth: 1)
                    )
            )
        }
        .buttonStyle(DashboardPressStyle())
    }

    // MARK: - 4. Exam category selector (`setupCategoryCards`)

    /// Android kept eight category cards in the layout and revealed only the
    /// one matching `selectedSubject`, which it re-selected from and answered
    /// with `showModeDialog`. iOS keeps all eight visible so the choice is real,
    /// and reproduces the dialog that follows a switch.
    private var categorySelector: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: AppTheme.Spacing.sm) {
                ForEach(DashboardViewModel.categories, id: \.self) { category in
                    Button {
                        guard category != selectedGoal else { return }
                        selectedGoal = category
                        viewModel.persistCategory(category)
                        RemoteLogger.log(
                            tag: "Dashboard_Category_Changed",
                            message: "User switched category to: \(category)"
                        )
                        prompt = .modeChoice
                        Task { await reload() }
                    } label: {
                        Text(category)
                            .font(AppTheme.Font.caption.weight(.semibold))
                            .foregroundStyle(category == selectedGoal ? Color.white : AppTheme.Ink.textSecondary)
                            .padding(.horizontal, AppTheme.Spacing.md)
                            .padding(.vertical, AppTheme.Spacing.sm)
                            .background(
                                RoundedRectangle(cornerRadius: AppTheme.Radius.pill)
                                    .fill(category == selectedGoal ? AppTheme.Ink.teal : AppTheme.Ink.surface)
                            )
                    }
                    .buttonStyle(DashboardPressStyle())
                }
            }
            .padding(.vertical, 2)
        }
    }

    // MARK: - 5. Search box (`searchEditText`)

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
        .buttonStyle(DashboardPressStyle())
    }

    // MARK: - 6. Active battle invite (`checkActiveInvitations`, `showInviteBanner`)

    private func battleInviteBanner(host: String, lobbyId: String) -> some View {
        InkCard(fill: AppTheme.Ink.invitation, radius: AppTheme.Radius.card) {
            HStack(spacing: AppTheme.Spacing.md) {
                Image(systemName: "person.2.wave.2.fill")
                    .font(.system(size: 24))
                    .foregroundStyle(AppTheme.Ink.textTertiary)

                VStack(alignment: .leading, spacing: 2) {
                    Text("Battle Invitation ⚔️")
                        .font(AppTheme.Font.callout.weight(.bold))
                        .foregroundStyle(AppTheme.Ink.textPrimary)
                    // `showInviteBanner`'s "$host invited you to battle!".
                    Text("\(host) invited you to battle!")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Ink.textSecondary)
                }

                Spacer()

                NavigationLink {
                    BattleLobbyView(lobbyId: lobbyId, topicName: selectedGoal, isHost: false)
                } label: {
                    Text("Accept")
                        .font(AppTheme.Font.captionBold)
                        .padding(.horizontal, AppTheme.Spacing.md)
                        .padding(.vertical, AppTheme.Spacing.xs)
                        .background(Capsule().fill(AppTheme.Ink.elevated))
                        .foregroundStyle(AppTheme.Ink.textPrimary)
                }
            }
        }
    }

    // MARK: - 7. Equipped guardian hero card (`layoutDashboardHeroCard`)

    private var equippedCompanionHeroCard: some View {
        InkCard(
            fill: AppTheme.Ink.profileCard,
            stroke: AppTheme.Ink.teal.opacity(0.6),
            radius: AppTheme.Radius.materialCard
        ) {
            HStack(spacing: AppTheme.Spacing.md) {
                Image(systemName: "shield.checkered")
                    .font(.system(size: 34))
                    .foregroundStyle(AppTheme.Ink.cyan)
                    .frame(width: 72, height: 72)
                    .background(Circle().fill(AppTheme.Ink.elevated))

                VStack(alignment: .leading, spacing: 3) {
                    HStack(spacing: 6) {
                        Text("EQUIPPED GUARDIAN")
                            .font(AppTheme.Font.micro.weight(.bold))
                            .foregroundStyle(AppTheme.Ink.teal)
                        Text("• Tier 1")
                            .font(AppTheme.Font.micro)
                            .foregroundStyle(AppTheme.Ink.textSecondary)
                    }

                    Text(selectedAvatarName)
                        .font(AppTheme.Font.title3)
                        .foregroundStyle(AppTheme.Ink.textPrimary)
                        .lineLimit(1)

                    Text("Combat Power: \(max(stats.points * 3, 1450)) CP")
                        .font(AppTheme.Font.micro.weight(.semibold))
                        .foregroundStyle(AppTheme.Ink.gold)

                    NavigationLink {
                        WarriorSelectionView()
                    } label: {
                        HStack(spacing: 4) {
                            Text("Switch Guardian (27 Warriors)")
                            Image(systemName: "chevron.right")
                                .font(.system(size: 8, weight: .bold))
                        }
                        .font(AppTheme.Font.micro.weight(.bold))
                        .foregroundStyle(AppTheme.Ink.teal)
                        .padding(.top, 2)
                    }
                }

                Spacer(minLength: 0)
            }
        }
    }

    // MARK: - 8. Profile summary card (`profileSummaryCard`, `iv_profile_dashboard`)

    private var profileSummaryCard: some View {
        InkCard(
            fill: AppTheme.Ink.profileCard,
            stroke: AppTheme.Ink.blue,
            radius: AppTheme.Radius.materialCard
        ) {
            HStack(spacing: AppTheme.Spacing.md) {
                // The avatar opened the guardian showcase; the card body opened
                // the profile. Two targets, as in Kotlin.
                NavigationLink {
                    GuardianShowcaseView(initialWarriorId: selectedAvatarId)
                } label: {
                    AvatarView(
                        url: viewModel.profile.photoURL ?? session.currentUser?.avatarURL,
                        name: displayName,
                        size: 70,
                        strokeColor: AppTheme.Ink.gold,
                        strokeWidth: 2,
                        backdrop: AppTheme.Ink.avatarBackdrop
                    )
                }

                NavigationLink {
                    ProfileView()
                } label: {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(timeOfDayGreeting)
                            .font(AppTheme.Font.micro.weight(.semibold))
                            .foregroundStyle(AppTheme.Ink.teal)

                        Text(displayName)
                            .font(AppTheme.Font.cardTitle)
                            .foregroundStyle(AppTheme.Ink.textPrimary)
                            .lineLimit(1)

                        HStack(spacing: AppTheme.Spacing.sm) {
                            Text("\(displayStreak) Days Active")
                                .font(AppTheme.Font.subheadline)
                                .foregroundStyle(AppTheme.Ink.textSecondary)

                            Text("•")
                                .foregroundStyle(AppTheme.Ink.textSecondary)

                            Text("Level \(viewModel.profile.level)")
                                .font(AppTheme.Font.subheadline.weight(.semibold))
                                .foregroundStyle(AppTheme.Ink.gold)
                        }

                        // `expProgressBar` = (exp % 1000) / 1000.
                        VStack(alignment: .leading, spacing: 2) {
                            ProgressView(
                                value: Double(viewModel.experienceInLevel),
                                total: Double(DashboardViewModel.levelWidth)
                            )
                            .tint(AppTheme.Ink.gold)
                            .scaleEffect(y: 1.2)

                            Text("\(viewModel.experienceInLevel) / \(DashboardViewModel.levelWidth) XP to Next Level")
                                .font(AppTheme.Font.micro)
                                .foregroundStyle(AppTheme.Ink.gold)
                        }
                        .padding(.top, AppTheme.Spacing.xxs)
                    }
                }

                Spacer(minLength: 0)
            }
        }
    }

    // MARK: - 9. Two-up rank row (`rankCard`, `details`, `badgeContainer`)

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

                    // `badgeContainer` — the tier art `updateBadgeUI` swapped in,
                    // tappable for `showRankInfoDialog`.
                    Button {
                        isShowingRankProgression = true
                    } label: {
                        AndroidIcon(viewModel.rankTier.artwork, size: 46, tint: AppTheme.Ink.gold)
                    }
                    .buttonStyle(DashboardPressStyle())

                    Text(viewModel.rankTier.title)
                        .font(AppTheme.Font.subheadline.weight(.bold))
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

                    Text(predictedRankText)
                        .font(AppTheme.Font.prediction)
                        .foregroundStyle(AppTheme.Ink.cyan)
                        .minimumScaleFactor(0.6)
                        .lineLimit(1)

                    Text(predictedConfidenceText)
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Ink.textSecondary)
                        .multilineTextAlignment(.center)
                        .lineLimit(2)

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

    // MARK: - 10. Four-up quick stats (`txtStatsWins` … `txtStatsBattles`)

    /// Kotlin sourced the tile entirely from `DailyStatsManager`; the remote
    /// summary is only a fallback for a user with no local history at all.
    private var detailsCard: some View {
        InkCard(fill: AppTheme.Ink.surface, radius: AppTheme.Radius.card) {
            HStack(spacing: 0) {
                InkStatTile(value: "\(displayWins)", label: "Wins ✅")
                statDivider

                NavigationLink {
                    AccuracyView()
                } label: {
                    InkStatTile(value: displayAccuracyText, label: "Accuracy 🎯")
                }

                statDivider

                NavigationLink {
                    AccuracyView()
                } label: {
                    InkStatTile(value: "\(displayStreak)", label: "Streak 🔥")
                }

                statDivider

                InkStatTile(value: "\(displayBattles)", label: "Battles 🏆")
            }
        }
    }

    private var statDivider: some View {
        Rectangle()
            .fill(AppTheme.Ink.slate.opacity(0.5))
            .frame(width: 1, height: 34)
    }

    // MARK: - 11. Quick practice topics (`compose_topic_selector`)

    private var quickPracticeTopicScroller: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
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

            switch viewModel.topicsState {
            case .idle, .loading:
                HStack(spacing: AppTheme.Spacing.sm) {
                    ProgressView().scaleEffect(0.8)
                    Text("Loading clinical topics…")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Ink.textSecondary)
                }
                .padding(.vertical, AppTheme.Spacing.sm)

            case let .failed(message):
                Text(message)
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Ink.textSecondary)

            case let .loaded(topics):
                if topics.isEmpty {
                    Text("No topics available for this subject.")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Ink.textSecondary)
                } else {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: AppTheme.Spacing.sm) {
                            ForEach(topics) { topic in
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
                                    Text(topic.name)
                                        .font(AppTheme.Font.subheadline.weight(.medium))
                                        .foregroundStyle(AppTheme.Ink.textPrimary)
                                        .lineLimit(1)
                                        .padding(.horizontal, AppTheme.Spacing.lg)
                                        .padding(.vertical, AppTheme.Spacing.sm)
                                        .background(
                                            RoundedRectangle(cornerRadius: AppTheme.Radius.option)
                                                .fill(AppTheme.Ink.surface)
                                                .overlay(
                                                    RoundedRectangle(cornerRadius: AppTheme.Radius.option)
                                                        .stroke(AppTheme.Ink.border, lineWidth: 1)
                                                )
                                        )
                                }
                            }
                        }
                        .padding(.vertical, 2)
                    }
                }
            }
        }
    }

    // MARK: - 12. Daily high-yield challenge (`cardTodayChallenge`)

    private var todayChallengeCard: some View {
        InkCard(
            fill: AppTheme.Ink.profileCard,
            stroke: AppTheme.Ink.teal.opacity(0.4),
            radius: AppTheme.Radius.card
        ) {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                Button {
                    withAnimation(.spring(response: 0.35)) {
                        isTodayChallengeExpanded.toggle()
                    }
                } label: {
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            HStack(spacing: 6) {
                                Text("TODAY'S DAILY HIGH-YIELD")
                                    .font(AppTheme.Font.micro.weight(.bold))
                                    .foregroundStyle(AppTheme.Ink.gold)
                                Text("• 10 MCQs")
                                    .font(AppTheme.Font.micro.weight(.semibold))
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
                .buttonStyle(DashboardPressStyle())

                if isTodayChallengeExpanded {
                    Divider().padding(.vertical, 2)

                    Text(viewModel.todayQuestion?.question ?? "Loading today's high-yield clinical challenge…")
                        .font(AppTheme.Font.callout)
                        .foregroundStyle(AppTheme.Ink.textPrimary)
                        .padding(.vertical, AppTheme.Spacing.xxs)

                    // `compose_today_options` — Kotlin auto-started the full
                    // challenge from any option tap.
                    ForEach(todayOptions, id: \.self) { option in
                        NavigationLink {
                            QuizView(quiz: Self.todayChallengeQuiz(subject: selectedGoal))
                        } label: {
                            Text(option)
                                .font(AppTheme.Font.micro)
                                .foregroundStyle(AppTheme.Ink.textPrimary)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(AppTheme.Spacing.sm)
                                .background(
                                    RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                                        .fill(AppTheme.Ink.elevated)
                                )
                        }
                        .buttonStyle(DashboardPressStyle())
                    }

                    NavigationLink {
                        QuizView(quiz: Self.todayChallengeQuiz(subject: selectedGoal))
                    } label: {
                        Text("Start Full 10-Question Daily Challenge")
                            .font(AppTheme.Font.captionBold)
                            .frame(maxWidth: .infinity)
                            .frame(height: 38)
                            .background(
                                RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                                    .fill(AppTheme.Palette.primary)
                            )
                            .foregroundStyle(AppTheme.Palette.onPrimary)
                    }
                    .padding(.top, AppTheme.Spacing.xxs)
                }
            }
        }
    }

    private var todayOptions: [String] {
        viewModel.todayQuestion?.options ?? []
    }

    private static func todayChallengeQuiz(subject: String) -> Quiz {
        Quiz(
            id: 200,
            title: "Today's Clinical Challenge",
            topic: "Uncategorized",
            subject: subject,
            questionCount: 10,
            durationSeconds: 300
        )
    }

    // MARK: - 13. Clinical motivation quote (`motivationCard`)

    private var motivationQuoteCard: some View {
        Button {
            let impact = UIImpactFeedbackGenerator(style: .light)
            impact.impactOccurred()
            withAnimation(.easeInOut(duration: 0.25)) {
                currentMotivationIndex = (currentMotivationIndex + 1) % motivationQuotes.count
            }
        } label: {
            InkCard(
                fill: AppTheme.Ink.surface,
                stroke: AppTheme.Ink.slate.opacity(0.3),
                radius: AppTheme.Radius.card
            ) {
                HStack(spacing: AppTheme.Spacing.md) {
                    Image(systemName: "quote.opening")
                        .font(.system(size: 20))
                        .foregroundStyle(AppTheme.Ink.teal)

                    Text(motivationText)
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
        .buttonStyle(DashboardPressStyle())
    }

    /// Before the first tap the field shows the accuracy-threshold line
    /// `loadDashboardAccuracyStats` left behind; afterwards it rotates.
    private var motivationText: String {
        guard motivationQuotes.indices.contains(currentMotivationIndex) else {
            return viewModel.localStats.encouragement
        }
        return motivationQuotes[currentMotivationIndex]
    }

    // MARK: - 14. Battle modes (`setupBattleModeCards`)

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
                // `cardRankedBattle`
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

                // `cardChallengeFriends`
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

                // `cardRapidFire`
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
                .buttonStyle(DashboardPressStyle())

                // `cardPracticeMode`
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

                // `cardCustomBattle` — Kotlin opened the topic dialog first.
                NavigationLink {
                    TopicChallengePickerView(mode: .challenge, subject: selectedGoal)
                } label: {
                    BattleModeCard(
                        tag: "🛡️ CUSTOM",
                        emoji: "🛡️",
                        title: "Create Room",
                        subtitle: "Host a private battle",
                        fill: AppTheme.Ink.custom
                    )
                }

                // `cardSurvivalMode`
                Button {
                    RemoteLogger.log(tag: "Dashboard_Tap", message: "User tapped Survival Mode (goal: \(selectedGoal))")
                    isShowingSurvivalMode = true
                } label: {
                    BattleModeCard(
                        tag: "💀 SURVIVAL",
                        emoji: "⏳",
                        title: "Survival Mode",
                        subtitle: "3 strikes and you're out",
                        fill: AppTheme.Ink.rapidFire
                    )
                }
                .buttonStyle(DashboardPressStyle())

                // `cardSubjectSurvival`
                NavigationLink {
                    TopicChallengePickerView(mode: .solo, subject: selectedGoal)
                } label: {
                    BattleModeCard(
                        tag: "🫀 TOPIC RUN",
                        emoji: "🫀",
                        title: "Subject Survival",
                        subtitle: "Survive one high-yield topic",
                        fill: AppTheme.Ink.testMode
                    )
                }

                // `cardCustomModeBattle`
                NavigationLink {
                    TopicChallengePickerView(mode: .solo, subject: selectedGoal)
                } label: {
                    BattleModeCard(
                        tag: "⚔️ CUSTOM BATTLE",
                        emoji: "🎯",
                        title: "Custom Battle",
                        subtitle: "Pick a topic and go solo",
                        fill: AppTheme.Ink.ranked
                    )
                }

                // `cardKingOfTopic` — topics under 200 questions are locked in
                // Kotlin; see BLOCKERS for the picker's missing gate.
                NavigationLink {
                    TopicChallengePickerView(mode: .challenge, subject: selectedGoal)
                } label: {
                    BattleModeCard(
                        tag: "👑 KING OF TOPIC",
                        emoji: "👑",
                        title: "King of the Topic",
                        subtitle: "200+ question topics only",
                        fill: AppTheme.Ink.custom
                    )
                }
            }
        }
    }

    // MARK: - 15. Quick action tiles (`setupQuickActionCards`, `setupDashboardNavigationCards`)

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

            NavigationLink { AiChatView() } label: {
                QuickTile(emoji: "🤖", title: "Medical AI")
            }

            NavigationLink { TopicsView() } label: {
                QuickTile(emoji: "📚", title: "Subjects")
            }

            NavigationLink { SharedQuestionsView() } label: {
                QuickTile(emoji: "📊", title: "Shared MCQs")
            }

            NavigationLink { HistoryView() } label: {
                QuickTile(emoji: "📜", title: "Battle History")
            }

            NavigationLink { ReferralView() } label: {
                QuickTile(emoji: "💌", title: "Referral Program")
            }

            NavigationLink { ReelsView() } label: {
                QuickTile(emoji: "🎬", title: "Medical Reels")
            }

            NavigationLink { WarriorSelectionView() } label: {
                QuickTile(emoji: "🛡️", title: "27 Warriors")
            }

            NavigationLink { CreditsTreasureView() } label: {
                QuickTile(emoji: "💎", title: "Treasury")
            }

            NavigationLink { PredictorView() } label: {
                QuickTile(emoji: "🧾", title: "Predictor")
            }
        }
    }

    // MARK: - 16. Daily learning streak (`streakCard`)

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
                        Text("\(displayStreak) Days Active • View Detailed Analytics")
                            .font(AppTheme.Font.subheadline)
                            .foregroundStyle(AppTheme.Ink.textSecondary)
                        if let today = viewModel.localStats.todayAccuracyText {
                            Text(today)
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
    }

    // MARK: - 17. Navigation drawer (`setupToolbarAndSidebar`)

    private enum DrawerDestination: Hashable {
        case leaderboard, thesis, researchWorkspace, predictor, referral, poster
        case profile, settings, help, goalSelection, creditsTreasure
        case aiChat, sharedQuestions, accuracy
        case reels, warriors
        case ranked, challengeFriends, myQuizzes, editProfile, widgetSettings
    }

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
                    drawerLink("Edit Profile", .editProfile)
                    drawerLink("My Quizzes", .myQuizzes)
                    drawerLink("Widget Settings", .widgetSettings)
                    drawerLink("Settings", .settings)
                    drawerLink("Help & Support", .help)
                    // `nav_logout`
                    Button("Logout") {
                        isShowingMenu = false
                        prompt = .logout
                    }
                    // `side_delete_account`
                    Button("Delete Account", role: .destructive) {
                        isShowingMenu = false
                        prompt = .deleteAccount
                    }
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

    private func drawerLink(_ title: String, _ destination: DrawerDestination) -> some View {
        Button {
            isShowingMenu = false
            path.append(destination)
        } label: {
            Text(title)
        }
    }

    // MARK: - Derived values

    private var displayName: String {
        let name = viewModel.profile.name.isEmpty
            ? (session.currentUser?.name ?? "")
            : viewModel.profile.name
        return name.isEmpty ? "User" : name
    }

    private var displayStreak: Int {
        viewModel.localStats.hasHistory ? viewModel.localStats.streak : stats.streak
    }

    private var displayWins: Int {
        viewModel.localStats.hasHistory ? viewModel.localStats.wins : stats.correct
    }

    private var displayBattles: Int {
        viewModel.localStats.hasHistory ? viewModel.localStats.battles : stats.attempted
    }

    private var displayAccuracyText: String {
        guard viewModel.localStats.hasHistory else {
            guard stats.accuracy > 0 else { return "0%" }
            return stats.accuracy > 1 ? "\(Int(stats.accuracy))%" : "\(Int(stats.accuracy * 100))%"
        }
        return viewModel.localStats.accuracyText
    }

    private var predictedRankText: String {
        guard let range = viewModel.prediction?.range, !range.isEmpty else { return "—" }
        return range
    }

    private var predictedConfidenceText: String {
        guard let prediction = viewModel.prediction, !prediction.confidenceText.isEmpty else {
            return "Calibrating Performance"
        }
        return prediction.confidenceText
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
}

// MARK: - Dashboard sub-views

/// A tinted battle-mode card: uppercase tag, emoji, headline title, caption
/// subtitle. One per card id in `setupBattleModeCards`.
struct BattleModeCard: View {
    let tag: String
    let emoji: String
    let title: String
    let subtitle: String
    let fill: Color

    var body: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
            Text(tag)
                .font(AppTheme.Font.micro.weight(.bold))
                .foregroundStyle(AppTheme.Ink.textTertiary)

            Text(emoji)
                .font(AppTheme.Font.display)

            Text(title)
                .font(AppTheme.Font.cardTitle)
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

/// An emoji quick tile — the iOS stand-in for the `cardLeaderboard`,
/// `cardBattleHistory`, `cardSubjects` and `cardReferral` blocks that
/// `setupQuickActionCards` and `setupDashboardNavigationCards` wired.
struct QuickTile: View {
    let emoji: String
    let title: String

    var body: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            Text(emoji).font(.system(size: 26))
            Text(title)
                .font(AppTheme.Font.cardTitle)
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

/// Ports `showRankInfoDialog()` — the "Rank Progression Info" dialog, reachable
/// from `badgeContainer`, whose Android destination was the standalone
/// `RankActivity` this port replaces.
struct DashboardRankProgressionSheet: View {
    let tier: DashboardRankTier

    var body: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
            Text("Rank Progression Info")
                .font(AppTheme.Font.title3)
                .foregroundStyle(AppTheme.Ink.textPrimary)

            Text(tier.progressionSheet)
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Ink.textSecondary)

            Spacer()
        }
        .padding(AppTheme.Spacing.xl)
        .frame(maxWidth: .infinity, alignment: .leading)
        .inkBackground()
    }
}

/// Ports the two `AlertDialog`s behind `showMobileVerificationDialog` and
/// `showOtpConfirmationDialog`, which the activity raised from `onResume`
/// through `checkAndPromptMobileVerification`.
struct DashboardVerificationSheet: View {

    @EnvironmentObject private var viewModel: DashboardViewModel
    @EnvironmentObject private var session: SessionStore

    @State private var phone: String = ""
    @State private var otp: String = ""

    var body: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
            Text("🏥 MediGyaan Account Verification")
                .font(AppTheme.Font.title3)
                .foregroundStyle(AppTheme.Ink.teal)

            if let notice = viewModel.verificationNotice {
                Text(notice)
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Ink.gold)
            }

            switch viewModel.verification {
            case .hidden:
                Text("Your mobile number is verified.")
                    .font(AppTheme.Font.callout)
                    .foregroundStyle(AppTheme.Ink.textSecondary)

            case .phone:
                Text("Enter your 10-digit mobile number for order processing and payment verification:")
                    .font(AppTheme.Font.callout)
                    .foregroundStyle(AppTheme.Ink.textSecondary)

                TextField("Mobile Number (e.g. 9876543210)", text: $phone)
                    .keyboardType(.numberPad)
                    .textContentType(.telephoneNumber)
                    .font(AppTheme.Font.body)
                    .padding(AppTheme.Spacing.md)
                    .background(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.option)
                            .fill(AppTheme.Ink.surface)
                            .overlay(
                                RoundedRectangle(cornerRadius: AppTheme.Radius.option)
                                    .stroke(AppTheme.Ink.slate, lineWidth: 2)
                            )
                    )
                    .onAppear { phone = viewModel.profile.mobileNumber }

            case let .otp(phoneNumber):
                Text("An OTP has been sent to +91 \(phoneNumber).\nEnter the 6-digit OTP to complete MediGyaan verification:")
                    .font(AppTheme.Font.callout)
                    .foregroundStyle(AppTheme.Ink.textSecondary)

                TextField("Enter OTP (e.g. 123456)", text: $otp)
                    .keyboardType(.numberPad)
                    .textContentType(.oneTimeCode)
                    .font(AppTheme.Font.title3)
                    .multilineTextAlignment(.center)
                    .padding(AppTheme.Spacing.md)
                    .background(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.option)
                            .fill(AppTheme.Ink.surface)
                            .overlay(
                                RoundedRectangle(cornerRadius: AppTheme.Radius.option)
                                    .stroke(AppTheme.Ink.teal, lineWidth: 2)
                            )
                    )
            }

            if viewModel.isVerifying {
                ProgressView().frame(maxWidth: .infinity)
            } else {
                actions
            }

            Spacer()
        }
        .padding(AppTheme.Spacing.xl)
        .frame(maxWidth: .infinity, alignment: .leading)
        .inkBackground()
    }

    @ViewBuilder
    private var actions: some View {
        switch viewModel.verification {
        case .hidden:
            Button("Close") { viewModel.dismissVerification() }
                .buttonStyle(DashboardPressStyle())

        case .phone:
            // `sendMobileVerificationOtp`'s guard: ten digits, all numeric.
            Button("VERIFY & SEND OTP") {
                Task { await viewModel.sendVerificationOTP(userId: session.userId, phone: phone) }
            }
            .buttonStyle(DashboardPressStyle())
            .disabled(!isPhoneValid)

            Button("SKIP FOR NOW") { viewModel.dismissVerification() }
                .buttonStyle(DashboardPressStyle())

        case .otp:
            Button("VERIFY OTP") {
                Task {
                    await viewModel.verifyOTP(userId: session.userId, phone: currentPhone, otp: otp)
                }
            }
            .buttonStyle(DashboardPressStyle())

            Button("CANCEL") {
                otp = ""
                viewModel.dismissVerification()
            }
            .buttonStyle(DashboardPressStyle())
        }
    }

    private var isPhoneValid: Bool {
        phone.count == 10 && phone.allSatisfy(\.isNumber)
    }

    /// The number the OTP step verifies against — the sheet keeps no state of
    /// its own beyond the field it was opened with.
    private var currentPhone: String {
        if case let .otp(phoneNumber) = viewModel.verification { return phoneNumber }
        return phone
    }
}

/// Ports `animateClick()` — `R.anim.press_pop` replayed on every tappable card.
private struct DashboardPressStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.96 : 1)
            .animation(.easeOut(duration: 0.12), value: configuration.isPressed)
    }
}

/// Ports `animateDashboardEntrance()` — `R.anim.card_entrance` replayed on each
/// card with `startOffset = (index * 55ms).coerceAtMost(700ms)`.
private struct DashboardCardEntrance: ViewModifier {
    let index: Int
    @State private var hasEntered = false

    func body(content: Content) -> some View {
        content
            .opacity(hasEntered ? 1 : 0)
            .offset(y: hasEntered ? 0 : 12)
            .onAppear {
                guard !hasEntered else { return }
                let delay = min(Double(index) * 0.055, 0.7)
                Task {
                    try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
                    withAnimation(.easeOut(duration: 0.28)) {
                        self.hasEntered = true
                    }
                }
            }
    }
}

private extension View {
    func dashboardEntrance(_ index: Int) -> some View {
        modifier(DashboardCardEntrance(index: index))
    }
}