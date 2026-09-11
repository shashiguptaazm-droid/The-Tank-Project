import XCTest
@testable import MediGyaan

/// Integration tests that exercise the **live** PHP backend at
/// `medigyaan.xyz/Neurons/`.
///
/// These assert the negative paths, which are deterministic, require no
/// credentials, and prove the Swift client is genuinely wire-compatible with the
/// production scripts: the request reaches PHP, PHP's `{success:false,...}`
/// envelope is parsed, and its own message text surfaces to the UI.
///
/// If the host is unreachable the tests skip rather than fail, so a flaky
/// network never turns CI red.
final class LiveBackendTests: XCTestCase {

    private var client: HTTPClient!

    override func setUp() {
        super.setUp()
        client = HTTPClient()
    }

    /// Skips the test when the backend cannot be reached at all.
    private func skipIfOffline() throws {
        let semaphore = DispatchSemaphore(value: 0)
        var reachable = false
        var request = URLRequest(url: APIConfig.baseURL)
        request.timeoutInterval = 10
        request.httpMethod = "HEAD"

        URLSession.shared.dataTask(with: request) { _, response, _ in
            reachable = (response as? HTTPURLResponse) != nil
            semaphore.signal()
        }.resume()

        _ = semaphore.wait(timeout: .now() + 12)
        try XCTSkipUnless(reachable, "medigyaan.xyz is unreachable; skipping live backend test.")
    }

    /// Asserts the thrown error is a backend `success:false` carrying `expected`.
    private func assertBackendError(
        _ expected: String?,
        file: StaticString = #filePath,
        line: UInt = #line,
        _ operation: () async throws -> Void
    ) async throws {
        do {
            _ = try await operation()
            XCTFail("Expected the backend to reject this request", file: file, line: line)
        } catch let error as APIError {
            switch error {
            case let .server(message, _):
                if let expected {
                    XCTAssertEqual(message, expected, file: file, line: line)
                }
            case .transport:
                throw XCTSkip("Backend unreachable mid-test: \(error.localizedDescription)")
            default:
                XCTFail("Unexpected API error: \(error)", file: file, line: line)
            }
        }
    }

    /// Runs `operation` and returns the backend's own `(message, code)` when it
    /// rejects the request with a `success: false` envelope. Transport failures
    /// skip, since a flaky network should never turn CI red.
    private func serverError(
        from operation: () async throws -> Void,
        file: StaticString = #filePath,
        line: UInt = #line
    ) async throws -> (message: String?, code: Int?) {
        do {
            _ = try await operation()
            XCTFail("Expected the backend to reject this request", file: file, line: line)
            return (nil, nil)
        } catch let error as APIError {
            if case .transport = error {
                throw XCTSkip("Backend unreachable mid-test: \(error.localizedDescription)")
            }
            guard case let .server(message, code) = error else {
                XCTFail("Unexpected API error: \(error)", file: file, line: line)
                return (nil, nil)
            }
            return (message, code)
        }
    }

    // MARK: - Auth

    /// Live contract: `{"success":false,"error":"Invalid credentials","code":401}`.
    func testLoginRejectsBadCredentialsWithBackendMessage() async throws {
        try skipIfOffline()

        let auth = AuthAPI(client: client)
        try await assertBackendError("Invalid credentials") {
            _ = try await auth.login(email: "codebuff-probe@example.com", password: "wrong-password")
        }
    }

    /// `api/login.php` reads `php://input`, so a JSON body is parsed and a
    /// form body is **not**. The two encodings therefore get different answers,
    /// which is what makes this a genuine proof of the JSON path rather than a
    /// restatement of the rejection test above.
    ///
    /// Verified against production:
    /// - JSON `{"email":…,"password":"x"}` -> `Invalid credentials` / 401
    /// - form `email=…&password=x`         -> `Email and password required` / 400
    func testLoginAcceptsJsonBody() async throws {
        try skipIfOffline()

        let json = try await serverError {
            _ = try await client.postObject(
                json: ["email": "codebuff-probe@example.com", "password": "x"],
                to: .login
            )
        }
        XCTAssertEqual(json.message, "Invalid credentials")
        XCTAssertEqual(json.code, 401)

        // The identical credentials sent form-encoded are invisible to the
        // script, so it falls back to its "missing fields" branch.
        let form = try await serverError {
            _ = try await client.postObject(
                form: ["email": "codebuff-probe@example.com", "password": "x"],
                to: .login
            )
        }
        XCTAssertEqual(form.message, "Email and password required")
        XCTAssertEqual(form.code, 400)
        XCTAssertNotEqual(
            json.message,
            form.message,
            "A form body must not be readable by api/login.php"
        )
    }

    // MARK: - Dashboard

    /// Live contract: `{"success":false,"message":"Invalid User ID"}`.
    func testDashboardRejectsInvalidUser() async throws {
        try skipIfOffline()

        let study = StudyAPI(client: client)
        try await assertBackendError("Invalid User ID") {
            _ = try await study.dashboard(userId: 0)
        }
    }

    // MARK: - Quizzes

    /// Live contract: `{"success":false,"message":"Invalid quiz_id"}`.
    func testQuizQuestionsRejectsInvalidQuizId() async throws {
        try skipIfOffline()

        let study = StudyAPI(client: client)
        try await assertBackendError("Invalid quiz_id") {
            _ = try await study.questions(quizId: 0)
        }
    }

    /// Live contract: `{"success":false,"message":"Invalid user"}`.
    func testQuizListRejectsInvalidUser() async throws {
        try skipIfOffline()

        let study = StudyAPI(client: client)
        try await assertBackendError("Invalid user") {
            _ = try await study.quizzes(topicId: 0, userId: 0)
        }
    }

    // MARK: - Social

    /// `api/fetch_posts.php` guards itself: `{"success":false,"error":"Unauthorized Access"}`.
    func testFeedRejectsUnauthorizedAccess() async throws {
        try skipIfOffline()

        let social = SocialAPI(client: client)
        try await assertBackendError("Unauthorized Access") {
            _ = try await social.posts(userId: 0)
        }
    }

    // MARK: - Predictor

    /// Live contract: `{"success":false,"message":"No attempts found"}`.
    func testRankPredictorReportsNoAttempts() async throws {
        try skipIfOffline()

        let predictor = PredictorAPI(client: client)
        try await assertBackendError("No attempts found") {
            _ = try await predictor.predictRank(userId: 0, score: 500)
        }
    }

    /// Confirms a script that answers `200` with a `success:false` body is still
    /// treated as a failure rather than decoded as success.
    func testSuccessFalseOnHTTP200Throws() async throws {
        try skipIfOffline()

        do {
            _ = try await client.getObject(.predictRank, query: ["user_id": "0"])
            XCTFail("A success:false body should throw")
        } catch let error as APIError {
            if case .transport = error {
                throw XCTSkip("Backend unreachable mid-test.")
            }
            XCTAssertNotNil(error.errorDescription)
        }
    }

    // MARK: - Endpoint sweep

    /// `GET`s an endpoint, retrying once on a transport failure.
    ///
    /// Production is a single shared LiteSpeed host, and firing 50-odd requests
    /// back to back can have a connection reset. That surfaces as `.transport`
    /// with no bearing on the endpoint's health, so one retry separates a genuine
    /// outage from a dropped connection.
    private func probe(_ endpoint: APIConfig.Endpoint) async throws {
        do {
            _ = try await client.getObject(endpoint)
        } catch let error as APIError {
            guard Self.isWorthRetrying(error) else { throw error }
            try? await Task.sleep(for: .milliseconds(1_500))
            _ = try await client.getObject(endpoint)
        }
    }

    /// Whether a probe failure looks transient rather than real.
    ///
    /// A shared production host answers a spurious 404 now and then when 50-plus
    /// requests arrive back to back from one fresh address. A genuine typo in a
    /// path 404s on both attempts, so retrying once keeps every bit of detection
    /// power while stopping the host's hiccups from reddening the build.
    private static func isWorthRetrying(_ error: APIError) -> Bool {
        switch error {
        case .transport:
            return true
        case let .httpStatus(status):
            return status == 404
        case .server, .decoding, .invalidResponse, .unauthorized:
            return false
        }
    }

    /// Every configured endpoint must map to a real script: the host has to
    /// answer, and the path must not 404 (which is what a typo looks like).
    ///
    /// A bare `GET` is not a valid call for most of these scripts, and production
    /// legitimately answers 400/401/403 while validating input, so only a
    /// transport failure or a 404 is treated as unroutable. Other non-2xx
    /// statuses are collected and printed, keeping server-side degradation
    /// visible without making the build fail for reasons the app cannot control.
    func testAllEndpointsAreRoutable() async throws {
        try skipIfOffline()

        var unreachable: [String] = []
        var degraded: [String] = []

        for endpoint in APIConfig.Endpoint.allCases {
            // Pace the sweep: this is a shared production host, not a test rig.
            try? await Task.sleep(for: .milliseconds(120))

            do {
                try await probe(endpoint)
            } catch let error as APIError {
                switch error {
                case .transport:
                    unreachable.append("\(endpoint.rawValue): \(error.localizedDescription)")
                case let .httpStatus(status):
                    if status == 404 {
                        unreachable.append("\(endpoint.rawValue): HTTP 404 (wrong path?)")
                    } else {
                        degraded.append("\(endpoint.rawValue): HTTP \(status)")
                    }
                case .server, .decoding, .invalidResponse, .unauthorized:
                    // A reachable script that rejected the request is the norm.
                    break
                }
            } catch {
                unreachable.append("\(endpoint.rawValue): \(error.localizedDescription)")
            }
        }

        if !degraded.isEmpty {
            print("NOTE: \(degraded.count) endpoint(s) answered with a non-2xx status:")
            for entry in degraded.sorted() { print("   \(entry)") }
        }
        if !unreachable.isEmpty {
            print("FAIL: \(unreachable.count) endpoint(s) did not respond:")
            for entry in unreachable.sorted() { print("   \(entry)") }
        }

        // One annotation per endpoint so CI diagnostics are never truncated.
        for entry in unreachable.sorted() {
            XCTFail("Unroutable endpoint — \(entry)")
        }
    }
}
