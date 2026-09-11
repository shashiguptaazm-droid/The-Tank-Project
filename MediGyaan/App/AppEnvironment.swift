import SwiftUI

/// Dependency-injection plumbing.
///
/// `SessionStore` is an `ObservableObject` injected with `.environmentObject`,
/// while the stateless API facade travels through the environment as a plain
/// value so previews and tests can swap in a stubbed backend.
private struct APIKey: EnvironmentKey {
    static let defaultValue: MediGyaanAPI = .live
}

extension EnvironmentValues {
    /// The backend client facade.
    var api: MediGyaanAPI {
        get { self[APIKey.self] }
        set { self[APIKey.self] = newValue }
    }
}
