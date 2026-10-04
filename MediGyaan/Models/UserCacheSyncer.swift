import Foundation

/// Synchronizes local stats and accuracy history to the backend.
/// 1:1 port of Android `UserCacheSyncer.kt`.
public enum UserCacheSyncer {

    private static let syncURL = URL(string: "https://medigyaan.com/Neurons/api/sync_user_cache.php")!

    public static func sync(userId: Int) async {
        guard userId > 0 else { return }

        let overall = DailyStatsManager.shared.getOverallStats()
        let today = DailyStatsManager.shared.getToday()
        let streak = DailyStatsManager.shared.getCurrentStreak()

        let formFields: [String: String] = [
            "user_id": String(userId),
            "daily_stats_json": DailyStatsManager.shared.exportRawJson(),
            "accuracy_history_json": AccuracyHistoryManager.shared.exportRawJson(),
            "overall_attempted": String(overall.attempted),
            "overall_correct": String(overall.correct),
            "today_attempted": String(today.attempted),
            "today_correct": String(today.correct),
            "local_streak": String(streak)
        ]

        var request = URLRequest(url: syncURL)
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")

        let bodyString = formFields
            .map { key, value in
                let escapedKey = key.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? key
                let escapedVal = value.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? value
                return "\(escapedKey)=\(escapedVal)"
            }
            .joined(separator: "&")

        request.httpBody = bodyString.data(using: .utf8)

        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
                // Synced successfully
            }
        } catch {
            // Background sync error handled gracefully
        }
    }
}
