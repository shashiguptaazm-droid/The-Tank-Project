import SwiftUI

/// Quiz/battle attempt history model.
///
/// 1:1 port of Android `HistoryModel.kt`.
public struct QuizHistoryItem: Identifiable, Codable, Hashable {
    public var id: String { historyId }
    public let historyId: String
    public let userId: Int
    public let mode: String // PRACTICE / CHALLENGE / FINAL_TEST / SINGLE_PLAYER
    public let title: String
    public let topic: String
    public let score: Int
    public let totalQuestions: Int
    public let correctAnswers: Int
    public let wrongAnswers: Int
    public let percentage: Float
    public let challengeId: String
    public let reviewJson: String
    public let timestamp: Double

    public init(
        historyId: String = UUID().uuidString,
        userId: Int = 0,
        mode: String = "PRACTICE",
        title: String = "",
        topic: String = "",
        score: Int = 0,
        totalQuestions: Int = 0,
        correctAnswers: Int = 0,
        wrongAnswers: Int = 0,
        percentage: Float = 0,
        challengeId: String = "",
        reviewJson: String = "",
        timestamp: Double = Date().timeIntervalSince1970
    ) {
        self.historyId = historyId
        self.userId = userId
        self.mode = mode
        self.title = title
        self.topic = topic
        self.score = score
        self.totalQuestions = totalQuestions
        self.correctAnswers = correctAnswers
        self.wrongAnswers = wrongAnswers
        self.percentage = percentage
        self.challengeId = challengeId
        self.reviewJson = reviewJson
        self.timestamp = timestamp
    }
}

/// Local and Firebase history tracker matching Android `HistoryManager.kt`.
public final class QuizHistoryManager: ObservableObject {

    public static let shared = QuizHistoryManager()
    private let cacheKey = "quiz_history_items_v1"

    @Published public private(set) var historyItems: [QuizHistoryItem] = []

    private init() {
        loadLocalHistory()
    }

    private func loadLocalHistory() {
        if let data = UserDefaults.standard.data(forKey: cacheKey),
           let items = try? JSONDecoder().decode([QuizHistoryItem].self, from: data) {
            self.historyItems = items.sorted { $0.timestamp > $1.timestamp }
        }
    }

    public func saveHistory(
        userId: Int,
        mode: String,
        title: String,
        topic: String,
        score: Int,
        totalQuestions: Int,
        correctAnswers: Int,
        wrongAnswers: Int,
        challengeId: String = "",
        reviewJson: String = ""
    ) {
        let attempted = correctAnswers + wrongAnswers
        let percentage: Float = attempted > 0 ? (Float(correctAnswers) * 100.0) / Float(attempted) : 0.0

        let item = QuizHistoryItem(
            userId: userId,
            mode: mode,
            title: title,
            topic: topic,
            score: score,
            totalQuestions: totalQuestions,
            correctAnswers: correctAnswers,
            wrongAnswers: wrongAnswers,
            percentage: percentage,
            challengeId: challengeId,
            reviewJson: reviewJson
        )

        historyItems.insert(item, at: 0)
        if let encoded = try? JSONEncoder().encode(historyItems) {
            UserDefaults.standard.set(encoded, forKey: cacheKey)
        }
    }
}
