import Foundation

/// Dashboard, topic browsing, quiz delivery, and stats synchronisation.
struct StudyAPI {

    private let client: HTTPClient

    init(client: HTTPClient = .shared) {
        self.client = client
    }

    // MARK: - Dashboard & analytics

    /// Loads the dashboard summary (`dash_api.php`).
    ///
    /// Live contract: `{"success":false,"message":"Invalid User ID"}` for a bad
    /// id, otherwise the statistics block.
    func dashboard(userId: Int) async throws -> DashboardStats {
        try await client.get(.dashboard, query: ["user_id": String(userId)], as: DashboardStats.self)
    }

    /// Loads recent attempt history (`attempts_api.php`).
    func attempts(userId: Int) async throws -> [AttemptSummary] {
        struct Wrapper: Decodable {
            let items: [AttemptSummary]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("attempts", "data", "history", "results")
            }
        }
        let wrapper = try await client.get(.attempts, query: ["user_id": String(userId)], as: Wrapper.self)
        return wrapper.items
    }

    /// Loads leaderboard rankings.
    ///
    /// `LeaderboardActivity` calls `leaderboard1.php?user_id=$userId`; the
    /// optional scope narrows the result server-side.
    func leaderboard(userId: Int, scope: String) async throws -> [LeaderboardEntry] {
        struct Wrapper: Decodable {
            let items: [LeaderboardEntry]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("leaderboard", "data", "rankings", "results")
            }
        }
        let wrapper = try await client.get(
            .leaderboard,
            query: ["user_id": String(userId), "scope": scope],
            as: Wrapper.self
        )
        return wrapper.items
    }

    /// Pushes local statistics to the server (`api/sync_user_cache.php`, which
    /// reads `$_POST`, so this must be form-encoded).
    func syncUserCache(_ payload: UserCachePayload) async throws -> Acknowledgment {
        try await client.post(form: payload.formFields, to: .syncUserCache, as: Acknowledgment.self)
    }

    /// Pushes a finished attempt to `api/sync_game_stats.php`.
    func syncAttempt(_ attempt: QuizAttempt) async throws -> Acknowledgment {
        try await client.post(form: attempt.syncFormFields, to: .syncGameStats, as: Acknowledgment.self)
    }

    // MARK: - Topics

    /// Loads the topic catalogue (`get_topics.php`).
    func topics(subject: String? = nil) async throws -> [Topic] {
        struct Wrapper: Decodable {
            let items: [Topic]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("topics", "data", "results", "subjects")
            }
        }
        var query: [String: String] = [:]
        if let subject, !subject.isEmpty { query["subject"] = subject }
        let wrapper = try await client.get(.topics, query: query, as: Wrapper.self)
        return wrapper.items
    }

    /// Searches topics (`api/topicsearch.php`).
    func searchTopics(query text: String) async throws -> [Topic] {
        struct Wrapper: Decodable {
            let items: [Topic]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("topics", "data", "results")
            }
        }
        let wrapper = try await client.get(.topicSearch, query: ["q": text, "query": text], as: Wrapper.self)
        return wrapper.items
    }

    /// Global search across topics and questions (`api/searchv2.php`).
    func globalSearch(query text: String, userId: Int) async throws -> [Topic] {
        struct Wrapper: Decodable {
            let items: [Topic]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("topics", "results", "data")
            }
        }
        let wrapper = try await client.get(
            .search,
            query: ["q": text, "query": text, "user_id": String(userId)],
            as: Wrapper.self
        )
        return wrapper.items
    }

    // MARK: - Quizzes

    /// Lists quizzes for a topic (`quiz_apiv2.php`).
    func quizzes(topicId: Int, userId: Int) async throws -> [Quiz] {
        struct Wrapper: Decodable {
            let items: [Quiz]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("quizzes", "data", "results")
            }
        }
        let wrapper = try await client.get(
            .quiz,
            query: ["topic_id": String(topicId), "user_id": String(userId)],
            as: Wrapper.self
        )
        return wrapper.items
    }

    /// Loads the questions for a quiz (`get_quiz_questions.php`).
    func questions(quizId: Int) async throws -> [Question] {
        struct Wrapper: Decodable {
            let items: [Question]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("questions", "data", "results")
            }
        }
        let wrapper = try await client.get(
            .quizQuestions,
            query: ["quiz_id": String(quizId)],
            as: Wrapper.self
        )
        return wrapper.items
    }

    /// Loads one question (`api/get_single_question.php`).
    func question(id: Int) async throws -> Question {
        try await client.get(.singleQuestion, query: ["question_id": String(id)], as: Question.self)
    }

    /// Shares a quiz, returning the public link (`quiz_share.php`).
    func shareQuiz(quizId: Int, userId: Int) async throws -> Acknowledgment {
        try await client.post(
            form: ["quiz_id": String(quizId), "user_id": String(userId)],
            to: .quizShare,
            as: Acknowledgment.self
        )
    }

    /// Deletes a quiz owned by the user (`delete_quiz_api.php`).
    func deleteQuiz(quizId: Int, userId: Int) async throws -> Acknowledgment {
        try await client.post(
            form: ["quiz_id": String(quizId), "user_id": String(userId)],
            to: .deleteQuiz,
            as: Acknowledgment.self
        )
    }

    /// Loads quizzes shared with the user (`shared_api.php`).
    func sharedQuizzes(userId: Int) async throws -> [Quiz] {
        struct Wrapper: Decodable {
            let items: [Quiz]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("quizzes", "data", "shared")
            }
        }
        let wrapper = try await client.get(.shared, query: ["user_id": String(userId)], as: Wrapper.self)
        return wrapper.items
    }

    // MARK: - Challenges

    /// Joins a challenge lobby (`join_lobby.php`).
    func joinLobby(userId: Int, topicId: Int, code: String) async throws -> Acknowledgment {
        try await client.post(
            form: [
                "user_id": String(userId),
                "topic_id": String(topicId),
                "code": code,
                "lobby_code": code,
            ],
            to: .joinLobby,
            as: Acknowledgment.self
        )
    }

    /// Loads the user's challenges (`sync_challenge_v16_authenticated.php`).
    func challenges(userId: Int) async throws -> [Challenge] {
        struct Wrapper: Decodable {
            let items: [Challenge]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("challenges", "data", "results")
            }
        }
        let wrapper = try await client.get(
            .syncChallenge,
            query: ["user_id": String(userId), "action": "list"],
            as: Wrapper.self
        )
        return wrapper.items
    }

    /// Polls the live battle state (`livebattle.php`).
    func liveBattle(lobbyId: String, userId: Int) async throws -> [Participant] {
        struct Wrapper: Decodable {
            let items: [Participant]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("participants", "players", "data")
            }
        }
        let wrapper = try await client.get(
            .liveBattle,
            query: ["lobby_id": lobbyId, "user_id": String(userId)],
            as: Wrapper.self
        )
        return wrapper.items
    }

    /// Loads lobby participants (`participants_api.php`).
    func participants(lobbyId: String) async throws -> [Participant] {
        struct Wrapper: Decodable {
            let items: [Participant]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("participants", "players", "data")
            }
        }
        let wrapper = try await client.get(.participants, query: ["lobby_id": lobbyId], as: Wrapper.self)
        return wrapper.items
    }
}
