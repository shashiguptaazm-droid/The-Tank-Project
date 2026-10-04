import Foundation

/// AI model candidate specification (provider + model ID).
public struct ModelCandidate: Identifiable, Codable, Hashable {
    public var id: String { "\(provider):\(model)" }
    public let provider: String
    public let model: String

    public init(provider: String, model: String) {
        self.provider = provider
        self.model = model
    }
}

/// Dynamic LLM provider failover and rotation engine.
/// 1:1 port of Android `ModelRotator.kt`.
public final class ModelRotator {

    public static let shared = ModelRotator()

    private let userDefaultsKey = "model_rotator_prefs_v1"
    private let failureCooldownSeconds: TimeInterval = 24 * 60 * 60 // 24 hours

    // Hardcoded fallback models strictly matching Android `ModelRotator.fallbackModels`
    private let fallbackModels: [String: [String]] = [
        "groq": ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b", "llama-3.1-8b-instant"],
        "openrouter": [
            "google/gemini-2.5-flash",
            "meta-llama/llama-3-8b-instruct:free",
            "mistralai/mistral-7b-instruct:free"
        ],
        "cloudflare": [
            "@cf/meta/llama-3-8b-instruct",
            "@cf/meta/llama-3.1-8b-instruct",
            "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b"
        ],
        "deepseek": ["deepseek-chat"],
        "mistral": ["mistral-large-latest", "open-mixtral-8x22b"],
        "cerebras": ["llama3.1-70b", "llama3.1-8b"],
        "cohere": ["command-r-plus", "command-r"],
        "replicate": ["meta/meta-llama-3-70b-instruct"],
        "gemini": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"]
    ]

    private var failureCounts: [String: Int] = [:]
    private var providerCooldowns: [String: Date] = [:]
    private var lastSuccessfulCandidate: ModelCandidate?

    private init() {
        // Clear provider cooldowns on startup for resilient inference
        providerCooldowns["gemini"] = nil
        providerCooldowns["deepseek"] = nil
    }

    /// Build prioritized candidate pool based on provider, past successes, and failure penalties.
    public func buildPool(provider: String = "auto") -> [ModelCandidate] {
        let cleanProvider = provider.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        var pool: [ModelCandidate] = []
        let now = Date()

        if cleanProvider == "auto" {
            let providers = [
                "openrouter",
                "groq",
                "cerebras",
                "deepseek",
                "cohere",
                "mistral",
                "replicate",
                "cloudflare",
                "gemini"
            ]

            // Place last successful model first
            if let last = lastSuccessfulCandidate, !isProviderCoolingDown(last.provider, now: now) {
                pool.append(last)
            }

            var candidates: [ModelCandidate] = []
            for p in providers {
                if isProviderCoolingDown(p, now: now) { continue }
                let models = fallbackModels[p] ?? []
                for m in models {
                    let cand = ModelCandidate(provider: p, model: m)
                    if cand != lastSuccessfulCandidate {
                        candidates.append(cand)
                    }
                }
            }

            // Sort by fewest failure penalties
            candidates.sort { getFailureCount(for: $0) < getFailureCount(for: $1) }
            pool.append(contentsOf: candidates)
        } else {
            if isProviderCoolingDown(cleanProvider, now: now) { return [] }
            let models = fallbackModels[cleanProvider] ?? []
            var candidates = models.map { ModelCandidate(provider: cleanProvider, model: $0) }
            candidates.sort { getFailureCount(for: $0) < getFailureCount(for: $1) }
            pool.append(contentsOf: candidates)
        }

        return pool
    }

    public func markSuccess(candidate: ModelCandidate) {
        lastSuccessfulCandidate = candidate
        failureCounts[candidate.id] = 0
    }

    public func markFailure(candidate: ModelCandidate, cooldownProvider: Bool = false) {
        let current = failureCounts[candidate.id] ?? 0
        failureCounts[candidate.id] = current + 1

        if cooldownProvider {
            providerCooldowns[candidate.provider] = Date().addingTimeInterval(failureCooldownSeconds)
        }
    }

    private func isProviderCoolingDown(_ provider: String, now: Date) -> Bool {
        guard let cooldownUntil = providerCooldowns[provider] else { return false }
        if now < cooldownUntil {
            return true
        } else {
            providerCooldowns[provider] = nil
            return false
        }
    }

    private func getFailureCount(for candidate: ModelCandidate) -> Int {
        failureCounts[candidate.id] ?? 0
    }
}
