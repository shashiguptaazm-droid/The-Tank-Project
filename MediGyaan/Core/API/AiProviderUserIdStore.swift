import Foundation

/// Ports Android's `AiProviderUserId` (`data/remote/AiProviderUserId.kt`) — the
/// process-global singleton that `EduLabsApplication.onCreate()` installs and the
/// AI gateway call sites read.
///
/// It reads the signed-in student's id **once per process**. The gateway uses it
/// for the training log and for per-user rate limiting, *not* for
/// authentication, so a failure to read it degrades to anonymous rather than
/// failing the request. The value is cached because it cannot change without a
/// re-login, and the AI path is hot enough that a preference read per call is
/// worth avoiding. ``refresh()`` clears the cache for the sign-in and sign-out
/// paths.
///
/// Despite the Kotlin name, the value is **not per-provider**: the Kotlin reads a
/// single app-wide `SharedPreferences` int, and so does this. The identifier is
/// neither random, a UUID, a hash nor provider-supplied — it is verbatim whatever
/// the login flow last wrote under the `user_id` preference.
///
/// **Storage mapping.** Android reads
/// `getSharedPreferences("MY_APP", MODE_PRIVATE).getInt("user_id", 0)`. iOS has
/// no per-file preferences, so the equivalent is `UserDefaults.standard` under
/// the same key's iOS spelling, `"mg.user_id"` — which is exactly what
/// `SessionStore` writes on sign-in and removes on sign-out.
///
/// **Thread safety.** Kotlin uses `@Volatile` plus `synchronized(this)`. This
/// port uses a single `NSLock` with the same double-checked shape, and declares
/// `@unchecked Sendable` because every piece of mutable state is reachable only
/// under that lock. Invariant: *every* read and write of ``defaults`` and
/// ``cached`` happens while `lock` is held.
final class AiProviderUserIdStore: @unchecked Sendable {

    /// Shared instance. Kotlin's `object AiProviderUserId` is a process-wide
    /// singleton, so the port keeps one shared instance of the same shape.
    static let shared = AiProviderUserIdStore()

    /// Ports the `@Volatile` fields and their `-1` sentinel. Nested rather than
    /// stored so no property initializer has to name `Self`.
    private enum Constants {
        /// Android's `private var cached: Int = -1`. `-1` means "not yet
        /// resolved"; any value `>= 0` is a resolved id served from the cache.
        static let unresolved = -1

        /// Android's fallback when the id cannot be read: pre-login, nothing
        /// installed yet, or an unreadable preference.
        static let anonymous = 0

        /// Android's `SharedPreferences("MY_APP")` key `"user_id"`, in its iOS
        /// spelling. Owned by `SessionStore`; duplicated here only because that
        /// type's key is `fileprivate`.
        static let userIdKey = "mg.user_id"
    }

    /// Guards ``defaults`` and ``cached``. See the type's thread-safety note.
    private let lock = NSLock()

    /// Ports Kotlin's `@Volatile private var context: Context?`. Android holds
    /// the `Application` context purely to reach `SharedPreferences`; iOS needs
    /// the `UserDefaults` instance itself. `nil` is the not-installed state that
    /// makes ``currentUserId`` degrade to anonymous.
    private var defaults: UserDefaults?

    /// Ports Kotlin's `@Volatile private var cached: Int = -1`.
    private var cached: Int = Constants.unresolved

    /// Kotlin's implicit private constructor on an `object`: the type is only
    /// reachable through ``shared``.
    private init() {}

    /// Ports `AiProviderUserId.install(appContext: Context)`.
    ///
    /// Safe to call repeatedly — like the Kotlin, only the **first** install is
    /// kept, so a later caller cannot swap the storage out from under a cached
    /// id. Android normalises its argument to `appContext.applicationContext`
    /// for exactly that reason; on iOS the argument already *is* the
    /// process-wide instance, so there is nothing further to normalise.
    ///
    /// This must complete before the first AI call. An uninstalled store answers
    /// ``currentUserId`` with ``Constants/anonymous`` and — exactly as the Kotlin
    /// does — does **not** memoise that answer, so the next call retries rather
    /// than pinning an anonymous id for the rest of the process.
    func install(defaults: UserDefaults = .standard) {
        lock.lock()
        defer { lock.unlock() }
        if self.defaults == nil {
            self.defaults = defaults
        }
    }

    /// Ports `AiProviderUserId.current(): Int`.
    ///
    /// The current user id, or ``Constants/anonymous`` when it is unknown
    /// (pre-login, not installed yet, or the preference is unreadable). The
    /// double-checked shape of the Kotlin is preserved exactly: the cached value
    /// is read before the lock is taken, re-checked inside it, and the
    /// `UserDefaults` read therefore happens at most once per process.
    ///
    /// The Kotlin swallows a `ClassCastException` from `getInt` and yields `0`;
    /// a non-numeric value under the key fails the same cast here and takes the
    /// same branch. Both stay silent, as on Android.
    var currentUserId: Int {
        lock.lock()

        let memoised = cached
        if memoised >= 0 {
            lock.unlock()
            return memoised
        }

        guard let store = defaults else {
            lock.unlock()
            return Constants.anonymous
        }

        let resolved: Int
        if let stored = store.object(forKey: Constants.userIdKey),
           let number = stored as? NSNumber {
            resolved = number.intValue
        } else {
            resolved = Constants.anonymous
        }

        cached = resolved
        lock.unlock()
        return resolved
    }

    /// Ports `AiProviderUserId.refresh()`.
    ///
    /// Call after login or logout so the next read picks up the new session —
    /// Kotlin's `synchronized(this) { cached = -1 }`. Deliberately does **not**
    /// clear the installed storage: that is the one-wins part of
    /// ``install(defaults:)``.
    func refresh() {
        lock.lock()
        cached = Constants.unresolved
        lock.unlock()
    }
}
