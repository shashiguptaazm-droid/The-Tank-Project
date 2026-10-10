import SwiftUI

/// Quiz/battle attempt history model.
///
/// 1:1 port of Android `HistoryModel.kt`.
public struct QuizHistoryItem: Identifiable, Codable, Hashable {
    public var id: String { historyId }
    public let historyId: String
    public let userId: Int
    public let mode: String // PRACTICE / CHALLENGE / FINAL_TEST / SINGLE_PLAYER
    public let title: String
    public let topic: String
    public let score: Int
    public let totalQuestions: Int
    public let correctAnswers: Int
    public let wrongAnswers: Int
    public let percentage: Float
    public let challengeId: String
    public let reviewJson: String
    public let timestamp: Double

    public init(
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
}

/// Local and Firebase history tracker matching Android `HistoryManager.kt`.
public final class QuizHistoryManager: ObservableObject {

    public static let shared = QuizHistoryManager()

    /// The `UserDefaults` key the local mirror is cached under.
    ///
    /// Android has no local mirror at all — history lives only in Firebase
    /// under `history/{user_id}/{pushKey}` — so this key is iOS-only. It still
    /// uses a bare literal because `AppPreferences` does not yet own a history
    /// key; see the porting report's blocker list.
    private let cacheKey = "quiz_history_items_v1"

    @Published public private(set) var historyItems: [QuizHistoryItem] = []

    private init() {
        loadLocalHistory()
    }

    private func loadLocalHistory() {
        if let data = UserDefaults.standard.data(forKey: cacheKey),
           let items = try? JSONDecoder().decode([QuizHistoryItem].self, from: data) {
            self.historyItems = items.sorted { $0.timestamp > $1.timestamp }
        }
    }

    public func saveHistory(
        userId: Int,
        mode: String,
        title: String,
        topic: String,
        score: Int,
        totalQuestions: Int,
        correctAnswers: Int,
        wrongAnswers: Int,
        challengeId: String = "",
        reviewJson: String = ""
    ) {
        let attempted = correctAnswers + wrongAnswers
        let percentage: Float = attempted > 0 ? (Float(correctAnswers) * 100.0) / Float(attempted) : 0.0

        let item = QuizHistoryItem(
            userId: userId,
            mode: mode,
            title: title,
            topic: topic,
            score: score,
            totalQuestions: totalQuestions,
            correctAnswers: correctAnswers,
            wrongAnswers: wrongAnswers,
            percentage: percentage,
            challengeId: challengeId,
            reviewJson: reviewJson
        )

        historyItems.insert(item, at: 0)
        if let encoded = try? JSONEncoder().encode(historyItems) {
            UserDefaults.standard.set(encoded, forKey: cacheKey)
        }
    }
}

// MARK: - `HistoryManager` parity

/// Additions that port the parts of Android `HistoryManager` the original
/// iOS port folded away — the `user_id` rejection, the `MY_APP` preference
/// namespace, the Firebase `history/{userId}/{pushKey}` path and the
/// chronologically-sortable push key that becomes `historyId`.
///
/// Everything here is additive: ``QuizViewModel``, ``MCQViewModel`` and
/// ``SubjectTestViewModel`` all call the original ``QuizHistoryManager/saveHistory(userId:mode:title:topic:score:totalQuestions:correctAnswers:wrongAnswers:challengeId:reviewJson:)``,
/// whose signature and behaviour are untouched.
extension QuizHistoryManager {

    /// Ports `HistoryManager.TAG`.
    static let logTag = "HISTORY_MANAGER"

    /// Ports `context.getSharedPreferences("MY_APP", Context.MODE_PRIVATE)` —
    /// the single preference file every Android key below is read from.
    static let preferencesName = "MY_APP"

    /// Ports `FirebaseDatabase.getInstance().getReference("history")`.
    static let firebaseHistoryRoot = "history"

    /// Ports the `user_id` key read out of `SharedPreferences("MY_APP")`.
    ///
    /// iOS keeps the same value under the `SessionStore` mirror key rather
    /// than the Android spelling, because `SessionStore.DefaultsKey` is
    /// file-private and cannot be referenced from here. Once `AppPreferences`
    /// owns a `userId` key this should read that instead of the literal.
    static let userIdPreferenceKey = "mg.user_id"

    /// The 64-character alphabet Firebase uses for `push().key`, in value
    /// order: `-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz`.
    private static let pushIdAlphabet: [Character] =
        Array("-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz")

    /// Ports the `history/$userId/$key` path Kotlin builds by hand for its
    /// `Log.d` / `Log.e` lines in `performSave`.
    static func historyPath(userId: Int, historyId: String) -> String {
        "\(Self.firebaseHistoryRoot)/\(userId)/\(historyId)"
    }

    /// Ports `prefs.getInt("user_id", 0)` — the signed-in doctor, or `0`.
    static func storedUserId(defaults: UserDefaults = .standard) -> Int {
        defaults.integer(forKey: Self.userIdPreferenceKey)
    }

    /// Ports the `if (userId == 0)` early-out in `HistoryManager.performSave`,
    /// which rejects the write instead of storing a record nobody can read back.
    static func isValidUserId(_ userId: Int) -> Bool {
        userId != 0
    }

    /// Ports `val attempted = correctAnswers + wrongAnswers` followed by
    /// `val percentage = if (attempted > 0) (correctAnswers * 100f) /
    /// attempted else 0f`.
    static func percentage(correctAnswers: Int, wrongAnswers: Int) -> Float {
        let attempted = correctAnswers + wrongAnswers
        guard attempted > 0 else { return 0 }
        return (Float(correctAnswers) * 100.0) / Float(attempted)
    }

    /// Ports `database.push().key`: a 20-character key whose first eight
    /// characters are the epoch-millisecond timestamp and whose remaining
    /// twelve are random, both in the Firebase base64 alphabet — which is what
    /// makes Firebase return history rows in chronological order.
    ///
    /// ``QuizHistoryItem``'s default `historyId` is a `UUID`, which does not
    /// sort; callers wanting Android's ordering generate the id here instead.
    static func makePushId(date: Date = Date()) -> String {
        let milliseconds = UInt64(max(0, date.timeIntervalSince1970 * 1000))
        var characters = Self.encodePushIdBase64(milliseconds, width: 8)
        for _ in 0..<12 {
            characters.append(Self.pushIdAlphabet[Int.random(in: 0...63)])
        }
        return String(characters)
    }

    /// Six bits per character, most significant first, as Firebase's
    /// `Utilities.timestampToPushID` packs the 48-bit millisecond timestamp.
    private static func encodePushIdBase64(_ value: UInt64, width: Int) -> [Character] {
        var buffer = value
        var digits = [Int](repeating: 0, count: width)
        for offset in stride(from: width - 1, through: 0, by: -1) {
            digits[offset] = Int(buffer & 63)
            buffer >>= 6
        }
        return digits.map { Self.pushIdAlphabet[$0] }
    }

    /// Ports `HistoryManager.performSave(…)`: the `user_id == 0` rejection, the
    /// derived `percentage`, the generated `historyId`, the
    /// `System.currentTimeMillis()` timestamp and the single write.
    ///
    /// Kotlin reports the outcome through `onComplete(Boolean)` once Firebase
    /// acknowledges the `setValue`; iOS has no remote half, so the flag is
    /// returned directly and `false` means Kotlin's "Invalid user_id" early-out.
    @discardableResult
    func saveHistoryEntry(
        userId: Int,
        mode: String,
        title: String,
        topic: String,
        score: Int,
        totalQuestions: Int,
        correctAnswers: Int,
        wrongAnswers: Int,
        challengeId: String = "",
        reviewJson: String = ""
    ) -> Bool {
        guard Self.isValidUserId(userId) else {
            RemoteLogger.log(
                tag: Self.logTag,
                message: "Invalid user_id in preferences; history not saved"
            )
            return false
        }

        let item = QuizHistoryItem(
            historyId: Self.makePushId(),
            userId: userId,
            mode: mode,
            title: title,
            topic: topic,
            score: score,
            totalQuestions: totalQuestions,
            correctAnswers: correctAnswers,
            wrongAnswers: wrongAnswers,
            percentage: Self.percentage(correctAnswers: correctAnswers, wrongAnswers: wrongAnswers),
            challengeId: challengeId,
            reviewJson: reviewJson
        )

        historyItems.insert(item, at: 0)
        persistLocalCache()

        RemoteLogger.log(
            tag: Self.logTag,
            message: "History saved to \(Self.historyPath(userId: userId, historyId: item.historyId))"
        )
        return true
    }

    /// The encode-and-write half of `saveHistory`, split out so the entry
    /// builder above does not repeat the `UserDefaults` plumbing.
    private func persistLocalCache() {
        guard let encoded = try? JSONEncoder().encode(historyItems) else { return }
        UserDefaults.standard.set(encoded, forKey: cacheKey)
    }
}
