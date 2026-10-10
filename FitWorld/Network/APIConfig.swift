import Foundation

enum APIConfig {
    /// Phase 1 target: the medicscholar VPS backend served through nginx TLS
    /// (per IMPLEMENTATION_PLAN_IOS.md §2). Overridable for local testing.
    static let baseURL = URL(string: "https://fitworld.medigyaan.com")!

    /// Public so tests and Debug menus can point elsewhere.
    static func configured(_ customScheme: String? = nil, host: String? = nil) -> URL {
        guard (customScheme != nil) || (host != nil) else { return baseURL }
        var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false)!
        if let customScheme { components.scheme = customScheme }
        if let host { components.host = host }
        return components.url!
    }
}
