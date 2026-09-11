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

    // MARK: - Auth

    /// Live contract: `{"success":false,"error":"Invalid credentials","code":401}`.
    func testLoginRejectsBadCredentialsWithBackendMessage() async throws {
        try skipIfOffline()

        let auth = AuthAPI(client: client)
        try await assertBackendError("Invalid credentials") {
            _ = try await auth.login(email: "codebuff-probe@example.com", password: "wrong-password")
        }
    }

    /// The JSON request body must actually be read by PHP — if the client sent
    /// a form body instead, the script would answer differently.
    func testLoginAcceptsJsonBody() async throws {
        try skipIfOffline()

        let data = try await client.postObject(
            json: ["email": "codebuff-probe@example.com", "password": "x"],
            to: .login
        )

        XCTAssertEqual(data["success"] as? Bool, false)
        XCTAssertEqual(data["error"] as? String, "Invalid credentials")
        // Proves the JSON body was parsed, since PHP echoes its own code field.
        XCTAssertEqual(data["code"] as? Int, 401)
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

    /// Every configured endpoint should at least respond without a transport
    /// error, confirming the URL is routable and not a typo.
    func testAllEndpointsAreRoutable() async throws {
        try skipIfOffline()

        var unreachable: [String] = []

        for endpoint in APIConfig.Endpoint.allCases {
            do {
                _ = try await client.getObject(endpoint)
            } catch let error as APIError {
                switch error {
                case .transport, .httpStatus:
                    unreachable.append("\(endpoint.rawValue): \(error.localizedDescription)")
                case .server, .decoding, .invalidResponse, .unauthorized:
                    // A reachable script that rejected the request is fine here.
                    break
                }
            } catch {
                unreachable.append("\(endpoint.rawValue): \(error.localizedDescription)")
            }
        }

        XCTAssertTrue(
            unreachable.isEmpty,
            "These endpoints did not respond:\n\(unreachable.joined(separator: "\n"))"
        )
    }
}
