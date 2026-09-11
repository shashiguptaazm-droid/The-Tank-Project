import Foundation

/// Thesis workspace operations backed by `thesis_session_backend.php`,
/// `reference_cache_backend.php`, and `theme_layout_backend.php`.
struct ThesisAPI {

    private let client: HTTPClient

    init(client: HTTPClient = .shared) {
        self.client = client
    }

    /// Loads (or creates) the user's thesis workspace.
    func session(userId: Int, sessionId: String? = nil) async throws -> ThesisSession {
        var query: [String: String] = ["user_id": String(userId), "action": "get"]
        if let sessionId { query["session_id"] = sessionId }
        return try await client.get(.thesisSession, query: query, as: ThesisSession.self)
    }

    /// Persists workspace metadata.
    func updateSession(
        userId: Int,
        sessionId: String,
        title: String,
        topic: String,
        speciality: String,
        studyType: String
    ) async throws -> Acknowledgment {
        try await client.post(
            form: [
                "action": "update",
                "user_id": String(userId),
                "session_id": sessionId,
                "title": title,
                "topic": topic,
                "speciality": speciality,
                "study_type": studyType,
            ],
            to: .thesisSession,
            as: Acknowledgment.self
        )
    }

    /// Requests AI generation of a single chapter.
    ///
    /// The Android `ThesisBackgroundService` polled this endpoint while a
    /// chapter was generating, so the response is a status envelope and the
    /// chapter is fetched again once it completes.
    func generateChapter(
        userId: Int,
        sessionId: String,
        chapterIndex: Int,
        chapterTitle: String,
        instructions: String
    ) async throws -> Acknowledgment {
        try await client.post(
            form: [
                "action": "generate_chapter",
                "user_id": String(userId),
                "session_id": sessionId,
                "chapter_no": String(chapterIndex),
                "chapter_title": chapterTitle,
                "prompt": instructions,
            ],
            to: .thesisSession,
            as: Acknowledgment.self
        )
    }

    /// Saves edited chapter text.
    func saveChapter(
        userId: Int,
        sessionId: String,
        chapterIndex: Int,
        content: String
    ) async throws -> Acknowledgment {
        try await client.post(
            form: [
                "action": "save_chapter",
                "user_id": String(userId),
                "session_id": sessionId,
                "chapter_no": String(chapterIndex),
                "content": content,
            ],
            to: .thesisSession,
            as: Acknowledgment.self
        )
    }

    /// Lists cached references.
    func references(sessionId: String, query text: String? = nil) async throws -> [ThesisReference] {
        struct Wrapper: Decodable {
            let items: [ThesisReference]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("references", "data", "results", "articles")
            }
        }
        var params: [String: String] = ["session_id": sessionId, "action": "list"]
        if let text, !text.isEmpty { params["q"] = text }
        let wrapper = try await client.get(
            .referenceCache,
            query: params,
            as: Wrapper.self
        )
        return wrapper.items
    }

    /// Caches a new reference.
    func addReference(sessionId: String, reference: ThesisReference) async throws -> Acknowledgment {
        try await client.post(
            form: [
                "action": "add",
                "session_id": sessionId,
                "title": reference.title,
                "authors": reference.authors,
                "journal": reference.journal,
                "year": reference.year,
                "doi": reference.doi,
                "pmid": reference.pubmedId,
                "abstract": reference.abstract,
            ],
            to: .referenceCache,
            as: Acknowledgment.self
        )
    }

    /// Builds the PRISMA flow counts for the review chapter.
    func prisma(sessionId: String, counts: PrismaCounts) async throws -> Acknowledgment {
        try await client.post(
            form: [
                "action": "prisma",
                "session_id": sessionId,
                "identified": String(counts.identified),
                "screened": String(counts.screened),
                "eligible": String(counts.eligible),
                "included": String(counts.included),
                "excluded": String(counts.excluded),
            ],
            to: .thesisSession,
            as: Acknowledgment.self
        )
    }

    /// Loads the completion checklist.
    func checklist(sessionId: String) async throws -> [ThesisChecklistItem] {
        struct Wrapper: Decodable {
            let items: [ThesisChecklistItem]
            init(from decoder: Decoder) throws {
                let container = try decoder.flexibleContainer()
                items = container.flexArray("checklist", "items", "data", "tasks")
            }
        }
        let wrapper = try await client.get(
            .thesisSession,
            query: ["session_id": sessionId, "action": "checklist"],
            as: Wrapper.self
        )
        return wrapper.items
    }

    /// Analyses a captured poster image and returns the extracted outline
    /// (`poster_session_backend.php`, used by `PosterAnalysisActivity`).
    ///
    /// The Android client uploaded the bitmap as a base64 field, so the same
    /// form encoding is used here.
    func analyzePoster(userId: Int, imageBase64: String) async throws -> String {
        let response = try await client.post(
            form: [
                "action": "analyze",
                "user_id": String(userId),
                "image": imageBase64,
                "image_base64": imageBase64,
            ],
            to: .posterSession,
            as: PosterAnalysis.self
        )
        return response.text
    }

    /// Renders the thesis to a themed layout (`theme_layout_backend.php`).
    func themeLayout(sessionId: String, themeId: String) async throws -> Acknowledgment {
        try await client.post(
            form: ["session_id": sessionId, "theme_id": themeId],
            to: .themeLayout,
            as: Acknowledgment.self
        )
    }
}

/// The poster script has returned its payload under several keys.
private struct PosterAnalysis: Decodable {
    let text: String

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        let candidates = [
            container.flexString("outline"),
            container.flexString("analysis"),
            container.flexString("result"),
            container.flexString("text"),
            container.flexString("data"),
            container.flexString("message"),
        ]
        text = candidates.first { !$0.isEmpty } ?? ""
    }
}

/// AI features.
///
/// The Android build ships provider API keys inside `ApiKeys.kt` and calls
/// Groq, Gemini, DeepSeek, Mistral, and others directly. Embedding those keys in
/// a shipped iOS binary is worse than Android (they are trivially extractable
/// from the bundle), so this client routes every request through the
/// project's own `ask_ai2.php` gateway, which already fronts those providers.
struct AIAPI {

    private let client: HTTPClient

    init(client: HTTPClient = .shared) {
        self.client = client
    }

    /// Sends a prompt through the backend AI gateway (`ask_ai2.php`).
    func ask(
        prompt: String,
        userId: Int,
        model: String? = nil,
        context: String? = nil
    ) async throws -> String {
        var fields: [String: String] = [
            "prompt": prompt,
            "user_id": String(userId),
        ]
        if let model { fields["model"] = model }
        if let context { fields["context"] = context }

        let response = try await client.post(
            form: fields,
            to: .askAi,
            as: AIResponse.self
        )
        return response.text
    }

    /// Generates a taunt/comment for the live challenge screen (`taunt_ai.php`).
    func taunt(topic: String, userId: Int) async throws -> String {
        let response = try await client.post(
            form: ["topic": topic, "user_id": String(userId)],
            to: .tauntAi,
            as: AIResponse.self
        )
        return response.text
    }

    /// The gateway has returned the answer under several different keys.
    private struct AIResponse: Decodable {
        let text: String

        init(from decoder: Decoder) throws {
            let container = try decoder.flexibleContainer()
            let candidates = [
                container.flexString("response"),
                container.flexString("answer"),
                container.flexString("reply"),
                container.flexString("text"),
                container.flexString("content"),
                container.flexString("message"),
            ]
            text = candidates.first { !$0.isEmpty } ?? ""
        }
    }
}
