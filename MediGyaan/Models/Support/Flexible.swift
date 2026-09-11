import Foundation

// MARK: - Tolerant JSON decoding
//
// MySQL hands nearly every column back to PHP as a string, so the API mixes
// `{"user_id":"42","correct":"1"}` with `{"user_id":42}`, omits keys entirely on
// some endpoints, and varies between `snake_case` and `camelCase`.
//
// Rather than fight `Codable`'s all-or-nothing synthesis, every model decodes
// through the non-throwing helpers below. They accept any of the representations
// the backend is known to produce and fall back to a sane default.

/// A `CodingKey` that can be constructed from an arbitrary string, so models can
/// decode with string literals instead of declaring a `CodingKeys` enum each time.
struct AnyCodingKey: CodingKey {
    var stringValue: String
    var intValue: Int?

    init?(stringValue: String) {
        self.stringValue = stringValue
        self.intValue = nil
    }

    init?(intValue: Int) {
        self.stringValue = String(intValue)
        self.intValue = intValue
    }

    init(_ name: String) {
        self.stringValue = name
        self.intValue = nil
    }
}

extension KeyedDecodingContainer where Key == AnyCodingKey {

    // MARK: Primitive readers

    /// Reads an `Int` from an int, double, numeric string, or bool.
    func flexInt(_ names: String...) -> Int {
        for name in names {
            guard let raw = try? decodeIfPresent(AnyDecodable.self, forKey: AnyCodingKey(name)),
                  let value = raw.value else { continue }
            if let int = value as? Int { return int }
            if let double = value as? Double { return Int(double) }
            if let string = value as? String { return Int(string) ?? Int(Double(string) ?? 0) ?? 0 }
            if let bool = value as? Bool { return bool ? 1 : 0 }
        }
        return 0
    }

    /// Reads a `Double` from a double, int, or numeric string.
    func flexDouble(_ names: String...) -> Double {
        for name in names {
            guard let raw = try? decodeIfPresent(AnyDecodable.self, forKey: AnyCodingKey(name)),
                  let value = raw.value else { continue }
            if let double = value as? Double { return double }
            if let int = value as? Int { return Double(int) }
            if let string = value as? String { return Double(string) ?? 0 }
            if let bool = value as? Bool { return bool ? 1 : 0 }
        }
        return 0
    }

    /// Reads a `String` from a string, number, or bool.
    func flexString(_ names: String...) -> String {
        for name in names {
            guard let raw = try? decodeIfPresent(AnyDecodable.self, forKey: AnyCodingKey(name)),
                  let value = raw.value else { continue }
            if let string = value as? String { return string }
            if let int = value as? Int { return String(int) }
            if let double = value as? Double { return String(double) }
            if let bool = value as? Bool { return bool ? "1" : "0" }
        }
        return ""
    }

    /// Reads a `Bool` from a bool, `0`/`1`, or `"true"`/`"false"`/`"yes"`.
    func flexBool(_ names: String...) -> Bool {
        for name in names {
            guard let raw = try? decodeIfPresent(AnyDecodable.self, forKey: AnyCodingKey(name)),
                  let value = raw.value else { continue }
            if let bool = value as? Bool { return bool }
            if let int = value as? Int { return int != 0 }
            if let string = value as? String {
                switch string.lowercased() {
                case "1", "true", "yes", "y": return true
                default: return false
                }
            }
        }
        return false
    }

    // MARK: Collection readers

    /// Reads an array, tolerating `null`, a missing key, or a single object.
    func flexArray<T: Decodable>(_ names: String...) -> [T] {
        for name in names {
            guard let raw = try? decodeIfPresent(AnyDecodable.self, forKey: AnyCodingKey(name)),
                  let value = raw.value else { continue }
            if let array = value as? [Any] {
                return array.compactMap { element in
                    guard let data = try? JSONSerialization.data(withJSONObject: element) else { return nil }
                    return try? JSONDecoder().decode(T.self, from: data)
                }
            }
            // A single object where an array was expected.
            if let data = try? JSONSerialization.data(withJSONObject: value),
               let single = try? JSONDecoder().decode(T.self, from: data) {
                return [single]
            }
        }
        return []
    }

    /// Reads an array of strings, tolerating numbers and nested objects.
    func flexStringArray(_ names: String...) -> [String] {
        for name in names {
            guard let raw = try? decodeIfPresent(AnyDecodable.self, forKey: AnyCodingKey(name)),
                  let value = raw.value else { continue }
            if let array = value as? [Any] {
                return array.compactMap { element in
                    if let string = element as? String { return string }
                    if let int = element as? Int { return String(int) }
                    if let dict = element as? [String: Any] {
                        return (dict["name"] as? String) ?? (dict["label"] as? String)
                    }
                    return nil
                }
            }
            if let string = value as? String, !string.isEmpty {
                // Some columns hold JSON-encoded arrays.
                if let data = string.data(using: .utf8),
                   let nested = try? JSONSerialization.jsonObject(with: data) as? [Any] {
                    return nested.compactMap { $0 as? String }
                }
                return [string]
            }
        }
        return []
    }

    /// Reads a nested decodable object, returning `nil` when absent/malformed.
    func flexObject<T: Decodable>(_ names: String...) -> T? {
        for name in names {
            guard let raw = try? decodeIfPresent(AnyDecodable.self, forKey: AnyCodingKey(name)),
                  let value = raw.value,
                  let data = try? JSONSerialization.data(withJSONObject: value) else { continue }
            if let object = try? JSONDecoder().decode(T.self, from: data) { return object }
        }
        return nil
    }

    /// Truthy when the key exists and carries a "success" style value.
    func flexSuccess() -> Bool {
        flexBool("success", "status", "ok")
    }
}

/// Type-erased `Decodable` used by the helpers above to inspect a raw value.
private struct AnyDecodable: Decodable {
    let value: Any?

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            value = nil
        } else if let bool = try? container.decode(Bool.self) {
            value = bool
        } else if let int = try? container.decode(Int.self) {
            value = int
        } else if let double = try? container.decode(Double.self) {
            value = double
        } else if let string = try? container.decode(String.self) {
            value = string
        } else if let array = try? container.decode([AnyDecodable].self) {
            value = array.map { $0.value }
        } else if let dict = try? container.decode([String: AnyDecodable].self) {
            value = dict.mapValues { $0.value }
        } else {
            value = nil
        }
    }
}

extension Decoder {
    /// Convenience accessor for the tolerant container.
    func flexibleContainer() throws -> KeyedDecodingContainer<AnyCodingKey> {
        try container(keyedBy: AnyCodingKey.self)
    }
}
