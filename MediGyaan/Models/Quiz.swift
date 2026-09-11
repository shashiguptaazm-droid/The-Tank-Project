import Foundation

/// A quiz/test container returned by `quiz_apiv2.php` and `shared_api.php`.
struct Quiz: Decodable, Identifiable, Hashable {
    let id: Int
    let title: String
    let topic: String
    let subject: String
    let questionCount: Int
    let durationSeconds: Int
    let difficulty: String
    let ownerId: Int
    let createdAt: String

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        id = container.flexInt("quiz_id", "id")
        title = container.flexString("title", "quiz_title", "name")
        topic = container.flexString("topic", "topic_name")
        subject = container.flexString("subject", "subject_name")
        questionCount = container.flexInt("question_count", "total_questions", "questions", "count")
        durationSeconds = container.flexInt("duration", "duration_seconds", "time_limit")
        difficulty = container.flexString("difficulty", "level")
        ownerId = container.flexInt("user_id", "owner_id", "created_by")
        createdAt = container.flexString("created_at", "date")
    }

    init(
        id: Int,
        title: String,
        topic: String = "",
        subject: String = "",
        questionCount: Int = 0,
        durationSeconds: Int = 0,
        difficulty: String = "",
        ownerId: Int = 0,
        createdAt: String = ""
    ) {
        self.id = id
        self.title = title
        self.topic = topic
        self.subject = subject
        self.questionCount = questionCount
        self.durationSeconds = durationSeconds
        self.difficulty = difficulty
        self.ownerId = ownerId
        self.createdAt = createdAt
    }
}

/// A single MCQ. Options arrive either as a `options` array or as the four
/// `option1..option4` columns, so both shapes are accepted.
struct Question: Decodable, Identifiable, Hashable {
    let id: Int
    let text: String
    let options: [String]
    let correctIndex: Int
    let explanation: String
    let imageURL: URL?
    let topic: String
    let subject: String
    let marks: Int
    let negativeMarks: Double

    var correctOption: String? {
        guard options.indices.contains(correctIndex) else { return nil }
        return options[correctIndex]
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        id = container.flexInt("question_id", "id")
        text = container.flexString("question", "question_text", "text", "questionName")
        explanation = container.flexString("explanation", "solution", "reason")
        topic = container.flexString("topic", "topic_name")
        subject = container.flexString("subject", "subject_name")
        marks = container.flexInt("marks", "mark", "positive_marks")
        negativeMarks = container.flexDouble("negative_marks", "negative")

        let image = container.flexString("image", "image_url", "question_image")
        imageURL = image.isEmpty ? nil : URL(string: image)

        // Preferred shape: an explicit options array.
        var parsed = container.flexStringArray("options", "option_list", "choices")
        if parsed.isEmpty {
            // Fallback: separate option1..option4 columns.
            parsed = ["option1", "option2", "option3", "option4"]
                .map { container.flexString($0) }
                .filter { !$0.isEmpty }
        }
        options = parsed

        // `correct_option` may be a 1-based answer number, a 0-based index, or
        // the answer text itself, depending on which script produced the row.
        // A value inside `1...options.count` is treated as 1-based unless the
        // response also carries an explicit `correct_index`.
        let rawCorrect = container.flexString("correct_option", "correct", "answer", "correct_answer")
        if let numeric = Int(rawCorrect) {
            let hasExplicitIndex = !container.flexString("correct_index", "answer_index").isEmpty
            if numeric >= 1, numeric <= options.count, !hasExplicitIndex {
                correctIndex = numeric - 1
            } else {
                correctIndex = numeric
            }
        } else if let match = options.firstIndex(where: {
            $0.compare(rawCorrect, options: [.caseInsensitive, .diacriticInsensitive]) == .orderedSame
        }) {
            correctIndex = match
        } else {
            correctIndex = container.flexInt("correct_index", "answer_index")
        }
    }

    init(
        id: Int,
        text: String,
        options: [String],
        correctIndex: Int,
        explanation: String = "",
        imageURL: URL? = nil,
        topic: String = "",
        subject: String = "",
        marks: Int = 1,
        negativeMarks: Double = 0
    ) {
        self.id = id
        self.text = text
        self.options = options
        self.correctIndex = correctIndex
        self.explanation = explanation
        self.imageURL = imageURL
        self.topic = topic
        self.subject = subject
        self.marks = marks
        self.negativeMarks = negativeMarks
    }
}

/// One answered question inside an attempt, persisted locally and synced to
/// `attempts_api.php` / `api/sync_game_stats.php`.
struct AttemptAnswer: Codable, Identifiable, Hashable {
    var id: Int { questionId }
    let questionId: Int
    let selectedIndex: Int
    let correctIndex: Int
    let timeTakenSeconds: Int

    var isCorrect: Bool { selectedIndex == correctIndex }

    init(questionId: Int, selectedIndex: Int, correctIndex: Int, timeTakenSeconds: Int = 0) {
        self.questionId = questionId
        self.selectedIndex = selectedIndex
        self.correctIndex = correctIndex
        self.timeTakenSeconds = timeTakenSeconds
    }
}

/// A completed quiz attempt. `api/sync_game_stats.php` reads these as form
/// fields.
struct QuizAttempt: Codable, Identifiable, Hashable {
    let id: String
    let quizId: Int
    let quizTitle: String
    let userId: Int
    let answers: [AttemptAnswer]
    let startedAt: Date
    let finishedAt: Date
    let mode: String

    var attempted: Int { answers.count }
    var correct: Int { answers.filter(\.isCorrect).count }
    var wrong: Int { attempted - correct }

    var accuracy: Double {
        guard attempted > 0 else { return 0 }
        return Double(correct) / Double(attempted)
    }

    var durationSeconds: Int {
        max(0, Int(finishedAt.timeIntervalSince(startedAt)))
    }

    init(
        id: String = UUID().uuidString,
        quizId: Int,
        quizTitle: String,
        userId: Int,
        answers: [AttemptAnswer],
        startedAt: Date,
        finishedAt: Date,
        mode: String = "test"
    ) {
        self.id = id
        self.quizId = quizId
        self.quizTitle = quizTitle
        self.userId = userId
        self.answers = answers
        self.startedAt = startedAt
        self.finishedAt = finishedAt
        self.mode = mode
    }

    /// Form payload expected by the stats-sync scripts.
    var syncFormFields: [String: String] {
        [
            "user_id": String(userId),
            "quiz_id": String(quizId),
            "attempted": String(attempted),
            "correct": String(correct),
            "wrong": String(wrong),
            "accuracy": String(format: "%.2f", accuracy * 100),
            "duration": String(durationSeconds),
            "mode": mode,
            "answers_json": (try? JSONEncoder().encode(answers))
                .flatMap { String(data: $0, encoding: .utf8) } ?? "[]",
        ]
    }
}

/// A row in the attempt history list from `attempts_api.php`.
struct AttemptSummary: Decodable, Identifiable, Hashable {
    let id: Int
    let quizTitle: String
    let attempted: Int
    let correct: Int
    let wrong: Int
    let accuracy: Double
    let date: String

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        id = container.flexInt("attempt_id", "id")
        quizTitle = container.flexString("quiz_title", "title", "quiz", "name")
        attempted = container.flexInt("attempted", "total", "total_questions")
        correct = container.flexInt("correct", "correct_answers", "right")
        wrong = container.flexInt("wrong", "incorrect", "wrong_answers")
        accuracy = container.flexDouble("accuracy", "score", "percent")
        date = container.flexString("date", "created_at", "attempted_at", "timestamp")
    }
}
