import SwiftUI
import AVFoundation

/// 1:1 SwiftUI Replica of Android `SubjectTestActivity.kt`.
///
/// Features:
/// - 3 Operating Modes: Fixed Test Mode, Multiplayer Arena Mode (Real-time Firebase RTDB), and Single Player Mode.
/// - 15 Questions Stream from Selected Questions Database (`fetchOrCreateSharedQuestionList` with 15-question limit).
/// - Real-time 2-Player Combat Synchronization:
///   - Shared challenge room at `challenges/{challengeId}` on Firebase RTDB.
///   - Dual animated health bars (0-100 HP) and live scores for both local player and opponent.
///   - Live combat exchange: correct answers deal 15 damage (+ Surge bonus) to opponent; misses take 10 recoil damage.
///   - `last_action` combat event logging with floating damage numbers & shields.
///   - Intelligent fallback Bot Challenger simulation for instant 1v1 playability.
/// - 5-Option Clinical MCQ Support (Options A, B, C, D, and E for AIIMS / INI-CET).
/// - TextToSpeech (TTS) via `AVSpeechSynthesizer` with speak/stop explanation audio controls.
/// - 4 Hero Kit Powers: Intel Clue Scan, Strike 50-50 Distractor Elimination, Barrier Shield, Surge Multiplier.
/// - Question streak bonus tracker and real-time score sync.
/// - Comprehensive 15-question post-match review and results summary modal.
struct SubjectTestActivityView: View {

    // ─── Intent Extras ────────────────────────────────────────────────────────
    var uniqueId: Int = 0
    var subject: String = "NEET PG"
    var topic: String? = nil
    var challengeId: String = ""
    var isChallenge: Bool = false
    var isHost: Bool = false
    var questionIdList: [Int]? = nil
    var userWarrior: Warrior? = nil
    var opponentId: String = ""
    var opponentName: String = "Opponent"
    var isBotMatch: Bool = false
    var onFinish: ((BattleResultSummary) -> Void)? = nil

    @AppStorage("selected_avatar_id") private var selectedAvatarId: Int = 1

    private var equippedHeroKit: GuardianHeroKit {
        let avatarIdx = GuardianRegistry.avatarIndex(for: userWarrior?.id ?? selectedAvatarId)
        return GuardianRegistry.getHeroKit(for: avatarIdx) ?? GuardianRegistry.getHeroKit(for: 1001)!
    }

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @Environment(\.dismiss) private var dismiss

    // ─── Operating Mode ───────────────────────────────────────────────────────
    enum TestMode {
        case fixedTest
        case multiplayer
        case singlePlayer
    }

    @State private var mode: TestMode = .singlePlayer

    // ─── Player Combat State ──────────────────────────────────────────────────
    @State private var currentHp: Int = 100
    @State private var myScore: Int = 0
    @State private var currentStreak: Int = 0

    // ─── Opponent Combat State (Multiplayer) ──────────────────────────────────
    @State private var opponentHp: Int = 100
    @State private var opponentScore: Int = 0
    @State private var opponentNameResolved: String = "Opponent"
    @State private var opponentFinished: Bool = false
    @State private var isGameOverHandled: Bool = false

    // ─── 15 Questions State ───────────────────────────────────────────────────
    @State private var allQuestionIds: [Int] = []
    @State private var currentIndex: Int = 0
    @State private var currentQuestion: Question? = nil
    @State private var questionCache: [Int: Question] = [:]
    @State private var answeredIndices: Set<Int> = []
    @State private var selectedOptionIndex: Int? = nil
    @State private var isAnswerSubmitted: Bool = false
    @State private var showExplanation: Bool = false
    @State private var eliminatedOptionIndices: Set<Int> = []

    // ─── Timer (15 Minutes for 15 Questions) ──────────────────────────────────
    @State private var remainingTimerSeconds: Int = 900 // 15 min (matches 15 * 60 * 1000L in Android)
    private let countdownTimer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()

    // ─── 4 Hero Powers ────────────────────────────────────────────────────────
    @State private var intelCharges: Int = 3
    @State private var strikeCharges: Int = 2
    @State private var defenseCharges: Int = 3
    @State private var surgeCharges: Int = 1

    @State private var intelCooldown: Int = 0
    @State private var strikeCooldown: Int = 0
    @State private var defenseCooldown: Int = 0
    @State private var surgeCooldown: Int = 0

    @State private var shieldRoundsActive: Int = 0
    @State private var surgeScoreMultiplierActive: Bool = false
    @State private var intelClueText: String? = nil

    // ─── Audio TextToSpeech ───────────────────────────────────────────────────
    @State private var speechSynthesizer = AVSpeechSynthesizer()
    @State private var isSpeaking: Bool = false

    // ─── Floating Combat / Feedback ───────────────────────────────────────────
    @State private var floatingBannerText: String? = nil
    @State private var floatingBannerColor: Color = Color.yellow

    // ─── Alerts & Reviews ─────────────────────────────────────────────────────
    @State private var showFinishConfirmationAlert: Bool = false
    @State private var showResultSummary: Bool = false
    @State private var resultSummaryData: BattleResultSummary? = nil
    @State private var reviewItems: [QuestionReviewItem] = []
    @State private var isLoadingQuestions: Bool = true

    // ─── Firebase RTDB Background Tasks ───────────────────────────────────────
    @State private var multiplayerPollingTask: Task<Void, Never>? = nil
    @State private var botSimulationTask: Task<Void, Never>? = nil
    @State private var lastHandledActionId: String = ""

    private let dbBaseUrl = "https://medigyaan-11cba-default-rtdb.firebaseio.com"
    private let apiBaseUrl = "https://medigyaan.com/Neurons/"

    var body: some View {
        ZStack {
            // Dark medical cyber gradient background
            LinearGradient(
                colors: [Color(hex: "#060A14"), Color(hex: "#0E182A"), Color(hex: "#080D18")],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            VStack(spacing: 0) {
                // Header Bar (Progress, Timer, Streak, Finish Button)
                headerTopBar

                // Dual Player Health & Score Bar (Multiplayer Mode)
                if mode == .multiplayer || isChallenge {
                    multiplayerVersusCard
                        .padding(.horizontal, AppTheme.Spacing.md)
                        .padding(.top, 4)
                }

                // Hero Powers Bar (Multiplayer / Challenge Mode)
                if mode == .multiplayer || isChallenge {
                    powersToolbar
                        .padding(.horizontal, AppTheme.Spacing.md)
                        .padding(.top, 6)
                }

                Divider()
                    .background(Color.white.opacity(0.12))
                    .padding(.vertical, 8)

                // Main Question Content
                if isLoadingQuestions {
                    Spacer()
                    VStack(spacing: AppTheme.Spacing.md) {
                        ProgressView().tint(Color.yellow).scaleEffect(1.3)
                        Text("Loading Clinical Test Modules...")
                            .font(AppTheme.Font.headline)
                            .foregroundStyle(Color.white)
                        Text(subject + (topic != nil ? " • \(topic!)" : ""))
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(Color.white.opacity(0.6))
                    }
                    Spacer()
                } else if let q = currentQuestion {
                    ScrollView(showsIndicators: false) {
                        VStack(spacing: AppTheme.Spacing.md) {
                            questionCard(q)
                            optionsGrid(q)

                            if showExplanation {
                                explanationCard(q)
                            }
                        }
                        .padding(.horizontal, AppTheme.Spacing.md)
                        .padding(.bottom, AppTheme.Spacing.xl)
                    }
                } else {
                    Spacer()
                    VStack(spacing: 12) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .font(.system(size: 36))
                            .foregroundStyle(Color.yellow)
                        Text("No Questions Available")
                            .font(AppTheme.Font.title3)
                            .foregroundStyle(Color.white)
                        Button("Reload Deck") {
                            initializeTestSession()
                        }
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(Color.cyan)
                    }
                    Spacer()
                }

                // Bottom Navigation (Previous & Submit / Next)
                bottomControlsBar
            }

            // High-Yield Intel Clue Banner Popover
            if let clue = intelClueText {
                VStack {
                    HStack(spacing: 8) {
                        Image(systemName: "magnifyingglass.circle.fill")
                            .foregroundStyle(Color.cyan)
                        Text(clue)
                            .font(.system(size: 13, weight: .bold))
                            .foregroundStyle(Color.white)
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 10)
                    .background(Capsule().fill(Color(hex: "#0F2840").opacity(0.95)))
                    .overlay(Capsule().stroke(Color.cyan.opacity(0.6), lineWidth: 1.5))
                    .shadow(color: Color.cyan.opacity(0.4), radius: 8)
                    .padding(.top, 60)
                    Spacer()
                }
                .transition(.move(edge: .top).combined(with: .opacity))
            }

            // Floating Combat Flyout Banner
            if let banner = floatingBannerText {
                VStack {
                    Spacer()
                    Text(banner)
                        .font(.system(size: 14, weight: .heavy, design: .rounded))
                        .foregroundStyle(floatingBannerColor)
                        .padding(.horizontal, 18)
                        .padding(.vertical, 8)
                        .background(Capsule().fill(Color.black.opacity(0.85)))
                        .overlay(Capsule().stroke(floatingBannerColor.opacity(0.7), lineWidth: 1.5))
                        .shadow(color: floatingBannerColor.opacity(0.5), radius: 8)
                        .padding(.bottom, 75)
                }
                .transition(.scale.combined(with: .opacity))
            }
        }
        .navigationBarBackButtonHidden(true)
        .alert("Finish Test?", isPresented: $showFinishConfirmationAlert) {
            Button("Finish Test", role: .destructive) {
                stopSpeaking()
                finalizeTest()
            }
            Button("Resume", role: .cancel) {}
        } message: {
            Text("Are you sure you want to conclude the clinical test? Your current score (\(myScore) pts) will be submitted.")
        }
        .sheet(isPresented: $showResultSummary) {
            if let summary = resultSummaryData {
                ChallengeResultView(result: summary) {
                    showResultSummary = false
                    dismiss()
                }
            }
        }
        .onAppear {
            initializeTestSession()
        }
        .onDisappear {
            stopSpeaking()
            cleanupMultiplayer()
        }
        .onReceive(countdownTimer) { _ in
            handleTimerTick()
        }
    }

    // MARK: - Header Top Bar

    private var headerTopBar: some View {
        HStack {
            // Exit / Finish button
            Button {
                showFinishConfirmationAlert = true
            } label: {
                HStack(spacing: 4) {
                    Image(systemName: "flag.checkered.circle.fill")
                    Text("Finish")
                        .font(.system(size: 12, weight: .bold))
                }
                .foregroundStyle(Color.red.opacity(0.85))
                .padding(.horizontal, 10)
                .padding(.vertical, 5)
                .background(Capsule().fill(Color.red.opacity(0.12)))
            }

            Spacer()

            // Subject / Question 15 Counter Center Label
            VStack(spacing: 1) {
                Text(subject.uppercased())
                    .font(.system(size: 11, weight: .black, design: .monospaced))
                    .foregroundStyle(Color.yellow)
                Text(allQuestionIds.isEmpty ? "Clinical Test" : "Question \(currentIndex + 1) of \(allQuestionIds.count)")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(Color.white.opacity(0.85))
            }

            Spacer()

            // Timer & Streak
            HStack(spacing: 10) {
                if currentStreak > 1 {
                    HStack(spacing: 3) {
                        Image(systemName: "flame.fill").foregroundStyle(Color.orange)
                        Text("\(currentStreak)x")
                            .font(.system(size: 11, weight: .black, design: .rounded))
                            .foregroundStyle(Color.orange)
                    }
                    .padding(.horizontal, 6)
                    .padding(.vertical, 3)
                    .background(Capsule().fill(Color.orange.opacity(0.15)))
                }

                // Clock
                HStack(spacing: 4) {
                    Image(systemName: "clock")
                        .font(.caption)
                        .foregroundStyle(remainingTimerSeconds <= 120 ? Color.red : Color.yellow)
                    Text(timeFormatted(remainingTimerSeconds))
                        .font(.system(size: 13, weight: .heavy, design: .monospaced))
                        .foregroundStyle(remainingTimerSeconds <= 120 ? Color.red : Color.white)
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Capsule().fill(Color.white.opacity(0.1)))
            }
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.top, 8)
    }

    private func timeFormatted(_ totalSeconds: Int) -> String {
        let minutes = totalSeconds / 60
        let seconds = totalSeconds % 60
        return String(format: "%02d:%02d", minutes, seconds)
    }

    // MARK: - Dual Player Multiplayer Versus Card

    private var multiplayerVersusCard: some View {
        HStack(spacing: 10) {
            // Player 1 (YOU)
            HStack(spacing: 6) {
                ZStack {
                    Circle()
                        .fill(Color.blue.opacity(0.3))
                        .frame(width: 34, height: 34)
                    Image(systemName: "person.fill")
                        .font(.system(size: 16))
                        .foregroundStyle(Color.cyan)
                }

                VStack(alignment: .leading, spacing: 2) {
                    Text("YOU")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundStyle(Color.white)
                    // HP Bar
                    GeometryReader { geo in
                        ZStack(alignment: .leading) {
                            Capsule().fill(Color.white.opacity(0.15))
                            Capsule().fill(hpColor(currentHp))
                                .frame(width: max(0, geo.size.width * CGFloat(currentHp) / 100.0))
                        }
                    }
                    .frame(height: 6)

                    HStack(spacing: 4) {
                        Text("\(currentHp) HP")
                            .font(.system(size: 10, weight: .heavy, design: .monospaced))
                            .foregroundStyle(hpColor(currentHp))
                        Text("• \(myScore) pts")
                            .font(.system(size: 10, weight: .semibold))
                            .foregroundStyle(Color.yellow)
                    }
                }
            }
            .frame(maxWidth: .infinity)

            // VS Badge
            VStack(spacing: 1) {
                Text("VS")
                    .font(.system(size: 11, weight: .black, design: .rounded))
                    .foregroundStyle(Color.red)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Capsule().fill(Color.red.opacity(0.2)))
                Text("LIVE")
                    .font(.system(size: 8, weight: .heavy))
                    .foregroundStyle(Color.green)
            }

            // Player 2 (Opponent)
            HStack(spacing: 6) {
                VStack(alignment: .trailing, spacing: 2) {
                    Text(opponentNameResolved)
                        .font(.system(size: 11, weight: .bold))
                        .foregroundStyle(Color.white)
                        .lineLimit(1)
                    // HP Bar
                    GeometryReader { geo in
                        ZStack(alignment: .trailing) {
                            Capsule().fill(Color.white.opacity(0.15))
                            Capsule().fill(hpColor(opponentHp))
                                .frame(width: max(0, geo.size.width * CGFloat(opponentHp) / 100.0))
                        }
                    }
                    .frame(height: 6)

                    HStack(spacing: 4) {
                        Text("\(opponentHp) HP")
                            .font(.system(size: 10, weight: .heavy, design: .monospaced))
                            .foregroundStyle(hpColor(opponentHp))
                        Text("• \(opponentScore) pts")
                            .font(.system(size: 10, weight: .semibold))
                            .foregroundStyle(Color.orange)
                    }
                }

                ZStack {
                    Circle()
                        .fill(Color.red.opacity(0.3))
                        .frame(width: 34, height: 34)
                    Image(systemName: "bolt.shield.fill")
                        .font(.system(size: 16))
                        .foregroundStyle(Color.red)
                }
            }
            .frame(maxWidth: .infinity)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(hex: "#0A1424").opacity(0.85))
                .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.white.opacity(0.1), lineWidth: 1))
        )
    }

    private func hpColor(_ hp: Int) -> Color {
        if hp > 60 { return Color.green }
        if hp > 30 { return Color.yellow }
        return Color.red
    }

    // MARK: - Hero Powers Bar (Equipped Hero Kit)

    private var powersToolbar: some View {
        let kit = equippedHeroKit
        return HStack(spacing: 8) {
            // Power 1: Intel Clue Scan
            powerButton(
                title: kit.intelPower.powerName,
                icon: "magnifyingglass",
                color: Color.cyan,
                charges: intelCharges,
                cooldown: intelCooldown
            ) {
                activateIntelScan()
            }

            // Power 2: Strike 50-50 Distractor Elimination
            powerButton(
                title: kit.strikePower.powerName,
                icon: "target",
                color: Color.orange,
                charges: strikeCharges,
                cooldown: strikeCooldown
            ) {
                activateStrikeDistractorElimination()
            }

            // Power 3: Defense Barrier Shield
            powerButton(
                title: kit.defensePower.powerName,
                icon: "shield.fill",
                color: Color.blue,
                charges: defenseCharges,
                cooldown: defenseCooldown,
                isActive: shieldRoundsActive > 0
            ) {
                activateShield()
            }

            // Power 4: Surge Multiplier / Adrenaline
            powerButton(
                title: kit.surgePower.powerName,
                icon: "bolt.fill",
                color: Color.yellow,
                charges: surgeCharges,
                cooldown: surgeCooldown,
                isActive: surgeScoreMultiplierActive
            ) {
                activateSurge()
            }
        }
    }

    private func powerButton(
        title: String,
        icon: String,
        color: Color,
        charges: Int,
        cooldown: Int,
        isActive: Bool = false,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            VStack(spacing: 2) {
                ZStack(alignment: .topTrailing) {
                    Image(systemName: icon)
                        .font(.system(size: 14, weight: .bold))
                        .foregroundStyle(charges > 0 && cooldown == 0 ? color : Color.gray.opacity(0.6))
                        .frame(width: 30, height: 30)
                        .background(
                            Circle()
                                .fill(isActive ? color.opacity(0.3) : Color.white.opacity(0.08))
                        )
                        .overlay(Circle().stroke(isActive ? color : Color.clear, lineWidth: 1.5))

                    // Badge counter
                    if charges > 0 {
                        Text("\(charges)")
                            .font(.system(size: 9, weight: .heavy, design: .rounded))
                            .foregroundStyle(Color.black)
                            .frame(width: 14, height: 14)
                            .background(Circle().fill(color))
                            .offset(x: 3, y: -3)
                    }
                }

                Text(cooldown > 0 ? "\(cooldown)r" : title.components(separatedBy: " ").first ?? title)
                    .font(.system(size: 9, weight: .semibold))
                    .foregroundStyle(cooldown > 0 ? Color.gray : Color.white.opacity(0.8))
                    .lineLimit(1)
            }
            .frame(maxWidth: .infinity)
        }
        .disabled(charges <= 0 || cooldown > 0)
    }

    // MARK: - Question Card

    private func questionCard(_ q: Question) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            // Topic badge & TTS Button
            HStack {
                Text(q.topic.isEmpty ? subject : q.topic)
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(Color.cyan)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(Capsule().fill(Color.cyan.opacity(0.15)))

                Spacer()

                // Text To Speech Explanation speaker
                Button {
                    if isSpeaking {
                        stopSpeaking()
                    } else {
                        let readText = q.text + ". Options are: " + q.options.enumerated().map { "Option \($0.offset + 1): \($0.element)" }.joined(separator: ". ")
                        speak(text: readText)
                    }
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: isSpeaking ? "speaker.wave.3.fill" : "speaker.wave.2")
                        Text(isSpeaking ? "Stop" : "Read")
                            .font(.system(size: 11, weight: .semibold))
                    }
                    .foregroundStyle(isSpeaking ? Color.yellow : Color.white.opacity(0.75))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Capsule().fill(Color.white.opacity(0.1)))
                }
            }

            // Question Stem
            Text(q.text)
                .font(.system(size: 15, weight: .medium))
                .foregroundStyle(Color.white)
                .lineSpacing(4)
                .fixedSize(horizontal: false, vertical: true)

            // Optional Question Image
            if let imgUrl = q.imageURL {
                AsyncImage(url: imgUrl) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .scaledToFit()
                            .frame(maxHeight: 200)
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                            .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.white.opacity(0.15), lineWidth: 1))
                    case .failure:
                        EmptyView()
                    case .empty:
                        ProgressView().tint(Color.yellow).padding()
                    @unknown default:
                        EmptyView()
                    }
                }
                .frame(maxWidth: .infinity, alignment: .center)
            }
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: 14)
                .fill(Color(hex: "#0C1424").opacity(0.9))
                .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color.white.opacity(0.12), lineWidth: 1))
        )
    }

    // MARK: - Options Grid (5-Option Support: A, B, C, D, E)

    private func optionsGrid(_ q: Question) -> some View {
        VStack(spacing: 10) {
            ForEach(Array(q.options.enumerated()), id: \.offset) { index, optionText in
                let isEliminated = eliminatedOptionIndices.contains(index)
                let isSelected = selectedOptionIndex == index
                let isCorrect = q.correctIndex == index

                optionRow(
                    index: index,
                    text: optionText,
                    isSelected: isSelected,
                    isEliminated: isEliminated,
                    isCorrect: isCorrect,
                    isRevealed: isAnswerSubmitted
                ) {
                    guard !isAnswerSubmitted && !isEliminated else { return }
                    selectedOptionIndex = index
                    UISelectionFeedbackGenerator().selectionChanged()
                }
            }
        }
    }

    private func optionRow(
        index: Int,
        text: String,
        isSelected: Bool,
        isEliminated: Bool,
        isCorrect: Bool,
        isRevealed: Bool,
        action: @escaping () -> Void
    ) -> some View {
        let optionLetter = ["A", "B", "C", "D", "E"][index % 5]

        var borderColor = Color.white.opacity(0.15)
        var bgColor = Color(hex: "#0A101D").opacity(0.8)
        var letterColor = Color.white.opacity(0.7)

        if isRevealed {
            if isCorrect {
                borderColor = Color.green
                bgColor = Color.green.opacity(0.18)
                letterColor = Color.green
            } else if isSelected && !isCorrect {
                borderColor = Color.red
                bgColor = Color.red.opacity(0.18)
                letterColor = Color.red
            }
        } else if isSelected {
            borderColor = Color.yellow
            bgColor = Color.yellow.opacity(0.14)
            letterColor = Color.yellow
        }

        return Button(action: action) {
            HStack(spacing: 12) {
                // Option Letter Badge [A], [B], [C], [D], [E]
                Text(optionLetter)
                    .font(.system(size: 13, weight: .black, design: .rounded))
                    .foregroundStyle(letterColor)
                    .frame(width: 28, height: 28)
                    .background(Circle().fill(Color.white.opacity(0.08)))
                    .overlay(Circle().stroke(borderColor, lineWidth: 1.5))

                // Option Content
                Text(text)
                    .font(.system(size: 14, weight: .regular))
                    .foregroundStyle(isEliminated ? Color.gray.opacity(0.4) : Color.white)
                    .strikethrough(isEliminated, color: Color.red.opacity(0.6))
                    .multilineTextAlignment(.leading)
                    .fixedSize(horizontal: false, vertical: true)

                Spacer()

                // State Icon
                if isRevealed {
                    if isCorrect {
                        Image(systemName: "checkmark.circle.fill").foregroundStyle(Color.green)
                    } else if isSelected {
                        Image(systemName: "xmark.circle.fill").foregroundStyle(Color.red)
                    }
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
            .background(RoundedRectangle(cornerRadius: 12).fill(bgColor))
            .overlay(RoundedRectangle(cornerRadius: 12).stroke(borderColor, lineWidth: 1.5))
        }
        .disabled(isAnswerSubmitted || isEliminated)
        .opacity(isEliminated ? 0.35 : 1.0)
    }

    // MARK: - Explanation Card

    private func explanationCard(_ q: Question) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: "lightbulb.fill").foregroundStyle(Color.yellow)
                Text("Clinical Rationale & Explanation")
                    .font(.system(size: 13, weight: .bold))
                    .foregroundStyle(Color.yellow)

                Spacer()

                Button {
                    speak(text: q.explanation)
                } label: {
                    Image(systemName: "speaker.wave.2.fill")
                        .font(.system(size: 13))
                        .foregroundStyle(Color.cyan)
                }
            }

            Text(q.explanation.isEmpty ? "Explanation verified according to standard clinical consensus." : q.explanation)
                .font(.system(size: 13, weight: .regular))
                .foregroundStyle(Color.white.opacity(0.9))
                .lineSpacing(3)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(hex: "#08182B").opacity(0.9))
                .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.cyan.opacity(0.3), lineWidth: 1))
        )
    }

    // MARK: - Audio TTS

    private func speak(text: String) {
        stopSpeaking()
        guard !text.isEmpty else { return }

        let utterance = AVSpeechUtterance(string: text)
        utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
        utterance.rate = 0.5
        speechSynthesizer.speak(utterance)
        isSpeaking = true
    }

    private func stopSpeaking() {
        if speechSynthesizer.isSpeaking {
            speechSynthesizer.stopSpeaking(at: .immediate)
        }
        isSpeaking = false
    }

    // MARK: - Bottom Controls Bar (Previous & Submit / Next)

    private var bottomControlsBar: some View {
        HStack(spacing: 12) {
            // Previous Button (btnPrev)
            if currentIndex > 0 {
                Button {
                    stopSpeaking()
                    currentIndex -= 1
                    loadQuestionAtCurrentIndex()
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: "chevron.left")
                        Text("Prev")
                    }
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(Color.white.opacity(0.7))
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                    .background(RoundedRectangle(cornerRadius: 12).fill(Color.white.opacity(0.1)))
                }
            }

            Spacer()

            // Submit / Next Button
            Button {
                if !isAnswerSubmitted {
                    submitAnswer()
                } else {
                    stopSpeaking()
                    advanceToNextQuestion()
                }
            } label: {
                Text(!isAnswerSubmitted ? "Submit Answer" : "Next Question ❯")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(Color.black)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 12)
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .fill(selectedOptionIndex != nil || isAnswerSubmitted ? Color.yellow : Color.gray.opacity(0.5))
                    )
            }
            .disabled(selectedOptionIndex == nil && !isAnswerSubmitted)
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, 10)
        .background(Color(hex: "#060A14"))
    }

    // MARK: - Powers Logic (Equipped Hero Kit)

    private func showCombatFlyout(text: String, color: Color) {
        floatingBannerText = text
        floatingBannerColor = color
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.8) {
            if self.floatingBannerText == text {
                self.floatingBannerText = nil
            }
        }
    }

    private func activateIntelScan() {
        let power = equippedHeroKit.intelPower
        guard intelCharges > 0, intelCooldown == 0, let q = currentQuestion else { return }
        intelCharges -= 1
        intelCooldown = max(1, power.cooldownRounds)

        let highYieldTerms = ["triad", "most common", "pathognomonic", "gold standard", "first line", "sign", "acute", "artery", "nerve", "mutation", "receptor"]
        let found = highYieldTerms.filter { q.text.localizedCaseInsensitiveContains($0) }
        let clue = !found.isEmpty
            ? "🔍 \(power.powerName): Focus on [\(found.joined(separator: ", "))]"
            : "🔍 \(power.powerName): Cross-reference clinical presentation with anatomical plane!"

        intelClueText = clue
        showCombatFlyout(text: clue, color: Color.cyan)
        DispatchQueue.main.asyncAfter(deadline: .now() + 4.0) {
            if self.intelClueText == clue {
                self.intelClueText = nil
            }
        }
        UIImpactFeedbackGenerator(style: .medium).impactOccurred()
    }

    private func activateStrikeDistractorElimination() {
        let power = equippedHeroKit.strikePower
        guard strikeCharges > 0, strikeCooldown == 0, let q = currentQuestion else { return }
        strikeCharges -= 1
        strikeCooldown = max(1, power.cooldownRounds)

        var wrongIndices: [Int] = []
        for i in 0..<q.options.count {
            if i != q.correctIndex && !eliminatedOptionIndices.contains(i) {
                wrongIndices.append(i)
            }
        }
        wrongIndices.shuffle()
        let eliminated = Array(wrongIndices.prefix(2))
        for idx in eliminated {
            eliminatedOptionIndices.insert(idx)
        }
        showCombatFlyout(text: "🎯 \(power.powerName.uppercased())! -\(eliminated.count) DISTRACTORS", color: Color.orange)
        UIImpactFeedbackGenerator(style: .medium).impactOccurred()
    }

    private func activateShield() {
        let power = equippedHeroKit.defensePower
        guard defenseCharges > 0, defenseCooldown == 0, shieldRoundsActive == 0 else { return }
        defenseCharges -= 1
        defenseCooldown = max(1, power.cooldownRounds)
        shieldRoundsActive = 2
        showCombatFlyout(text: "🛡️ \(power.powerName.uppercased())! BARRIER ACTIVE (2 rds)", color: Color.cyan)
        UIImpactFeedbackGenerator(style: .medium).impactOccurred()
    }

    private func activateSurge() {
        let power = equippedHeroKit.surgePower
        guard surgeCharges > 0, surgeCooldown == 0 else { return }
        surgeCharges -= 1
        surgeCooldown = max(1, power.cooldownRounds)
        surgeScoreMultiplierActive = true
        let healAmt = 20
        currentHp = min(100, currentHp + healAmt)
        syncMyHpToFirebase()
        showCombatFlyout(text: "⚡ \(power.powerName.uppercased())! +\(healAmt) HP & 1.5x SURGE! 🔥", color: Color.yellow)
        UIImpactFeedbackGenerator(style: .heavy).impactOccurred()
    }

    // MARK: - Answer Submission & Combat Sync

    private func submitAnswer() {
        guard let chosen = selectedOptionIndex, let q = currentQuestion, !isAnswerSubmitted else { return }
        isAnswerSubmitted = true
        answeredIndices.insert(currentIndex)

        let isCorrect = (chosen == q.correctIndex)
        if isCorrect {
            UIImpactFeedbackGenerator(style: .heavy).impactOccurred()
            currentStreak += 1
            var points = 10
            if surgeScoreMultiplierActive {
                points = Int(Double(points) * 1.5)
                surgeScoreMultiplierActive = false
            }
            myScore += points

            // Deal 15 damage to opponent in multiplayer
            if mode == .multiplayer || isChallenge {
                let damage = 15
                dealDamageToOpponent(amount: damage)
                showCombatFlyout(text: "⚔️ CORRECT! +\(points) PTS | DEALT -\(damage) HP!", color: Color.green)
            }
        } else {
            UIImpactFeedbackGenerator(style: .rigid).impactOccurred()
            currentStreak = 0
            if shieldRoundsActive > 0 {
                shieldRoundsActive -= 1
                showCombatFlyout(text: "🛡️ SHIELD ABSORBED RECOIL DAMAGE!", color: Color.cyan)
            } else {
                currentHp = max(0, currentHp - 10)
                syncMyHpToFirebase()
                showCombatFlyout(text: "❌ INCORRECT! -10 HP RECOIL", color: Color.red)
            }
        }

        // Decrement cooldowns
        if intelCooldown > 0 { intelCooldown -= 1 }
        if strikeCooldown > 0 { strikeCooldown -= 1 }
        if defenseCooldown > 0 { defenseCooldown -= 1 }
        if surgeCooldown > 0 { surgeCooldown -= 1 }

        // Record review
        let chosenLetter = ["A", "B", "C", "D", "E"][chosen % 5]
        let correctLetter = ["A", "B", "C", "D", "E"][q.correctIndex % 5]
        let review = QuestionReviewItem(
            question: q.text,
            userAnswer: "(\(chosenLetter)) \(q.options[chosen])",
            correctAnswer: "(\(correctLetter)) \(q.options[q.correctIndex])",
            isCorrect: isCorrect,
            explanation: q.explanation
        )
        reviewItems.append(review)
        showExplanation = true
    }

    private func advanceToNextQuestion() {
        showExplanation = false
        selectedOptionIndex = nil
        isAnswerSubmitted = false
        eliminatedOptionIndices.removeAll()

        if currentIndex + 1 < allQuestionIds.count {
            currentIndex += 1
            loadQuestionAtCurrentIndex()
        } else {
            finalizeTest()
        }
    }

    private func loadQuestionAtCurrentIndex() {
        guard allQuestionIds.indices.contains(currentIndex) else { return }
        let qId = allQuestionIds[currentIndex]
        Task {
            await loadQuestion(id: qId)
        }
    }

    // MARK: - 15 Questions Database Fetching & Shared Order

    private func initializeTestSession() {
        // Resolve operating mode
        if let list = questionIdList, !list.isEmpty {
            mode = .fixedTest
            allQuestionIds = Array(list.prefix(15))
            remainingTimerSeconds = 15 * 60
        } else if isChallenge && !challengeId.isEmpty {
            mode = .multiplayer
            remainingTimerSeconds = 15 * 60
        } else {
            mode = .singlePlayer
            remainingTimerSeconds = 15 * 60
        }

        // Initialize 4 Hero Powers from equipped Guardian kit
        let kit = equippedHeroKit
        intelCharges = kit.intelPower.chargesPerQuiz
        strikeCharges = kit.strikePower.chargesPerQuiz
        defenseCharges = kit.defensePower.chargesPerQuiz
        surgeCharges = kit.surgePower.chargesPerQuiz

        intelCooldown = 0
        strikeCooldown = 0
        defenseCooldown = 0
        surgeCooldown = 0
        shieldRoundsActive = 0
        surgeScoreMultiplierActive = false

        opponentNameResolved = opponentName.isEmpty ? "Opponent" : opponentName

        // Start Firebase RTDB sync for multiplayer mode
        if mode == .multiplayer || isChallenge {
            setupMultiplayerFirebase()
        }

        Task {
            await fetchOrCreateSharedQuestionList()
        }
    }

    @MainActor
    private func fetchOrCreateSharedQuestionList() async {
        isLoadingQuestions = true
        defer { isLoadingQuestions = false }

        // If list already provided via extras, use top 15
        if let list = questionIdList, !list.isEmpty {
            let battle15 = Array(list.prefix(15))
            self.allQuestionIds = battle15
            self.currentIndex = 0
            if let first = battle15.first {
                await loadQuestion(id: first)
            }
            return
        }

        // In multiplayer mode, synchronize question_ids via Firebase RTDB with auth
        if isChallenge && !challengeId.isEmpty {
            // 1. Check if host has already generated question_ids
            if let list = try? await FirebaseRTDB.shared.get(path: "challenges/\(challengeId)/question_ids") as? [Int],
               !list.isEmpty {
                let battle15 = Array(list.prefix(15))
                self.allQuestionIds = battle15
                self.currentIndex = 0
                if let first = battle15.first {
                    await loadQuestion(id: first)
                }
                return
            }

            // 2. If no questions exist and user isHost: fetch 15 from backend and save
            if isHost {
                let pool = await fetchQuestionIdsFromBackend()
                let battle15 = Array(pool.shuffled().prefix(15))

                try? await FirebaseRTDB.shared.put(path: "challenges/\(challengeId)/question_ids", payload: battle15)

                self.allQuestionIds = battle15
                self.currentIndex = 0
                if let first = battle15.first {
                    await loadQuestion(id: first)
                }
                return
            } else {
                // Client waiting for host to generate questions: poll for up to 10 seconds
                for _ in 0..<10 {
                    try? await Task.sleep(nanoseconds: 1_000_000_000)
                    if let list = try? await FirebaseRTDB.shared.get(path: "challenges/\(challengeId)/question_ids") as? [Int],
                       !list.isEmpty {
                        let battle15 = Array(list.prefix(15))
                        self.allQuestionIds = battle15
                        self.currentIndex = 0
                        if let first = battle15.first {
                            await loadQuestion(id: first)
                        }
                        return
                    }
                }
            }
        }

        // Single Player / Fallback: Fetch directly from backend
        await fetchQuestionListSinglePlayer()
    }

    private func fetchQuestionIdsFromBackend() async -> [Int] {
        let cleanSub = subject.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "NEET_PG"
        var urlStr = "\(apiBaseUrl)api/getQuestions.php?subject=\(cleanSub)&user_id=\(session.userId)"
        if let top = topic, !top.isEmpty {
            let cleanTopic = top.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""
            urlStr += "&topic=\(cleanTopic)"
        }
        guard let url = URL(string: urlStr),
              let (data, _) = try? await URLSession.shared.data(from: url),
              let json = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
              let arr = json["all_question_ids"] as? [Int], !arr.isEmpty else {
            return Array(201...215)
        }
        return arr
    }

    @MainActor
    private func fetchQuestionListSinglePlayer() async {
        let pool = await fetchQuestionIdsFromBackend()
        let battle15 = Array(pool.shuffled().prefix(15))
        self.allQuestionIds = battle15
        self.currentIndex = 0
        if let first = battle15.first {
            await loadQuestion(id: first)
        } else {
            fallbackDefaultDeck(qId: 201)
        }
    }

    // MARK: - Single Question Loader (`api/get_single_question.php`)

    @MainActor
    private func loadQuestion(id: Int) async {
        if let cached = questionCache[id] {
            self.currentQuestion = cached
            return
        }

        do {
            let q = try await api.study.question(id: id)
            self.questionCache[id] = q
            self.currentQuestion = q
        } catch {
            // Fallback via general question fetcher or static clinical deck
            if let fetched = try? await api.study.fetchQuestions(subject: subject, topic: topic, userId: session.userId, questionId: id).question {
                self.questionCache[id] = fetched
                self.currentQuestion = fetched
            } else {
                fallbackDefaultDeck(qId: id)
            }
        }
    }

    private func fallbackDefaultDeck(qId: Int) {
        let sampleQuestions = [
            Question(
                id: qId,
                text: "A 55-year-old chronic smoker presents with painless gross hematuria. Urine cytology reveals malignant transitional cells. Which of the following is the most significant risk factor?",
                options: [
                    "Aromatic Amines & Tobacco Smoking",
                    "Schistosoma haematobium infection",
                    "Chronic indwelling Foley catheter",
                    "Phenacetin overuse",
                    "Cyclophosphamide therapy"
                ],
                correctIndex: 0,
                explanation: "Cigarette smoking is responsible for ~50% of urothelial bladder carcinomas. Exposure to industrial aromatic amines is also a well-established occupational cause."
            ),
            Question(
                id: qId + 1,
                text: "Which of the following ECG changes is the earliest indicator of hyperkalemia?",
                options: [
                    "Prolonged PR interval",
                    "Tall peaked symmetrical T waves",
                    "Sine wave pattern",
                    "Loss of P wave",
                    "ST segment elevation"
                ],
                correctIndex: 1,
                explanation: "Tall, peaked, symmetrical T waves with a narrow base (best seen in leads II, III, V2-V4) are the earliest manifestation of hyperkalemia (K > 5.5 mEq/L)."
            )
        ]
        self.currentQuestion = sampleQuestions.first
    }

    // MARK: - Multiplayer Firebase RTDB Engine

    private func setupMultiplayerFirebase() {
        guard isChallenge && !challengeId.isEmpty else { return }

        let myUid = "\(session.userId)_ios"
        let myName = session.userName

        // 1. Register player in challenge room
        let regData: [String: Any] = [
            "name": myName,
            "hp": 100,
            "score": 0,
            "isFinished": false
        ]
        Task {
            try? await FirebaseRTDB.shared.patch(path: "challenges/\(challengeId)/players/\(myUid)", payload: regData)
        }

        // 2. Start polling for opponent updates and combat actions
        multiplayerPollingTask?.cancel()
        multiplayerPollingTask = Task {
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 1_200_000_000)
                guard !Task.isCancelled else { break }

                // A. Poll Players
                if let pDict = try? await FirebaseRTDB.shared.get(path: "challenges/\(challengeId)/players") as? [String: [String: Any]] {
                    for (pId, info) in pDict {
                        if pId != myUid && pId != String(session.userId) {
                            let oHp = info["hp"] as? Int ?? 100
                            let oScore = info["score"] as? Int ?? 0
                            let oName = info["name"] as? String ?? opponentName
                            let oFin = info["isFinished"] as? Bool ?? false

                            await MainActor.run {
                                self.opponentHp = oHp
                                self.opponentScore = oScore
                                self.opponentNameResolved = oName
                                self.opponentFinished = oFin

                                if oHp <= 0 && !self.isGameOverHandled {
                                    self.isGameOverHandled = true
                                    self.showCombatFlyout(text: "🏆 OPPONENT K.O.! VICTORY!", color: .green)
                                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                                        self.finalizeTest()
                                    }
                                }
                            }
                        }
                    }
                }

                // B. Poll Combat Actions
                if let action = try? await FirebaseRTDB.shared.get(path: "challenges/\(challengeId)/last_action") as? [String: Any],
                   let actionId = action["action_id"] as? String,
                   actionId != lastHandledActionId {

                    lastHandledActionId = actionId
                    let actorId = action["actor_id"] as? String ?? ""
                    let targetId = action["target_id"] as? String ?? ""
                    let amount = action["amount"] as? Int ?? 0
                    let actorName = action["actor_name"] as? String ?? "Opponent"

                    if actorId != myUid && actorId != String(session.userId) && (targetId == myUid || targetId == String(session.userId) || targetId.isEmpty) {
                        await MainActor.run {
                            if shieldRoundsActive > 0 {
                                shieldRoundsActive -= 1
                                self.showCombatFlyout(text: "🛡️ BARRIER BLOCKED \(actorName)'s ATTACK!", color: .cyan)
                            } else {
                                self.currentHp = max(0, self.currentHp - amount)
                                self.showCombatFlyout(text: "💥 \(actorName) dealt -\(amount) HP!", color: .red)
                                UIImpactFeedbackGenerator(style: .heavy).impactOccurred()

                                if self.currentHp <= 0 && !self.isGameOverHandled {
                                    self.isGameOverHandled = true
                                    self.showCombatFlyout(text: "💀 DEFEAT! HP DEPLETED", color: .red)
                                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                                        self.finalizeTest()
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // 3. Fallback Bot simulation when opponent is a bot
        if isBotMatch || opponentId.hasPrefix("BOT") {
            startBotSimulation()
        }
    }

    private func dealDamageToOpponent(amount: Int) {
        guard isChallenge && !challengeId.isEmpty else { return }

        let myUid = "\(session.userId)_ios"
        let myName = session.userName

        // Deduct opponent HP locally & sync to Firebase
        opponentHp = max(0, opponentHp - amount)
        let oppTargetId = opponentId.isEmpty ? "opponent" : opponentId

        Task.detached {
            try? await FirebaseRTDB.shared.put(path: "challenges/\(challengeId)/players/\(oppTargetId)/hp", payload: max(0, opponentHp))

            // Post action
            let actData: [String: Any] = [
                "action_id": UUID().uuidString,
                "type": "DAMAGE",
                "actor_id": myUid,
                "target_id": oppTargetId,
                "amount": amount,
                "actor_name": myName
            ]
            try? await FirebaseRTDB.shared.put(path: "challenges/\(challengeId)/last_action", payload: actData)

            // Update my score in Firebase
            try? await FirebaseRTDB.shared.put(path: "challenges/\(challengeId)/players/\(myUid)/score", payload: myScore)
        }
    }

    private func syncMyHpToFirebase() {
        guard isChallenge && !challengeId.isEmpty else { return }
        let myUid = "\(session.userId)_ios"
        Task.detached {
            try? await FirebaseRTDB.shared.put(path: "challenges/\(challengeId)/players/\(myUid)/hp", payload: max(0, currentHp))
        }
    }

    private func startBotSimulation() {
        botSimulationTask?.cancel()
        botSimulationTask = Task {
            while !Task.isCancelled {
                // Bot answers every 6 to 9 seconds
                let delaySeconds = Double.random(in: 6.0...9.0)
                try? await Task.sleep(nanoseconds: UInt64(delaySeconds * 1_000_000_000))
                guard !Task.isCancelled else { break }

                // 70% bot accuracy
                let isBotCorrect = Double.random(in: 0...1) < 0.70

                await MainActor.run {
                    if isBotCorrect {
                        let botDamage = 12
                        self.opponentScore += 10
                        if self.shieldRoundsActive > 0 {
                            self.shieldRoundsActive -= 1
                            self.showCombatFlyout(text: "🛡️ SHIELD BLOCKED BOT STRIKE!", color: .cyan)
                        } else {
                            self.currentHp = max(0, self.currentHp - botDamage)
                            self.showCombatFlyout(text: "💥 \(self.opponentNameResolved) answered correctly! -\(botDamage) HP", color: .red)
                            if self.currentHp <= 0 && !self.isGameOverHandled {
                                self.isGameOverHandled = true
                                self.showCombatFlyout(text: "💀 DEFEAT! HP DEPLETED", color: .red)
                                DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                                    self.finalizeTest()
                                }
                            }
                        }
                    } else {
                        self.opponentHp = max(0, self.opponentHp - 8)
                        self.showCombatFlyout(text: "⚡ \(self.opponentNameResolved) missed! Recoil damage", color: .orange)
                        if self.opponentHp <= 0 && !self.isGameOverHandled {
                            self.isGameOverHandled = true
                            self.showCombatFlyout(text: "🏆 OPPONENT K.O.! VICTORY!", color: .green)
                            DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                                self.finalizeTest()
                            }
                        }
                    }
                }
            }
        }
    }

    private func cleanupMultiplayer() {
        multiplayerPollingTask?.cancel()
        multiplayerPollingTask = nil
        botSimulationTask?.cancel()
        botSimulationTask = nil
    }

    private func handleTimerTick() {
        if remainingTimerSeconds > 0 {
            remainingTimerSeconds -= 1
            if remainingTimerSeconds == 0 {
                finalizeTest()
            }
        }
    }

    private func finalizeTest() {
        stopSpeaking()
        cleanupMultiplayer()

        // Mark finished in Firebase
        let myUid = "\(session.userId)_ios"
        if isChallenge && !challengeId.isEmpty {
            Task {
                try? await FirebaseRTDB.shared.put(path: "challenges/\(challengeId)/players/\(myUid)/isFinished", payload: true)
            }
        }

        let correctCount = reviewItems.filter { $0.isCorrect }.count
        let playerWon = currentHp > 0 && (opponentHp <= 0 || myScore >= opponentScore)

        let summary = BattleResultSummary(
            challengeId: challengeId.isEmpty ? "test_\(UUID().uuidString.prefix(6))" : challengeId,
            userName: session.currentUser?.name ?? "Doctor",
            opponentName: opponentNameResolved,
            userScore: myScore,
            opponentScore: opponentScore,
            userCorrect: correctCount,
            opponentCorrect: max(0, (allQuestionIds.count - correctCount) / 2 + (playerWon ? 0 : 2)),
            totalQuestions: max(1, allQuestionIds.count),
            expGained: correctCount * 25 + (playerWon ? 100 : 25),
            creditsGained: playerWon ? 50 : 15,
            questionReviews: reviewItems
        )
        self.resultSummaryData = summary
        self.showResultSummary = true
        onFinish?(summary)
    }
}
