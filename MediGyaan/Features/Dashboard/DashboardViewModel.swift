import Foundation

// Ports `DashboardActivity.kt` (1464 lines) — the app's home screen.
//
// The Kotlin activity mixed six concerns into one class: rank/XP math, the
// `dash_api.php` and `get_profilev1.php` fetches, the predicted-rank round trip,
// the topic scroller, the daily challenge, and a mobile-verification prompt that
// fires on every `onResume`. Each becomes a value type below and a loader on
// ``DashboardViewModel``; SwiftUI has no `onResume`, so the re-entrant half of
// that lifecycle (`loadDashboardAccuracyStats`, `setupCategoryCards`,
// `checkActiveInvitations`) is driven by the view's `.task` and `.refreshable`.

// MARK: - Rank tiers

/// Ports `RankInfo`, `getRankInfo(rankTitle:)` and `getRankInfoFromExp(exp:)` —
/// the nine XP bands the dashboard badge cycles through, each with its tier
/// drawable and the emoji `txtBadgeEmoji` was sized to hold.
struct DashboardRankTier: Hashable {

    /// `RankInfo.title` — already upper-cased by `getRankInfo`.
    let title: String

    /// `RankInfo.drawable`, e.g. `R.drawable.ic_legend`.
    let artwork: AndroidAsset

    /// `RankInfo.emoji`.
    let emoji: String

    /// `RankInfo.minXp` — the XP floor for this band.
    let minimumXP: Int

    static let legend = DashboardRankTier(title: "LEGEND", artwork: .ic_legend, emoji: "🏆", minimumXP: 100_000)
    static let grandmaster = DashboardRankTier(title: "GRANDMASTER", artwork: .ic_grandmaster, emoji: "👑", minimumXP: 60_000)
    static let master = DashboardRankTier(title: "MASTER", artwork: .ic_master, emoji: "🔱", minimumXP: 30_000)
    static let scholar = DashboardRankTier(title: "SCHOLAR", artwork: .ic_scholar, emoji: "📚", minimumXP: 15_000)
    static let expert = DashboardRankTier(title: "EXPERT", artwork: .ic_expert, emoji: "⚔️", minimumXP: 7_500)
    static let warrior = DashboardRankTier(title: "WARRIOR", artwork: .ic_warrior, emoji: "🛡️", minimumXP: 3_500)
    static let skilled = DashboardRankTier(title: "SKILLED", artwork: .ic_skilled, emoji: "🎯", minimumXP: 1_500)
    static let rookie = DashboardRankTier(title: "ROOKIE", artwork: .ic_rookie, emoji: "🚀", minimumXP: 500)
    static let aspirant = DashboardRankTier(title: "ASPIRANT", artwork: .ic_beginner, emoji: "🌱", minimumXP: 0)

    /// Descending by `minimumXP`, the order `showRankInfoDialog()` printed the
    /// progression table in.
    static let progression: [DashboardRankTier] = [
        legend, grandmaster, master, scholar, expert, warrior, skilled, rookie, aspirant,
    ]

    /// `getRankInfo(rankTitle:)`: lower-cased and trimmed lookup, where both
    /// "aspirant" and "beginner" resolve to the bottom band and anything
    /// unrecognised falls back to it too.
    static func named(_ rawTitle: String) -> DashboardRankTier {
        switch rawTitle.lowercased().trimmingCharacters(in: .whitespacesAndNewlines) {
        case "legend": return legend
        case "grandmaster": return grandmaster
        case "master": return master
        case "scholar": return scholar
        case "expert": return expert
        case "warrior": return warrior
        case "skilled": return skilled
        case "rookie": return rookie
        default: return aspirant
        }
    }

    /// `getRankInfoFromExp(exp:)`: the highest band the experience clears.
    static func forExperience(_ experience: Int) -> DashboardRankTier {
        progression.first { experience >= $0.minimumXP } ?? aspirant
    }

    /// The body of `showRankInfoDialog()`, which the Kotlin activity declared
    /// but never invoked.
    var progressionSheet: String {
        var lines = "Current Rank: \(title)\n\nRequired XP for Ranks:"
        for tier in DashboardRankTier.progression {
            lines += "\n\(tier.title): \(tier.minimumXP) XP"
        }
        return lines
    }
}

// MARK: - Profile

/// Ports `applyProfileResponse` — the subset of the `get_profilev1.php` payload
/// the dashboard itself renders. The Kotlin activity wrote `name`, `photo_url`,
/// `user_phone`, `phone_verified` and `user_exp` straight into
/// `SharedPreferences("MY_APP")` before touching the views.
struct DashboardProfile: Hashable {

    let name: String
    let photoURL: URL?
    let wins: Int
    let streak: Int
    let level: Int
    let experience: Int
    let rankTitle: String
    let mobileNumber: String
    let isMobileVerified: Bool

    static let empty = DashboardProfile(
        name: "",
        photoURL: nil,
        wins: 0,
        streak: 0,
        level: 1,
        experience: 0,
        rankTitle: "ASPIRANT",
        mobileNumber: "",
        isMobileVerified: false
    )

    init(
        name: String,
        photoURL: URL?,
        wins: Int,
        streak: Int,
        level: Int,
        experience: Int,
        rankTitle: String,
        mobileNumber: String,
        isMobileVerified: Bool
    ) {
        self.name = name
        self.photoURL = photoURL
        self.wins = wins
        self.streak = streak
        self.level = level
        self.experience = experience
        self.rankTitle = rankTitle
        self.mobileNumber = mobileNumber
        self.isMobileVerified = isMobileVerified
    }

    /// `applyProfileResponse` reads `data` off the root and falls back to the
    /// root itself when the envelope is absent.
    init(json: [String: Any]) {
        self.init(
            name: json["name"] as? String ?? "",
            photoURL: DashboardProfile.normalizedPhotoURL(json["photo"] as? String ?? ""),
            wins: json["wins"] as? Int ?? 0,
            streak: json["streak"] as? Int ?? 0,
            level: json["level"] as? Int ?? 1,
            experience: json["exp"] as? Int ?? 0,
            rankTitle: (json["rank_title"] as? String) ?? "ASPIRANT",
            mobileNumber: (json["mobile_no"] as? String ?? "").trimmingCharacters(in: .whitespaces),
            isMobileVerified: DashboardProfile.isVerifiedFlag(json["mobile_verified"])
        )
    }

    /// `setupHeader()`'s normalisation of `photo_url`: a relative path is
    /// stripped of any `../` or `./` segments and re-rooted on the backend,
    /// while an absolute URL is left alone.
    static func normalizedPhotoURL(_ photo: String) -> URL? {
        let trimmed = photo.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        if trimmed.hasPrefix("http") { return URL(string: trimmed) }
        let clean = trimmed
            .replacingOccurrences(of: "../", with: "")
            .replacingOccurrences(of: "./", with: "")
            .trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        return URL(string: BackendEndpoints.base + clean)
    }

    /// `optInt("mobile_verified", 0) == 1 || optBoolean("mobile_verified", false)`,
    /// tolerating the string form the PHP script also emits.
    private static func isVerifiedFlag(_ flag: Any?) -> Bool {
        if let number = flag as? Int { return number == 1 }
        if let flag = flag as? Bool { return flag }
        if let text = flag as? String { return text == "1" || text.lowercased() == "true" }
        return false
    }
}

// MARK: - Predicted rank

/// Ports the predicted-rank payload shared by `fetchPredictionFromServer`
/// (`predict_rank.php`) and `loadPredictedRankFromServer`
/// (`api_load_predicted_rank.php`). Both wrote the same four
/// `SharedPreferences` keys, which `loadPredictedRankFromPrefs` then re-read.
struct DashboardRankPrediction: Hashable {

    /// `"$minRank - $maxRank"`, verbatim — the server returns both bounds as
    /// strings, not numbers.
    let range: String
    let tier: String
    let confidence: Int
    let timestamp: Int

    init(range: String, tier: String, confidence: Int, timestamp: Int) {
        self.range = range
        self.tier = tier
        self.confidence = confidence
        self.timestamp = timestamp
    }

    init(json: [String: Any], timestamp: Int) {
        let minRank = json["predicted_min_rank"] as? String ?? ""
        let maxRank = json["predicted_max_rank"] as? String ?? ""
        self.init(
            range: minRank.isEmpty && maxRank.isEmpty ? "" : "\(minRank) - \(maxRank)",
            tier: json["tier"] as? String ?? "",
            confidence: json["confidence"] as? Int ?? 0,
            timestamp: (json["timestamp"] as? Int) ?? timestamp
        )
    }

    /// `"Confidence ${confidence}% - $tier"` for `txtPredictedConfidence`.
    var confidenceText: String { "Confidence \(confidence)% - \(tier)" }
}

// MARK: - Topics

/// Ports `TopicData` and the response mapping inside `TopicSelectorList`.
struct DashboardTopic: Identifiable, Hashable {

    let name: String
    let count: Int

    var id: String { name }

    /// `mode == "KING_OF_TOPIC" && topic.count < 200` — the topic renders greyed
    /// out, states how many questions it has, and swallows the tap.
    var isKingOfTopicLocked: Bool { count < 200 }

    /// `"Need 200 Qs (${topic.count} now)"`.
    var lockNote: String { "Need 200 Qs (\(count) now)" }
}

// MARK: - Daily challenge

/// Ports `loadTodayFirstQuestion()` — a single `getQuestions.php` row with the
/// leading question number stripped.
struct DashboardQuestionPreview: Hashable {

    let question: String
    let options: [String]

    init(question: String, options: [String]) {
        self.question = question
        self.options = options
    }

    init(json: [String: Any]) {
        self.init(
            question: DashboardQuestionPreview.stripLeadingNumber(json["question"] as? String ?? ""),
            options: [
                json["option_a"] as? String ?? "",
                json["option_b"] as? String ?? "",
                json["option_c"] as? String ?? "",
                json["option_d"] as? String ?? "",
            ].filter { !$0.isEmpty }
        )
    }

    /// The Android build leaves the card blank when the request fails. iOS keeps
    /// the canned case the screen already shipped so an offline launch still
    /// shows something.
    static let fallback = DashboardQuestionPreview(
        question: "A 45-year-old patient presents with painless progressive loss of vision. What is the most likely initial diagnostic modality?",
        options: [
            "Slit-lamp biomicroscopy",
            "Optical Coherence Tomography",
            "Fundus Fluorescein Angiography",
            "B-Scan Ultrasonography",
        ]
    )

    /// `replace(Regex("^\\d+[.\\s\\-)]+\\s*"), "")`.
    private static func stripLeadingNumber(_ text: String) -> String {
        text.replacingOccurrences(of: #"^\d+[.\s\-)]+\s*"#, with: "", options: .regularExpression)
    }
}

// MARK: - Local stats

/// Ports the `DailyStatsManager` reads at the top of
/// `loadDashboardAccuracyStats()`. The Android four-up stat tile is sourced
/// entirely from local storage — `dash_api.php` never feeds it.
struct DashboardLocalStats: Hashable {

    let attempted: Int
    let correct: Int
    /// Already a whole percentage: `calculateAccuracy` returns `correct * 100 / attempted`.
    let accuracy: Int
    let streak: Int
    /// `getTotalBattles` — which the Kotlin manager defines as overall attempted.
    let battles: Int
    /// `getTotalWins` — overall correct.
    let wins: Int
    let todayAttempted: Int
    let todayCorrect: Int

    static let empty = DashboardLocalStats(
        attempted: 0,
        correct: 0,
        accuracy: 0,
        streak: 0,
        battles: 0,
        wins: 0,
        todayAttempted: 0,
        todayCorrect: 0
    )

    var accuracyText: String { "\(accuracy)%" }

    var todayAccuracyText: String? {
        guard todayAttempted > 0 else { return nil }
        return "\(todayCorrect)/\(todayAttempted) correct today"
    }

    /// The `txtMotivation` threshold ladder applied at the end of
    /// `loadDashboardAccuracyStats()`.
    var encouragement: String {
        if accuracy >= 85 { return "Legend pace. Keep the streak clean." }
        if accuracy >= 70 { return "Excellent consistency. Push one more battle." }
        return "Keep practicing every day."
    }

    /// Whether anything has been recorded yet — the screen falls back to the
    /// remote `dash_api.php` summary when nothing is.
    var hasHistory: Bool { attempted > 0 }
}

// MARK: - Mobile verification

/// The three states of `checkAndPromptMobileVerification`, which fired from
/// every `onResume` until the backend reported the number verified.
enum DashboardVerificationStage: Hashable {
    case hidden
    case phone
    case otp(phone: String)
}

// MARK: - View model

/// Backs `DashboardView`. Replaces `DashboardActivity`'s inline Volley calls.
///
/// The API client and user id arrive through `load(api:userId:subject:)`
/// rather than `init`, because a `@StateObject`'s wrapped value is get-only —
/// the view cannot rebuild the model once the SwiftUI environment (and
/// therefore the session) becomes available.
@MainActor
final class DashboardViewModel: ObservableObject {

    @Published private(set) var statsState: LoadState<DashboardStats> = .idle
    @Published private(set) var attempts: [AttemptSummary] = []

    /// `fetchProfileData` / `applyProfileResponse`. Never downgraded to
    /// `.empty` by a failed refresh, so the header keeps its last good values.
    @Published private(set) var profile: DashboardProfile = .empty
    @Published private(set) var prediction: DashboardRankPrediction?
    @Published private(set) var topicsState: LoadState<[DashboardTopic]> = .idle
    @Published private(set) var todayQuestion: DashboardQuestionPreview?
    @Published private(set) var localStats: DashboardLocalStats = .empty

    @Published private(set) var verification: DashboardVerificationStage = .hidden
    /// The `Toast` shown by the verification dialogs.
    @Published private(set) var verificationNotice: String?
    @Published private(set) var isVerifying: Bool = false

    @Published var errorMessage: String?

    /// The eight `setupCategoryCards()` subjects, keyed to `cardNeetPg` …
    /// `cardBcbr`.
    static let categories: [String] = [
        "NEET PG", "NEET UG", "UPSC", "CAT", "Commerce", "Law", "Computer Software", "BCBR",
    ]

    /// `expProgressBar` divides `exp % 1000` by 1000, so a level is 1000 XP wide.
    static let levelWidth = 1000

    // MARK: - Derived

    /// The dashboard never had a dedicated empty state — every TextView kept
    /// rendering zeros — so this stands in for `state.value ?? .empty`.
    var stats: DashboardStats { statsState.value ?? .empty }

    /// `updateBadgeUI(getRankInfoFromExp(getCurrentExp()))`.
    var rankTier: DashboardRankTier { DashboardRankTier.forExperience(profile.experience) }

    var experienceInLevel: Int { profile.experience % Self.levelWidth }

    // MARK: - Load

    /// Stands in for `onCreate` plus the `onResume` re-read of
    /// `selectedSubject` and the local accuracy stats.
    func load(api: MediGyaanAPI, userId: Int, subject: String) async {
        guard userId > 0 else {
            statsState = .failed("You need to be signed in to view your dashboard.")
            return
        }

        localStats = Self.readLocalStats()
        if statsState.value == nil { statsState = .loading }

        let fallbackStats = Self.cachedStats(userId: userId)

        async let attemptsResult: [AttemptSummary] = fetchAttempts(api: api, userId: userId)
        async let profileResult: DashboardProfile? = fetchProfile(userId: userId)
        async let predictionResult: DashboardRankPrediction? = fetchPrediction(userId: userId)
        async let topicsResult: LoadState<[DashboardTopic]> = fetchTopics(subject: subject)
        async let questionResult: DashboardQuestionPreview? = fetchTodayQuestion(userId: userId)

        let liveStats = await fetchStats(userId: userId)
        // `fetchDatabaseData` renders the cached body first and lets the live
        // one overwrite it; on a Volley error the cache is all the user sees.
        if case .failed = liveStats, let fallbackStats {
            statsState = .loaded(fallbackStats)
        } else {
            statsState = liveStats
        }

        self.attempts = await attemptsResult

        let fetchedProfile = await profileResult
        if let fetchedProfile { self.profile = fetchedProfile }

        let fetchedPrediction = await predictionResult
        if let fetchedPrediction { self.prediction = fetchedPrediction }

        topicsState = await topicsResult

        let fetchedQuestion = await questionResult
        if let fetchedQuestion { self.todayQuestion = fetchedQuestion }
    }

    /// `handleCategorySelection`'s `prefs.edit().putString(KEY_SELECTED_SUBJECT, …)`.
    func persistCategory(_ category: String) {
        UserDefaults.standard.set(category, forKey: Self.selectedSubjectKey)
    }

    // MARK: - Fetchers

    /// `fetchDatabaseData` — `POST dash_api.php` with `user_id`, cached in
    /// `FirebaseOnlineCache` for five minutes.
    private func fetchStats(userId: Int) async -> LoadState<DashboardStats> {
        do {
            let json = try await HTTPClient.shared.postObject(form: ["user_id": String(userId)], to: .dashboard)
            let data = try JSONSerialization.data(withJSONObject: json)
            FirebaseOnlineCache.putString(
                key: Self.statsCacheKey(userId),
                response: String(decoding: data, as: UTF8.self)
            )
            return .loaded(try JSONDecoder().decode(DashboardStats.self, from: data))
        } catch {
            RemoteLogger.log(tag: "DASH", message: "Volley error: \(error.localizedDescription)")
            return .failed(LoadState<DashboardStats>.message(for: error))
        }
    }

    private func fetchAttempts(api: MediGyaanAPI, userId: Int) async -> [AttemptSummary] {
        (try? await api.study.attempts(userId: userId)) ?? []
    }

    /// `fetchProfileData` — `GET get_profilev1.php?user_id=…&viewer_id=…`,
    /// cached for ten minutes, then `applyProfileResponse`.
    private func fetchProfile(userId: Int) async -> DashboardProfile? {
        let cacheKey = "GET:\(BackendEndpoints.base)get_profilev1.php?user_id=\(userId)&viewer_id=\(userId)"
        if let cached = Self.cachedObject(key: cacheKey, maxAgeMs: FirebaseOnlineCache.TTL.profile) {
            return Self.applyProfile(cached)
        }
        do {
            let json = try await HTTPClient.shared.getObject(
                .profile,
                query: ["user_id": String(userId), "viewer_id": String(userId)]
            )
            if let data = try? JSONSerialization.data(withJSONObject: json) {
                FirebaseOnlineCache.putString(key: cacheKey, response: String(decoding: data, as: UTF8.self))
            }
            return Self.applyProfile(json)
        } catch {
            RemoteLogger.log(tag: "DASHBOARD_DEBUG", message: "Profile fetch network error: \(error.localizedDescription)")
            return nil
        }
    }

    /// `fetchPredictionFromServer` — `POST predict_rank.php` with the local
    /// accuracy figures, then echoed back by `savePredictedRankToServer`. Falls
    /// back to `loadPredictedRankFromPrefs` whenever the script declines.
    private func fetchPrediction(userId: Int) async -> DashboardRankPrediction? {
        let stats = localStats
        do {
            let json = try await HTTPClient.shared.postObject(
                form: [
                    "accuracy": String(stats.accuracy),
                    "streak": String(stats.streak),
                    "attempted": String(stats.attempted),
                    "correct": String(stats.correct),
                    "user_id": String(userId),
                ],
                to: .predictRank
            )
            guard (json["success"] as? Bool) == true else { return Self.storedPrediction() }
            let prediction = DashboardRankPrediction(
                json: json,
                timestamp: Int(Date().timeIntervalSince1970 * 1000)
            )
            Self.persist(prediction)
            Self.savePrediction(prediction, userId: userId)
            return prediction
        } catch {
            return Self.storedPrediction()
        }
    }

    /// `TopicSelectorList`'s `LaunchedEffect(subject)` — `GET api/getTopics.php`,
    /// deduplicated by name and sorted, cached for 24 hours.
    private func fetchTopics(subject: String) async -> LoadState<[DashboardTopic]> {
        let cacheKey = "GET:\(BackendEndpoints.base)api/getTopics.php?subject=\(Self.escape(subject))"
        if let cached = Self.cachedObject(key: cacheKey, maxAgeMs: FirebaseOnlineCache.TTL.topics) {
            let topics = Self.topics(from: cached)
            if !topics.isEmpty { return .loaded(topics) }
        }
        do {
            let json = try await HTTPClient.shared.getObject(.topicsApi, query: ["subject": subject])
            if let data = try? JSONSerialization.data(withJSONObject: json) {
                FirebaseOnlineCache.putString(key: cacheKey, response: String(decoding: data, as: UTF8.self))
            }
            return .loaded(Self.topics(from: json))
        } catch {
            RemoteLogger.log(tag: "TOPICS", message: "Error: \(error.localizedDescription)")
            return .failed(LoadState<[DashboardTopic]>.message(for: error))
        }
    }

    /// `loadTodayFirstQuestion` — one `getQuestions.php` row.
    private func fetchTodayQuestion(userId: Int) async -> DashboardQuestionPreview? {
        do {
            let json = try await HTTPClient.shared.getObject(
                .questionsApi,
                query: [
                    "subject": "NEET PG",
                    "topic": "Uncategorized",
                    "limit": "1",
                    "user_id": String(userId),
                ]
            )
            guard (json["success"] as? Bool) == true,
                  let data = json["data"] as? [String: Any] else { return nil }
            return DashboardQuestionPreview(json: data)
        } catch {
            return .fallback
        }
    }

    // MARK: - Mobile verification

    /// `checkAndPromptMobileVerification()` — the `onResume` gate.
    func checkMobileVerification(userId: Int) async {
        guard userId > 0 else { return }

        let storedPhone = UserDefaults.standard.string(forKey: Self.phoneKey) ?? ""
        let isVerified = UserDefaults.standard.bool(forKey: Self.verifiedKey)
        if isVerified, !storedPhone.isEmpty, storedPhone != Self.placeholderPhone { return }

        guard let url = URL(string: "\(BackendEndpoints.base)api/verify_mobile.php?user_id=\(userId)&action=check_status") else {
            self.verification = .phone
            return
        }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue(APIConfig.appSignature, forHTTPHeaderField: "X-App-Signature")

        do {
            let (data, _) = try await URLSession.shared.data(for: request)
            let json = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] ?? [:]
            guard (json["success"] as? Bool) == true else {
                self.verification = .phone
                return
            }
            let phone = (json["mobile_no"] as? String ?? "").trimmingCharacters(in: .whitespaces)
            let verified = (json["mobile_verified"] as? Bool) ?? false
            if !phone.isEmpty { Self.persistPhone(phone, verified: verified) }
            if !verified || phone.isEmpty || phone == Self.placeholderPhone {
                self.verification = .phone
            }
        } catch {
            self.verification = .phone
        }
    }

    /// `sendMobileVerificationOtp` — `POST action=send_otp`.
    func sendVerificationOTP(userId: Int, phone: String) async {
        isVerifying = true
        defer { isVerifying = false }

        let json = await Self.postVerificationJSON([
            "action": "send_otp",
            "user_id": userId,
            "mobile_no": phone,
        ])
        let message = json["message"] as? String ?? ""
        if message.isEmpty {
            verificationNotice = (json["success"] as? Bool) == true
                ? "OTP sent successfully!"
                : "Failed to send SMS"
        } else {
            verificationNotice = message
        }
        // The Kotlin dialog advanced on both branches, failure included.
        verification = .otp(phone: phone)
    }

    /// `showOtpConfirmationDialog`'s positive button — `POST action=verify_otp`.
    func verifyOTP(userId: Int, phone: String, otp: String) async {
        let trimmed = otp.trimmingCharacters(in: .whitespaces)
        guard !trimmed.isEmpty else {
            verificationNotice = "Please enter the OTP received"
            verification = .otp(phone: phone)
            return
        }

        isVerifying = true
        defer { isVerifying = false }

        let json = await Self.postVerificationJSON([
            "action": "verify_otp",
            "user_id": userId,
            "mobile_no": phone,
            "otp": trimmed,
        ])
        guard (json["success"] as? Bool) == true else {
            let message = json["message"] as? String ?? ""
            verificationNotice = message.isEmpty ? "Invalid OTP" : message
            verification = .otp(phone: phone)
            return
        }

        Self.persistPhone(phone, verified: true)
        RemoteLogger.log(
            tag: "PAYMENT_MONITOR",
            message: "[USER_PHONE] Mobile number +91 \(phone) successfully verified for MediGyaan!"
        )
        verificationNotice = "✅ Mobile number +91 \(phone) verified!"
        verification = .hidden
    }

    /// "SKIP FOR NOW" — the phone dialog is the only cancellable one, so the
    /// OTP step deliberately ignores this.
    func dismissVerification() {
        verification = .hidden
    }

    func dismissVerificationNotice() {
        verificationNotice = nil
    }

    /// `deleteAccount()` — clears the dashboard-owned preferences and reports
    /// success; the view signs the session out on `true`.
    func deleteAccount(userId: Int) async -> Bool {
        guard let url = URL(string: "\(BackendEndpoints.base)delete_account.php?user_id=\(userId)") else {
            errorMessage = "Could not reach the server."
            return false
        }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"

        guard let (data, _) = try? await URLSession.shared.data(for: request),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            errorMessage = "Network error"
            return false
        }
        guard (json["success"] as? Bool) == true else {
            errorMessage = "Failed to delete account"
            return false
        }
        Self.clearStoredKeys()
        return true
    }

    // MARK: - Persistence

    // `SharedPreferences("MY_APP")` keys, kept verbatim.
    private static let selectedSubjectKey = "selected_subject_preference"
    private static let nameKey = "name"
    private static let photoKey = "photo_url"
    private static let experienceKey = "user_exp"
    private static let phoneKey = "user_phone"
    private static let verifiedKey = "phone_verified"
    private static let predictedRankKey = "predicted_rank"
    private static let predictedTierKey = "predicted_tier"
    private static let predictedConfidenceKey = "predicted_confidence"
    private static let predictedTimestampKey = "predicted_timestamp"

    /// The `9999999999` sentinel the PHP backend stores for unverified users.
    private static let placeholderPhone = "9999999999"

    private static var verificationEndpoint: String { "\(BackendEndpoints.base)api/verify_mobile.php" }

    private static func statsCacheKey(userId: Int) -> String {
        "POST:\(BackendEndpoints.base)dash_api.php:user_id=\(userId)"
    }

    private static func escape(_ value: String) -> String {
        value.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? value
    }

    // MARK: - Helpers

    private static func readLocalStats() -> DashboardLocalStats {
        let manager = DailyStatsManager.shared
        let overall = manager.getOverallStats()
        let today = manager.getToday()
        return DashboardLocalStats(
            attempted: overall.attempted,
            correct: overall.correct,
            accuracy: manager.calculateAccuracy(attempted: overall.attempted, correct: overall.correct),
            streak: manager.getCurrentStreak(),
            battles: overall.attempted,
            wins: overall.correct,
            todayAttempted: today.attempted,
            todayCorrect: today.correct
        )
    }

    private static func cachedObject(key: String, maxAgeMs: Int) -> [String: Any]? {
        guard let body = FirebaseOnlineCache.cachedString(key: key, maxAgeMs: maxAgeMs),
              let data = body.data(using: .utf8) else { return nil }
        return try? JSONSerialization.jsonObject(with: data) as? [String: Any]
    }

    private static func cachedStats(userId: Int) -> DashboardStats? {
        guard let body = FirebaseOnlineCache.cachedString(
            key: statsCacheKey(userId),
            maxAgeMs: FirebaseOnlineCache.TTL.dashboard
        ), let data = body.data(using: .utf8) else { return nil }
        return try? JSONDecoder().decode(DashboardStats.self, from: data)
    }

    /// `applyProfileResponse` — persist the preferences, then hand back the model.
    private static func applyProfile(_ json: [String: Any]) -> DashboardProfile {
        let data = (json["data"] as? [String: Any]) ?? json
        let profile = DashboardProfile(json: data)
        let defaults = UserDefaults.standard
        if !profile.name.isEmpty { defaults.set(profile.name, forKey: nameKey) }
        if let photoURL = profile.photoURL { defaults.set(photoURL.absoluteString, forKey: photoKey) }
        if !profile.mobileNumber.isEmpty { defaults.set(profile.mobileNumber, forKey: phoneKey) }
        defaults.set(profile.isMobileVerified, forKey: verifiedKey)
        defaults.set(profile.experience, forKey: experienceKey)
        return profile
    }

    private static func persist(_ prediction: DashboardRankPrediction) {
        let defaults = UserDefaults.standard
        defaults.set(prediction.range, forKey: predictedRankKey)
        defaults.set(prediction.tier, forKey: predictedTierKey)
        defaults.set(prediction.confidence, forKey: predictedConfidenceKey)
        defaults.set(prediction.timestamp, forKey: predictedTimestampKey)
    }

    /// `loadPredictedRankFromPrefs()`.
    private static func storedPrediction() -> DashboardRankPrediction? {
        let defaults = UserDefaults.standard
        guard let range = defaults.string(forKey: predictedRankKey) else { return nil }
        return DashboardRankPrediction(
            range: range,
            tier: defaults.string(forKey: predictedTierKey) ?? "",
            confidence: defaults.integer(forKey: predictedConfidenceKey),
            timestamp: defaults.integer(forKey: predictedTimestampKey)
        )
    }

    /// `savePredictedRankToServer` — fire and forget; both listeners were empty.
    ///
    /// Kotlin sent `predicted_min_rank` and `predicted_max_rank` as separate
    /// values; the range is split back apart here so the server keeps receiving
    /// the bounds it expects.
    private static func savePrediction(_ prediction: DashboardRankPrediction, userId: Int) {
        guard let url = URL(string: "\(BackendEndpoints.base)api_save_predicted_rank.php") else { return }
        let bounds = prediction.range.components(separatedBy: " - ")
        let minRank = bounds.first ?? prediction.range
        let maxRank = bounds.count > 1 ? bounds[1] : prediction.range

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.setValue(APIConfig.appSignature, forHTTPHeaderField: "X-App-Signature")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        let fields = [
            "user_id": String(userId),
            "predicted_min_rank": minRank,
            "predicted_max_rank": maxRank,
            "tier": prediction.tier,
            "confidence": String(prediction.confidence),
            "timestamp": String(prediction.timestamp),
        ]
        let body = fields
            .map { entry in "\(entry.key)=\(Self.formEscape(entry.value))" }
            .joined(separator: "&")
        request.httpBody = body.data(using: .utf8)
        URLSession.shared.dataTask(with: request).resume()
    }

    private static func formEscape(_ value: String) -> String {
        var allowed = CharacterSet.urlQueryAllowed
        allowed.remove(charactersIn: "&=+?/")
        return value.addingPercentEncoding(withAllowedCharacters: allowed) ?? value
    }

    /// `TopicSelectorList.applyTopicsResponse` — reads `data` (objects carrying
    /// `name`/`count`, or bare strings), then `distinctBy { it.name }
    /// .sortedBy { it.name }`.
    private static func topics(from json: [String: Any]) -> [DashboardTopic] {
        guard (json["success"] as? Bool) == true else { return [] }
        var seen = Set<String>()
        var result: [DashboardTopic] = []

        if let objects = json["data"] as? [[String: Any]] {
            for item in objects {
                guard let name = item["name"] as? String, !name.isEmpty else { continue }
                guard seen.insert(name).inserted else { continue }
                result.append(DashboardTopic(name: name, count: item["count"] as? Int ?? 0))
            }
        } else if let names = json["data"] as? [String] {
            for name in names where !name.isEmpty {
                guard seen.insert(name).inserted else { continue }
                result.append(DashboardTopic(name: name, count: 0))
            }
        }
        return result.sorted { $0.name < $1.name }
    }

    private static func postVerificationJSON(_ body: [String: Any]) async -> [String: Any] {
        guard let url = URL(string: verificationEndpoint) else { return [:] }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(APIConfig.appSignature, forHTTPHeaderField: "X-App-Signature")
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        guard let (data, _) = try? await URLSession.shared.data(for: request) else { return [:] }
        return (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] ?? [:]
    }

    private static func persistPhone(_ phone: String, verified: Bool) {
        let defaults = UserDefaults.standard
        defaults.set(phone, forKey: phoneKey)
        defaults.set(verified, forKey: verifiedKey)
    }

    /// Android clears the entire `MY_APP` preference file on delete/logout.
    /// iOS shares one `UserDefaults` domain, so only the keys this screen owns
    /// are removed; the session is cleared separately by the caller.
    private static func clearStoredKeys() {
        let defaults = UserDefaults.standard
        for key in [
            nameKey, photoKey, experienceKey, phoneKey, verifiedKey,
            predictedRankKey, predictedTierKey, predictedConfidenceKey,
            predictedTimestampKey, selectedSubjectKey,
        ] {
            defaults.removeObject(forKey: key)
        }
    }
}