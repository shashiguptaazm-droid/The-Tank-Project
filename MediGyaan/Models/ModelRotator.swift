import Foundation

/// Ports `ModelCandidate`: Android's `data class ModelCandidate(val provider:
/// String, val model: String)` — the `(provider, model)` pair that every
/// rotation decision is made about.
///
/// `Identifiable`/`Codable` are additive conveniences; Kotlin's `data class`
/// already gave structural equality and hashing over both fields, which the
/// `Hashable` conformance reproduces, so `==` means what `equals` meant.
struct ModelCandidate: Identifiable, Codable, Hashable {
    var id: String { "\(provider):\(model)" }
    let provider: String
    let model: String

    init(provider: String, model: String) {
        self.provider = provider
        self.model = model
    }
}

/// Ports Android `object ModelRotator` (`ModelRotator.kt`): the failover engine
/// that orders a pool of `(provider, model)` candidates for the AI chat, thesis
/// and poster flows.
///
/// ## Rotation algorithm
///
/// `buildPool(provider:)` has the same two shapes as Kotlin's `buildPool`:
///
/// * `"auto"` — walk a fixed nine-provider priority list
///   (`openrouter, groq, cerebras, deepseek, cohere, mistral, replicate,
///   cloudflare, gemini`), skipping any provider whose cooldown has not expired;
///   pin the last successful candidate to the head of the pool when its provider
///   is not cooling down; then append everything else **sorted by ascending
///   failure count**. A candidate equal to the last successful one is not
///   duplicated.
/// * a named provider — an empty pool while that provider is cooling down,
///   otherwise the same ordering scoped to the provider, with the last
///   successful candidate hoisted to the head when it belongs to that provider.
///
/// The sort is **stable** in Kotlin (`sortedBy`), so equal failure counts keep
/// provider-priority order; the port sorts with an explicit index tiebreak
/// because Swift's `sort(by:)` makes no such guarantee.
///
/// There is no round-robin and no weighting: position in the pool is the only
/// scheduling signal, and the only state carried forward is the failure counter,
/// the sticky last success, and the per-provider cooldown expiry.
///
/// ## Cooldown and removal
///
/// A provider is dropped from every future pool until its expiry passes, which is
/// cleared lazily on the next `buildPool` that observes it (`isProviderCoolingDown`).
/// `markSuccess` also lifts the cooldown immediately, so a provider that recovers
/// is retried on the very next request. Nothing is ever deleted permanently — a
/// cooled-down provider simply produces an empty pool until it expires, which the
/// callers read as "no provider available".
///
/// ## Thread safety
///
/// Android's `object` is unsynchronised: `dynamicModels`, `fallbackModels` reads
/// and every `SharedPreferences` access are plain mutable state, reached from the
/// UI thread *and* from the background executor `EduLabsApplication.onCreate()`
/// spins up to call `ModelRotator.init(this)`.
///
/// The port is stricter — every public member takes `lock`, an `NSLock`, because
/// ``AppDelegateBootstrap/prewarmBackgroundSystems()`` warms this type off the
/// main thread while a view model may build a pool on it. `NSLock` rather than an
/// `actor` because `AppDelegateBootstrap` calls `buildPool()` from a non-`async`
/// `DispatchQueue` closure, where an `actor` hop would not compile. Private
/// helpers are the *unlocked* cores and are only ever called with `lock` held;
/// `NSLock` is non-recursive, so no public method may re-enter one.
///
/// ## Persistence
///
/// Kotlin keeps state in a dedicated `SharedPreferences` file,
/// `model_rotator_prefs`. iOS has no equivalent, so state lives in
/// `UserDefaults.standard` under the ``userDefaultsKey`` prefix, hydrated once in
/// `init()` — which is the same work Android performed off the launch thread via
/// `Executors.newSingleThreadExecutor().execute { ModelRotator.init(this) }`.
///
/// No secrets live here or in the Kotlin original: this file holds only provider
/// *names* and model *identifiers*, never a key.
final class ModelRotator {

    /// Ports `ModelRotator`'s Kotlin `object` singleton: `EduLabsApplication`
    /// reaches the rotator as `ModelRotator.<fn>` with no receiver, so the port
    /// keeps exactly one instance. First touch runs ``init()``.
    static let shared = ModelRotator()

    // MARK: - Persisted keys

    /// Ports `PREFS_NAME = "model_rotator_prefs"`. iOS has no per-file preference
    /// store, so this doubles as the prefix every rotator key is filed under
    /// inside `UserDefaults.standard`, keeping the rotator out of the app's
    /// shared keyspace.
    private let userDefaultsKey = "model_rotator_prefs_v1"

    /// Ports `KEY_LAST_SUCCESSFUL_PROVIDER`.
    private let keyLastSuccessfulProvider = "last_successful_provider"

    /// Ports `KEY_LAST_SUCCESSFUL_MODEL`.
    private let keyLastSuccessfulModel = "last_successful_model"

    /// Ports `KEY_LAST_REFRESH_HF`. Like the Kotlin original it is declared but
    /// never read or written — `shouldRefreshHuggingFaceModels()` short-circuits
    /// to `false`. Kept so the persisted schema stays documented and complete.
    private let keyLastRefreshHF = "last_refresh_hf"

    /// Ports `KEY_LAST_REFRESH_OR`, stamped by `replaceProviderModels(provider:)`
    /// and read by `shouldRefreshOpenRouterFreeModels()`.
    private let keyLastRefreshOR = "last_refresh_or"

    /// Ports `KEY_PROVIDER_COOLDOWN_PREFIX`.
    private let keyProviderCooldownPrefix = "provider_cooldown_"

    /// Backing store for the rotator's half of `UserDefaults.standard`.
    private let defaults = UserDefaults.standard

    /// Guards every mutable store on this type. See the type-level thread-safety
    /// note; never held across anything that can throw.
    private let lock = NSLock()

    /// Ports `PROVIDER_COOLDOWN_MS = 24 * 60 * 60 * 1000L`.
    private let failureCooldownSeconds: TimeInterval = 24 * 60 * 60

    /// Ports the hourly refresh cadence inside `shouldRefreshOpenRouterFreeModels()`.
    private static let modelRefreshInterval: TimeInterval = 60 * 60

    /// Ports the `Log.w("ModelRotator", …)` tag. Reports go to `RemoteLogger`
    /// rather than logcat.
    private static let logTag = "ModelRotator"

    /// Ports the eight provider-wide refusal phrases in
    /// `isProviderWideRefusalText` / `providerCooldownFor`, lifted out so the two
    /// Kotlin functions cannot drift apart.
    private static let providerWideRefusalPhrases = [
        "none of its models can be used for the day",
        "no models can be used for the day",
        "no models available for the day",
        "models cannot be used today",
        "provider unavailable for today",
        "try again tomorrow",
        "come back tomorrow",
        "temporarily unavailable"
    ]

    // MARK: - Model registry

    /// Ports `fallbackModels` — nine providers, verbatim — with two entries
    /// corrected against ``AiModelDefaults`` after batch 4 verified the providers
    /// live. Those two ids are 404/402 on the wire, so shipping them would spend
    /// the whole cooldowns of two providers on guaranteed failures.
    ///
    /// * `cerebras`: Kotlin's `llama3.1-70b` / `llama3.1-8b` are retired —
    ///   replaced by `AiModelDefaults.cerebrasDefault` (`gpt-oss-120b`).
    /// * `cohere`: Kotlin's `command-r-plus` / `command-r` are the v1 names and
    ///   now 404 — replaced by `AiModelDefaults.cohereDefault`
    ///   (`command-a-03-2025`), the Cohere v2 line.
    ///
    /// The other seven providers are byte-identical to the Kotlin map and to
    /// `AiModelDefaults`. Only the Kotlin model ids carry no secrets; they are
    /// identifiers, not credentials.
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
        "cerebras": ["gpt-oss-120b"],
        "cohere": ["command-a-03-2025"],
        "replicate": ["meta/meta-llama-3-70b-instruct"],
        "gemini": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"]
    ]

    /// Ports `dynamicModels`: server-supplied model lists that shadow
    /// ``fallbackModels`` for a provider once refreshed.
    private var dynamicModels: [String: [String]] = [:]

    /// Ports the `fail_${provider}_${model}` counters, keyed by
    /// ``failureKey(provider:model:)``. Also the sort key that decides pool order.
    private var failureCounts: [String: Int] = [:]

    /// Ports the `provider_cooldown_*` expiry timestamps, keyed by
    /// ``cooldownKey(for:)``. Stored as `Date` rather than Kotlin's epoch-millis
    /// `Long`, since `UserDefaults` round-trips `Date` natively.
    private var providerCooldowns: [String: Date] = [:]

    /// Ports the `last_successful_provider` / `last_successful_model` pair read
    /// back by `getLastSuccessful()`.
    private var lastSuccessfulCandidate: ModelCandidate?

    /// Ports `init(context: Context)`: take the store, replay the persisted
    /// dynamic model list, then clear the `gemini` and `deepseek` cooldowns.
    ///
    /// Android needed a `Context` only to reach `getSharedPreferences`, so the
    /// parameter disappears and the work moves into the singleton's initialiser.
    /// The `gemini`/`deepseek` reset is load-bearing: those two providers are
    /// rate-limited per day rather than genuinely broken, and Android clears them
    /// on every cold start so a 24-hour penalty cannot outlive the process.
    private init() {
        loadPersistedState()
        clearProviderCooldownLocked("gemini")
        clearProviderCooldownLocked("deepseek")
    }

    // MARK: - Public API

    /// Ports `buildPool(provider: String): List<ModelCandidate>`.
    ///
    /// `provider == "auto"` runs the nine-provider priority list; anything else is
    /// scoped to one provider. Returns an empty array when that provider is
    /// cooling down, which callers read as "nothing available right now".
    ///
    /// The default argument is an iOS addition so
    /// `ModelRotator.shared.buildPool()` resolves the same `"auto"` the Kotlin
    /// callers pass explicitly.
    func buildPool(provider: String = "auto") -> [ModelCandidate] {
        let cleanProvider = normalize(provider)
        var pool: [ModelCandidate] = []
        let now = Date()

        lock.lock()
        defer { lock.unlock() }

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

            let sticky = lastSuccessfulCandidate
            if let sticky, !isProviderCoolingDown(sticky.provider, now: now) {
                pool.append(sticky)
            }

            var candidates: [ModelCandidate] = []
            for p in providers {
                if isProviderCoolingDown(p, now: now) { continue }
                for m in modelListLocked(for: p) {
                    let cand = ModelCandidate(provider: p, model: m)
                    if cand != sticky {
                        candidates.append(cand)
                    }
                }
            }

            pool.append(contentsOf: sortedByFailureCount(candidates))
        } else {
            if isProviderCoolingDown(cleanProvider, now: now) { return [] }

            var candidates = modelListLocked(for: cleanProvider).map {
                ModelCandidate(provider: cleanProvider, model: $0)
            }

            if let sticky = lastSuccessfulCandidate, sticky.provider == cleanProvider {
                if let index = candidates.firstIndex(of: sticky) {
                    candidates.remove(at: index)
                }
                pool.append(sticky)
            }

            pool.append(contentsOf: sortedByFailureCount(candidates))
        }

        return pool
    }

    /// Ports `markSuccess(candidate: ModelCandidate)`: remember the winner, lift
    /// any provider cooldown, and reset that model's failure counter to zero.
    ///
    /// The cooldown clear is what makes a recovered provider immediately
    /// eligible again on the next `buildPool`.
    func markSuccess(candidate: ModelCandidate) {
        lock.lock()
        defer { lock.unlock() }

        lastSuccessfulCandidate = candidate
        defaults.set(candidate.provider, forKey: scopedKey(keyLastSuccessfulProvider))
        defaults.set(candidate.model, forKey: scopedKey(keyLastSuccessfulModel))
        clearProviderCooldownLocked(candidate.provider)
        setFailureCountLocked(provider: candidate.provider, model: candidate.model, count: 0)
    }

    /// Ports the model-level failure path: bump `fail_${provider}_${model}` and,
    /// when asked, start the provider's 24-hour cooldown.
    ///
    /// Kotlin's `markFailure(provider, model, error)` instead takes the provider's
    /// error *text* and sniffs it for a provider-wide refusal. This signature takes
    /// a `Bool` and cannot sniff text, so it is preserved verbatim as the
    /// explicit-flag form; the text-driven form is
    /// ``markFailure(provider:model:error:)``, which supersedes it.
    func markFailure(candidate: ModelCandidate, cooldownProvider: Bool = false) {
        lock.lock()
        defer { lock.unlock() }

        let current = getFailureCountLocked(provider: candidate.provider, model: candidate.model)
        setFailureCountLocked(provider: candidate.provider, model: candidate.model, count: current + 1)

        if cooldownProvider {
            applyProviderFailureLocked(provider: candidate.provider, cooldownMs: failureCooldownSeconds)
        }
    }

    /// Ports `markFailure(provider: String, model: String, error: String)` —
    /// bump the model's failure counter and escalate to a provider-wide cooldown
    /// when the error text is one of the eight provider-wide refusal phrases
    /// (`isProviderWideRefusalText`).
    func markFailure(provider: String, model: String, error: String) {
        lock.lock()
        defer { lock.unlock() }

        let current = getFailureCountLocked(provider: provider, model: model)
        setFailureCountLocked(provider: provider, model: model, count: current + 1)

        if isProviderWideRefusalText(error) {
            applyProviderFailureLocked(provider: provider, cooldownMs: cooldownFor(error: error))
        }

        RemoteLogger.log(tag: Self.logTag, message: "Model failed: \(provider)/\(model): \(error)")
    }

    /// Ports `markProviderFailure(provider, error, cooldownMs = providerCooldownFor(error))`.
    ///
    /// `cooldownMs` is an optional override so a caller can express a duration
    /// other than the 24-hour default; passing `nil` reproduces Kotlin's default
    /// argument, which resolves through ``cooldownFor(error:)``.
    func markProviderFailure(provider: String, error: String, cooldownMs: TimeInterval? = nil) {
        lock.lock()
        defer { lock.unlock() }

        applyProviderFailureLocked(
            provider: provider,
            cooldownMs: cooldownMs ?? cooldownFor(error: error)
        )

        RemoteLogger.log(tag: Self.logTag, message: "Provider failed: \(provider): \(error)")
    }

    /// Ports `clearLastSuccessfulIfMatches(provider, model)`: drop the sticky
    /// winner only when it is the very candidate being reported, so one failing
    /// model cannot unpin an unrelated healthy one.
    func clearLastSuccessfulIfMatches(provider: String, model: String) {
        lock.lock()
        defer { lock.unlock() }

        guard let last = lastSuccessfulCandidate,
              last.provider == provider,
              last.model == model else { return }

        lastSuccessfulCandidate = nil
        defaults.removeObject(forKey: scopedKey(keyLastSuccessfulProvider))
        defaults.removeObject(forKey: scopedKey(keyLastSuccessfulModel))
    }

    /// Ports `replaceProviderModels(provider, models)`: install a server-supplied
    /// model list for a provider, shadowing ``fallbackModels``, persist it, and
    /// stamp the OpenRouter refresh clock when the provider is `openrouter`.
    ///
    /// The provider name is normalised before use. Kotlin keyed the map with the
    /// raw argument while `buildPool` looked it up lowercased, so a mixed-case
    /// caller silently persisted a list nothing would ever read; normalising
    /// removes that dead path.
    func replaceProviderModels(provider: String, models: [String]) {
        let key = modelsKey(for: normalize(provider))

        lock.lock()
        defer { lock.unlock() }

        dynamicModels[normalize(provider)] = models

        guard let data = try? JSONEncoder().encode(models) else {
            RemoteLogger.log(tag: Self.logTag, message: "Failed to encode models for \(provider)")
            return
        }
        defaults.set(data, forKey: key)

        if normalize(provider) == "openrouter" {
            defaults.set(Date(), forKey: scopedKey(keyLastRefreshOR))
        }
    }

    /// Ports `shouldRefreshHuggingFaceModels(): Boolean`, which is hard-coded to
    /// `false` in Kotlin and reads neither ``keyLastRefreshHF`` nor any network
    /// state. iOS keeps the same unconditional answer — Hugging Face is not among
    /// the nine rotated providers, and ``fallbackModels`` has no `huggingface`
    /// entry, so there is nothing to refresh into.
    func shouldRefreshHuggingFaceModels() -> Bool { false }

    /// Ports `shouldRefreshOpenRouterFreeModels(): Boolean`: `true` when an hour
    /// has passed since `replaceProviderModels(_:models:)` last stamped
    /// `openrouter`.
    ///
    /// Android answered `true` whenever `SharedPreferences` was still null, i.e.
    /// before `init(context)` had run. iOS has no such null state — an unstamped
    /// key reads back as no `Date`, which returns `true` here by the same
    /// arithmetic (the epoch is more than an hour ago).
    func shouldRefreshOpenRouterFreeModels() -> Bool {
        lock.lock()
        defer { lock.unlock() }

        guard let lastRefresh = defaults.object(forKey: scopedKey(keyLastRefreshOR)) as? Date else {
            return true
        }
        return Date().timeIntervalSince(lastRefresh) > Self.modelRefreshInterval
    }

    /// Ports `getLastSuccessful()`, surfaced for callers that want the sticky
    /// winner directly. Kotlin reached it only through `buildPool`, which hides it
    /// whenever its provider is cooling down — so this is the only way to answer
    /// "what did we last succeed with?" without forcing a pool rebuild.
    var lastSuccessful: ModelCandidate? {
        lock.lock()
        defer { lock.unlock() }
        return lastSuccessfulCandidate
    }

    /// Ports the `dynamicModels[p] ?: fallbackModels[p] ?: emptyList()` resolution
    /// used inside `buildPool`, for callers that only need the ids — Android's
    /// `ModelRotator.buildPool("openrouter").map { it.model }`.
    func models(forProvider provider: String) -> [String] {
        lock.lock()
        defer { lock.unlock() }
        return modelListLocked(for: normalize(provider))
    }

    // MARK: - Unlocked private cores
    //
    // Everything below assumes `lock` is already held. `NSLock` is non-recursive,
    // so none of these may take it, and none may call a public method above.

    /// Ports `isProviderCoolingDown(provider, nowMs)`.
    ///
    /// A lapsed cooldown is cleared here — Kotlin clears the preference key in the
    /// same branch — so the first caller to notice the expiry is the one that
    /// pays for the cleanup.
    private func isProviderCoolingDown(_ provider: String, now: Date) -> Bool {
        let key = cooldownKey(for: provider)
        guard let expiry = providerCooldowns[key] else { return false }

        guard expiry > now else {
            providerCooldowns[key] = nil
            defaults.removeObject(forKey: key)
            return false
        }
        return true
    }

    /// Ports `getFailureCount(provider, model)`, reached from `buildPool` through
    /// the candidate-shaped overload.
    private func getFailureCount(for candidate: ModelCandidate) -> Int {
        getFailureCountLocked(provider: candidate.provider, model: candidate.model)
    }

    /// Ports `setFailureCount(provider, model, count)` — the `apply()` half of
    /// Kotlin's `prefs.edit()` write.
    private func setFailureCountLocked(provider: String, model: String, count: Int) {
        let key = failureKey(provider: provider, model: model)
        failureCounts[key] = count
        defaults.set(count, forKey: key)
    }

    /// Ports `providerCooldownFor(error: String)`.
    ///
    /// Kotlin branches on the eight refusal phrases but **both branches return
    /// `PROVIDER_COOLDOWN_MS`**, so the conditional is dead and every provider
    /// failure costs a flat 24 hours. The port keeps that behaviour and drops the
    /// no-op branch; whether to cool down at all is decided by
    /// ``isProviderWideRefusalText(_:)``, not here.
    private func cooldownFor(error: String) -> TimeInterval {
        failureCooldownSeconds
    }

    /// Ports `isProviderWideRefusalText(text: String)`.
    private func isProviderWideRefusalText(_ text: String) -> Bool {
        let lowered = text.lowercased()
        return Self.providerWideRefusalPhrases.contains { lowered.contains($0) }
    }

    private func getFailureCountLocked(provider: String, model: String) -> Int {
        failureCounts[failureKey(provider: provider, model: model)] ?? 0
    }

    private func applyProviderFailureLocked(provider: String, cooldownMs: TimeInterval) {
        let key = cooldownKey(for: provider)
        let expiry = Date().addingTimeInterval(cooldownMs)
        providerCooldowns[key] = expiry
        defaults.set(expiry, forKey: key)
    }

    /// Ports `clearProviderCooldown(provider)`.
    private func clearProviderCooldownLocked(_ provider: String) {
        let key = cooldownKey(for: provider)
        providerCooldowns[key] = nil
        defaults.removeObject(forKey: key)
    }

    /// Ports `dynamicModels[p] ?: fallbackModels[p] ?: emptyList()`.
    private func modelListLocked(for provider: String) -> [String] {
        dynamicModels[provider] ?? fallbackModels[provider] ?? []
    }

    /// Ports `candidates.sortBy { getFailureCount(it.provider, it.model) }`.
    ///
    /// Kotlin's `sortedBy` is a stable sort, so ties keep the order the priority
    /// walk produced. `Array.sort(by:)` in Swift gives no stability guarantee, so
    /// the original index is the explicit tiebreak — otherwise two candidates
    /// with equal failure counts could swap places between calls and starve one.
    private func sortedByFailureCount(_ candidates: [ModelCandidate]) -> [ModelCandidate] {
        candidates.enumerated()
            .sorted { lhs, rhs in
                let left = getFailureCount(for: lhs.element)
                let right = getFailureCount(for: rhs.element)
                return left == right ? lhs.offset < rhs.offset : left < right
            }
            .map { $0.element }
    }

    // MARK: - Persistence helpers

    /// Ports `loadDynamicModels()` together with the read side of
    /// `getLastSuccessful()`, `getFailureCount()` and `isProviderCoolingDown()`.
    ///
    /// Android re-read `SharedPreferences` on every single access. The port
    /// hydrates the in-memory maps once here and writes through on every
    /// mutation; only this process writes these keys, so the two are equivalent
    /// and `buildPool` stays allocation-cheap.
    ///
    /// Deliberately unlocked — it runs from `init()`, before `shared` is
    /// published and therefore before any other thread can reach this instance.
    private func loadPersistedState() {
        dynamicModels = [:]
        failureCounts = [:]
        providerCooldowns = [:]
        lastSuccessfulCandidate = nil

        let modelPrefix = scopedKey("models.")
        let cooldownPrefix = scopedKey(keyProviderCooldownPrefix)
        let failurePrefix = scopedKey("fail_")

        for (key, value) in defaults.dictionaryRepresentation() {
            if key.hasPrefix(modelPrefix),
               let data = value as? Data,
               let models = try? JSONDecoder().decode([String].self, from: data),
               !models.isEmpty {
                dynamicModels[String(key.dropFirst(modelPrefix.count))] = models
            } else if key.hasPrefix(cooldownPrefix),
                      let expiry = value as? Date {
                providerCooldowns[key] = expiry
            } else if key.hasPrefix(failurePrefix),
                      let count = value as? Int {
                failureCounts[key] = count
            }
        }

        if let provider = defaults.string(forKey: scopedKey(keyLastSuccessfulProvider)),
           let model = defaults.string(forKey: scopedKey(keyLastSuccessfulModel)) {
            lastSuccessfulCandidate = ModelCandidate(provider: provider, model: model)
        }
    }

    private func scopedKey(_ suffix: String) -> String { "\(userDefaultsKey).\(suffix)" }

    /// Ports the `"models_$provider"` key. Kotlin wrote a `JSONArray` string; the
    /// port writes `[String]` as JSON `Data`, which `UserDefaults` round-trips
    /// without a lossy string hop.
    private func modelsKey(for provider: String) -> String { scopedKey("models.\(provider)") }

    /// Ports the `"fail_${provider}_${model}"` key verbatim.
    private func failureKey(provider: String, model: String) -> String {
        scopedKey("fail_\(provider)_\(model)")
    }

    /// Ports `providerCooldownKey(provider)` —
    /// `"$KEY_PROVIDER_COOLDOWN_PREFIX" + provider.trim().lowercase()`.
    ///
    /// The normalisation is load-bearing rather than cosmetic: it is what keeps
    /// `"OpenRouter"` and `"openrouter"` sharing one cooldown instead of writing
    /// two keys that only half the lookups ever read.
    private func cooldownKey(for provider: String) -> String {
        scopedKey(keyProviderCooldownPrefix + normalize(provider))
    }

    /// Ports `provider.trim().lowercase()` from `buildPool` and
    /// `providerCooldownKey`.
    private func normalize(_ provider: String) -> String {
        provider.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    }
}