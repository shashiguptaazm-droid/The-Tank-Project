import Foundation

/// Standard three-state async loading model, replacing the ad-hoc
/// progress-bar/visibility juggling in the Android activities.
enum LoadState<Value> {
    case idle
    case loading
    case loaded(Value)
    case failed(String)

    var value: Value? {
        if case let .loaded(value) = self { return value }
        return nil
    }

    var isLoading: Bool {
        if case .loading = self { return true }
        return false
    }

    var errorMessage: String? {
        if case let .failed(message) = self { return message }
        return nil
    }

    /// Runs `operation`, mapping thrown `APIError`s to user-facing text.
    mutating func load(_ operation: () async throws -> Value) async {
        self = .loading
        do {
            self = .loaded(try await operation())
        } catch {
            self = .failed(Self.message(for: error))
        }
    }

    static func message(for error: Error) -> String {
        if let apiError = error as? APIError {
            return apiError.errorDescription ?? "Something went wrong."
        }
        if (error as NSError).domain == NSURLErrorDomain {
            return "Network unavailable. Check your connection and try again."
        }
        return error.localizedDescription
    }
}

extension LoadState: Equatable where Value: Equatable {}
