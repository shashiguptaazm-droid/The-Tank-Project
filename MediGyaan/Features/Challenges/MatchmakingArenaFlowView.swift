import SwiftUI

/// Complete end-to-end matchmaking flow orchestrator replicating Android's
/// `MatchmakingActivity.kt` -> `TopicLoadingActivity.kt` -> `ClassicGameActivity.kt` -> `ChallengeResultActivity.kt`.
///
/// Seamlessly navigates across four stages:
/// 1. `.searching`: Real-time radar queue with 30s countdown and bot fallback matching (`MatchmakingActivityView`).
/// 2. `.versus`: Split-screen 1v1 Showdown Staging Screen with 3D hero zoom controls (`LoadingActivityView`).
/// 3. `.battle`: Live 1v1 Combat Arena Duel (`ClassicGameActivityView`) with dual HP bars, powers, and bot AI.
/// 4. `.result`: Battle results screen (`ChallengeResultView`) with scoreboard and question review.
struct MatchmakingArenaFlowView: View {

    var subject: String = "NEET PG"
    var topic: String? = nil
    var battleStyle: BattleStyle = .subjectTest

    @EnvironmentObject private var session: SessionStore
    @Environment(\.dismiss) private var dismiss
    @AppStorage("selectedAvatarId") private var selectedAvatarId: Int = 1

    enum BattleStyle {
        case subjectTest   // 15-question subject duel replicating SubjectTestActivity.kt
        case classicArena  // endless arena combat replicating ClassicGameActivity.kt
    }

    enum ArenaStage {
        case searching
        case versus
        case battle
        case result
    }

    @State private var currentStage: ArenaStage = .searching

    // ─── Matchmaking State ────────────────────────────────────────────────────
    @State private var matchedOpponentName: String = "Dr. Vihaan"
    @State private var matchedOpponentRank: String = "Warrior"
    @State private var matchedOpponentWarrior: Warrior = Warrior.all.randomElement()!
    @State private var userWarrior: Warrior = Warrior.all.first!
    @State private var challengeId: String = ""
    @State private var opponentId: String = ""
    @State private var isHost: Bool = false
    @State private var isBotMatch: Bool = false
    @State private var sharedQuestionIds: [Int] = []

    // ─── Result State ─────────────────────────────────────────────────────────
    @State private var battleResult: BattleResultSummary? = nil

    var body: some View {
        ZStack {
            switch currentStage {
            case .searching:
                MatchmakingActivityView(subject: subject, topic: topic) { chId, isH, isBot, oppId, oppName, qIds in
                    self.challengeId = chId
                    self.isHost = isH
                    self.isBotMatch = isBot
                    self.opponentId = oppId
                    self.matchedOpponentName = oppName
                    self.matchedOpponentWarrior = Warrior.all.randomElement()!
                    self.sharedQuestionIds = qIds

                    RemoteLogger.log(
                        tag: "ArenaFlow_Matched",
                        message: "Match ready! Transitioning to loading faceoff. Opponent=\(oppName)"
                    )

                    withAnimation {
                        self.currentStage = .versus
                    }
                }

            case .versus:
                LoadingActivityView(
                    challengeId: challengeId,
                    userId: String(session.currentUser?.id ?? 0),
                    userName: session.currentUser?.name ?? "Dr. Aspirant",
                    opponentId: opponentId,
                    opponentName: matchedOpponentName,
                    subject: subject,
                    topic: topic,
                    isHost: isHost,
                    isBotMatch: isBotMatch,
                    questionIds: sharedQuestionIds
                ) {
                    RemoteLogger.log(
                        tag: "ArenaFlow_BattleStart",
                        message: "Faceoff complete! Entering Classic Battle Arena."
                    )
                    withAnimation {
                        self.currentStage = .battle
                    }
                }

            case .battle:
                if battleStyle == .subjectTest {
                    SubjectTestActivityView(
                        subject: subject,
                        topic: topic,
                        challengeId: challengeId,
                        isChallenge: true,
                        isHost: isHost,
                        questionIdList: sharedQuestionIds,
                        userWarrior: userWarrior,
                        opponentId: opponentId,
                        opponentName: matchedOpponentName,
                        isBotMatch: isBotMatch
                    ) { result in
                        self.battleResult = result
                        withAnimation {
                            self.currentStage = .result
                        }
                    }
                } else {
                    ClassicGameActivityView(
                        challengeId: challengeId,
                        subject: subject,
                        topic: topic,
                        isHost: isHost,
                        isChallenge: true,
                        realMultiplayer: !isBotMatch,
                        opponentId: opponentId,
                        opponentName: matchedOpponentName,
                        opponentWarrior: matchedOpponentWarrior,
                        userWarrior: userWarrior
                    ) { result in
                        self.battleResult = result
                        withAnimation {
                            self.currentStage = .result
                        }
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
    }

    private func setupFighters() {
        if let w = Warrior.warrior(for: selectedAvatarId) {
            userWarrior = w
        } else {
            userWarrior = Warrior.all.first!
        }
        matchedOpponentWarrior = Warrior.all.randomElement()!
    }
}
