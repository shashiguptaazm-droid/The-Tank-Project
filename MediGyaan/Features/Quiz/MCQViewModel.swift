import SwiftUI
import AVFoundation
import UIKit

/// Ports the four `MCQActivity` launch modes read off the `MODE` intent extra.
///
/// Kotlin branches in `onCreate` on `"SURVIVAL"`, `"KING_OF_TOPIC"`,
/// `"TODAY_CHALLENGE"` and `"CUSTOM_BATTLE"`, and derives three overlapping
/// booleans from them: `isBattleMode` (all four), `isSurvivalMode` (the first,
/// the second — which also flips `isSurvivalMode` on — and the fourth) and
/// `isKingOfTopic`. Those booleans drive the header chrome, the pool sizing,
/// the XP multipliers and the "1 mistake = elimination" rule, so the
/// distinctions are preserved rather than collapsed.
enum MCQMode: String, Hashable {

    /// No `MODE` extra — the ordinary `getQuestions.php` practice stream.
    case practice

    /// `MODE = "SURVIVAL"` — sudden death; `SELECTED_TOPIC` may be absent.
    case survival

    /// `MODE = "KING_OF_TOPIC"` — Kotlin also sets `isSurvivalMode = true`.
    case kingOfTopic

    /// `MODE = "TODAY_CHALLENGE"` — a 10-minute, 10-question sprint.
    case todayChallenge

    /// `MODE = "CUSTOM_BATTLE"` — Kotlin also sets `isSurvivalMode = true`.
    case customBattle

    /// `intent.getStringExtra("MODE")` — the Android key this enum decodes.
    static let intentExtraKey = "MODE"

    /// Mirrors the `when (mode)` chain in `MCQActivity.onCreate`.
    init(androidMode raw: String?) {
        switch raw {
        case "SURVIVAL": self = .survival
        case "KING_OF_TOPIC": self = .kingOfTopic
        case "TODAY_CHALLENGE": self = .todayChallenge
        case "CUSTOM_BATTLE": self = .customBattle
        default: self = .practice
        }
    }

    /// Kotlin: `isSurvivalMode || isKingOfTopic || isTodayChallenge`.
    var isBattleMode: Bool { self != .practice }

    /// Kotlin's `isSurvivalMode`, which `KING_OF_TOPIC` and `CUSTOM_BATTLE`
    /// also set — every one of them awards the per-round XP multiplier and
    /// ends the run on a single mistake.
    var isSurvivalMode: Bool {
        switch self {
        case .survival, .kingOfTopic, .customBattle: return true
        case .practice, .todayChallenge: return false
        }
    }

    /// Kotlin's `isKingOfTopic`, which additionally demands 200 pool questions.
    var isKingOfTopic: Bool { self == .kingOfTopic }

    /// The `&limit=` `fetchQuestion` appends to a non-specific fetch.
    var questionLimit: Int? {
        switch self {
        case .todayChallenge: return 10
        case .customBattle: return 15
        case .practice, .survival, .kingOfTopic: return nil
        }
    }

    /// `tvBattleModeBadge`. Android only ever sets these strings.
    var badge: String {
        switch self {
        case .survival: return "💀 SURVIVAL MODE"
        case .kingOfTopic: return "👑 KING OF THE TOPIC"
        case .customBattle: return "⚔️ CUSTOM BATTLE"
        case .todayChallenge: return "⏱️ TODAY'S CHALLENGE"
        case .practice: return "⚔️ BATTLE MODE"
        }
    }

    /// `battleProgressBar` stays `GONE` for the endless modes and is populated
    /// only for the two fixed-length sprints.
    var showsProgressBar: Bool {
        self == .customBattle || self == .todayChallenge
    }

    /// `battleProgressBar.max` — 15 for the custom sprint, 10 for the daily.
    var progressBarMaximum: Int {
        switch self {
        case .customBattle: return 15
        case .todayChallenge: return 10
        case .practice, .survival, .kingOfTopic: return 1
        }
    }
}

/// Ports the launch parameters `MCQActivity.onCreate` gathers from its intent
/// and from `SharedPreferences("MY_APP")`.
struct MCQSessionConfig {

    /// `intent.getStringExtra("MODE")`.
    var mode: MCQMode = .practice

    /// `intent.getStringExtra("SELECTED_SUBJECT")`, falling back to the
    /// `selected_subject_preference` preference and then to `"General"`.
    var subject: String = "General"

    /// `intent.getStringExtra("SELECTED_TOPIC")`. `nil` means "All Topics".
    var topic: String?

    /// `intent.getIntegerArrayListExtra("QUESTION_ID_LIST")` — a fixed test.
    /// A non-empty list sets Kotlin's `isFixedTest` and hides the topic picker.
    var fixedQuestionIds: [Int] = []

    /// `question_id`, whether it arrived as the `/question/<id>` and
    /// `share.php` deep-link query parameter or matched out of an
    /// `ACTION_SEND` payload by `(?:question_id|id)[=\/](\d+)`. A value above
    /// zero also sets `isFixedTest` in Kotlin.
    var singleQuestionId: Int?

    init(
        mode: MCQMode = .practice,
        subject: String = "General",
        topic: String? = nil,
        fixedQuestionIds: [Int] = [],
        singleQuestionId: Int? = nil
    ) {
        self.mode = mode
        self.subject = subject
        self.topic = topic
        self.fixedQuestionIds = fixedQuestionIds
        self.singleQuestionId = singleQuestionId
    }
}

/// Ports `MCQActivity.showBadgePopup()` — the `dialog_badge_unlocked` dialog
/// Android inflates for the 5 / 10 / 25 streak milestones and dismisses after
/// three seconds.
struct MCQBadgeEvent: Identifiable, Equatable {
    let id: UUID = UUID()
    let title: String
    let message: String
}

/// Ports the four modal outcomes `MCQActivity` raises through non-cancelable
/// `AlertDialog`s: `showSurvivalEndDialog`, `showChallengeTimeoutDialog`, the
/// "Custom Battle Complete!" dialog, and `showNotEnoughQuestionsDialog`.
enum MCQTerminalEvent: Identifiable, Equatable {

    /// `showSurvivalEndDialog()` — rounds survived, best streak, session XP.
    case survivalEnded(rounds: Int, maxStreak: Int, totalXP: Int)

    /// `showChallengeTimeoutDialog()` — the 10-minute sprint ran out.
    case challengeTimedOut

    /// The "Custom Battle Complete!" dialog raised two seconds after the last
    /// of the 15 sprint questions is answered.
    case customBattleComplete(totalXP: Int, maxStreak: Int)

    /// `showNotEnoughQuestionsDialog()` — King of the Topic needs 200 rows.
    case notEnoughQuestions(available: Int, required: Int)

    var id: String {
        switch self {
        case .survivalEnded: return "survivalEnded"
        case .challengeTimedOut: return "challengeTimedOut"
        case .customBattleComplete: return "customBattleComplete"
        case .notEnoughQuestions: return "notEnoughQuestions"
        }
    }

    var title: String {
        switch self {
        case .survivalEnded: return "Survival Ended!"
        case .challengeTimedOut: return "Time's Up!"
        case .customBattleComplete: return "Custom Battle Complete!"
        case .notEnoughQuestions: return "Not Enough Questions"
        }
    }

    var message: String {
        switch self {
        case let .survivalEnded(rounds, best, totalXP):
            return "You survived \(rounds) rounds.\nMax Streak: \(best)\nTotal XP this session: \(totalXP)"
        case .challengeTimedOut:
            return "The 10-minute challenge has ended."
        case let .customBattleComplete(totalXP, best):
            return "You completed 15 questions.\nTotal XP: \(totalXP)\nMax Streak: \(best)"
        case let .notEnoughQuestions(available, required):
            return "This topic has only \(available) questions. King Mode requires at least \(required).\n\nMore questions coming soon!"
        }
    }
}

/// Ports the six fixed strings `MCQActivity.showReportDialog()` offers from its
/// `setItems(reasons)` array.
enum MCQReportReason {
    static let all = [
        "Wrong answer",
        "Wrong explanation",
        "Image not loading",
        "Duplicate question",
        "Typo / wording",
        "Other"
    ]
}

/// The gamified practice screen: question streaming, answer locking, instant
/// scoring with combo / streak / speed XP, the four battle-mode headers, the
/// survival and streak rules, the topic picker, the question navigator and the
/// local answer cache.
///
/// Ports `com.rankwarz.edulabsrtm.MCQActivity.kt` — the streaming half of it.
/// That one Activity serves five different launches; this view is parameterised
/// by ``MCQMode`` and ``MCQSessionConfig`` instead of intent extras.
///
/// Rendering reuses `Question` and the shared `OptionRow` / `CardContainer`
/// components, which already mirror the Android `option_selector` rows.
@MainActor
final class MCQViewModel: NSObject, ObservableObject, AVSpeechSynthesizerDelegate {

    // MARK: - Loaded content

    /// The current question, or why it could not be fetched.
    @Published private(set) var state: LoadState<Question> = .idle

    /// `api/getTopics.php` for the selected subject, backing `topicSpinner`.
    @Published private(set) var topicsState: LoadState<[String]> = .idle

    /// `all_question_ids` — the whole pool the navigator walks.
    @Published private(set) var allQuestionIds: [Int] = []

    /// `currentIndex` into ``allQuestionIds``.
    @Published private(set) var currentIndex: Int = 0

    /// `"All Topics"` followed by the fetched names.
    @Published private(set) var topicsList: [String] = ["All Topics"]

    /// The topic spinner's current selection.
    @Published var selectedTopic: String = "All Topics"

    // MARK: - Answer state

    /// `radioGroup.checkedRadioButtonId`, held as the option letter.
    @Published private(set) var selectedLetter: String?

    /// `showResult` has run, so the option rows are locked.
    @Published private(set) var revealed: Bool = false

    /// Kotlin disables `submitBtn` for the duration of the round trip.
    @Published private(set) var isSubmitting: Bool = false

    /// Set when Kotlin re-renders with the AI-expanded explanation.
    @Published private(set) var explanationOverride: String?

    // MARK: - Gamification

    @Published private(set) var comboCount: Int = 0
    @Published private(set) var currentExp: Int = 0
    @Published private(set) var currentStreak: Int = 0
    @Published private(set) var maxStreak: Int = 0
    @Published private(set) var survivalRound: Int = 1

    /// The speed component of `tvBattleModeTimerOrSpeed`, recomputed each second.
    @Published private(set) var speedBonusXP: Int = 0

    /// Seconds spent on the current question, for the speed ticker.
    @Published private(set) var elapsedSeconds: Int = 0

    /// `timeLeftSeconds`, seeded to 600 for `TODAY_CHALLENGE`.
    @Published private(set) var challengeSecondsLeft: Int = 600

    /// `statusText` — the one line Kotlin mutates on every state change.
    @Published private(set) var statusText: String = "Question 1 of 1"

    /// `dailyProgressBar` — answered ÷ pool size, as a fraction.
    @Published private(set) var dailyProgress: Double = 0

    /// How many pool questions carry a cached answer.
    @Published private(set) var answeredPoolCount: Int = 0

    /// `showFloatingXp`'s gold `+N XP!` toast.
    @Published private(set) var floatingXP: Int?

    /// `UIImpactFeedbackGenerator` and `UINotificationFeedbackGenerator` have no
    /// SwiftUI surface, so the triggers are published and the view animates.
    @Published private(set) var shakeTrigger: Int = 0
    @Published private(set) var popTrigger: Int = 0

    // MARK: - Transient UI

    /// `Snackbar.make(rootLayout, …)` for every `showButtonFeedback` call.
    @Published var toastMessage: String?

    /// `dialog_badge_unlocked` — the 5 / 10 / 25 streak milestones.
    @Published var badgeEvent: MCQBadgeEvent?

    /// The non-cancelable end-of-run dialogs; cleared by
    /// ``dismissTerminalEvent()``.
    @Published var terminalEvent: MCQTerminalEvent?

    /// `speakBtn`'s toggle for the explanation reader.
    @Published private(set) var isSpeaking: Bool = false

    // MARK: - Private state

    private let configuration: MCQSessionConfig
    private var api: MediGyaanAPI = .live
    private var userId: Int = 0
    private var currentSubject: String = "General"
    private var currentTopic: String?
    private var currentQuestionTopic: String = "General"

    private var isFixedTest: Bool
    private var isNavigating: Bool = false
    private var isAutoNavigating: Bool = false
    private var questionStartTime: Date?

    private var tickerTask: Task<Void, Never>?
    private var autoAdvanceTask: Task<Void, Never>?
    private var speechSynthesizer = AVSpeechSynthesizer()

    /// Android kept one `SharedPreferences` blob named `MCQ_ANSWERS` whose
    /// entries are `"q_<questionId>" → "A"|"B"|"C"|"D"` (or the `"SYNCED"`
    /// marker written when reconciling the server's `answered_ids`). The same
    /// blob is mirrored into `UserDefaults` under the same name.
    private static let answersStoreKey = "MCQ_ANSWERS"

    /// `optionA..optionD` mapped to the letters `submitAnswerx1.php` expects.
    private static let optionLetters = ["A", "B", "C", "D", "E"]

    // MARK: - Init

    init(configuration: MCQSessionConfig = MCQSessionConfig()) {
        self.configuration = configuration
        self.isFixedTest = !configuration.fixedQuestionIds.isEmpty
            || ((configuration.singleQuestionId ?? 0) > 0)
        super.init()
        self.currentSubject = Self.sanitizeSubject(configuration.subject)
        self.currentTopic = Self.normalizeTopic(configuration.topic)
        self.selectedTopic = Self.normalizeTopic(configuration.topic) ?? "All Topics"
        self.currentQuestionTopic = self.currentSubject
        self.currentExp = RankProgressStore.exp()
        self.speechSynthesizer.delegate = self
    }

    // MARK: - Derived state

    var mode: MCQMode { configuration.mode }

    /// Kotlin hides `topicLayout` for battle modes and for fixed tests.
    var showsTopicPicker: Bool {
        !configuration.mode.isBattleMode && !isFixedTest
    }

    var question: Question? { state.value }

    /// `allQuestionIds.size`, floored at 1 so the status line never reads
    /// "of 0" the way the Kotlin string template would.
    var totalCount: Int { max(allQuestionIds.count, 1) }

    var isFirstQuestion: Bool { currentIndex <= 0 }

    var isLastQuestion: Bool { currentIndex >= allQuestionIds.count - 1 }

    /// `isAnswered` in the picker — a locally cached answer exists.
    func isAnsweredLocally(_ id: Int) -> Bool {
        Self.answerStore()[Self.answerKey(id)] != nil
    }

    /// The visible explanation, preferring the AI-expanded variant Kotlin
    /// writes back onto the question object.
    var currentExplanation: String {
        if let explanationOverride, !explanationOverride.isEmpty { return explanationOverride }
        return question?.explanation ?? ""
    }

    /// The review payload for ``ReviewView``, in Kotlin's `createReviewJson`
    /// key order.
    var reviewJSON: String {
        Self.makeReviewJSON(
            question: question,
            selected: selectedLetter ?? "",
            isCorrect: isAnsweredCorrectly,
            explanation: currentExplanation
        )
    }

    /// Whether the revealed pair matches, recomputed rather than stored.
    private var isAnsweredCorrectly: Bool {
        guard let selected = selectedLetter, let question = question else { return false }
        return Self.normalizeLetter(selected)
            == Self.normalizeLetter(Self.letter(for: question.correctIndex))
    }

    // MARK: - Lifecycle

    /// Ports `MCQActivity.onCreate` → `fetchTopics()` / `fetchQuestion(...)`.
    func start(api: MediGyaanAPI, userId: Int) async {
        self.api = api
        self.userId = userId
        self.currentExp = RankProgressStore.exp()

        if configuration.mode.isBattleMode {
            startTicker()
        }

        if isFixedTest {
            var ids = configuration.fixedQuestionIds
            if ids.isEmpty, let single = configuration.singleQuestionId, single > 0 {
                ids = [single]
            }
            allQuestionIds = ids
            guard let first = ids.first else {
                state = .failed("No question id was supplied for this test.")
                return
            }
            currentIndex = 0
            await fetchQuestion(id: first)
            return
        }

        await loadTopics()
        await fetchQuestion(id: nil)
    }

    /// Cancels the speed / challenge ticker and the auto-advance hop, mirroring
    /// `onDestroy`'s `removeCallbacksAndMessages(null)` and `tts?.shutdown()`.
    func stop() {
        tickerTask?.cancel()
        tickerTask = nil
        autoAdvanceTask?.cancel()
        autoAdvanceTask = nil
        stopSpeech()
    }

    deinit {
        tickerTask?.cancel()
        autoAdvanceTask?.cancel()
    }

    // MARK: - Topics

    /// Ports `fetchTopics()` — `api/getTopics.php?subject=<subject>`.
    func loadTopics() async {
        topicsState = .loading
        do {
            let fetched = try await api.study.topics(subject: currentSubject)
            var names = ["All Topics"]
            names.append(contentsOf: fetched.map { $0.name }.filter { !$0.isEmpty })
            var seen = Set<String>()
            let deduped = names.filter { seen.insert($0).inserted }
            topicsList = deduped
            topicsState = .loaded(deduped)
        } catch {
            topicsState = .failed(LoadState<Never>.message(for: error))
        }
    }

    /// Ports the `topicSpinner.onItemSelected` body: ignore the first
    /// programmatic selection and every selection made while a fixed test or a
    /// battle is running, otherwise clear the pool and restart the stream.
    func selectTopic(_ topic: String) async {
        guard showsTopicPicker, topic != selectedTopic else { return }
        selectedTopic = topic
        currentTopic = Self.normalizeTopic(topic)
        stopSpeech()
        allQuestionIds = []
        currentIndex = 0
        await fetchQuestion(id: nil)
    }

    // MARK: - Question streaming

    /// Ports `fetchQuestion(questionId: Int?)`.
    ///
    /// A `nil` id streams `getQuestions.php?subject=…&topic=…&limit=…`; a
    /// non-nil id fetches that single row. Kotlin cancels any in-flight request
    /// tagged `MCQ_REQUESTS` first; the Swift task is not tracked, so the
    /// `isNavigating` guard in `navigate(_:)` is what prevents a double hop.
    func fetchQuestion(id: Int?) async {
        isNavigating = true
        state = .loading

        do {
            let result = try await api.study.fetchQuestions(
                subject: currentSubject,
                topic: currentTopic,
                userId: userId,
                questionId: id,
                limit: id == nil ? configuration.mode.questionLimit : nil
            )

            if allQuestionIds.isEmpty, !result.allQuestionIds.isEmpty {
                allQuestionIds = resolvePool(from: result.allQuestionIds)
                if configuration.mode.isKingOfTopic,
                   result.allQuestionIds.count < 200,
                   terminalEvent == nil {
                    terminalEvent = .notEnoughQuestions(
                        available: result.allQuestionIds.count,
                        required: 200
                    )
                }
                updateDailyProgress()
            }

            var loaded = result.question
            if let head = allQuestionIds.first, let fetched = loaded, fetched.id != head {
                // Kotlin re-fetches when the streamed row is not the head of the
                // pool, so the first question always matches the navigator.
                loaded = try? await api.study.question(id: head)
            }
            if loaded == nil, let fallbackId = id ?? allQuestionIds.first {
                loaded = try? await api.study.question(id: fallbackId)
            }

            guard let question = loaded else {
                state = .failed("No question is available for this subject yet.")
                isNavigating = false
                return
            }
            display(question)
        } catch {
            let message = LoadState<Never>.message(for: error)
            state = .failed(message)
            toastMessage = "Network error: \(message)"
        }
        isNavigating = false
    }

    /// Ports the pool-building branch of the `fetchQuestion` success handler:
    /// battle modes shuffle unattempted questions to the front and truncate to
    /// the sprint length; everything else takes the server order verbatim.
    private func resolvePool(from ids: [Int]) -> [Int] {
        guard configuration.mode.isBattleMode else { return ids }
        var unattempted: [Int] = []
        var attempted: [Int] = []
        for id in ids {
            if isAnsweredLocally(id) {
                attempted.append(id)
            } else {
                unattempted.append(id)
            }
        }
        var pool = unattempted.shuffled() + attempted.shuffled()
        if configuration.mode == .customBattle {
            pool = Array(pool.prefix(15))
        } else if configuration.mode == .todayChallenge {
            pool = Array(pool.prefix(10))
        }
        return pool
    }

    /// Ports `displayQuestionWithAnimation` → `displayQuestionData`.
    ///
    /// The Kotlin version fades the card out, rebuilds, then fades it back in;
    /// SwiftUI's implicit animation on ``state`` covers the same beat.
    private func display(_ question: Question) {
        currentQuestionTopic = Self.extractTopic(question)
        selectedLetter = nil
        revealed = false
        isSubmitting = false
        explanationOverride = nil
        questionStartTime = Date()
        elapsedSeconds = 0
        speedBonusXP = 0
        state = .loaded(question)
        updateStatusText()
        updateDailyProgress()

        // Kotlin ignores the local cache entirely in battle mode, so a sprint
        // is never pre-solved by an earlier session.
        guard !configuration.mode.isBattleMode else { return }
        if let cached = Self.answerStore()[Self.answerKey(question.id)] {
            reveal(
                correct: Self.letter(for: question.correctIndex),
                selected: cached,
                explanation: question.explanation,
                fromCache: true
            )
        }
    }

    // MARK: - Answering

    /// Records the radio selection. Kotlin defers grading to `submitBtn`.
    func selectOption(at index: Int) {
        guard !revealed, !isSubmitting else { return }
        selectedLetter = Self.letter(for: index)
    }

    /// Ports `submitAnswer()` — the empty-radiogroup guard, the button disable
    /// and the POST to `submitAnswerx1.php`.
    func submit() {
        guard let question = question, let letter = selectedLetter else {
            toastMessage = "Select an answer first!"
            return
        }
        guard !revealed, !isSubmitting else { return }
        isSubmitting = true
        Task { await submit(letter: letter, for: question) }
    }

    private func submit(letter: String, for question: Question) async {
        do {
            let ack = try await api.study.submitAnswer(
                questionId: question.id,
                answer: letter,
                userId: userId
            )
            guard ack.success else {
                isSubmitting = false
                toastMessage = ack.message.isEmpty ? "Could not submit answer" : ack.message
                return
            }
            Self.saveAnswer(letter, for: question.id)
            updateDailyProgress()
            reveal(
                correct: Self.letter(for: question.correctIndex),
                selected: letter,
                explanation: question.explanation,
                fromCache: false
            )
        } catch {
            isSubmitting = false
            toastMessage = "Network error: \(LoadState<Never>.message(for: error))"
        }
    }

    /// Ports `showResult()` and its `finalizeResult` closure: combo, streak,
    /// the speed bonus, the survival round multiplier, the 5 / 10 / 25 streak
    /// milestones, the option re-colouring and the history write.
    private func reveal(correct: String, selected: String, explanation: String, fromCache: Bool) {
        selectedLetter = selected
        revealed = true
        isSubmitting = false

        let isCorrect = Self.normalizeLetter(selected) == Self.normalizeLetter(correct)

        if isCorrect {
            comboCount += 1
            popTrigger += 1
            currentStreak += 1
            maxStreak = max(maxStreak, currentStreak)

            var gain = 10 + (comboCount * 2)
            gain += speedBonusXP

            if configuration.mode.isSurvivalMode {
                gain += survivalRound * 5
                survivalRound += 1
            }

            switch currentStreak {
            case 5:
                gain += 50
                badgeEvent = MCQBadgeEvent(
                    title: "🔥 5 Streak Bonus!",
                    message: "You gained +50 bonus XP"
                )
            case 10:
                gain += 150
                badgeEvent = MCQBadgeEvent(
                    title: "🔥 10 Streak Super Bonus!",
                    message: "You gained +150 bonus XP"
                )
            case 25:
                gain += 500
                badgeEvent = MCQBadgeEvent(
                    title: "🏆 25 Streak Legend!",
                    message: "Special Badge Unlocked!"
                )
            default:
                break
            }

            currentExp += gain
            // Kotlin: `prefs.edit().putInt("user_exp", currentExp).apply()`.
            RankProgressStore.setExp(currentExp)
            floatingXP = gain

            statusText = configuration.mode.isSurvivalMode
                ? "SURVIVED! +\(gain) XP (Speed: +\(speedBonusXP))"
                : "+\(gain) XP! 🔥 Combo: \(comboCount)"

            recordStatistics(isCorrect: true)

            if !fromCache && !isAutoNavigating {
                scheduleAutoAdvance()
            }
        } else {
            comboCount = 0
            shakeTrigger += 1
            currentStreak = 0

            if configuration.mode.isSurvivalMode && !fromCache {
                statusText = "SURVIVAL ENDED at Round \(survivalRound)"
                recordStatistics(isCorrect: false)
                if terminalEvent == nil {
                    terminalEvent = .survivalEnded(
                        rounds: survivalRound,
                        maxStreak: maxStreak,
                        totalXP: currentExp
                    )
                }
            } else {
                statusText = "+0 XP • Wrong answer"
                recordStatistics(isCorrect: false)
            }
        }

        persistHistory(selected: selected, isCorrect: isCorrect)

        // Kotlin returns early here for the final question of a custom sprint.
        if configuration.mode == .customBattle, isLastQuestion {
            statusText = "CUSTOM BATTLE COMPLETE! +\(currentExp) XP"
            if terminalEvent == nil {
                terminalEvent = .customBattleComplete(
                    totalXP: currentExp,
                    maxStreak: maxStreak
                )
            }
            return
        }

        // Kotlin asks the gateway for a richer explanation when the stored one
        // is thinner than 100 characters.
        let trimmed = explanation.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.count < 100 && !fromCache {
            explanationOverride = "Loading enhanced AI explanation..."
            Task { await loadEnhancedExplanation(base: trimmed) }
        } else {
            explanationOverride = trimmed
        }
    }

    /// Ports `fetchAiAnswerForAutoExplanation()` together with the
    /// `saveEnhancedExplanationToDatabase()` write that follows it.
    private func loadEnhancedExplanation(base: String) async {
        guard let question = question else { return }
        let prompt = """
        Question: \(question.text)
        Base Explanation: \(base)
        Query: Explain this MCQ in detail.
        """
        let context = "{\"question_id\":\(question.id),\"subject\":\"\(currentSubject)\"}"

        var resolved = base
        do {
            let reply = try await api.ai.ask(
                prompt: prompt,
                userId: userId,
                model: "ask_ai2",
                context: context
            )
            let trimmed = reply.trimmingCharacters(in: .whitespacesAndNewlines)
            if !trimmed.isEmpty { resolved = trimmed }
        } catch {
            resolved = base
        }

        AiTrainingLogger.log(
            userId: userId,
            source: "mcq_auto_explanation",
            provider: "medigyaan_backend",
            model: "ask_ai2",
            prompt: prompt,
            response: resolved,
            status: resolved == base ? "failed" : "completed",
            contextJson: context
        )

        explanationOverride = resolved.isEmpty ? base : "🤖 AI Enhanced:\n\n\(resolved)"
    }

    // MARK: - Per-answer side effects

    /// Ports the `DailyStatsManager` / `AccuracyHistoryManager` /
    /// `UserCacheSyncer` trio `finalizeResult` fires on every answer.
    private func recordStatistics(isCorrect: Bool) {
        DailyStatsManager.shared.recordAnswer(topic: currentQuestionTopic, isCorrect: isCorrect)
        AccuracyHistoryManager.shared.recordAnswer(isCorrect: isCorrect)
        Task { await UserCacheSyncer.sync(userId: userId) }
    }

    /// Ports `HistoryManager.saveHistory(…, reviewJson = review)`. Kotlin stores
    /// the running totals rather than this question alone, so the same is done
    /// here.
    private func persistHistory(selected: String, isCorrect: Bool) {
        let today = DailyStatsManager.shared.getToday()
        QuizHistoryManager.shared.saveHistory(
            userId: userId,
            mode: "PRACTICE",
            title: "Practice Session",
            topic: currentQuestionTopic,
            score: currentExp,
            totalQuestions: today.attempted,
            correctAnswers: today.correct,
            wrongAnswers: max(0, today.attempted - today.correct),
            reviewJson: reviewJSON
        )
    }

    /// Ports `handleAutoAdvance()` — the 1.8 s hop to the next question.
    private func scheduleAutoAdvance() {
        autoAdvanceTask?.cancel()
        isAutoNavigating = true
        autoAdvanceTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 1_800_000_000)
            guard let self, !Task.isCancelled else { return }
            self.isAutoNavigating = false
            self.navigate(1)
        }
    }

    // MARK: - Navigation

    /// Ports `navigate(step: Int)` — bounds-checked, speech-cancelling and
    /// re-entrancy guarded exactly like Kotlin's `isNavigating` flag.
    func navigate(_ step: Int) {
        guard !isNavigating, !allQuestionIds.isEmpty else { return }
        stopSpeech()
        let target = currentIndex + step
        guard allQuestionIds.indices.contains(target) else { return }
        currentIndex = target
        Task { await fetchQuestion(id: allQuestionIds[target]) }
    }

    /// Ports `showQuestionPicker()`'s `onItemClick`.
    func jump(to index: Int) {
        guard allQuestionIds.indices.contains(index) else { return }
        stopSpeech()
        currentIndex = index
        Task { await fetchQuestion(id: allQuestionIds[index]) }
    }

    // MARK: - Terminal events

    /// Clears ``terminalEvent`` — Kotlin's `setPositiveButton` handler.
    func dismissTerminalEvent() {
        terminalEvent = nil
    }

    /// Retires the floating `+N XP!` badge after its one-second flight, as the
    /// `withEndAction` in `showFloatingXp` does.
    func clearFloatingXP() {
        floatingXP = nil
    }

    /// Dismisses `dialog_badge_unlocked` after Kotlin's three seconds.
    func clearBadgeEvent() {
        badgeEvent = nil
    }

    // MARK: - Ticker

    /// The merged `speedTickerHandler` (1 s) and `challengeTimerHandler` (1 s)
    /// loops. Both ran at the same cadence, so one task drives both; Kotlin's
    /// `isFinishing || isDestroyed` guard becomes `Task.isCancelled`.
    private func startTicker() {
        tickerTask?.cancel()
        tickerTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 1_000_000_000)
                guard let self, !Task.isCancelled else { return }
                self.tick()
            }
        }
    }

    private func tick() {
        if let start = questionStartTime {
            elapsedSeconds = Int(Date().timeIntervalSince(start))
            speedBonusXP = Self.speedBonus(forSeconds: elapsedSeconds)
        }

        if configuration.mode == .todayChallenge, challengeSecondsLeft > 0 {
            challengeSecondsLeft -= 1
            if challengeSecondsLeft == 0 {
                tickerTask?.cancel()
                if terminalEvent == nil {
                    terminalEvent = .challengeTimedOut
                }
            }
        }
    }

    /// `tvBattleModeTimerOrSpeed` in full — the daily challenge pairs the
    /// countdown with the live bonus, the other battle modes show speed, then
    /// elapsed seconds.
    var battleTimerText: String {
        switch configuration.mode {
        case .todayChallenge:
            let minutes = challengeSecondsLeft / 60
            let seconds = challengeSecondsLeft % 60
            return String(format: "⏱ %02d:%02d • +%d XP", minutes, seconds, speedBonusXP)
        case .customBattle, .kingOfTopic, .survival:
            if speedBonusXP > 0 { return "⚡ +\(speedBonusXP) XP Speed" }
            return "⏱ \(elapsedSeconds)s"
        case .practice:
            return "⚡ +15 XP"
        }
    }

    /// `tvBattleModeTitle`.
    var battleTitle: String {
        switch configuration.mode {
        case .survival:
            return "Sudden Death • \(currentSubject)"
        case .kingOfTopic:
            return "Crown Arena • \(currentTopic ?? currentSubject)"
        case .customBattle:
            return "15-Question Battle Sprint"
        case .todayChallenge:
            return "10-Minute Challenge Sprint"
        case .practice:
            return "Practice"
        }
    }

    /// `tvBattleModeSubtitle` in its post-answer form, from
    /// `updateBattleHeaderUI()`.
    var battleSubtitle: String {
        let position = min(currentIndex + 1, totalCount)
        switch configuration.mode {
        case .survival:
            return "Round \(survivalRound) • Streak: \(currentStreak) (Best: \(maxStreak))"
        case .kingOfTopic:
            return "Streak: \(currentStreak) (Best: \(maxStreak)) • Round \(survivalRound)"
        case .customBattle:
            return "Question \(position) of \(totalCount) • Max Streak: \(maxStreak)"
        case .todayChallenge:
            return "Question \(position) of \(totalCount) • Streak: \(currentStreak)"
        case .practice:
            return "Question \(currentIndex + 1) of \(totalCount)"
        }
    }

    // MARK: - TTS

    /// Ports `speakExplanation()` — reads whatever is currently in the
    /// explanation card.
    func toggleExplanationSpeech() {
        if isSpeaking {
            stopSpeech()
            return
        }
        let text = currentExplanation
        guard !text.isEmpty else {
            toastMessage = "No explanation loaded"
            return
        }
        speechSynthesizer.stopSpeaking(at: .immediate)
        let utterance = AVSpeechUtterance(string: text)
        utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
        utterance.rate = AVSpeechUtteranceDefaultSpeechRate
        speechSynthesizer.speak(utterance)
        isSpeaking = true
    }

    /// Kotlin's `tts?.stop()` at the top of `navigate`.
    func stopSpeech() {
        speechSynthesizer.stopSpeaking(at: .immediate)
        isSpeaking = false
    }

    nonisolated func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didFinish utterance: AVSpeechUtterance) {
        Task { @MainActor [weak self] in
            self?.isSpeaking = false
        }
    }

    // MARK: - Report

    /// Records the report and surfaces Kotlin's failure toast. The
    /// `api/report_question.php` round trip needs a `StudyAPI` method that does
    /// not exist yet — see the porting report's blocker list.
    func submitReport(reason: String, details: String) {
        guard let question = question, question.id > 0 else {
            toastMessage = "No question loaded to report"
            return
        }
        RemoteLogger.log(
            tag: "MCQ_Report",
            message: "Report queued for question #\(question.id)",
            metadata: [
                "question_id": String(question.id),
                "reason": reason,
                "details": details
            ]
        )
        toastMessage = "Network error — report not sent"
    }

    // MARK: - Progress bookkeeping

    private func updateStatusText() {
        statusText = configuration.mode.isSurvivalMode
            ? "Survival Mode - Round \(survivalRound)"
            : "Question \(currentIndex + 1) of \(totalCount)"
    }

    /// Ports `updateDailyProgress()`.
    private func updateDailyProgress() {
        let total = allQuestionIds.count
        guard total > 0 else {
            dailyProgress = 0
            answeredPoolCount = 0
            return
        }
        let answered = allQuestionIds.filter { isAnsweredLocally($0) }.count
        dailyProgress = Double(answered) / Double(total)
        answeredPoolCount = answered
    }

    // MARK: - Pure helpers

    private static func answerKey(_ id: Int) -> String { "q_\(id)" }

    private static func answerStore() -> [String: String] {
        UserDefaults.standard.dictionary(forKey: Self.answersStoreKey) as? [String: String] ?? [:]
    }

    /// Kotlin's synchronous `commit()`: quiz progress has to survive an
    /// immediate process death, so the write must not be deferred.
    private static func saveAnswer(_ letter: String, for id: Int) {
        var store = Self.answerStore()
        store[Self.answerKey(id)] = letter
        UserDefaults.standard.set(store, forKey: Self.answersStoreKey)
    }

    /// The A/B/C/D mapping shared by `submitAnswerx1.php`, `createReviewJson`
    /// and the question picker.
    static func letter(for index: Int) -> String {
        Self.optionLetters.indices.contains(index) ? Self.optionLetters[index] : ""
    }

    /// The index for a stored letter; `-1` for Kotlin's `"SYNCED"` marker and
    /// for anything unrecognised.
    static func index(for letter: String) -> Int {
        Self.optionLetters.firstIndex(of: Self.normalizeLetter(letter)) ?? -1
    }

    /// Kotlin's `replace(Regex("[^A-Za-z0-9]"), "")` applied to both answers
    /// before the case-insensitive comparison.
    static func normalizeLetter(_ raw: String) -> String {
        String(raw.uppercased().filter { $0.isLetter || $0.isNumber })
    }

    /// The three speed tiers shared by `speedTickerRunnable` and `showResult`.
    static func speedBonus(forSeconds seconds: Int) -> Int {
        if seconds < 5 { return 15 }
        if seconds < 10 { return 10 }
        if seconds < 15 { return 5 }
        return 0
    }

    /// Kotlin: `rawSubject.replace(Regex("[^\\p{L}\\p{N}\\s]"), "").trim()`,
    /// collapsing to `"General"` when nothing survives.
    static func sanitizeSubject(_ raw: String) -> String {
        let filtered = raw.filter { $0.isLetter || $0.isNumber || $0.isWhitespace }
        let trimmed = filtered.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? "General" : trimmed
    }

    /// Maps `"All Topics"` and empty strings onto `nil`, as Kotlin's `topicParam`
    /// did.
    static func normalizeTopic(_ raw: String?) -> String? {
        guard let raw = raw else { return nil }
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, trimmed != "All Topics" else { return nil }
        return trimmed
    }

    /// Ports `extractQuestionTopic()`: `topic`, then `topic_name`, then
    /// `subject`, then `"General"`, with non-alphanumerics stripped.
    static func extractTopic(_ question: Question) -> String {
        let candidates = [question.topic, question.subject]
        let chosen = candidates.first { !$0.isEmpty && $0.lowercased() != "null" } ?? "General"
        return Self.sanitizeSubject(chosen)
    }

    /// Ports `createReviewJson()` — one object inside an array, keys verbatim.
    static func makeReviewJSON(
        question: Question?,
        selected: String,
        isCorrect: Bool,
        explanation: String
    ) -> String {
        guard let question = question else { return "[]" }
        let correctLetter = Self.letter(for: question.correctIndex)
        let selectedIndex = Self.index(for: selected)
        let item = ReviewQuestionItem(
            question_id: question.id,
            question: question.text,
            option_a: question.options.indices.contains(0) ? question.options[0] : "",
            option_b: question.options.indices.contains(1) ? question.options[1] : "",
            option_c: question.options.indices.contains(2) ? question.options[2] : "",
            option_d: question.options.indices.contains(3) ? question.options[3] : "",
            option_e: question.options.indices.contains(4) ? question.options[4] : "",
            selected_option: selected,
            correct_option: correctLetter,
            selected_answer_text: question.options.indices.contains(selectedIndex)
                ? question.options[selectedIndex]
                : "",
            correct_answer_text: question.options.indices.contains(question.correctIndex)
                ? question.options[question.correctIndex]
                : "",
            score_change: isCorrect ? 1 : 0,
            explanation: explanation,
            image_url: question.imageURL?.absoluteString ?? "",
            is_correct: isCorrect ? 1 : 0
        )
        guard let data = try? JSONEncoder().encode([item]),
              let json = String(data: data, encoding: .utf8) else {
            return "[]"
        }
        return json
    }
}
