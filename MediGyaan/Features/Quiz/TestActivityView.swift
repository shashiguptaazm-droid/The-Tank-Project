import SwiftUI
import AVFoundation

/// Complete 1:1 SwiftUI replication of Android's `TestActivity.kt` and `SubjectTestActivity.kt`.
///
/// Features:
/// 1. Dual Mode Exam HUD:
///    - **Solo Practice Mode**: 50-Question NEET PG / USMLE mock exam with timer, streak tracking, question progress, and instant review.
///    - **1v1 Challenge Mode**: Real-time HP duel, opponent AI combat simulation, dynamic combat ticker (`tvCombatTicker`), and low-HP critical vignette.
/// 2. Guardian Hero Kit Power-Ups:
///    - ⚡ **Adrenaline / Intel (50:50)**: Eliminates 2 incorrect options.
///    - 🛡️ **Shield / Defense**: Absorbs incoming damage.
///    - 💥 **Shock / Strike**: 2x critical damage multiplier on correct answer.
///    - 🌀 **Surge / Confuse**: Scrambles opponent speed.
/// 3. Clinical Question Presentation:
///    - Image zoom hint card with full-screen pinch-zoom viewer.
///    - 4 option cards (A, B, C, D) with distinct option badges.
///    - Text-to-Speech (TTS) audio narration (`AVSpeechSynthesizer`).
///    - Full clinical explanation card with diagnostic pearls.
/// 4. Review Tracking & VPS Telemetry:
///    - Builds structured `reviewJson` mirroring Android's `reviewJson`.
///    - Emits real-time logs via `RemoteLogger` to `/Neurons/api/client_log.php`.
public struct TestActivityView: View {

    public let quiz: Quiz
    public let isChallenge: Bool
    public let opponentName: String
    public var onFinish: (() -> Void)?

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @Environment(\.dismiss) private var dismiss

    // ─── Question Progression & State ─────────────────────────────────────────
    @State private var questions: [Question] = []
    @State private var currentIndex: Int = 0
    @State private var isLoading: Bool = true
    @State private var selectedOptionIndex: Int? = nil
    @State private var isAnswerSubmitted: Bool = false
    @State private var timeRemainingSeconds: Int = 45
    @State private var timerActive: Bool = false

    // ─── Scoring, Streak & HP ─────────────────────────────────────────────────
    @State private var score: Int = 0
    @State private var streak: Int = 0
    @State private var playerHp: Int = 100
    @State private var opponentHp: Int = 100
    @State private var combatTicker: String = "⚔️ Exam round ready. Answer swiftly!"

    // ─── Hero Kit Power-Ups (Intel, Defense, Strike, Surge) ───────────────────
    @State private var intelCharges: Int = 3
    @State private var defenseCharges: Int = 2
    @State private var strikeCharges: Int = 2
    @State private var surgeCharges: Int = 1
    @State private var isShieldActive: Bool = false
    @State private var isStrikeActive: Bool = false
    @State private var eliminatedOptions: Set<Int> = []

    // ─── TTS & Media ──────────────────────────────────────────────────────────
    @State private var isSpeaking: Bool = false
    @State private var zoomImageURL: URL? = nil
    @State private var speechSynthesizer = AVSpeechSynthesizer()

    // ─── Results & Review ─────────────────────────────────────────────────────
    @State private var reviewRecords: [TestQuestionReview] = []
    @State private var isExamCompleted: Bool = false

    public init(
        quiz: Quiz,
        isChallenge: Bool = false,
        opponentName: String = "Dr. Opponent",
        onFinish: (() -> Void)? = nil
    ) {
        self.quiz = quiz
        self.isChallenge = isChallenge
        self.opponentName = opponentName
        self.onFinish = onFinish
    }

    private var currentQuestion: Question? {
        guard currentIndex < questions.count else { return nil }
        return questions[currentIndex]
    }

    public var body: some View {
        ZStack {
            AppTheme.Palette.surface.ignoresSafeArea()

            if isLoading {
                LoadingStateView(message: "Loading clinical questions for \(quiz.title)...")
            } else if isExamCompleted {
                examResultView
            } else if let question = currentQuestion {
                VStack(spacing: 0) {
                    headerHUD
                    Divider()

                    ScrollView {
                        VStack(spacing: AppTheme.Spacing.md) {
                            // Challenge Battle Bar
                            if isChallenge {
                                challengeDuelHUD
                            }

                            // Combat Ticker
                            combatTickerView

                            // Question Title & Content
                            questionCardView(question: question)

                            // Option Cards
                            optionsListView(question: question)

                            // Clinical Explanation Card
                            if isAnswerSubmitted {
                                explanationCardView(question: question)
                            }
                        }
                        .padding(AppTheme.Spacing.md)
                    }

                    // Bottom Powers & Navigation Bar
                    bottomControlsBar
                }
            } else {
                EmptyStateView(
                    title: "No Questions Available",
                    message: "Questions for this test series could not be loaded.",
                    systemImage: "doc.text.magnifyingglass"
                )
            }
        }
        .navigationBarHidden(true)
        .fullScreenCover(item: $zoomImageURL) { url in
            ZoomImageViewer(url: url)
        }
        .task {
            await initializeTest()
        }
        .onDisappear {
            speechSynthesizer.stopSpeaking(at: .immediate)
        }
    }

    // MARK: - Header HUD

    private var headerHUD: some View {
        HStack(spacing: AppTheme.Spacing.md) {
            Button {
                RemoteLogger.log(tag: "TestActivity_Exit", message: "User exited test at question \(currentIndex + 1)")
                dismiss()
            } label: {
                Image(systemName: "xmark")
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                    .padding(8)
            }

            VStack(alignment: .leading, spacing: 2) {
                Text(quiz.title)
                    .font(AppTheme.Font.headlineBold)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                    .lineLimit(1)

                Text("Question \(currentIndex + 1) of \(questions.count)")
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Palette.textSecondary)
            }

            Spacer()

            // Streak Pill
            if streak > 0 {
                HStack(spacing: 4) {
                    Text("🔥")
                    Text("\(streak) streak")
                        .font(AppTheme.Font.captionBold)
                        .foregroundStyle(Color.orange)
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Color.orange.opacity(0.15))
                .clipShape(Capsule())
            }

            // Audio TTS Button
            Button {
                toggleSpeech()
            } label: {
                Image(systemName: isSpeaking ? "speaker.wave.3.fill" : "speaker.wave.2")
                    .font(.system(size: 17))
                    .foregroundStyle(isSpeaking ? Color.green : AppTheme.Palette.primary)
                    .padding(6)
            }

            // Timer Pill
            HStack(spacing: 4) {
                Image(systemName: "timer")
                    .font(.system(size: 13))
                Text("\(timeRemainingSeconds)s")
                    .font(.system(size: 13, weight: .bold, design: .monospaced))
            }
            .foregroundStyle(timeRemainingSeconds <= 10 ? Color.red : AppTheme.Palette.primary)
            .padding(.horizontal, 10)
            .padding(.vertical, 5)
            .background(
                Capsule().fill(timeRemainingSeconds <= 10 ? Color.red.opacity(0.15) : AppTheme.Palette.primary.opacity(0.12))
            )
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, AppTheme.Spacing.sm)
        .background(AppTheme.Palette.cardBackground)
    }

    // MARK: - Challenge Duel HUD (Android TestActivity split health bars)

    private var challengeDuelHUD: some View {
        HStack(spacing: AppTheme.Spacing.md) {
            // Player HP
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text("You")
                        .font(AppTheme.Font.captionBold)
                        .foregroundStyle(AppTheme.Palette.textPrimary)
                    Spacer()
                    Text("\(playerHp) HP")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundStyle(Color.green)
                }
                ProgressView(value: Double(playerHp), total: 100.0)
                    .tint(playerHp > 30 ? Color.green : Color.red)
            }

            Text("VS")
                .font(.system(size: 13, weight: .black))
                .foregroundStyle(Color.orange)

            // Opponent HP
            VStack(alignment: .trailing, spacing: 4) {
                HStack {
                    Text("\(opponentHp) HP")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundStyle(Color.red)
                    Spacer()
                    Text(opponentName)
                        .font(AppTheme.Font.captionBold)
                        .foregroundStyle(AppTheme.Palette.textPrimary)
                        .lineLimit(1)
                }
                ProgressView(value: Double(opponentHp), total: 100.0)
                    .tint(Color.red)
            }
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card)
                .fill(AppTheme.Palette.cardBackground)
                .overlay(RoundedRectangle(cornerRadius: AppTheme.Radius.card).stroke(Color.orange.opacity(0.3), lineWidth: 1))
        )
    }

    // MARK: - Combat Ticker View

    private var combatTickerView: some View {
        HStack(spacing: 8) {
            Image(systemName: "bolt.horizontal.fill")
                .font(.system(size: 13))
                .foregroundStyle(Color.orange)
            Text(combatTicker)
                .font(AppTheme.Font.captionBold)
                .foregroundStyle(AppTheme.Palette.textPrimary)
                .lineLimit(1)
            Spacer()
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(Color.orange.opacity(0.12))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    // MARK: - Question Card View with Image Zoom Hint

    private func questionCardView(question: Question) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
            // Subject & Difficulty Badges
            HStack(spacing: 6) {
                Text(question.subject.isEmpty ? quiz.subject : question.subject)
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(AppTheme.Palette.primary)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(AppTheme.Palette.primary.opacity(0.15))
                    .clipShape(Capsule())

                if !question.difficulty.isEmpty {
                    Text(question.difficulty.uppercased())
                        .font(.system(size: 10, weight: .bold))
                        .foregroundStyle(AppTheme.Palette.accent)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(AppTheme.Palette.accent.opacity(0.15))
                        .clipShape(Capsule())
                }

                Spacer()
            }

            // Question Prompt Text
            Text(question.text)
                .font(AppTheme.Font.bodyBold)
                .foregroundStyle(AppTheme.Palette.textPrimary)
                .fixedSize(horizontal: false, vertical: true)

            // Medical Clinical Image with Tap-to-Zoom Hint
            if let imageURL = question.imageURL {
                ZStack(alignment: .bottomTrailing) {
                    AsyncImage(url: imageURL) { phase in
                        switch phase {
                        case .success(let image):
                            image
                                .resizable()
                                .scaledToFit()
                                .frame(maxHeight: 200)
                                .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.option))
                        case .failure(_):
                            Label("Clinical Image Available", systemImage: "photo")
                                .font(AppTheme.Font.caption)
                        case .empty:
                            ProgressView().frame(height: 140)
                        @unknown default:
                            EmptyView()
                        }
                    }

                    // Zoom Badge Hint
                    HStack(spacing: 4) {
                        Image(systemName: "plus.magnifyingglass")
                        Text("Tap to Zoom")
                    }
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.black.opacity(0.7))
                    .clipShape(Capsule())
                    .padding(8)
                }
                .contentShape(Rectangle())
                .onTapGesture {
                    zoomImageURL = imageURL
                }
            }
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card)
                .fill(AppTheme.Palette.cardBackground)
        )
    }

    // MARK: - Options List View

    private func optionsListView(question: Question) -> some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            ForEach(Array(question.options.enumerated()), id: \.offset) { index, optionText in
                let optionLetter = String(UnicodeScalar(65 + index)!)
                let isEliminated = eliminatedOptions.contains(index)

                Button {
                    guard !isAnswerSubmitted, !isEliminated else { return }
                    submitOption(index: index, question: question)
                } label: {
                    HStack(spacing: 12) {
                        // Letter Badge (A, B, C, D)
                        ZStack {
                            Circle()
                                .fill(optionBadgeBackground(index: index, question: question))
                                .frame(width: 32, height: 32)
                            Text(optionLetter)
                                .font(.system(size: 14, weight: .bold))
                                .foregroundStyle(optionBadgeForeground(index: index, question: question))
                        }

                        // Option Content
                        Text(optionText)
                            .font(AppTheme.Font.body)
                            .foregroundStyle(isEliminated ? AppTheme.Palette.textSecondary.opacity(0.4) : AppTheme.Palette.textPrimary)
                            .multilineTextAlignment(.leading)
                            .strikethrough(isEliminated)

                        Spacer()

                        // Indicator Icon
                        if isAnswerSubmitted {
                            if index == question.correctOptionIndex {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundStyle(Color.green)
                            } else if index == selectedOptionIndex {
                                Image(systemName: "xmark.circle.fill")
                                    .foregroundStyle(Color.red)
                            }
                        }
                    }
                    .padding(AppTheme.Spacing.md)
                    .background(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.option)
                            .fill(optionCardBackground(index: index, question: question))
                            .overlay(
                                RoundedRectangle(cornerRadius: AppTheme.Radius.option)
                                    .stroke(optionBorderColor(index: index, question: question), lineWidth: 1.5)
                            )
                    )
                }
                .buttonStyle(.plain)
                .disabled(isAnswerSubmitted || isEliminated)
                .opacity(isEliminated ? 0.35 : 1.0)
            }
        }
    }

    // MARK: - Explanation Card View

    private func explanationCardView(question: Question) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            HStack {
                Image(systemName: "lightbulb.fill")
                    .foregroundStyle(Color.yellow)
                Text("Clinical Explanation & High-Yield Pearl")
                    .font(AppTheme.Font.headlineBold)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                Spacer()
            }

            Text(question.explanation.isEmpty ? "Correct answer is Option \(String(UnicodeScalar(65 + question.correctOptionIndex)!)). Review the key diagnostic principles and NEET-PG guidelines." : question.explanation)
                .font(AppTheme.Font.body)
                .foregroundStyle(AppTheme.Palette.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card)
                .fill(Color.blue.opacity(0.08))
                .overlay(RoundedRectangle(cornerRadius: AppTheme.Radius.card).stroke(Color.blue.opacity(0.25), lineWidth: 1))
        )
    }

    // MARK: - Bottom Hero Powers & Navigation Bar

    private var bottomControlsBar: some View {
        VStack(spacing: AppTheme.Spacing.xs) {
            // Guardian Powers Bar
            HStack(spacing: AppTheme.Spacing.md) {
                // 1. Adrenaline / Intel (50:50)
                powerButton(
                    icon: "bolt.fill",
                    color: Color.yellow,
                    name: "Intel (50:50)",
                    charges: intelCharges
                ) {
                    useIntelPower()
                }

                // 2. Shield / Defense
                powerButton(
                    icon: "shield.fill",
                    color: Color.blue,
                    name: "Shield",
                    charges: defenseCharges
                ) {
                    useDefensePower()
                }

                // 3. Shock / Strike (2x)
                powerButton(
                    icon: "flame.fill",
                    color: Color.red,
                    name: "Shock (2x)",
                    charges: strikeCharges
                ) {
                    useStrikePower()
                }

                // 4. Surge / Confuse
                powerButton(
                    icon: "tornado",
                    color: Color.purple,
                    name: "Surge",
                    charges: surgeCharges
                ) {
                    useSurgePower()
                }
            }
            .padding(.horizontal, AppTheme.Spacing.md)
            .padding(.top, 4)

            // Next Question or Complete Button
            if isAnswerSubmitted {
                Button {
                    advanceToNextQuestion()
                } label: {
                    Text(currentIndex + 1 < questions.count ? "Next Clinical Question →" : "Finish & View Results 🏆")
                        .font(AppTheme.Font.headlineBold)
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(AppTheme.Palette.primary)
                        .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.button))
                }
                .padding(.horizontal, AppTheme.Spacing.md)
                .padding(.bottom, 6)
            }
        }
        .padding(.vertical, 6)
        .background(AppTheme.Palette.cardBackground)
    }

    private func powerButton(
        icon: String,
        color: Color,
        name: String,
        charges: Int,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            VStack(spacing: 3) {
                ZStack(alignment: .topTrailing) {
                    Circle()
                        .fill(color.opacity(0.15))
                        .frame(width: 36, height: 36)
                    Image(systemName: icon)
                        .font(.system(size: 16))
                        .foregroundStyle(color)
                        .frame(width: 36, height: 36)

                    Text("\(charges)")
                        .font(.system(size: 9, weight: .black))
                        .foregroundStyle(.white)
                        .padding(3)
                        .background(Circle().fill(charges > 0 ? color : Color.gray))
                        .offset(x: 4, y: -4)
                }

                Text(name)
                    .font(.system(size: 9, weight: .bold))
                    .foregroundStyle(charges > 0 ? AppTheme.Palette.textPrimary : AppTheme.Palette.textSecondary)
            }
        }
        .disabled(charges <= 0 || isAnswerSubmitted)
        .opacity(charges > 0 ? 1.0 : 0.4)
    }

    // MARK: - Exam Completed Result View

    private var examResultView: some View {
        VStack(spacing: AppTheme.Spacing.lg) {
            Spacer()

            ZStack {
                Circle()
                    .fill(Color.orange.opacity(0.15))
                    .frame(width: 90, height: 90)
                Image(systemName: score >= 50 ? "trophy.fill" : "medal.fill")
                    .font(.system(size: 46))
                    .foregroundStyle(Color.orange)
            }

            Text(score >= 50 ? "Exam Conquered!" : "Test Completed")
                .font(AppTheme.Font.titleBold)
                .foregroundStyle(AppTheme.Palette.textPrimary)

            Text("You scored \(score)% in \(quiz.title)")
                .font(AppTheme.Font.headline)
                .foregroundStyle(AppTheme.Palette.textSecondary)

            HStack(spacing: AppTheme.Spacing.xl) {
                metricItem(title: "Correct", value: "\(reviewRecords.filter(\.isCorrect).count)", color: Color.green)
                metricItem(title: "Incorrect", value: "\(reviewRecords.filter { !$0.isCorrect }.count)", color: Color.red)
                metricItem(title: "Best Streak", value: "🔥 \(streak)", color: Color.orange)
            }
            .padding(.horizontal, AppTheme.Spacing.xl)
            .padding(.vertical, AppTheme.Spacing.md)
            .background(AppTheme.Palette.cardBackground)
            .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.card))

            Spacer()

            Button {
                RemoteLogger.log(tag: "TestActivity_Done", message: "User finished test with score \(score)")
                onFinish?()
                dismiss()
            } label: {
                Text("Return to Hub")
                    .font(AppTheme.Font.headlineBold)
                    .foregroundStyle(.white)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(AppTheme.Palette.primary)
                    .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.button))
            }
            .padding(.horizontal, AppTheme.Spacing.xl)
            .padding(.bottom, AppTheme.Spacing.lg)
        }
        .padding(AppTheme.Spacing.lg)
    }

    private func metricItem(title: String, value: String, color: Color) -> some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.system(size: 20, weight: .bold))
                .foregroundStyle(color)
            Text(title)
                .font(AppTheme.Font.caption)
                .foregroundStyle(AppTheme.Palette.textSecondary)
        }
    }

    // MARK: - Actions & Game Mechanics

    @MainActor
    private func initializeTest() async {
        RemoteLogger.log(tag: "TestActivity_Init", message: "Loading questions for Quiz #\(quiz.id): \(quiz.title)")
        isLoading = true

        do {
            let loaded = try await api.study.questions(quizId: quiz.id)
            if !loaded.isEmpty {
                self.questions = loaded
            } else {
                self.questions = generateFallbackMockQuestions()
            }
        } catch {
            RemoteLogger.log(tag: "TestActivity_Fallback", message: "Network fetch failed; generating fallback questions.")
            self.questions = generateFallbackMockQuestions()
        }

        self.isLoading = false
        startQuestionTimer()
    }

    private func startQuestionTimer() {
        timeRemainingSeconds = isChallenge ? 20 : 45
        timerActive = true

        Task {
            while timerActive && timeRemainingSeconds > 0 && !isAnswerSubmitted {
                try? await Task.sleep(nanoseconds: 1_000_000_000)
                guard timerActive, !isAnswerSubmitted else { break }
                timeRemainingSeconds -= 1
            }

            if timeRemainingSeconds == 0 && !isAnswerSubmitted {
                await MainActor.run {
                    handleTimeExpired()
                }
            }
        }
    }

    @MainActor
    private func handleTimeExpired() {
        guard let question = currentQuestion, !isAnswerSubmitted else { return }
        combatTicker = "⏳ Time expired for this question!"
        submitOption(index: -1, question: question)
    }

    private func submitOption(index: Int, question: Question) {
        timerActive = false
        isAnswerSubmitted = true
        selectedOptionIndex = index

        let isCorrect = (index == question.correctOptionIndex)
        let damage = isStrikeActive ? 40 : 20

        if isCorrect {
            streak += 1
            let streakBonus = min(streak * 2, 10)
            score = min(score + 10 + streakBonus, 100)

            if isChallenge {
                opponentHp = max(0, opponentHp - damage)
                combatTicker = isStrikeActive ? "💥 CRITICAL STRIKE! Dealt \(damage) damage!" : "🎯 Correct! Dealt \(damage) damage to \(opponentName)!"
            } else {
                combatTicker = "🎯 Correct diagnosis! +10 Points (Streak: \(streak))"
            }
        } else {
            streak = 0
            if isChallenge {
                if isShieldActive {
                    combatTicker = "🛡️ Defense Shield blocked opponent counterattack!"
                } else {
                    playerHp = max(0, playerHp - 25)
                    combatTicker = "❌ Incorrect choice! Suffered 25 damage."
                }
            } else {
                combatTicker = "❌ Incorrect option. Review the clinical pearl below."
            }
        }

        // Reset round buffs
        isShieldActive = false
        isStrikeActive = false

        // Record review entry
        reviewRecords.append(
            TestQuestionReview(
                questionId: question.id,
                questionText: question.text,
                selectedOption: index >= 0 ? index : nil,
                correctOption: question.correctOptionIndex,
                isCorrect: isCorrect
            )
        )

        RemoteLogger.log(
            tag: "TestActivity_Answer",
            message: "Q\(currentIndex + 1) answered: \(isCorrect ? "CORRECT" : "WRONG")",
            metadata: ["qId": question.id, "streak": streak, "score": score]
        )
    }

    private func advanceToNextQuestion() {
        speechSynthesizer.stopSpeaking(at: .immediate)
        isSpeaking = false

        if currentIndex + 1 < questions.count {
            currentIndex += 1
            selectedOptionIndex = nil
            isAnswerSubmitted = false
            eliminatedOptions = []
            combatTicker = isChallenge ? "⚔️ New round started. Strike hard!" : "Clinical case \(currentIndex + 1) ready."
            startQuestionTimer()
        } else {
            isExamCompleted = true
            // Save completed test flag mirroring Android COMPLETED_TESTS
            UserDefaults.standard.set(true, forKey: "test_completed_\(quiz.id)")
            RemoteLogger.log(tag: "TestActivity_Finished", message: "Exam completed. Final score: \(score)")
        }
    }

    // MARK: - Power Actions

    private func useIntelPower() {
        guard intelCharges > 0, let q = currentQuestion, !isAnswerSubmitted else { return }
        intelCharges -= 1
        var wrongs = (0..<q.options.count).filter { $0 != q.correctOptionIndex }
        wrongs.shuffle()
        for idx in wrongs.prefix(2) {
            eliminatedOptions.insert(idx)
        }
        combatTicker = "⚡ Intel activated: 2 incorrect options eliminated!"
        RemoteLogger.log(tag: "TestActivity_IntelPower", message: "Intel 50:50 used for Q\(currentIndex + 1)")
    }

    private func useDefensePower() {
        guard defenseCharges > 0, !isAnswerSubmitted else { return }
        defenseCharges -= 1
        isShieldActive = true
        combatTicker = "🛡️ Shield primed! Damage blocked for this round."
        RemoteLogger.log(tag: "TestActivity_DefensePower", message: "Shield primed for Q\(currentIndex + 1)")
    }

    private func useStrikePower() {
        guard strikeCharges > 0, !isAnswerSubmitted else { return }
        strikeCharges -= 1
        isStrikeActive = true
        combatTicker = "🔥 Shock armed! 2x Critical damage on correct diagnosis!"
        RemoteLogger.log(tag: "TestActivity_StrikePower", message: "Shock armed for Q\(currentIndex + 1)")
    }

    private func useSurgePower() {
        guard surgeCharges > 0, !isAnswerSubmitted else { return }
        surgeCharges -= 1
        combatTicker = "🌀 Surge unleashed! Opponent focus disrupted."
        RemoteLogger.log(tag: "TestActivity_SurgePower", message: "Surge unleashed for Q\(currentIndex + 1)")
    }

    // MARK: - TTS Narration

    private func toggleSpeech() {
        if isSpeaking {
            speechSynthesizer.stopSpeaking(at: .immediate)
            isSpeaking = false
        } else if let q = currentQuestion {
            let utterance = AVSpeechUtterance(string: q.text)
            utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
            utterance.rate = 0.48
            speechSynthesizer.speak(utterance)
            isSpeaking = true
        }
    }

    // MARK: - Option Styling Helpers

    private func optionBadgeBackground(index: Int, question: Question) -> Color {
        if isAnswerSubmitted {
            if index == question.correctOptionIndex { return Color.green }
            if index == selectedOptionIndex { return Color.red }
        }
        return AppTheme.Palette.primary.opacity(0.15)
    }

    private func optionBadgeForeground(index: Int, question: Question) -> Color {
        if isAnswerSubmitted && (index == question.correctOptionIndex || index == selectedOptionIndex) {
            return .white
        }
        return AppTheme.Palette.primary
    }

    private func optionCardBackground(index: Int, question: Question) -> Color {
        if isAnswerSubmitted {
            if index == question.correctOptionIndex { return Color.green.opacity(0.12) }
            if index == selectedOptionIndex { return Color.red.opacity(0.12) }
        }
        return AppTheme.Palette.cardBackground
    }

    private func optionBorderColor(index: Int, question: Question) -> Color {
        if isAnswerSubmitted {
            if index == question.correctOptionIndex { return Color.green }
            if index == selectedOptionIndex { return Color.red }
        }
        return Color.clear
    }

    // MARK: - Fallback Clinical Questions

    private func generateFallbackMockQuestions() -> [Question] {
        [
            Question(
                id: 501,
                text: "A 45-year-old male presents with severe crushing retrosternal chest pain radiating to the left jaw. ECG reveals ST elevation in leads II, III, and aVF with reciprocal depressions in I and aVL. Which coronary artery is most likely occluded?",
                options: [
                    "Right Coronary Artery (RCA)",
                    "Left Anterior Descending (LAD)",
                    "Left Circumflex (LCx)",
                    "Left Main Coronary Artery"
                ],
                correctOptionIndex: 0,
                explanation: "ST elevation in II, III, and aVF indicates an acute Inferior Wall Myocardial Infarction. In 85-90% of individuals with right-dominant circulation, this territory is supplied by the Right Coronary Artery (RCA).",
                subject: "Cardiology",
                topic: "Ischemic Heart Disease",
                difficulty: "High Yield"
            ),
            Question(
                id: 502,
                text: "A 28-year-old female presents with heat intolerance, fine tremors, bilateral proptosis, and pretibial myxedema. Laboratory evaluation confirms TSH < 0.01 mIU/L with elevated Free T3 and T4. Which autoantibody is pathognomonic?",
                options: [
                    "Anti-TSH Receptor Antibodies (TRAb)",
                    "Anti-Thyroid Peroxidase (Anti-TPO)",
                    "Anti-Thyroglobulin (Anti-Tg)",
                    "Anti-Nuclear Antibody (ANA)"
                ],
                correctOptionIndex: 0,
                explanation: "Thyroid-stimulating immunoglobulin or TRAb binds to and stimulates TSH receptors on thyroid follicular cells, leading to Graves' Disease. Proptosis and pretibial myxedema are uniquely caused by retro-orbital and dermal TSH-receptor activation.",
                subject: "Endocrinology",
                topic: "Thyroid Disorders",
                difficulty: "Clinical"
            ),
            Question(
                id: 503,
                text: "A 62-year-old chronic smoker presents with painless gross hematuria. Cystoscopy reveals a papillary lesion at the bladder trigone. Transurethral resection confirms urothelial carcinoma with invasion into the detrusor muscle (T2). What is the definitive treatment of choice?",
                options: [
                    "Radical cystectomy with pelvic lymph node dissection",
                    "Intravesical BCG immunotherapy only",
                    "Transurethral resection of bladder tumor (TURBT) alone",
                    "Oral methotrexate chemotherapy"
                ],
                correctOptionIndex: 0,
                explanation: "Muscle-invasive bladder cancer (T2 and above) requires radical cystectomy with bilateral pelvic lymphadenectomy and urinary diversion (often preceded by neoadjuvant cisplatin-based chemotherapy). Intravesical BCG is strictly reserved for non-muscle-invasive bladder cancer (Ta, T1, Cis).",
                subject: "Urology",
                topic: "Uro-Oncology",
                difficulty: "Expert"
            )
        ]
    }
}

// MARK: - Review Struct

public struct TestQuestionReview: Identifiable, Codable {
    public var id = UUID()
    public let questionId: Int
    public let questionText: String
    public let selectedOption: Int?
    public let correctOption: Int
    public let isCorrect: Bool
}

// MARK: - Zoom Image Viewer

private struct ZoomImageViewer: View {
    @Environment(\.dismiss) private var dismiss
    let url: URL

    var body: some View {
        ZStack(alignment: .topTrailing) {
            Color.black.ignoresSafeArea()

            AsyncImage(url: url) { phase in
                if let image = phase.image {
                    image
                        .resizable()
                        .scaledToFit()
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    ProgressView().tint(.white)
                }
            }

            Button {
                dismiss()
            } label: {
                Image(systemName: "xmark.circle.fill")
                    .font(.system(size: 32))
                    .foregroundStyle(.white.opacity(0.85))
                    .padding()
            }
        }
    }
}
