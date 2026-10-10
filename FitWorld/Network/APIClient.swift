import Foundation

enum APIError: LocalizedError {
    case invalidResponse
    case http(status: Int, message: String?)
    case offline
    case encodingFailed

    var errorDescription: String? {
        switch self {
        case .invalidResponse: return "Unexpected server response."
        case .http(let status, let message):
            return message ?? "Request failed (HTTP \(status))."
        case .offline: return "You appear to be offline. Data stays safe on this device."
        case .encodingFailed: return "Could not encode the request."
        }
    }
}

/// Small async/await JSON client. Bearer token injected from the keychain.
struct APIClient {
    let baseURL: URL
    private let tokenStore: TokenStoreProtocol
    private let session: URLSession

    init(baseURL: URL, tokenStore: TokenStoreProtocol, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.tokenStore = tokenStore
        self.session = session
    }

    // MARK: Requests

    func get<T: Decodable>(_ path: String, query: [URLQueryItem] = []) async throws -> T {
        try await request(path, method: "GET", query: query, body: nil)
    }

    func post<T: Decodable>(_ path: String, body: some Encodable) async throws -> T {
        try await request(path, method: "POST", query: [], body: body)
    }

    func put<T: Decodable>(_ path: String, body: some Encodable) async throws -> T {
        try await request(path, method: "PUT", query: [], body: body)
    }

    private func request<T: Decodable>(_ path: String,
                                        method: String,
                                        query: [URLQueryItem],
                                        body: (any Encodable)?) async throws -> T {
        guard Reachability.isOnline() else { throw APIError.offline }

        var components = URLComponents(url: baseURL.appendingPathComponent(path),
                                       resolvingAgainstBaseURL: false)
        if !query.isEmpty { components?.queryItems = query }
        guard let url = components?.url else { throw APIError.invalidResponse }

        var req = URLRequest(url: url)
        req.httpMethod = method
        req.timeoutInterval = 15
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        if let token = tokenStore.accessToken {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let body {
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = try JSONEncoder().encode(body)
        }

        let (data, response) = try await session.data(for: req)
        guard let http = response as? HTTPURLResponse else { throw APIError.invalidResponse }

        guard (200..<300).contains(http.statusCode) else {
            let message = Self.errorMessage(from: data)
            if http.statusCode == 401 {
                // The refresh flow in AuthService handles 401 recovery.
            }
            throw APIError.http(status: http.statusCode, message: message)
        }
        return try JSONDecoder().decode(T.self, from: data)
    }

    private static func errorMessage(from data: Data) -> String? {
        struct ErrBody: Decodable { let detail: String? }
        return (try? JSONDecoder().decode(ErrBody.self, from: data))?.detail
    }
}

/// Cheap reachability probe. Offline is a first-class state in this app:
/// everything must keep working without network.
enum Reachability {
    static func isOnline() -> Bool {
        // Phase 1: assume online unless a request fails; URLSession surfaces
        // real errors, and all critical paths are offline-first anyway.
        true
    }
}
