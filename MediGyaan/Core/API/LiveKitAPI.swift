import Foundation

/// Fetches LiveKit access tokens from the SFU's host.
///
/// The app never holds the LiveKit API secret — that would be extractable from
/// an `.ipa` exactly like the Groq/Gemini keys the Android build shipped. The
/// secret stays on the VPS and this client only ever receives a short-lived,
/// room-scoped JWT.
///
/// `medigyaan.com` is a different host from `APIConfig.baseURL`, so this uses the
/// absolute-URL path on `HTTPClient`.
struct LiveKitAPI {

    private let client: HTTPClient

    init(client: HTTPClient = .shared) {
        self.client = client
    }

    /// Requests a token for `room` on behalf of `userId`.
    ///
    /// The display name is sent so the SFU can report it to other participants,
    /// which is how the remote caller's name appears in the call UI.
    func token(room: String, userId: Int, displayName: String) async throws -> CallToken {
        let body = try await client.postObject(
            form: [
                "room": room,
                "user_id": String(userId),
                "display_name": displayName,
            ],
            toAbsolute: APIConfig.LiveKit.tokenURL
        )

        // The endpoint follows the same `{success, message}` envelope as the rest
        // of the backend, so a failure is reported through `APIError.server`.
        if let success = body["success"] as? Bool, success == false {
            let message = (body["message"] as? String)
                ?? (body["error"] as? String)
                ?? "Could not start the call."
            throw APIError.server(message: message, code: body["code"] as? Int)
        }

        guard let token = body["token"] as? String, !token.isEmpty else {
            throw APIError.decoding(underlying: "LiveKit token endpoint returned no token")
        }

        return CallToken(
            token: token,
            url: (body["url"] as? String) ?? APIConfig.LiveKit.webSocketURL,
            room: (body["room"] as? String) ?? room,
            expiresAt: body["expires_at"] as? Int
        )
    }
}
