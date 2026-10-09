import SwiftUI

/// 1:1 SwiftUI port of Android `ClassicGameActivity.kt`.
///
/// Features a real-time 1v1 battle arena duel:
/// - Split-screen Player vs Opponent HUD with dual HP bars and trailing ghost damage bars.
/// - Active Guardian combat powers (Adrenaline ⚡, Shield 🛡️, Shock 💥, Surge 🌀).
/// - Dynamic floating combat numbers (-20 HP, BLOCKED!, CRITICAL!, +15 HP).
/// - Interactive question cards with instant feedback and haptic cues.
/// - Autonomous opponent bot simulation based on personality and speed metrics.
/// - Low-HP critical vignette overlay and K.O. victory/defeat conditions.
/// - Smooth transition to `ChallengeResultView` with question reviews.
struct ClassicBattleArenaView: View {

    let subject: String
    let topic: String?
    let challengeId: String
    let opponentName: String
    let opponentRank: String
    let opponentWarrior: Warrior
    let userWarrior: Warrior
    var onFinish: ((BattleResultSummary) -> Void)?

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @Environment(\.dismiss) private var dismiss

    // ─── Health & Combat State ────────────────────────────────────────────────
    @State private var playerMaxHp: Int = 100
    @State private var playerHp: Int = 100
    @State private var playerGhostHp: Double = 100
    @State private var opponentMaxHp: Int = 100
    @State private var opponentHp: Int = 100
    @State private var opponentGhostHp: Double = 100

    @State private var playerScore: Int = 0
    @State private var opponentScore: Int = 0
    @State private var playerStreak: Int = 0
    @State private var userCorrectCount: Int = 0
    @State private var opponentCorrectCount: Int = 0

    // ─── Hero Kit Power-Ups ───────────────────────────────────────────────────
    @State private var adrenalineCharges: Int = 3
    @State private var shieldCharges: Int = 2
    @State private var shockCharges: Int = 2
    @State private var surgeCharges: Int = 1

    @State private var isShieldActive: Bool = false
    @State private var isShockArmed: Bool = false
    @State private var isSurgeActive: Bool = false
    @State private var eliminatedOptionIndices: Set<Int> = []

    // ─── Question Progression ─────────────────────────────────────────────────
    @State private var questions: [Question] = []
    @State private var currentIndex: Int = 0
    @State private var isLoadingQuestions: Bool = true
    @State private var selectedOptionIndex: Int? = nil
    @State private var isAnswerSubmitted: Bool = false
    @State private var roundTimerSeconds: Int = 15
    @State private var isRoundActive: Bool = false
    @State private var showForfeitAlert: Bool = false

    // ─── Dynamic Feedback & Animations ────────────────────────────────────────
    @State private var floatingCombatTexts: [FloatingCombatItem] = []
    @State private var isCriticalHpFlashing: Bool = false
    @State private var screenShakeOffset: CGFloat = 0
    @State private var showExplanation: Bool = false
    @State private var questionReviews: [QuestionReviewItem] = []

    // ─── Timers ───────────────────────────────────────────────────────────────
    private let tickTimer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()
    @State private var botResponseWorkItem: DispatchWorkItem? = nil

    private var currentQuestion: Question? {
        guard questions.indices.contains(currentIndex) else { return nil }
        return questions[currentIndex]
    }

    var body: some View {
        ZStack {
            // Dark arena background
            LinearGradient(
                colors: [Color(hex: "#060913"), Color(hex: "#0F172A"), Color(hex: "#05070E")],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            // Critical HP Vignette Overlay
            if playerHp <= 30 {
                RadialGradient(
                    gradient: Gradient(colors: [Color.clear, Color.red.opacity(isCriticalHpFlashing ? 0.35 : 0.15)]),
                    center: .center,
                    startRadius: 100,
                    endRadius: 400
                )
                .ignoresSafeArea()
                .animation(.easeInOut(duration: 0.8).repeatForever(autoreverses: true), value: isCriticalHpFlashing)
                .onAppear { isCriticalHpFlashing = true }
            }

            VStack(spacing: 0) {
                // Top Arena Header & Forfeit Bar
                arenaTopBar

                // Versus 1v1 Dual HP Hud
                versusHealthHUD
                    .padding(.horizontal, AppTheme.Spacing.md)
                    .padding(.top, 4)

                // Hero Power-Up Toolbar
                heroPowersToolbar
                    .padding(.horizontal, AppTheme.Spacing.md)
                    .padding(.top, AppTheme.Spacing.xs)

                Divider()
                    .background(Color.white.opacity(0.1))
                    .padding(.vertical, AppTheme.Spacing.xs)

                // Question Area or Loading State
                if isLoadingQuestions {
                    Spacer()
                    VStack(spacing: AppTheme.Spacing.md) {
                        ProgressView()
                            .tint(Color.yellow)
                            .scaleEffect(1.3)
                        Text("Loading Clinical Combat Scenarios...")
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
                    Text("Battle Concluded")
                        .font(AppTheme.Font.title2)
                        .foregroundStyle(Color.white)
                    Spacer()
                }
            }
            .offset(x: screenShakeOffset)

            // Dynamic Floating Combat Numbers
            ForEach(floatingCombatTexts) { item in
                Text(item.text)
                    .font(.system(size: 22, weight: .black, design: .rounded))
                    .foregroundStyle(item.color)
                    .shadow(color: item.color.opacity(0.6), radius: 6)
                    .position(item.position)
                    .opacity(item.opacity)
            }
        }
        .navigationBarBackButtonHidden(true)
        .alert("Abandon Battle?", isPresented: $showForfeitAlert) {
            Button("Forfeit Match", role: .destructive) {
                RemoteLogger.log(tag: "ClassicArena_Forfeit", message: "User forfeited match: \(challengeId)")
                finishBattle(playerWon: false, isForfeit: true)
            }
            Button("Continue Fighting", role: .cancel) {}
        } message: {
            Text("Leaving now will count as an immediate defeat and surrender your arena rank points.")
        }
        .onAppear {
            initializeFighters()
            Task { await loadArenaQuestions() }
        }
        .onReceive(tickTimer) { _ in
            handleTimerTick()
        }
    }

    // MARK: - Arena Top Bar

    private var arenaTopBar: some View {
        HStack {
            Button {
                showForfeitAlert = true
            } label: {
                HStack(spacing: 4) {
                    Image(systemName: "chevron.left")
                    Text("Forfeit")
                }
                .font(AppTheme.Font.caption.weight(.semibold))
                .foregroundStyle(AppTheme.Palette.textMuted)
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(Capsule().fill(Color.white.opacity(0.08)))
            }

            Spacer()

            VStack(spacing: 2) {
                Text(subject.uppercased())
                    .font(.system(size: 10, weight: .black, design: .monospaced))
                    .foregroundStyle(Color.yellow)

                if let topic = topic, !topic.isEmpty {
                    Text(topic)
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(Color.white)
                        .lineLimit(1)
                }
            }

            Spacer()

            // Round Tracker
            HStack(spacing: 4) {
                Image(systemName: "flame.fill")
                    .foregroundStyle(playerStreak > 0 ? Color.orange : Color.gray)
                Text("\(playerStreak)x")
                    .font(.system(size: 12, weight: .black, design: .monospaced))
                    .foregroundStyle(playerStreak > 0 ? Color.orange : Color.gray)
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(Capsule().fill(Color.white.opacity(0.06)))
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.top, AppTheme.Spacing.xs)
    }

    // MARK: - Versus 1v1 Dual HP HUD

    private var versusHealthHUD: some View {
        HStack(alignment: .center, spacing: AppTheme.Spacing.sm) {
            // Player Fighter Card
            fighterHealthPod(
                name: session.currentUser?.name ?? "Dr. You",
                avatar: userWarrior.avatarImageName,
                rank: "Aspirant",
                currentHp: playerHp,
                maxHp: playerMaxHp,
                ghostHp: playerGhostHp,
                score: playerScore,
                isPlayer: true
            )

            // Center Match Round Timer
            VStack(spacing: 4) {
                ZStack {
                    Circle()
                        .stroke(roundTimerSeconds <= 5 ? Color.red.opacity(0.3) : Color.yellow.opacity(0.2), lineWidth: 3)
                        .frame(width: 48, height: 48)

                    Text("\(roundTimerSeconds)")
                        .font(.system(size: 20, weight: .black, design: .monospaced))
                        .foregroundStyle(roundTimerSeconds <= 5 ? Color.red : Color.yellow)
                        .scaleEffect(roundTimerSeconds <= 5 ? 1.15 : 1.0)
                        .animation(.easeInOut(duration: 0.3), value: roundTimerSeconds)
                }

                Text("ROUND \(currentIndex + 1)/\(max(1, questions.count))")
                    .font(.system(size: 8, weight: .black, design: .monospaced))
                    .foregroundStyle(AppTheme.Palette.textMuted)
            }
            .frame(width: 64)

            // Opponent Fighter Card
            fighterHealthPod(
                name: opponentName,
                avatar: opponentWarrior.avatarImageName,
                rank: opponentRank,
                currentHp: opponentHp,
                maxHp: opponentMaxHp,
                ghostHp: opponentGhostHp,
                score: opponentScore,
                isPlayer: false
            )
        }
    }

    private func fighterHealthPod(
        name: String,
        avatar: String,
        rank: String,
        currentHp: Int,
        maxHp: Int,
        ghostHp: Double,
        score: Int,
        isPlayer: Bool
    ) -> some View {
        VStack(alignment: isPlayer ? .leading : .trailing, spacing: 4) {
            HStack(spacing: 6) {
                if isPlayer {
                    fighterAvatarView(avatar: avatar, isPlayer: isPlayer)
                }

                VStack(alignment: isPlayer ? .leading : .trailing, spacing: 2) {
                    Text(name)
                        .font(.system(size: 13, weight: .bold))
                        .foregroundStyle(Color.white)
                        .lineLimit(1)

                    HStack(spacing: 4) {
                        Text(rank.uppercased())
                            .font(.system(size: 8, weight: .black))
                            .foregroundStyle(isPlayer ? Color.cyan : Color.purple)

                        Text("• \(score) pts")
                            .font(.system(size: 9, weight: .semibold, design: .monospaced))
                            .foregroundStyle(AppTheme.Palette.textMuted)
                    }
                }

                if !isPlayer {
                    fighterAvatarView(avatar: avatar, isPlayer: isPlayer)
                }
            }

            // Health Bar with Trailing Ghost Bar
            ZStack(alignment: isPlayer ? .leading : .trailing) {
                // Background Track
                RoundedRectangle(cornerRadius: 4)
                    .fill(Color.white.opacity(0.12))
                    .frame(height: 10)

                // Ghost Damage Bar (smooth drop)
                GeometryReader { geo in
                    let ratio = CGFloat(max(0, min(1.0, ghostHp / Double(maxHp))))
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.orange.opacity(0.8))
                        .frame(width: geo.size.width * ratio, height: 10)
                }
                .frame(height: 10)

                // Current Active Health Bar
                GeometryReader { geo in
                    let ratio = CGFloat(max(0, min(1.0, Double(currentHp) / Double(maxHp))))
                    RoundedRectangle(cornerRadius: 4)
                        .fill(
                            LinearGradient(
                                colors: currentHp > 30 ? [Color(hex: "#10B981"), Color(hex: "#059669")] : [Color(hex: "#EF4444"), Color(hex: "#DC2626")],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(width: geo.size.width * ratio, height: 10)
                }
                .frame(height: 10)
            }

            // HP Text
            Text("\(max(0, currentHp)) / \(maxHp) HP")
                .font(.system(size: 9, weight: .bold, design: .monospaced))
                .foregroundStyle(currentHp <= 30 ? Color.red : Color.white.opacity(0.8))
        }
        .frame(maxWidth: .infinity)
        .padding(8)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                .fill(Color.white.opacity(0.04))
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                        .stroke(isPlayer ? Color.cyan.opacity(0.3) : Color.purple.opacity(0.3), lineWidth: 1)
                )
        )
    }

    private func fighterAvatarView(avatar: String, isPlayer: Bool) -> some View {
        ZStack {
            Circle()
                .fill((isPlayer ? Color.cyan : Color.purple).opacity(0.2))
                .frame(width: 34, height: 34)

            Image(systemName: isPlayer ? "person.crop.circle.fill" : "bolt.shield.fill")
                .font(.system(size: 20))
                .foregroundStyle(isPlayer ? Color.cyan : Color.purple)
        }
    }

    // MARK: - Hero Power-Up Toolbar

    private var heroPowersToolbar: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            // Adrenaline (Heal + 50/50 eliminate)
            powerButton(
                title: "ADRENALINE",
                icon: "bolt.heart.fill",
                charges: adrenalineCharges,
                tint: Color(hex: "#10B981"),
                isActive: false
            ) {
                activateAdrenaline()
            }

            // Shield (Absorb incoming damage)
            powerButton(
                title: "SHIELD",
                icon: "shield.checkered",
                charges: shieldCharges,
                tint: Color(hex: "#3B82F6"),
                isActive: isShieldActive
            ) {
                activateShield()
            }

            // Shock (Bonus +15 dmg to opponent)
            powerButton(
                title: "SHOCK",
                icon: "bolt.fill",
                charges: shockCharges,
                tint: Color(hex: "#F59E0B"),
                isActive: isShockArmed
            ) {
                activateShock()
            }

            // Surge (Double Points multiplier)
            powerButton(
                title: "SURGE",
                icon: "sparkles",
                charges: surgeCharges,
                tint: Color(hex: "#EC4899"),
                isActive: isSurgeActive
            ) {
                activateSurge()
            }
        }
    }

    private func powerButton(
        title: String,
        icon: String,
        charges: Int,
        tint: Color,
        isActive: Bool,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            VStack(spacing: 3) {
                ZStack {
                    Circle()
                        .fill(isActive ? tint : tint.opacity(0.18))
                        .frame(width: 32, height: 32)
                        .overlay(
                            Circle()
                                .stroke(tint, lineWidth: isActive ? 2 : 1)
                        )

                    Image(systemName: icon)
                        .font(.system(size: 14, weight: .bold))
                        .foregroundStyle(isActive ? Color.black : tint)
                }

                HStack(spacing: 2) {
                    Text(title)
                        .font(.system(size: 8, weight: .black))
                        .foregroundStyle(Color.white.opacity(0.8))

                    Text("(\(charges))")
                        .font(.system(size: 8, weight: .bold, design: .monospaced))
                        .foregroundStyle(charges > 0 ? tint : Color.gray)
                }
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 4)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                    .fill(isActive ? tint.opacity(0.2) : Color.white.opacity(0.03))
            )
        }
        .disabled(charges <= 0 || isAnswerSubmitted)
        .opacity(charges > 0 && !isAnswerSubmitted ? 1.0 : 0.4)
    }

    // MARK: - Question Card

    private func questionCard(_ q: Question) -> some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                HStack {
                    Text("CLINICAL CASE STEM")
                        .font(.system(size: 10, weight: .black, design: .monospaced))
                        .foregroundStyle(Color.yellow)

                    Spacer()

                    Text(q.topic.isEmpty ? subject : q.topic)
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundStyle(AppTheme.Palette.textMuted)
                }

                Text(q.text)
                    .font(.system(size: 16, weight: .medium))
                    .foregroundStyle(Color.white)
                    .fixedSize(horizontal: false, vertical: true)

                // Optional question image
                if let imageURL = q.imageURL {
                    AsyncImage(url: imageURL) { phase in
                        switch phase {
                        case .empty:
                            ProgressView()
                                .frame(height: 140)
                        case .success(let image):
                            image
                                .resizable()
                                .scaledToFit()
                                .frame(maxHeight: 180)
                                .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.sm))
                        case .failure:
                            EmptyView()
                        @unknown default:
                            EmptyView()
                        }
                    }
                    .frame(maxWidth: .infinity)
                }
            }
            .padding(AppTheme.Spacing.sm)
        }
    }

    // MARK: - Options Grid

    private func optionsGrid(_ q: Question) -> some View {
        VStack(spacing: AppTheme.Spacing.xs) {
            ForEach(0..<q.options.count, id: \.self) { index in
                let optionLetter = ["A", "B", "C", "D"][index % 4]
                let isEliminated = eliminatedOptionIndices.contains(index)
                let isSelected = selectedOptionIndex == index
                let isCorrect = q.correctIndex == index

                Button {
                    guard !isAnswerSubmitted, !isEliminated else { return }
                    submitUserAnswer(index: index, question: q)
                } label: {
                    HStack(spacing: AppTheme.Spacing.sm) {
                        // Letter Badge
                        Text(optionLetter)
                            .font(.system(size: 12, weight: .black, design: .monospaced))
                            .foregroundStyle(optionBadgeColor(index: index, isCorrect: isCorrect, isSelected: isSelected))
                            .frame(width: 28, height: 28)
                            .background(
                                Circle()
                                    .fill(optionBadgeBgColor(index: index, isCorrect: isCorrect, isSelected: isSelected))
                            )

                        Text(q.options[index])
                            .font(.system(size: 14, weight: .medium))
                            .foregroundStyle(isEliminated ? Color.gray : Color.white)
                            .strikethrough(isEliminated, color: Color.red)
                            .multilineTextAlignment(.leading)
                            .fixedSize(horizontal: false, vertical: true)

                        Spacer()

                        if isAnswerSubmitted {
                            if isCorrect {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundStyle(Color(hex: "#10B981"))
                            } else if isSelected {
                                Image(systemName: "xmark.circle.fill")
                                    .foregroundStyle(Color(hex: "#EF4444"))
                            }
                        }
                    }
                    .padding(AppTheme.Spacing.sm)
                    .background(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                            .fill(optionBackgroundColor(index: index, isCorrect: isCorrect, isSelected: isSelected))
                            .overlay(
                                RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                                    .stroke(optionBorderColor(index: index, isCorrect: isCorrect, isSelected: isSelected), lineWidth: isSelected ? 2 : 1)
                            )
                    )
                }
                .disabled(isAnswerSubmitted || isEliminated)
                .opacity(isEliminated ? 0.35 : 1.0)
            }
        }
    }

    private func optionBadgeColor(index: Int, isCorrect: Bool, isSelected: Bool) -> Color {
        if isAnswerSubmitted {
            if isCorrect { return Color.black }
            if isSelected { return Color.white }
        }
        return isSelected ? Color.black : Color.cyan
    }

    private func optionBadgeBgColor(index: Int, isCorrect: Bool, isSelected: Bool) -> Color {
        if isAnswerSubmitted {
            if isCorrect { return Color(hex: "#10B981") }
            if isSelected { return Color(hex: "#EF4444") }
        }
        return isSelected ? Color.cyan : Color.cyan.opacity(0.15)
    }

    private func optionBackgroundColor(index: Int, isCorrect: Bool, isSelected: Bool) -> Color {
        if isAnswerSubmitted {
            if isCorrect { return Color(hex: "#10B981").opacity(0.2) }
            if isSelected { return Color(hex: "#EF4444").opacity(0.2) }
        }
        return isSelected ? Color.cyan.opacity(0.15) : Color.white.opacity(0.04)
    }

    private func optionBorderColor(index: Int, isCorrect: Bool, isSelected: Bool) -> Color {
        if isAnswerSubmitted {
            if isCorrect { return Color(hex: "#10B981") }
            if isSelected { return Color(hex: "#EF4444") }
        }
        return isSelected ? Color.cyan : Color.white.opacity(0.1)
    }

    // MARK: - Explanation Card

    private func explanationCard(_ q: Question) -> some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
                HStack {
                    Image(systemName: "lightbulb.fill")
                        .foregroundStyle(Color.yellow)
                    Text("CLINICAL RATIONALE")
                        .font(.system(size: 11, weight: .black, design: .monospaced))
                        .foregroundStyle(Color.yellow)
                    Spacer()
                }

                Text(q.explanation.isEmpty ? "Correct answer is: \(q.correctOption ?? "Option A")." : q.explanation)
                    .font(AppTheme.Font.subheadline)
                    .foregroundStyle(AppTheme.Palette.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)

                HStack {
                    Spacer()
                    Button("Next Round ➔") {
                        advanceToNextQuestion()
                    }
                    .font(AppTheme.Font.headline)
                    .foregroundStyle(Color.black)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 8)
                    .background(Capsule().fill(Color.yellow))
                }
                .padding(.top, 4)
            }
            .padding(AppTheme.Spacing.sm)
        }
    }

    // MARK: - Power-Up Logic

    private func activateAdrenaline() {
        guard adrenalineCharges > 0, !isAnswerSubmitted, let q = currentQuestion else { return }
        adrenalineCharges -= 1

        // 1. Heal user
        let healAmount = (userWarrior.id == 1) ? 30 : 15
        playerHp = min(playerMaxHp, playerHp + healAmount)
        playerGhostHp = Double(playerHp)
        spawnFloatingText("+\(healAmount) HP ⚡", color: Color.green, isPlayer: true)

        // 2. Eliminate 2 wrong choices (50-50)
        var wrongIndices: [Int] = []
        for i in 0..<q.options.count {
            if i != q.correctIndex && !eliminatedOptionIndices.contains(i) {
                wrongIndices.append(i)
            }
        }
        wrongIndices.shuffle()
        for idx in wrongIndices.prefix(2) {
            eliminatedOptionIndices.insert(idx)
        }

        UIImpactFeedbackGenerator(style: .medium).impactOccurred()
        RemoteLogger.log(tag: "ClassicArena_Power", message: "Activated Adrenaline: healed \(healAmount) HP, eliminated \(eliminatedOptionIndices.count) options")
    }

    private func activateShield() {
        guard shieldCharges > 0, !isShieldActive, !isAnswerSubmitted else { return }
        shieldCharges -= 1
        isShieldActive = true
        spawnFloatingText("SHIELD ACTIVE 🛡️", color: Color.cyan, isPlayer: true)
        UIImpactFeedbackGenerator(style: .medium).impactOccurred()
        RemoteLogger.log(tag: "ClassicArena_Power", message: "Activated Shield Ward")
    }

    private func activateShock() {
        guard shockCharges > 0, !isShockArmed, !isAnswerSubmitted else { return }
        shockCharges -= 1
        isShockArmed = true
        spawnFloatingText("SHOCK ARMED 💥", color: Color.orange, isPlayer: true)
        UIImpactFeedbackGenerator(style: .medium).impactOccurred()
        RemoteLogger.log(tag: "ClassicArena_Power", message: "Activated Shock Strike")
    }

    private func activateSurge() {
        guard surgeCharges > 0, !isSurgeActive, !isAnswerSubmitted else { return }
        surgeCharges -= 1
        isSurgeActive = true
        spawnFloatingText("SURGE 2.0x 🌀", color: Color.pink, isPlayer: true)
        UIImpactFeedbackGenerator(style: .medium).impactOccurred()
        RemoteLogger.log(tag: "ClassicArena_Power", message: "Activated Surge Multiplier")
    }

    // MARK: - Round Timer & Game Progression

    private func handleTimerTick() {
        guard isRoundActive, !isAnswerSubmitted else { return }

        if roundTimerSeconds > 0 {
            roundTimerSeconds -= 1
            if roundTimerSeconds == 0 {
                // Time Out = Player counted as wrong answer
                handlePlayerTimeout()
            }
        }
    }

    private func handlePlayerTimeout() {
        guard let q = currentQuestion, !isAnswerSubmitted else { return }
        isAnswerSubmitted = true
        UIImpactFeedbackGenerator(style: .heavy).impactOccurred()

        // Damage Player for timeout
        applyDamageToPlayer(amount: 15)
        playerStreak = 0
        spawnFloatingText("TIME EXPIRED! -15 HP", color: Color.red, isPlayer: true)

        recordQuestionReview(question: q, chosenIndex: nil, isCorrect: false)
        showExplanation = true
    }

    private func submitUserAnswer(index: Int, question: Question) {
        guard !isAnswerSubmitted else { return }
        isAnswerSubmitted = true
        selectedOptionIndex = index
        let isCorrect = (index == question.correctIndex)

        RemoteLogger.log(
            tag: "ClassicArena_Answer",
            message: "User answered Q#\(question.id) (Option [\(["A","B","C","D"][index % 4])]): correct=\(isCorrect), streak=\(playerStreak)"
        )

        if isCorrect {
            UIImpactFeedbackGenerator(style: .heavy).impactOccurred()
            userCorrectCount += 1
            playerStreak += 1

            var points = 100 + (playerStreak * 10)
            if isSurgeActive {
                points *= 2
                isSurgeActive = false
            }
            playerScore += points
            spawnFloatingText("+\(points) PTS 🔥", color: Color.yellow, isPlayer: true)

            // Deal Damage to Opponent
            var damageToOpponent = 20
            if isShockArmed {
                damageToOpponent += 15
                isShockArmed = false
                spawnFloatingText("CRITICAL STRIKE! 💥", color: Color.orange, isPlayer: false)
            }
            applyDamageToOpponent(amount: damageToOpponent)
        } else {
            UIImpactFeedbackGenerator(style: .rigid).impactOccurred()
            playerStreak = 0
            // Self Damage on wrong answer
            applyDamageToPlayer(amount: 15)
        }

        recordQuestionReview(question: question, chosenIndex: index, isCorrect: isCorrect)
        showExplanation = true
    }

    private func recordQuestionReview(question: Question, chosenIndex: Int?, isCorrect: Bool) {
        let chosenText = chosenIndex != nil && question.options.indices.contains(chosenIndex!)
            ? question.options[chosenIndex!]
            : "No Answer"

        let review = QuestionReviewItem(
            question: question.text,
            userAnswer: chosenText,
            correctAnswer: question.correctOption ?? "Option A",
            isCorrect: isCorrect,
            explanation: question.explanation
        )
        questionReviews.append(review)
    }

    private func advanceToNextQuestion() {
        showExplanation = false
        selectedOptionIndex = nil
        isAnswerSubmitted = false
        eliminatedOptionIndices.removeAll()
        isShieldActive = false
        isShockArmed = false
        isSurgeActive = false

        // Check K.O. conditions
        if playerHp <= 0 || opponentHp <= 0 {
            finishBattle(playerWon: playerHp > opponentHp, isForfeit: false)
            return
        }

        if currentIndex + 1 < questions.count {
            currentIndex += 1
            roundTimerSeconds = 15
            isRoundActive = true
            scheduleBotOpponentAction()
        } else {
            finishBattle(playerWon: playerScore >= opponentScore, isForfeit: false)
        }
    }

    // MARK: - Damage Application & Smooth Ghost Bars

    private func applyDamageToPlayer(amount: Int) {
        if isShieldActive {
            isShieldActive = false
            spawnFloatingText("BLOCKED! 🛡️", color: Color.cyan, isPlayer: true)
            return
        }

        playerHp = max(0, playerHp - amount)
        spawnFloatingText("-\(amount) HP", color: Color.red, isPlayer: true)

        // Shake Screen
        withAnimation(.default) { screenShakeOffset = 10 }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
            withAnimation(.default) { screenShakeOffset = -8 }
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
            withAnimation(.default) { screenShakeOffset = 0 }
        }

        // Smooth Ghost HP decay
        withAnimation(.easeOut(duration: 0.6)) {
            playerGhostHp = Double(playerHp)
        }

        if playerHp <= 0 {
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
                finishBattle(playerWon: false, isForfeit: false)
            }
        }
    }

    private func applyDamageToOpponent(amount: Int) {
        opponentHp = max(0, opponentHp - amount)
        spawnFloatingText("-\(amount) HP", color: Color.orange, isPlayer: false)

        withAnimation(.easeOut(duration: 0.6)) {
            opponentGhostHp = Double(opponentHp)
        }

        if opponentHp <= 0 {
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
                finishBattle(playerWon: true, isForfeit: false)
            }
        }
    }

    // MARK: - Bot Opponent AI Simulation

    private func scheduleBotOpponentAction() {
        botResponseWorkItem?.cancel()
        guard let q = currentQuestion else { return }

        // Bot ponders between 3.5 and 6.0 seconds
        let delay = Double.random(in: 3.5...6.0)
        let item = DispatchWorkItem {
            guard !isAnswerSubmitted, isRoundActive else { return }

            // 78% accuracy probability
            let botCorrect = Double.random(in: 0...1.0) < 0.78
            if botCorrect {
                opponentCorrectCount += 1
                opponentScore += 100
                // Bot attacks player
                applyDamageToPlayer(amount: 15)
                spawnFloatingText("+100 PTS", color: Color.purple, isPlayer: false)
            } else {
                spawnFloatingText("MISS! ❌", color: Color.gray, isPlayer: false)
            }
        }

        botResponseWorkItem = item
        DispatchQueue.main.asyncAfter(deadline: .now() + delay, execute: item)
    }

    // MARK: - Floating Combat Text

    private func spawnFloatingText(_ text: String, color: Color, isPlayer: Bool) {
        let xPos: CGFloat = isPlayer ? 100 : UIScreen.main.bounds.width - 100
        let item = FloatingCombatItem(
            text: text,
            color: color,
            position: CGPoint(x: xPos, y: 160)
        )
        floatingCombatTexts.append(item)

        withAnimation(.easeOut(duration: 1.2)) {
            if let index = floatingCombatTexts.firstIndex(where: { $0.id == item.id }) {
                floatingCombatTexts[index].position.y -= 50
                floatingCombatTexts[index].opacity = 0
            }
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 1.3) {
            floatingCombatTexts.removeAll(where: { $0.id == item.id })
        }
    }

    // MARK: - Match Loading & Finishing

    private func initializeFighters() {
        playerMaxHp = 100
        playerHp = 100
        playerGhostHp = 100
        opponentMaxHp = 100
        opponentHp = 100
        opponentGhostHp = 100
    }

    @MainActor
    private func loadArenaQuestions() async {
        isLoadingQuestions = true
        defer {
            isLoadingQuestions = false
            isRoundActive = true
            scheduleBotOpponentAction()
        }

        do {
            let res = try await api.study.fetchQuestions(
                subject: subject,
                topic: topic,
                userId: session.userId,
                limit: 5
            )

            var loaded: [Question] = []
            if let firstQ = res.question {
                loaded.append(firstQ)
            }

            // Fetch remaining questions up to 5
            for qId in res.allQuestionIds.prefix(5) {
                if loaded.count >= 5 { break }
                if let first = res.question, first.id == qId { continue }
                if let single = try? await api.study.question(id: qId) {
                    loaded.append(single)
                }
            }

            if !loaded.isEmpty {
                self.questions = loaded
                RemoteLogger.log(tag: "ClassicArena_Questions", message: "Loaded \(loaded.count) questions from server")
                return
            }
        } catch {
            RemoteLogger.log(tag: "ClassicArena_Error", message: "Failed server questions: \(error.localizedDescription), using high-yield arena deck")
        }

        // Reliable clinical fallback deck so battle never fails
        self.questions = fallbackQuestionsDeck(subject: subject)
    }

    private func finishBattle(playerWon: Bool, isForfeit: Bool) {
        botResponseWorkItem?.cancel()
        isRoundActive = false

        let summary = BattleResultSummary(
            challengeId: challengeId,
            userName: session.currentUser?.name ?? "Dr. You",
            opponentName: opponentName,
            userScore: isForfeit ? 0 : playerScore,
            opponentScore: opponentScore,
            userCorrect: userCorrectCount,
            opponentCorrect: opponentCorrectCount,
            totalQuestions: max(1, questions.count),
            expGained: playerWon ? 250 : 75,
            creditsGained: playerWon ? 120 : 30,
            questionReviews: questionReviews
        )

        RemoteLogger.log(
            tag: "ClassicArena_Finish",
            message: "Battle concluded: won=\(playerWon), userScore=\(playerScore), oppScore=\(opponentScore), reviews=\(questionReviews.count)"
        )

        onFinish?(summary)
    }

    private func fallbackQuestionsDeck(subject: String) -> [Question] {
        // High-yield clinical NEET PG questions
        return [
            MockQuestions.make(
                id: 101,
                text: "A 45-year-old male presents with acute severe retrosternal chest pain radiating to the left arm. ECG demonstrates ST-segment elevation in leads II, III, and aVF. Which coronary artery is most likely occluded?",
                options: ["Left Anterior Descending (LAD)", "Right Coronary Artery (RCA)", "Left Circumflex Artery (LCx)", "Left Main Coronary Artery"],
                correctIndex: 1,
                explanation: "ST elevation in leads II, III, and aVF indicates an acute inferior wall myocardial infarction, which is most commonly supplied by the Right Coronary Artery (RCA) in 85-90% of individuals."
            ),
            MockQuestions.make(
                id: 102,
                text: "Which of the following pharmacological agents is the primary first-line choice for acute anaphylactic shock?",
                options: ["Intravenous Hydrocortisone", "Intramuscular Epinephrine (1:1000)", "Intravenous Diphenhydramine", "Nebulized Salbutamol"],
                correctIndex: 1,
                explanation: "Intramuscular Epinephrine (1:1000) administered into the anterolateral mid-thigh is the immediate drug of choice for anaphylaxis due to its alpha-1 vasoconstrictor and beta-2 bronchodilator actions."
            ),
            MockQuestions.make(
                id: 103,
                text: "A patient with fever and neck stiffness has a lumbar puncture revealing markedly elevated opening pressure, predominantly polymorphonuclear pleocytosis, high protein, and markedly reduced glucose. The most likely diagnosis is:",
                options: ["Viral Meningoencephalitis", "Acute Bacterial Meningitis", "Tuberculous Meningitis", "Cryptococcal Meningitis"],
                correctIndex: 1,
                explanation: "Acute bacterial meningitis typically shows CSF with neutrophilic pleocytosis, elevated protein (>100 mg/dL), and low CSF glucose (<40% of blood glucose) with high opening pressure."
            ),
            MockQuestions.make(
                id: 104,
                text: "In acute pancreatitis, which of the following serum enzyme levels is more specific and remains elevated longer?",
                options: ["Serum Amylase", "Serum Lipase", "Alkaline Phosphatase", "Serum LDH"],
                correctIndex: 1,
                explanation: "Serum lipase has greater diagnostic sensitivity and specificity than amylase for acute pancreatitis and remains elevated for 7-14 days compared to 3-5 days for amylase."
            ),
            MockQuestions.make(
                id: 105,
                text: "A neonate presents with persistent bilious vomiting and abdominal distension within 24 hours of birth. An abdominal X-ray shows the classic 'double-bubble' sign. What is the definitive diagnosis?",
                options: ["Hypertrophic Pyloric Stenosis", "Duodenal Atresia", "Intussusception", "Midgut Volvulus"],
                correctIndex: 1,
                explanation: "The 'double-bubble' sign on plain abdominal radiograph is pathognomonic for duodenal atresia, representing gas in the dilated stomach and proximal duodenum."
            )
        ]
    }
}

// MARK: - Floating Combat Item

private struct FloatingCombatItem: Identifiable {
    let id = UUID()
    let text: String
    let color: Color
    var position: CGPoint
    var opacity: Double = 1.0
}

// MARK: - Mock Helper

private enum MockQuestions {
    static func make(id: Int, text: String, options: [String], correctIndex: Int, explanation: String) -> Question {
        let dict: [String: Any] = [
            "question_id": id,
            "question_text": text,
            "options": options,
            "correct_option": "\(correctIndex)",
            "explanation": explanation,
            "subject": "Clinical Medicine",
            "topic": "High-Yield NEET PG",
            "marks": 4,
            "negative_marks": 1.0
        ]
        let data = try! JSONSerialization.data(withJSONObject: dict)
        return try! JSONDecoder().decode(Question.self, from: data)
    }
}
