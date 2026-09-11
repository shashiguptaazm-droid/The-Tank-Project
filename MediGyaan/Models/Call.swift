import Foundation

/// A room-scoped LiveKit access token, plus the server it is valid against.
///
/// Minted by `livekit_token.php` on the SFU's host. The API secret that signs
/// these never reaches the app.
struct CallToken: Decodable, Hashable {
    /// Signed JWT presented to the SFU.
    let token: String
    /// WebSocket endpoint, e.g. `wss://medigyaan.com/rtc`.
    let url: String
    /// Room the token grants access to.
    let room: String
    /// Unix timestamp the token stops being accepted.
    let expiresAt: Int?

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        token = container.flexString("token", "access_token", "jwt")
        url = container.flexString("url", "ws_url", "server_url")
        room = container.flexString("room", "room_name")
        let expiry = container.flexInt("expires_at", "exp")
        expiresAt = expiry == 0 ? nil : expiry
    }

    /// Memberwise init, for previews and tests.
    init(token: String, url: String, room: String, expiresAt: Int? = nil) {
        self.token = token
        self.url = url
        self.room = room
        self.expiresAt = expiresAt
    }

    /// Seconds until the token lapses, or `nil` when the server did not say.
    func remainingLifetime(now: Date = Date()) -> Int? {
        guard let expiresAt else { return nil }
        return expiresAt - Int(now.timeIntervalSince1970)
    }
}

/// Room naming.
///
/// The names are kept **byte-identical to the Android app** so that a room
/// created on one platform resolves to the same room on the other. Android's
/// `MessengerActivity.getRoomName` builds:
///
/// ```kotlin
/// if (u1 < u2) "edu_lab_rtm_${u1}_${u2}" else "edu_lab_rtm_${u2}_${u1}"
/// ```
///
/// and `VideoCallActivity` uses the ad-hoc `"EDULABS_" + timestamp`.
///
/// Note: matching names are necessary but not sufficient for cross-platform
/// calling — Android still dials `meet.jit.si`, so the two only interoperate
/// once Android is moved to this SFU as well.
enum CallRoom {

    /// Deterministic 1-on-1 room for two user ids, in the same order on both
    /// sides regardless of who dials.
    static func oneToOne(_ first: Int, _ second: Int) -> String {
        let low = min(first, second)
        let high = max(first, second)
        return "edu_lab_rtm_\(low)_\(high)"
    }

    /// Ad-hoc room, mirroring `VideoCallActivity`'s `EDULABS_<timestamp>`.
    static func adHoc(now: Date = Date()) -> String {
        "EDULABS_\(Int(now.timeIntervalSince1970 * 1000))"
    }
}

/// Whether a call carries video or is audio only.
enum CallKind: String, CaseIterable, Hashable {
    case video
    case audio

    var title: String {
        switch self {
        case .video: return "Video call"
        case .audio: return "Voice call"
        }
    }

    var systemImage: String {
        switch self {
        case .video: return "video.fill"
        case .audio: return "phone.fill"
        }
    }
}
