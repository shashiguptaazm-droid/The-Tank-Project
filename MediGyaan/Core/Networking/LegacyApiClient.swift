import Foundation

/// Ports `ApiClient`: the Android client's shared `OkHttpClient` (120 s
/// connect/read/write timeouts, BODY-level logging) and the eleven `Retrofit`
/// instances built on top of it — ten third-party AI providers plus the
/// server-side AI gateway at `Neurons/ai_provider_proxy.php`.
///
/// `HTTPClient` already owns transport for everything under
/// `APIConfig.baseURL`: URL composition, JSON/form encoding, multipart,
/// timeouts, `APILogger` recording and `APIError` mapping. None of that is
/// duplicated here. What `HTTPClient` cannot express is the one shape this file
/// needs — a JSON `POST` to an **absolute** URL outside `APIConfig.baseURL`
/// carrying a per-call `Authorization` header. `postObject(form:toAbsolute:)`
/// is form-encoded, and `APIConfig.Endpoint` has no case for
/// `ai_provider_proxy.php`. That gap is what ``LegacyApiClient`` fills.
///
/// Note that the gateway answers HTTP 200 with `success: false` for provider
/// outages and leans on the `permanent` flag to decide whether to cool a
/// provider down, so unlike `HTTPClient` this client **decodes and returns**
/// a logical failure rather than throwing it.
final class LegacyApiClient {

    /// Shared instance. `ApiClient` is a Kotlin `object`, so the port keeps one
    /// eagerly built client rather than a per-call-site session.
    static let shared = LegacyApiClient()

    /// `AiGatewayService` posts every action to this one script; `action` in
    /// the body is what tells the server which of them is being invoked.
    static let gatewayEndpoint = "ai_provider_proxy.php"

    private let session: URLSession

    init(session: URLSession? = nil) {
        if let session {
            self.session = session
        } else {
            let configuration = URLSessionConfiguration.default
            configuration.timeoutIntervalForRequest = APIConfig.requestTimeout
            configuration.timeoutIntervalForResource = APIConfig.resourceTimeout
            configuration.waitsForConnectivity = true
            configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
            self.session = URLSession(configuration: configuration)
        }
    }

    // MARK: - Server-side AI gateway

    /// Absolute URL of `ai_provider_proxy.php`. Same origin as
    /// `APIConfig.baseURL`, hence the same `X-App-Signature` requirement.
    var gatewayURL: URL {
        APIConfig.baseURL.appendingPathComponent(LegacyApiClient.gatewayEndpoint)
    }

    func gatewayChat(
        _ request: LegacyGatewayChatRequest
    ) async throws -> LegacyGatewayChatResponse {
        try await post(request, to: gatewayURL, headers: gatewayHeaders, as: LegacyGatewayChatResponse.self)
    }

    func gatewayModels(
        _ request: LegacyGatewayModelsRequest
    ) async throws -> LegacyGatewayModelsResponse {
        try await post(request, to: gatewayURL, headers: gatewayHeaders, as: LegacyGatewayModelsResponse.self)
    }

    func gatewayImages(
        _ request: LegacyGatewayImageRequest
    ) async throws -> LegacyGatewayImageResponse {
        try await post(request, to: gatewayURL, headers: gatewayHeaders, as: LegacyGatewayImageResponse.self)
    }

    // MARK: - Direct provider calls

    /// Direct, key-authenticated chat completion — the shape of
    /// `AiService.chatCompletion(@Url url, @Header("Authorization") auth, @Body)`.
    ///
    /// `ApiClient`'s own comment is the contract for this method: the per-provider
    /// Retrofit instances are retained only for endpoints the gateway does not
    /// proxy yet. New call sites belong on the gateway, or they reintroduce the
    /// key leak that `ai_provider_proxy.php` exists to close.
    func chatCompletion(
        url: URL,
        bearerToken: String?,
        request payload: LegacyAIChatRequest
    ) async throws -> LegacyAIChatResponse {
        var headers: [String: String] = [:]
        if let bearerToken, !bearerToken.isEmpty {
            headers["Authorization"] = "Bearer \(bearerToken)"
        }
        return try await post(payload, to: url, headers: headers, as: LegacyAIChatResponse.self)
    }

    /// Convenience overload resolving a provider-relative `path` against
    /// ``LegacyAIProvider/baseURL``.
    func chatCompletion(
        provider: LegacyAIProvider,
        path: String,
        bearerToken: String?,
        request payload: LegacyAIChatRequest
    ) async throws -> LegacyAIChatResponse {
        try await chatCompletion(
            url: provider.baseURL.appendingPathComponent(path),
            bearerToken: bearerToken,
            request: payload
        )
    }

    // MARK: - Transport shim

    private var gatewayHeaders: [String: String] {
        [
            "X-App-Signature": APIConfig.appSignature,
            "Authorization": "Bearer \(HTTPClient.shared.authToken ?? "")"
        ]
    }

    private func post<Request: Encodable, Response: Decodable>(
        _ payload: Request,
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

        let data = try await perform(request)
        do {
            return try JSONDecoder().decode(Response.self, from: data)
        } catch {
            let snippet = String(data: data.prefix(500), encoding: .utf8) ?? "<binary data>"
            RemoteLogger.log(
                tag: "DECODING_ERROR",
                message: "Failed decoding \(String(describing: responseType)): \(error.localizedDescription)",
                metadata: [
                    "targetType": String(describing: responseType),
                    "errorDescription": String(describing: error),
                    "dataSnippet": snippet
                ]
            )
            throw APIError.decoding(underlying: String(describing: error))
        }
    }

    private func perform(_ request: URLRequest) async throws -> Data {
        let startTime = CFAbsoluteTimeGetCurrent()
        let requestHeaders = request.allHTTPHeaderFields ?? [:]
        let url = request.url ?? APIConfig.baseURL

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            APILogger.shared.record(
                method: "POST",
                url: url,
                statusCode: 0,
                durationMs: Int((CFAbsoluteTimeGetCurrent() - startTime) * 1000),
                headers: requestHeaders,
                requestBody: request.httpBody,
                responseBody: nil,
                error: error
            )
            throw APIError.transport(message: error.localizedDescription)
        }

        guard let http = response as? HTTPURLResponse else {
            APILogger.shared.record(
                method: "POST",
                url: url,
                statusCode: 0,
                durationMs: Int((CFAbsoluteTimeGetCurrent() - startTime) * 1000),
                headers: requestHeaders,
                requestBody: request.httpBody,
                responseBody: data,
                error: APIError.invalidResponse
            )
            throw APIError.invalidResponse
        }

        let elapsedMs = Int((CFAbsoluteTimeGetCurrent() - startTime) * 1000)

        guard (200 ..< 300).contains(http.statusCode) else {
            let envelope = try? JSONDecoder().decode(LegacyGatewayEnvelope.self, from: data)
            let error = APIError.server(
                message: envelope?.error ?? envelope?.message ?? "HTTP \(http.statusCode)",
                code: http.statusCode
            )
            APILogger.shared.record(
                method: "POST",
                url: url,
                statusCode: http.statusCode,
                durationMs: elapsedMs,
                headers: requestHeaders,
                requestBody: request.httpBody,
                responseBody: data,
                error: error
            )
            throw error
        }

        APILogger.shared.record(
            method: "POST",
            url: url,
            statusCode: http.statusCode,
            durationMs: elapsedMs,
            headers: requestHeaders,
            requestBody: request.httpBody,
            responseBody: data,
            error: nil
        )
        return data
    }

    /// Minimal envelope used only to explain a non-2xx gateway response.
    private struct LegacyGatewayEnvelope: Decodable {
        let error: String?
        let message: String?
    }
}

// MARK: - Providers

/// Ports the ten `Retrofit` instances declared on `ApiClient`, keeping their
/// base URLs verbatim. Each is only for endpoints the gateway does not proxy.
enum LegacyAIProvider: String, CaseIterable {
    case groq
    case gemini
    case openRouter = "openrouter"
    case deepSeek = "deepseek"
    case mistral
    case cloudflare
    case cerebras
    case cohere
    case replicate
    case openAI = "openai"

    var baseURL: URL {
        switch self {
        case .groq: return URL(string: "https://api.groq.com/")!
        case .gemini: return URL(string: "https://generativelanguage.googleapis.com/")!
        case .openRouter: return URL(string: "https://openrouter.ai/")!
        case .deepSeek: return URL(string: "https://api.deepseek.com/")!
        case .mistral: return URL(string: "https://api.mistral.ai/")!
        case .cloudflare: return URL(string: "https://api.cloudflare.com/")!
        case .cerebras: return URL(string: "https://api.cerebras.ai/")!
        case .cohere: return URL(string: "https://api.cohere.ai/")!
        case .replicate: return URL(string: "https://api.replicate.com/")!
        case .openAI: return URL(string: "https://api.openai.com/")!
        }
    }
}

// MARK: - AiService payloads

/// Ports `AiService.Message`.
struct LegacyAIMessage: Codable, Equatable {
    let role: String
    let content: String

    init(role: String, content: String) {
        self.role = role
        self.content = content
    }
}

/// Ports `AiService.ResponseFormat`.
struct LegacyAIResponseFormat: Codable, Equatable {
    let type: String

    init(type: String) {
        self.type = type
    }
}

/// Ports `AiService.ChatRequest` for the direct, key-authenticated providers.
/// Defaults mirror the Kotlin ones: `temperature = 0.2`, `max_tokens = 2048`.
struct LegacyAIChatRequest: Encodable {
    let model: String
    let messages: [LegacyAIMessage]
    let temperature: Double
    let maxTokens: Int
    let responseFormat: LegacyAIResponseFormat?

    enum CodingKeys: String, CodingKey {
        case model
        case messages
        case temperature
        case maxTokens = "max_tokens"
        case responseFormat = "response_format"
    }

    init(
        model: String,
        messages: [LegacyAIMessage],
        temperature: Double = 0.2,
        maxTokens: Int = 2048,
        responseFormat: LegacyAIResponseFormat? = nil
    ) {
        self.model = model
        self.messages = messages
        self.temperature = temperature
        self.maxTokens = maxTokens
        self.responseFormat = responseFormat
    }
}

/// Ports `AiService.ChatResponse` — the OpenAI-compatible envelope that Groq,
/// OpenRouter, DeepSeek, Mistral, Cerebras and Replicate all return.
struct LegacyAIChatResponse: Decodable {

    struct MessageContent: Decodable {
        let content: String
    }

    struct Choice: Decodable {
        let message: MessageContent
    }

    let choices: [Choice]

    /// First choice's text, or an empty string when the provider returned none.
    var text: String { choices.first?.message.content ?? "" }
}

// MARK: - AiGatewayService payloads

/// Ports `AiGatewayService.GatewayChatRequest`. Defaults mirror Kotlin:
/// `temperature = 0.3`, `max_tokens = 2048`, `user_id = 0`, `source = "ai_chat"`.
struct LegacyGatewayChatRequest: Encodable {
    let provider: String
    let model: String
    let messages: [LegacyAIMessage]
    let temperature: Double
    let maxTokens: Int
    let userId: Int
    let source: String
    let responseFormat: LegacyAIResponseFormat?
    let action: String

    enum CodingKeys: String, CodingKey {
        case action
        case provider
        case model
        case messages
        case temperature
        case maxTokens = "max_tokens"
        case userId = "user_id"
        case source
        case responseFormat = "response_format"
    }

    init(
        provider: String,
        model: String,
        messages: [LegacyAIMessage],
        temperature: Double = 0.3,
        maxTokens: Int = 2048,
        userId: Int = 0,
        source: String = "ai_chat",
        responseFormat: LegacyAIResponseFormat? = nil,
        action: String = "chat"
    ) {
        self.provider = provider
        self.model = model
        self.messages = messages
        self.temperature = temperature
        self.maxTokens = maxTokens
        self.userId = userId
        self.source = source
        self.responseFormat = responseFormat
        self.action = action
    }
}

/// Ports `AiGatewayService.GatewayModelsRequest`.
struct LegacyGatewayModelsRequest: Encodable {
    let provider: String
    let action: String

    enum CodingKeys: String, CodingKey {
        case action
        case provider
    }

    init(provider: String, action: String = "models") {
        self.provider = provider
        self.action = action
    }
}

/// Ports `AiGatewayService.GatewayImageRequest`. Defaults mirror Kotlin:
/// `size = ""`, `user_id = 0`, `source = "poster_image"`.
struct LegacyGatewayImageRequest: Encodable {
    let provider: String
    let model: String
    let prompt: String
    let size: String
    let userId: Int
    let source: String
    let action: String

    enum CodingKeys: String, CodingKey {
        case action
        case provider
        case model
        case prompt
        case size
        case userId = "user_id"
        case source
    }

    init(
        provider: String,
        model: String,
        prompt: String,
        size: String = "",
        userId: Int = 0,
        source: String = "poster_image",
        action: String = "images"
    ) {
        self.provider = provider
        self.model = model
        self.prompt = prompt
        self.size = size
        self.userId = userId
        self.source = source
        self.action = action
    }
}

/// Ports `AiGatewayService.GatewayChatResponse`.
///
/// The server flattens every upstream shape into `text`, so one parser covers
/// OpenAI's `choices[0].message.content` and Cohere v2's
/// `message.content[].text` alike.
struct LegacyGatewayChatResponse: Decodable {
    let success: Bool
    let provider: String
    let model: String
    let text: String
    let error: String
    let permanent: Bool
    let durationMs: Int

    enum CodingKeys: String, CodingKey {
        case success
        case provider
        case model
        case text
        case error
        case permanent
        case durationMs = "duration_ms"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        success = try container.decodeIfPresent(Bool.self, forKey: .success) ?? false
        provider = try container.decodeIfPresent(String.self, forKey: .provider) ?? ""
        model = try container.decodeIfPresent(String.self, forKey: .model) ?? ""
        text = try container.decodeIfPresent(String.self, forKey: .text) ?? ""
        error = try container.decodeIfPresent(String.self, forKey: .error) ?? ""
        permanent = try container.decodeIfPresent(Bool.self, forKey: .permanent) ?? false
        durationMs = try container.decodeIfPresent(Int.self, forKey: .durationMs) ?? 0
    }

    /// Present only on 503, meaning the provider has no usable credential.
    var unavailable: Bool {
        !success && error.range(of: "not available", options: .caseInsensitive) != nil
    }
}

/// Ports `AiGatewayService.GatewayModelsResponse`.
struct LegacyGatewayModelsResponse: Decodable {
    let success: Bool
    let provider: String
    let error: String
    let models: LegacyGatewayModelList?

    enum CodingKeys: String, CodingKey {
        case success
        case provider
        case error
        case models
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        success = try container.decodeIfPresent(Bool.self, forKey: .success) ?? false
        provider = try container.decodeIfPresent(String.self, forKey: .provider) ?? ""
        error = try container.decodeIfPresent(String.self, forKey: .error) ?? ""
        models = try container.decodeIfPresent(LegacyGatewayModelList.self, forKey: .models)
    }

    /// Provider-agnostic model identifiers from whichever envelope came back.
    var modelIds: [String] { models?.ids() ?? [] }
}

/// Ports `AiGatewayService.GatewayModelList` / `GatewayModelEntry`.
struct LegacyGatewayModelList: Decodable {

    struct Entry: Decodable {
        let id: String?
        let name: String?

        enum CodingKeys: String, CodingKey {
            case id
            case name
        }
    }

    /// OpenRouter/Cerebras send `data`; Cohere sends `models`.
    let data: [Entry]?
    let models: [Entry]?

    enum CodingKeys: String, CodingKey {
        case data
        case models
    }

    func ids() -> [String] {
        let entries = data ?? models ?? []
        return entries
            .compactMap { $0.id ?? $0.name }
            .filter { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
    }
}

/// Ports `AiGatewayService.GatewayImageResponse` / `GatewayImageEnvelope`.
struct LegacyGatewayImageResponse: Decodable {
    let success: Bool
    let error: String
    let data: LegacyGatewayImageEnvelope?

    enum CodingKeys: String, CodingKey {
        case success
        case error
        case data
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        success = try container.decodeIfPresent(Bool.self, forKey: .success) ?? false
        error = try container.decodeIfPresent(String.self, forKey: .error) ?? ""
        data = try container.decodeIfPresent(LegacyGatewayImageEnvelope.self, forKey: .data)
    }

    var entries: [LegacyGatewayImageEntry] { data?.data ?? [] }
}

struct LegacyGatewayImageEnvelope: Decodable {
    let data: [LegacyGatewayImageEntry]
}

/// Ports `AiGatewayService.GatewayImageEntry`. OpenRouter returns `url` or
/// `b64_json` depending on the model, so both are optional.
struct LegacyGatewayImageEntry: Decodable {
    let url: String?
    let b64Json: String?

    enum CodingKeys: String, CodingKey {
        case url
        case b64Json = "b64_json"
    }
}