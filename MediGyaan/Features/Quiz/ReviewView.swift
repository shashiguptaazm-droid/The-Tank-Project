import SwiftUI

/// Review question data model mirroring `ReviewQuestionModel` in Android `ReviewActivity.kt`
public struct ReviewQuestionItem: Identifiable, Codable, Hashable {
    public var id: Int { question_id }
    public let question_id: Int
    public let question: String
    public let option_a: String
    public let option_b: String
    public let option_c: String
    public let option_d: String
    public let option_e: String
    public let selected_option: String
    public let correct_option: String
    public let selected_answer_text: String
    public let correct_answer_text: String
    public let score_change: Int
    public let explanation: String
    public let image_url: String
    public let is_correct: Int

    public init(
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
}

/// Detailed performance breakdown and answer analysis.
/// 1:1 port of Android `ReviewActivity.kt` and `ReviewAdapter.kt`.
public struct ReviewView: View {

    public let questions: [ReviewQuestionItem]
    @Environment(\.dismiss) private var dismiss

    @State private var filter: FilterMode = .all
    @State private var expandedQuestionIds: Set<Int> = []

    public enum FilterMode: String, CaseIterable {
        case all = "All"
        case correct = "Correct"
        case wrong = "Incorrect"
    }

    public init(questions: [ReviewQuestionItem]) {
        self.questions = questions
    }

    public init(reviewJson: String) {
        guard let data = reviewJson.data(using: .utf8),
              let decoded = try? JSONDecoder().decode([ReviewQuestionItem].self, from: data) else {
            self.questions = []
            return
        }
        self.questions = decoded
    }

    private var totalQuestions: Int { questions.count }
    private var correctCount: Int { questions.filter { $0.is_correct == 1 }.count }
    private var wrongCount: Int { totalQuestions - correctCount }
    private var accuracy: Int {
        guard totalQuestions > 0 else { return 0 }
        return Int((Double(correctCount) / Double(totalQuestions)) * 100)
    }

    private var filteredQuestions: [ReviewQuestionItem] {
        switch filter {
        case .all:
            return questions
        case .correct:
            return questions.filter { $0.is_correct == 1 }
        case .wrong:
            return questions.filter { $0.is_correct != 1 }
        }
    }

    public var body: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.md) {
                summaryHeader
                filterChips

                if filteredQuestions.isEmpty {
                    emptyState
                } else {
                    LazyVStack(spacing: AppTheme.Spacing.md) {
                        ForEach(Array(filteredQuestions.enumerated()), id: \.element.id) { index, item in
                            questionCard(index: index + 1, item: item)
                        }
                    }
                }
            }
            .padding(AppTheme.Spacing.md)
        .onAppear {
            RemoteLogger.log(tag: "ReviewView_Open", message: "User opened Exam Question Review screen")
        }
        }
        .screenBackground()
        .navigationTitle("Review Answers")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button("Done") { dismiss() }
            }
        }
    }

    // MARK: - Summary Header
    private var summaryHeader: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Performance Breakdown")
                            .font(AppTheme.Font.headline)
                            .foregroundStyle(Color.white)
                        Text("Detailed accuracy & rationales")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.textMuted)
                    }
                    Spacer()
                    Text("\(accuracy)%")
                        .font(.system(size: 26, weight: .bold, design: .rounded))
                        .foregroundStyle(accuracy >= 60 ? AppTheme.Palette.success : AppTheme.Palette.warning)
                }

                // Progress Bar
                GeometryReader { geo in
                    ZStack(alignment: .leading) {
                        Capsule()
                            .fill(Color(white: 0.2))
                        Capsule()
                            .fill(
                                LinearGradient(
                                    colors: [Color(hex: "06B6D4"), Color(hex: "3B82F6")],
                                    startPoint: .leading,
                                    endPoint: .trailing
                                )
                            )
                            .frame(width: geo.size.width * CGFloat(Double(accuracy) / 100.0))
                    }
                }
                .frame(height: 8)
                .padding(.vertical, 4)

                // 3 Metric Tiles
                HStack(spacing: AppTheme.Spacing.sm) {
                    metricTile(title: "Correct", count: correctCount, color: AppTheme.Palette.success)
                    metricTile(title: "Wrong", count: wrongCount, color: AppTheme.Palette.error)
                    metricTile(title: "Total", count: totalQuestions, color: AppTheme.Palette.primary)
                }
            }
        }
    }

    private func metricTile(title: String, count: Int, color: Color) -> some View {
        VStack(spacing: 2) {
            Text("\(count)")
                .font(.system(size: 20, weight: .black))
                .foregroundStyle(Color.white)
            Text(title)
                .font(AppTheme.Font.caption2)
                .foregroundStyle(Color.white.opacity(0.8))
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                .fill(color.opacity(0.35))
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                        .stroke(color.opacity(0.6), lineWidth: 1)
                )
        )
    }

    // MARK: - Filters
    private var filterChips: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            ForEach(FilterMode.allCases, id: \.self) { mode in
                let isSelected = filter == mode
                Button {
                    filter == mode ? () : (filter = mode)
                } label: {
                    Text(mode.rawValue)
                        .font(AppTheme.Font.caption.weight(.semibold))
                        .padding(.horizontal, 14)
                        .padding(.vertical, 7)
                        .background(
                            Capsule().fill(isSelected ? AppTheme.Palette.primary : AppTheme.Palette.cardBackgroundElevated)
                        )
                        .foregroundStyle(isSelected ? Color.white : AppTheme.Palette.textSecondary)
                }
            }
            Spacer()
        }
    }

    // MARK: - Question Card
    private func questionCard(index: Int, item: ReviewQuestionItem) -> some View {
        let isCorrect = item.is_correct == 1
        let isExpanded = expandedQuestionIds.contains(item.id)

        return CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                // Header row
                HStack(alignment: .center, spacing: AppTheme.Spacing.sm) {
                    ZStack {
                        Circle()
                            .fill(isCorrect ? AppTheme.Palette.success : AppTheme.Palette.error)
                            .frame(width: 28, height: 28)
                        Text("\(index)")
                            .font(.system(size: 13, weight: .bold))
                            .foregroundStyle(Color.white)
                    }

                    VStack(alignment: .leading, spacing: 2) {
                        Text(isCorrect ? "Correct" : "Incorrect")
                            .font(AppTheme.Font.callout.weight(.bold))
                            .foregroundStyle(isCorrect ? AppTheme.Palette.success : AppTheme.Palette.error)
                        if item.score_change != 0 {
                            Text("\(item.score_change > 0 ? "+" : "")\(item.score_change) pts")
                                .font(AppTheme.Font.caption2)
                                .foregroundStyle(AppTheme.Palette.textMuted)
                        }
                    }

                    Spacer()

                    Image(systemName: isCorrect ? "checkmark.circle.fill" : "xmark.circle.fill")
                        .font(.title3)
                        .foregroundStyle(isCorrect ? AppTheme.Palette.success : AppTheme.Palette.error)
                }

                // Question text
                Text(item.question)
                    .font(AppTheme.Font.body.weight(.medium))
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                    .padding(.top, 4)

                // Optional clinical image
                if !item.image_url.isEmpty {
                    AsyncImage(url: URL(string: item.image_url.hasPrefix("http") ? item.image_url : "https://medigyaan.com/Neurons/\(item.image_url)")) { phase in
                        switch phase {
                        case .success(let image):
                            image
                                .resizable()
                                .scaledToFit()
                                .frame(maxHeight: 180)
                                .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.md))
                        case .failure:
                            EmptyView()
                        default:
                            ProgressView()
                                .frame(height: 100)
                        }
                    }
                }

                // Options list
                VStack(spacing: 6) {
                    optionRow(label: "A", text: item.option_a, item: item)
                    optionRow(label: "B", text: item.option_b, item: item)
                    optionRow(label: "C", text: item.option_c, item: item)
                    optionRow(label: "D", text: item.option_d, item: item)
                    if !item.option_e.isEmpty {
                        optionRow(label: "E", text: item.option_e, item: item)
                    }
                }
                .padding(.top, 4)

                // Explanation / Rationale section
                if !item.explanation.isEmpty {
                    Divider()
                        .padding(.vertical, 4)

                    Button {
                        if isExpanded {
                            expandedQuestionIds.remove(item.id)
                        } else {
                            expandedQuestionIds.insert(item.id)
                        }
                    } label: {
                        HStack {
                            Image(systemName: "lightbulb.fill")
                                .foregroundStyle(AppTheme.Palette.accent)
                            Text("Clinical Explanation")
                                .font(AppTheme.Font.caption.weight(.semibold))
                                .foregroundStyle(AppTheme.Palette.accent)
                            Spacer()
                            Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                                .font(.caption)
                                .foregroundStyle(AppTheme.Palette.textMuted)
                        }
                    }

                    if isExpanded {
                        Text(item.explanation)
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                            .padding(AppTheme.Spacing.sm)
                            .background(
                                RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                                    .fill(Color.white.opacity(0.04))
                            )
                            .transition(.opacity.combined(with: .move(edge: .top)))
                    }
                }
            }
        }
    }

    private func optionRow(label: String, text: String, item: ReviewQuestionItem) -> some View {
        guard !text.isEmpty else { return AnyView(EmptyView()) }

        let normalizedCorrect = item.correct_option.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        let normalizedUser = item.selected_option.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()

        let isTargetCorrect = (normalizedCorrect == label)
        let isUserChoice = (normalizedUser == label)

        var borderCol: Color = Color.clear
        var bgCol: Color = Color.white.opacity(0.03)

        if isTargetCorrect {
            borderCol = AppTheme.Palette.success
            bgCol = AppTheme.Palette.success.opacity(0.15)
        } else if isUserChoice && !isTargetCorrect {
            borderCol = AppTheme.Palette.error
            bgCol = AppTheme.Palette.error.opacity(0.15)
        }

        return AnyView(
            HStack(spacing: AppTheme.Spacing.sm) {
                Text(label)
                    .font(.system(size: 13, weight: .bold))
                    .foregroundStyle(isTargetCorrect ? AppTheme.Palette.success : (isUserChoice ? AppTheme.Palette.error : AppTheme.Palette.textSecondary))
                    .frame(width: 24, height: 24)
                    .background(
                        Circle().fill(Color.white.opacity(0.08))
                    )

                Text(text)
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Palette.textPrimary)

                Spacer()

                if isTargetCorrect {
                    Image(systemName: "checkmark")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(AppTheme.Palette.success)
                } else if isUserChoice {
                    Image(systemName: "xmark")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(AppTheme.Palette.error)
                }
            }
            .padding(.horizontal, AppTheme.Spacing.sm)
            .padding(.vertical, 8)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                    .fill(bgCol)
                    .overlay(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                            .stroke(borderCol, lineWidth: borderCol == .clear ? 0 : 1.5)
                    )
            )
        )
    }

    private var emptyState: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            Image(systemName: "checkmark.seal")
                .font(.system(size: 48))
                .foregroundStyle(AppTheme.Palette.textMuted)
                .padding(.top, 40)
            Text("No questions in this filter")
                .font(AppTheme.Font.headline)
                .foregroundStyle(AppTheme.Palette.textPrimary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 30)
    }
}