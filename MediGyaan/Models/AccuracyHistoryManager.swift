import Foundation

/// Period stats bucket matching Android's `AccuracyPeriodStats`.
struct AccuracyPeriodStats: Identifiable, Codable, Hashable {
    var id: String { label }
    let label: String
    let attempted: Int
    let correct: Int

    var accuracy: Int {
        guard attempted > 0 else { return 0 }
        return (correct * 100) / attempted
    }

    init(label: String, attempted: Int, correct: Int) {
        self.label = label
        self.attempted = attempted
        self.correct = correct
    }
}

/// Local persistence and calculation engine for accuracy history,
/// strictly porting `AccuracyHistoryManager.kt`.
final class AccuracyHistoryManager {

    static let shared = AccuracyHistoryManager()

    private let userDefaultsKey = "ACCURACY_HISTORY_PREF_DAILY_HISTORY"

    private init() {}

    private func todayKey() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyyMMdd"
        formatter.locale = Locale(identifier: "en_US_POSIX")
        return formatter.string(from: Date())
    }

    private func loadHistory() -> [String: [String: Int]] {
        guard let data = UserDefaults.standard.data(forKey: userDefaultsKey),
              let dict = try? JSONDecoder().decode([String: [String: Int]].self, from: data) else {
            return [:]
        }
        return dict
    }

    private func saveHistory(_ history: [String: [String: Int]]) {
        if let data = try? JSONEncoder().encode(history) {
            UserDefaults.standard.set(data, forKey: userDefaultsKey)
        }
    }

    func exportRawJson() -> String {
        let history = loadHistory()
        guard let data = try? JSONEncoder().encode(history),
              let str = String(data: data, encoding: .utf8) else {
            return "{}"
        }
        return str
    }

    /// Record a question answer attempt (isCorrect: true/false).
    func recordAnswer(isCorrect: BooleanLiteralType) {
        var history = loadHistory()
        let key = todayKey()

        var dayObj = history[key] ?? ["attempted": 0, "correct": 0]
        let attempted = (dayObj["attempted"] ?? 0) + 1
        let correct = (dayObj["correct"] ?? 0) + (isCorrect ? 1 : 0)

        dayObj["attempted"] = attempted
        dayObj["correct"] = correct
        history[key] = dayObj

        saveHistory(history)
    }

    /// Retrieve today's recorded stats.
    func getTodayStats() -> AccuracyPeriodStats {
        let history = loadHistory()
        let key = todayKey()
        let dayObj = history[key]

        let attempted = dayObj?["attempted"] ?? 0
        let correct = dayObj?["correct"] ?? 0

        return AccuracyPeriodStats(label: "Today", attempted: attempted, correct: correct)
    }

    /// Retrieve last N days performance.
    func getLastNDays(days: Int) -> [AccuracyPeriodStats] {
        let history = loadHistory()
        let keyFormatter = DateFormatter()
        keyFormatter.dateFormat = "yyyyMMdd"
        keyFormatter.locale = Locale(identifier: "en_US_POSIX")

        let labelFormatter = DateFormatter()
        labelFormatter.dateFormat = "dd MMM"
        labelFormatter.locale = Locale(identifier: "en_US_POSIX")

        var result: [AccuracyPeriodStats] = []
        let calendar = Calendar.current
        let now = Date()

        for i in stride(from: days - 1, through: 0, by: -1) {
            if let date = calendar.date(byAdding: .day, value: -i, to: now) {
                let key = keyFormatter.string(from: date)
                let label = labelFormatter.string(from: date)

                let dayObj = history[key]
                let attempted = dayObj?["attempted"] ?? 0
                let correct = dayObj?["correct"] ?? 0

                result.append(AccuracyPeriodStats(label: label, attempted: attempted, correct: correct))
            }
        }

        return result
    }

    /// Retrieve last N weeks aggregated performance.
    func getLastNWeeks(weeks: Int) -> [AccuracyPeriodStats] {
        let history = loadHistory()
        let calendar = Calendar.current
        let keyFormatter = DateFormatter()
        keyFormatter.dateFormat = "yyyyMMdd"
        keyFormatter.locale = Locale(identifier: "en_US_POSIX")

        var result: [AccuracyPeriodStats] = []
        let now = Date()

        for w in stride(from: weeks - 1, through: 0, by: -1) {
            guard let endOfTargetWeek = calendar.date(byAdding: .weekOfYear, value: -w, to: now) else { continue }

            var startOfWeek = endOfTargetWeek
            var interval: TimeInterval = 0
            _ = calendar.dateInterval(of: .weekOfYear, start: &startOfWeek, interval: &interval, for: endOfTargetWeek)

            var attempted = 0
            var correct = 0

            for d in 0..<7 {
                if let dayDate = calendar.date(byAdding: .day, value: d, to: startOfWeek) {
                    let key = keyFormatter.string(from: dayDate)
                    let dayObj = history[key]
                    attempted += dayObj?["attempted"] ?? 0
                    correct += dayObj?["correct"] ?? 0
                }
            }

            let label = "W\(weeks - w)"
            result.append(AccuracyPeriodStats(label: label, attempted: attempted, correct: correct))
        }

        return result
    }

    /// Retrieve last N months aggregated performance.
    func getLastNMonths(months: Int) -> [AccuracyPeriodStats] {
        let history = loadHistory()
        let calendar = Calendar.current
        let keyFormatter = DateFormatter()
        keyFormatter.dateFormat = "yyyyMMdd"
        keyFormatter.locale = Locale(identifier: "en_US_POSIX")

        let labelFormatter = DateFormatter()
        labelFormatter.dateFormat = "MMM yy"
        labelFormatter.locale = Locale(identifier: "en_US_POSIX")

        var result: [AccuracyPeriodStats] = []
        let now = Date()

        for m in stride(from: months - 1, through: 0, by: -1) {
            guard let monthDate = calendar.date(byAdding: .month, value: -m, to: now) else { continue }

            guard let monthInterval = calendar.dateInterval(of: .month, for: monthDate) else { continue }

            var attempted = 0
            var correct = 0
            var walkDate = monthInterval.start

            while walkDate < monthInterval.end {
                let key = keyFormatter.string(from: walkDate)
                let dayObj = history[key]
                attempted += dayObj?["attempted"] ?? 0
                correct += dayObj?["correct"] ?? 0

                guard let next = calendar.date(byAdding: .day, value: 1, to: walkDate) else { break }
                walkDate = next
            }

            let label = labelFormatter.string(from: monthDate)
            result.append(AccuracyPeriodStats(label: label, attempted: attempted, correct: correct))
        }

        return result
    }
}
