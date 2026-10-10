import Foundation

// MARK: - Direct provider chat completion
//
// Ports `AiService` (`data/remote/AiService.kt`) — the single-method Retrofit
// interface behind Android's ten direct AI-provider clients in `ApiClient`.
//
// `AiService` is `@POST @Url url / @Header("Authorization") auth /
// @Body ChatRequest : ChatResponse`. Because Retrofit resolves the URL from the
// per-provider `baseUrl` at the call site, the Kotlin file carries **no** path,
// **no** host and **no** key — the caller supplied all three. That is preserved:
// `AIAPIProviderPath` writes the commonly used paths down once, and the bearer
// token arrives as a parameter, never as a stored value.
//
// `ApiClient` is explicit that these per-provider clients are dead weight kept
// only for endpoints `ai_provider_proxy.php` does not proxy yet ("do not add new
// call sites against them: doing so reintroduces the key leak"). The same
// warning applies verbatim to this file.
//
// ## Already carried by `LegacyApiClient` (batch 4) — not redeclared
// * `ChatRequest` → `LegacyAIChatRequest` (identical keys: `model`, `messages`,
//   `temperature` = 0.2, `max_tokens` = 2048, `response_format`)
// * `Message` → `LegacyAIMessage`
// * `ResponseFormat` → `LegacyAIResponseFormat`
// * `ChatResponse` / `Choice` / `MessageContent` → `LegacyAIChatResponse`
// * `ApiClient`'s ten base URLs → `LegacyAIProvider`
//
// What remains — and what this file adds — is the **Gemini** half of
// `AiService.kt`, which `LegacyApiClient` does not model, plus a tolerant
// reader for Gemini's reply shape.

extension AIAPI {

    /// Ports `AiService.chatCompletion(@Url url, @Header("Authorization") auth, @Body request)`.
    ///
    /// - Returns: `choices[0].message.content`, or an empty string when the
    ///   provider returned no choice (`LegacyAIChatResponse.text`).
    func providerChatCompletion(
        url: URL,
        bearerToken: String?,
        request payload: LegacyAIChatRequest
    ) async throws -> String {
        let response = try await LegacyApiClient.shared.chatCompletion(
            url: url,
            bearerToken: bearerToken,
            request: payload
        )
        return response.text
    }

    /// Ports the same call once the caller has resolved host + path from
    /// ``LegacyAIProvider``, which is what Retrofit's `@Url` did on Android.
    ///
    /// Defaults to the OpenAI-compatible `v1/chat/completions`; pass `path`
    /// explicitly for Groq (`openai/v1/…`) or OpenRouter (`api/v1/…`).
    func providerChatCompletion(
        provider: LegacyAIProvider,
        path: String = AIAPIProviderPath.chatCompletions,
        bearerToken: String?,
        request payload: LegacyAIChatRequest
    ) async throws -> String {
        try await providerChatCompletion(
            url: provider.baseURL.appendingPathComponent(path),
            bearerToken: bearerToken,
            request: payload
        )
    }

    /// Ports `AiService.GeminiRequest` — Google does not speak the OpenAI chat
    /// envelope, so this posts `contents` + `generationConfig` to
    /// `v1beta/models/{model}:generateContent`.
    ///
    /// The key is a parameter, never a stored constant. It is sent as
    /// `x-goog-api-key`; Android sent the same key as an `Authorization`
    /// header here (see the report's RISK note), which Google's REST API ignores.
    func geminiGenerateContent(
        model: String,
        apiKey: String?,
        request payload: AIAPIGeminiRequest
    ) async throws -> AIAPIGeminiResponse {
        var headers: [String: String] = [:]
        if let apiKey, !apiKey.isEmpty {
            headers["x-goog-api-key"] = apiKey
        }
        let url = AIAPIProviderPath.geminiGenerateContentURL(model: model)
        return try await AIAPIDirectProviderTransport.post(
            payload,
            to: url,
            headers: headers,
            as: AIAPIGeminiResponse.self
        )
    }
}

// MARK: - Provider paths

/// Ports the URL the Kotlin caller assembled by hand for `AiService`'s `@Url`.
///
/// None of these strings exist in `AiService.kt` — Retrofit hid them. The
/// OpenAI-compatible entries are inferred from the `baseUrl` values in
/// `ApiClient` plus the discovery paths in `ModelDiscoveryService`
/// (`openai/v1/models` for Groq, `api/v1/models` for OpenRouter); pass
/// `path:` explicitly if a provider ever diverges.
enum AIAPIProviderPath {

    /// OpenAI-compatible chat path for Mistral, DeepSeek, Cerebras, Cohere,
    /// Replicate, Cloudflare and the OpenAI fallback.
    static let chatCompletions = "v1/chat/completions"

    /// Groq nests OpenAI under `openai/v1`.
    static let groqChatCompletions = "openai/v1/chat/completions"

    /// OpenRouter nests it under `api/v1`.
    static let openRouterChatCompletions = "api/v1/chat/completions"

    /// Gemini's generation path. The model lives in the URL, not the body.
    static func geminiGenerateContent(model: String) -> String {
        "v1beta/models/\(model):generateContent"
    }

    /// Absolute Gemini generation URL, built segment-by-segment so the `:`
    /// verb survives path encoding.
    static func geminiGenerateContentURL(model: String) -> URL {
        var url = LegacyAIProvider.gemini.baseURL
        url.appendPathComponent("v1beta")
        url.appendPathComponent("models")
        url.appendPathComponent("\(model):generateContent")
        return url
    }

    /// The inferred chat path for a provider. Providers that are not
    /// OpenAI-compatible fall back to the standard path; pass `path:` to override.
    static func chatCompletions(for provider: LegacyAIProvider) -> String {
        switch provider {
        case .groq: return groqChatCompletions
        case .openRouter: return openRouterChatCompletions
        case .gemini: return geminiGenerateContent(model: "gemini-1.5-flash")
        default: return chatCompletions
        }
    }
}

// MARK: - Gemini payloads

/// Ports `AiService.Part` (`text`), and `model/GeminiPart`, which is the same
/// single-field class declared in `ThesisModels.kt`.
struct AIAPIGeminiPart: Encodable, Equatable {
    let text: String

    init(text: String) {
        self.text = text
    }
}

/// Ports `AiService.Content` (`parts` only) and `model/GeminiContent`.
///
/// `role` is the optional addition Google's schema allows but Kotlin omits; it
/// is encoded only when supplied, matching Gson's null-omitting behaviour.
struct AIAPIGeminiContent: Encodable, Equatable {
    let parts: [AIAPIGeminiPart]
    let role: String?

    enum CodingKeys: String, CodingKey {
        case parts
        case role
    }

    init(parts: [AIAPIGeminiPart], role: String? = nil) {
        self.parts = parts
        self.role = role
    }
}

/// Ports `AiService.GenerationConfig` (`temperature`, `maxOutputTokens`) and the
/// superset `model/GeminiGenerationConfig`, which adds `responseMimeType`.
/// Keys are camelCase here — Google's own casing, unlike the rest of the file.
struct AIAPIGeminiGenerationConfig: Encodable, Equatable {
    let temperature: Double
    let maxOutputTokens: Int
    let responseMimeType: String?

    enum CodingKeys: String, CodingKey {
        case temperature
        case maxOutputTokens
        case responseMimeType
    }

    init(temperature: Double, maxOutputTokens: Int, responseMimeType: String? = nil) {
        self.temperature = temperature
        self.maxOutputTokens = maxOutputTokens
        self.responseMimeType = responseMimeType
    }
}

/// Ports `AiService.GeminiRequest`. There is deliberately no `model` field:
/// on Google's REST API the model is part of the path.
struct AIAPIGeminiRequest: Encodable {
    let contents: [AIAPIGeminiContent]
    let generationConfig: AIAPIGeminiGenerationConfig

    init(contents: [AIAPIGeminiContent], generationConfig: AIAPIGeminiGenerationConfig) {
        self.contents = contents
        self.generationConfig = generationConfig
    }
}

/// Ports the shape of a `generateContent` reply.
///
/// Deliberately tolerant, and **not** in Kotlin: `AiService` declares only
/// `ChatResponse`, so a Gemini reply — `{ "candidates": [ { "content": { "parts":
/// [ { "text": … } ] } } ] }` — could not be decoded there at all. Reading it
/// this way keeps the two provider families from sharing one wrong envelope.
struct AIAPIGeminiResponse: Decodable {

    /// One fragment of generated text.
    struct Part: Decodable {
        let text: String

        init(from decoder: Decoder) throws {
            text = try decoder.flexibleContainer().flexString("text")
        }
    }

    /// `content.parts` of one candidate.
    struct Content: Decodable {
        let parts: [Part]

        init(from decoder: Decoder) throws {
            parts = try decoder.flexibleContainer().flexArray("parts", "text")
        }
    }

    /// One generation candidate. `finishReason` is `STOP` on success, or the
    /// reason generation was cut short.
    struct Candidate: Decodable {
        let content: Content?
        let finishReason: String

        init(from decoder: Decoder) throws {
            let container = try decoder.flexibleContainer()
            let payload: Content? = container.flexObject("content")
            content = payload
            finishReason = container.flexString("finishReason", "finish_reason")
        }
    }

    let candidates: [Candidate]

    init(from decoder: Decoder) throws {
        candidates = try decoder.flexibleContainer().flexArray("candidates")
    }

    /// First non-empty candidate's concatenated text.
    var text: String {
        for candidate in candidates {
            let joined = (candidate.content?.parts ?? [])
                .map(\.text)
                .joined()
            if !joined.isEmpty { return joined }
        }
        return ""
    }

    /// `true` when the provider reported why it stopped, or truncated.
    var isTruncated: Bool {
        for candidate in candidates where !candidate.finishReason.isEmpty {
            if candidate.finishReason != "STOP" { return true }
        }
        return false
    }
}

// MARK: - Transport

/// Ports the `ApiClient` OkHttp interceptor behaviour for the one shape
/// `LegacyApiClient` cannot express: a JSON `POST` to an absolute **Google**
/// URL whose reply is not the OpenAI chat envelope.
///
/// Same contract as `LegacyApiClient.post` — 120 s timeout, BODY-level
/// `APILogger` recording, `APIError` mapping — so the two are indistinguishable
/// in the Network Inspector.
private enum AIAPIDirectProviderTransport {

    private static let session: URLSession = {
        let configuration = URLSessionConfiguration.default
        configuration.timeoutIntervalForRequest = APIConfig.requestTimeout
        configuration.timeoutIntervalForResource = APIConfig.resourceTimeout
        configuration.waitsForConnectivity = true
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        return URLSession(configuration: configuration)
    }()

    static func post<Body: Encodable, Response: Decodable>(
        _ payload: Body,
        to url: URL,
        headers: [String: String],
        as responseType: Response.Type
    ) async throws -> Response {
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = APIConfig.requestTimeout
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue(APIConfig.userAgent, forHTTPHeaderField: "User-Agent")
        for (field, value) in headers where !value.isEmpty {
            request.setValue(value, forHTTPHeaderField: field)
        }
        request.httpBody = try JSONEncoder().encode(payload)

        let startTime = CFAbsoluteTimeGetCurrent()
        let requestHeaders = request.allHTTPHeaderFields ?? [:]

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await AIAPIDirectProviderTransport.session.data(for: request)
        } catch {
            record(statusCode: 0, request: request, startTime: startTime, data: nil, error: error)
            throw APIError.transport(message: error.localizedDescription)
        }

        guard let http = response as? HTTPURLResponse else {
            record(statusCode: 0, request: request, startTime: startTime, data: data, error: APIError.invalidResponse)
            throw APIError.invalidResponse
        }

        guard (200 ..< 300).contains(http.statusCode) else {
            let message = AIAPIProviderErrorEnvelope.message(in: data) ?? "HTTP \(http.statusCode)"
            let error = APIError.server(message: message, code: http.statusCode)
            record(statusCode: http.statusCode, request: request, startTime: startTime, data: data, error: error)
            throw error
        }

        record(statusCode: http.statusCode, request: request, startTime: startTime, data: data, error: nil)

        do {
            return try JSONDecoder().decode(Response.self, from: data)
        } catch {
            throw APIError.decoding(underlying: String(describing: error))
        }
    }

    private static func record(
        statusCode: Int,
        request: URLRequest,
        startTime: CFAbsoluteTime,
        data: Data?,
        error: Error?
    ) {
        APILogger.shared.record(
            method: "POST",
            url: request.url ?? APIConfig.baseURL,
            statusCode: statusCode,
            durationMs: Int((CFAbsoluteTimeGetCurrent() - startTime) * 1000),
            headers: request.allHTTPHeaderFields ?? [:],
            requestBody: request.httpBody,
            responseBody: data,
            error: error
        )
    }
}

/// Ports Google's error envelope, `{"error": {"message": …, "code": …}}`,
/// which is nested where the MediGyaan backend's is flat. Used only to explain a
/// non-2xx response — a provider outage is a thrown `APIError.server`, not a
/// value, because unlike the gateway this path has no `success: false` on 200.
private struct AIAPIProviderErrorEnvelope: Decodable {

    struct Payload: Decodable {
        let message: String

        init(from decoder: Decoder) throws {
            message = try decoder.flexibleContainer().flexString("message", "status", "detail")
        }
    }

    static func message(in data: Data) -> String? {
        guard let envelope = try? JSONDecoder().decode(AIAPIProviderErrorEnvelope.self, from: data) else {
            return nil
        }
        return envelope.message.isEmpty ? nil : envelope.message
    }

    let message: String

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        let payload: Payload? = container.flexObject("error")
        let nested = payload?.message ?? ""
        message = nested.isEmpty ? container.flexString("message", "error") : nested
    }
}