import Foundation

/// Ports `BackendEndpoints`: the PHP endpoint registry for the MediGyaan backend.
///
/// Android ships this as a second catalogue alongside `APIConfig`, so the shape
/// (one namespace of `String` constants, each a full absolute URL) is preserved
/// here rather than folded into `APIConfig.Endpoint`.
///
/// These are URLs, not credentials, so they carry no security weight — they live
/// here only so the address of a backend is written down once instead of being
/// copied between call sites. Everything under `/Neurons/` is the PHP backend;
/// nothing here is a key.
///
/// Android moved these out of `ApiKeys.kt`, which previously held the URL
/// constants next to the provider secrets. Shipping credentials inside the APK
/// means anyone can extract them with `strings classes.dex`.
///
/// ## Relationship to `APIConfig`
///
/// * `base` is byte-for-byte the value of ``APIConfig/baseURL``; it is restated
///   because the Android registry composes every endpoint as `BASE + <file>` and
///   the catalogue is read verbatim against that original.
/// * Three entries are already reachable through `APIConfig.Endpoint` and are
///   wired into a client: `thesisSessionBackend` → `.thesisSession`
///   (`ThesisAPI`), `posterSessionBackend` → `.posterSession` (`ThesisAPI`), and
///   `askAI` → `.askAi` (`AIAPI`).
/// * Two entries have **no** `APIConfig.Endpoint` case and no client:
///   `aiProxy` and `chatHistory`.
enum BackendEndpoints {

    /// Root every other constant in this registry is composed against.
    static let base = "https://medigyaan.com/Neurons/"

    /// AI gateway. Holds all third-party provider credentials server-side.
    static let aiProxy = base + "ai_provider_proxy.php"

    static let thesisSessionBackend = base + "thesis_session_backend.php"
    static let posterSessionBackend = base + "poster_session_backend.php"
    static let askAI = base + "ask_ai2.php"
    static let chatHistory = base + "chat_history.php"
}

/// Ports `AiModelDefaults`: model identifiers chosen server-side.
///
/// These are names, not secrets.
///
/// The defaults here are the ones verified live against the providers on
/// 2026-09-30. They are overridable from the server via the gateway's `models`
/// action, so a provider retiring a model is a server change, not an app release.
///
/// Note that ``ModelRotator`` carries its own, older fallback table; the values
/// here supersede it wherever they overlap.
enum AiModelDefaults {

    /// OpenRouter, verified working.
    static let openRouterDefault = "google/gemini-2.5-flash"

    /// Cohere v2. `command-r` / `command-r-plus` are the v1 names and 404 now.
    static let cohereDefault = "command-a-03-2025"

    /// Cerebras. `llama3.1-70b` / `llama3.1-8b` were retired; 402 without credit.
    static let cerebrasDefault = "gpt-oss-120b"

    static let groqDefault = "llama-3.1-8b-instant"
    static let deepseekDefault = "deepseek-chat"
    static let mistralDefault = "mistral-large-latest"

    static let endpointModel = "deepseek-r1:70b"
    static let endpointBaseURL = "https://endpointai-backend-production.up.railway.app/"
}