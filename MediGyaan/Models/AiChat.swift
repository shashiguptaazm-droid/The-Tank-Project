import Foundation

/// A message in the medical AI chat thread.
/// Ports the multi-turn chat and related-question model from Android's `AiChatActivity.kt`.
struct AiChatMessage: Identifiable, Equatable {
    let id: UUID
    let role: MessageRole
    var text: String
    let timestamp: Date
    var attachmentName: String?
    var relatedQuestions: [Question]
    var isStreaming: Bool
    var responseTimeMs: Int?
    var feedback: Int // -1: dislike, 0: neutral, 1: like
    var counselCard: CounselCardData?
    var thesisCard: ThesisCardData?
    var chapterCard: ChapterCardData?

    enum MessageRole: String, Codable {
        case user
        case assistant
        case system
    }

    init(
        id: UUID = UUID(),
        role: MessageRole,
        text: String,
        timestamp: Date = Date(),
        attachmentName: String? = nil,
        relatedQuestions: [Question] = [],
        isStreaming: Bool = false,
        responseTimeMs: Int? = nil,
        feedback: Int = 0,
        counselCard: CounselCardData? = nil,
        thesisCard: ThesisCardData? = nil,
        chapterCard: ChapterCardData? = nil
    ) {
        self.id = id
        self.role = role
        self.text = text
        self.timestamp = timestamp
        self.attachmentName = attachmentName
        self.relatedQuestions = relatedQuestions
        self.isStreaming = isStreaming
        self.responseTimeMs = responseTimeMs
        self.feedback = feedback
        self.counselCard = counselCard
        self.thesisCard = thesisCard
        self.chapterCard = chapterCard
    }

    var isUser: Bool { role == .user }
}

/// Medical clinical prompt suggestions for quick one-tap inquiries.
struct AiPromptSuggestion: Identifiable, Hashable {
    let id = UUID()
    let icon: String
    let title: String
    let prompt: String
}

// MARK: - NEET PG AI Counselor Card Data

struct CounselCollege: Identifiable, Equatable, Hashable {
    let id = UUID()
    let institute: String
    let course: String
    let closingRank: String
    let category: String
    let quota: String
    let state: String
    let feePerYear: String
    let stipendYear1: String
    let bondYears: String
    let chance: String // "Dream", "Target", "Safe"
}

struct CounselCardData: Equatable {
    var query: String
    var summary: String
    var results: [CounselCollege]
    var error: String = ""
    var isExpanded: Bool = true
}

// MARK: - Thesis Topic Card Data

struct ThesisTopicResult: Identifiable, Equatable, Hashable {
    let id: Int
    let subject: String
    let snippet: String
    let displayTitle: String
    let studyType: String
    let difficulty: String
}

struct ThesisCardData: Equatable {
    var query: String
    var results: [ThesisTopicResult]
    var isExpanded: Bool = true
}

// MARK: - Chapter Generator Card Data

struct ChapterCardData: Equatable {
    var chapterName: String
    var sections: [String]
    var isExpanded: Bool = true
}

