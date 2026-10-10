import Foundation
import CryptoKit
import Security

/// Ports `NetworkingModule` (`com.rankwarz.edulabsrtm.utils.NetworkingModule`,
/// Android): the process-wide dependency graph that lazily hands out the app's
/// HTTP clients.
///
/// The Kotlin original is a bare `object` holding two lazily-built fields — a
/// Volley `RequestQueue` and an `OkHttpClient` configured with a 60 s connect
/// timeout and 120 s read/write timeouts. It registers **no** Hilt/Dagger
/// bindings, selects **no** base URL (callers hard-code
/// `https://medigyaan.com/Neurons/…`), installs **no** interceptors and does
/// **no** debug/release switching. Everything else about Android transport
/// policy lives outside the file, in `AndroidManifest.xml` and
/// `res/xml/network_security_config.xml`; the HTTPS-only and certificate-pinning
/// rules from that config are mirrored here.
///
/// Both lazy fields collapse into a single ``HTTPClient`` on iOS: one
/// `URLSession` already multiplexes, pools and negotiates HTTP/2 the way
/// Volley's dispatcher threads and OkHttp's connection pool did. This type is
/// therefore the *composition root* — it resolves clients, selects base URLs and
/// builds transport configuration. Request/response behaviour stays in
/// ``HTTPClient`` and is never reimplemented here.
///
/// `static let` storage reproduces the Kotlin `object` singleton's lazy,
/// once-only initialisation, and additionally removes the double-initialisation
/// race present in the original's unsynchronised `if (field == null)` checks.
enum NetworkingModule {

    // MARK: - Singleton binding

    /// The process-wide client every backend call is routed through.
    ///
    /// This is the iOS counterpart of *both* Android fields at once: the shared
    /// `RequestQueue` that messenger polling was funnelled through, and the
    /// shared `OkHttpClient`. One pooled session serves both.
    static let shared: HTTPClient = HTTPClient.shared

    /// Builds an independent client aimed at a specific host.
    ///
    /// Mirrors the Kotlin pattern of a caller supplying its own base URL
    /// (`MessengerRepository` hard-coded `messenger_api.php`); used for the
    /// legacy host and for tests/staging.
    static func client(baseURL: URL = APIConfig.baseURL) -> HTTPClient {
        let client = HTTPClient()
        client.baseURL = baseURL
        return client
    }

    /// Builds an independent client that additionally validates the server's
    /// SPKI pin during the TLS handshake.
    ///
    /// The Android equivalent is declarative — `network_security_config.xml`
    /// applies to every socket the process opens, with no per-client opt-in. On
    /// iOS pinning is a `URLSessionDelegate` concern, so it has to be requested
    /// explicitly through this factory. ``shared`` is *not* pinned, because
    /// pinning the whole app's traffic would couple every feature to
    /// certificate rotation.
    static func pinnedClient(baseURL: URL = APIConfig.baseURL) -> HTTPClient {
        let configuration = makeConfiguration()
        let session = URLSession(
            configuration: configuration,
            delegate: PinnedSessionDelegate.shared,
            delegateQueue: nil
        )
        let client = HTTPClient(session: session)
        client.baseURL = baseURL
        return client
    }

    // MARK: - Transport configuration

    /// Timeouts and caching ported from the Kotlin `OkHttpClient.Builder()` chain.
    ///
    /// `NetworkingModule.getOkHttpClient()` set connect 60 s, read 120 s and
    /// write 120 s. `URLSession` has no separate connect or write budget, so the
    /// closest faithful mapping is:
    /// * *connect* — subsumed by `timeoutIntervalForRequest`, and further
    ///   relaxed by `waitsForConnectivity`, which parks the request instead of
    ///   failing it while the radio is down. Android's 60 s connect timeout was
    ///   in practice shorter than a cold radio wake on a bad network.
    /// * *read* / *write* — both map onto `timeoutIntervalForRequest`, which is
    ///   budgeted from the moment the request is handed to the loading system,
    ///   so a large upload cannot overrun it the way a per-socket write timeout
    ///   would have on Android.
    struct Timeouts {

        /// Android's `connectTimeout(60, SECONDS)`.
        static let connect: TimeInterval = 60

        /// Android's `readTimeout(120, SECONDS)`; also the upload budget.
        static let readWrite: TimeInterval = APIConfig.requestTimeout

        /// Hard ceiling on a single request's entire lifetime.
        static let resource: TimeInterval = APIConfig.resourceTimeout

        /// Cookies are disabled because OkHttp's default `CookieJar` is
        /// `NO_COOKIES` and the PHP backend is stateless (Bearer token plus the
        /// `X-App-Signature` header). Letting `URLSession` keep a cookie jar
        /// would introduce cross-request state Android never had.
        static func configuration() -> URLSessionConfiguration {
            let configuration = URLSessionConfiguration.default
            configuration.timeoutIntervalForRequest = readWrite
            configuration.timeoutIntervalForResource = resource
            configuration.waitsForConnectivity = true
            configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
            configuration.httpShouldSetCookies = false
            configuration.httpCookieAcceptPolicy = .never
            configuration.urlCache = nil
            return configuration
        }
    }

    /// Builds the session configuration described by ``Timeouts``.
    static func makeConfiguration() -> URLSessionConfiguration {
        Timeouts.configuration()
    }

    // MARK: - Certificate pinning

    /// SHA-256 SPKI pin set, transcribed from
    /// `app/src/main/res/xml/network_security_config.xml`.
    ///
    /// Android accepts the handshake if *any* pin matches, which is what allows
    /// zero-downtime rotation.
    enum Pin: String, CaseIterable {

        /// Let's Encrypt **YE1 intermediate**, valid 2025-09-03 → 2028-09-02.
        /// The live pin: every future leaf is issued by this same intermediate,
        /// so it survives Certbot's 90-day renewals, which a leaf pin would not.
        case letsEncryptIntermediateYE1 = "brzvtCELCIZUo4sD/qPX0ccRtPsd3DY6RfmxpOU9oB4="

        /// Current leaf SPKI, valid 2026-09-11 → 2026-12-10. A spare only —
        /// drop it once the intermediate pin is confirmed in the field.
        case currentLeafSpare = "OHcipZC1J8Dlcf/7DQztpfb0LJK0t9CzVPnDHeAd2UY="

        /// Whether `pin` is part of the accepted set.
        static func matches(_ pin: String) -> Bool {
            allCases.contains { $0.rawValue == pin }
        }
    }

    /// Hosts the pin set covers. Both are served by one SAN on a single
    /// certificate, so a single pin list covers them.
    static let pinnedHosts: Set<String> = ["medigyaan.com", "www.medigyaan.com"]

    /// Validates a server trust against the system chain *and* the SPKI pin set.
    ///
    /// - Returns: `true` when the host is not pinned, when the system chain
    ///   evaluates but no pin matches, or when the leaf's SPKI matches a pin.
    static func evaluate(_ trust: SecTrust, host: String) -> Bool {
        guard pinnedHosts.contains(host) else { return true }

        var trustError: CFError?
        guard SecTrustEvaluateWithError(trust, &trustError) else { return false }

        guard let chain = SecTrustCopyCertificateChain(trust) as? [SecCertificate],
              let leaf = chain.first,
              let publicKey = SecCertificateCopyKey(leaf),
              let spki = SecKeyCopyExternalRepresentation(publicKey, nil) as Data?
        else { return false }

        let digest = SHA256.hash(data: spki)
        return Pin.matches(Data(digest).base64EncodedString())
    }

    /// TLS challenge handler that applies ``evaluate`` to server-trust
    /// challenges for the pinned hosts and defers to the system everywhere else.
    final class PinnedSessionDelegate: NSObject, URLSessionDelegate {

        /// `URLSession` retains its delegate until invalidated, and the session
        /// handed to ``pinnedClient(baseURL:)`` lives for the process lifetime.
        static let shared = PinnedSessionDelegate()

        func urlSession(
            _ session: URLSession,
            didReceive challenge: URLAuthenticationChallenge,
            completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void
        ) {
            guard challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
                  let trust = challenge.protectionSpace.serverTrust
            else {
                completionHandler(.performDefaultHandling, nil)
                return
            }

            if NetworkingModule.evaluate(trust, host: challenge.protectionSpace.host) {
                completionHandler(.useCredential, URLCredential(trust: trust))
            } else {
                completionHandler(.cancelAuthenticationChallenge, nil)
            }
        }
    }
}