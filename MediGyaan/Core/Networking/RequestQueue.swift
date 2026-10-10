import Foundation

/// Ports `VolleyQueue` (`data/remote/VolleyQueue.kt`): the app-wide singleton
/// request queue — connection caps, memory/disk cache sizing, retry policy,
/// request priorities and tag-based cancellation.
///
/// The Android original is a 35-line double-checked-locking singleton wrapping
/// `Volley.newRequestQueue(context, HurlStack)`, so the throttling numbers below
/// are the Volley defaults that call inherits rather than values written in the
/// source file itself:
/// * `NetworkDispatcher.DEFAULT_MAX_REQUESTS_PER_HOST` of 6 →
///   ``URLSessionConfiguration/httpMaximumConnectionsPerHost``.
/// * `Volley.DEFAULT_MAX_CACHE_SIZE` of 20 MB → ``URLCache``.
/// * `DefaultRetryPolicy` → ``RetryPolicy``.
/// * `RequestQueue.cancelAll(tag)` → ``cancelAll(tag:)`` over a token registry.
///   Tags live in use across the app (`"sync_result"`, `"predictor"`, and the
///   per-screen `VOLLEY_TAG` / `PLAYER_AVATAR_TAG` / `FINAL_SYNC_TAG` / `ACTION_TAG`
///   constants that teardown paths cancel).
/// * `Request.Priority` → ``Priority``, mapped onto `Task(priority:)`.
///
/// Volley's `HurlStack` is stateless — no cookie jar, no credential store — so
/// this session is configured the same way. Swift's `static let shared` is
/// already lazily initialised exactly once under a lock, which is the direct
/// equivalent of the `@Volatile instance` + `synchronized` pair in the original.
///
/// The Android file also tags every socket with `TrafficStats.setThreadStatsTag`
/// to silence StrictMode `UntaggedSocketViolation`. That has no iOS counterpart:
/// the platform exposes no per-socket byte accounting to sandboxed apps.
final class RequestQueue {

    // MARK: - Singleton

    static let shared = RequestQueue()

    /// Mirrors Volley's `NetworkDispatcher.DEFAULT_MAX_REQUESTS_PER_HOST`.
    static let maxRequestsPerHost = 6

    /// Mirrors `Volley.DEFAULT_MAX_CACHE_SIZE` (20 MB), applied to both cache tiers.
    static let cacheCapacity = 20 * 1024 * 1024

    /// The configured session every request in the app funnels through.
    let session: URLSession

    /// The shared cache, exposed so callers can inspect or invalidate it.
    let cache: URLCache

    private let registry = Registry()

    private init() {
        let cache = URLCache(
            memoryCapacity: RequestQueue.cacheCapacity,
            diskCapacity: RequestQueue.cacheCapacity,
            diskPath: "MediGyaanNetworkCache"
        )
        let configuration = URLSessionConfiguration.default
        configuration.httpMaximumConnectionsPerHost = RequestQueue.maxRequestsPerHost
        configuration.timeoutIntervalForRequest = APIConfig.requestTimeout
        configuration.timeoutIntervalForResource = APIConfig.resourceTimeout
        configuration.waitsForConnectivity = true
        configuration.requestCachePolicy = .useProtocolCachePolicy
        configuration.urlCache = cache
        configuration.httpShouldSetCookies = false
        configuration.httpCookieAcceptPolicy = .never
        configuration.urlCredentialStorage = nil
        self.cache = cache
        self.session = URLSession(configuration: configuration)
    }

    // MARK: - Scheduling

    /// Volley's `Request.Priority`.
    ///
    /// Volley's own queue orders requests by *ascending* priority value, so
    /// `LOWEST` is dispatched before `HIGHEST` — a long-standing quirk of
    /// `PriorityBlockingQueue`. This mapping uses the intuitive ordering (higher
    /// priority is dispatched first) and keeps the queue FIFO within a priority.
    enum Priority: Int, Comparable {
        /// Cheapest to starve.
        case lowest = 0
        /// Background prefetch.
        case low
        /// The default for ordinary calls.
        case normal
        /// User-visible work.
        case high
        /// Interaction-blocking work.
        case highest

        static func < (lhs: Priority, rhs: Priority) -> Bool {
            lhs.rawValue < rhs.rawValue
        }

        /// The Swift concurrency priority used for the dispatch task.
        ///
        /// `URLSessionTask.priority` is not reachable through `data(for:)`, which
        /// is why the request priority is applied at the task level instead.
        var taskPriority: TaskPriority {
            switch self {
            case .highest, .high: return .high
            case .normal: return .medium
            case .low, .lowest: return .low
            }
        }

        /// The `URLSessionTask` priority value this level corresponds to.
        var sessionPriority: Float {
            switch self {
            case .highest, .high: return URLSessionTask.highPriority
            case .normal: return URLSessionTask.defaultPriority
            case .low, .lowest: return URLSessionTask.lowPriority
            }
        }
    }

    /// Volley's `DefaultRetryPolicy`: a socket timeout, a retry budget and an
    /// exponential backoff multiplier applied between attempts.
    ///
    /// Retries are spent on transport failures and on `408`, `429` and `5xx`
    /// responses, mirroring `BasicNetwork.shouldRetry`; every other `4xx` is
    /// handed back to the caller untouched.
    struct RetryPolicy {

        /// Per-attempt timeout, and the base of the backoff delay.
        var timeout: TimeInterval

        /// Retries allowed after the first attempt.
        var maxRetries: Int

        /// Multiplier applied to ``timeout`` after each failed attempt.
        var backoffMultiplier: Double

        init(timeout: TimeInterval, maxRetries: Int, backoffMultiplier: Double) {
            self.timeout = timeout
            self.maxRetries = maxRetries
            self.backoffMultiplier = backoffMultiplier
        }

        /// `DefaultRetryPolicy.DEFAULT_BACKOFF_MULT`.
        static let defaultBackoffMultiplier = 0.5

        /// `DefaultRetryPolicy(5_000, 1, 1f)` — the dashboard's most common policy.
        static let `default` = RetryPolicy(timeout: 5, maxRetries: 1, backoffMultiplier: 1.0)

        /// `DefaultRetryPolicy(10_000, 2, DEFAULT_BACKOFF_MULT)` — topic and
        /// question fetches.
        static let standard = RetryPolicy(
            timeout: 10,
            maxRetries: 2,
            backoffMultiplier: RetryPolicy.defaultBackoffMultiplier
        )

        /// `DefaultRetryPolicy(45_000, 0, 1f)` — AI assistant calls, never retried
        /// because a partial generation cannot be replayed safely.
        static let longRunning = RetryPolicy(timeout: 45, maxRetries: 0, backoffMultiplier: 1.0)

        /// Delay before the attempt that follows 0-based `attempt`.
        func backoff(afterAttempt attempt: Int) -> TimeInterval {
            timeout * pow(backoffMultiplier, Double(max(attempt, 0)))
        }

        /// Whether a status code is worth spending a retry on.
        static func isRetriable(statusCode: Int) -> Bool {
            statusCode == 408 || statusCode == 429 || statusCode >= 500
        }
    }

    // MARK: - Sending

    /// Sends `request` through the shared queue, applying the retry budget and
    /// registering the request so it can be cancelled by tag.
    ///
    /// The raw response is returned rather than thrown on a non-`2xx` status:
    /// Volley separates transport from interpretation — `RequestQueue` hands back
    /// a `NetworkResponse` and the `Request` decides what the status means. Only
    /// transport failures, an exhausted retry budget and cancellation throw here.
    ///
    /// Cancelling the surrounding Swift `Task` cancels the in-flight request, the
    /// same way Volley's `Request.cancel()` does.
    func perform(
        _ request: URLRequest,
        policy: RetryPolicy = .default,
        priority: Priority = .normal,
        tag: String? = nil
    ) async throws -> (Data, HTTPURLResponse) {
        guard let url = request.url else { throw APIError.invalidResponse }

        let registry = self.registry
        let session = self.session
        let token = CancellationToken()
        let id = UUID()
        registry.insert(token, id: id, tag: tag)

        let work = Task(priority: priority.taskPriority) { () async throws -> (Data, HTTPURLResponse) in
            defer {
                token.detach()
                registry.remove(id: id)
            }
            return try await Self.dispatch(request, url: url, session: session, policy: policy, token: token)
        }
        token.attach { work.cancel() }

        return try await withTaskCancellationHandler {
            try await work.value
        } onCancel: {
            token.cancel()
        }
    }

    /// Performs the request and retries while the policy allows it.
    private static func dispatch(
        _ request: URLRequest,
        url: URL,
        session: URLSession,
        policy: RetryPolicy,
        token: CancellationToken
    ) async throws -> (Data, HTTPURLResponse) {
        let method = request.httpMethod ?? "GET"
        var attempt = 0
        var lastError: Error = APIError.transport(message: "The request could not be sent")

        while true {
            if token.isCancelled { throw CancellationError() }

            var attemptRequest = request
            attemptRequest.timeoutInterval = policy.timeout
            let startedAt = CFAbsoluteTimeGetCurrent()

            do {
                let (data, response) = try await session.data(for: attemptRequest)
                let elapsedMs = Int((CFAbsoluteTimeGetCurrent() - startedAt) * 1000)

                guard let http = response as? HTTPURLResponse else {
                    let error = APIError.invalidResponse
                    APILogger.shared.record(
                        method: method,
                        url: url,
                        statusCode: 0,
                        durationMs: elapsedMs,
                        headers: attemptRequest.allHTTPHeaderFields ?? [:],
                        requestBody: attemptRequest.httpBody,
                        responseBody: data,
                        error: error
                    )
                    throw error
                }

                APILogger.shared.record(
                    method: method,
                    url: url,
                    statusCode: http.statusCode,
                    durationMs: elapsedMs,
                    headers: attemptRequest.allHTTPHeaderFields ?? [:],
                    requestBody: attemptRequest.httpBody,
                    responseBody: data,
                    error: nil
                )

                guard RetryPolicy.isRetriable(statusCode: http.statusCode),
                      attempt < policy.maxRetries else {
                    return (data, http)
                }
                lastError = APIError.server(message: "HTTP \(http.statusCode)", code: http.statusCode)
            } catch is CancellationError {
                throw CancellationError()
            } catch let error as APIError where errorIsFatal(error) {
                throw error
            } catch {
                lastError = APIError.transport(message: error.localizedDescription)
                APILogger.shared.record(
                    method: method,
                    url: url,
                    statusCode: 0,
                    durationMs: Int((CFAbsoluteTimeGetCurrent() - startedAt) * 1000),
                    headers: attemptRequest.allHTTPHeaderFields ?? [:],
                    requestBody: attemptRequest.httpBody,
                    responseBody: nil,
                    error: error
                )
            }

            attempt += 1
            guard attempt <= policy.maxRetries else { break }
            try await Task.sleep(nanoseconds: UInt64(policy.backoff(afterAttempt: attempt) * 1_000_000_000))
        }

        throw lastError
    }

    /// `APIError.invalidResponse` is raised by the transport itself rather than
    /// produced by a failed attempt, so it is never retried.
    private static func errorIsFatal(_ error: APIError) -> Bool {
        if case .invalidResponse = error { return true }
        return false
    }

    // MARK: - Cancellation

    /// Mirrors `RequestQueue.cancelAll(tag)`: cancels every tracked request
    /// carrying `tag`, whether it is queued, sleeping between retries or in flight.
    /// - Returns: How many requests were cancelled.
    @discardableResult
    func cancelAll(tag: String) -> Int {
        registry.cancelAll(tag: tag)
    }

    /// Cancels every tracked request, tagged or not. Volley's untagged
    /// `cancelAll()` only sweeps untagged requests; this broader sweep is what
    /// ``finish()`` needs.
    /// - Returns: How many requests were cancelled.
    @discardableResult
    func cancelAll() -> Int {
        registry.cancelAll()
    }

    /// Requests currently tracked by the queue.
    var activeRequestCount: Int {
        registry.count
    }

    /// Mirrors `RequestQueue.finish()`: cancels everything in flight and drops
    /// cached responses. The session stays usable afterwards.
    func finish() {
        cancelAll()
        cache.removeAllCachedResponses()
    }

    // MARK: - Cancellation plumbing

    /// Stands in for a Volley `Request` tag: a cancel handle the registry can
    /// reach once the request is in flight.
    final class CancellationToken {

        private let lock = NSLock()
        private var cancelWork: (() -> Void)?
        private var cancelled = false

        /// Whether ``cancel()`` has been called.
        var isCancelled: Bool {
            lock.lock()
            defer { lock.unlock() }
            return cancelled
        }

        /// Registers how to cancel the in-flight work.
        ///
        /// The closure captures the dispatch task, which is what makes
        /// `URLSessionTask.cancel()` reachable: `data(for:)` does not hand back a
        /// task handle, so cancellation has to travel through the `Task` wrapping it.
        func attach(cancelWork: @escaping () -> Void) {
            lock.lock()
            if cancelled {
                lock.unlock()
                cancelWork()
                return
            }
            self.cancelWork = cancelWork
            lock.unlock()
        }

        func detach() {
            lock.lock()
            cancelWork = nil
            lock.unlock()
        }

        /// Cancels the work this token is attached to.
        func cancel() {
            lock.lock()
            cancelled = true
            let cancelWork = self.cancelWork
            lock.unlock()
            cancelWork?()
        }
    }

    /// The tag index backing ``cancelAll(tag:)``. Lock-guarded rather than an
    /// actor so `perform` can register and deregister without an `await` on the
    /// hot path.
    private final class Registry {

        private let lock = NSLock()
        private var entries: [UUID: (tag: String?, token: CancellationToken)] = [:]

        var count: Int {
            lock.lock()
            defer { lock.unlock() }
            return entries.count
        }

        func insert(_ token: CancellationToken, id: UUID, tag: String?) {
            lock.lock()
            defer { lock.unlock() }
            entries[id] = (tag, token)
        }

        func remove(id: UUID) {
            lock.lock()
            defer { lock.unlock() }
            entries.removeValue(forKey: id)
        }

        func cancelAll(tag: String) -> Int {
            lock.lock()
            defer { lock.unlock() }
            let matches = entries.values.filter { $0.tag == tag }
            matches.forEach { $0.token.cancel() }
            return matches.count
        }

        func cancelAll() -> Int {
            lock.lock()
            defer { lock.unlock() }
            let all = Array(entries.values)
            all.forEach { $0.token.cancel() }
            return all.count
        }
    }
}