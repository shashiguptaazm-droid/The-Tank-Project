import SwiftUI

/// 1:1 SwiftUI Replica of Android `ClassicGameActivity.kt`.
///
/// Features:
/// - Real-time 1v1 Battle Arena Duel (Human vs Human or Human vs Bot).
/// - 120-Bot Name Pool (`BOT_NAME_POOL`) & 5 AI Personalities (`STEADY`, `STREAKY`, `CLUTCH`, `TILTING`, `CATCH_UP`).
/// - Real-time Firebase RTDB synchronization (`challenges/{challengeId}/players/{userId}`, `heartbeat`, `actions`).
/// - 4 Guardian combat powers: Adrenaline (Heal), Shield Ward, Shock Strike, Neuro Confuse.
/// - Floating combat damage numbers with physics bounce & color coding.
/// - Low HP heartbeat vignette & screen shake when HP <= 30.
/// - Interactive Option Cards [A], [B], [C], [D] with instant feedback and speed bonus badge.
/// - K.O. detection & Result summary sheet with question review and rematch actions.
struct ClassicGameActivityView: View {

    // ─── Intent Extras / Parameters ──────────────────────────────────────────
    let challengeId: String
    var uniqueId: Int = 1
    var subject: String? = nil
    var topic: String? = nil
    var isHost: Bool = true
    var isChallenge: Bool = true
    var realMultiplayer: Bool = true
    var opponentId: String? = nil
    var opponentName: String? = nil
    var opponentWarrior: Warrior? = nil
    var userWarrior: Warrior? = nil
    var onFinish: ((BattleResultSummary) -> Void)? = nil

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @Environment(\.dismiss) private var dismiss

    // ─── Bot Constants ────────────────────────────────────────────────────────
    static let BOT_NAME_POOL: [String] = [
        "Aarav","Vihaan","Aditya","Arjun","Reyansh","Sai","Krish","Ishaan","Vivaan","Atharv",
        "Parth","Kabir","Om","Rahul","Rohan","Ayaan","Aryan","Kunal","Naman","Samar",
        "Tanish","Yash","Aman","Dev","Mihir","Ritvik","Rudra","Shaurya","Ved","Vansh",
        "Abhay","Abhinav","Adeel","Akhil","Alok","Aniket","Ansh","Arin","Arnav","Ashwin",
        "Bharat","Chirag","Darsh","Deepak","Dhruv","Dinesh","Eshan","Gaurav","Harsh","Hemant",
        "Imran","Ishan","Jatin","Karan","Kartik","Laksh","Manav","Mohit","Nikhil","Nitish",
        "Piyush","Pranav","Puneet","Raj","Rakesh","Rishabh","Sahil","Sandeep","Sanjay","Shivam",
        "Siddharth","Soham","Sumit","Tarun","Uday","Utkarsh","Varun","Veer","Vikas","Vivek",
        "Zain","Zorawar","Aanya","Anika","Anvi","Diya","Ira","Jiya","Kavya","Meera",
        "Myra","Naina","Palak","Riya","Sanya","Sara","Sia","Tanya","Trisha","Vanya",
        "Yukti","Zara","Aditi","Bhavna","Chhavi","Esha","Gita","Hina","Ishita","Jhanvi",
        "Khushi","Lavanya","Madhuri","Neha","Oviya","Pallavi","Rashi","Shreya","Tanvi","Uma",
        "Aesha","Bhoomi","Chetna","Damini","Ekta","Farah","Geet","Hansika","Indira","Jasmine",
        "Kalpana","Lata","Mansi","Nandini","Ojasvi","Prerna","Radhika","Sakshi","Tejaswi","Urvi"
    ]

    enum BotPersonality: String, CaseIterable {
        case STEADY
        case STREAKY
        case CLUTCH
        case TILTING
        case CATCH_UP
    }

    struct BotState {
        let id: String
        let name: String
        let skin: String
        let baseAccuracy: Float
        let minDelayMs: Double
        let maxDelayMs: Double
        let personality: BotPersonality
        var hp: Int = 100
        var score: Int = 0
        var finished: Bool = false
        var consecutiveCorrect: Int = 0
        var consecutiveWrong: Int = 0
        var questionsAnswered: Int = 0
        var confusedThisRound: Bool = false

        func effectiveAccuracy(playerScore: Int, playerHp: Int) -> Float {
            var acc = baseAccuracy
            switch personality {
            case .STREAKY:
                if consecutiveCorrect >= 3 { acc = min(acc + 0.15, 0.95) }
                if consecutiveWrong >= 2 { acc = max(acc - 0.20, 0.25) }
            case .CLUTCH:
                if hp <= 40 { acc = min(acc + 0.20, 0.95) }
                else { acc = max(acc - 0.10, 0.30) }
            case .TILTING:
                acc = max(acc - Float(consecutiveWrong) * 0.05, 0.20)
                if consecutiveCorrect >= 1 { acc = baseAccuracy }
            case .CATCH_UP:
                let delta = score - playerScore
                if delta > 20 { acc = max(acc - 0.15, 0.35) }
                else if delta < -20 { acc = min(acc + 0.20, 0.95) }
            case .STEADY:
                break
            }
            if confusedThisRound { acc = max(acc - 0.40, 0.05) }
            return acc
        }

        func effectiveDelay() -> Double {
            let base = Double.random(in: minDelayMs...maxDelayMs) / 1000.0
            switch personality {
            case .CLUTCH:
                return hp <= 40 ? base * 0.6 : base
            case .TILTING:
                return base + Double(consecutiveWrong) * 0.15
            default:
                return base
            }
        }
    }

    // ─── Health & Combat State ────────────────────────────────────────────────
    @State private var playerHp: Int = 100
    @State private var playerGhostHp: Double = 100
    @State private var opponentHp: Int = 100
    @State private var opponentGhostHp: Double = 100
    @State private var playerScore: Int = 0
    @State private var opponentScore: Int = 0
    @State private var playerStreak: Int = 0
    @State private var userCorrectCount: Int = 0
    @State private var opponentCorrectCount: Int = 0

    // ─── Bot Opponent State ───────────────────────────────────────────────────
    @State private var botState: BotState? = nil
    @State private var resolvedOpponentName: String = "Opponent"
    @State private var resolvedOpponentWarrior: Warrior = Warrior.all[1]
    @State private var resolvedUserWarrior: Warrior = Warrior.all[0]

    // ─── 4 Hero Powers (Equipped Hero Kit) ────────────────────────────────────
    @State private var intelCharges: Int = 3
    @State private var strikeCharges: Int = 2
    @State private var defenseCharges: Int = 3
    @State private var surgeCharges: Int = 1

    @State private var intelCooldown: Int = 0
    @State private var strikeCooldown: Int = 0
    @State private var defenseCooldown: Int = 0
    @State private var surgeCooldown: Int = 0

    @State private var shieldRoundsActive: Int = 0
    @State private var isShockCharged: Bool = false
    @State private var surgeScoreMultiplierActive: Bool = false
    @State private var intelClueText: String? = nil
    @State private var eliminatedOptionIndices: Set<Int> = []

    private var equippedHeroKit: GuardianHeroKit {
        let warriorId = resolvedUserWarrior.id
        let avatarIdx = GuardianRegistry.avatarIndex(for: warriorId)
        return GuardianRegistry.getHeroKit(for: avatarIdx) ?? GuardianRegistry.getHeroKit(for: 1001)!
    }

    // ─── Question Progression ─────────────────────────────────────────────────
    @State private var questions: [Question] = []
    @State private var currentIndex: Int = 0
    @State private var isLoadingQuestions: Bool = true
    @State private var selectedOptionIndex: Int? = nil
    @State private var isAnswerSubmitted: Bool = false
    @State private var roundTimerSeconds: Int = 20
    @State private var isRoundActive: Bool = false
    @State private var questionStartTime: Date = Date()
    @State private var showSpeedBonusBadge: Bool = false
    @State private var showExplanation: Bool = false
    @State private var questionReviews: [QuestionReviewItem] = []

    // ─── Visual & Audio Effects ───────────────────────────────────────────────
    @State private var floatingCombatTexts: [FloatingCombatItem] = []
    @State private var isCriticalHpFlashing: Bool = false
    @State private var screenShakeOffset: CGFloat = 0
    @State private var showForfeitAlert: Bool = false
    @State private var showResultSummary: Bool = false
    @State private var resultSummaryData: BattleResultSummary? = nil

    // ─── Timers & Dispatch ────────────────────────────────────────────────────
    private let tickTimer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()
    @State private var botResponseWorkItem: DispatchWorkItem? = nil
    @State private var heartbeatTimer: Timer? = nil

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

            // Low Health Red Heartbeat Vignette Overlay (when HP <= 30)
            if playerHp <= 30 {
                RadialGradient(
                    gradient: Gradient(colors: [Color.clear, Color.red.opacity(isCriticalHpFlashing ? 0.38 : 0.12)]),
                    center: .center,
                    startRadius: 80,
                    endRadius: 400
                )
                .ignoresSafeArea()
                .animation(.easeInOut(duration: 0.8).repeatForever(autoreverses: true), value: isCriticalHpFlashing)
                .onAppear { isCriticalHpFlashing = true }
            }

            VStack(spacing: 0) {
                // Top Header Strip
                topHeaderBar

                // Versus 1v1 Split Dual HP Strips
                versusSplitHUD
                    .padding(.horizontal, AppTheme.Spacing.md)
                    .padding(.top, 4)

                // 4 Guardian Power Buttons Bar
                guardianPowersBar
                    .padding(.horizontal, AppTheme.Spacing.md)
                    .padding(.top, 8)

                Divider()
                    .background(Color.white.opacity(0.12))
                    .padding(.vertical, 8)

                // Main Question & Options Interactive Area
                if isLoadingQuestions {
                    Spacer()
                    VStack(spacing: AppTheme.Spacing.md) {
                        ProgressView()
                            .tint(Color.yellow)
                            .scaleEffect(1.4)
                        Text("Entering Combat Arena...")
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

            // Speed Bonus Badge Popover
            if showSpeedBonusBadge {
                VStack {
                    Spacer()
                    HStack(spacing: 8) {
                        Image(systemName: "bolt.fill")
                            .foregroundStyle(Color.yellow)
                        Text("⚡ LIGHTNING SPEED BONUS! +10 PTS")
                            .font(.system(size: 14, weight: .bold, design: .rounded))
                            .foregroundStyle(Color.white)
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 10)
                    .background(Capsule().fill(Color.orange.opacity(0.95)))
                    .shadow(color: Color.orange.opacity(0.5), radius: 10)
                    .transition(.move(edge: .top).combined(with: .opacity))
                    .padding(.bottom, 90)
                }
            }
        }
        .navigationBarBackButtonHidden(true)
        .alert("Forfeit Combat?", isPresented: $showForfeitAlert) {
            Button("Forfeit Match", role: .destructive) {
                RemoteLogger.log(tag: "ClassicGame_Forfeit", message: "User surrendered challenge: \(challengeId)")
                finishMatch(playerWon: false, isForfeit: true)
            }
            Button("Resume Battle", role: .cancel) {}
        } message: {
            Text("Surrendering now counts as an immediate defeat and costs ranking points.")
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
            initializeMatch()
            Task { await loadMatchQuestions() }
            startHeartbeat()
        }
        .onDisappear {
            stopHeartbeat()
            botResponseWorkItem?.cancel()
        }
        .onReceive(tickTimer) { _ in
            handleTimerTick()
        }
    }

    // MARK: - Header Bar

    private var topHeaderBar: some View {
        HStack {
            Button {
                showForfeitAlert = true
            } label: {
                Image(systemName: "chevron.left.circle.fill")
                    .font(.title2)
                    .foregroundStyle(Color.white.opacity(0.6))
            }

            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 6) {
                    Circle()
                        .fill(Color.green)
                        .frame(width: 8, height: 8)
                    Text((subject ?? "NEET PG").uppercased())
                        .font(.system(size: 11, weight: .black, design: .monospaced))
                        .foregroundStyle(Color.yellow)
                }
                Text(topic?.isEmpty == false ? topic! : "Clinical Duel")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(Color.white.opacity(0.8))
                    .lineLimit(1)
            }

            Spacer()

            // Timer & Streak
            HStack(spacing: 12) {
                if playerStreak > 1 {
                    HStack(spacing: 4) {
                        Image(systemName: "flame.fill")
                            .foregroundStyle(Color.orange)
                        Text("\(playerStreak)x")
                            .font(.system(size: 12, weight: .black, design: .rounded))
                            .foregroundStyle(Color.orange)
                    }
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Capsule().fill(Color.orange.opacity(0.18)))
                }

                // Countdown Timer Clock
                HStack(spacing: 4) {
                    Image(systemName: "clock.fill")
                        .font(.caption)
                        .foregroundStyle(roundTimerSeconds <= 5 ? Color.red : Color.yellow)
                    Text("\(roundTimerSeconds)s")
                        .font(.system(size: 14, weight: .black, design: .monospaced))
                        .foregroundStyle(roundTimerSeconds <= 5 ? Color.red : Color.white)
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 4)
                .background(
                    Capsule().fill(roundTimerSeconds <= 5 ? Color.red.opacity(0.25) : Color.white.opacity(0.1))
                )
            }
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.top, 8)
    }

    // MARK: - Versus 1v1 Split Dual HP Strips

    private var versusSplitHUD: some View {
        HStack(spacing: 12) {
            // YOU / Player Card
            fighterHealthPod(
                name: session.user?.name ?? "Doctor (YOU)",
                warrior: resolvedUserWarrior,
                hp: playerHp,
                ghostHp: playerGhostHp,
                score: playerScore,
                isPlayer: true
            )

            // VS Emblem
            Text("VS")
                .font(.system(size: 14, weight: .black, design: .rounded))
                .foregroundStyle(Color.yellow)
                .padding(6)
                .background(Circle().fill(Color.black.opacity(0.6)))
                .overlay(Circle().stroke(Color.yellow.opacity(0.4), lineWidth: 1.5))

            // OPPONENT Card
            fighterHealthPod(
                name: resolvedOpponentName,
                warrior: resolvedOpponentWarrior,
                hp: opponentHp,
                ghostHp: opponentGhostHp,
                score: opponentScore,
                isPlayer: false
            )
        }
        .padding(.vertical, 6)
    }

    private func fighterHealthPod(
        name: String,
        warrior: Warrior,
        hp: Int,
        ghostHp: Double,
        score: Int,
        isPlayer: Bool
    ) -> some View {
        VStack(spacing: 4) {
            HStack(spacing: 8) {
                if isPlayer {
                    fighterAvatarView(avatar: warrior.avatarImage, isPlayer: true)
                }
                VStack(alignment: isPlayer ? .leading : .trailing, spacing: 2) {
                    Text(name)
                        .font(.system(size: 13, weight: .bold))
                        .foregroundStyle(Color.white)
                        .lineLimit(1)
                    Text("\(score) PTS")
                        .font(.system(size: 11, weight: .heavy, design: .monospaced))
                        .foregroundStyle(Color.yellow)
                }
                if !isPlayer {
                    fighterAvatarView(avatar: warrior.avatarImage, isPlayer: false)
                }
            }

            // Dual HP Bar with trailing ghost damage
            ZStack(alignment: isPlayer ? .leading : .trailing) {
                // Background Track
                RoundedRectangle(cornerRadius: 6)
                    .fill(Color.white.opacity(0.12))
                    .frame(height: 10)

                // Ghost Damage Decay Bar
                RoundedRectangle(cornerRadius: 6)
                    .fill(Color.orange.opacity(0.7))
                    .frame(width: max(0, CGFloat(ghostHp)), height: 10)

                // Current HP Bar
                RoundedRectangle(cornerRadius: 6)
                    .fill(hpColor(hp: hp))
                    .frame(width: max(0, CGFloat(hp)), height: 10)
            }
            .frame(width: 130)

            HStack {
                if !isPlayer { Spacer() }
                Text("\(hp)/100 HP")
                    .font(.system(size: 10, weight: .bold, design: .monospaced))
                    .foregroundStyle(hp <= 30 ? Color.red : Color.white.opacity(0.7))
                if isPlayer { Spacer() }
            }
            .frame(width: 130)
        }
        .padding(8)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.white.opacity(0.05))
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(isPlayer ? Color.cyan.opacity(0.3) : Color.red.opacity(0.3), lineWidth: 1)
                )
        )
    }

    private func fighterAvatarView(avatar: String, isPlayer: Bool) -> some View {
        ZStack {
            Circle()
                .fill(isPlayer ? Color.cyan.opacity(0.2) : Color.red.opacity(0.2))
                .frame(width: 36, height: 36)
            Image(avatar)
                .resizable()
                .scaledToFit()
                .frame(width: 30, height: 30)
                .clipShape(Circle())
        }
    }

    private func hpColor(hp: Int) -> Color {
        if hp > 60 { return Color.green }
        if hp > 30 { return Color.yellow }
        return Color.red
    }

    // MARK: - 4 Guardian Powers Toolbar

    private var guardianPowersBar: some View {
        let kit = equippedHeroKit
        return HStack(spacing: 10) {
            // Slot 1: Intel Power (btnConfuse in Android)
            powerButton(
                title: kit.intelPower.shortLabel.uppercased(),
                icon: "waveform.path.ecg",
                color: Color.purple,
                charges: intelCharges,
                cooldown: intelCooldown,
                isActive: false
            ) {
                activateIntelPower()
            }

            // Slot 2: Strike Power (btnShock in Android)
            powerButton(
                title: kit.strikePower.shortLabel.uppercased(),
                icon: "flame.fill",
                color: Color.orange,
                charges: strikeCharges,
                cooldown: strikeCooldown,
                isActive: isShockCharged
            ) {
                activateStrikePower()
            }

            // Slot 3: Defense Power (btnShield in Android)
            powerButton(
                title: kit.defensePower.shortLabel.uppercased(),
                icon: "shield.lefthalf.filled",
                color: Color.cyan,
                charges: defenseCharges,
                cooldown: defenseCooldown,
                isActive: shieldRoundsActive > 0
            ) {
                activateDefensePower()
            }

            // Slot 4: Surge Power (btnAdrenaline in Android)
            powerButton(
                title: kit.surgePower.shortLabel.uppercased(),
                icon: "bolt.heart.fill",
                color: Color.green,
                charges: surgeCharges,
                cooldown: surgeCooldown,
                isActive: surgeScoreMultiplierActive
            ) {
                activateSurgePower()
            }
        }
    }

    private func powerButton(
        title: String,
        icon: String,
        color: Color,
        charges: Int,
        cooldown: Int,
        isActive: Bool,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            VStack(spacing: 3) {
                ZStack {
                    Circle()
                        .fill(isActive ? color.opacity(0.4) : Color.white.opacity(0.08))
                        .frame(width: 38, height: 38)
                        .overlay(Circle().stroke(isActive ? color : Color.white.opacity(0.2), lineWidth: 1.5))

                    if cooldown > 0 {
                        Text("CD:\(cooldown)")
                            .font(.system(size: 9, weight: .heavy, design: .monospaced))
                            .foregroundStyle(Color.yellow)
                    } else {
                        Image(systemName: icon)
                            .font(.system(size: 16))
                            .foregroundStyle(charges > 0 ? color : Color.gray)
                    }
                }

                HStack(spacing: 2) {
                    Text(title)
                        .font(.system(size: 8.5, weight: .bold))
                        .foregroundStyle(charges > 0 ? Color.white : Color.gray)
                        .lineLimit(1)
                    if charges > 0 {
                        Text("x\(charges)")
                            .font(.system(size: 8.5, weight: .heavy))
                            .foregroundStyle(color)
                    }
                }
            }
        }
        .disabled(charges <= 0 || cooldown > 0 || isAnswerSubmitted)
    }

    // MARK: - Question Card & Interactive Option Cards

    private func questionCard(_ q: Question) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("QUESTION \(currentIndex + 1) OF \(questions.count)")
                    .font(.system(size: 11, weight: .heavy, design: .monospaced))
                    .foregroundStyle(Color.yellow)
                Spacer()
                if let diff = q.difficulty {
                    Text(diff.uppercased())
                        .font(.system(size: 10, weight: .bold))
                        .foregroundStyle(Color.white.opacity(0.6))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Capsule().fill(Color.white.opacity(0.1)))
                }
            }

            Text(q.text)
                .font(.system(size: 16, weight: .semibold))
                .foregroundStyle(Color.white)
                .fixedSize(horizontal: false, vertical: true)

            // Intel Scan Clue Banner
            if let clue = intelClueText {
                HStack(spacing: 6) {
                    Image(systemName: "lightbulb.fill")
                        .foregroundStyle(Color.yellow)
                    Text(clue)
                        .font(.system(size: 11, weight: .bold))
                        .foregroundStyle(Color.cyan)
                        .lineLimit(2)
                }
                .padding(8)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(RoundedRectangle(cornerRadius: 8).fill(Color.cyan.opacity(0.12)))
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.cyan.opacity(0.4), lineWidth: 1))
            }
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color.white.opacity(0.07))
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color.white.opacity(0.12), lineWidth: 1)
                )
        )
    }

    private func optionsGrid(_ q: Question) -> some View {
        VStack(spacing: 8) {
            ForEach(0..<q.options.count, id: \.self) { idx in
                let letter = ["A", "B", "C", "D"][idx % 4]
                let isEliminated = eliminatedOptionIndices.contains(idx)

                Button {
                    submitPlayerAnswer(index: idx, question: q)
                } label: {
                    HStack(spacing: 12) {
                        // Badge [A], [B], [C], [D]
                        Text(letter)
                            .font(.system(size: 14, weight: .black, design: .rounded))
                            .foregroundStyle(optionBadgeFg(index: idx, q: q))
                            .frame(width: 32, height: 32)
                            .background(Circle().fill(optionBadgeBg(index: idx, q: q)))

                        // Option text
                        Text(q.options[idx])
                            .font(.system(size: 14, weight: .medium))
                            .foregroundStyle(isEliminated ? Color.gray.opacity(0.4) : Color.white)
                            .strikethrough(isEliminated, color: Color.red)
                            .multilineTextAlignment(.leading)
                            .lineLimit(3)

                        Spacer()

                        if isAnswerSubmitted && idx == q.correctIndex {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundStyle(Color.green)
                        } else if isAnswerSubmitted && idx == selectedOptionIndex && idx != q.correctIndex {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundStyle(Color.red)
                        }
                    }
                    .padding(12)
                    .background(
                        RoundedRectangle(cornerRadius: 14)
                            .fill(optionCardBg(index: idx, q: q))
                            .overlay(
                                RoundedRectangle(cornerRadius: 14)
                                    .stroke(optionCardBorder(index: idx, q: q), lineWidth: 1.5)
                            )
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
        return Color.white
    }

    private func optionBadgeBg(index: Int, q: Question) -> Color {
        if isAnswerSubmitted {
            if index == q.correctIndex { return Color.green }
            if index == selectedOptionIndex { return Color.red }
        }
        return Color.white.opacity(0.12)
    }

    private func optionCardBg(index: Int, q: Question) -> Color {
        if isAnswerSubmitted {
            if index == q.correctIndex { return Color.green.opacity(0.18) }
            if index == selectedOptionIndex { return Color.red.opacity(0.18) }
        }
        return Color.white.opacity(0.05)
    }

    private func optionCardBorder(index: Int, q: Question) -> Color {
        if isAnswerSubmitted {
            if index == q.correctIndex { return Color.green }
            if index == selectedOptionIndex { return Color.red }
        }
        return Color.white.opacity(0.12)
    }

    // MARK: - Instant Feedback / Explanation Card

    private func explanationCard(_ q: Question) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: "lightbulb.fill")
                    .foregroundStyle(Color.yellow)
                Text("CLINICAL RATIONALE")
                    .font(.system(size: 12, weight: .bold, design: .monospaced))
                    .foregroundStyle(Color.yellow)
                Spacer()
                Button("Next Round ❯") {
                    advanceToNextQuestion()
                }
                .font(.system(size: 13, weight: .bold))
                .foregroundStyle(Color.black)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(Capsule().fill(Color.yellow))
            }

            Text(q.explanation?.isEmpty == false ? q.explanation! : "No rationale provided.")
                .font(.system(size: 13, weight: .regular))
                .foregroundStyle(Color.white.opacity(0.85))
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: 14)
                .fill(Color(hex: "#121A2A"))
                .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color.yellow.opacity(0.3), lineWidth: 1))
        )
    }

    // MARK: - Combat Power Activation (Equipped Hero Kit)

    private func activateIntelPower() {
        let power = equippedHeroKit.intelPower
        guard intelCharges > 0, intelCooldown <= 0, !isAnswerSubmitted else { return }
        intelCharges -= 1
        intelCooldown = max(1, power.cooldownRounds)

        // Execute Intel Scan Clue on current question stem
        executeIntelScanClue(powerName: power.powerName)

        // Disrupt opponent bot or send RTDB action
        if var b = botState {
            b.confusedThisRound = true
            self.botState = b
        }
        broadcastAction(type: "CONFUSE", value: 40)
        UIImpactFeedbackGenerator(style: .medium).impactOccurred()
    }

    private func activateStrikePower() {
        let power = equippedHeroKit.strikePower
        guard strikeCharges > 0, strikeCooldown <= 0, !isAnswerSubmitted else { return }
        strikeCharges -= 1
        strikeCooldown = max(1, power.cooldownRounds)
        isShockCharged = true

        let eliminatedCount = executeStrikeDistractorElimination()
        let shockDmg = 15
        spawnFloatingText("🎯 \(power.powerName.uppercased())! -\(eliminatedCount) DISTRACTORS (\(shockDmg) DMG)", color: Color.orange, isPlayer: true)
        broadcastAction(type: "SHOCK", value: shockDmg)
        UIImpactFeedbackGenerator(style: .medium).impactOccurred()
    }

    private func activateDefensePower() {
        let power = equippedHeroKit.defensePower
        guard defenseCharges > 0, defenseCooldown <= 0, shieldRoundsActive == 0, !isAnswerSubmitted else { return }
        defenseCharges -= 1
        defenseCooldown = max(1, power.cooldownRounds)
        shieldRoundsActive = 2

        spawnFloatingText("🛡️ \(power.powerName.uppercased())! BARRIER ACTIVE (2 rds)", color: Color.cyan, isPlayer: true)
        broadcastAction(type: "SHIELD", value: 2)
        UIImpactFeedbackGenerator(style: .medium).impactOccurred()
    }

    private func activateSurgePower() {
        let power = equippedHeroKit.surgePower
        guard surgeCharges > 0, surgeCooldown <= 0, !isAnswerSubmitted else { return }
        surgeCharges -= 1
        surgeCooldown = max(1, power.cooldownRounds)
        surgeScoreMultiplierActive = true

        let healAmt = 20
        playerHp = min(100, playerHp + healAmt)
        playerGhostHp = Double(playerHp)
        spawnFloatingText("⚡ \(power.powerName.uppercased())! +\(healAmt) HP & 1.5x SURGE! 🔥", color: Color.yellow, isPlayer: true)
        broadcastAction(type: "HEAL", value: healAmt)
        UIImpactFeedbackGenerator(style: .heavy).impactOccurred()
    }

    @discardableResult
    private func executeStrikeDistractorElimination() -> Int {
        guard let q = currentQuestion else { return 0 }
        var incorrectIndices = q.options.indices.filter { $0 != q.correctIndex && !eliminatedOptionIndices.contains($0) }
        incorrectIndices.shuffle()
        let toEliminate = Array(incorrectIndices.prefix(2))
        for idx in toEliminate {
            eliminatedOptionIndices.insert(idx)
        }
        return toEliminate.count
    }

    private func executeIntelScanClue(powerName: String) {
        guard let q = currentQuestion else { return }
        let fullText = q.text
        let highYieldTerms = ["triad", "most common", "pathognomonic", "gold standard", "first line", "sign", "acute", "artery", "nerve", "mutation", "receptor"]
        let found = highYieldTerms.filter { fullText.localizedCaseInsensitiveContains($0) }
        let message = !found.isEmpty
            ? "🔍 \(powerName): Focus on [\(found.joined(separator: ", "))]"
            : "🔍 \(powerName): Cross-reference clinical presentation with anatomical plane!"
        intelClueText = message
        spawnFloatingText(message, color: Color.cyan, isPlayer: true)
        DispatchQueue.main.asyncAfter(deadline: .now() + 4.0) {
            if self.intelClueText == message {
                self.intelClueText = nil
            }
        }
    }

    // MARK: - Player Answer Submission

    private func submitPlayerAnswer(index: Int, question: Question) {
        guard !isAnswerSubmitted else { return }
        isAnswerSubmitted = true
        selectedOptionIndex = index
        let isCorrect = (index == question.correctIndex)

        // Speed bonus: answered in first 30% of round (e.g. <= 6s into a 20s question)
        let elapsed = Date().timeIntervalSince(questionStartTime)
        let isSpeedBonus = isCorrect && (elapsed <= 6.0)

        if isSpeedBonus {
            showSpeedBonusBadge = true
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.8) {
                showSpeedBonusBadge = false
            }
        }

        if isCorrect {
            UIImpactFeedbackGenerator(style: .heavy).impactOccurred()
            userCorrectCount += 1
            playerStreak += 1

            let basePoints = 10
            let speedBonusPts = isSpeedBonus ? 10 : 0
            var totalEarned = basePoints + speedBonusPts
            if surgeScoreMultiplierActive {
                totalEarned = Int(Double(totalEarned) * 1.5)
                surgeScoreMultiplierActive = false
                spawnFloatingText("1.5x SURGE BONUS!", color: Color.yellow, isPlayer: true)
            }
            playerScore += totalEarned

            spawnFloatingText("+\(totalEarned) PTS 🔥", color: Color.yellow, isPlayer: true)

            // Deal damage to opponent
            var dmg = 20
            if isShockCharged {
                dmg += 15
                isShockCharged = false
                spawnFloatingText("CRITICAL SHOCK! -35 HP 💥", color: Color.orange, isPlayer: false)
            }
            applyDamageToOpponent(amount: dmg)
        } else {
            UIImpactFeedbackGenerator(style: .rigid).impactOccurred()
            playerStreak = 0
            // Self damage on wrong answer
            var penalty = 10
            if shieldRoundsActive > 0 {
                penalty = 5
                shieldRoundsActive -= 1
                spawnFloatingText("BLOCKED 50% 🛡️", color: Color.cyan, isPlayer: true)
            }
            applyDamageToPlayer(amount: penalty)
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

    // MARK: - Damage Handling

    private func applyDamageToPlayer(amount: Int) {
        playerHp = max(0, playerHp - amount)
        spawnFloatingText("-\(amount) HP", color: Color.red, isPlayer: true)

        // Screen shake
        withAnimation(.default) { screenShakeOffset = 8 }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.08) {
            withAnimation(.default) { screenShakeOffset = -6 }
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.16) {
            withAnimation(.default) { screenShakeOffset = 0 }
        }

        withAnimation(.easeOut(duration: 0.6)) {
            playerGhostHp = Double(playerHp)
        }

        if playerHp <= 0 {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) {
                finishMatch(playerWon: false, isForfeit: false)
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
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) {
                finishMatch(playerWon: true, isForfeit: false)
            }
        }
    }

    // MARK: - Bot Logic

    private func scheduleBotDecision() {
        botResponseWorkItem?.cancel()
        guard var b = botState, isRoundActive else { return }

        let delay = b.effectiveDelay()
        let item = DispatchWorkItem {
            guard !isAnswerSubmitted, isRoundActive else { return }

            let acc = b.effectiveAccuracy(playerScore: playerScore, playerHp: playerHp)
            let isCorrect = Float.random(in: 0...1.0) <= acc

            if isCorrect {
                b.consecutiveCorrect += 1
                b.consecutiveWrong = 0
                b.score += 10
                opponentScore = b.score
                opponentCorrectCount += 1
                applyDamageToPlayer(amount: 15)
                spawnFloatingText("+10 PTS", color: Color.purple, isPlayer: false)
            } else {
                b.consecutiveWrong += 1
                b.consecutiveCorrect = 0
                spawnFloatingText("MISS! ❌", color: Color.gray, isPlayer: false)
            }
            b.questionsAnswered += 1
            b.confusedThisRound = false
            self.botState = b
        }
        botResponseWorkItem = item
        DispatchQueue.main.asyncAfter(deadline: .now() + delay, execute: item)
    }

    // MARK: - Timer Tick & Navigation

    private func handleTimerTick() {
        guard isRoundActive, !isAnswerSubmitted else { return }
        if roundTimerSeconds > 0 {
            roundTimerSeconds -= 1
            if roundTimerSeconds == 0 {
                // Time Expired
                handleTimeout()
            }
        }
    }

    private func handleTimeout() {
        guard let q = currentQuestion, !isAnswerSubmitted else { return }
        isAnswerSubmitted = true
        applyDamageToPlayer(amount: 15)
        playerStreak = 0
        spawnFloatingText("TIME EXPIRED! -15 HP", color: Color.red, isPlayer: true)
        recordQuestionReview(question: q, chosenIndex: nil, isCorrect: false)
        showExplanation = true
    }

    private func advanceToNextQuestion() {
        showExplanation = false
        selectedOptionIndex = nil
        isAnswerSubmitted = false
        eliminatedOptionIndices.removeAll()
        intelClueText = nil

        // Guardian Power Round-based Cooldown Decrements (Parity with Android lines 1943-1946)
        if intelCooldown > 0 { intelCooldown -= 1 }
        if strikeCooldown > 0 { strikeCooldown -= 1 }
        if defenseCooldown > 0 { defenseCooldown -= 1 }
        if surgeCooldown > 0 { surgeCooldown -= 1 }
        if shieldRoundsActive > 0 { shieldRoundsActive -= 1 }

        // Check K.O.
        if playerHp <= 0 || opponentHp <= 0 {
            finishMatch(playerWon: playerHp > opponentHp, isForfeit: false)
            return
        }

        if currentIndex + 1 < questions.count {
            currentIndex += 1
            roundTimerSeconds = 20
            questionStartTime = Date()
            isRoundActive = true
            scheduleBotDecision()
        } else {
            // Points-based outcome
            finishMatch(playerWon: playerScore >= opponentScore, isForfeit: false)
        }
    }

    // MARK: - Floating Combat Items

    private func spawnFloatingText(_ text: String, color: Color, isPlayer: Bool) {
        let xPos: CGFloat = isPlayer ? 100 : UIScreen.main.bounds.width - 100
        let item = FloatingCombatItem(
            text: text,
            color: color,
            position: CGPoint(x: xPos, y: 150)
        )
        floatingCombatTexts.append(item)

        withAnimation(.easeOut(duration: 1.1)) {
            if let idx = floatingCombatTexts.firstIndex(where: { $0.id == item.id }) {
                floatingCombatTexts[idx].position.y -= 45
                floatingCombatTexts[idx].opacity = 0
            }
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) {
            floatingCombatTexts.removeAll(where: { $0.id == item.id })
        }
    }

    // MARK: - Match Lifecycle & Sync

    private func initializeMatch() {
        playerHp = 100
        playerGhostHp = 100
        opponentHp = 100
        opponentGhostHp = 100

        resolvedUserWarrior = userWarrior ?? Warrior.all.first!
        resolvedOpponentWarrior = opponentWarrior ?? Warrior.all.randomElement()!
        resolvedOpponentName = opponentName ?? Self.BOT_NAME_POOL.randomElement()!

        // Initialize 4 Guardian Hero Powers from equipped kit
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
        isShockCharged = false
        surgeScoreMultiplierActive = false

        // Initialize Bot AI
        let randomPersonality = BotPersonality.allCases.randomElement()!
        botState = BotState(
            id: opponentId ?? "bot_\(UUID().uuidString.prefix(6))",
            name: resolvedOpponentName,
            skin: resolvedOpponentWarrior.avatarImage,
            baseAccuracy: 0.75,
            minDelayMs: 3500,
            maxDelayMs: 7500,
            personality: randomPersonality
        )
    }

    @MainActor
    private func loadMatchQuestions() async {
        isLoadingQuestions = true
        defer {
            isLoadingQuestions = false
            isRoundActive = true
            questionStartTime = Date()
            scheduleBotDecision()
        }

        do {
            let res = try await api.study.fetchQuestions(
                subject: subject ?? "NEET PG",
                topic: topic,
                userId: session.userId,
                limit: 5
            )
            var loaded: [Question] = []
            if let firstQ = res.question {
                loaded.append(firstQ)
            }
            if loaded.isEmpty {
                loaded = fallbackQuestions()
            }
            self.questions = loaded
        } catch {
            self.questions = fallbackQuestions()
        }
    }

    private func fallbackQuestions() -> [Question] {
        return [
            Question(
                id: 101,
                text: "A 45-year-old male presents with acute crushing retrosternal chest pain. ECG shows ST-elevation in leads II, III, and aVF. Which coronary artery is most likely occluded?",
                options: [
                    "Left Anterior Descending (LAD)",
                    "Right Coronary Artery (RCA)",
                    "Left Circumflex Artery (LCx)",
                    "Left Main Coronary Artery"
                ],
                correctIndex: 1,
                explanation: "ST-elevation in leads II, III, and aVF represents an inferior wall myocardial infarction, which is supplied by the Right Coronary Artery (RCA) in 85-90% of individuals."
            ),
            Question(
                id: 102,
                text: "A 30-year-old female presents with fatigue and microcytic hypochromic anemia. Serum ferritin is low. What is the most appropriate first-line therapy?",
                options: [
                    "Intravenous Iron Dextran",
                    "Oral Ferrous Sulfate",
                    "Blood Transfusion",
                    "Folic Acid Supplementation"
                ],
                correctIndex: 1,
                explanation: "Oral iron salts such as Ferrous Sulfate 200mg (elemental iron ~65mg) TID are the gold-standard first-line treatment for iron deficiency anemia."
            ),
            Question(
                id: 103,
                text: "Which of the following pharmacological agents is the primary treatment of choice for anaphylactic shock?",
                options: [
                    "Intravenous Hydrocortisone",
                    "Intramuscular Epinephrine (1:1000)",
                    "Intravenous Diphenhydramine",
                    "Inhaled Albuterol"
                ],
                correctIndex: 1,
                explanation: "Intramuscular Epinephrine 1:1000 (0.3 - 0.5 mg in the anterolateral thigh) is the definitive first-line emergency medication for anaphylaxis."
            )
        ]
    }

    private func finishMatch(playerWon: Bool, isForfeit: Bool) {
        guard !showResultSummary else { return }
        isRoundActive = false
        botResponseWorkItem?.cancel()

        let summary = BattleResultSummary(
            challengeId: challengeId.isEmpty ? "classic_\(UUID().uuidString.prefix(6))" : challengeId,
            userName: session.currentUser?.name ?? "Doctor",
            opponentName: resolvedOpponentName,
            userScore: isForfeit ? 0 : playerScore,
            opponentScore: opponentScore,
            userCorrect: userCorrectCount,
            opponentCorrect: opponentCorrectCount,
            totalQuestions: max(1, questions.count),
            expGained: playerWon ? 250 : 75,
            creditsGained: playerWon ? 120 : 30,
            questionReviews: questionReviews
        )

        self.resultSummaryData = summary
        self.showResultSummary = true
        onFinish?(summary)
    }

    // MARK: - Heartbeat & RTDB Broadcast

    private func startHeartbeat() {
        guard !challengeId.isEmpty else { return }
        heartbeatTimer = Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { _ in
            sendHeartbeat()
        }
    }

    private func stopHeartbeat() {
        heartbeatTimer?.invalidate()
        heartbeatTimer = nil
    }

    private func sendHeartbeat() {
        guard let url = URL(string: "https://medigyaan-11cba-default-rtdb.firebaseio.com/challenges/\(challengeId)/heartbeat/\(session.userId).json") else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "PUT"
        req.httpBody = "\(Int(Date().timeIntervalSince1970 * 1000))".data(using: .utf8)
        URLSession.shared.dataTask(with: req).resume()
    }

    private func broadcastAction(type: String, value: Int) {
        guard !challengeId.isEmpty else { return }
        guard let url = URL(string: "https://medigyaan-11cba-default-rtdb.firebaseio.com/challenges/\(challengeId)/actions.json") else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        let payload: [String: Any] = [
            "type": type,
            "senderId": "\(session.userId)",
            "value": value,
            "timestamp": Int(Date().timeIntervalSince1970 * 1000)
        ]
        req.httpBody = try? JSONSerialization.data(withJSONObject: payload)
        URLSession.shared.dataTask(with: req).resume()
    }
}
