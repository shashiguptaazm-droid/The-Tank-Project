import Foundation

/// News feed, reactions, and the in-app messenger.
struct SocialAPI {

    private let client: HTTPClient

    init(client: HTTPClient = .shared) {
        self.client = client
    }

    /// Loads the feed (`api/fetch_posts.php`).
    ///
    /// This script rejects unauthenticated calls with
    /// `{"success":false,"error":"Unauthorized Access"}`, so a `user_id` is
    /// always supplied.
    func posts(userId: Int, page: Int = 1) async throws -> [Post] {
        struct Wrapper: Decodable {
            let items: [Post]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("posts", "data", "feed", "results")
            }
        }
        let wrapper = try await client.get(
            .fetchPosts,
            query: ["user_id": String(userId), "page": String(page)],
            as: Wrapper.self
        )
        return wrapper.items
    }

    /// Loads comments for a post.
    func comments(postId: Int) async throws -> [Comment] {
        struct Wrapper: Decodable {
            let items: [Comment]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("comments", "data", "results")
            }
        }
        let wrapper = try await client.get(
            .fetchPosts,
            query: ["post_id": String(postId), "action": "comments"],
            as: Wrapper.self
        )
        return wrapper.items
    }

    /// Likes or unlikes a post (`api/social_actions.php`).
    func setLiked(postId: Int, userId: Int, liked: Bool) async throws -> Acknowledgment {
        try await client.post(
            form: [
                "action": liked ? "like" : "unlike",
                "post_id": String(postId),
                "user_id": String(userId),
            ],
            to: .socialActions,
            as: Acknowledgment.self
        )
    }

    /// Adds a comment (`api/social_actions.php`).
    func addComment(postId: Int, userId: Int, text: String) async throws -> Acknowledgment {
        try await client.post(
            form: [
                "action": "comment",
                "post_id": String(postId),
                "user_id": String(userId),
                "comment": text,
            ],
            to: .socialActions,
            as: Acknowledgment.self
        )
    }

    /// Creates a new post.
    func createPost(userId: Int, content: String, imageBase64: String? = nil) async throws -> Acknowledgment {
        var fields: [String: String] = [
            "action": "create",
            "user_id": String(userId),
            "content": content,
        ]
        if let imageBase64 { fields["image"] = imageBase64 }
        return try await client.post(form: fields, to: .socialActions, as: Acknowledgment.self)
    }

    /// Loads a conversation thread (`messenger_api.php`).
    func messages(conversationId: String, userId: Int) async throws -> [ChatMessage] {
        struct Wrapper: Decodable {
            let items: [ChatMessage]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("messages", "data", "chat", "results")
            }
        }
        let wrapper = try await client.get(
            .messenger,
            query: ["conversation_id": conversationId, "user_id": String(userId)],
            as: Wrapper.self
        )
        return wrapper.items
    }

    /// Sends a message (`messenger_api.php`).
    func sendMessage(conversationId: String, userId: Int, text: String) async throws -> Acknowledgment {
        try await client.post(
            form: [
                "action": "send",
                "conversation_id": conversationId,
                "user_id": String(userId),
                "message": text,
            ],
            to: .messenger,
            as: Acknowledgment.self
        )
    }
}

/// Rank prediction and college lookup.
struct PredictorAPI {

    private let client: HTTPClient

    init(client: HTTPClient = .shared) {
        self.client = client
    }

    /// Predicts a rank from a score (`predict_rank.php`).
    ///
    /// Live contract for an unknown user: `{"success":false,"message":"No attempts found"}`.
    func predictRank(userId: Int, score: Double) async throws -> RankPrediction {
        try await client.get(
            .predictRank,
            query: ["user_id": String(userId), "score": String(score)],
            as: RankPrediction.self
        )
    }

    /// Looks up colleges for a predicted rank (`predictor_app.php`).
    func colleges(rank: Int, state: String? = nil) async throws -> [College] {
        struct Wrapper: Decodable {
            let items: [College]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("colleges", "data", "results")
            }
        }
        var query: [String: String] = ["rank": String(rank)]
        if let state, !state.isEmpty { query["state"] = state }
        let wrapper = try await client.get(.predictorApp, query: query, as: Wrapper.self)
        return wrapper.items
    }
}

/// Referral programme.
struct ReferralAPI {

    private let client: HTTPClient

    init(client: HTTPClient = .shared) {
        self.client = client
    }

    /// Loads the referral summary (`api/referral_api.php`, `referral.php`).
    func summary(userId: Int) async throws -> ReferralInfo {
        try await client.get(.referralApi, query: ["user_id": String(userId)], as: ReferralInfo.self)
    }

    /// Applies a referral code at signup.
    func apply(code: String, userId: Int) async throws -> Acknowledgment {
        try await client.post(
            form: ["action": "apply", "referral_code": code, "user_id": String(userId)],
            to: .referral,
            as: Acknowledgment.self
        )
    }
}
