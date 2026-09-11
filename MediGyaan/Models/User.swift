import Foundation

/// A MediGyaan account. Mirrors the columns returned by `api/login.php`,
/// `get_profilev1.php`, and the `sync_user_cache.php` payloads.
struct User: Decodable, Identifiable, Hashable {
    let id: Int
    let name: String
    let email: String
    let phone: String
    let avatarURL: URL?
    let college: String
    let course: String
    let referralCode: String
    let isVerified: Bool
    let streak: Int
    let overallAttempted: Int
    let overallCorrect: Int

    var accuracy: Double {
        guard overallAttempted > 0 else { return 0 }
        return Double(overallCorrect) / Double(overallAttempted)
    }

    var initials: String {
        let parts = name.split(separator: " ").prefix(2)
        let letters = parts.compactMap { $0.first }.map(String.init)
        return letters.joined().uppercased()
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        id = container.flexInt("user_id", "userId", "id")
        name = container.flexString("name", "full_name", "username")
        email = container.flexString("email")
        phone = container.flexString("phone", "mobile")
        let avatar = container.flexString("avatar", "avatar_url", "profile_pic", "image")
        avatarURL = avatar.isEmpty ? nil : URL(string: avatar)
        college = container.flexString("college", "institution")
        course = container.flexString("course", "stream")
        referralCode = container.flexString("referral_code", "referralCode")
        isVerified = container.flexBool("verified", "is_verified")
        streak = container.flexInt("streak", "local_streak", "daily_streak")
        overallAttempted = container.flexInt("overall_attempted", "total_attempted")
        overallCorrect = container.flexInt("overall_correct", "total_correct")
    }

    /// Memberwise initialiser for previews and tests.
    init(
        id: Int,
        name: String,
        email: String,
        phone: String = "",
        avatarURL: URL? = nil,
        college: String = "",
        course: String = "",
        referralCode: String = "",
        isVerified: Bool = true,
        streak: Int = 0,
        overallAttempted: Int = 0,
        overallCorrect: Int = 0
    ) {
        self.id = id
        self.name = name
        self.email = email
        self.phone = phone
        self.avatarURL = avatarURL
        self.college = college
        self.course = course
        self.referralCode = referralCode
        self.isVerified = isVerified
        self.streak = streak
        self.overallAttempted = overallAttempted
        self.overallCorrect = overallCorrect
    }
}

/// Response of `api/login.php`:
/// `{"success":true,"user_id":12,"name":"..."}`.
struct LoginResponse: Decodable {
    let success: Bool
    let userId: Int
    let name: String
    let email: String
    let token: String
    let message: String

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        success = container.flexBool("success")
        userId = container.flexInt("user_id", "userId", "id")
        name = container.flexString("name")
        email = container.flexString("email")
        token = container.flexString("token", "auth_token", "access_token")
        // The backend uses `error` for failures and `message` otherwise.
        let error = container.flexString("error")
        message = error.isEmpty ? container.flexString("message") : error
    }
}

/// Generic acknowledgement used by the many scripts that only return an
/// envelope: `{"success":true,"message":"Saved"}`.
struct Acknowledgment: Decodable {
    let success: Bool
    let message: String

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        success = container.flexBool("success")
        let error = container.flexString("error")
        message = error.isEmpty ? container.flexString("message") : error
    }
}

/// Payload written by `api/sync_user_cache.php` (which reads `$_POST`).
struct UserCachePayload {
    let userId: Int
    let dailyStatsJSON: String
    let accuracyHistoryJSON: String
    let overallAttempted: Int
    let overallCorrect: Int
    let todayAttempted: Int
    let todayCorrect: Int
    let localStreak: Int

    /// Form fields exactly as the PHP script expects them.
    var formFields: [String: String] {
        [
            "user_id": String(userId),
            "daily_stats_json": dailyStatsJSON,
            "accuracy_history_json": accuracyHistoryJSON,
            "overall_attempted": String(overallAttempted),
            "overall_correct": String(overallCorrect),
            "today_attempted": String(todayAttempted),
            "today_correct": String(todayCorrect),
            "local_streak": String(localStreak),
        ]
    }
}
