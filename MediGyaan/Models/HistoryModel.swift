import Foundation

/// Ports `HistoryModel` (`com.rankwarz.edulabsrtm.HistoryModel.kt`): the 13-field
/// quiz/battle attempt record that Android writes to Firebase Realtime Database
/// under `history/<userId>/<historyId>` via `HistoryManager.performSave`.
///
/// Serialisation contract: Android hands the data class straight to Firebase's
/// bean mapper, so the wire keys are the Kotlin property names verbatim. The
/// `CodingKeys` below therefore reproduce them exactly (`historyId`, `userId`,
/// `mode`, `title`, `topic`, `score`, `totalQuestions`, `correctAnswers`,
/// `wrongAnswers`, `percentage`, `challengeId`, `reviewJson`, `timestamp`) so
/// existing caches and any server round-trip stay readable.
///
/// Deliberately **not** a redeclaration of `QuizHistoryItem`
/// (`Models/QuizHistoryManager.swift`) — see the orchestrator note in that file.
struct HistoryModel: Codable, Identifiable, Hashable {

    /// Ports the mode values documented on `HistoryModel.mode` in
    /// `HistoryModel.kt`: `// PRACTICE / CHALLENGE / FINAL_TEST / SINGLE_PLAYER`.
    /// Android stores these as a bare `String`, so `HistoryModel.mode` stays a
    /// `String`; this enum only gives the filter chips a typed vocabulary.
    enum Mode: String, CaseIterable, Hashable {
        case practice = "PRACTICE"
        case challenge = "CHALLENGE"
        case finalTest = "FINAL_TEST"
        case singlePlayer = "SINGLE_PLAYER"

        /// Ports the lenient comparison `HistoryListView` performs with
        /// `caseInsensitiveCompare` against the raw `mode` column.
        static func resolve(_ raw: String) -> Mode? {
            Mode(rawValue: raw.trimmingCharacters(in: .whitespacesAndNewlines).uppercased())
        }
    }

    /// Ports `HistoryModel.historyId`. This is the Firebase `push()` key under
    /// `history/<userId>/`, so it is the natural — and unique — list identity.
    var id: String { historyId }

    /// Ports `HistoryModel.historyId` (Kotlin `String = ""`). iOS defaults to a
    /// fresh UUID so an unsaved record still has a stable row identity, matching
    /// `QuizHistoryManager.saveHistory`.
    let historyId: String

    /// Ports `HistoryModel.userId` (Kotlin `Int = 0`).
    let userId: Int

    /// Ports `HistoryModel.mode` (Kotlin `String = ""`, documented as
    /// PRACTICE / CHALLENGE / FINAL_TEST / SINGLE_PLAYER). Held as a raw string
    /// so unknown server modes never fail to decode.
    let mode: String

    /// Ports `HistoryModel.title` (Kotlin `String = ""`).
    let title: String

    /// Ports `HistoryModel.topic` (Kotlin `String = ""`).
    let topic: String

    /// Ports `HistoryModel.score` (Kotlin `Int = 0`).
    let score: Int

    /// Ports `HistoryModel.totalQuestions` (Kotlin `Int = 0`).
    let totalQuestions: Int

    /// Ports `HistoryModel.correctAnswers` (Kotlin `Int = 0`).
    let correctAnswers: Int

    /// Ports `HistoryModel.wrongAnswers` (Kotlin `Int = 0`).
    let wrongAnswers: Int

    /// Ports `HistoryModel.percentage` (Kotlin `Float = 0f`). Android computes it
    /// at the call site in `HistoryManager.performSave` as
    /// `(correctAnswers * 100f) / (correctAnswers + wrongAnswers)`, then stores
    /// the result — it is a stored field, not a derived one.
    let percentage: Float

    /// Ports `HistoryModel.challengeId` (Kotlin `String = ""`).
    let challengeId: String

    /// Ports `HistoryModel.reviewJson` (Kotlin `String = ""`), documented as
    /// "Detailed question-by-question data". Stays an opaque string because the
    /// payload schema belongs to `ReviewQuestionItem` in `Features/Quiz/ReviewView.swift`.
    let reviewJson: String

    /// Ports `HistoryModel.timestamp` (Kotlin `Long = System.currentTimeMillis()`).
    /// Android stores epoch **milliseconds**; iOS stores epoch **seconds** to match
    /// `Date(timeIntervalSince1970:)` in `HistoryListView.formattedDate`. Decoding
    /// normalises millisecond sources, see `normalizeTimestamp(_:)`.
    let timestamp: Double

    /// Ports the Kotlin property names one-for-one. Firebase's bean mapper uses
    /// these names, and `JSONEncoder` writes the same camelCase keys that the
    /// existing `quiz_history_items_v1` `UserDefaults` cache already contains.
    enum CodingKeys: String, CodingKey {
        case historyId
        case userId
        case mode
        case title
        case topic
        case score
        case totalQuestions
        case correctAnswers
        case wrongAnswers
        case percentage
        case challengeId
        case reviewJson
        case timestamp
    }

    /// Ports the `HistoryModel` data-class constructor; every default mirrors
    /// the Kotlin default argument on the corresponding property.
    init(
        historyId: String = UUID().uuidString,
        userId: Int = 0,
        mode: String = "PRACTICE",
        title: String = "",
        topic: String = "",
        score: Int = 0,
        totalQuestions: Int = 0,
        correctAnswers: Int = 0,
        wrongAnswers: Int = 0,
        percentage: Float = 0,
        challengeId: String = "",
        reviewJson: String = "",
        timestamp: Double = Date().timeIntervalSince1970
    ) {
        self.historyId = historyId
        self.userId = userId
        self.mode = mode
        self.title = title
        self.topic = topic
        self.score = score
        self.totalQuestions = totalQuestions
        self.correctAnswers = correctAnswers
        self.wrongAnswers = wrongAnswers
        self.percentage = percentage
        self.challengeId = challengeId
        self.reviewJson = reviewJson
        self.timestamp = timestamp
    }

    /// Tolerant decode following the `Models/Quiz.swift` convention: PHP/MySQL
    /// returns every column as a string, omits keys, and alternates between
    /// snake_case and camelCase, so no lookup uses the Swift property name alone.
    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        historyId = container.flexString("historyId", "history_id", "id", "key")
        userId = container.flexInt("userId", "user_id", "uid")
        mode = container.flexString("mode", "quiz_type", "type")
        title = container.flexString("title", "quiz_title", "name")
        topic = container.flexString("topic", "topic_name", "subject")
        score = container.flexInt("score", "marks", "total_score")
        totalQuestions = container.flexInt("totalQuestions", "total_questions", "question_count", "total")
        correctAnswers = container.flexInt("correctAnswers", "correct_answers", "correct", "right")
        wrongAnswers = container.flexInt("wrongAnswers", "wrong_answers", "wrong", "incorrect")
        percentage = Float(container.flexDouble("percentage", "percent", "accuracy", "score_percent"))
        challengeId = container.flexString("challengeId", "challenge_id", "battle_id")
        reviewJson = container.flexString("reviewJson", "review_json", "review", "answers_json", "detail")
        timestamp = HistoryModel.normalizeTimestamp(
            container.flexDouble("timestamp", "created_at", "date", "time", "attempted_at")
        )
    }

    /// Ports `HistoryListView.filteredList`'s `caseInsensitiveCompare` filter,
    /// exposing the same four buckets as `Mode`.
    var resolvedMode: Mode? { Mode.resolve(mode) }

    /// Ports the `percentage` computation in `HistoryManager.performSave`
    /// (`if (attempted > 0) correctAnswers * 100f / attempted else 0f`), so
    /// callers building a record do not have to re-derive it.
    static func calculatePercentage(correctAnswers: Int, wrongAnswers: Int) -> Float {
        let attempted = correctAnswers + wrongAnswers
        guard attempted > 0 else { return 0 }
        return (Float(correctAnswers) * 100.0) / Float(attempted)
    }

    /// Android writes `System.currentTimeMillis()`, while the iOS cache written
    /// by `QuizHistoryManager` writes `Date().timeIntervalSince1970`. Anything at
    /// or above 1e11 can only be a millisecond value in practice (1e11 seconds
    /// is the year 5138, 1e11 milliseconds is 1973), so it is scaled down.
    private static func normalizeTimestamp(_ raw: Double) -> Double {
        guard raw >= 100_000_000_000 else { return raw }
        return raw / 1000.0
    }
}