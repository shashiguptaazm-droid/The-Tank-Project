import SwiftUI

/// Formatted question text generator and shareable card helper.
///
/// 1:1 port of Android `QuestionShareHelper.kt` & `QuestionShareBottomSheet.kt`.
public enum QuestionShareHelper {

    public struct QuestionShareData: Hashable {
        public let questionId: Int
        public let questionText: String
        public let optionA: String
        public let optionB: String
        public let optionC: String
        public let optionD: String
        public let subject: String
        public let topic: String
        public let imageURL: String?
        public let userId: Int
        public let correctAnswer: String?
        public let explanation: String?
        public let isAnswered: Bool

        public init(
            questionId: Int,
            questionText: String,
            optionA: String,
            optionB: String,
            optionC: String,
            optionD: String,
            subject: String,
            topic: String,
            imageURL: String? = nil,
            userId: Int = 0,
            correctAnswer: String? = nil,
            explanation: String? = nil,
            isAnswered: Bool = false
        ) {
            self.questionId = questionId
            self.questionText = questionText
            self.optionA = optionA
            self.optionB = optionB
            self.optionC = optionC
            self.optionD = optionD
            self.subject = subject
            self.topic = topic
            self.imageURL = imageURL
            self.userId = userId
            self.correctAnswer = correctAnswer
            self.explanation = explanation
            self.isAnswered = isAnswered
        }
    }

    public static func buildShareUrl(questionId: Int, userId: Int) -> URL {
        URL(string: "https://medigyaan.com/Neurons/share.php?question_id=\(questionId)&ref=\(userId)")!
    }

    public static func buildShareText(data: QuestionShareData, includeAnswer: Bool = false) -> String {
        var sb = ""
        sb += "🧠 *MediGyaan Medical MCQ Challenge*\n"
        let subj = data.subject.isEmpty ? "NEET PG" : data.subject
        sb += "📚 *Subject:* \(subj)"
        if !data.topic.isEmpty && data.topic != "General" {
            sb += " • *Topic:* \(data.topic)"
        }
        sb += "\n\n"

        let cleanQ = data.questionText.replacingOccurrences(of: "^\\d+[.\\s\\-)]+\\s*", with: "", options: .regularExpression)
        sb += "*Q:* \(cleanQ)\n\n"

        sb += "A) \(data.optionA)\n"
        sb += "B) \(data.optionB)\n"
        sb += "C) \(data.optionC)\n"
        sb += "D) \(data.optionD)\n\n"

        if includeAnswer, let ans = data.correctAnswer, !ans.isEmpty {
            sb += "✅ *Correct Answer:* Option \(ans)\n"
            if let exp = data.explanation, !exp.isEmpty {
                sb += "💡 *Explanation:* \(exp)\n\n"
            } else {
                sb += "\n"
            }
        }

        let link = buildShareUrl(questionId: data.questionId, userId: data.userId).absoluteString
        sb += "🎯 *Think you know the answer? Solve & compete on MediGyaan:*\n"
        sb += "👉 \(link)\n\n"
        sb += "#MediGyaan #NEETPG #MedicalMCQ #NextExam"
        return sb
    }
}
