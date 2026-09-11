import Foundation
import Security

/// A credential key. Mirrors the small set of values the Android app wrote into
/// unencrypted `SharedPreferences`.
enum SecretKey: String, CaseIterable {
    case authToken
    case userId
    case email
    case password
    case fcmToken
}

/// Storage for sensitive values.
///
/// Abstracted behind a protocol because the Keychain is unavailable in some
/// legitimate configurations: an unsigned simulator build has no
/// `keychain-access-groups` entitlement, so every `SecItemAdd` fails with
/// `errSecMissingEntitlement` (-34018). Tests inject ``InMemorySecretStore`` so
/// they exercise session logic rather than Keychain availability, and the
/// production app keeps using the real Keychain.
protocol SecretStore: AnyObject {
    /// Stores a value, replacing any existing one. Returns `false` on failure.
    @discardableResult
    func set(_ value: String, for key: SecretKey) -> Bool

    /// Reads a value, or `nil` when absent or unreadable.
    func get(_ key: SecretKey) -> String?

    /// Removes a single value.
    @discardableResult
    func remove(_ key: SecretKey) -> Bool

    /// Removes every value this store owns.
    @discardableResult
    func removeAll() -> Bool
}

// MARK: - Keychain

/// Keychain-backed store used in the running app.
final class KeychainStore: SecretStore {

    static let shared = KeychainStore()

    private let service: String

    init(service: String = "com.corp.medigyaan") {
        self.service = service
    }

    @discardableResult
    func set(_ value: String, for key: SecretKey) -> Bool {
        guard let data = value.data(using: .utf8) else { return false }
        return set(data, for: key)
    }

    @discardableResult
    func set(_ data: Data, for key: SecretKey) -> Bool {
        // Delete first so the write is idempotent.
        remove(key)

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key.rawValue,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlock,
        ]
        let status = SecItemAdd(query as CFDictionary, nil)
        if status != errSecSuccess {
            // -34018 on an unsigned build is expected and not actionable here.
            print("[KeychainStore] set(\(key.rawValue)) failed with OSStatus \(status)")
        }
        return status == errSecSuccess
    }

    func get(_ key: SecretKey) -> String? {
        guard let data = getData(key) else { return nil }
        return String(data: data, encoding: .utf8)
    }

    func getData(_ key: SecretKey) -> Data? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key.rawValue,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        guard status == errSecSuccess else { return nil }
        return item as? Data
    }

    @discardableResult
    func remove(_ key: SecretKey) -> Bool {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key.rawValue,
        ]
        let status = SecItemDelete(query as CFDictionary)
        return status == errSecSuccess || status == errSecItemNotFound
    }

    @discardableResult
    func removeAll() -> Bool {
        SecretKey.allCases.allSatisfy { remove($0) }
    }
}

// MARK: - In-memory

/// Volatile store for tests and SwiftUI previews.
final class InMemorySecretStore: SecretStore {

    private var storage: [String: String] = [:]

    init(initial: [SecretKey: String] = [:]) {
        for (key, value) in initial {
            storage[key.rawValue] = value
        }
    }

    @discardableResult
    func set(_ value: String, for key: SecretKey) -> Bool {
        storage[key.rawValue] = value
        return true
    }

    func get(_ key: SecretKey) -> String? {
        storage[key.rawValue]
    }

    @discardableResult
    func remove(_ key: SecretKey) -> Bool {
        storage[key.rawValue] = nil
        return true
    }

    @discardableResult
    func removeAll() -> Bool {
        storage.removeAll()
        return true
    }
}
