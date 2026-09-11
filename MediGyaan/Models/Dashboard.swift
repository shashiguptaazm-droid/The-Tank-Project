import Foundation

/// Aggregated statistics rendered by the dashboard (`dash_api.php`).
struct DashboardStats: Decodable, Hashable {
    let userId: Int
    let name: String
    let attempted: Int
    let correct: Int
    let wrong: Int
    let accuracy: Double
    let streak: Int
    let rank: Int
    let points: Int
    let todayAttempted: Int
    let todayCorrect: Int
    let totalTests: Int
    let message: String

    var accuracyPercentText: String {
        String(format: "%.1f%%", accuracy > 1 ? accuracy : accuracy * 100)
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        userId = container.flexInt("user_id", "userId", "id")
        name = container.flexString("name", "username")
        attempted = container.flexInt("attempted", "total_attempted", "overall_attempted")
        correct = container.flexInt("correct", "total_correct", "overall_correct")
        wrong = container.flexInt("wrong", "total_wrong", "incorrect")
        accuracy = container.flexDouble("accuracy", "overall_accuracy", "percent")
        streak = container.flexInt("streak", "local_streak", "daily_streak")
        rank = container.flexInt("rank", "rank_no", "position")
        points = container.flexInt("points", "score", "total_points")
        todayAttempted = container.flexInt("today_attempted")
        todayCorrect = container.flexInt("today_correct")
        totalTests = container.flexInt("total_tests", "tests", "test_count")
        let error = container.flexString("error")
        message = error.isEmpty ? container.flexString("message") : error
    }

    /// Empty state used before the first successful fetch.
    static let empty = DashboardStats()

    init() {
        userId = 0
        name = ""
        attempted = 0
        correct = 0
        wrong = 0
        accuracy = 0
        streak = 0
        rank = 0
        points = 0
        todayAttempted = 0
        todayCorrect = 0
        totalTests = 0
        message = ""
    }
}

/// Per-day accuracy bucket backing the progress chart, mirroring the Android
/// `DailyStatsManager` / `AccuracyHistoryManager` structures.
struct DailyStat: Codable, Identifiable, Hashable {
    var id: String { day }
    let day: String
    let attempted: Int
    let correct: Int

    var accuracy: Double {
        guard attempted > 0 else { return 0 }
        return Double(correct) / Double(attempted)
    }

    init(day: String, attempted: Int, correct: Int) {
        self.day = day
        self.attempted = attempted
        self.correct = correct
    }
}

/// Referral summary from `referral.php` / `api/referral_api.php`.
struct ReferralInfo: Decodable, Hashable {
    let code: String
    let totalReferrals: Int
    let successfulReferrals: Int
    let pointsEarned: Int
    let shareURL: URL?
    let message: String

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        code = container.flexString("referral_code", "code", "referralCode")
        totalReferrals = container.flexInt("total_referrals", "referrals", "total")
        successfulReferrals = container.flexInt("successful_referrals", "successful", "completed")
        pointsEarned = container.flexInt("points_earned", "points", "earned")
        let url = container.flexString("share_url", "url", "link")
        shareURL = url.isEmpty ? nil : URL(string: url)
        let error = container.flexString("error")
        message = error.isEmpty ? container.flexString("message") : error
    }

    init(
        code: String,
        totalReferrals: Int = 0,
        successfulReferrals: Int = 0,
        pointsEarned: Int = 0,
        shareURL: URL? = nil,
        message: String = ""
    ) {
        self.code = code
        self.totalReferrals = totalReferrals
        self.successfulReferrals = successfulReferrals
        self.pointsEarned = pointsEarned
        self.shareURL = shareURL
        self.message = message
    }
}

/// A college/university entry from the college predictor.
struct College: Decodable, Identifiable, Hashable {
    let id: Int
    let name: String
    let state: String
    let seats: Int
    let openingRank: Int
    let closingRank: Int
    let fees: String
    let website: URL?

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        id = container.flexInt("college_id", "id")
        name = container.flexString("college", "college_name", "name", "institute")
        state = container.flexString("state", "location")
        seats = container.flexInt("seats", "total_seats")
        openingRank = container.flexInt("opening_rank", "rank_from")
        closingRank = container.flexInt("closing_rank", "rank_to")
        fees = container.flexString("fees", "fee", "tuition")
        let site = container.flexString("website", "url", "link")
        website = site.isEmpty ? nil : URL(string: site)
    }
}
