import Foundation

/// Central configuration for the MediGyaan PHP backend.
///
/// These paths mirror the hard-coded endpoints used by the Android client in
/// `com.rankwarz.edulabsrtm` (`Retrofit` services plus `Volley` requests), so the
/// iOS app talks to exactly the same set of live production scripts.
///
/// Note that some scripts read `$_POST` (requiring
/// `application/x-www-form-urlencoded`) while others — notably `api/login.php` —
/// read a JSON body. See `HTTPClient` for the two request encodings.
enum APIConfig {

    /// HTTPS root of the production backend (`medigyaan.xyz`).
    static let baseURL = URL(string: "https://medigyaan.xyz/Neurons/")!

    /// A few legacy scripts are only served over plain HTTP. The
    /// `NSAppTransportSecurity` exception in Info.plist permits this.
    static let legacyBaseURL = URL(string: "http://medigyaan.xyz/Neurons/")!

    static let requestTimeout: TimeInterval = 120
    static let resourceTimeout: TimeInterval = 180

    /// The LiveKit SFU that carries audio and video calls.
    ///
    /// This replaces the Jitsi Meet SDK the Android app uses, which dialled the
    /// public `meet.jit.si` service. Calls now run on our own single-node SFU,
    /// deployed on the VPS that serves `medigyaan.com` — a *different* machine
    /// from the shared hosting behind `baseURL` (`medigyaan.xyz`).
    ///
    /// The token endpoint necessarily lives on the SFU's host, because the API
    /// secret that signs access tokens never leaves that box. Clients only ever
    /// see a short-lived, room-scoped token.
    enum LiveKit {
        /// WebSocket endpoint clients connect to.
        static let webSocketURL = "wss://medigyaan.com/rtc"

        /// Mints a room-scoped access token for the signed-in user.
        static let tokenURL = URL(string: "https://medigyaan.com/Neurons/livekit_token.php")!
    }

    /// Every backend script the Android app is known to call.
    enum Endpoint: String, CaseIterable {

        // MARK: Authentication & account
        case login = "api/login.php"
        case googleCallback = "google-callback.php"
        case sendOtp = "send_otp3.php"
        case verifyOtp = "verify_otp12.php"
        case forgotPasswordSendOtp = "forgot_password_send_otp.php"
        case forgotPasswordVerifyOtp = "forgot_password_verify_otp.php"
        case resetPassword = "reset_password_app.php"
        case profile = "get_profilev1.php"
        case updateProfile = "update_profile_api.php"
        case updateFcm = "api/update_fcmv2.php"

        // MARK: Dashboard & analytics
        case dashboard = "dash_api.php"
        case attempts = "attempts_api.php"
        case syncGameStats = "api/sync_game_stats.php"
        case syncUserCache = "api/sync_user_cache.php"
        case predictRank = "predict_rank.php"
        case leaderboard = "leaderboard1.php"
        case submitAnswer = "submitAnswerx1.php"

        // MARK: Topics, quizzes & tests
        case topics = "get_topics.php"
        case topicsLegacy = "getTopics.php"
        case topicSearch = "api/topicsearch.php"
        case search = "api/searchv2.php"
        case quiz = "quiz_apiv2.php"
        case quizQuestions = "get_quiz_questions.php"
        case questionsLegacy = "getQuestions.php"
        case questionsApi = "api/getQuestions.php"
        case testStructure = "api/get_test_structure.php"
        case singleQuestion = "api/get_single_question.php"
        case createQuiz = "createquiz.php"
        case addToQuiz = "addtoquiz.php"
        case userQuizzes = "getuserquizzes.php"
        case deleteQuiz = "delete_quiz_api.php"
        case quizShare = "quiz_share.php"
        case share = "share.php"
        case shared = "shared_api.php"

        // MARK: Live challenges & battles
        case joinLobby = "join_lobby.php"
        case liveBattle = "livebattle.php"
        case participants = "participants_api.php"
        case tauntAi = "taunt_ai.php"
        case syncChallenge = "sync_challenge_v16_authenticated.php"

        // MARK: Social
        case fetchPosts = "api/fetch_posts.php"
        case socialActions = "api/social_actions.php"
        case messenger = "messenger_api.php"
        case closeFriends = "get_close_friends.php"
        case followUnfollow = "follow_unfollow_apiv4.php"

        // MARK: Thesis suite
        case thesisSession = "thesis_session_backend.php"
        case themeLayout = "theme_layout_backend.php"
        case referenceCache = "reference_cache_backend.php"
        case posterSession = "poster_session_backend.php"

        // MARK: AI
        case askAi = "ask_ai2.php"

        // MARK: Predictor
        case predictorApp = "predictor_app.php"

        // MARK: Referrals
        case referral = "referral.php"
        case referralApi = "api/referral_api.php"

        /// Absolute URL for this endpoint on the primary HTTPS host.
        var url: URL { APIConfig.baseURL.appendingPathComponent(rawValue) }

        /// Absolute URL on the legacy HTTP host, for scripts that are HTTP-only.
        var legacyURL: URL { APIConfig.legacyBaseURL.appendingPathComponent(rawValue) }
    }
}
