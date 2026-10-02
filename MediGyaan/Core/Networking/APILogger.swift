import Foundation
import Combine

/// Real-time in-memory and persistent inspector for all outgoing and incoming API calls.
/// Accessible directly inside the app under Settings -> Network Inspector, and can also be exported or fetched.
final class APILogger: ObservableObject {

    static let shared = APILogger()

    struct Entry: Identifiable, Codable {
        let id: String
        let timestamp: Date
        let method: String
        let url: String
        let statusCode: Int
        let durationMs: Int
        let requestHeaders: [String: String]
        let requestBody: String?
        let responseBody: String?
        let error: String?

        var isSuccess: Bool { (200 ..< 300).contains(statusCode) && error == nil }
        var formattedTime: String {
            let formatter = DateFormatter()
            formatter.dateFormat = "HH:mm:ss.SSS"
            return formatter.string(from: timestamp)
        }
    }

    @Published private(set) var entries: [Entry] = []
    private let queue = DispatchQueue(label: "com.corp.medigyaan.apilogger", qos: .utility)
    private let maxEntries = 200

    private init() {
        loadPersisted()
    }

    func record(
        method: String,
        url: URL,
        statusCode: Int,
        durationMs: Int,
        headers: [String: String],
        requestBody: Data?,
        responseBody: Data?,
        error: Error?
    ) {
        let reqString = requestBody.flatMap { String(data: $0, encoding: .utf8) }
        let resString = responseBody.flatMap { String(data: $0, encoding: .utf8) }

        let entry = Entry(
            id: UUID().uuidString,
            timestamp: Date(),
            method: method,
            url: url.absoluteString,
            statusCode: statusCode,
            durationMs: durationMs,
            requestHeaders: headers,
            requestBody: reqString?.isEmpty == false ? reqString : nil,
            responseBody: resString?.isEmpty == false ? resString : nil,
            error: error?.localizedDescription
        )

        DispatchQueue.main.async {
            self.entries.insert(entry, at: 0)
            if self.entries.count > self.maxEntries {
                self.entries = Array(self.entries.prefix(self.maxEntries))
            }
        }

        queue.async {
            self.persist()
        }
    }

    func clear() {
        DispatchQueue.main.async {
            self.entries.removeAll()
        }
        queue.async {
            self.persist()
        }
    }

    func exportJSON() -> String {
        guard let data = try? JSONEncoder().encode(entries),
              let string = String(data: data, encoding: .utf8) else {
            return "[]"
        }
        return string
    }

    private var storageURL: URL {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        return docs.appendingPathComponent("api_logs.json")
    }

    private func persist() {
        guard let data = try? JSONEncoder().encode(entries) else { return }
        try? data.write(to: storageURL, options: .atomic)
    }

    private func loadPersisted() {
        guard let data = try? Data(contentsOf: storageURL),
              let loaded = try? JSONDecoder().decode([Entry].self, from: data) else { return }
        self.entries = loaded
    }
}
