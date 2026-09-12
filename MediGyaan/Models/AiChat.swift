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
        isStreaming: Bool = false
    ) {
        self.id = id
        self.role = role
        self.text = text
        self.timestamp = timestamp
        self.attachmentName = attachmentName
        self.relatedQuestions = relatedQuestions
        self.isStreaming = isStreaming
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
