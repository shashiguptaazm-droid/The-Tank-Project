import SwiftUI

/// Renders a branded, high-definition (1080px width) image card for MCQ social media sharing.
@MainActor
struct QuestionCardRenderer {

    /// Renders a question card into a `UIImage` using iOS 16's native `ImageRenderer`.
    static func render(
        question: Question,
        includeAnswer: Bool = false
    ) -> UIImage? {
        let cardView = QuestionCardExportView(question: question, includeAnswer: includeAnswer)
            .frame(width: 1080)

        let renderer = ImageRenderer(content: cardView)
        renderer.scale = 1.0
        renderer.isOpaque = true
        return renderer.uiImage
    }
}

/// The visual SwiftUI layout for the 1080px export card.
struct QuestionCardExportView: View {

    let question: Question
    let includeAnswer: Bool

    private let optionLetters = ["A", "B", "C", "D", "E", "F"]

    var body: some View {
        VStack(alignment: .leading, spacing: 28) {
            // Header Bar
            HStack(alignment: .center, spacing: 16) {
                Image("ic_launcher")
                    .resizable()
                    .scaledToFit()
                    .frame(width: 60, height: 60)
                    .clipShape(RoundedRectangle(cornerRadius: 14))

                VStack(alignment: .leading, spacing: 4) {
                    Text("MediGyaan")
                        .font(.system(size: 28, weight: .bold, design: .rounded))
                        .foregroundStyle(.white)

                    Text("NEET-PG / Medical MCQ Challenge")
                        .font(.system(size: 16, weight: .medium))
                        .foregroundStyle(Color(hex: 0x9F_B3_CC))
                }

                Spacer()

                Text(subjectTopicBadge)
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(Color(hex: 0x64_DF_DF))
                    .padding(.horizontal, 16)
                    .padding(.vertical, 8)
                    .background(Color(hex: 0x2A_3C_64))
                    .clipShape(Capsule())
            }

            Divider()
                .overlay(Color(hex: 0x2E_40_68))

            // Optional Image
            if let imageURL = question.imageURL {
                AsyncImage(url: imageURL) { phase in
                    if let image = phase.image {
                        image
                            .resizable()
                            .scaledToFit()
                            .frame(maxHeight: 400)
                            .frame(maxWidth: .infinity)
                            .clipShape(RoundedRectangle(cornerRadius: 16))
                    }
                }
            }

            // Question Statement
            Text(cleanQuestionText)
                .font(.system(size: 28, weight: .bold))
                .foregroundStyle(.white)
                .lineSpacing(8)

            // Options List
            VStack(spacing: 16) {
                ForEach(Array(question.options.enumerated()), id: \.offset) { index, option in
                    let letter = optionLetters.indices.contains(index) ? optionLetters[index] : "\(index + 1)"
                    let isCorrect = includeAnswer && index == question.correctIndex

                    HStack(spacing: 16) {
                        Text(letter)
                            .font(.system(size: 20, weight: .bold))
                            .foregroundStyle(.white)
                            .frame(width: 44, height: 44)
                            .background(isCorrect ? Color(hex: 0x10_B9_81) : Color(hex: 0x3A_50_6B))
                            .clipShape(Circle())

                        Text(cleanOption(option))
                            .font(.system(size: 22, weight: isCorrect ? .bold : .regular))
                            .foregroundStyle(isCorrect ? Color(hex: 0x34_D3_99) : Color(hex: 0xE0_E6_ED))
                            .multilineTextAlignment(.leading)

                        Spacer()

                        if isCorrect {
                            Image(systemName: "checkmark.circle.fill")
                                .font(.system(size: 24))
                                .foregroundStyle(Color(hex: 0x34_D3_99))
                        }
                    }
                    .padding(18)
                    .background(isCorrect ? Color(hex: 0x06_4E_3B) : Color(hex: 0x1A_27_44))
                    .clipShape(RoundedRectangle(cornerRadius: 18))
                    .overlay(
                        RoundedRectangle(cornerRadius: 18)
                            .stroke(isCorrect ? Color(hex: 0x10_B9_81) : Color(hex: 0x2E_40_68), lineWidth: isCorrect ? 2 : 1)
                    )
                }
            }

            // Explanation Banner (if enabled)
            if includeAnswer && !question.explanation.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    HStack(spacing: 8) {
                        Image(systemName: "lightbulb.fill")
                            .foregroundStyle(Color(hex: 0xF4_C9_5D))
                        Text("Explanation")
                            .font(.system(size: 20, weight: .bold))
                            .foregroundStyle(.white)
                    }

                    Text(question.explanation)
                        .font(.system(size: 18))
                        .foregroundStyle(Color(hex: 0xC8_EA_D9))
                        .lineSpacing(6)
                }
                .padding(20)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color(hex: 0x1B_3B_2B))
                .clipShape(RoundedRectangle(cornerRadius: 18))
            }

            Divider()
                .overlay(Color(hex: 0x2E_40_68))

            // Footer Bar
            HStack {
                Text("🧠 Can you solve this? Attempt on MediGyaan App!")
                    .font(.system(size: 18, weight: .bold))
                    .foregroundStyle(Color(hex: 0xF4_C9_5D))

                Spacer()

                Text("medigyaan.xyz")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(Color(hex: 0x64_DF_DF))
            }
        }
        .padding(40)
        .background(
            LinearGradient(
                colors: [Color(hex: 0x0D_1B_2A), Color(hex: 0x1B_26_3B), Color(hex: 0x0D_1B_2A)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        )
        .clipShape(RoundedRectangle(cornerRadius: 32))
        .overlay(
            RoundedRectangle(cornerRadius: 32)
                .stroke(Color(hex: 0x3A_50_6B), lineWidth: 3)
        )
    }

    private var cleanQuestionText: String {
        question.text.replacingOccurrences(of: #"^\d+[.\s\-)\]]+\s*"#, with: "", options: .regularExpression)
    }

    private func cleanOption(_ text: String) -> String {
        text.replacingOccurrences(of: #"^\d+[.\s\-)\]]+\s*"#, with: "", options: .regularExpression).trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private var subjectTopicBadge: String {
        if !question.topic.isEmpty, question.topic != "General", question.topic != "Uncategorized" {
            return "\(question.subject) • \(question.topic)"
        }
        return question.subject.isEmpty ? "NEET PG" : question.subject
    }
}
