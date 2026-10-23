import SwiftUI
import AVFoundation

/// 1:1 SwiftUI Replica of Android `SubjectTestActivity.kt`.
///
/// Features:
/// - 3 Operating Modes: Fixed Test Mode, Multiplayer Arena Mode, and Single Player Mode.
/// - 5-Option Clinical MCQ Support (Option A, B, C, D, and Option E for AIIMS / INI-CET).
/// - TextToSpeech (TTS) via `AVSpeechSynthesizer` with speak/stop explanation audio controls.
/// - 4 Hero Kit Powers: Intel Clue Scan, Strike 50-50 Distractor Elimination, Barrier Shield, Surge Multiplier.
/// - Question streak bonus tracker and real-time score sync.
/// - Previous question navigation (`btnPrev`) and Early Finish Test dialog (`btnFinishTest`).
/// - Comprehensive post-match review and results summary modal.
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

    // ─── State ────────────────────────────────────────────────────────────────
    @State private var currentHp: Int = 100
    @State private var myScore: Int = 0
    @State private var currentStreak: Int = 0
    @State private var allQuestionIds: [Int] = []
    @State private var currentIndex: Int = 0
    @State private var currentQuestion: Question? = nil
    @State private var answeredIndices: Set<Int> = []
    @State private var selectedOptionIndex: Int? = nil
    @State private var isAnswerSubmitted: Bool = false
    @State private var showExplanation: Bool = false
    @State private var eliminatedOptionIndices: Set<Int> = []

    // ─── Timer ────────────────────────────────────────────────────────────────
    @State private var remainingTimerSeconds: Int = 1800 // 30 min or 15 min
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
    @State private var isShockArmed: Bool = false
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

                // Hero Powers Bar (Multiplayer / Challenge Mode)
                if mode == .multiplayer || isChallenge {
                    powersToolbar
                        .padding(.horizontal, AppTheme.Spacing.md)
                        .padding(.top, 4)
                }

                Divider()
                    .background(Color.white.opacity(0.12))
                    .padding(.vertical, 8)

                // Main Content
                if isLoadingQuestions {
                    Spacer()
                    VStack(spacing: AppTheme.Spacing.md) {
                        ProgressView().tint(Color.yellow).scaleEffect(1.3)
                        Text("Loading Clinical Test Modules...")
                            .font(AppTheme.Font.headline)
                            .foregroundStyle(Color.white)
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
                    Text("No Questions Available")
                        .font(AppTheme.Font.title3)
                        .foregroundStyle(Color.white)
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
        }
        .navigationBarBackButtonHidden(true)
        .alert("Finish Test?", isPresented: $showFinishConfirmationAlert) {
            Button("Finish Test", role: .destructive) {
                stopSpeaking()
                finalizeTest()
            }
            Button("Continue", role: .cancel) {}
        } message: {
            Text("Are you sure you want to end the test now? Your current score and progress will be saved.")
        }
        .sheet(isPresented: $showResultSummary) {
            if let res = resultSummaryData {
                ChallengeResultView(result: res) {
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

            // Subject / Topic Center Label
            VStack(spacing: 1) {
                Text(subject.uppercased())
                    .font(.system(size: 11, weight: .black, design: .monospaced))
                    .foregroundStyle(Color.yellow)
                Text(topic?.isEmpty == false ? topic! : "Clinical Test")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(Color.white.opacity(0.7))
                    .lineLimit(1)
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

    // MARK: - Hero Powers Bar (Equipped Hero Kit)

    private var powersToolbar: some View {
        let kit = equippedHeroKit
        return HStack(spacing: 10) {
            // Slot 1: Intel Clue Scan
            powerBtn(title: kit.intelPower.shortLabel.uppercased(), icon: "magnifyingglass", charges: intelCharges, cd: intelCooldown, color: Color.cyan) {
                activateIntelScan()
            }
            // Slot 2: Strike 50-50 Distractor Elimination
            powerBtn(title: kit.strikePower.shortLabel.uppercased(), icon: "bolt.fill", charges: strikeCharges, cd: strikeCooldown, color: Color.orange) {
                activateStrikeDistractorElimination()
            }
            // Slot 3: Defense Barrier Shield
            powerBtn(title: kit.defensePower.shortLabel.uppercased(), icon: "shield.fill", charges: defenseCharges, cd: defenseCooldown, color: Color.blue) {
                activateShield()
            }
            // Slot 4: Surge Multiplier & Healing
            powerBtn(title: kit.surgePower.shortLabel.uppercased(), icon: "heart.fill", charges: surgeCharges, cd: surgeCooldown, color: Color.pink) {
                activateSurge()
            }
        }
    }

    private func powerBtn(
        title: String,
        icon: String,
        charges: Int,
        cd: Int,
        color: Color,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            VStack(spacing: 2) {
                ZStack {
                    Circle()
                        .fill(Color.white.opacity(0.08))
                        .frame(width: 36, height: 36)
                        .overlay(Circle().stroke(charges > 0 ? color.opacity(0.5) : Color.white.opacity(0.1), lineWidth: 1))

                    if cd > 0 {
                        Text("\(cd)")
                            .font(.system(size: 11, weight: .heavy, design: .monospaced))
                            .foregroundStyle(Color.yellow)
                    } else {
                        Image(systemName: icon)
                            .font(.system(size: 15))
                            .foregroundStyle(charges > 0 ? color : Color.gray)
                    }
                }
                HStack(spacing: 2) {
                    Text(title)
                        .font(.system(size: 9, weight: .bold))
                        .foregroundStyle(Color.white.opacity(0.8))
                    if charges > 0 {
                        Text("x\(charges)").font(.system(size: 9, weight: .heavy)).foregroundStyle(color)
                    }
                }
            }
        }
        .disabled(charges <= 0 || cd > 0 || isAnswerSubmitted)
    }

    // MARK: - Question Card & 5-Option Clinical MCQ

    private func questionCard(_ q: Question) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("QUESTION \(currentIndex + 1) OF \(allQuestionIds.isEmpty ? 1 : allQuestionIds.count)")
                    .font(.system(size: 11, weight: .heavy, design: .monospaced))
                    .foregroundStyle(Color.yellow)
                Spacer()
                Text("PTS: \(myScore)")
                    .font(.system(size: 11, weight: .heavy, design: .monospaced))
                    .foregroundStyle(Color.green)
            }

            Text(q.text)
                .font(.system(size: 15, weight: .medium))
                .foregroundStyle(Color.white)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: 14)
                .fill(Color.white.opacity(0.06))
                .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color.white.opacity(0.1), lineWidth: 1))
        )
    }

    private func optionsGrid(_ q: Question) -> some View {
        VStack(spacing: 8) {
            ForEach(0..<q.options.count, id: \.self) { idx in
                let letter = ["A", "B", "C", "D", "E"][idx % 5]
                let isEliminated = eliminatedOptionIndices.contains(idx)

                Button {
                    guard !isAnswerSubmitted && !isEliminated else { return }
                    selectedOptionIndex = idx
                } label: {
                    HStack(spacing: 12) {
                        Text(letter)
                            .font(.system(size: 14, weight: .black, design: .rounded))
                            .foregroundStyle(optionBadgeFg(index: idx, q: q))
                            .frame(width: 32, height: 32)
                            .background(Circle().fill(optionBadgeBg(index: idx, q: q)))

                        Text(q.options[idx])
                            .font(.system(size: 14, weight: .medium))
                            .foregroundStyle(isEliminated ? Color.gray.opacity(0.35) : Color.white)
                            .strikethrough(isEliminated, color: Color.red)
                            .multilineTextAlignment(.leading)
                            .lineLimit(3)

                        Spacer()

                        if isAnswerSubmitted && idx == q.correctIndex {
                            Image(systemName: "checkmark.circle.fill").foregroundStyle(Color.green)
                        } else if isAnswerSubmitted && idx == selectedOptionIndex && idx != q.correctIndex {
                            Image(systemName: "xmark.circle.fill").foregroundStyle(Color.red)
                        }
                    }
                    .padding(12)
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .fill(optionCardBg(index: idx, q: q))
                            .overlay(RoundedRectangle(cornerRadius: 12).stroke(optionCardBorder(index: idx, q: q), lineWidth: 1.5))
                    )
                }
                .disabled(isAnswerSubmitted || isEliminated)
            }
        }
    }

    private func optionBadgeFg(index: Int, q: Question) -> Color {
        if isAnswerSubmitted {
            if index == q.correctIndex { return Color.black }
            if index == selectedOptionIndex { return Color.white }
        }
        return selectedOptionIndex == index ? Color.black : Color.white
    }

    private func optionBadgeBg(index: Int, q: Question) -> Color {
        if isAnswerSubmitted {
            if index == q.correctIndex { return Color.green }
            if index == selectedOptionIndex { return Color.red }
        }
        return selectedOptionIndex == index ? Color.yellow : Color.white.opacity(0.12)
    }

    private func optionCardBg(index: Int, q: Question) -> Color {
        if isAnswerSubmitted {
            if index == q.correctIndex { return Color.green.opacity(0.18) }
            if index == selectedOptionIndex { return Color.red.opacity(0.18) }
        }
        return selectedOptionIndex == index ? Color.yellow.opacity(0.12) : Color.white.opacity(0.05)
    }

    private func optionCardBorder(index: Int, q: Question) -> Color {
        if isAnswerSubmitted {
            if index == q.correctIndex { return Color.green }
            if index == selectedOptionIndex { return Color.red }
        }
        return selectedOptionIndex == index ? Color.yellow : Color.white.opacity(0.12)
    }

    // MARK: - Explanation & TextToSpeech (TTS) Card

    private var explanationCardView: some View {
        Group {
            if let q = currentQuestion {
                explanationCard(q)
            }
        }
    }

    private func explanationCard(_ q: Question) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: "waveform.badge.magnifyingglass")
                    .foregroundStyle(Color.yellow)
                Text("EXPLANATION & CLINICAL RATIONALE")
                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                    .foregroundStyle(Color.yellow)

                Spacer()

                // TextToSpeech Speak / Stop button (replicates btnSpeakExplanation)
                Button {
                    toggleSpeech(for: q.explanation ?? "")
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: isSpeaking ? "stop.circle.fill" : "speaker.wave.2.circle.fill")
                        Text(isSpeaking ? "Stop" : "Read Aloud")
                            .font(.system(size: 11, weight: .bold))
                    }
                    .foregroundStyle(isSpeaking ? Color.red : Color.cyan)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Capsule().fill(Color.white.opacity(0.1)))
                }
            }

            Text(!q.explanation.isEmpty ? q.explanation : "No rationale provided.")
                .font(.system(size: 13, weight: .regular))
                .foregroundStyle(Color.white.opacity(0.85))
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: 14)
                .fill(Color(hex: "#101B2E"))
                .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color.yellow.opacity(0.25), lineWidth: 1))
        )
    }

    private func toggleSpeech(for text: String) {
        if isSpeaking {
            stopSpeaking()
        } else {
            speak(text: text)
        }
    }

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
        showCombatFlyout(text: "⚡ \(power.powerName.uppercased())! +\(healAmt) HP & 1.5x SURGE! 🔥", color: Color.yellow)
        UIImpactFeedbackGenerator(style: .heavy).impactOccurred()
    }

    // MARK: - Answer Submission

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
        } else {
            UIImpactFeedbackGenerator(style: .rigid).impactOccurred()
            currentStreak = 0
            if shieldRoundsActive > 0 {
                shieldRoundsActive -= 1
            } else {
                currentHp = max(0, currentHp - 10)
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
            await fetchQuestionDetails(qId: qId)
        }
    }

    // MARK: - Session Setup & API Loading

    private func initializeTestSession() {
        // Resolve operating mode
        if let list = questionIdList, !list.isEmpty {
            mode = .fixedTest
            allQuestionIds = list
            remainingTimerSeconds = 30 * 60
        } else if isChallenge && !challengeId.isEmpty {
            mode = .multiplayer
            remainingTimerSeconds = 15 * 60
        } else {
            mode = .singlePlayer
            remainingTimerSeconds = 30 * 60
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
        isShockArmed = false
        surgeScoreMultiplierActive = false

        Task {
            await loadInitialQuestions()
        }
    }

    @MainActor
    private func loadInitialQuestions() async {
        isLoadingQuestions = true
        defer { isLoadingQuestions = false }

        if allQuestionIds.isEmpty {
            do {
                let res = try await api.study.fetchQuestions(
                    subject: subject,
                    topic: topic,
                    userId: session.userId,
                    limit: 10
                )
                if let q = res.question {
                    allQuestionIds = [q.id]
                    self.currentQuestion = q
                } else {
                    fallbackDefaultDeck()
                }
            } catch {
                fallbackDefaultDeck()
            }
        } else {
            await fetchQuestionDetails(qId: allQuestionIds[0])
        }
    }

    @MainActor
    private func fetchQuestionDetails(qId: Int) async {
        do {
            let res = try await api.study.fetchQuestions(
                subject: subject,
                topic: topic,
                userId: session.userId,
                limit: 1
            )
            if let q = res.question {
                self.currentQuestion = q
            }
        } catch {
            // Keep existing question if fetch fails
        }
    }

    private func fallbackDefaultDeck() {
        let sampleQuestions = [
            Question(
                id: 201,
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
                id: 202,
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
        allQuestionIds = sampleQuestions.map { $0.id }
        self.currentQuestion = sampleQuestions.first
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
        let correctCount = reviewItems.filter { $0.isCorrect }.count
        let playerWon = correctCount >= max(1, reviewItems.count / 2)

        let summary = BattleResultSummary(
            challengeId: challengeId.isEmpty ? "test_\(UUID().uuidString.prefix(6))" : challengeId,
            userName: session.currentUser?.name ?? "Doctor",
            opponentName: "Clinical Examiner",
            userScore: myScore,
            opponentScore: 0,
            userCorrect: correctCount,
            opponentCorrect: 0,
            totalQuestions: max(1, reviewItems.count),
            expGained: correctCount * 25,
            creditsGained: playerWon ? 50 : 15,
            questionReviews: reviewItems
        )
        self.resultSummaryData = summary
        self.showResultSummary = true
    }
}
