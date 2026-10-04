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
final class DailyStatsManager {

    static let shared = DailyStatsManager()

    private let userDefaultsKey = "MCQ_STATS_HISTORY_DAILY_DATA"

    private init() {}

    private func getTodayKey() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyyMMdd"
        formatter.locale = Locale(identifier: "en_US_POSIX")
        return formatter.string(from: Date())
    }

    private func load() -> [String: [String: Any]] {
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
        let cleanTopic = topic.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "General" : topic.trimmingCharacters(in: .whitespacesAndNewlines)
        var data = load()
        let today = getTodayKey()

        var todayObj = data[today] ?? [
            "attempted": 0,
            "correct": 0,
            "topics": [String: [String: Int]]()
        ]

        let attempted = (todayObj["attempted"] as? Int ?? 0) + 1
        let correct = (todayObj["correct"] as? Int ?? 0) + (isCorrect ? 1 : 0)

        todayObj["attempted"] = attempted
        todayObj["correct"] = correct

        var topicsObj = (todayObj["topics"] as? [String: [String: Int]]) ?? [:]
        var topicObj = topicsObj[cleanTopic] ?? ["attempted": 0, "correct": 0]

        let topicAttempted = (topicObj["attempted"] ?? 0) + 1
        let topicCorrect = (topicObj["correct"] ?? 0) + (isCorrect ? 1 : 0)

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
        let attempted = obj["attempted"] as? Int ?? 0
        let correct = obj["correct"] as? Int ?? 0
        return (attempted, correct)
    }

    /// Retrieve today's topic-wise map: Topic -> (attempted, correct)
    func getTodayTopicWise() -> [String: (attempted: Int, correct: Int)] {
        var result: [String: (attempted: Int, correct: Int)] = [:]
        let data = load()
        let today = getTodayKey()

        guard let todayObj = data[today],
              let topicsObj = todayObj["topics"] as? [String: [String: Int]] else {
            return result
        }

        for (topic, dict) in topicsObj {
            let attempted = dict["attempted"] ?? 0
            let correct = dict["correct"] ?? 0
            result[topic] = (attempted, correct)
        }

        return result
    }

    /// Retrieve overall stats across all recorded days.
    func getOverallStats() -> (attempted: Int, correct: Int) {
        let data = load()
        var attempted = 0
        var correct = 0

        for (_, dayObj) in data {
            attempted += dayObj["attempted"] as? Int ?? 0
            correct += dayObj["correct"] as? Int ?? 0
        }

        return (attempted, correct)
    }

    func getOverallAccuracy() -> Int {
        let stats = getOverallStats()
        return calculateAccuracy(attempted: stats.attempted, correct: stats.correct)
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
            guard let obj = data[key],
                  let attempted = obj["attempted"] as? Int,
                  attempted > 0 else {
                break
            }
            streak += 1
            guard let prev = calendar.date(byAdding: .day, value: -1, to: calDate) else { break }
            calDate = prev
        }

        return streak
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
                let attempted = obj?["attempted"] as? Int ?? 0
                let correct = obj?["correct"] as? Int ?? 0
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
}
