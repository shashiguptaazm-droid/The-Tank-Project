import SwiftUI
import WidgetKit

/// iOS App Widget Data Manager.
///
/// 1:1 port of Android `NeetAppWidget.kt` & `NeetWidgetActivity.kt`.
/// Manages NEET exam countdowns, daily streak tracking, active live challenge alerts,
/// and synchronizes data with iOS WidgetKit timelines and Shared App Groups.
public final class NeetWidgetManager: ObservableObject {

    public static let shared = NeetWidgetManager()
    private let userDefaults = UserDefaults(suiteName: "group.com.corp.medigyaan") ?? UserDefaults.standard

    @Published public private(set) var examName: String = "NEET PG"
    @Published public private(set) var examDateString: String = "2026-06-15"
    @Published public private(set) var daysRemaining: Int = 0
    @Published public private(set) var hasActiveChallenge: Bool = false
    @Published public private(set) var challengeHostName: String = ""

    private init() {
        loadSettings()
        calculateDaysRemaining()
    }

    public func loadSettings() {
        examName = userDefaults.string(forKey: "selected_exam_name") ?? "NEET PG"
        examDateString = userDefaults.string(forKey: "selected_exam_date") ?? "2026-06-15"
        hasActiveChallenge = userDefaults.bool(forKey: "has_challenge")
        challengeHostName = userDefaults.string(forKey: "challenge_host_name") ?? ""
        calculateDaysRemaining()
    }

    public func saveSettings(name: String, dateString: String) {
        examName = name
        examDateString = dateString
        userDefaults.set(name, forKey: "selected_exam_name")
        userDefaults.set(dateString, forKey: "selected_exam_date")
        calculateDaysRemaining()
        WidgetCenter.shared.reloadAllTimelines()
    }

    public func setChallengeAlert(hostName: String, challengeId: String) {
        hasActiveChallenge = true
        challengeHostName = hostName
        userDefaults.set(true, forKey: "has_challenge")
        userDefaults.set(hostName, forKey: "challenge_host_name")
        userDefaults.set(challengeId, forKey: "challenge_id")
        userDefaults.set(Date().timeIntervalSince1970, forKey: "challenge_time")
        WidgetCenter.shared.reloadAllTimelines()
    }

    public func clearChallengeAlert() {
        hasActiveChallenge = false
        userDefaults.set(false, forKey: "has_challenge")
        userDefaults.removeObject(forKey: "challenge_host_name")
        userDefaults.removeObject(forKey: "challenge_id")
        WidgetCenter.shared.reloadAllTimelines()
    }

    private func calculateDaysRemaining() {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        if let targetDate = formatter.date(from: examDateString) {
            let cal = Calendar.current
            let diff = cal.dateComponents([.day], from: Date(), to: targetDate)
            daysRemaining = max(0, diff.day ?? 0)
        } else {
            daysRemaining = 0
        }
    }
}
