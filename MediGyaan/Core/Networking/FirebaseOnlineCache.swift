import Foundation

/// Ports `FirebaseOnlineCache`: the cross-restart response cache the Android
/// client keeps in Cloud Firestore under `users/{uid}/online_cache/{documentId}`.
///
/// **Why this is an idiom mapping and not a mechanical port.** iOS links only
/// LiveKit — there is no `FirebaseAuth`/`Firestore` SDK and none can be added
/// without editing `project.yml`. Every Firestore call is therefore
/// re-expressed against the PHP backend through `HTTPClient`, and the parts the
/// `Models/` layer depends on are reproduced **verbatim** so the cache keys stay
/// identical on both platforms.
///
/// Preserved verbatim from the Kotlin original:
/// - Collection `online_cache` under `users/{uid}`, one document per key.
/// - ``documentId(forKey:)`` — URL-safe Base64 of the UTF-8 key with the `=`
///   padding **kept** and no line wrapping (Android's
///   `Base64.URL_SAFE or Base64.NO_WRAP`), truncated to 900 characters.
/// - Document fields `key` (first 500 characters), `response`, `updatedAt`
///   (epoch milliseconds).
/// - Freshness: `now - updatedAt <= maxAgeMs`; the body is dropped only when it
///   is stale **and** `allowStale` is `false`. `allowStale` defaults to `true`
///   and every Android call site uses that default, so in practice a stale body
///   is still painted while the network refresh runs behind it.
/// - Write guards: signed-out user, blank body, or a body over 450 000
///   characters all skip the write.
/// - Failures are swallowed — a failed read yields `nil`, a failed write is
///   logged and dropped.
enum FirebaseOnlineCache {

    /// Mirrors `MAX_FIRESTORE_RESPONSE_CHARS`. Firestore caps a document near
    /// 1 MiB, so oversized bodies were never stored.
    private static let maxResponseChars = 450_000

    /// Byte cap on a single `key` field, mirroring `key.take(500)`.
    private static let maxKeyChars = 500

    /// `documentId` is truncated to 900 characters, mirroring `take(900)`.
    private static let maxDocumentIdChars = 900

    private enum DefaultsKey {
        /// Mirrors `SessionStore.DefaultsKey.userId`, which is `private` there
        /// and therefore unreachable from this file. Android reads
        /// `FirebaseAuth.getInstance().currentUser?.uid`; the signed-in
        /// `Int` standing in for the Firebase uid is the only identity this
        /// cache has on iOS.
        static let userId = "mg.user_id"

        /// Off by default. The cross-device endpoint does not exist on the
        /// backend yet, so pushing to it would 404 on every dashboard load.
        /// See the port notes in the batch report.
        static let remoteSync = "mg.onlineCacheRemoteSync"
    }

    /// The `maxAgeMs` values the Android call sites actually pass. Exposed so a
    /// `Features/` port reproduces the numbers rather than re-deriving them.
    enum TTL {
        /// Topic lists — `TopicSelectorList`, `TopicSelector.searchTopics`.
        static let topics: Int = 24 * 60 * 60 * 1000
        /// Dashboard stats — `DashboardActivity.fetchDatabaseData`.
        static let dashboard: Int = 5 * 60 * 1000
        /// Profile and connection lists —
        /// `fetchProfileData`, `TopicChallengeSelectionActivity`.
        static let profile: Int = 10 * 60 * 1000
    }

    // MARK: - Read

    /// Returns the cached body for `key`, or `nil` when nothing is cached or the
    /// cached body is stale and `allowStale` is `false`.
    ///
    /// Android delivers this through an `onResult: (String?) -> Unit` callback;
    /// the `async` return value is the idiomatic equivalent.
    static func getString(
        key: String,
        maxAgeMs: Int,
        allowStale: Bool = true
    ) async -> String? {
        cachedString(key: key, maxAgeMs: maxAgeMs, allowStale: allowStale)
    }

    /// Synchronous form of ``getString(key:maxAgeMs:allowStale:)``.
    static func cachedString(
        key: String,
        maxAgeMs: Int,
        allowStale: Bool = true
    ) -> String? {
        guard let uid = currentUserId() else { return nil }
        guard let entry = storage.entry(uid: uid, documentId: documentId(forKey: key)) else { return nil }
        let isFresh = nowMs() - entry.updatedAt <= maxAgeMs
        return (isFresh || allowStale) ? entry.response : nil
    }

    // MARK: - Write

    /// Write-through store, fired and forgotten exactly as the Kotlin original.
    ///
    /// Callers pair this with their own network request, so a failure here is
    /// logged and dropped — never surfaced.
    static func putString(key: String, response: String) {
        guard let uid = currentUserId() else { return }

        let body = response.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !body.isEmpty else { return }

        // Kotlin's String.length counts UTF-16 code units, not characters, and
        // the size guard is the observable decision here — so count the same way.
        let length = response.utf16.count
        guard length <= maxResponseChars else {
            RemoteLogger.log(
                tag: "FirebaseOnlineCache",
                message: "Skipping oversized cache write for \(key)",
                metadata: ["key": key, "chars": length]
            )
            return
        }

        let docId = documentId(forKey: key)
        let storedKey = String(key.prefix(maxKeyChars))

        storage.upsert(
            uid: uid,
            documentId: docId,
            entry: Entry(key: storedKey, response: response, updatedAt: nowMs())
        )

        guard remoteSyncEnabled else { return }
        Task {
            await push(uid: uid, documentId: docId, key: storedKey, response: response)
        }
    }

    // MARK: - Remote tier

    /// Pushes one entry to the backend script that replaces Firestore.
    ///
    /// Disabled unless `mg.onlineCacheRemoteSync` is set; see the batch report —
    /// the script is not deployed yet, so this is inert in production.
    private static func push(uid: Int, documentId: String, key: String, response: String) async {
        do {
            _ = try await HTTPClient.shared.postObject(
                form: [
                    "user_id": String(uid),
                    "doc_id": documentId,
                    "key": key,
                    "response": response,
                    "updated_at": String(nowMs())
                ],
                toAbsolute: backendURL
            )
        } catch {
            RemoteLogger.log(
                tag: "FirebaseOnlineCache",
                message: "Cache write failed for \(key)",
                metadata: ["key": key, "error": String(describing: error)]
            )
        }
    }

    /// Replaces the Firestore subcollection with a single script that takes the
    /// `user_id` + `doc_id` pair as its identity.
    ///
    /// Requested as a `POST` rather than a `GET` because the body carries the
    /// cached response verbatim and `HTTPClient.getObject(toAbsolute:)` is the
    /// only absolute-URL GET, and it deliberately omits the `X-App-Signature`
    /// header that every `Neurons/api/*.php` script requires.
    private static var backendURL: URL {
        APIConfig.baseURL.appendingPathComponent("api/online_cache.php")
    }

    private static var remoteSyncEnabled: Bool {
        UserDefaults.standard.bool(forKey: DefaultsKey.remoteSync)
    }

    // MARK: - Key derivation

    /// Verbatim port of `FirebaseOnlineCache.documentId`.
    ///
    /// `Data.base64EncodedString()` emits the standard alphabet with padding and
    /// no line breaks, so mapping `+` → `-` and `/` → `_` reproduces Android's
    /// `Base64.URL_SAFE or Base64.NO_WRAP`. Base64 output is pure ASCII, so
    /// `prefix(900)` counts the same characters as Kotlin's `take(900)`.
    static func documentId(forKey key: String) -> String {
        let encoded = Data(key.utf8)
            .base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
        return String(encoded.prefix(maxDocumentIdChars))
    }

    // MARK: - Identity and clock

    /// `nil` mirrors Android's `uid()` returning `null`, which made every read a
    /// miss and every write a no-op.
    private static func currentUserId() -> Int? {
        let uid = UserDefaults.standard.integer(forKey: DefaultsKey.userId)
        return uid > 0 ? uid : nil
    }

    /// Epoch milliseconds, matching `System.currentTimeMillis()`.
    private static func nowMs() -> Int {
        Int((Date().timeIntervalSince1970 * 1000).rounded())
    }

    // MARK: - Storage

    private static let storage = Storage()

    /// One cached body. Field names are the Firestore document field names.
    private struct Entry: Codable {
        let key: String
        let response: String
        let updatedAt: Int
    }

    /// Bodies live in one JSON file per user inside the caches directory, which
    /// mirrors Firestore's per-uid subcollection and gives iOS the eviction
    /// Android never performed — the system purges the caches directory under
    /// disk pressure.
    ///
    /// The whole file is kept in memory behind an `NSLock`: reads must be
    /// synchronous, and `SWIFT_STRICT_CONCURRENCY` is `minimal`, so there is no
    /// actor to suspend on.
    private final class Storage {
        private let lock = NSLock()
        private var loadedUID: Int = 0
        private var entries: [String: Entry] = [:]

        func entry(uid: Int, documentId: String) -> Entry? {
            lock.lock()
            defer { lock.unlock() }
            loadIfNeeded(uid: uid)
            return entries[documentId]
        }

        func upsert(uid: Int, documentId: String, entry: Entry) {
            lock.lock()
            defer { lock.unlock() }
            loadIfNeeded(uid: uid)
            entries[documentId] = entry
            persist(uid: uid)
        }

        private func loadIfNeeded(uid: Int) {
            guard loadedUID != uid else { return }
            loadedUID = uid

            guard let url = fileURL(uid: uid),
                  let data = try? Data(contentsOf: url),
                  let decoded = try? JSONDecoder().decode([String: Entry].self, from: data)
            else {
                entries = [:]
                return
            }
            entries = decoded
        }

        private func persist(uid: Int) {
            guard let url = fileURL(uid: uid) else { return }
            guard let data = try? JSONEncoder().encode(entries) else { return }
            do {
                try FileManager.default.createDirectory(
                    at: url.deletingLastPathComponent(),
                    withIntermediateDirectories: true
                )
                try data.write(to: url, options: .atomic)
            } catch {
                RemoteLogger.log(
                    tag: "FirebaseOnlineCache",
                    message: "Cache persist failed",
                    metadata: ["error": String(describing: error)]
                )
            }
        }

        private func fileURL(uid: Int) -> URL? {
            guard let caches = FileManager.default
                .urls(for: .cachesDirectory, in: .userDomainMask).first
            else { return nil }
            return caches.appendingPathComponent("MediGyaan/online_cache_\(uid).json")
        }
    }
}
