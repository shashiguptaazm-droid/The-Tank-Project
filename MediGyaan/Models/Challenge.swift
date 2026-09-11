import Foundation

/// A head-to-head challenge (`join_lobby.php`, `livebattle.php`).
struct Challenge: Decodable, Identifiable, Hashable {
    let id: Int
    let topic: String
    let subject: String
    let hostId: Int
    let hostName: String
    let opponentId: Int
    let opponentName: String
    let status: String
    let questionCount: Int
    let createdAt: String

    var isPending: Bool {
        status.lowercased().contains("pending") || status.lowercased().contains("waiting")
    }

    var isCompleted: Bool {
        status.lowercased().contains("complete") || status.lowercased().contains("finished")
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        id = container.flexInt("challenge_id", "id", "lobby_id")
        topic = container.flexString("topic", "topic_name")
        subject = container.flexString("subject", "subject_name")
        hostId = container.flexInt("host_id", "challenger_id", "user_id", "creator_id")
        hostName = container.flexString("host_name", "challenger", "creator", "challenger_name")
        opponentId = container.flexInt("opponent_id", "opponent_user_id", "challenged_id")
        opponentName = container.flexString("opponent_name", "opponent", "challenged_name")
        status = container.flexString("status", "state")
        questionCount = container.flexInt("question_count", "questions", "total_questions")
        createdAt = container.flexString("created_at", "date", "time")
    }
}

/// A participant in a lobby (`participants_api.php`).
struct Participant: Decodable, Identifiable, Hashable {
    let id: Int
    let name: String
    let avatarURL: URL?
    let score: Int
    let isReady: Bool
    let rank: Int

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        id = container.flexInt("user_id", "id")
        name = container.flexString("name", "username")
        let avatar = container.flexString("avatar", "avatar_url")
        avatarURL = avatar.isEmpty ? nil : URL(string: avatar)
        score = container.flexInt("score", "points")
        isReady = container.flexBool("ready", "is_ready")
        rank = container.flexInt("rank", "position")
    }
}

/// A leaderboard row (`LeaderboardActivity`).
struct LeaderboardEntry: Decodable, Identifiable, Hashable {
    let id: Int
    let name: String
    let avatarURL: URL?
    let score: Int
    let accuracy: Double
    let rank: Int

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        id = container.flexInt("user_id", "id")
        name = container.flexString("name", "username")
        let avatar = container.flexString("avatar", "avatar_url", "profile_pic")
        avatarURL = avatar.isEmpty ? nil : URL(string: avatar)
        score = container.flexInt("score", "points", "total_score")
        accuracy = container.flexDouble("accuracy", "percent", "percentage")
        rank = container.flexInt("rank", "position", "rank_no")
    }

    init(id: Int, name: String, avatarURL: URL? = nil, score: Int, accuracy: Double = 0, rank: Int) {
        self.id = id
        self.name = name
        self.avatarURL = avatarURL
        self.score = score
        self.accuracy = accuracy
        self.rank = rank
    }
}

/// Prediction result from `predict_rank.php` / `predictor_app.php`.
struct RankPrediction: Decodable, Hashable {
    let predictedRank: Int
    let predictedScore: Double
    let percentile: Double
    let collegeName: String
    let message: String

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        predictedRank = container.flexInt("predicted_rank", "rank", "prediction", "expected_rank")
        predictedScore = container.flexDouble("predicted_score", "score", "expected_score")
        percentile = container.flexDouble("percentile", "percentage")
        collegeName = container.flexString("college", "college_name", "institute")
        let error = container.flexString("error")
        message = error.isEmpty ? container.flexString("message") : error
    }
}

/// A quiz session used while a live battle or single-player run is in progress.
struct QuizSession: Identifiable, Hashable {
    let id: String
    let quizId: Int
    let title: String
    let questions: [Question]
    let durationSeconds: Int
    let topic: String

    var questionCount: Int { questions.count }

    init(
        id: String = UUID().uuidString,
        quizId: Int,
        title: String,
        questions: [Question],
        durationSeconds: Int = 0,
        topic: String = ""
    ) {
        self.id = id
        self.quizId = quizId
        self.title = title
        self.questions = questions
        self.durationSeconds = durationSeconds
        self.topic = topic
    }
}
