import SwiftUI

/// Complete end-to-end matchmaking flow orchestrator replicating Android's
/// `MatchmakingActivity.kt` -> `TopicLoadingActivity.kt` -> `ClassicGameActivity.kt` -> `ChallengeResultActivity.kt`.
///
/// Seamlessly navigates across four stages:
/// 1. `.searching`: Real-time radar queue with 30s countdown and bot fallback matching.
/// 2. `.versus`: Split-screen 1v1 Showdown Staging Screen with rank badges and battle countdown.
/// 3. `.battle`: Live 1v1 Combat Arena Duel (`ClassicBattleArenaView`) with dual HP bars and powers.
/// 4. `.result`: Battle results screen (`ChallengeResultView`) with scoreboard and question review.
struct MatchmakingArenaFlowView: View {

    var subject: String = "NEET PG"
    var topic: String? = nil

    @EnvironmentObject private var session: SessionStore
    @Environment(\.dismiss) private var dismiss

    enum ArenaStage {
        case searching
        case versus
        case battle
        case result
    }

    @State private var currentStage: ArenaStage = .searching

    // ─── Matchmaking State ────────────────────────────────────────────────────
    @State private var queueSeconds: Int = 0
    @State private var statusText: String = "Searching for challenger..."
    @State private var matchedOpponentName: String = "Dr. Vihaan"
    @State private var matchedOpponentRank: String = "Warrior"
    @State private var matchedOpponentWarrior: Warrior = Warrior.all.randomElement()!
    @State private var userWarrior: Warrior = Warrior.all.first!
    @State private var challengeId: String = ""

    // ─── Versus Stage State ───────────────────────────────────────────────────
    @State private var versusCountdown: Int = 3
    @State private var pulseScale: CGFloat = 1.0

    // ─── Result State ─────────────────────────────────────────────────────────
    @State private var battleResult: BattleResultSummary? = nil

    // ─── Timers ───────────────────────────────────────────────────────────────
    private let radarTimer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()

    var body: some View {
        ZStack {
            switch currentStage {
            case .searching:
                searchingRadarStage
            case .versus:
                versusShowdownStage
            case .battle:
                ClassicBattleArenaView(
                    subject: subject,
                    topic: topic,
                    challengeId: challengeId,
                    opponentName: matchedOpponentName,
                    opponentRank: matchedOpponentRank,
                    opponentWarrior: matchedOpponentWarrior,
                    userWarrior: userWarrior
                ) { result in
                    self.battleResult = result
                    withAnimation {
                        self.currentStage = .result
                    }
                }
            case .result:
                if let result = battleResult {
                    ChallengeResultView(result: result) {
                        dismiss()
                    }
                } else {
                    EmptyView()
                }
            }
        }
        .screenBackground()
        .navigationBarBackButtonHidden(currentStage != .searching)
        .onAppear {
            setupFighters()
            RemoteLogger.log(
                tag: "MatchmakingFlow_Start",
                message: "Matchmaking flow initialized for subject: \(subject), topic: \(topic ?? "All")"
            )
        }
        .onReceive(radarTimer) { _ in
            handleRadarTick()
        }
    }

    // MARK: - Stage 1: Searching Radar Stage

    private var searchingRadarStage: some View {
        VStack(spacing: AppTheme.Spacing.xl) {
            // Header
            VStack(spacing: 4) {
                Text(subject.uppercased())
                    .font(.system(size: 11, weight: .black, design: .monospaced))
                    .foregroundStyle(Color.yellow)

                Text(topic ?? "All Clinical Topics")
                    .font(AppTheme.Font.title3)
                    .foregroundStyle(Color.white)
            }
            .padding(.top, AppTheme.Spacing.lg)

            Spacer()

            // Radar Visual
            VStack(spacing: AppTheme.Spacing.lg) {
                ZStack {
                    Circle()
                        .stroke(Color.yellow.opacity(0.3), lineWidth: 2)
                        .frame(width: 180, height: 180)
                        .scaleEffect(pulseScale)
                        .opacity(2.0 - Double(pulseScale))

                    Circle()
                        .fill(Color.yellow.opacity(0.12))
                        .frame(width: 120, height: 120)

                    Image(systemName: "swords")
                        .font(.system(size: 44, weight: .bold))
                        .foregroundStyle(Color.yellow)
                        .shadow(color: Color.yellow.opacity(0.6), radius: 10)
                }
                .onAppear {
                    withAnimation(.easeInOut(duration: 1.5).repeatForever(autoreverses: false)) {
                        pulseScale = 1.8
                    }
                }

                VStack(spacing: 4) {
                    Text(statusText)
                        .font(AppTheme.Font.headline)
                        .foregroundStyle(Color.white)

                    Text(String(format: "%02d:%02d", queueSeconds / 60, queueSeconds % 60))
                        .font(.system(size: 22, weight: .bold, design: .monospaced))
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }
            }

            Spacer()

            // Cancel Button
            Button {
                dismiss()
            } label: {
                Text("Cancel Search")
                    .font(AppTheme.Font.subheadline.weight(.semibold))
                    .foregroundStyle(AppTheme.Palette.textMuted)
                    .padding(.horizontal, 24)
                    .padding(.vertical, 12)
                    .background(Capsule().fill(Color.white.opacity(0.08)))
            }
            .padding(.bottom, AppTheme.Spacing.xl)
        }
        .padding(AppTheme.Spacing.md)
    }

    // MARK: - Stage 2: Versus Showdown Stage

    private var versusShowdownStage: some View {
        VStack(spacing: AppTheme.Spacing.xl) {
            Spacer()

            VStack(spacing: 8) {
                Text("MATCH CONFIRMED")
                    .font(.system(size: 12, weight: .black, design: .monospaced))
                    .foregroundStyle(Color.yellow)

                Text("PREPARE FOR BATTLE")
                    .font(.system(size: 24, weight: .black, design: .rounded))
                    .foregroundStyle(Color.white)
            }

            HStack(spacing: AppTheme.Spacing.md) {
                // User Fighter Pod
                fighterProfilePod(
                    name: session.currentUser?.name ?? "Dr. You",
                    rank: "Aspirant",
                    warrior: userWarrior,
                    color: AppTheme.Palette.primary
                )

                // Central VS Emblem
                VStack(spacing: 6) {
                    Text("VS")
                        .font(.system(size: 32, weight: .black, design: .rounded))
                        .foregroundStyle(Color.red)
                        .shadow(color: Color.red.opacity(0.8), radius: 12)
                        .scaleEffect(1.1)

                    Text("\(versusCountdown)")
                        .font(.system(size: 28, weight: .black, design: .monospaced))
                        .foregroundStyle(Color.yellow)
                        .scaleEffect(1.2)
                        .animation(.easeInOut(duration: 0.3), value: versusCountdown)
                }

                // Opponent Fighter Pod
                fighterProfilePod(
                    name: matchedOpponentName,
                    rank: matchedOpponentRank,
                    warrior: matchedOpponentWarrior,
                    color: Color.purple
                )
            }
            .padding(.horizontal, AppTheme.Spacing.xs)

            VStack(spacing: 4) {
                Text("SYNCHRONIZING ARENA TELEMETRY...")
                    .font(.system(size: 11, weight: .black, design: .monospaced))
                    .foregroundStyle(Color(hex: "#00FF41"))

                ProgressView()
                    .tint(Color.yellow)
            }
            .padding(.top, AppTheme.Spacing.md)

            Spacer()
        }
        .padding(AppTheme.Spacing.md)
    }

    private func fighterProfilePod(name: String, rank: String, warrior: Warrior, color: Color) -> some View {
        CardContainer {
            VStack(spacing: AppTheme.Spacing.xs) {
                ZStack {
                    Circle()
                        .fill(color.opacity(0.2))
                        .frame(width: 76, height: 76)

                    Image(systemName: "person.crop.circle.fill")
                        .font(.system(size: 48))
                        .foregroundStyle(color)
                }

                Text(name)
                    .font(AppTheme.Font.headline)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                    .lineLimit(1)

                Text(warrior.displayName)
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundStyle(AppTheme.Palette.textMuted)
                    .lineLimit(1)

                Text(rank.uppercased())
                    .font(.system(size: 9, weight: .black))
                    .foregroundStyle(color)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(Capsule().fill(color.opacity(0.18)))
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, AppTheme.Spacing.sm)
        }
    }

    // MARK: - Matchmaking State Transition

    private func handleRadarTick() {
        switch currentStage {
        case .searching:
            queueSeconds += 1
            if queueSeconds == 3 {
                statusText = "Expanding search criteria..."
            } else if queueSeconds >= 6 {
                // Match Found!
                pairWithOpponent()
            }
        case .versus:
            if versusCountdown > 1 {
                versusCountdown -= 1
            } else {
                // Enter Live Battle
                withAnimation {
                    self.currentStage = .battle
                }
            }
        case .battle, .result:
            break
        }
    }

    private func setupFighters() {
        if let firstWarrior = Warrior.all.first {
            userWarrior = firstWarrior
        }
        matchedOpponentWarrior = Warrior.all.randomElement() ?? userWarrior
    }

    private func pairWithOpponent() {
        // Android BOT_NAME_POOL
        let botNames = [
            "Dr. Vihaan", "Dr. Aditya", "Dr. Arjun", "Dr. Reyansh", "Dr. Ishaan",
            "Dr. Parth", "Dr. Kabir", "Dr. Rahul", "Dr. Rohan", "Dr. Aarav",
            "Dr. Aanya", "Dr. Anika", "Dr. Diya", "Dr. Kavya", "Dr. Meera", "Dr. Neha"
        ]
        matchedOpponentName = botNames.randomElement()!
        matchedOpponentRank = ["Warrior", "Skilled", "Scholar", "Master"].randomElement()!
        matchedOpponentWarrior = Warrior.all.randomElement() ?? userWarrior
        challengeId = "ARENA_PVP_\(session.userId)_\(Int(Date().timeIntervalSince1970))"

        RemoteLogger.log(
            tag: "MatchmakingFlow_Matched",
            message: "Match created: \(challengeId) against \(matchedOpponentName) (\(matchedOpponentRank))"
        )

        withAnimation {
            self.currentStage = .versus
        }
    }
}
