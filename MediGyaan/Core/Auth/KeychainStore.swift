import Foundation
import Security

/// Keychain wrapper used for credentials and tokens.
///
/// The Android app kept the user id, name, and e-mail in unencrypted
/// `SharedPreferences`; on iOS the sensitive half of that state lives in the
/// Keychain instead, while non-sensitive display data stays in `UserDefaults`.
final class KeychainStore {

    static let shared = KeychainStore()

    private let service: String

    init(service: String = "com.corp.medigyaan") {
        self.service = service
    }

    enum Key: String {
        case authToken
        case userId
        case email
        case password
        case fcmToken
    }

    /// Stores a string, replacing any existing value.
    @discardableResult
    func set(_ value: String, for key: Key) -> Bool {
        guard let data = value.data(using: .utf8) else { return false }
        return set(data, for: key)
    }

    @discardableResult
    func set(_ data: Data, for key: Key) -> Bool {
        // Delete first so the write is idempotent.
        _ = remove(key)

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key.rawValue,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlock,
        ]
        return SecItemAdd(query as CFDictionary, nil) == errSecSuccess
    }

    /// Reads a string value, or `nil` when absent.
    func get(_ key: Key) -> String? {
        guard let data = getData(key) else { return nil }
        return String(data: data, encoding: .utf8)
    }

    /// Reads raw data, or `nil` when absent.
    func getData(_ key: Key) -> Data? {
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

    /// Removes a single value.
    @discardableResult
    func remove(_ key: Key) -> Bool {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key.rawValue,
        ]
        let status = SecItemDelete(query as CFDictionary)
        return status == errSecSuccess || status == errSecItemNotFound
    }

    /// Clears every value owned by this service — used on sign-out.
    @discardableResult
    func removeAll() -> Bool {
        Key.allCases.allSatisfy { remove($0) }
    }
}

extension KeychainStore.Key: CaseIterable {}
