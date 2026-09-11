import Foundation

/// Errors surfaced by the MediGyaan networking layer.
///
/// The PHP backend answers with a `{ "success": false, ... }` envelope rather
/// than HTTP status codes for most logical failures — `api/login.php` for
/// example returns `{"success":false,"error":"Invalid credentials","code":401}`.
/// `APIError.server` therefore carries the backend's own message.
enum APIError: LocalizedError, Equatable {

    /// The response was not an HTTP response, or the URL was unusable.
    case invalidResponse

    /// The backend replied with a `success: false` envelope.
    /// - Parameters:
    ///   - message: The backend's `error`/`message` field, if present.
    ///   - code: The backend's own `code` field, if present.
    case server(message: String?, code: Int?)

    /// A non-2xx HTTP status that is not explained by a JSON envelope.
    case httpStatus(Int)

    /// The response body could not be decoded into the expected shape.
    case decoding(underlying: String)

    /// Transport-level failure (offline, DNS, TLS, timeout).
    case transport(message: String)

    /// The caller is not authenticated and the endpoint requires a session.
    case unauthorized

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "The server sent an unexpected response."
        case let .server(message, _):
            return message ?? "The server rejected the request."
        case let .httpStatus(status):
            if status == 404 { return "This feature is not available on the server yet." }
            if status >= 500 { return "The server is temporarily unavailable. Please try again." }
            return "Request failed (HTTP \(status))."
        case .decoding:
            return "We couldn't read the server's response."
        case .transport:
            return "Network unavailable. Check your connection and try again."
        case .unauthorized:
            return "Your session has expired. Please sign in again."
        }
    }

    /// Backend-supplied code, when one was returned.
    var serverCode: Int? {
        if case let .server(_, code) = self { return code }
        return nil
    }
}
