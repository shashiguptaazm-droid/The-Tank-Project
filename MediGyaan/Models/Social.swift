import Foundation

/// A news-feed post from `api/fetch_posts.php`.
struct Post: Decodable, Identifiable, Hashable {
    let id: Int
    let authorId: Int
    let authorName: String
    let authorAvatarURL: URL?
    let content: String
    let imageURL: URL?
    let likeCount: Int
    let commentCount: Int
    let shareCount: Int
    let isLiked: Bool
    let createdAt: String

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        id = container.flexInt("post_id", "id")
        authorId = container.flexInt("user_id", "author_id")
        authorName = container.flexString("name", "author", "username", "author_name")
        let avatar = container.flexString("avatar", "avatar_url", "profile_pic")
        authorAvatarURL = avatar.isEmpty ? nil : URL(string: avatar)
        content = container.flexString("caption", "content", "post", "text", "body", "description")
        let image = container.flexString("image", "image_url", "post_image", "media")
        let filePaths = container.flexStringArray("file_paths", "files", "images")
        let resolvedImage = !image.isEmpty ? image : (filePaths.first ?? "")
        imageURL = resolvedImage.isEmpty ? nil : URL(string: resolvedImage)
        likeCount = container.flexInt("likes", "like_count", "total_likes")
        commentCount = container.flexInt("comments", "comment_count", "total_comments")
        shareCount = container.flexInt("shares", "share_count")
        isLiked = container.flexBool("liked", "is_liked", "user_liked")
        createdAt = container.flexString("created_at", "date", "time", "timestamp")
    }

    init(
        id: Int,
        authorId: Int,
        authorName: String,
        authorAvatarURL: URL? = nil,
        content: String,
        imageURL: URL? = nil,
        likeCount: Int = 0,
        commentCount: Int = 0,
        shareCount: Int = 0,
        isLiked: Bool = false,
        createdAt: String = ""
    ) {
        self.id = id
        self.authorId = authorId
        self.authorName = authorName
        self.authorAvatarURL = authorAvatarURL
        self.content = content
        self.imageURL = imageURL
        self.likeCount = likeCount
        self.commentCount = commentCount
        self.shareCount = shareCount
        self.isLiked = isLiked
        self.createdAt = createdAt
    }
}

/// A question shared by the user, tracked from `shared_api.php`.
/// Ports `SharedQuestionModel` from Android's `SharedQuestionsActivity.kt`.
struct SharedQuestion: Decodable, Identifiable, Hashable {
    let id: Int
    let question: String
    let totalAttempts: Int
    let totalCorrect: Int
    let accuracy: Double

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        id = container.flexInt("question_id", "id")
        question = container.flexString("question", "question_text", "text")
        totalAttempts = container.flexInt("total_attempts", "attempts", "count")
        totalCorrect = container.flexInt("total_correct", "correct")
        accuracy = container.flexDouble("accuracy", "accuracy_rate")
    }

    init(
        id: Int,
        question: String,
        totalAttempts: Int = 0,
        totalCorrect: Int = 0,
        accuracy: Double = 0.0
    ) {
        self.id = id
        self.question = question
        self.totalAttempts = totalAttempts
        self.totalCorrect = totalCorrect
        self.accuracy = accuracy
    }
}

/// A peer attempt record on a shared question from `attempts_api.php`.
/// Ports `AttemptModel` from Android's `QuestionAttemptsActivity.kt`.
struct QuestionAttemptPeer: Decodable, Identifiable, Hashable {
    let id: String
    let temporaryUserId: String
    let userAnswer: String
    let isCorrect: Bool
    let name: String
    let createdAt: String

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        temporaryUserId = container.flexString("temporary_user_id", "user_id")
        userAnswer = container.flexString("user_answer", "answer")
        isCorrect = container.flexBool("is_correct")
        name = container.flexString("name", "user_name", "student")
        createdAt = container.flexString("created_at", "date", "time")
        id = "\(temporaryUserId)_\(createdAt)"
    }

    init(
        temporaryUserId: String,
        userAnswer: String,
        isCorrect: Bool,
        name: String,
        createdAt: String
    ) {
        self.temporaryUserId = temporaryUserId
        self.userAnswer = userAnswer
        self.isCorrect = isCorrect
        self.name = name
        self.createdAt = createdAt
        self.id = "\(temporaryUserId)_\(createdAt)"
    }
}

/// A comment on a post.
struct Comment: Decodable, Identifiable, Hashable {
    let id: Int
    let postId: Int
    let authorName: String
    let authorAvatarURL: URL?
    let text: String
    let createdAt: String

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        id = container.flexInt("comment_id", "id")
        postId = container.flexInt("post_id")
        authorName = container.flexString("name", "author", "username")
        let avatar = container.flexString("avatar", "avatar_url")
        authorAvatarURL = avatar.isEmpty ? nil : URL(string: avatar)
        text = container.flexString("comment", "text", "content")
        createdAt = container.flexString("created_at", "date", "time")
    }
}

/// An entry in the in-app messenger (`messenger_api.php`).
struct ChatMessage: Decodable, Identifiable, Hashable {
    let id: String
    let conversationId: String
    let senderId: Int
    let senderName: String
    let text: String
    let sentAt: Date
    let isMine: Bool

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        let rawId = container.flexString("message_id", "id")
        senderId = container.flexInt("sender_id", "user_id", "from")
        conversationId = container.flexString("conversation_id", "thread_id", "chat_id")
        id = rawId.isEmpty ? UUID().uuidString : rawId
        senderName = container.flexString("sender_name", "name", "username")
        text = container.flexString("message", "text", "content", "body")
        isMine = container.flexBool("is_mine", "mine", "self")
        // Timestamps arrive as unix seconds or a MySQL datetime string.
        let raw = container.flexString("sent_at", "created_at", "time", "timestamp")
        if let seconds = Double(raw), seconds > 1_000_000_000 {
            sentAt = Date(timeIntervalSince1970: seconds)
        } else {
            sentAt = DateFormatter.backend.date(from: raw) ?? Date()
        }
    }

    init(
        id: String = UUID().uuidString,
        conversationId: String,
        senderId: Int,
        senderName: String,
        text: String,
        sentAt: Date = Date(),
        isMine: Bool
    ) {
        self.id = id
        self.conversationId = conversationId
        self.senderId = senderId
        self.senderName = senderName
        self.text = text
        self.sentAt = sentAt
        self.isMine = isMine
    }
}

extension DateFormatter {
    /// Shared parser for the MySQL `yyyy-MM-dd HH:mm:ss` datetimes the backend
    /// returns (server runs in IST).
    static let backend: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(identifier: "Asia/Kolkata")
        formatter.dateFormat = "yyyy-MM-dd HH:mm:ss"
        return formatter
    }()
}
