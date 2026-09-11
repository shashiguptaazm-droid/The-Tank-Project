import XCTest
@testable import MediGyaan

/// Networking-layer unit tests. No live backend required.
final class HTTPClientTests: XCTestCase {

    // MARK: - Form encoding

    /// `api/sync_user_cache.php` and friends read `$_POST`, so the body must be
    /// `application/x-www-form-urlencoded`, not JSON.
    func testFormEncodingProducesPostBody() {
        let data = HTTPClient.formEncode(["user_id": "42", "local_streak": "5"])
        let body = String(data: data, encoding: .utf8)

        XCTAssertEqual(body, "local_streak=5&user_id=42")
    }

    func testFormEncodingEscapesReservedCharacters() {
        let data = HTTPClient.formEncode(["email": "a+b@example.com"])
        let body = String(data: data, encoding: .utf8)

        // `+` and `@` must be percent-encoded so PHP decodes them literally.
        XCTAssertEqual(body, "email=a%2Bb%40example.com")
        XCTAssertFalse(body?.contains("+ ") ?? true)
    }

    func testFormEncodingHandlesEmptyValues() {
        let data = HTTPClient.formEncode(["q": ""])
        XCTAssertEqual(String(data: data, encoding: .utf8), "q=")
    }

    // MARK: - Endpoint construction

    func testEndpointURLsUseTheProductionHost() {
        XCTAssertEqual(
            APIConfig.Endpoint.login.url.absoluteString,
            "https://medigyaan.xyz/Neurons/api/login.php"
        )
        XCTAssertEqual(
            APIConfig.Endpoint.dashboard.url.absoluteString,
            "https://medigyaan.xyz/Neurons/dash_api.php"
        )
    }

    /// The leaderboard script was only reachable via a string template in the
    /// Android client, so it is asserted explicitly here.
    func testLeaderboardEndpointIsConfigured() {
        XCTAssertEqual(
            APIConfig.Endpoint.leaderboard.url.absoluteString,
            "https://medigyaan.xyz/Neurons/leaderboard1.php"
        )
    }

    func testEveryEndpointProducesAValidURL() {
        for endpoint in APIConfig.Endpoint.allCases {
            XCTAssertTrue(
                endpoint.url.absoluteString.hasPrefix("https://medigyaan.xyz/Neurons/"),
                "\(endpoint.rawValue) produced an unexpected URL"
            )
            XCTAssertTrue(endpoint.rawValue.hasSuffix(".php"), "\(endpoint.rawValue) is not a script")
        }
    }

    // MARK: - Error mapping

    func testAPIErrorSurfacesBackendMessage() {
        let error = APIError.server(message: "Invalid credentials", code: 401)

        XCTAssertEqual(error.errorDescription, "Invalid credentials")
        XCTAssertEqual(error.serverCode, 401)
    }

    func testAPIErrorFallsBackWhenMessageMissing() {
        let error = APIError.server(message: nil, code: nil)
        XCTAssertEqual(error.errorDescription, "The server rejected the request.")
    }

    func testHTTPStatusMessagesAreUserFacing() {
        XCTAssertEqual(
            APIError.httpStatus(503).errorDescription,
            "The server is temporarily unavailable. Please try again."
        )
        XCTAssertEqual(
            APIError.httpStatus(404).errorDescription,
            "This feature is not available on the server yet."
        )
    }

    // MARK: - Multipart

    func testMultipartBodyIsWellFormed() {
        var multipart = MultipartFormData(boundary: "TESTBOUNDARY")
        multipart.addField(name: "user_id", value: "7")
        multipart.addFile(
            name: "file",
            filename: "a.txt",
            mimeType: "text/plain",
            data: Data("hi".utf8)
        )

        let body = String(data: multipart.finalize(), encoding: .utf8) ?? ""

        XCTAssertEqual(multipart.contentType, "multipart/form-data; boundary=TESTBOUNDARY")
        XCTAssertTrue(body.contains("Content-Disposition: form-data; name=\"user_id\""))
        XCTAssertTrue(body.contains("filename=\"a.txt\""))
        XCTAssertTrue(body.hasSuffix("--TESTBOUNDARY--\r\n"))
    }

    // MARK: - LoadState

    func testLoadStateCapturesSuccess() async {
        var state: LoadState<Int> = .idle
        await state.load { 42 }

        XCTAssertEqual(state.value, 42)
        XCTAssertNil(state.errorMessage)
    }

    func testLoadStateMapsBackendErrorToMessage() async {
        var state: LoadState<Int> = .idle
        await state.load { throw APIError.server(message: "No attempts found", code: nil) }

        XCTAssertEqual(state.errorMessage, "No attempts found")
        XCTAssertNil(state.value)
    }
}
