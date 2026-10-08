import SwiftUI

/// Share bottom sheet modal for clinical questions.
///
/// 1:1 port of Android `QuestionShareBottomSheet.kt`.
/// Features formatted preview cards, toggles to include/hide rationales,
/// and direct links to share on WhatsApp, Telegram, or via native iOS ShareLink.
struct QuestionShareSheet: View {

    let data: QuestionShareHelper.QuestionShareData

    @Environment(\.dismiss) private var dismiss
    @State private var includeAnswer: Bool = false
    @State private var hasCopied: Bool = false

    init(data: QuestionShareHelper.QuestionShareData) {
        self.data = data
    }

    init(question: Question, userId: Int = 0) {
        let optA = question.options.indices.contains(0) ? question.options[0] : ""
        let optB = question.options.indices.contains(1) ? question.options[1] : ""
        let optC = question.options.indices.contains(2) ? question.options[2] : ""
        let optD = question.options.indices.contains(3) ? question.options[3] : ""
        let letters = ["A", "B", "C", "D", "E"]
        let corr = question.options.indices.contains(question.correctIndex) ? letters[question.correctIndex] : nil

        self.data = QuestionShareHelper.QuestionShareData(
            questionId: question.id,
            questionText: question.text,
            optionA: optA,
            optionB: optB,
            optionC: optC,
            optionD: optD,
            subject: question.subject.isEmpty ? "Medical MCQ" : question.subject,
            topic: question.topic,
            imageURL: question.imageURL?.absoluteString,
            userId: userId,
            correctAnswer: corr,
            explanation: question.explanation
        )
    }

    private var shareText: String {
        QuestionShareHelper.buildShareText(data: data, includeAnswer: includeAnswer)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: AppTheme.Spacing.md) {
                    // Header Subtitle
                    Text("\(data.subject) • \(data.topic.isEmpty ? "High-Yield" : data.topic)")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary)

                    // Formatted Card Preview
                    CardContainer {
                        VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
                            HStack {
                                TagBadge(text: "Q#\(data.questionId)", tint: AppTheme.Palette.primary)
                                Spacer()
                                Image(systemName: "brain.head.profile")
                                    .foregroundStyle(AppTheme.Palette.accent)
                            }

                            Text(data.questionText)
                                .font(AppTheme.Font.headline)
                                .foregroundStyle(AppTheme.Palette.textPrimary)
                                .padding(.vertical, 2)

                            VStack(alignment: .leading, spacing: 3) {
                                Text("A) \(data.optionA)").font(AppTheme.Font.caption)
                                Text("B) \(data.optionB)").font(AppTheme.Font.caption)
                                Text("C) \(data.optionC)").font(AppTheme.Font.caption)
                                Text("D) \(data.optionD)").font(AppTheme.Font.caption)
                            }
                            .foregroundStyle(AppTheme.Palette.textSecondary)

                            if includeAnswer, let ans = data.correctAnswer {
                                Divider().background(AppTheme.Palette.divider)
                                HStack {
                                    Text("Correct Answer: Option \(ans)")
                                        .font(AppTheme.Font.caption.weight(.bold))
                                        .foregroundStyle(AppTheme.Palette.success)
                                }
                            }
                        }
                    }

                    // Include Answer Toggle (if answered)
                    if data.isAnswered {
                        Toggle(isOn: $includeAnswer) {
                            Text("Include Correct Answer & Clinical Explanation")
                                .font(AppTheme.Font.subheadline)
                                .foregroundStyle(AppTheme.Palette.textPrimary)
                        }
                        .tint(AppTheme.Palette.primary)
                        .padding(.horizontal, AppTheme.Spacing.xs)
                    }

                    // Share Actions Grid
                    VStack(spacing: AppTheme.Spacing.sm) {
                        ShareLink(item: shareText) {
                            HStack {
                                Image(systemName: "square.and.arrow.up")
                                Text("Share with Medical Peers")
                            }
                            .font(AppTheme.Font.headline)
                            .foregroundStyle(Color.white)
                            .frame(maxWidth: .infinity)
                            .frame(height: 50)
                            .background(RoundedRectangle(cornerRadius: AppTheme.Radius.md).fill(AppTheme.Palette.primary))
                        }

                        Button {
                            UIPasteboard.general.string = shareText
                            hasCopied = true
                        } label: {
                            HStack {
                                Image(systemName: hasCopied ? "checkmark" : "doc.on.doc")
                                Text(hasCopied ? "Copied to Clipboard!" : "Copy Formatted Text")
                            }
                            .font(AppTheme.Font.subheadline.weight(.semibold))
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                            .frame(maxWidth: .infinity)
                            .frame(height: 44)
                        }
                    }
                    .padding(.top, AppTheme.Spacing.sm)
                }
                .padding(AppTheme.Spacing.md)
            }
            .screenBackground()
            .navigationTitle("Share MCQ")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}
