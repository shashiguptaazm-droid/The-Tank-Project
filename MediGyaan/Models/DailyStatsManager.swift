import Foundation

/// Per-topic performance item.
struct TopicAccuracyItem: Identifiable, Hashable {
    var id: String { topic }
    let topic: String
    let attempted: Int
    let correct: Int
    let accuracy: Int
}

/// Comprehensive daily and per-topic accuracy tracking engine,
/// strictly porting `DailyStatsManager.kt`.
///
/// Record envelope, per the Kotlin `recordAnswer()` writer:
/// `{ "yyyyMMdd": { "attempted": Int, "correct": Int,
///                  "topics": { "<Topic>": { "attempted": Int, "correct": Int } } } }`.
/// Blank topics collapse to `"General"`. Days are keyed in the device's current
/// timezone with no retention window — every recorded day is kept forever.
///
/// Storage keys diverge from Android by necessity. Android writes JSON *text* to
/// SharedPreferences file `MCQ_STATS_HISTORY`, key `daily_data`. iOS writes JSON
/// `Data` to `UserDefaults`, key `MCQ_STATS_HISTORY_DAILY_DATA`. The two stores
/// are physically separate (no shared container, no sync path), so the payload is
/// not transferable between platforms; the iOS key is kept as the live key and
/// `daily_data` is accepted only as a legacy alias during normalisation.
final class DailyStatsManager {

    static let shared = DailyStatsManager()

    private let userDefaultsKey = "MCQ_STATS_HISTORY_DAILY_DATA"

    /// Android `DailyStatsManager.KEY_DATA` (`"daily_data"`). Retained solely as a
    /// legacy read alias; see `normaliseStoredPayloadIfNeeded()`.
    private static let androidStorageKey = "daily_data"

    private init() {}

    private func getTodayKey() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyyMMdd"
        formatter.locale = Locale(identifier: "en_US_POSIX")
        return formatter.string(from: Date())
    }

    /// Ports the Kotlin `optInt(key, default)` defaulting scattered through
    /// `DailyStatsManager.kt`: a missing, null or non-numeric field reads as `0`.
    private static func intValue(_ value: Any?) -> Int {
        if let int = value as? Int { return int }
        if let number = value as? NSNumber { return number.intValue }
        return 0
    }

    /// Ports the Kotlin `todayObj.optJSONObject("topics") ?: JSONObject()` fallback:
    /// a day record whose `topics` value is absent or malformed reads as an empty
    /// map rather than failing the whole load.
    private static func topicsDict(from value: Any?) -> [String: [String: Any]] {
        if let typed = value as? [String: [String: Any]] { return typed }
        if let loose = value as? [String: Any] {
            var result: [String: [String: Any]] = [:]
            for (topic, entry) in loose {
                if let dict = entry as? [String: Any] { result[topic] = dict }
            }
            return result
        }
        return [:]
    }

    /// Ports the Android `putString(KEY_DATA, json.toString())` write shape, which
    /// lands the daily map as JSON *text* rather than encoded bytes. Any legacy
    /// text payload — at the iOS key, or at the Android key `daily_data` — is read,
    /// rewritten as `Data` at the iOS key, and the old entry cleared. Lossless and
    /// idempotent: the rewrite and the clear both target the source key, so a
    /// second call finds encoded `Data` at the iOS key and does nothing.
    private func normaliseStoredPayloadIfNeeded() {
        let defaults = UserDefaults.standard

        if let legacyText = defaults.string(forKey: userDefaultsKey) {
            if let encoded = legacyText.data(using: .utf8) {
                defaults.set(encoded, forKey: userDefaultsKey)
            } else {
                defaults.removeObject(forKey: userDefaultsKey)
            }
            return
        }

        guard defaults.data(forKey: userDefaultsKey) == nil else { return }

        if let legacyText = defaults.string(forKey: Self.androidStorageKey) {
            if let encoded = legacyText.data(using: .utf8) {
                defaults.set(encoded, forKey: userDefaultsKey)
            }
            defaults.removeObject(forKey: Self.androidStorageKey)
        } else if let legacyData = defaults.data(forKey: Self.androidStorageKey) {
            defaults.set(legacyData, forKey: userDefaultsKey)
            defaults.removeObject(forKey: Self.androidStorageKey)
        }
    }

    private func load() -> [String: [String: Any]] {
        normaliseStoredPayloadIfNeeded()
        guard let data = UserDefaults.standard.data(forKey: userDefaultsKey),
              let dict = (try? JSONSerialization.jsonObject(with: data)) as? [String: [String: Any]] else {
            return [:]
        }
        return dict
    }

    private func save(_ data: [String: [String: Any]]) {
        if let encoded = try? JSONSerialization.data(withJSONObject: data) {
            UserDefaults.standard.set(encoded, forKey: userDefaultsKey)
        }
    }

    func calculateAccuracy(attempted: Int, correct: Int) -> Int {
        guard attempted > 0 else { return 0 }
        return (correct * 100) / attempted
    }

    /// Record a question answer attempt by topic.
    func recordAnswer(topic: String, isCorrect: Bool) {
        let trimmed = topic.trimmingCharacters(in: .whitespacesAndNewlines)
        let cleanTopic = trimmed.isEmpty ? "General" : trimmed
        var data = load()
        let today = getTodayKey()

        var todayObj = data[today] ?? [
            "attempted": 0,
            "correct": 0,
            "topics": [String: [String: Any]]()
        ]

        let attempted = Self.intValue(todayObj["attempted"]) + 1
        let correct = Self.intValue(todayObj["correct"]) + (isCorrect ? 1 : 0)

        todayObj["attempted"] = attempted
        todayObj["correct"] = correct

        var topicsObj = Self.topicsDict(from: todayObj["topics"])
        var topicObj = topicsObj[cleanTopic] ?? ["attempted": 0, "correct": 0]

        let topicAttempted = Self.intValue(topicObj["attempted"]) + 1
        let topicCorrect = Self.intValue(topicObj["correct"]) + (isCorrect ? 1 : 0)

        topicObj["attempted"] = topicAttempted
        topicObj["correct"] = topicCorrect
        topicsObj[cleanTopic] = topicObj
        todayObj["topics"] = topicsObj

        data[today] = todayObj
        save(data)
    }

    /// Retrieve today's (attempted, correct).
    func getToday() -> (attempted: Int, correct: Int) {
        let data = load()
        let today = getTodayKey()
        guard let obj = data[today] else { return (0, 0) }
        let attempted = Self.intValue(obj["attempted"])
        let correct = Self.intValue(obj["correct"])
        return (attempted, correct)
    }

    /// Retrieve today's topic-wise map: Topic -> (attempted, correct)
    func getTodayTopicWise() -> [String: (attempted: Int, correct: Int)] {
        var result: [String: (attempted: Int, correct: Int)] = [:]
        let data = load()
        let today = getTodayKey()

        guard let todayObj = data[today] else { return result }

        for (topic, entry) in Self.topicsDict(from: todayObj["topics"]) {
            result[topic] = (Self.intValue(entry["attempted"]), Self.intValue(entry["correct"]))
        }

        return result
    }

    /// Retrieve overall stats across all recorded days.
    func getOverallStats() -> (attempted: Int, correct: Int) {
        let data = load()
        var attempted = 0
        var correct = 0

        for (_, dayObj) in data {
            attempted += Self.intValue(dayObj["attempted"])
            correct += Self.intValue(dayObj["correct"])
        }

        return (attempted, correct)
    }

    func getOverallAccuracy() -> Int {
        let stats = getOverallStats()
        return calculateAccuracy(attempted: stats.attempted, correct: stats.correct)
    }

    /// Ports `DailyStatsManager.getTotalBattles()`: the overall *attempted* count,
    /// i.e. the first element of the Kotlin `getOverallStats()` `Pair`.
    func getTotalBattles() -> Int {
        getOverallStats().attempted
    }

    /// Ports `DailyStatsManager.getTotalWins()`: the overall *correct* count,
    /// i.e. the second element of the Kotlin `getOverallStats()` `Pair`.
    func getTotalWins() -> Int {
        getOverallStats().correct
    }

    /// Calculate active daily streak.
    func getCurrentStreak() -> Int {
        let data = load()
        var streak = 0
        let calendar = Calendar.current
        var calDate = Date()

        let formatter = DateFormatter()
        formatter.dateFormat = "yyyyMMdd"
        formatter.locale = Locale(identifier: "en_US_POSIX")

        while true {
            let key = formatter.string(from: calDate)
            guard let obj = data[key], Self.intValue(obj["attempted"]) > 0 else {
                break
            }
            streak += 1
            guard let prev = calendar.date(byAdding: .day, value: -1, to: calDate) else { break }
            calDate = prev
        }

        return streak
    }

    /// Ports `DailyStatsManager.getLastNDays(context, days)`: summed
    /// (attempted, correct) over today and the preceding `days - 1` days. Days
    /// absent from storage contribute zeros, matching the Kotlin `optInt` default,
    /// and a non-positive `days` yields `(0, 0)` as `repeat(days)` does.
    func getLastNDays(days: Int) -> (attempted: Int, correct: Int) {
        guard days > 0 else { return (0, 0) }

        let data = load()
        let calendar = Calendar.current
        let now = Date()

        let keyFormatter = DateFormatter()
        keyFormatter.dateFormat = "yyyyMMdd"
        keyFormatter.locale = Locale(identifier: "en_US_POSIX")

        var totalAttempted = 0
        var totalCorrect = 0

        for offset in 0..<days {
            guard let date = calendar.date(byAdding: .day, value: -offset, to: now) else { continue }
            let obj = data[keyFormatter.string(from: date)]
            totalAttempted += Self.intValue(obj?["attempted"])
            totalCorrect += Self.intValue(obj?["correct"])
        }

        return (totalAttempted, totalCorrect)
    }

    func getRankBadge() -> String {
        let accuracy = getOverallAccuracy()
        switch accuracy {
        case 90...100: return "🏆 Legend"
        case 80..<90: return "🔥 Master"
        case 70..<80: return "⚔️ Warrior"
        case 60..<70: return "🎯 Skilled"
        case 50..<60: return "📘 Rookie"
        default: return "🌱 Beginner"
        }
    }

    /// Retrieve graph trend data for the last N days: list of (DateLabel, AccuracyPercent).
    func getGraphData(days: Int) -> [(label: String, accuracy: Int)] {
        guard days > 0 else { return [] }

        let data = load()
        var list: [(label: String, accuracy: Int)] = []
        let calendar = Calendar.current
        let now = Date()

        let keyFormatter = DateFormatter()
        keyFormatter.dateFormat = "yyyyMMdd"
        keyFormatter.locale = Locale(identifier: "en_US_POSIX")

        let labelFormatter = DateFormatter()
        labelFormatter.dateFormat = "dd MMM"
        labelFormatter.locale = Locale(identifier: "en_US_POSIX")

        for i in 0..<days {
            if let date = calendar.date(byAdding: .day, value: -i, to: now) {
                let key = keyFormatter.string(from: date)
                let label = labelFormatter.string(from: date)
                let obj = data[key]
                let attempted = Self.intValue(obj?["attempted"])
                let correct = Self.intValue(obj?["correct"])
                let accuracy = calculateAccuracy(attempted: attempted, correct: correct)

                list.append((label, accuracy))
            }
        }

        return list.reversed()
    }

    /// Return topic accuracy list sorted by accuracy descending.
    func getTopicAccuracyList() -> [TopicAccuracyItem] {
        let topicMap = getTodayTopicWise()
        return topicMap.map { entry in
            let acc = calculateAccuracy(attempted: entry.value.attempted, correct: entry.value.correct)
            return TopicAccuracyItem(
                topic: entry.key,
                attempted: entry.value.attempted,
                correct: entry.value.correct,
                accuracy: acc
            )
        }.sorted { $0.accuracy > $1.accuracy }
    }

    /// Export raw JSON representation of daily stats.
    func exportRawJson() -> String {
        let data = load()
        guard let jsonData = try? JSONSerialization.data(withJSONObject: data),
              let str = String(data: jsonData, encoding: .utf8) else {
            return "{}"
        }
        return str
    }
}
