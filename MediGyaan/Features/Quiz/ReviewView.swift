import SwiftUI

/// One row of the `REVIEW_JSON` array, and of the review list rendered by
/// ``ReviewView``.
///
/// Ports `ReviewQuestionModel` from Android `ReviewActivity.kt`. Every field
/// carries a default because Gson instantiated the data class from a sparse map
/// — a row without `explanation` or `image_url` still decoded on Android, and
/// `Codable`'s synthesised decoding drops every key the payload omits here too.
struct ReviewQuestionItem: Identifiable, Codable, Hashable {

    var id: Int { question_id }

    let question_id: Int
    let question: String
    let option_a: String
    let option_b: String
    let option_c: String
    let option_d: String
    let option_e: String
    let selected_option: String
    let correct_option: String
    let selected_answer_text: String
    let correct_answer_text: String
    let score_change: Int
    let explanation: String
    let image_url: String
    let is_correct: Int

    init(
        question_id: Int = 0,
        question: String = "",
        option_a: String = "",
        option_b: String = "",
        option_c: String = "",
        option_d: String = "",
        option_e: String = "",
        selected_option: String = "",
        correct_option: String = "",
        selected_answer_text: String = "",
        correct_answer_text: String = "",
        score_change: Int = 0,
        explanation: String = "",
        image_url: String = "",
        is_correct: Int = 0
    ) {
        self.question_id = question_id
        self.question = question
        self.option_a = option_a
        self.option_b = option_b
        self.option_c = option_c
        self.option_d = option_d
        self.option_e = option_e
        self.selected_option = selected_option
        self.correct_option = correct_option
        self.selected_answer_text = selected_answer_text
        self.correct_answer_text = correct_answer_text
        self.score_change = score_change
        self.explanation = explanation
        self.image_url = image_url
        self.is_correct = is_correct
    }

    // MARK: - Derived display state

    /// Ports `val isCorrect = model.is_correct == 1` from `ReviewQuestionCard`.
    var isCorrect: Bool { is_correct == 1 }

    /// Ports the header `Text` in `ReviewQuestionCard`: `"Correct Answer"` when
    /// the pick matched, `"Wrong Answer"` otherwise.
    var verdictTitle: String { isCorrect ? "Correct Answer" : "Wrong Answer" }

    /// Ports the `optionsList` of `ReviewQuestionCard`: A..E, keeping only the
    /// non-blank entries the Kotlin `if (optionText.isNotBlank())` guard kept.
    var optionPairs: [ReviewOption] {
        [
            ReviewOption(key: "A", text: option_a),
            ReviewOption(key: "B", text: option_b),
            ReviewOption(key: "C", text: option_c),
            ReviewOption(key: "D", text: option_d),
            ReviewOption(key: "E", text: option_e)
        ]
        .filter { !$0.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
    }

    /// Ports the `options` list the Ask AI button built in `ReviewQuestionCard`.
    /// Note the deliberate A..D window: `option_e` was never offered to the
    /// tutor even though it is drawn in the option list.
    var askAIOptions: [String] {
        [
            ReviewOption(key: "A", text: option_a),
            ReviewOption(key: "B", text: option_b),
            ReviewOption(key: "C", text: option_c),
            ReviewOption(key: "D", text: option_d)
        ]
        .filter { !$0.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
        .map { "\($0.key). \($0.text)" }
    }

    /// Ports the `"Your Answer"` `ReviewAnswerBox` line: `"Not Attempted"` when
    /// nothing was selected, otherwise `"<letter>. <text>"`.
    var yourAnswerLine: String {
        selected_option.isEmpty ? "Not Attempted" : "\(selected_option). \(selected_answer_text)"
    }

    /// Ports the `"Correct Answer"` `ReviewAnswerBox` line.
    var correctAnswerLine: String {
        "\(correct_option). \(correct_answer_text)"
    }

    /// Ports the `"Score: ..."` line, which Kotlin only signs when the value is
    /// non-negative — so a `0` reads `+0`.
    var scoreLine: String {
        score_change >= 0 ? "Score: +\(score_change)" : "Score: \(score_change)"
    }

    /// Ports the `if (model.image_url.isNotEmpty() && model.image_url != "null")`
    /// guard plus the `https://medigyaan.com/Neurons/` prefix Coil was handed
    /// for a relative path.
    var resolvedImageURL: URL? {
        let trimmed = image_url.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, trimmed != "null" else { return nil }
        if trimmed.hasPrefix("http") { return URL(string: trimmed) }
        return URL(string: "https://medigyaan.com/Neurons/\(trimmed)")
    }

    /// Ports one `"A" to model.option_a` pair of `optionsList`.
    struct ReviewOption: Identifiable, Hashable {
        let key: String
        let text: String
        var id: String { key }
    }
}

/// The post-attempt answer review.
///
/// Ports `ReviewScreen` from Android `ReviewActivity.kt` — the header card with
/// the correct / wrong / tallies and the accuracy bar, the per-question answer
/// analysis and the "Ask AI Medical Tutor" handoff. Android received its rows as
/// the `REVIEW_JSON` intent extra; iOS callers pass either the raw string or the
/// decoded array.
struct ReviewView: View {

    let questions: [ReviewQuestionItem]

    /// Correct-only, wrong-only and unfiltered views of the review list. An
    /// iOS addition — `ReviewScreen` had no filter, it rendered every row.
    enum FilterMode: String, CaseIterable {
        case all = "All"
        case correct = "Correct"
        case wrong = "Incorrect"
    }

    @Environment(\.dismiss) private var dismiss

    @State private var filter: FilterMode = .all
    /// The `var expanded by remember { mutableStateOf(false) }` of
    /// `ReviewQuestionCard`, hoisted so one answer stays open as the list scrolls.
    @State private var expandedQuestionIds: Set<Int> = []
    /// The row whose "Ask AI" button was last tapped.
    @State private var askAIItem: ReviewQuestionItem?
    @State private var errorMessage: String?

    init(questions: [ReviewQuestionItem]) {
        self.questions = questions
        _errorMessage = State(initialValue: nil)
    }

    /// Ports `ReviewActivity.onCreate`'s
    /// `intent.getStringExtra("REVIEW_JSON") ?: "[]"` followed by the
    /// `try { Gson().fromJson(...) } catch { emptyList() }` block. A malformed
    /// payload still renders the empty state; it additionally surfaces an alert
    /// where Android only printed a stack trace.
    init(reviewJson: String) {
        let trimmed = reviewJson.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty,
              let data = trimmed.data(using: .utf8),
              let decoded = try? JSONDecoder().decode([ReviewQuestionItem].self, from: data) else {
            self.questions = []
            _errorMessage = State(
                initialValue: trimmed.isEmpty ? nil : "Review data could not be read."
            )
            return
        }
        self.questions = decoded
        _errorMessage = State(initialValue: nil)
    }

    // MARK: - Derived counts

    private var totalQuestions: Int { questions.count }
    private var correctCount: Int { questions.filter(\.isCorrect).count }
    private var wrongCount: Int { totalQuestions - correctCount }

    /// Ports `(correctAnswers / totalQuestions * 100).toInt()`, guarding the
    /// divide-by-zero with the Kotlin `if (totalQuestions > 0)` branch.
    private var accuracy: Int {
        guard totalQuestions > 0 else { return 0 }
        return Int(Double(correctCount) / Double(totalQuestions) * 100)
    }

    private var filteredQuestions: [ReviewQuestionItem] {
        switch filter {
        case .all:
            return questions
        case .correct:
            return questions.filter(\.isCorrect)
        case .wrong:
            return questions.filter { !$0.isCorrect }
        }
    }

    // MARK: - Body

    var body: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.lg) {
                summaryHeader
                filterChips

                if questions.isEmpty {
                    noReviewDataState
                } else if filteredQuestions.isEmpty {
                    emptyState
                } else {
                    LazyVStack(spacing: AppTheme.Spacing.md) {
                        ForEach(Array(filteredQuestions.enumerated()), id: \.element.id) { index, item in
                            questionCard(index: index + 1, item: item)
                        }
                    }
                }
            }
            .padding(AppTheme.Spacing.lg)
        }
        .screenBackground()
        .navigationTitle("Review Answers")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button("Done") { dismiss() }
            }
        }
        .sheet(item: $askAIItem) { item in
            if let question = askAIQuestion(for: item) {
                AskAiSheet(question: question)
            } else {
                NavigationStack {
                    Text("This question cannot be opened in the AI tutor.")
                        .font(AppTheme.Font.callout)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                        .multilineTextAlignment(.center)
                        .padding(AppTheme.Spacing.xl)
                }
            }
        }
        .errorAlert(message: $errorMessage)
        .onAppear {
            RemoteLogger.log(tag: "ReviewView_Open", message: "User opened Exam Question Review screen")
        }
    }

    // MARK: - Summary header

    /// Ports the header `Card` of `ReviewScreen`: the title block, the three
    /// `SummaryMetricCard` tiles and the `Accuracy` progress card.
    private var summaryHeader: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.lg) {
                VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
                    Text("Review Answers")
                        .font(AppTheme.Font.title)
                        .foregroundStyle(AppTheme.Palette.textPrimary)
                    Text("Detailed performance analysis")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textMuted)
                }

                ProgressRow(
                    title: "Accuracy",
                    value: Double(accuracy) / 100.0,
                    tint: AppTheme.Palette.info,
                    caption: "\(accuracy)%"
                )

                HStack(spacing: AppTheme.Spacing.sm) {
                    metricTile(title: "Correct", count: correctCount, tint: AppTheme.Palette.success)
                    metricTile(title: "Wrong", count: wrongCount, tint: AppTheme.Palette.error)
                    metricTile(title: "Total", count: totalQuestions, tint: AppTheme.Palette.primary)
                }
            }
        }
    }

    /// Ports `SummaryMetricCard`: the tallied value over its label, tinted per
    /// outcome. Android filled the tile with a flat literal per role; here the
    /// role colour is the theme token.
    private func metricTile(title: String, count: Int, tint: Color) -> some View {
        VStack(spacing: AppTheme.Spacing.xxs) {
            Text("\(count)")
                .font(AppTheme.Font.title2)
                .foregroundStyle(AppTheme.Palette.textPrimary)
            Text(title)
                .font(AppTheme.Font.micro)
                .foregroundStyle(AppTheme.Palette.textSecondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.md, style: .continuous)
                .fill(tint.opacity(0.18))
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.md, style: .continuous)
                        .stroke(tint.opacity(0.55), lineWidth: 1)
                )
        )
    }

    // MARK: - Filters

    private var filterChips: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            ForEach(FilterMode.allCases, id: \.self) { mode in
                let isSelected = filter == mode
                Button {
                    if filter != mode { filter = mode }
                } label: {
                    Text(mode.rawValue)
                        .font(AppTheme.Font.caption.weight(.semibold))
                        .padding(.horizontal, AppTheme.Spacing.md)
                        .padding(.vertical, AppTheme.Spacing.sm)
                        .background(
                            Capsule().fill(
                                isSelected
                                    ? AppTheme.Palette.primary
                                    : AppTheme.Palette.cardBackgroundElevated
                            )
                        )
                        .foregroundStyle(
                            isSelected ? AppTheme.Palette.onPrimary : AppTheme.Palette.textSecondary
                        )
                }
                .buttonStyle(.plain)
            }
            Spacer(minLength: 0)
        }
    }

    // MARK: - Question card

    /// Ports `ReviewQuestionCard` from `ReviewActivity.kt`: the verdict header,
    /// the stem, the optional clinical image and the two answer boxes are always
    /// visible; the option list, explanation and Ask AI button sit inside the
    /// `AnimatedVisibility(visible = expanded)` block.
    private func questionCard(index: Int, item: ReviewQuestionItem) -> some View {
        let isExpanded = expandedQuestionIds.contains(item.id)

        return CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                questionHeader(index: index, item: item, isExpanded: isExpanded)

                Text(item.question)
                    .font(AppTheme.Font.body.weight(.bold))
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)

                questionImage(for: item)

                answerBox(
                    title: "Your Answer",
                    answer: item.yourAnswerLine,
                    tint: item.isCorrect ? AppTheme.Palette.success : AppTheme.Palette.danger
                )

                answerBox(
                    title: "Correct Answer",
                    answer: item.correctAnswerLine,
                    tint: AppTheme.Palette.success
                )

                if isExpanded {
                    expandedSection(for: item)
                }
            }
        }
    }

    /// Ports the header `Row` of `ReviewQuestionCard`: the index badge, the
    /// verdict with its score delta, and the chevron that drives `expanded`.
    private func questionHeader(index: Int, item: ReviewQuestionItem, isExpanded: Bool) -> some View {
        let tint = item.isCorrect ? AppTheme.Palette.success : AppTheme.Palette.danger

        return HStack(alignment: .center, spacing: AppTheme.Spacing.md) {
            Text("\(index)")
                .font(AppTheme.Font.callout.weight(.bold))
                .foregroundStyle(AppTheme.Palette.textPrimary)
                .frame(width: 42, height: 42)
                .background(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.md, style: .continuous)
                        .fill(tint)
                )

            VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
                Text(item.verdictTitle)
                    .font(AppTheme.Font.callout.weight(.bold))
                    .foregroundStyle(tint)
                Text(item.scoreLine)
                    .font(AppTheme.Font.caption2)
                    .foregroundStyle(AppTheme.Palette.textMuted)
            }

            Spacer(minLength: 0)

            Button {
                toggleExpansion(for: item)
            } label: {
                Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                    .font(AppTheme.Font.callout.weight(.bold))
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                    .frame(width: 32, height: 32)
                    .background(Circle().fill(AppTheme.Palette.cardBackgroundElevated))
            }
            .buttonStyle(.plain)
            .accessibilityLabel(isExpanded ? "Collapse options" : "Expand options")
        }
    }

    /// Ports the `AsyncImage` block of `ReviewQuestionCard`. Coil's crossfade
    /// and `ContentScale.Crop` become SwiftUI's built-in `AsyncImage` plus
    /// `scaledToFill`; the fixed height is kept so a tall figure cannot push the
    /// answer boxes off screen.
    @ViewBuilder
    private func questionImage(for item: ReviewQuestionItem) -> some View {
        if let url = item.resolvedImageURL {
            AsyncImage(url: url) { phase in
                switch phase {
                case .success(let image):
                    image
                        .resizable()
                        .scaledToFill()
                        .frame(height: 200)
                        .clipped()
                        .clipShape(
                            RoundedRectangle(cornerRadius: AppTheme.Radius.lg, style: .continuous)
                        )
                case .failure:
                    EmptyView()
                default:
                    ProgressView()
                        .frame(maxWidth: .infinity)
                        .frame(height: 200)
                }
            }
        }
    }

    /// Ports `ReviewAnswerBox`: a rounded block with a translucent caption above
    /// the semi-bold answer line, whose height follows the text
    /// (`overflow = TextOverflow.Visible`).
    private func answerBox(title: String, answer: String, tint: Color) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
            Text(title)
                .font(AppTheme.Font.caption2.weight(.bold))
                .foregroundStyle(AppTheme.Palette.textPrimary.opacity(0.7))
            Text(answer)
                .font(AppTheme.Font.callout.weight(.semibold))
                .foregroundStyle(AppTheme.Palette.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(AppTheme.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.materialCard, style: .continuous)
                .fill(tint.opacity(0.22))
        )
    }

    /// Ports the `AnimatedVisibility(visible = expanded)` block: "All Options",
    /// the explanation card and the Ask AI button.
    private func expandedSection(for item: ReviewQuestionItem) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
            Text("All Options")
                .font(AppTheme.Font.callout.weight(.bold))
                .foregroundStyle(AppTheme.Palette.textPrimary)

            VStack(spacing: AppTheme.Spacing.xs) {
                ForEach(item.optionPairs) { option in
                    optionRow(option: option, item: item)
                }
            }

            if !item.explanation.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                explanationCard(item.explanation)
            }

            askAIButton(for: item)
        }
        .transition(.opacity.combined(with: .move(edge: .top)))
    }

    /// Ports the per-option `Row` of `ReviewQuestionCard`. The correct key wins
    /// first; a selected key that is not the correct one is marked wrong;
    /// everything else stays neutral.
    @ViewBuilder
    private func optionRow(option: ReviewQuestionItem.ReviewOption, item: ReviewQuestionItem) -> some View {
        let correctKey = item.correct_option.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        let selectedKey = item.selected_option.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        let isCorrectOption = option.key == correctKey
        let isPickedWrong = option.key == selectedKey && option.key != correctKey
        let tint = isCorrectOption
            ? AppTheme.Palette.success
            : (isPickedWrong ? AppTheme.Palette.danger : AppTheme.Palette.cardBackgroundElevated)

        HStack(alignment: .center, spacing: AppTheme.Spacing.md) {
            Text(option.key)
                .font(AppTheme.Font.caption.weight(.bold))
                .foregroundStyle(AppTheme.Palette.textPrimary)
                .frame(width: 30, height: 30)
                .background(Circle().fill(AppTheme.Palette.textPrimary.opacity(0.12)))

            Text(option.text)
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Palette.textPrimary)
                .fixedSize(horizontal: false, vertical: true)

            Spacer(minLength: 0)

            if isCorrectOption {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(AppTheme.Palette.success)
            } else if isPickedWrong {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundStyle(AppTheme.Palette.warning)
            }
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(tint.opacity(0.35))
        )
        .animation(.spring(response: 0.35, dampingFraction: 0.6), value: tint)
    }

    /// Ports the `Explanation` card nested inside the expanded section.
    private func explanationCard(_ explanation: String) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            Text("Explanation")
                .font(AppTheme.Font.callout.weight(.bold))
                .foregroundStyle(AppTheme.Palette.textPrimary)
            Text(explanation)
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Palette.textSecondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(AppTheme.Spacing.lg)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.materialCard, style: .continuous)
                .fill(AppTheme.Palette.cardBackgroundElevated)
        )
    }

    /// Ports the "💬 Ask AI Medical Tutor" `Button`. Android handed
    /// `AiChatDialogHelper.openAskAiDialog` the question id, stem, A..D options,
    /// the resolved correct answer and the explanation; iOS opens the ported
    /// ``AskAiSheet``. The empty-stem guard is the same Toast Kotlin raised
    /// ("No question available"), surfaced here as an alert.
    private func askAIButton(for item: ReviewQuestionItem) -> some View {
        Button {
            guard !item.question.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                errorMessage = "No question available"
                return
            }
            askAIItem = item
        } label: {
            Text("💬 Ask AI Medical Tutor")
                .font(AppTheme.Font.callout.weight(.bold))
                .frame(maxWidth: .infinity)
                .padding(.vertical, AppTheme.Spacing.md)
                .background(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.option, style: .continuous)
                        .fill(AppTheme.Palette.primary)
                )
                .foregroundStyle(AppTheme.Palette.onPrimary)
        }
        .buttonStyle(.plain)
    }

    /// Ports the `AiChatDialogHelper.openAskAiDialog(questionId, question,
    /// options, correctAnswer, explanation)` payload. ``AskAiSheet`` takes a
    /// ``Question``, so the flat review row is re-shaped into the backend's
    /// question payload — including Android's A..D-only option list — and run
    /// through ``Question``'s own lenient decoder.
    private func askAIQuestion(for item: ReviewQuestionItem) -> Question? {
        var payload: [String: Any] = [
            "question_id": item.question_id,
            "question": item.question,
            "options": item.askAIOptions,
            "correct_option": item.correct_option,
            "explanation": item.explanation.isEmpty ? item.correct_answer_text : item.explanation
        ]
        if let imageURL = item.resolvedImageURL, let absolute = imageURL.absoluteString {
            payload["image_url"] = absolute
        }
        guard let data = try? JSONSerialization.data(withJSONObject: payload) else { return nil }
        return try? JSONDecoder().decode(Question.self, from: data)
    }

    // MARK: - State

    private func toggleExpansion(for item: ReviewQuestionItem) {
        if expandedQuestionIds.contains(item.id) {
            expandedQuestionIds.remove(item.id)
        } else {
            expandedQuestionIds.insert(item.id)
        }
    }

    // MARK: - Empty states

    /// Ports the `if (reviewList.isEmpty())` branch of `ReviewScreen`.
    private var noReviewDataState: some View {
        CardContainer {
            VStack(spacing: AppTheme.Spacing.sm) {
                Text("No Review Data Found")
                    .font(AppTheme.Font.title3)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                Text("Questions you attempt will appear here.")
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Palette.textSecondary)
                    .multilineTextAlignment(.center)
            }
            .frame(maxWidth: .infinity)
            .padding(AppTheme.Spacing.xxl)
        }
    }

    /// Reached only when the filter hides every row — an iOS addition.
    private var emptyState: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            Image(systemName: "line.3.horizontal.decrease.circle")
                .font(.system(size: 34))
                .foregroundStyle(AppTheme.Palette.textMuted)
                .padding(.top, AppTheme.Spacing.xxl)
            Text("No questions in this filter")
                .font(AppTheme.Font.headline)
                .foregroundStyle(AppTheme.Palette.textPrimary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, AppTheme.Spacing.xxl)
    }
}