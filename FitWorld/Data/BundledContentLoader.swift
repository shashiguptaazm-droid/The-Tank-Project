import Foundation

/// Reads seed content JSON from the app bundle. In Phase 1 the seed is the
/// source of truth; server sync layers on top later (M8). Bundled content is
/// always labeled with its reviewStatus, never presented as reviewed by default.
struct BundledContentLoader {
    let bundle: Bundle

    // MARK: Exercise decoding

    func loadExercises() throws -> [Exercise] {
        guard let data = try? data(forResource: "seed_exercises", ofType: "json") else {
            // Not an error for a fresh project: seed will be added next.
            return []
        }
        return try decodeArray(from: data, dateDecoding: .iso8601)
    }

    func loadWorkouts() throws -> [Workout] {
        guard let data = try? data(forResource: "seed_workouts", ofType: "json") else {
            return []
        }
        return try decodeArray(from: data, dateDecoding: .iso8601)
    }

    func loadPrograms() throws -> [Program] {
        guard let data = try? data(forResource: "seed_programs", ofType: "json") else {
            return []
        }
        return try decodeArray(from: data, dateDecoding: .iso8601)
    }

    // MARK: Helpers

    private func data(forResource name: String, ofType ext: String) throws -> Data {
        guard let url = bundle.url(forResource: name, withExtension: ext) else {
            throw CocoaError(.fileNoSuchFile,
                             userInfo: [NSFilePathErrorKey: "\(name).\(ext)"])
        }
        return try Data(contentsOf: url)
    }

    private func decodeArray<T: Decodable>(from data: Data,
                                           dateDecoding: JSONDecoder.DateDecodingStrategy) throws -> [T] {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = dateDecoding
        return try decoder.decode([T].self, from: data)
    }
}
