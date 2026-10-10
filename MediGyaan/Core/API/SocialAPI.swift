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
        let query: [String: String] = userId > 0
            ? ["user_id": String(userId), "page": String(page)]
            : ["page": String(page)]
        do {
            return try await client.get(.fetchPosts, query: query, as: [Post].self)
        } catch {
            let wrapper = try await client.get(.fetchPosts, query: query, as: Wrapper.self)
            return wrapper.items
        }
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
        guard userId > 0 else { return [] }
        struct Wrapper: Decodable {
            let items: [ChatMessage]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("messages", "data", "chat", "results")
            }
        }
        let receiverId = Int(conversationId) ?? 1
        do {
            return try await client.get(
                .messenger,
                query: ["fetch_messages": String(receiverId), "user_id": String(userId)],
                as: [ChatMessage].self
            )
        } catch {
            do {
                let wrapper = try await client.get(
                    .messenger,
                    query: ["fetch_messages": String(receiverId), "user_id": String(userId)],
                    as: Wrapper.self
                )
                return wrapper.items
            } catch {
                return []
            }
        }
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

    /// Sends a direct message with optional attachment strictly conforming to Android's `sendMessageToPhpBackend`.
    func sendDirectMessage(
        userId: Int,
        receiverId: Int,
        message: String,
        attachment: String = ""
    ) async throws -> Bool {
        let form = [
            "user_id": String(userId),
            "receiver_id": String(receiverId),
            "message": message,
            "attachment": attachment
        ]
        let response = try await client.postObject(form: form, to: .messenger)
        return (response["success"] as? Bool) ?? true
    }

    /// Deletes a message from thread (`messenger_api.php?delete_message=1`).
    func deleteMessage(messageId: String, userId: Int) async throws -> Bool {
        let response = try await client.getObject(
            .messenger,
            query: ["delete_message": "1", "message_id": messageId, "user_id": String(userId)]
        )
        return (response["success"] as? Bool) ?? true
    }

    /// Fetches list of user IDs followed / connected (`messenger_api.php?get_connections&user_id=X`).
    func connections(userId: Int) async throws -> [Int] {
        struct ConnectionItem: Decodable {
            let userId: Int
            enum CodingKeys: String, CodingKey {
                case userId = "user_id"
            }
        }
        struct Wrapper: Decodable {
            let connections: [ConnectionItem]?
            let data: [ConnectionItem]?
        }
        let url = APIConfig.baseURL.appendingPathComponent("messenger_api.php").appending(queryItems: [
            URLQueryItem(name: "get_connections", value: nil),
            URLQueryItem(name: "user_id", value: String(userId))
        ])
        var request = URLRequest(url: url)
        request.setValue("EduLabs_Android_App", forHTTPHeaderField: "User-Agent")
        request.setValue("EduLabsRTM_Secure_v1_2026", forHTTPHeaderField: "X-App-Signature")
        let (data, _) = try await URLSession.shared.data(for: request)
        if let array = try? JSONDecoder().decode([ConnectionItem].self, from: data) {
            return array.map(\.userId).filter { $0 != userId && $0 > 0 }
        }
        if let wrapper = try? JSONDecoder().decode(Wrapper.self, from: data) {
            let list = (wrapper.connections ?? wrapper.data ?? [])
            return list.map(\.userId).filter { $0 != userId && $0 > 0 }
        }
        return []
    }

    /// Loads profile for a user (`get_profilev1.php?user_id=X&viewer_id=Y`).
    func userProfile(userId: Int, viewerId: Int) async throws -> ChatUserItem {
        let url = APIConfig.baseURL.appendingPathComponent("get_profilev1.php").appending(queryItems: [
            URLQueryItem(name: "user_id", value: String(userId)),
            URLQueryItem(name: "viewer_id", value: String(viewerId))
        ])
        var request = URLRequest(url: url)
        request.setValue("EduLabs_Android_App", forHTTPHeaderField: "User-Agent")
        request.setValue("EduLabsRTM_Secure_v1_2026", forHTTPHeaderField: "X-App-Signature")
        let (data, _) = try await URLSession.shared.data(for: request)
        let json = (try? JSONSerialization.jsonObject(with: data) as? [String: Any]) ?? [:]
        let obj = (json["data"] as? [String: Any]) ?? json
        let name = (obj["name"] as? String) ?? "User \(userId)"
        var photo = (obj["photo"] as? String) ?? (obj["profile_pic"] as? String) ?? ""
        if !photo.isEmpty && !photo.hasPrefix("http") {
            photo = "https://medigyaan.com/Neurons/" + photo.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        }
        return ChatUserItem(id: userId, name: name, image: photo, isOnline: false)
    }

    /// Blocks a user (`block_user.php`).
    func blockUser(userId: Int, blockedUserId: Int) async throws -> Bool {
        let url = APIConfig.baseURL.appendingPathComponent("block_user.php")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.setValue("EduLabsRTM_Secure_v1_2026", forHTTPHeaderField: "X-App-Signature")
        let bodyString = "user_id=\(userId)&blocked_user_id=\(blockedUserId)"
        request.httpBody = bodyString.data(using: .utf8)
        let (data, _) = try await URLSession.shared.data(for: request)
        if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            return (json["success"] as? Bool) ?? false
        }
        return false
    }

    /// Loads medical reels (`api/getReels.php`).
    func reels() async throws -> [Reel] {
        try await client.get(.getReels, as: [Reel].self)
    }

    /// Uploads an attachment to the VPS high-speed upload engine (`api/upload`).
    func uploadAttachment(data: Data, filename: String, mimeType: String) async throws -> URL {
        var request = URLRequest(url: APIConfig.VPS.uploadURL.appending(queryItems: [
            URLQueryItem(name: "token", value: APIConfig.VPS.uploadToken),
            URLQueryItem(name: "filename", value: filename)
        ]))
        request.httpMethod = "POST"
        request.setValue(mimeType, forHTTPHeaderField: "Content-Type")
        request.setValue(String(data.count), forHTTPHeaderField: "Content-Length")
        request.setValue(filename, forHTTPHeaderField: "X-Filename")
        request.setValue(APIConfig.VPS.uploadToken, forHTTPHeaderField: "X-Token")
        request.httpBody = data

        let (responseData, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, (200...299).contains(httpResponse.statusCode) else {
            throw APIError.server(message: "Upload failed with server error", code: nil)
        }

        struct UploadResponse: Decodable {
            let success: Bool?
            let ok: Bool?
            let fileUrl: String?
            let url: String?
        }
        let decoded = try JSONDecoder().decode(UploadResponse.self, from: responseData)
        guard let rawUrl = decoded.fileUrl ?? decoded.url, let url = URL(string: rawUrl) else {
            throw APIError.server(message: "Server did not return a valid file URL", code: nil)
        }
        return url
    }

    /// Loads questions shared by the user (`shared_api.php?user_id=X`).
    func sharedQuestions(userId: Int) async throws -> [SharedQuestion] {
        struct Wrapper: Decodable {
            let items: [SharedQuestion]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("questions", "data", "results")
            }
        }
        let wrapper = try await client.get(
            .shared,
            query: ["user_id": String(userId)],
            as: Wrapper.self
        )
        return wrapper.items
    }

    /// Loads peer attempts on a shared question (`attempts_api.php?question_id=X&user_id=Y`).
    func questionAttempts(questionId: Int, userId: Int) async throws -> [QuestionAttemptPeer] {
        struct Wrapper: Decodable {
            let items: [QuestionAttemptPeer]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("attempts", "data", "results")
            }
        }
        let wrapper = try await client.get(
            .attempts,
            query: ["question_id": String(questionId), "user_id": String(userId)],
            as: Wrapper.self
        )
        return wrapper.items
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
            let safe: [College]
            let target: [College]
            let dream: [College]
            let direct: [College]

            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                safe = container.flexArray("safe_colleges")
                target = container.flexArray("target_colleges")
                dream = container.flexArray("dream_colleges")
                direct = container.flexArray("colleges", "data", "results")
            }
        }
        var query: [String: String] = ["rank": String(rank)]
        if let state, !state.isEmpty { query["state"] = state }
        let wrapper = try await client.get(.predictorApp, query: query, as: Wrapper.self)
        let combined = wrapper.target + wrapper.safe + wrapper.dream + wrapper.direct
        return combined.isEmpty ? [] : Array(combined.prefix(100))
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
            to: .referralApi,
            as: Acknowledgment.self
        )
    }
}
