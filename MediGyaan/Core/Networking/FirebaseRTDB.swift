import Foundation

/// Centralized client for Firebase Realtime Database with automated Firebase Auth token acquisition.
///
/// Ensures all REST calls to `https://medigyaan-11cba-default-rtdb.firebaseio.com/` pass valid
/// `?auth=<idToken>` to satisfy Firebase RTDB security rules (`auth != null`), eliminating
/// "Permission denied" errors.
public final class FirebaseRTDB {

    public static let shared = FirebaseRTDB()

    private let dbBaseUrl = "https://medigyaan-11cba-default-rtdb.firebaseio.com"
    private let apiKey = "AIzaSyARowIWQb5dG_gxLj3O6TZ8c8o1QfR_Uks"

    private var cachedToken: String?
    private var tokenExpiry: Date?
    private let lock = NSLock()

    private init() {}

    /// Returns a valid Firebase Auth ID token, refreshing automatically via Firebase Auth REST API if expired.
    public func getAuthToken() async -> String? {
        lock.lock()
        if let token = cachedToken, let expiry = tokenExpiry, expiry > Date().addingTimeInterval(300) {
            lock.unlock()
            return token
        }
        lock.unlock()

        // Request anonymous token from Google Identity Toolkit
        guard let authUrl = URL(string: "https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=\(apiKey)") else {
            return nil
        }

        var request = URLRequest(url: authUrl)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body: [String: Any] = ["returnSecureToken": true]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)

        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let httpRes = response as? HTTPURLResponse, httpRes.statusCode == 200 else {
                RemoteLogger.log(tag: "FirebaseRTDB_Auth_Error", message: "Failed HTTP status: \((response as? HTTPURLResponse)?.statusCode ?? 0)")
                return nil
            }
            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let idToken = json["idToken"] as? String {
                let expiresInStr = json["expiresIn"] as? String ?? "3600"
                let expiresIn = Double(expiresInStr) ?? 3600

                lock.lock()
                self.cachedToken = idToken
                self.tokenExpiry = Date().addingTimeInterval(expiresIn)
                lock.unlock()

                RemoteLogger.log(tag: "FirebaseRTDB_Auth_Success", message: "Acquired Firebase RTDB auth token (expires in \(expiresIn)s)")
                return idToken
            }
        } catch {
            RemoteLogger.log(tag: "FirebaseRTDB_Auth_Exception", message: error.localizedDescription)
        }

        return nil
    }

    /// Builds a full RTDB URL appending `?auth=<idToken>`.
    public func authenticatedUrl(path: String) async -> URL? {
        let cleanPath = path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        var urlStr = "\(dbBaseUrl)/\(cleanPath).json"
        if let token = await getAuthToken() {
            urlStr += "?auth=\(token)"
        }
        return URL(string: urlStr)
    }

    /// Performs an authenticated GET request, parsing JSON dictionary or primitive.
    public func get(path: String) async throws -> Any? {
        guard let url = await authenticatedUrl(path: path) else {
            throw URLError(.badURL)
        }
        let (data, response) = try await URLSession.shared.data(from: url)
        if let httpRes = response as? HTTPURLResponse, httpRes.statusCode != 200 {
            let body = String(data: data, encoding: .utf8) ?? ""
            RemoteLogger.log(tag: "FirebaseRTDB_GET_Error", message: "Path: \(path), status: \(httpRes.statusCode), body: \(body)")
            throw URLError(.cannotParseResponse)
        }
        if data.isEmpty || String(data: data, encoding: .utf8) == "null" {
            return nil
        }
        return try? JSONSerialization.jsonObject(with: data)
    }

    /// Performs an authenticated PUT request, replacing the node.
    public func put(path: String, payload: Any) async throws {
        guard let url = await authenticatedUrl(path: path) else {
            throw URLError(.badURL)
        }
        var request = URLRequest(url: url)
        request.httpMethod = "PUT"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: payload)

        let (data, response) = try await URLSession.shared.data(for: request)
        if let httpRes = response as? HTTPURLResponse, httpRes.statusCode >= 400 {
            let body = String(data: data, encoding: .utf8) ?? ""
            RemoteLogger.log(tag: "FirebaseRTDB_PUT_Error", message: "Path: \(path), status: \(httpRes.statusCode), body: \(body)")
            throw URLError(.badServerResponse)
        }
    }

    /// Performs an authenticated PATCH request to update children at path.
    public func patch(path: String, payload: [String: Any]) async throws {
        guard let url = await authenticatedUrl(path: path) else {
            throw URLError(.badURL)
        }
        var request = URLRequest(url: url)
        request.httpMethod = "PATCH"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: payload)

        let (data, response) = try await URLSession.shared.data(for: request)
        if let httpRes = response as? HTTPURLResponse, httpRes.statusCode >= 400 {
            let body = String(data: data, encoding: .utf8) ?? ""
            RemoteLogger.log(tag: "FirebaseRTDB_PATCH_Error", message: "Path: \(path), status: \(httpRes.statusCode), body: \(body)")
            throw URLError(.badServerResponse)
        }
    }

    /// Performs an authenticated DELETE request to remove a node.
    public func delete(path: String) async throws {
        guard let url = await authenticatedUrl(path: path) else {
            throw URLError(.badURL)
        }
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        _ = try await URLSession.shared.data(for: request)
    }
}
