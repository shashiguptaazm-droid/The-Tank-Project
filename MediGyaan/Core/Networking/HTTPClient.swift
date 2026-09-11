import Foundation

/// Async/await wrapper over `URLSession` that understands the MediGyaan
/// backend's response conventions.
///
/// The PHP scripts are inconsistent about input encoding:
/// * `api/login.php` and friends read a **JSON** request body (`php://input`).
/// * Older scripts such as `api/sync_user_cache.php` read **`$_POST`**, which
///   requires `application/x-www-form-urlencoded`.
///
/// Both encodings are supported via `post(json:to:)` and `post(form:to:)`.
final class HTTPClient {

    static let shared = HTTPClient()

    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    /// Base URL used for every request. Defaults to the production HTTPS host.
    var baseURL: URL = APIConfig.baseURL

    /// Bearer token applied to requests when present.
    var authToken: String?

    init(session: URLSession? = nil) {
        if let session {
            self.session = session
        } else {
            let configuration = URLSessionConfiguration.default
            configuration.timeoutIntervalForRequest = APIConfig.requestTimeout
            configuration.timeoutIntervalForResource = APIConfig.resourceTimeout
            configuration.waitsForConnectivity = true
            configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
            self.session = URLSession(configuration: configuration)
        }

        decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .useDefaultKeys
        encoder = JSONEncoder()
    }

    // MARK: - Public API

    /// Performs a `GET` request against `endpoint` and decodes the response.
    /// - Parameters:
    ///   - endpoint: Backend script to call.
    ///   - query: Query-string parameters.
    ///   - type: Expected decodable type.
    func get<T: Decodable>(
        _ endpoint: APIConfig.Endpoint,
        query: [String: String] = [:],
        as type: T.Type = T.self
    ) async throws -> T {
        let data = try await send(method: "GET", endpoint: endpoint, query: query, body: nil, contentType: nil)
        return try decode(data, as: type)
    }

    /// Performs a `GET` request and returns the decoded JSON object without a
    /// concrete type — useful for endpoints whose schema is not yet pinned down.
    func getObject(
        _ endpoint: APIConfig.Endpoint,
        query: [String: String] = [:]
    ) async throws -> [String: Any] {
        let data = try await send(method: "GET", endpoint: endpoint, query: query, body: nil, contentType: nil)
        return try decodeObject(data)
    }

    /// `POST`s a JSON body and decodes the response.
    func post<T: Decodable>(
        json: [String: Any],
        to endpoint: APIConfig.Endpoint,
        query: [String: String] = [:],
        as type: T.Type = T.self
    ) async throws -> T {
        let body = try JSONSerialization.data(withJSONObject: json, options: [])
        let data = try await send(
            method: "POST",
            endpoint: endpoint,
            query: query,
            body: body,
            contentType: "application/json"
        )
        return try decode(data, as: type)
    }

    /// `POST`s a JSON body and returns the raw JSON object.
    func postObject(
        json: [String: Any],
        to endpoint: APIConfig.Endpoint,
        query: [String: String] = [:]
    ) async throws -> [String: Any] {
        let body = try JSONSerialization.data(withJSONObject: json, options: [])
        let data = try await send(
            method: "POST",
            endpoint: endpoint,
            query: query,
            body: body,
            contentType: "application/json"
        )
        return try decodeObject(data)
    }

    /// `POST`s an `application/x-www-form-urlencoded` body, for the older
    /// scripts that read `$_POST`. Decodes the response.
    func post<T: Decodable>(
        form: [String: String],
        to endpoint: APIConfig.Endpoint,
        query: [String: String] = [:],
        as type: T.Type = T.self
    ) async throws -> T {
        let body = HTTPClient.formEncode(form)
        let data = try await send(
            method: "POST",
            endpoint: endpoint,
            query: query,
            body: body,
            contentType: "application/x-www-form-urlencoded; charset=utf-8"
        )
        return try decode(data, as: type)
    }

    /// `POST`s a form body and returns the raw JSON object.
    func postObject(
        form: [String: String],
        to endpoint: APIConfig.Endpoint,
        query: [String: String] = [:]
    ) async throws -> [String: Any] {
        let body = HTTPClient.formEncode(form)
        let data = try await send(
            method: "POST",
            endpoint: endpoint,
            query: query,
            body: body,
            contentType: "application/x-www-form-urlencoded; charset=utf-8"
        )
        return try decodeObject(data)
    }

    /// `POST`s a form body to an **absolute** URL, for services that do not live
    /// under `APIConfig.baseURL`.
    ///
    /// The LiveKit token endpoint is served by the VPS that runs the SFU
    /// (`medigyaan.com`), while the rest of the backend is on shared hosting
    /// (`medigyaan.xyz`), so it cannot be expressed as an `Endpoint`.
    func postObject(form: [String: String], toAbsolute url: URL) async throws -> [String: Any] {
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue(
            "application/x-www-form-urlencoded; charset=utf-8",
            forHTTPHeaderField: "Content-Type"
        )
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.httpBody = HTTPClient.formEncode(form)
        if let authToken, !authToken.isEmpty {
            request.setValue("Bearer \(authToken)", forHTTPHeaderField: "Authorization")
        }
        return try decodeObject(try await execute(request))
    }

    /// Uploads raw multipart form data.
    func upload<T: Decodable>(
        to url: URL,
        multipart: MultipartFormData,
        as type: T.Type = T.self
    ) async throws -> T {
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue(multipart.contentType, forHTTPHeaderField: "Content-Type")
        request.httpBody = multipart.finalize()
        let data = try await execute(request)
        return try decode(data, as: type)
    }

    // MARK: - Core transport

    private func send(
        method: String,
        endpoint: APIConfig.Endpoint,
        query: [String: String],
        body: Data?,
        contentType: String?
    ) async throws -> Data {
        let url = try makeURL(endpoint: endpoint, query: query)
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.httpBody = body
        if let contentType {
            request.setValue(contentType, forHTTPHeaderField: "Content-Type")
        }
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let authToken, !authToken.isEmpty {
            request.setValue("Bearer \(authToken)", forHTTPHeaderField: "Authorization")
        }
        return try await execute(request)
    }

    private func execute(_ request: URLRequest) async throws -> Data {
        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw APIError.transport(message: error.localizedDescription)
        }

        guard let http = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        // The backend signals logical failures inside a `success: false` body,
        // but it also uses 401/503 for some paths.
        if http.statusCode == 401 {
            if let envelope = try? decoder.decode(Envelope.self, from: data),
               let message = envelope.error ?? envelope.message {
                throw APIError.server(message: message, code: envelope.code)
            }
            throw APIError.unauthorized
        }

        guard (200 ..< 300).contains(http.statusCode) else {
            // Prefer the backend's own explanation when it sent JSON.
            if let envelope = try? decoder.decode(Envelope.self, from: data),
               envelope.success == false {
                throw APIError.server(message: envelope.error ?? envelope.message, code: envelope.code)
            }
            throw APIError.httpStatus(http.statusCode)
        }

        // A 200 that still contains `success: false` is a logical failure.
        if let envelope = try? decoder.decode(Envelope.self, from: data),
           envelope.success == false {
            throw APIError.server(message: envelope.error ?? envelope.message, code: envelope.code)
        }

        return data
    }

    private func makeURL(endpoint: APIConfig.Endpoint, query: [String: String]) throws -> URL {
        guard var components = URLComponents(
            url: baseURL.appendingPathComponent(endpoint.rawValue),
            resolvingAgainstBaseURL: false
        ) else {
            throw APIError.invalidResponse
        }
        if !query.isEmpty {
            components.queryItems = query
                .sorted { $0.key < $1.key }
                .map { URLQueryItem(name: $0.key, value: $0.value) }
        }
        guard let url = components.url else { throw APIError.invalidResponse }
        return url
    }

    // MARK: - Decoding helpers

    private func decode<T: Decodable>(_ data: Data, as type: T.Type) throws -> T {
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decoding(underlying: String(describing: error))
        }
    }

    private func decodeObject(_ data: Data) throws -> [String: Any] {
        guard let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw APIError.decoding(underlying: "Response was not a JSON object")
        }
        return object
    }

    static func formEncode(_ fields: [String: String]) -> Data {
        var allowed = CharacterSet.alphanumerics
        allowed.insert(charactersIn: "-._~")
        let encoded = fields
            .sorted { $0.key < $1.key }
            .map { key, value -> String in
                let k = key.addingPercentEncoding(withAllowedCharacters: allowed) ?? key
                let v = value.addingPercentEncoding(withAllowedCharacters: allowed) ?? value
                return "\(k)=\(v)"
            }
            .joined(separator: "&")
        return Data(encoded.utf8)
    }

    /// The `{ "success": ..., "error"/"message": ..., "code": ... }` envelope
    /// shared by every backend script.
    private struct Envelope: Decodable {
        let success: Bool?
        let error: String?
        let message: String?
        let code: Int?
    }
}
