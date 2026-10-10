import Foundation
import KeychainAccess

/// Stores auth tokens in the iOS keychain — never in UserDefaults.
protocol TokenStoreProtocol: AnyObject {
    var accessToken: String? { get set }
    var refreshToken: String? { get set }
    var userEmail: String? { get set }
    func clearAll()
}

final class KeychainTokenStore: TokenStoreProtocol {
    private let keychain: Keychain

    init(service: String = "com.medigyaan.fitworld.tokens") {
        self.keychain = Keychain(service: service)
            .accessibility(.afterFirstUnlockThisDeviceOnly)
    }

    var accessToken: String? {
        get { try? keychain.get("access") }
        set { set("access", newValue) }
    }

    var refreshToken: String? {
        get { try? keychain.get("refresh") }
        set { set("refresh", newValue) }
    }

    var userEmail: String? {
        get { try? keychain.get("email") }
        set { set("email", newValue) }
    }

    func clearAll() {
        try? keychain.remove("access")
        try? keychain.remove("refresh")
        try? keychain.remove("email")
    }

    private func set(_ key: String, _ value: String?) {
        if let value {
            try? keychain.set(value, key: key)
        } else {
            try? keychain.remove(key)
        }
    }
}
