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
///
/// Storage shape mirrors the Android `SharedPreferences` file
/// `ACCURACY_HISTORY_PREF` / key `daily_history`, collapsed into the single
/// `UserDefaults` key `"ACCURACY_HISTORY_PREF_DAILY_HISTORY"`:
///
///     { "20250101": { "attempted": 12, "correct": 9 }, ... }
///
/// Accuracy is always `(correct * 100) / attempted` — integer division, so it
/// truncates. A bucket with `attempted <= 0` reports `0`, which is how days the
/// user never studied appear as flat zero on the trend chart.
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

    // MARK: - Formatters (ports of the Kotlin `SimpleDateFormat` instances)

    /// Ports the `SimpleDateFormat("yyyyMMdd", Locale.getDefault())` instances
    /// built inline by `todayKey()`, `getLastNDays()`, `getLastNWeeks()` and
    /// `getLastNMonths()`. `en_US_POSIX` pins the Gregorian calendar so the
    /// bucket key can never drift with the user's locale.
    private static func makeDayKeyFormatter() -> DateFormatter {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyyMMdd"
        formatter.locale = Locale(identifier: "en_US_POSIX")
        return formatter
    }

    /// Ports `SimpleDateFormat("dd MMM", Locale.getDefault())` used by
    /// `getLastNDays()` for the chart's x-axis labels.
    private static func makeDayLabelFormatter() -> DateFormatter {
        let formatter = DateFormatter()
        formatter.dateFormat = "dd MMM"
        formatter.locale = Locale(identifier: "en_US_POSIX")
        return formatter
    }

    /// Ports `SimpleDateFormat("MMM yy", Locale.getDefault())` used by
    /// `getLastNMonths()` for the month bucket label.
    private static func makeMonthLabelFormatter() -> DateFormatter {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMM yy"
        formatter.locale = Locale(identifier: "en_US_POSIX")
        return formatter
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

    /// Ports `AccuracyHistoryManager.exportRawJson(context)`. The string is the
    /// payload posted to `sync_user_cache.php` as `accuracy_history_json`, so it
    /// must stay the same `{"yyyyMMdd": {"attempted": Int, "correct": Int}}`
    /// shape Android produces — not a Swift `Codable` envelope.
    func exportRawJson() -> String {
        let history = loadHistory()
        guard let data = try? JSONEncoder().encode(history),
              let str = String(data: data, encoding: .utf8) else {
            return "{}"
        }
        return str
    }

    /// Record a question answer attempt (isCorrect: true/false).
    ///
    /// Ports `AccuracyHistoryManager.recordAnswer(context, isCorrect)`. Note the
    /// parameter type is spelled `BooleanLiteralType`, which is a stdlib
    /// typealias for `Bool`; every call site passes a plain `Bool` variable.
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

    // MARK: - Anchor-injected variants
    //
    // Android hardcodes its time anchor as `Calendar.getInstance()`, so none of
    // the Kotlin bucket builders can be driven from a SwiftUI preview, a
    // snapshot test, or a historical re-read. Each method below is the same
    // algorithm with the anchor passed in; the `()`-only overloads simply
    // forward `Date()`.

    /// Read-only structured form of the store, ports Kotlin's private
    /// `loadHistory(context)`. Consumers that need the raw `yyyyMMdd` buckets
    /// (rather than the `exportRawJson()` string) can use this instead of
    /// re-parsing the exported payload.
    func dailyHistorySnapshot() -> [String: [String: Int]] {
        return loadHistory()
    }

    /// Ports `AccuracyHistoryManager.recordAnswer(context, isCorrect)` with the
    /// `Calendar.getInstance()` anchor replaced by `date`, so a caller can
    /// back-date a record. The stored bucket key is still `yyyyMMdd` of `date`.
    func recordAnswer(isCorrect: Bool, on date: Date) {
        var history = loadHistory()
        let key = Self.makeDayKeyFormatter().string(from: date)

        var dayObj = history[key] ?? ["attempted": 0, "correct": 0]
        let attempted = (dayObj["attempted"] ?? 0) + 1
        let correct = (dayObj["correct"] ?? 0) + (isCorrect ? 1 : 0)

        dayObj["attempted"] = attempted
        dayObj["correct"] = correct
        history[key] = dayObj

        saveHistory(history)
    }

    /// Ports `AccuracyHistoryManager.getTodayStats(context)` with an explicit
    /// day anchor. Label is always `"Today"`, matching Kotlin.
    func getTodayStats(on date: Date) -> AccuracyPeriodStats {
        let history = loadHistory()
        let key = Self.makeDayKeyFormatter().string(from: date)
        let dayObj = history[key]

        let attempted = dayObj?["attempted"] ?? 0
        let correct = dayObj?["correct"] ?? 0

        return AccuracyPeriodStats(label: "Today", attempted: attempted, correct: correct)
    }

    /// Ports `AccuracyHistoryManager.getLastNDays(context, days)` with an
    /// explicit anchor. Oldest bucket first, labels `"dd MMM"`, one bucket per
    /// calendar day including days with no attempts (reported as 0/0).
    func getLastNDays(days: Int, endingAt date: Date) -> [AccuracyPeriodStats] {
        let history = loadHistory()
        let keyFormatter = Self.makeDayKeyFormatter()
        let labelFormatter = Self.makeDayLabelFormatter()

        var result: [AccuracyPeriodStats] = []
        let calendar = Calendar.current

        for i in stride(from: days - 1, through: 0, by: -1) {
            if let dayDate = calendar.date(byAdding: .day, value: -i, to: date) {
                let key = keyFormatter.string(from: dayDate)
                let label = labelFormatter.string(from: dayDate)

                let dayObj = history[key]
                let attempted = dayObj?["attempted"] ?? 0
                let correct = dayObj?["correct"] ?? 0

                result.append(AccuracyPeriodStats(label: label, attempted: attempted, correct: correct))
            }
        }

        return result
    }

    /// Ports `AccuracyHistoryManager.getLastNWeeks(context, weeks)` with an
    /// explicit anchor. Walks the whole calendar week containing the anchored
    /// date, from `firstWeekday` through +6 days, and labels buckets
    /// `"W1"…"W<n>"` oldest first.
    func getLastNWeeks(weeks: Int, endingAt date: Date) -> [AccuracyPeriodStats] {
        let history = loadHistory()
        let calendar = Calendar.current
        let keyFormatter = Self.makeDayKeyFormatter()

        var result: [AccuracyPeriodStats] = []

        for w in stride(from: weeks - 1, through: 0, by: -1) {
            guard let endOfTargetWeek = calendar.date(byAdding: .weekOfYear, value: -w, to: date) else { continue }

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

    /// Ports `AccuracyHistoryManager.getLastNMonths(context, months)` with an
    /// explicit anchor. Sums every day of each calendar month the anchor minus
    /// `months - 1` reaches, labelled `"MMM yy"`, oldest first.
    func getLastNMonths(months: Int, endingAt date: Date) -> [AccuracyPeriodStats] {
        let history = loadHistory()
        let calendar = Calendar.current
        let keyFormatter = Self.makeDayKeyFormatter()
        let labelFormatter = Self.makeMonthLabelFormatter()

        var result: [AccuracyPeriodStats] = []

        for m in stride(from: months - 1, through: 0, by: -1) {
            guard let monthDate = calendar.date(byAdding: .month, value: -m, to: date) else { continue }
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

    // MARK: - Today-anchored entry points (unchanged signatures)

    /// Retrieve today's recorded stats. Ports
    /// `AccuracyHistoryManager.getTodayStats(context)`.
    func getTodayStats() -> AccuracyPeriodStats {
        return getTodayStats(on: Date())
    }

    /// Retrieve last N days performance. Ports
    /// `AccuracyHistoryManager.getLastNDays(context, days)`.
    func getLastNDays(days: Int) -> [AccuracyPeriodStats] {
        return getLastNDays(days: days, endingAt: Date())
    }

    /// Retrieve last N weeks aggregated performance. Ports
    /// `AccuracyHistoryManager.getLastNWeeks(context, weeks)`.
    func getLastNWeeks(weeks: Int) -> [AccuracyPeriodStats] {
        return getLastNWeeks(weeks: weeks, endingAt: Date())
    }

    /// Retrieve last N months aggregated performance. Ports
    /// `AccuracyHistoryManager.getLastNMonths(context, months)`.
    func getLastNMonths(months: Int) -> [AccuracyPeriodStats] {
        return getLastNMonths(months: months, endingAt: Date())
    }
}