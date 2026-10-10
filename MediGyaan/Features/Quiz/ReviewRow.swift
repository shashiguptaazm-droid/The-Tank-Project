import SwiftUI

/// Ports `ReviewAdapter.onBindViewHolder()` and its inflated
/// `res/layout/item_review_row.xml`: the single card that renders one row of the
/// post-quiz review list.
///
/// The Kotlin adapter reads a raw `JSONArray` and, for every key, falls back
/// through a chain of aliases (`question` → `question_text`,
/// `selected_option` → `user_answer` → `your_answer`, `correct_option` →
/// `correct_answer`, `image_url` → `question_image`). ``Item`` keeps that
/// resolution, so a row can be built straight from decoded JSON
/// (`Item(json:)`) or assembled field by field.
///
/// State matrix, all of it driven by ``Item/isCorrect``:
///
/// | row state | your-answer colour | correct option | user option |
/// |---|---|---|---|
/// | correct | success green | green fill | green fill (same letter) |
/// | wrong | error red | green fill | red fill |
/// | unanswered | error red | green fill | neutral (no red fill) |
/// | unparsable key (`"N/A"`) | error red | none painted | neutral |
///
/// Android paints a conflicting row by calling `highlightWrong()` *after*
/// `highlightCorrect()`, so an explicit `is_correct: false` on a row whose user
/// and correct letters agree leaves the option red. ``Item/state(forLetter:)``
/// reproduces that paint order.
///
/// Android hardcodes the row's option fills as `#2E7D32` / `#C62828` / `#FF0000`
/// and the correct-answer line as `#1565C0`; those literals have no token in
/// `Palette+Android.swift`, so this port substitutes the semantic
/// ``AppTheme/Palette`` entries (`success`, `error`, `primary`), which also makes
/// the row adapt to dark mode.
struct ReviewRow: View {

    /// The raw image host from `ReviewAdapter.IMAGE_BASE_URL`.
    enum ImageSource {
        /// `IMAGE_BASE_URL` — the `"https://medigyaan.com/Neurons/"` companion
        /// constant. `ReviewAdapter.onBindViewHolder()` prefixes every relative
        /// `question_image` with it.
        static let baseURL = "https://medigyaan.com/Neurons/"
    }

    /// Ports one `JSONObject` element of the adapter's `reviewArray`.
    struct Item: Identifiable, Hashable {

        /// `question_id`, `-1` when absent.
        var questionID: Int = -1
        /// `question`, falling back to `question_text`.
        var question: String = ""
        var optionA: String = ""
        var optionB: String = ""
        var optionC: String = ""
        var optionD: String = ""
        /// `image_url`, falling back to `question_image`.
        var imagePath: String = ""
        /// `selected_option` → `user_answer` → `your_answer`.
        var userAnswerRaw: String = ""
        /// `correct_option` → `correct_answer` → `"N/A"`.
        var correctAnswerRaw: String = ""
        var explanation: String = ""
        /// `is_correct`. `nil` when the key is absent, which is what makes
        /// ``isCorrect`` fall back to comparing the two answer letters —
        /// `ReviewAdapter.readBoolean()` has the same absent/present split.
        var isCorrectFlag: Bool?

        /// Ports the adapter's `uniqueMap` key: `"ID_<id>"` when
        /// `question_id > 0`, otherwise the trimmed question text.
        var id: String {
            questionID > 0 ? "ID_\(questionID)" : question.trimmingCharacters(in: .whitespacesAndNewlines)
        }

        /// Field-by-field construction, for callers that already decoded the row
        /// into a model rather than raw JSON.
        init(
            questionID: Int = -1,
            question: String = "",
            optionA: String = "",
            optionB: String = "",
            optionC: String = "",
            optionD: String = "",
            imagePath: String = "",
            userAnswerRaw: String = "",
            correctAnswerRaw: String = "",
            explanation: String = "",
            isCorrectFlag: Bool? = nil
        ) {
            self.questionID = questionID
            self.question = question
            self.optionA = optionA
            self.optionB = optionB
            self.optionC = optionC
            self.optionD = optionD
            self.imagePath = imagePath
            self.userAnswerRaw = userAnswerRaw
            self.correctAnswerRaw = correctAnswerRaw
            self.explanation = explanation
            self.isCorrectFlag = isCorrectFlag
        }

        /// Ports `onBindViewHolder()`'s JSON reads, alias chains and all.
        init(json: [String: Any]) {
            questionID = Item.integer(json, "question_id", fallback: -1)
            question = Item.string(json, "question", fallback: Item.string(json, "question_text", fallback: "Question not available"))
            optionA = Item.string(json, "option_a")
            optionB = Item.string(json, "option_b")
            optionC = Item.string(json, "option_c")
            optionD = Item.string(json, "option_d")
            imagePath = Item.string(json, "image_url", fallback: Item.string(json, "question_image"))
            userAnswerRaw = Item.string(json, "selected_option", fallback: Item.string(json, "user_answer", fallback: Item.string(json, "your_answer")))
            correctAnswerRaw = Item.string(json, "correct_option", fallback: Item.string(json, "correct_answer", fallback: "N/A"))
            explanation = Item.string(json, "explanation")
            isCorrectFlag = Item.boolean(json, "is_correct")
        }

        /// Ports `normalizeAnswer()` — only a bare `A`/`B`/`C`/`D` survives.
        var userAnswerLetter: String {
            Item.normalizedLetter(userAnswerRaw)
        }

        /// Ports `normalizeAnswer()` applied to the correct-answer chain.
        var correctAnswerLetter: String {
            Item.normalizedLetter(correctAnswerRaw)
        }

        /// Ports `answerToText()` — the option body for a letter, `""` otherwise.
        func text(forLetter letter: String) -> String {
            switch letter.uppercased() {
            case "A": return optionA
            case "B": return optionB
            case "C": return optionC
            case "D": return optionD
            default: return ""
            }
        }

        /// Ports the `is_correct` / letter-comparison branch. An explicit flag
        /// always wins; otherwise the row is correct only when the learner
        /// actually answered and the letters match case-insensitively.
        var isCorrect: Bool {
            if let isCorrectFlag { return isCorrectFlag }
            return !userAnswerLetter.isEmpty
                && userAnswerLetter.caseInsensitiveCompare(correctAnswerLetter) == .orderedSame
        }

        /// Ports the `ImageView` visibility guard: blank, `"null"` and `"0"` all
        /// hide the image.
        var hasImage: Bool {
            let raw = imagePath.trimmingCharacters(in: .whitespacesAndNewlines)
            return !raw.isEmpty && raw != "null" && raw != "0"
        }

        /// Ports the `imgUrl` `when` block: absolute URLs pass through with the
        /// legacy `medigyaan.xyz` host swapped for `medigyaan.com`, relative
        /// paths are hung off ``ImageSource/baseURL``, and spaces are escaped.
        var imageURL: URL? {
            guard hasImage else { return nil }
            let raw = imagePath.trimmingCharacters(in: .whitespacesAndNewlines)
            let lowered = raw.lowercased()
            let resolved: String
            if lowered.hasPrefix("http://") || lowered.hasPrefix("https://") {
                resolved = raw.replacingOccurrences(of: "medigyaan.xyz", with: "medigyaan.com")
            } else {
                let relative = lowered.hasPrefix("./")
                    ? String(raw.dropFirst(2))
                    : raw
                resolved = ImageSource.baseURL + relative.drop(while: { $0 == "/" })
            }
            return URL(string: resolved.replacingOccurrences(of: " ", with: "%20"))
        }

        /// Ports the `itemExplanation` visibility guard.
        var hasExplanation: Bool {
            !explanation.isEmpty && explanation != "null"
        }

        /// Ports the non-blank `"A. …"` option list `askAiBtn` hands to
        /// `AiChatDialogHelper.openAskAiDialog()`.
        var askAIOptions: [String] {
            [("A", optionA), ("B", optionB), ("C", optionC), ("D", optionD)]
                .filter { !$0.1.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
                .map { "\($0.0). \($0.1)" }
        }

        /// Ports `calculateCompleteness()` over the resolved fields — the score
        /// the adapter's dedup uses to pick between two copies of one question.
        var completeness: Int {
            var score = 0
            for value in [question, optionA, optionB, optionC, optionD,
                          userAnswerRaw, correctAnswerRaw, explanation, imagePath] {
                if !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && value != "null" {
                    score += 1
                }
            }
            return score
        }

        /// Ports the adapter's `init` dedup: first occurrence wins its slot, and
        /// a later copy of the same question replaces it only when it is at
        /// least as complete. Insertion order is preserved.
        static func deduplicated(_ items: [Item]) -> [Item] {
            var keys: [String] = []
            var winners: [String: Item] = [:]
            for item in items {
                if let existing = winners[item.id] {
                    if item.completeness >= existing.completeness {
                        winners[item.id] = item
                    }
                } else {
                    winners[item.id] = item
                    keys.append(item.id)
                }
            }
            return keys.compactMap { winners[$0] }
        }

        // MARK: - JSON coercion

        private static func normalizedLetter(_ raw: String) -> String {
            switch raw.trimmingCharacters(in: .whitespacesAndNewlines).uppercased() {
            case "A": return "A"
            case "B": return "B"
            case "C": return "C"
            case "D": return "D"
            default: return ""
            }
        }

        private static func string(_ json: [String: Any], _ key: String, fallback: String = "") -> String {
            guard let value = json[key], !(value is NSNull) else { return fallback }
            if let text = value as? String { return text }
            return String(describing: value)
        }

        private static func integer(_ json: [String: Any], _ key: String, fallback: Int) -> Int {
            if let number = json[key] as? Int { return number }
            if let text = json[key] as? String,
               let number = Int(text.trimmingCharacters(in: .whitespacesAndNewlines)) {
                return number
            }
            return fallback
        }

        /// Ports `readBoolean()`: bool, `1`, `"true"` and `"1"` are true;
        /// anything else present is false; an absent key is `nil`.
        private static func boolean(_ json: [String: Any], _ key: String) -> Bool? {
            guard let value = json[key], !(value is NSNull) else { return nil }
            if let flag = value as? Bool { return flag }
            if let number = value as? Int { return number == 1 }
            if let number = value as? Double { return number == 1 }
            if let text = value as? String {
                let lowered = text.lowercased()
                return lowered == "true" || lowered == "1"
            }
            return false
        }
    }

    /// One review row, at 1-based `index`.
    let item: Item
    let index: Int
    /// Fires when `askAiBtn` is tapped, handing the host the same payload the
    /// Kotlin listener passes to `AiChatDialogHelper.openAskAiDialog()`.
    var onAskAI: (Item) -> Void

    private let imageHeight: CGFloat = 180

    init(item: Item, index: Int, onAskAI: @escaping (Item) -> Void) {
        self.item = item
        self.index = index
        self.onAskAI = onAskAI
    }

    var body: some View {
        CardContainer(padding: AppTheme.Spacing.md) {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                questionText
                if let url = item.imageURL {
                    questionImage(url)
                }
                optionsList
                userAnswerText
                correctAnswerText
                if item.hasExplanation {
                    explanationBlock
                }
                askAIButton
            }
        }
        .padding(.vertical, AppTheme.Spacing.xxs)
    }

    // MARK: - Question

    private var questionText: some View {
        Text("Q\(index): \(item.question)")
            .font(AppTheme.Font.bodyBold)
            .foregroundStyle(AppTheme.Palette.textPrimary)
            .fixedSize(horizontal: false, vertical: true)
    }

    private func questionImage(_ url: URL) -> some View {
        AsyncImage(url: url) { phase in
            if case .success(let image) = phase {
                image
                    .resizable()
                    .scaledToFill()
            } else {
                AndroidIcon(.ic_image_placeholder, size: AppTheme.Spacing.xxl, tint: AppTheme.Palette.textMuted)
            }
        }
        .frame(height: imageHeight)
        .frame(maxWidth: .infinity)
        .clipped()
        .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.md, style: .continuous))
    }

    // MARK: - Options

    private var optionsList: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
            ForEach(["A", "B", "C", "D"], id: \.self) { letter in
                optionChip(letter: letter)
            }
        }
    }

    private func optionChip(letter: String) -> some View {
        let state = item.state(forLetter: letter)
        return Text("\(letter). \(item.text(forLetter: letter))")
            .font(AppTheme.Font.callout)
            .foregroundStyle(state == .neutral ? AppTheme.Palette.textPrimary : AppTheme.Palette.onPrimary)
            .fixedSize(horizontal: false, vertical: true)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(AppTheme.Spacing.optionGap)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.md, style: .continuous)
                    .fill(chipBackground(for: state))
            )
    }

    private func chipBackground(for state: OptionReviewState) -> Color {
        switch state {
        case .correct:
            return AppTheme.Palette.success
        case .wrong:
            return AppTheme.Palette.error
        case .neutral:
            return AppTheme.Palette.optionBackground
        }
    }

    // MARK: - Answers

    private var userAnswerText: some View {
        Text(userAnswerLine)
            .font(AppTheme.Font.callout.weight(.bold))
            .foregroundStyle(item.isCorrect ? AppTheme.Palette.success : AppTheme.Palette.error)
            .fixedSize(horizontal: false, vertical: true)
    }

    /// Ports the `itemUserAnswer` branch: `"Not Answered"` when the answer did
    /// not normalise to a letter, otherwise the letter plus its option body.
    private var userAnswerLine: String {
        let letter = item.userAnswerLetter
        guard !letter.isEmpty else { return "Your Answer: Not Answered" }
        return "Your Answer: \(letter) → \(item.text(forLetter: letter))"
    }

    private var correctAnswerText: some View {
        Text("Correct Answer: \(item.correctAnswerLetter) → \(item.text(forLetter: item.correctAnswerLetter))")
            .font(AppTheme.Font.callout)
            .foregroundStyle(AppTheme.Palette.primary)
            .fixedSize(horizontal: false, vertical: true)
            .padding(.top, AppTheme.Spacing.xxs)
    }

    // MARK: - Explanation

    /// Ports `aiMarkdownSpannable("Explanation:\n$explanation")`. The Android
    /// background is a square `@color/colorPrimaryContainer`, so no radius.
    private var explanationBlock: some View {
        Text(explanationText)
            .font(AppTheme.Font.subheadline)
            .foregroundStyle(AppTheme.Palette.onPrimaryContainer)
            .fixedSize(horizontal: false, vertical: true)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(AppTheme.Spacing.optionGap)
            .background(AppTheme.Palette.primaryContainer)
    }

    private var explanationText: AttributedString {
        let raw = "Explanation:\n\(item.explanation)"
        return (try? AttributedString(markdown: raw)) ?? AttributedString(raw)
    }

    // MARK: - Ask AI

    private var askAIButton: some View {
        Button {
            onAskAI(item)
        } label: {
            Text("🤖 Ask AI Tutor")
                .font(AppTheme.Font.callout.weight(.bold))
                .padding(.horizontal, AppTheme.Spacing.xl)
                .padding(.vertical, AppTheme.Spacing.sm)
                .background(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.md, style: .continuous)
                        .fill(AppTheme.Palette.primary)
                )
                .foregroundStyle(AppTheme.Palette.onPrimary)
        }
        .buttonStyle(.plain)
        .padding(.top, AppTheme.Spacing.xxs)
        .accessibilityLabel("Ask AI Tutor")
    }
}

extension ReviewRow.Item {

    /// Ports the `resetOptionColors()` → `highlightCorrect()` →
    /// `highlightWrong()` paint order. The wrong check runs first because the
    /// Kotlin adapter paints the red fill last, letting it cover the green one.
    func state(forLetter letter: String) -> OptionReviewState {
        if !isCorrect,
           !userAnswerLetter.isEmpty,
           letter.caseInsensitiveCompare(userAnswerLetter) == .orderedSame {
            return .wrong
        }
        if !correctAnswerLetter.isEmpty,
           letter.caseInsensitiveCompare(correctAnswerLetter) == .orderedSame {
            return .correct
        }
        return .neutral
    }
}