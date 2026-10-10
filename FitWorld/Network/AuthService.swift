import Foundation
import Observation

struct AuthUser: Codable, Hashable {
    let id: String
    let email: String
    let name: String?
}

struct AuthResponse: Codable {
    let token: String
    let refreshToken: String?
    let user: AuthUser
}

struct LoginRequest: Codable { let email: String; let password: String }
struct RegisterRequest: Codable { let email: String; let password: String; let name: String? }

/// Handles register/login/logout. In Phase 1 the VPS API is the source of
/// truth; a signed-out local-only mode is supported so onboarding and the
/// library work without an account (graceful degradation, offline-first).
@Observable
final class AuthService {
    private let apiClient: APIClient
    private let tokenStore: TokenStoreProtocol

    var currentUser: AuthUser?
    var lastError: String?

    var isSignedIn: Bool { tokenStore.accessToken != nil }

    init(apiClient: APIClient, tokenStore: TokenStoreProtocol) {
        self.apiClient = apiClient
        self.tokenStore = tokenStore
        // Restore remembered email for the sign-in screen.
        currentUser = tokenStore.userEmail.map {
            AuthUser(id: "restore", email: $0, name: nil)
        }
    }

    func register(email: String, password: String, name: String?) async -> Bool {
        do {
            lastError = nil
            let response: AuthResponse = try await apiClient.post(
                "api/v1/auth/register",
                body: RegisterRequest(email: email, password: password, name: name))
            store(response)
            return true
        } catch {
            lastError = error.localizedDescription
            return false
        }
    }

    func login(email: String, password: String) async -> Bool {
        do {
            lastError = nil
            let response: AuthResponse = try await apiClient.post("api/v1/auth/login",
                                                                  body: LoginRequest(email: email,
                                                                                     password: password))
            store(response)
            return true
        } catch {
            lastError = error.localizedDescription
            return false
        }
    }

    func signOut() {
        tokenStore.clearAll()
        currentUser = nil
    }

    private func store(_ response: AuthResponse) {
        tokenStore.accessToken = response.token
        tokenStore.refreshToken = response.refreshToken
        tokenStore.userEmail = response.user.email
        currentUser = response.user
    }
}
