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
    /// Requires HTTP POST with `user_id` form body.
    func dashboard(userId: Int) async throws -> DashboardStats {
        guard userId > 0 else { return .empty }
        return try await client.post(form: ["user_id": String(userId)], to: .dashboard, as: DashboardStats.self)
    }

    /// Loads recent attempt history (`attempts_api.php`).
    func attempts(userId: Int) async throws -> [AttemptSummary] {
        guard userId > 0 else { return [] }
        struct Wrapper: Decodable {
            let items: [AttemptSummary]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("attempts", "data", "history", "results")
            }
        }
        do {
            let wrapper = try await client.get(.attempts, query: ["user_id": String(userId)], as: Wrapper.self)
            return wrapper.items
        } catch {
            return []
        }
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

    /// Submits a single answer in the background (`submitAnswerx1.php`).
    func submitAnswer(questionId: Int, answer: String, userId: Int) async throws -> Acknowledgment {
        try await client.post(
            form: [
                "question_id": String(questionId),
                "answer": answer,
                "user_id": String(userId)
            ],
            to: .submitAnswer,
            as: Acknowledgment.self
        )
    }

    // MARK: - Topics

    /// Loads the topic catalogue (`api/getTopics.php` or `api/topicsearch.php`).
    func topics(subject: String? = nil) async throws -> [Topic] {
        struct Wrapper: Decodable {
            let items: [Topic]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("topics", "data", "results", "subjects")
            }
        }
        if let subject, !subject.isEmpty {
            let wrapper = try await client.get(.topicsApi, query: ["subject": subject], as: Wrapper.self)
            return wrapper.items
        }
        // If no subject is passed, load topics across curriculum via topic search
        let wrapper = try await client.get(.topicSearch, query: ["q": "a"], as: Wrapper.self)
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
    ///
    /// Requires HTTP POST form data with `user_id` and `topic_id`.
    func quizzes(topicId: Int, userId: Int) async throws -> [Quiz] {
        struct Wrapper: Decodable {
            let items: [Quiz]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("quizzes", "data", "results")
            }
        }
        let wrapper = try await client.post(
            form: ["topic_id": String(topicId), "user_id": String(userId)],
            to: .quiz,
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
        let wrapper = try await client.post(
            form: ["quiz_id": String(quizId)],
            to: .quizQuestions,
            as: Wrapper.self
        )
        return wrapper.items
    }

    /// Loads one question (`api/get_single_question.php`).
    func question(id: Int) async throws -> Question {
        try await client.get(.singleQuestion, query: ["question_id": String(id)], as: Question.self)
    }

    /// Searches questions by topic or query (`api/getQuestions.php`).
    func searchQuestions(query text: String) async throws -> [Question] {
        struct Wrapper: Decodable {
            let items: [Question]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("questions", "data", "results")
            }
        }
        let wrapper = try await client.get(
            .questionsApi,
            query: ["query": text, "q": text, "topic": text],
            as: Wrapper.self
        )
        return wrapper.items
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
        do {
            let wrapper = try await client.get(
                .syncChallenge,
                query: ["user_id": String(userId), "action": "list"],
                as: Wrapper.self
            )
            return wrapper.items
        } catch {
            return []
        }
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
