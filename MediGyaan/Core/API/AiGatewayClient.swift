import Foundation

/// Ports `AiGatewayService`: the single client that talks to the MediGyaan AI
/// gateway, `Neurons/ai_provider_proxy.php` (`BackendEndpoints.aiProxy`).
///
/// ## WHY THIS EXISTS
///
/// The Android client used to call Groq / OpenRouter / DeepSeek / Mistral /
/// Cerebras / Hugging Face directly, with every provider API key compiled into
/// the APK — extractable by anyone running `strings classes.dex`. All provider
/// traffic now goes through `ai_provider_proxy.php`, which holds the keys
/// server-side. The client sends a provider **name** and never a key or a base
/// URL, so adding or retiring a provider is a server change, not an app
/// release. Nothing in this file is a credential, and nothing may become one.
///
/// ## RELATIONSHIP TO `LegacyApiClient`
///
/// `Core/Networking/LegacyApiClient.swift` (batch 4) already ports this file's
/// transport and **every** payload type: `LegacyGatewayChatRequest`,
/// `LegacyGatewayModelsRequest`, `LegacyGatewayImageRequest` and the matching
/// responses. None of that is redeclared here — this type consumes it.
///
/// What is added is the call shape Kotlin expressed with a **read-only computed
/// property**. Each request data class carried
/// `val action: String get() = "chat"`, commented in Android as "a constant of
/// the gateway, not something callers set." The batch-4 ports took `action` as
/// an ordinary initialiser parameter, which lets a caller pair a chat body with
/// the `models` action and get a confusing server-side error. This client never
/// exposes `action`; ``AiGatewayAction`` fixes it per method.
///
/// ## FAILURE CONVENTION — do not "fix" this
///
/// The gateway reports a provider outage **in band**: HTTP 200 with
/// `success: false`, a populated `error`, and `permanent` telling the caller
/// whether the provider is worth cooling down. Kotlin's `Retrofit` returned
/// that body rather than throwing, and both Android call sites handled a failed
/// call as a value (`AiChatActivity.kt:6510`, `PosterAnalysisActivity.kt:1032`).
/// `LegacyApiClient` preserves that: it throws only on a non-2xx status. Treat
/// a returned `success == false` as a normal outcome, not an exception.
final class AiGatewayClient {

    /// `ApiClient.aiGateway` is a lazily built singleton over the shared
    /// `OkHttpClient`, so the port keeps one eagerly built facade.
    static let shared = AiGatewayClient()

    private let transport: LegacyApiClient

    init(transport: LegacyApiClient = .shared) {
        self.transport = transport
    }

    /// Absolute URL of `ai_provider_proxy.php`, the same origin as
    /// ``APIConfig/baseURL`` and therefore the same `X-App-Signature`
    /// requirement.
    var endpoint: URL { transport.gatewayURL }

    // MARK: - Operations

    /// Ports `AiGatewayService.chat` — a chat completion against the provider
    /// named in `provider`.
    ///
    /// Defaults mirror `GatewayChatRequest`: `temperature = 0.3`,
    /// `max_tokens = 2048`, `user_id = 0`, `source = "ai_chat"`.
    /// `response_format` is omitted from the JSON body when `nil`, matching
    /// Gson's null-skipping and `JSONEncoder`'s `encodeIfPresent`.
    ///
    /// Returns normally when the gateway reports a logical failure. Inspect
    /// ``LegacyGatewayChatResponse/success``; feed a failure to
    /// ``needsProviderCooldown(_:)``.
    func chat(
        provider: String,
        model: String,
        messages: [LegacyAIMessage],
        temperature: Double = 0.3,
        maxTokens: Int = 2048,
        userId: Int = 0,
        source: String = "ai_chat",
        responseFormat: LegacyAIResponseFormat? = nil
    ) async throws -> LegacyGatewayChatResponse {
        let request = LegacyGatewayChatRequest(
            provider: provider,
            model: model,
            messages: messages,
            temperature: temperature,
            maxTokens: maxTokens,
            userId: userId,
            source: source,
            responseFormat: responseFormat,
            action: AiGatewayAction.chat.rawValue
        )
        return try await transport.gatewayChat(request)
    }

    /// Ports `AiGatewayService.models` — the provider's catalogue.
    ///
    /// Providers disagree on the envelope: OpenRouter and Cerebras send
    /// `{"data":[{"id":…}]}` while Cohere sends `{"models":[{"name":…}]}`.
    /// Read ``LegacyGatewayModelsResponse/modelIds`` rather than either raw
    /// array; it handles both and drops blank identifiers.
    func models(provider: String) async throws -> LegacyGatewayModelsResponse {
        let request = LegacyGatewayModelsRequest(
            provider: provider,
            action: AiGatewayAction.models.rawValue
        )
        return try await transport.gatewayModels(request)
    }

    /// Ports `AiGatewayService.images` — image generation.
    ///
    /// Defaults mirror `GatewayImageRequest`: `size = ""`, `user_id = 0`,
    /// `source = "poster_image"`. Read
    /// ``LegacyGatewayImageResponse/entries``; each entry carries either `url`
    /// or `b64_json` depending on the model, so both are optional.
    func images(
        provider: String,
        model: String,
        prompt: String,
        size: String = "",
        userId: Int = 0,
        source: String = "poster_image"
    ) async throws -> LegacyGatewayImageResponse {
        let request = LegacyGatewayImageRequest(
            provider: provider,
            model: model,
            prompt: prompt,
            size: size,
            userId: userId,
            source: source,
            action: AiGatewayAction.images.rawValue
        )
        return try await transport.gatewayImages(request)
    }

    // MARK: - Rotation verdict

    /// Ports the rotation rule both Android call sites apply to a failed chat
    /// response.
    ///
    /// `AiChatActivity.kt:6519` and `PosterAnalysisActivity.kt:1033` both
    /// branch on `response.unavailable || response.permanent` to choose between
    /// `ModelRotator.markProviderFailure` (cool the provider down) and
    /// `ModelRotator.markFailure` (just count it). The gateway sets `permanent`
    /// true for an upstream 401/403/429 — retrying is pointless — and false for
    /// a 5xx or a network blip, where the next candidate should get its turn.
    /// `unavailable` means the provider has no usable credential server-side.
    ///
    /// A successful response never cools anything down.
    func needsProviderCooldown(_ response: LegacyGatewayChatResponse) -> Bool {
        !response.success && (response.unavailable || response.permanent)
    }
}

/// Ports the three computed `action` getters declared on `GatewayChatRequest`,
/// `GatewayModelsRequest` and `GatewayImageRequest`.
///
/// `AiGatewayService` posts every operation to the same PHP script; `action` in
/// the JSON body is what tells `ai_provider_proxy.php` which is being invoked.
/// Kotlin made each a read-only computed property so callers could not choose
/// it — modelling it as an enum keeps that guarantee and keeps the three literal
/// strings in one place.
enum AiGatewayAction: String {
    case chat
    case models
    case images
}
