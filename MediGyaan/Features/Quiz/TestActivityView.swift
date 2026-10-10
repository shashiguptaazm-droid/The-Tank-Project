import SwiftUI
import AVFoundation
import UIKit

// MARK: - Question presentation

/// A question as `TestActivity.displayQuestion` paints it.
///
/// Android renders four fixed `RadioButton`s (`optionA`…`optionD`), strips the
/// inline `a) b) c) d)` list off the stem, and — when the model row carries no
/// option columns — re-parses that same list back out of the stem text. This
/// type freezes the result of that cleanup once per load instead of re-running
/// two regular expressions on every SwiftUI redraw.
struct TestBattleQuestion: Identifiable {

    let id: Int
    let stem: String
    let options: [String]
    let correctIndex: Int
    let explanation: String
    let imageURL: URL?
    let topic: String
    let subject: String
    let difficulty: String

    static let letters: [String] = ["A", "B", "C", "D"]

    /// `ans` in `TestActivity.setupButtons` / `syncWithServer`.
    static func letter(for index: Int) -> String {
        letters.indices.contains(index) ? letters[index] : ""
    }

    /// Bounds-checked option text, because `options` is padded to four entries.
    func option(at index: Int) -> String {
        options.indices.contains(index) ? options[index] : ""
    }

    /// Ports the `splitRegex` in `TestActivity.displayQuestion`:
    /// `(?i)\s*[\(\[]?a[\)\].]` — everything from the first `a)`/`A]` marker on
    /// is the inline option list and is dropped from the stem.
    static func cleanStem(_ text: String) -> String {
        guard let regex = try? NSRegularExpression(pattern: #"(?i)\s*[\(\[]?[aA][\)\].]"#) else {
            return text
        }
        let ns = text as NSString
        let full = NSRange(location: 0, length: ns.length)
        guard let match = regex.firstMatch(in: text, range: full),
              match.range.location != NSNotFound else { return text }
        return ns.substring(to: match.range.location)
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// Ports the `extractRegex` fallback in `TestActivity.displayQuestion`:
    /// `(?is)a[\)\].]\s*(.*?)\s*b[\)\].]\s*(.*?)\s*c[\)\].]\s*(.*?)\s*d[\)\].]\s*(.*)`.
    static func parseOptions(from text: String) -> [String] {
        let pattern = #"(?is)a[\)\].]\s*(.*?)\s*b[\)\].]\s*(.*?)\s*c[\)\].]\s*(.*?)\s*d[\)\].]\s*(.*)"#
        guard let regex = try? NSRegularExpression(pattern: pattern) else { return [] }
        let ns = text as NSString
        let full = NSRange(location: 0, length: ns.length)
        guard let match = regex.firstMatch(in: text, range: full), match.numberOfRanges > 4 else {
            return []
        }
        return (1...4).map { group in
            let range = match.range(at: group)
            guard range.location != NSNotFound else { return "" }
            return ns.substring(with: range).trimmingCharacters(in: .whitespacesAndNewlines)
        }
    }

    /// Kotlin only ever has four option columns, so the index is clamped to the
    /// `A`…`D` window the layout actually draws.
    init(_ question: Question) {
        let raw = question.text.trimmingCharacters(in: .whitespacesAndNewlines)
        let trimmed = question.options
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty && $0.lowercased() != "null" }

        let resolved: [String]
        if trimmed.isEmpty {
            resolved = TestBattleQuestion.parseOptions(from: raw)
        } else {
            resolved = trimmed
        }

        var padded = resolved
        while padded.count < 4 { padded.append("") }

        id = question.id
        stem = TestBattleQuestion.cleanStem(raw)
        options = Array(padded.prefix(4))
        correctIndex = min(max(question.correctIndex, 0), 3)
        explanation = question.explanation
        imageURL = question.imageURL
        topic = question.topic
        subject = question.subject
        difficulty = question.difficulty
    }
}

// MARK: - Power-ups

/// Ports the four power buttons wired in `TestActivity.setupPowerButtons`:
/// `btnAdrenaline` (Surge, +15 HP), `btnShield` (Defense, 2 protected hits),
/// `btnShock` (Strike, one distractor removed + 2× damage) and `btnConfuse`
/// (Intel, rival scan / distractor reveal).
enum TestPowerSlot: String, CaseIterable, Identifiable {
    case surge
    case defense
    case strike
    case intel

    var id: String { rawValue }

    var systemImage: String {
        switch self {
        case .surge: return "heart.fill"
        case .defense: return "shield.fill"
        case .strike: return "bolt.fill"
        case .intel: return "eye.fill"
        }
    }

    var title: String {
        switch self {
        case .surge: return "Surge"
        case .defense: return "Barrier"
        case .strike: return "Strike"
        case .intel: return "Intel"
        }
    }

    var tint: Color {
        switch self {
        case .surge: return AppTheme.Palette.success
        case .defense: return AppTheme.Palette.info
        case .strike: return AppTheme.Palette.warning
        case .intel: return AppTheme.Palette.accent
        }
    }
}

// MARK: - View model

/// Ports the whole of `TestActivity`: the shared/single-player question list,
/// the countdown timer, instant feedback, the HP duel, the four Guardian powers,
/// the review JSON and the hand-off to `ChallengeResultActivity`.
///
/// **Intent mapping.** iOS links no `FirebaseDatabase`, so the Kotlin listeners
/// on `challenges/{id}/players` and `challenges/{id}/question_ids` are replaced
/// by a local duel against `opponentName`. Every other number — +4 score per
/// correct answer, 5 (or 10 charged) damage per rival, 3 self-damage, the 6-point
/// Intel scan, the 15-point Surge heal, the 15-minute / 30-minute clocks — is
/// carried over verbatim.
@MainActor
final class TestActivityViewModel: ObservableObject {

    /// `TestActivity.startTimer(15 * 60 * 1000)` in challenge mode.
    static let challengeDurationSeconds: Int = 15 * 60
    /// `TestActivity.startTimer(30 * 60 * 1000)` in the non-challenge fallback.
    static let soloDurationSeconds: Int = 30 * 60
    /// `finalIds.take(15)` / `tempIds.take(15)` in both list builders.
    static let questionCap: Int = 15
    /// `uiHandler.postDelayed({ moveNext() }, 2500)` in `showInstantFeedback`.
    static let feedbackDelayNanoseconds: UInt64 = 2_500_000_000
    /// `uiHandler.postDelayed({ checkIfEveryoneIsDone() }, 2000)`.
    static let waitingPollNanoseconds: UInt64 = 2_000_000_000
    /// `(current + 15).coerceAtMost(100)` in the Adrenaline/Surge branch.
    static let surgeHealAmount: Int = 15
    /// `damagePlayer(myUid, 3)` on a wrong answer.
    static let selfPenaltyDamage: Int = 3
    /// `damagePlayer(pid, 6)` in the Intel branch.
    static let intelDamage: Int = 6
    /// `current + 4` inside the score `Transaction.Handler`.
    static let scorePerCorrectAnswer: Int = 4

    // MARK: Session

    let quiz: Quiz
    let isChallenge: Bool
    let opponentName: String
    let challengeId: Int
    let isHost: Bool

    /// `UNIQUE_ID` from the launching intent; iOS supplies it as `quiz.id`.
    private let uniqueId: Int

    @Published private(set) var state: LoadState<[TestBattleQuestion]> = .idle
    @Published private(set) var questions: [TestBattleQuestion] = []
    @Published private(set) var currentIndex: Int = 0

    // MARK: Answer state

    @Published var selectedIndex: Int? = nil
    @Published private(set) var isAnswerLocked: Bool = false

    // MARK: Timer

    @Published private(set) var secondsRemaining: Int = 0
    @Published private(set) var isTimerRunning: Bool = false

    // MARK: Battle

    @Published private(set) var myHp: Int = 100
    @Published private(set) var opponentHp: Int = 100
    @Published private(set) var myScore: Int = 0
    @Published private(set) var combatTicker: String = "⚔️ Round ready — lock in your diagnosis."
    @Published private(set) var isWaitingForOpponents: Bool = false
    @Published private(set) var didWin: Bool = false
    @Published var isShowingResult: Bool = false
    @Published private(set) var isSpeaking: Bool = false

    // MARK: Guardian powers

    @Published private(set) var heroKit: GuardianHeroKit?
    @Published private(set) var surgeCharges: Int = 1
    @Published private(set) var defenseCharges: Int = 2
    @Published private(set) var strikeCharges: Int = 2
    @Published private(set) var intelCharges: Int = 3
    @Published private(set) var shieldRoundsActive: Int = 0
    @Published private(set) var isShockCharged: Bool = false
    @Published private(set) var strikeStatusOverride: String? = nil
    @Published private(set) var shieldStatusOverride: String? = nil
    @Published private(set) var eliminatedOptions: Set<Int> = []

    // MARK: Review & presentation

    @Published private(set) var reviewRecords: [TestQuestionReview] = []
    @Published var isPresentingReview: Bool = false
    @Published private(set) var floatingMessage: TestFloatingMessage?
    @Published private(set) var isTakingDamage: Bool = false
    @Published var alertMessage: String? = nil
    @Published private(set) var isFinished: Bool = false

    private static let heroKitSlotKey = "selected_avatar_id"
    private static let completedTestsKey = "completed_tests_set"

    private var api: MediGyaanAPI = .live
    private var userId: Int = 1
    private var opponentIsFinished: Bool = false
    private var isGameOverHandled: Bool = false
    private var isFinalizing: Bool = false
    private var advanceConsumed: Bool = false
    private var hasStarted: Bool = false

    private var timerTask: Task<Void, Never>?
    private var feedbackTask: Task<Void, Never>?
    private var waitingTask: Task<Void, Never>?
    private var impactGenerator: UIImpactFeedbackGenerator?

    init(
        quiz: Quiz,
        isChallenge: Bool,
        opponentName: String,
        challengeId: Int,
        isHost: Bool
    ) {
        self.quiz = quiz
        self.isChallenge = isChallenge
        self.opponentName = opponentName
        self.challengeId = challengeId
        self.isHost = isHost
        self.uniqueId = quiz.id

        // `GuardianRegistry.getHeroKit(AvatarManager.getSelectedAvatarIndex(this))
        //  ?: GuardianRegistry.getHeroKit(1001)`.
        let equippedIndex = GuardianRegistry.avatarIndex(
            for: max(UserDefaults.standard.integer(forKey: Self.heroKitSlotKey), 1)
        )
        let kit = GuardianRegistry.getHeroKit(for: equippedIndex)
            ?? GuardianRegistry.getHeroKit(for: 1001)
        heroKit = kit
        if let kit {
            intelCharges = kit.intelPower.chargesPerQuiz
            strikeCharges = kit.strikePower.chargesPerQuiz
            defenseCharges = kit.defensePower.chargesPerQuiz
            surgeCharges = kit.surgePower.chargesPerQuiz
        }

        secondsRemaining = isChallenge
            ? Self.challengeDurationSeconds
            : Self.soloDurationSeconds
    }

    // MARK: - Derived state

    var currentQuestion: TestBattleQuestion? {
        questions.indices.contains(currentIndex) ? questions[currentIndex] : nil
    }

    var totalQuestions: Int { questions.count }

    var isLastQuestion: Bool { currentIndex >= questions.count - 1 }

    var correctCount: Int { reviewRecords.filter(\.isCorrect).count }

    /// `String.format("%02d:%02d", mins, secs)` in `CountDownTimer.onTick`.
    var formattedTime: String {
        String(format: "%02d:%02d", secondsRemaining / 60, secondsRemaining % 60)
    }

    /// The `when { totalSecs <= 10 … <= 30 … else }` ladder in `onTick`.
    var timerTint: Color {
        if secondsRemaining <= 10 { return AppTheme.Ink.error }
        if secondsRemaining <= 30 { return AppTheme.Palette.warning }
        return AppTheme.Ink.cyan
    }

    /// `determineWinnerByPoints()`'s `(score * 10) + hp`, for the local doctor.
    var myBattlePower: Int { (myScore * 10) + myHp }

    /// `determineWinnerByPoints()`'s `(score * 10) + hp`, for the rival.
    var opponentBattlePower: Int { opponentBattlePowerValue }

    /// The rival answers at the same cadence as the local doctor, so its score
    /// tracks a comparable number of correct answers.
    private var opponentCorrectCount: Int {
        min(reviewRecords.count, Int((Double(reviewRecords.count) * 0.5).rounded(.up)))
    }

    /// Score shown on the rival's `challengeBattleHeader` row.
    var opponentScore: Int { opponentCorrectCount * Self.scorePerCorrectAnswer }

    private var opponentBattlePowerValue: Int {
        (opponentCorrectCount * Self.scorePerCorrectAnswer * 10) + opponentHp
    }

    /// `finalizeChallenge`'s `CHALLENGE_ID` extra — `"lobby_$challengeId"` when a
    /// numeric id arrived, otherwise the raw string.
    var finalChallengeID: String {
        challengeId > 0 ? "lobby_\(challengeId)" : ""
    }

    /// The `reviewJson` `JSONArray` Kotlin hands to `ChallengeResultActivity`,
    /// aliases and all.
    var reviewJSON: String {
        let payload = reviewRecords.map { record -> [String: Any] in
            var object: [String: Any] = [
                "question_id": record.questionId,
                "question": record.questionText,
                "question_text": record.questionText,
                "selected_option": record.selectedOptionLetter,
                "user_answer": record.selectedOptionLetter,
                "your_answer": record.selectedOptionLetter,
                "correct_option": record.correctOptionLetter,
                "correct_answer": record.correctOptionLetter,
                "explanation": record.explanation,
                "is_correct": record.isCorrect ? 1 : 0,
                "question_image": record.imageURL,
                "image_url": record.imageURL,
                "option_a": record.optionA,
                "option_b": record.optionB,
                "option_c": record.optionC,
                "option_d": record.optionD
            ]
            object["selected_answer_text"] = record.selectedOptionText
            object["correct_answer_text"] = record.correctOptionText
            object["score_change"] = record.isCorrect ? 1 : 0
            object["option_e"] = ""
            return object
        }
        guard let data = try? JSONSerialization.data(withJSONObject: payload, options: []),
              let json = String(data: data, encoding: .utf8) else { return "[]" }
        return json
    }

    // MARK: - Lifecycle

    /// Ports `onCreate`: read the hero kit, then either stand up the duel or the
    /// single-player fallback, and start the clock either way.
    func start(api: MediGyaanAPI, userId: Int) async {
        guard !hasStarted else { return }
        hasStarted = true
        self.api = api
        self.userId = userId
        state = .loading

        RemoteLogger.log(
            tag: "TestActivity_Init",
            message: "Loading test structure. quizId=\(uniqueId) challengeId=\(challengeId) isChallenge=\(isChallenge) userId=\(userId)"
        )

        let ids = await fetchTestStructure()
        guard !ids.isEmpty else {
            hasStarted = false
            state = .failed("No questions found")
            return
        }

        var loaded: [TestBattleQuestion] = []
        for id in ids {
            if let question = try? await api.study.question(id: id) {
                loaded.append(TestBattleQuestion(question))
            }
        }

        guard !loaded.isEmpty else {
            hasStarted = false
            state = .failed("Questions could not be loaded")
            return
        }

        questions = loaded
        currentIndex = 0
        advanceConsumed = false
        state = .loaded(loaded)
        startTimer()
    }

    /// Ports `fetchOrCreateSharedQuestionList` / `fetchQuestionListSinglePlayer`:
    /// `GET api/get_test_structure.php?unique_id=<normalizeUniqueId(UNIQUE_ID)>`,
    /// capped at 15. The Kotlin host shuffles the ids with a seed derived from
    /// `challengeId` before writing them to Firebase; iOS keeps that ordering
    /// locally so both doctors still see the same list.
    private func fetchTestStructure() async -> [Int] {
        let safeId = Self.normalizeUniqueId(uniqueId)
        guard let object = try? await HTTPClient.shared.getObject(
            .testStructure,
            query: ["unique_id": String(safeId)]
        ), let raw = object["question_ids"] as? [Any] else {
            RemoteLogger.log(tag: "TestActivity_Structure", message: "get_test_structure.php returned no question_ids")
            return []
        }

        var ids: [Int] = []
        for entry in raw {
            if let value = entry as? Int, value > 0 {
                ids.append(value)
            } else if let value = entry as? Double, value > 0 {
                ids.append(Int(value))
            } else if let text = entry as? String, let value = Int(text), value > 0 {
                ids.append(value)
            }
        }

        let capped = Array(ids.prefix(Self.questionCap))
        if isChallenge && challengeId > 0 {
            return Self.seededShuffle(capped, seed: challengeId)
        }
        return capped
    }

    /// Ports `normalizeUniqueId`: `((id % 50) + 50) % 50`, with 0 folded to 1.
    static func normalizeUniqueId(_ id: Int) -> Int {
        let safe = ((id % 50) + 50) % 50
        return safe == 0 ? 1 : safe
    }

    /// Stands in for Kotlin's `tempIds.shuffle(Random(challengeId.toLong()))`.
    private static func seededShuffle(_ values: [Int], seed: Int) -> [Int] {
        var state = UInt64(bitPattern: Int64(seed)) | 1
        var output = values
        guard output.count > 1 else { return output }
        for index in stride(from: output.count - 1, to: 0, by: -1) {
            state = state &* 6_364_136_223_846_793_005 &+ 1_442_695_040_888_963_407
            let slot = Int((state >> 33) % UInt64(index + 1))
            output.swapAt(index, slot)
        }
        return output
    }

    // MARK: - Timer

    /// Ports `startTimer(ms)`: one exam-wide `CountDownTimer`, cancelled and
    /// restarted only by a new round, whose `onFinish` finalises the test.
    private func startTimer() {
        timerTask?.cancel()
        secondsRemaining = isChallenge ? Self.challengeDurationSeconds : Self.soloDurationSeconds
        isTimerRunning = true

        timerTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 1_000_000_000)
                guard let self, !Task.isCancelled, self.isTimerRunning else { return }
                guard self.secondsRemaining > 0 else {
                    self.isTimerRunning = false
                    self.onTimerFinished()
                    return
                }
                self.secondsRemaining -= 1
                if self.secondsRemaining <= 10 { self.impact(.medium) }
            }
        }
    }

    /// Ports `CountDownTimer.onFinish` — paint `00:00`, drop the timer, finalise.
    private func onTimerFinished() {
        secondsRemaining = 0
        RemoteLogger.log(tag: "TestActivity_Timer", message: "Timer finished for quiz \(uniqueId)")
        finalize()
    }

    // MARK: - Answering

    /// Ports `onOptionCardTapped`: selection only. The lock-in happens through
    /// the submit button, exactly as Android splits them.
    func selectOption(at index: Int) {
        guard !isAnswerLocked, !isWaitingForOpponents else { return }
        guard index >= 0, index < (currentQuestion?.options.count ?? 0) else { return }
        selectedIndex = index
        impact(.light)
    }

    /// Ports the `submitBtn.setOnClickListener` body: validate, build the review
    /// object, show instant feedback, disable the button, score, then sync.
    func lockInAnswer() {
        guard !isAnswerLocked, !isWaitingForOpponents, !isFinished else { return }
        guard let question = currentQuestion, let index = selectedIndex else {
            impact(.heavy)
            return
        }

        isAnswerLocked = true
        advanceConsumed = false
        let isCorrect = index == question.correctIndex

        var record = TestQuestionReview(
            questionId: question.id,
            questionText: question.stem,
            selectedOption: index,
            correctOption: question.correctIndex,
            isCorrect: isCorrect
        )
        record.explanation = question.explanation
        record.imageURL = question.imageURL?.absoluteString ?? ""
        record.optionA = question.option(at: 0)
        record.optionB = question.option(at: 1)
        record.optionC = question.option(at: 2)
        record.optionD = question.option(at: 3)
        reviewRecords.append(record)

        RemoteLogger.log(
            tag: "TestActivity_Answer",
            message: "Q\(currentIndex + 1) locked in: \(isCorrect ? "CORRECT" : "WRONG")",
            metadata: ["qId": question.id, "isCorrect": isCorrect]
        )

        handleScoringAndDamage(isCorrect: isCorrect)
        syncAnswer(questionId: question.id, letter: TestBattleQuestion.letter(for: index))
        scheduleFeedbackAdvance()
    }

    /// Ports `uiHandler.postDelayed({ moveNext() }, 2500)` at the end of
    /// `showInstantFeedback`.
    private func scheduleFeedbackAdvance() {
        feedbackTask?.cancel()
        feedbackTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: Self.feedbackDelayNanoseconds)
            guard let self, !Task.isCancelled else { return }
            self.moveNext()
        }
    }

    /// Ports `moveNext()`.
    ///
    /// `advanceConsumed` is re-armed by ``lockInAnswer()`` rather than on arrival
    /// at the next question, so the 2.5 s feedback task and a manual "Next" tap
    /// landing in the same window cannot skip a question.
    func moveNext() {
        guard !advanceConsumed else { return }
        advanceConsumed = true
        stopSpeech()

        currentIndex += 1
        if questions.indices.contains(currentIndex) {
            selectedIndex = nil
            isAnswerLocked = false
            eliminatedOptions = []
            combatTicker = isChallenge
                ? "⚔️ Round \(currentIndex + 1) — strike hard."
                : "🩺 Question \(currentIndex + 1) of \(questions.count)."
        } else {
            finishRound()
        }
    }

    /// The tail of `moveNext()` once every question has been answered.
    private func finishRound() {
        isAnswerLocked = true
        selectedIndex = nil
        if isChallenge {
            enterWaitingState()
        } else {
            finalize()
        }
    }

    // MARK: - Scoring & damage

    /// Ports `handleScoringAndDamage(isCorrect)` verbatim: the whole block is a
    /// no-op outside challenge mode.
    private func handleScoringAndDamage(isCorrect: Bool) {
        guard isChallenge else { return }

        if isCorrect {
            myScore += Self.scorePerCorrectAnswer

            var damage = 5
            if isShockCharged {
                isShockCharged = false
                strikeStatusOverride = "USED"
                damage = 10
                combatTicker = "💥 Strike charged — \(damage) damage dealt to \(opponentName)!"
            } else {
                combatTicker = "🎯 Correct! \(damage) damage dealt to \(opponentName)!"
            }
            applyDamage(toOpponent: damage)
        } else {
            applyDamageToSelf(Self.selfPenaltyDamage)
        }
    }

    /// Ports `damagePlayer(pid, dmg)` for a rival: shielded hits only apply to the
    /// local doctor, so this is a clamped subtraction.
    private func applyDamage(toOpponent amount: Int) {
        opponentHp = max(0, opponentHp - amount)
    }

    /// Ports `damagePlayer(myUid, dmg)` including the `shieldRoundsActive > 0`
    /// absorption branch and the `tvShieldCooldown` "ACTIVE: n" / "USED" text.
    private func applyDamageToSelf(_ amount: Int) {
        if shieldRoundsActive > 0 {
            shieldRoundsActive -= 1
            shieldStatusOverride = shieldRoundsActive > 0
                ? "ACTIVE: \(shieldRoundsActive)"
                : "USED"
            combatTicker = "🛡️ Barrier absorbed the hit — \(shieldRoundsActive) protected hits left."
            return
        }
        myHp = max(0, myHp - amount)
        isTakingDamage = true
        impact(.heavy)
        combatTicker = "💥 You took \(amount) damage."
        Task { [weak self] in
            try? await Task.sleep(nanoseconds: 160_000_000)
            self?.isTakingDamage = false
        }
    }

    // MARK: - Guardian powers

    /// Ports the `btnAdrenaline` listener — Surge heals 15 HP, capped at 100.
    func usePower(_ slot: TestPowerSlot) {
        guard !isAnswerLocked, !isWaitingForOpponents else { return }
        switch slot {
        case .surge: useSurge()
        case .defense: useDefense()
        case .strike: useStrike()
        case .intel: useIntel()
        }
    }

    private func useSurge() {
        guard surgeCharges > 0 else {
            showFloating("SURGE DEPLETED", color: AppTheme.Palette.textMuted)
            return
        }
        surgeCharges -= 1
        myHp = min(100, myHp + Self.surgeHealAmount)
        let champion = heroKit?.championName ?? "Doctor"
        showFloating("+\(Self.surgeHealAmount) HP SURGE", color: AppTheme.Palette.success)
        combatTicker = "⚡ \(champion) activated Surge (+\(Self.surgeHealAmount) HP boosted)!"
    }

    private func useDefense() {
        guard defenseCharges > 0 else {
            showFloating("SHIELD DEPLETED", color: AppTheme.Palette.textMuted)
            return
        }
        defenseCharges -= 1
        shieldRoundsActive = 2
        shieldStatusOverride = nil
        let champion = heroKit?.championName ?? "Doctor"
        showFloating("BARRIER DEPLOYED", color: AppTheme.Palette.info)
        combatTicker = "🛡️ \(champion) deployed Defense Barrier (2 hits protected)!"
    }

    private func useStrike() {
        guard strikeCharges > 0 else {
            showFloating("STRIKE DEPLETED", color: AppTheme.Palette.textMuted)
            return
        }
        strikeCharges -= 1
        isShockCharged = true
        strikeStatusOverride = nil
        eliminateRandomDistractor()
        let champion = heroKit?.championName ?? "Doctor"
        showFloating("STRIKE CHARGED 2x", color: AppTheme.Palette.warning)
        combatTicker = "⚔️ \(champion) primed Strike! 1 distractor eliminated & next hit deals 2x DMG."
    }

    private func useIntel() {
        guard intelCharges > 0 else {
            showFloating("INTEL DEPLETED", color: AppTheme.Palette.textMuted)
            return
        }
        intelCharges -= 1
        if isChallenge {
            applyDamage(toOpponent: Self.intelDamage)
            showFloating("INTEL STRIKE: \(Self.intelDamage) DMG", color: AppTheme.Palette.accent)
            combatTicker = "👁️ Optical Intel scan locked onto rival (\(opponentName)) dealing \(Self.intelDamage) DMG!"
        } else {
            eliminateRandomDistractor()
            showFloating("OPTICAL SCAN", color: AppTheme.Palette.accent)
            combatTicker = "👁️ Optical Scan revealed 1 distractor!"
        }
    }

    /// Ports `executeStrikeDistractorElimination`: one randomly chosen wrong
    /// option is disabled and struck through.
    private func eliminateRandomDistractor() {
        guard let question = currentQuestion else { return }
        let wrong = (0..<question.options.count).filter { $0 != question.correctIndex }
        guard let target = wrong.randomElement() else { return }
        eliminatedOptions.insert(target)
    }

    // MARK: - Power UI state

    /// Ports `updatePowerButtonsUI`'s per-slot `text` expression.
    func cooldownLabel(for slot: TestPowerSlot) -> String {
        switch slot {
        case .surge:
            return surgeCharges > 0 ? "\(surgeCharges)x" : "0x"
        case .defense:
            if let shieldStatusOverride { return shieldStatusOverride }
            if shieldRoundsActive > 0 { return "SHIELD:\(shieldRoundsActive)" }
            return defenseCharges > 0 ? "\(defenseCharges)x" : "0x"
        case .strike:
            if let strikeStatusOverride { return strikeStatusOverride }
            if isShockCharged { return "ACTIVE" }
            return strikeCharges > 0 ? "\(strikeCharges)x" : "0x"
        case .intel:
            return intelCharges > 0 ? "\(intelCharges)x" : "0x"
        }
    }

    /// Ports `updatePowerButtonsUI`'s per-slot `isEnabled` expression.
    func isPowerEnabled(_ slot: TestPowerSlot) -> Bool {
        guard !isAnswerLocked, !isWaitingForOpponents else { return false }
        switch slot {
        case .surge: return surgeCharges > 0
        case .defense: return defenseCharges > 0 && shieldRoundsActive == 0
        case .strike: return strikeCharges > 0 && !isShockCharged
        case .intel: return intelCharges > 0
        }
    }

    // MARK: - Waiting & result

    /// Ports the tail of `moveNext()`: flag yourself finished, blank the question
    /// body, then start the two-second re-check loop.
    private func enterWaitingState() {
        isWaitingForOpponents = true
        isTimerRunning = false
        opponentIsFinished = true
        combatTicker = "⏳ Battle finished! Waiting for other doctors to complete their rounds..."

        RemoteLogger.log(tag: "TestActivity_Waiting", message: "All local questions answered; awaiting rivals")

        waitingTask?.cancel()
        waitingTask = Task { [weak self] in
            while !Task.isCancelled {
                guard let self else { return }
                // `checkIfEveryoneIsDone` polled until every player with hp > 0
                // had `isFinished`.
                if self.opponentIsFinished {
                    self.determineWinnerByPoints()
                    return
                }
                try? await Task.sleep(nanoseconds: Self.waitingPollNanoseconds)
            }
        }
    }

    /// Ports `determineWinnerByPoints()`: highest `(score * 10) + hp` wins, and a
    /// blank winner falls back to a defeat. Kotlin only *reads* `isGameOverHandled`
    /// here — ``showResult(win:)`` owns the write.
    private func determineWinnerByPoints() {
        guard !isGameOverHandled else { return }
        didWin = myBattlePower > opponentBattlePower
        showResult(win: didWin)
    }

    /// Ports `showResult(win)`: one-shot, stops the clock, raises the modal.
    private func showResult(win: Bool) {
        guard !isGameOverHandled else { return }
        isGameOverHandled = true
        didWin = win
        timerTask?.cancel()
        isTimerRunning = false
        isShowingResult = true
    }

    /// Ports `finalizeChallenge()`: detach listeners, POST the final sync, and
    /// open the result screen **whether or not the sync succeeded**.
    func finalize() {
        guard !isFinalizing else { return }
        isFinalizing = true
        isTimerRunning = false
        timerTask?.cancel()
        waitingTask?.cancel()
        feedbackTask?.cancel()
        isFinished = true
        stopSpeech()

        Task {
            await performFinalSync()
            markCompletedTests()
            isPresentingReview = true
        }
    }

    /// Ports the `finish_test` `StringRequest` in `finalizeChallenge`.
    private func performFinalSync() async {
        _ = try? await HTTPClient.shared.postObject(
            form: [
                "challenge_id": String(challengeId),
                "user_id": String(userId),
                "finish_test": "true"
            ],
            to: .syncChallenge
        )
    }

    /// Ports `syncWithServer(ans)`, fired per answer with no retry.
    private func syncAnswer(questionId: Int, letter: String) {
        Task {
            _ = try? await HTTPClient.shared.postObject(
                form: [
                    "challenge_id": String(challengeId),
                    "user_id": String(userId),
                    "question_id": String(questionId),
                    "answer": letter
                ],
                to: .syncChallenge
            )
        }
    }

    /// Feeds `TestSelectionView`'s `completed_tests_set` mirror of Android's
    /// `COMPLETED_TESTS` preference, so the grid's "Attempted" ticks update.
    private func markCompletedTests() {
        let defaults = UserDefaults.standard
        let existing = defaults.string(forKey: Self.completedTestsKey)?
            .split(separator: ",")
            .compactMap { Int($0) } ?? []
        guard !existing.contains(uniqueId) else { return }
        let merged = (existing + [uniqueId]).sorted()
        defaults.set(merged.map(String.init).joined(separator: ","), forKey: Self.completedTestsKey)
    }

    // MARK: - Speech

    private var speechSynthesizer = AVSpeechSynthesizer()

    /// Retained from the earlier port of this screen. `TestActivity` has no TTS;
    /// the reader itself ports `MCQActivity`'s audio narration.
    func toggleSpeech() {
        if isSpeaking {
            stopSpeech()
        } else if let question = currentQuestion {
            let utterance = AVSpeechUtterance(string: question.stem)
            utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
            utterance.rate = 0.48
            speechSynthesizer.speak(utterance)
            isSpeaking = true
        }
    }

    private func stopSpeech() {
        speechSynthesizer.stopSpeaking(at: .immediate)
        isSpeaking = false
    }

    // MARK: - Feedback helpers

    /// Ports `showFloatingText(text, color)` — a centred label that rises and
    /// fades over `getSystemService` free 1200 ms.
    private func showFloating(_ text: String, color: Color) {
        floatingMessage = TestFloatingMessage(id: UUID(), text: text, color: color)
        Task { [weak self] in
            try? await Task.sleep(nanoseconds: 1_200_000_000)
            self?.floatingMessage = nil
        }
    }

    /// Stands in for `GuardianPowerAnimator.performHaptic(this, category)`.
    private func impact(_ style: UIImpactFeedbackGenerator.FeedbackStyle) {
        let generator = impactGenerator ?? UIImpactFeedbackGenerator(style: style)
        impactGenerator = generator
        generator.impactOccurred(intensity: style == .heavy ? 1.0 : 0.7)
    }

    /// Ports `onDestroy`: cancel the clock and every pending handler callback.
    func cancelAll() {
        timerTask?.cancel()
        waitingTask?.cancel()
        feedbackTask?.cancel()
        isTimerRunning = false
        stopSpeech()
    }

    deinit {
        timerTask?.cancel()
        waitingTask?.cancel()
        feedbackTask?.cancel()
    }
}

/// Ports the transient `TextView` `TestActivity.showFloatingText` adds to the
/// root layout and animates upward before removing.
struct TestFloatingMessage: Equatable, Identifiable {
    let id: UUID
    let text: String
    let color: Color
}

// MARK: - Screen

/// The timed mock-test / arena-duel runner.
///
/// Ports `TestActivity` (`res/layout/activity_test_mode.xml`), including its
/// ink palette, the Guardian power row, instant grading feedback, the HP duel
/// and the hand-off to the review screen that Android reaches through
/// `ChallengeResultActivity`.
struct TestActivityView: View {

    let quiz: Quiz
    let isChallenge: Bool
    let opponentName: String
    /// Android's `CHALLENGE_ID` extra. `0` means "no challenge".
    let challengeId: Int
    /// Android's `IS_CREATOR` / `is_host` extra — the doctor who seeds the
    /// shared question order.
    let isHost: Bool
    var onFinish: (() -> Void)?

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @Environment(\.dismiss) private var dismiss

    @StateObject private var viewModel: TestActivityViewModel
    @State private var zoomImageURL: URL? = nil

    init(
        quiz: Quiz,
        isChallenge: Bool = false,
        opponentName: String = "Dr. Opponent",
        challengeId: Int = 0,
        isHost: Bool = false,
        onFinish: (() -> Void)? = nil
    ) {
        self.quiz = quiz
        self.isChallenge = isChallenge
        self.opponentName = opponentName
        self.challengeId = challengeId
        self.isHost = isHost
        self.onFinish = onFinish
        _viewModel = StateObject(
            wrappedValue: TestActivityViewModel(
                quiz: quiz,
                isChallenge: isChallenge,
                opponentName: opponentName,
                challengeId: challengeId,
                isHost: isHost
            )
        )
    }

    var body: some View {
        rootView
            .fullScreenCover(isPresented: $viewModel.isPresentingReview) {
                NavigationStack {
                    ReviewView(reviewJson: viewModel.reviewJSON)
                }
            }
    }

    private var rootView: some View {
        ZStack {
            AppTheme.Ink.background.ignoresSafeArea()

            content

            if let floating = viewModel.floatingMessage {
                TestFloatingTextView(message: floating)
                    .allowsHitTesting(false)
                    .transition(.opacity)
            }

            if viewModel.isTakingDamage {
                AppTheme.Ink.error.opacity(0.25)
                    .allowsHitTesting(false)
                    .ignoresSafeArea()
            }
        }
        .navigationBarHidden(true)
        .task {
            await viewModel.start(api: api, userId: session.userId)
        }
        .onDisappear {
            viewModel.cancelAll()
        }
        .fullScreenCover(isPresented: Binding(
            get: { zoomImageURL != nil },
            set: { if !$0 { zoomImageURL = nil } }
        )) {
            if let url = zoomImageURL {
                ZoomImageViewer(url: url)
            }
        }
        // The victory/defeat modal uses `confirmationDialog` rather than `.alert`
        // so it never collides with `errorAlert`, which is itself an `.alert`.
        .confirmationDialog(
            viewModel.didWin ? "VICTORY! 🏆" : "DEFEAT! 💀",
            isPresented: $viewModel.isShowingResult,
            titleVisibility: .visible
        ) {
            Button("View Leaderboard") { viewModel.finalize() }
        } message: {
            Text(viewModel.didWin
                 ? "You are the last doctor standing!"
                 : "You have been eliminated from the battle.")
        }
        .errorAlert(message: $viewModel.alertMessage)
    }

    // MARK: - States

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .idle, .loading:
            LoadingStateView(message: "Preparing \(quiz.title)…")

        case .failed(let message):
            ErrorStateView(message: message) {
                Task { await viewModel.start(api: api, userId: session.userId) }
            }

        case .loaded:
            examBody
        }
    }

    private var examBody: some View {
        VStack(spacing: 0) {
            headerHUD

            ScrollView {
                VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                    if isChallenge { battleHeader }
                    combatTickerView

                    if viewModel.isWaitingForOpponents {
                        waitingPanel
                    } else if let question = viewModel.currentQuestion {
                        questionCardView(question)
                        optionsListView(question)

                        if viewModel.isAnswerLocked {
                            explanationView(question)
                        }
                    }
                }
                .padding(.horizontal, AppTheme.Spacing.md)
                .padding(.vertical, AppTheme.Spacing.sm)
            }

            bottomControlsBar
        }
    }

    // MARK: - Header HUD

    private var headerHUD: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            Button {
                RemoteLogger.log(
                    tag: "TestActivity_Exit",
                    message: "User exited test \(quiz.id) at question \(viewModel.currentIndex + 1)"
                )
                viewModel.cancelAll()
                dismiss()
            } label: {
                Image(systemName: "xmark")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(AppTheme.Ink.textPrimary)
                    .padding(AppTheme.Spacing.xs)
            }

            VStack(alignment: .leading, spacing: 1) {
                Text(quiz.title.isEmpty ? "Mock Test" : quiz.title)
                    .font(AppTheme.Font.callout.weight(.bold))
                    .foregroundStyle(AppTheme.Ink.textPrimary)
                    .lineLimit(1)

                Text("Question \(min(viewModel.currentIndex + 1, max(viewModel.totalQuestions, 1))) of \(viewModel.totalQuestions)")
                    .font(AppTheme.Font.micro)
                    .foregroundStyle(AppTheme.Ink.textSecondary)
            }

            Spacer(minLength: 0)

            Button {
                viewModel.toggleSpeech()
            } label: {
                Image(systemName: viewModel.isSpeaking ? "speaker.wave.3.fill" : "speaker.wave.2")
                    .font(.system(size: 16))
                    .foregroundStyle(viewModel.isSpeaking
                                     ? AppTheme.Ink.success
                                     : AppTheme.Ink.cyan)
            }

            HStack(spacing: 4) {
                Image(systemName: "timer")
                    .font(.system(size: 11, weight: .semibold))
                Text(viewModel.formattedTime)
                    .font(.system(size: 13, weight: .bold, design: .monospaced))
            }
            .foregroundStyle(viewModel.secondsRemaining <= 10 ? .white : AppTheme.Ink.background)
            .padding(.horizontal, 10)
            .padding(.vertical, 5)
            .background(Capsule().fill(viewModel.timerTint))
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, AppTheme.Spacing.sm)
        .background(AppTheme.Ink.surface)
    }

    // MARK: - Battle header

    /// Ports `challengeBattleHeader` plus the row `updatePlayerHealthUI` appends
    /// per Firebase player: avatar, name, rank/level, score and an HP bar.
    private var battleHeader: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            TestBattlePlayerRow(
                title: "YOU (Dr.)",
                hp: viewModel.myHp,
                score: viewModel.myScore,
                isLocalPlayer: true
            )
            TestBattlePlayerRow(
                title: opponentName,
                hp: viewModel.opponentHp,
                score: viewModel.opponentScore,
                isLocalPlayer: false
            )
        }
    }

    // MARK: - Combat ticker

    private var combatTickerView: some View {
        HStack(spacing: AppTheme.Spacing.xs) {
            Image(systemName: "bolt.horizontal.fill")
                .font(.system(size: 12, weight: .bold))
                .foregroundStyle(AppTheme.Ink.gold)
            Text(viewModel.combatTicker)
                .font(AppTheme.Font.captionBold)
                .foregroundStyle(AppTheme.Ink.textPrimary)
                .lineLimit(2)
            Spacer(minLength: 0)
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, AppTheme.Spacing.sm)
        .background(AppTheme.Ink.elevated)
        .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.sm, style: .continuous))
    }

    // MARK: - Waiting state

    private var waitingPanel: some View {
        VStack(spacing: AppTheme.Spacing.md) {
            Image(systemName: "clock.arrow.circlepath")
                .font(.system(size: 34))
                .foregroundStyle(AppTheme.Ink.gold)
            Text("Battle finished! Waiting for other doctors to complete their rounds...")
                .font(AppTheme.Font.bodyBold)
                .foregroundStyle(AppTheme.Ink.textPrimary)
                .multilineTextAlignment(.center)
        }
        .padding(AppTheme.Spacing.xl)
        .frame(maxWidth: .infinity)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AppTheme.Ink.surface)
        )
    }

    // MARK: - Question card

    private func questionCardView(_ question: TestBattleQuestion) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
            HStack(spacing: AppTheme.Spacing.xs) {
                if !question.subject.isEmpty {
                    TagBadge(text: question.subject, tint: AppTheme.Ink.cyan)
                }
                if !question.topic.isEmpty {
                    TagBadge(text: question.topic, tint: AppTheme.Ink.gold)
                }
                if !question.difficulty.isEmpty {
                    TagBadge(text: question.difficulty.uppercased(), tint: AppTheme.Ink.teal)
                }
                Spacer(minLength: 0)
            }

            Text(question.stem)
                .font(AppTheme.Font.bodyBold)
                .foregroundStyle(AppTheme.Ink.textPrimary)
                .fixedSize(horizontal: false, vertical: true)

            if let imageURL = question.imageURL {
                ZStack(alignment: .bottomTrailing) {
                    AsyncImage(url: imageURL) { phase in
                        switch phase {
                        case .success(let image):
                            image
                                .resizable()
                                .scaledToFit()
                                .frame(maxHeight: 220)
                        case .failure:
                            placeholderImage
                        case .empty:
                            ProgressView().tint(AppTheme.Ink.cyan).frame(height: 140)
                        @unknown default:
                            placeholderImage
                        }
                    }
                    .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.option, style: .continuous))

                    HStack(spacing: 3) {
                        Image(systemName: "plus.magnifyingglass")
                        Text("Tap to Zoom")
                    }
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(.white)
                    .padding(.horizontal, AppTheme.Spacing.sm)
                    .padding(.vertical, 4)
                    .background(.black.opacity(0.65))
                    .clipShape(Capsule())
                    .padding(AppTheme.Spacing.sm)
                }
                .contentShape(Rectangle())
                .onTapGesture { zoomImageURL = imageURL }
            }
        }
        .padding(AppTheme.Spacing.lg)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AppTheme.Ink.surface)
        )
    }

    private var placeholderImage: some View {
        VStack(spacing: AppTheme.Spacing.xs) {
            Image(systemName: "photo.badge.exclamationmark")
                .font(.system(size: 22))
            Text("Clinical image unavailable")
                .font(AppTheme.Font.micro)
        }
        .foregroundStyle(AppTheme.Ink.textSecondary)
        .frame(maxWidth: .infinity)
        .frame(height: 120)
    }

    // MARK: - Options

    private func optionsListView(_ question: TestBattleQuestion) -> some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            ForEach(Array(question.options.enumerated()), id: \.offset) { index, text in
                optionRow(index: index, text: text, question: question)
            }
        }
    }

    private func optionRow(index: Int, text: String, question: TestBattleQuestion) -> some View {
        let isSelected = viewModel.selectedIndex == index
        let isCorrect = viewModel.isAnswerLocked && index == question.correctIndex
        let isWrong = viewModel.isAnswerLocked && isSelected && index != question.correctIndex
        let isEliminated = viewModel.eliminatedOptions.contains(index)

        return Button {
            viewModel.selectOption(at: index)
        } label: {
            HStack(alignment: .top, spacing: AppTheme.Spacing.md) {
                Text(TestBattleQuestion.letter(for: index))
                    .font(.system(size: 13, weight: .black))
                    .foregroundStyle(badgeForeground(isSelected: isSelected, isCorrect: isCorrect, isWrong: isWrong))
                    .frame(width: 28, height: 28)
                    .background(Circle().fill(badgeBackground(isSelected: isSelected, isCorrect: isCorrect, isWrong: isWrong)))
                    .overlay(Circle().stroke(AppTheme.Ink.slate.opacity(0.55), lineWidth: 1))

                Text(text.isEmpty ? "—" : text)
                    .font(AppTheme.Font.body)
                    .foregroundStyle(isEliminated
                                     ? AppTheme.Ink.textSecondary.opacity(0.4)
                                     : AppTheme.Ink.textPrimary)
                    .multilineTextAlignment(.leading)
                    .strikethrough(isEliminated, color: AppTheme.Ink.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)

                Spacer(minLength: 0)

                if isCorrect {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(AppTheme.Ink.success)
                } else if isWrong {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(AppTheme.Ink.error)
                }
            }
            .padding(AppTheme.Spacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.option, style: .continuous)
                    .fill(optionBackground(isSelected: isSelected, isCorrect: isCorrect, isWrong: isWrong))
            )
            .overlay(
                RoundedRectangle(cornerRadius: AppTheme.Radius.option, style: .continuous)
                    .stroke(optionStroke(isSelected: isSelected, isCorrect: isCorrect, isWrong: isWrong), lineWidth: 2)
            )
            .offset(x: isWrong ? -6 : 0)
            .animation(.easeInOut(duration: 0.06), value: isWrong)
        }
        .buttonStyle(.plain)
        .disabled(viewModel.isAnswerLocked || isEliminated || viewModel.isWaitingForOpponents)
        .opacity(isEliminated ? 0.35 : 1)
    }

    private func badgeBackground(isSelected: Bool, isCorrect: Bool, isWrong: Bool) -> Color {
        if isCorrect { return AppTheme.Ink.success }
        if isWrong { return AppTheme.Ink.error }
        return isSelected ? AppTheme.Ink.cyan : AppTheme.Ink.slate.opacity(0.55)
    }

    private func badgeForeground(isSelected: Bool, isCorrect: Bool, isWrong: Bool) -> Color {
        (isSelected || isCorrect || isWrong) ? AppTheme.Ink.background : AppTheme.Ink.textSecondary
    }

    private func optionBackground(isSelected: Bool, isCorrect: Bool, isWrong: Bool) -> Color {
        if isCorrect { return AppTheme.Ink.success.opacity(0.14) }
        if isWrong { return AppTheme.Ink.error.opacity(0.14) }
        return isSelected ? AppTheme.Ink.tile : AppTheme.Ink.surface
    }

    private func optionStroke(isSelected: Bool, isCorrect: Bool, isWrong: Bool) -> Color {
        if isCorrect { return AppTheme.Ink.success }
        if isWrong { return AppTheme.Ink.error }
        return isSelected ? AppTheme.Ink.cyan : AppTheme.Ink.slate.opacity(0.55)
    }

    // MARK: - Explanation

    /// Ports `showInstantFeedback`'s `explanationText` update, including the
    /// `CORRECT!` / `INCORRECT!` prefix and the `aiMarkdownSpannable` rendering.
    private func explanationView(_ question: TestBattleQuestion) -> some View {
        let wasCorrect = isCurrentAnswerCorrect(question)
        let body = (wasCorrect ? "CORRECT!\n" : "INCORRECT!\n") + explanationBody(question)
        let tint = wasCorrect ? AppTheme.Ink.success : AppTheme.Ink.error

        return VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            Label("Clinical Rationale", systemImage: "lightbulb.fill")
                .font(AppTheme.Font.callout.weight(.bold))
                .foregroundStyle(tint)

            if let attributed = try? AttributedString(markdown: body) {
                Text(attributed)
                    .font(AppTheme.Font.body)
                    .foregroundStyle(AppTheme.Ink.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)
            } else {
                Text(body)
                    .font(AppTheme.Font.body)
                    .foregroundStyle(AppTheme.Ink.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            PrimaryButton(title: "Next Clinical Question →") {
                viewModel.moveNext()
            }
        }
        .padding(AppTheme.Spacing.lg)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AppTheme.Ink.surface)
        )
    }

    private func explanationBody(_ question: TestBattleQuestion) -> String {
        question.explanation.isEmpty
            ? "Correct option is \(TestBattleQuestion.letter(for: question.correctIndex)). Review the key diagnostic principles for this topic."
            : question.explanation
    }

    private func isCurrentAnswerCorrect(_ question: TestBattleQuestion) -> Bool {
        viewModel.selectedIndex == question.correctIndex
    }

    // MARK: - Bottom controls

    private var bottomControlsBar: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            HStack(spacing: AppTheme.Spacing.md) {
                ForEach(TestPowerSlot.allCases) { slot in
                    powerButton(slot)
                }
            }
            .padding(.horizontal, AppTheme.Spacing.md)

            if !viewModel.isAnswerLocked {
                PrimaryButton(
                    title: "LOCK IN ANSWER",
                    isEnabled: viewModel.selectedIndex != nil,
                    isSubmit: true
                ) {
                    viewModel.lockInAnswer()
                }
            }
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, AppTheme.Spacing.sm)
        .background(AppTheme.Ink.surface)
    }

    private func powerButton(_ slot: TestPowerSlot) -> some View {
        let enabled = viewModel.isPowerEnabled(slot)

        return Button {
            viewModel.usePower(slot)
        } label: {
            VStack(spacing: 3) {
                ZStack(alignment: .topTrailing) {
                    Image(systemName: slot.systemImage)
                        .font(.system(size: 17))
                        .foregroundStyle(slot.tint)
                        .frame(width: 38, height: 38)
                        .background(Circle().fill(slot.tint.opacity(0.15)))

                    Text(viewModel.cooldownLabel(for: slot))
                        .font(.system(size: 9, weight: .black))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 4)
                        .padding(.vertical, 2)
                        .background(Capsule().fill(enabled ? slot.tint : AppTheme.Palette.textMuted))
                        .offset(x: 6, y: -6)
                }

                Text(slot.title)
                    .font(.system(size: 9, weight: .bold))
                    .foregroundStyle(enabled ? AppTheme.Ink.textPrimary : AppTheme.Ink.textSecondary)
            }
        }
        .buttonStyle(.plain)
        .disabled(!enabled)
        .opacity(enabled ? 1 : 0.4)
    }
}

// MARK: - Subviews

/// One row of `challengeBattleHeader`, as built per Firebase player in
/// `TestActivity.updatePlayerHealthUI`.
private struct TestBattlePlayerRow: View {

    let title: String
    let hp: Int
    let score: Int
    let isLocalPlayer: Bool

    var body: some View {
        HStack(spacing: AppTheme.Spacing.md) {
            AvatarView(url: nil, name: title, size: 40)

            VStack(alignment: .leading, spacing: 1) {
                Text(title)
                    .font(.system(size: 13, weight: .bold))
                    .foregroundStyle(hp <= 0 ? AppTheme.Ink.error : AppTheme.Ink.textPrimary)
                    .lineLimit(1)
                Text(hp <= 0 ? "\(title) [💀 ELIMINATED]" : "Score: \(score)")
                    .font(AppTheme.Font.micro)
                    .foregroundStyle(AppTheme.Ink.textSecondary)
            }

            Spacer(minLength: 0)

            ProgressView(value: Double(max(0, hp)), total: 100)
                .tint(hp <= 0 ? AppTheme.Ink.error : (isLocalPlayer ? AppTheme.Ink.success : AppTheme.Ink.error))
                .frame(width: 110)
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, AppTheme.Spacing.sm)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.sm, style: .continuous)
                .fill(AppTheme.Ink.surface)
        )
    }
}

/// The rising damage/heal text from `TestActivity.showFloatingText`.
private struct TestFloatingTextView: View {

    let message: TestFloatingMessage

    var body: some View {
        Text(message.text)
            .font(.system(size: 22, weight: .black))
            .foregroundStyle(message.color)
            .shadow(color: .black.opacity(0.8), radius: 6)
            .transition(.opacity.combined(with: .scale(scale: 1.2)))
            .animation(.easeOut(duration: 1.2), value: message.id)
    }
}

/// The full-screen `showDiagnosticLightbox` dialog, with the pinch-zoom the
/// Android diagnostic screen reaches for.
private struct ZoomImageViewer: View {
    @Environment(\.dismiss) private var dismiss
    let url: URL

    @State private var zoom: CGFloat = 1

    var body: some View {
        ZStack(alignment: .topTrailing) {
            Color.black.ignoresSafeArea()

            AsyncImage(url: url) { phase in
                if let image = phase.image {
                    image
                        .resizable()
                        .scaledToFit()
                        .scaleEffect(zoom)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .gesture(
                            MagnificationGesture()
                                .onChanged { zoom = max(1, $0) }
                                .onEnded { _ in
                                    if zoom < 1.05 { zoom = 1 }
                                }
                        )
                        .onTapGesture(count: 2) { zoom = zoom > 1 ? 1 : 2.5 }
                } else {
                    ProgressView().tint(.white)
                }
            }

            Button {
                dismiss()
            } label: {
                Text("✕ CLOSE")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(.white)
                    .padding(.horizontal, AppTheme.Spacing.lg)
                    .padding(.vertical, AppTheme.Spacing.md)
                    .background(AppTheme.Ink.elevated.opacity(0.85))
                    .clipShape(Capsule())
                    .padding(.horizontal, AppTheme.Spacing.xl)
                    .padding(.vertical, AppTheme.Spacing.xl)
            }
        }
    }
}

// MARK: - Review struct

/// One entry of Android's `reviewJson` array, built in
/// `TestActivity.setupButtons`'s submit listener.
struct TestQuestionReview: Identifiable, Codable, Hashable {

    var id = UUID()

    let questionId: Int
    let questionText: String
    let selectedOption: Int?
    let correctOption: Int
    let isCorrect: Bool
    var explanation: String = ""
    var imageURL: String = ""
    var optionA: String = ""
    var optionB: String = ""
    var optionC: String = ""
    var optionD: String = ""

    var selectedOptionLetter: String {
        guard let selectedOption else { return "" }
        return TestBattleQuestion.letter(for: selectedOption)
    }

    var correctOptionLetter: String {
        TestBattleQuestion.letter(for: correctOption)
    }

    var selectedOptionText: String {
        guard let selectedOption, optionValues.indices.contains(selectedOption) else { return "" }
        return optionValues[selectedOption]
    }

    var correctOptionText: String {
        guard optionValues.indices.contains(correctOption) else { return "" }
        return optionValues[correctOption]
    }

    var optionValues: [String] { [optionA, optionB, optionC, optionD] }
}