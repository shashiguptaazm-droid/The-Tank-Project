import SwiftUI

/// The MCQ test runner. Ports `QuizViewerActivity` / `MCQActivity` / `TestActivity`.
struct QuizView: View {

    let quiz: Quiz

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @Environment(\.dismiss) private var dismiss

    @StateObject private var viewModel: QuizViewModel
    @State private var isConfirmingSubmit = false
    @State private var isShowingShareSheet = false
    @State private var isShowingAskAiSheet = false
    @State private var isShowingJumpSheet = false

    init(quiz: Quiz) {
        self.quiz = quiz
        _viewModel = StateObject(wrappedValue: QuizViewModel(quiz: quiz))
    }

    var body: some View {
        Group {
            if let result = viewModel.result {
                QuizResultView(attempt: result) { dismiss() }
            } else {
                content
            }
        }
        .navigationTitle(quiz.title.isEmpty ? "Practice" : quiz.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar(.hidden, for: .tabBar)
        .toolbar(.visible, for: .navigationBar)
        .toolbar {
            ToolbarItemGroup(placement: .topBarTrailing) {
                if viewModel.currentQuestion != nil {
                    // Audio Reader (TTS)
                    Button {
                        viewModel.toggleAudio()
                    } label: {
                        Image(systemName: viewModel.isSpeaking ? "speaker.wave.3.fill" : "speaker.wave.2")
                            .foregroundStyle(viewModel.isSpeaking ? AppTheme.Palette.accent : AppTheme.Palette.primary)
                    }

                    // Ask AI Assistant
                    Button {
                        isShowingAskAiSheet = true
                    } label: {
                        Image(systemName: "brain.head.profile")
                            .foregroundStyle(AppTheme.Palette.primary)
                    }

                    // Share Question
                    Button {
                        isShowingShareSheet = true
                    } label: {
                        Image(systemName: "square.and.arrow.up")
                    }

                    // Question Grid Jump
                    Button {
                        isShowingJumpSheet = true
                    } label: {
                        Image(systemName: "square.grid.3x3")
                    }
                }
            }
        }
        .sheet(isPresented: $isShowingShareSheet) {
            if let question = viewModel.currentQuestion {
                QuestionShareSheet(question: question, userId: session.userId)
            }
        }
        .sheet(isPresented: $isShowingAskAiSheet) {
            if let question = viewModel.currentQuestion {
                AskAiSheet(question: question)
            }
        }
        .sheet(isPresented: $isShowingJumpSheet) {
            jumpGridSheet
        }
        .task {
            // `@StateObject` is built before the environment exists, so the API
            // client and session user are supplied here instead.
            if !viewModel.hasStarted {
                await viewModel.start(api: api, userId: session.userId)
            }
        }
        .interactiveDismissDisabled(viewModel.result == nil && !viewModel.questions.isEmpty)
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .idle, .loading:
            LoadingStateView(message: "Fetching questions…")

        case let .failed(message):
            ErrorStateView(message: message) {
                Task { await viewModel.start(api: api, userId: session.userId) }
            }

        case .loaded:
            if viewModel.questions.isEmpty {
                EmptyStateView(
                    title: "No questions found",
                    message: "This quiz has no questions published yet.",
                    systemImage: "questionmark.square.dashed"
                )
            } else {
                quizBody
            }
        }
    }

    private var quizBody: some View {
        VStack(spacing: 0) {
            header

            ScrollView {
                VStack(alignment: .leading, spacing: AppTheme.Spacing.lg) {
                    if let question = viewModel.currentQuestion {
                        questionCard(question)
                        optionsList(question)

                        // Explanation card appears once answered
                        if viewModel.isQuestionAnswered(question) {
                            explanationCard(question)
                        }
                    }
                }
                .padding(AppTheme.Spacing.md)
            }

            footer
        }
        .screenBackground()
    }

    // MARK: - Header with Gamification Badges

    private var header: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            HStack {
                Text("Question \(viewModel.currentIndex + 1) of \(viewModel.questions.count)")
                    .font(AppTheme.Font.caption.weight(.medium))
                    .foregroundStyle(AppTheme.Palette.textSecondary)

                // Combo streak badge
                if viewModel.combo > 1 {
                    HStack(spacing: 3) {
                        Text("🔥")
                        Text("\(viewModel.combo) Streak")
                            .font(.system(size: 11, weight: .bold))
                    }
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(Color.orange.opacity(0.18))
                    .foregroundStyle(Color.orange)
                    .clipShape(Capsule())
                }

                // XP badge
                if viewModel.expEarned > 0 {
                    HStack(spacing: 3) {
                        Text("⭐")
                        Text("+\(viewModel.expEarned) XP")
                            .font(.system(size: 11, weight: .bold))
                    }
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(Color.blue.opacity(0.15))
                    .foregroundStyle(AppTheme.Palette.primary)
                    .clipShape(Capsule())
                }

                Spacer()

                HStack(spacing: AppTheme.Spacing.xxs) {
                    Image(systemName: "timer")
                    Text(viewModel.formattedTimeRemaining)
                        .monospacedDigit()
                }
                .font(AppTheme.Font.caption.weight(.semibold))
                .foregroundStyle(
                    viewModel.secondsRemaining <= 30
                        ? AppTheme.Palette.danger
                        : AppTheme.Palette.primary
                )
            }

            ProgressView(value: viewModel.progress)
                .tint(AppTheme.Palette.primary)
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, AppTheme.Spacing.sm)
        .background(AppTheme.Palette.cardBackground)
    }

    // MARK: - Question Card

    private func questionCard(_ question: Question) -> some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                if let imageURL = question.imageURL {
                    AsyncImage(url: imageURL) { image in
                        image.resizable().scaledToFit()
                    } placeholder: {
                        ProgressView()
                    }
                    .frame(maxHeight: 180)
                    .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.sm))
                }

                Text(question.text.isEmpty ? "Question" : question.text)
                    .font(AppTheme.Font.headline)
                    .fixedSize(horizontal: false, vertical: true)

                if !question.subject.isEmpty || !question.topic.isEmpty {
                    HStack(spacing: AppTheme.Spacing.xs) {
                        if !question.subject.isEmpty { TagBadge(text: question.subject) }
                        if !question.topic.isEmpty {
                            TagBadge(text: question.topic, tint: AppTheme.Palette.accent)
                        }
                    }
                }
            }
        }
    }

    // MARK: - Options List with Instant Review

    private func optionsList(_ question: Question) -> some View {
        VStack(spacing: 0) {
            ForEach(Array(question.options.enumerated()), id: \.offset) { index, option in
                OptionRow(
                    text: option,
                    index: index,
                    isSelected: viewModel.selectedIndex(for: question) == index,
                    reviewState: optionReviewState(for: question, index: index)
                ) {
                    viewModel.selectOption(index: index, question: question)
                }
            }
        }
    }

    private func optionReviewState(for question: Question, index: Int) -> OptionReviewState {
        guard let answer = viewModel.answers[question.id] else { return .neutral }
        if index == question.correctIndex {
            return .correct
        } else if index == answer.selectedIndex {
            return .wrong
        }
        return .neutral
    }

    // MARK: - Explanation Card

    private func explanationCard(_ question: Question) -> some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                HStack {
                    Label("Clinical Explanation", systemImage: "lightbulb.fill")
                        .font(.system(size: 15, weight: .bold))
                        .foregroundStyle(Color(hex: 0x2E_7D_32))

                    Spacer()

                    Button {
                        isShowingAskAiSheet = true
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: "brain.head.profile")
                            Text("Ask AI")
                        }
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(Color(hex: 0x39_49_AB))
                        .padding(.horizontal, 10)
                        .padding(.vertical, 4)
                        .background(Color(hex: 0xE8_EA_F6))
                        .clipShape(Capsule())
                    }
                }

                Text(question.explanation.isEmpty
                    ? "Correct option: \(question.correctOption ?? "A"). Review the topic thoroughly in your MediGyaan notes."
                    : question.explanation)
                    .font(AppTheme.Font.body)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)

                Divider()

                HStack {
                    Button {
                        isShowingShareSheet = true
                    } label: {
                        HStack(spacing: 6) {
                            Image(systemName: "square.and.arrow.up")
                            Text("Share MCQ Card")
                        }
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(AppTheme.Palette.primary)
                    }

                    Spacer()

                    Button {
                        viewModel.toggleAudio()
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: viewModel.isSpeaking ? "speaker.wave.3.fill" : "speaker.wave.2")
                            Text(viewModel.isSpeaking ? "Stop" : "Listen")
                        }
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                    }
                }
            }
        }
    }

    // MARK: - Jump Grid Sheet

    private var jumpGridSheet: some View {
        NavigationStack {
            ScrollView {
                LazyVGrid(
                    columns: Array(repeating: GridItem(.flexible(), spacing: 12), count: 5),
                    spacing: 12
                ) {
                    ForEach(Array(viewModel.questions.enumerated()), id: \.offset) { index, q in
                        let isAnswered = viewModel.isQuestionAnswered(q)
                        let isCorrect = viewModel.answers[q.id]?.isCorrect ?? false
                        let isCurrent = viewModel.currentIndex == index

                        Button {
                            viewModel.jump(to: index)
                            isShowingJumpSheet = false
                        } label: {
                            Text("\(index + 1)")
                                .font(.system(size: 15, weight: .bold))
                                .frame(maxWidth: .infinity)
                                .frame(height: 48)
                                .background(
                                    isAnswered
                                        ? (isCorrect ? AppTheme.Palette.success.opacity(0.18) : AppTheme.Palette.danger.opacity(0.18))
                                        : Color.primary.opacity(0.06)
                                )
                                .foregroundStyle(
                                    isAnswered
                                        ? (isCorrect ? AppTheme.Palette.success : AppTheme.Palette.danger)
                                        : AppTheme.Palette.textPrimary
                                )
                                .clipShape(RoundedRectangle(cornerRadius: 12))
                                .overlay(
                                    RoundedRectangle(cornerRadius: 12)
                                        .stroke(
                                            isCurrent ? AppTheme.Palette.primary : Color.clear,
                                            lineWidth: 2
                                        )
                                )
                        }
                    }
                }
                .padding()
            }
            .navigationTitle("Jump to Question")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { isShowingJumpSheet = false }
                }
            }
        }
    }

    // MARK: - Footer

    private var footer: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            HStack(spacing: AppTheme.Spacing.sm) {
                Button {
                    viewModel.goToPrevious()
                } label: {
                    Image(systemName: "chevron.left")
                        .frame(width: 44, height: 44)
                        .background(
                            RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                                .fill(Color.primary.opacity(0.08))
                        )
                }
                .disabled(viewModel.currentIndex == 0)
                .opacity(viewModel.currentIndex == 0 ? 0.4 : 1)

                if viewModel.isLastQuestion {
                    PrimaryButton(
                        title: "Submit Test",
                        isLoading: viewModel.isSubmitting,
                        isEnabled: viewModel.answeredCount > 0
                    ) {
                        isConfirmingSubmit = true
                    }
                } else {
                    PrimaryButton(title: "Next", isEnabled: true) {
                        viewModel.goToNext()
                    }
                }

                Button {
                    viewModel.goToNext()
                } label: {
                    Image(systemName: "chevron.right")
                        .frame(width: 44, height: 44)
                        .background(
                            RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                                .fill(Color.primary.opacity(0.08))
                        )
                }
                .disabled(viewModel.isLastQuestion)
                .opacity(viewModel.isLastQuestion ? 0.4 : 1)
            }

            Text("\(viewModel.answeredCount) of \(viewModel.questions.count) answered")
                .font(AppTheme.Font.caption)
                .foregroundStyle(AppTheme.Palette.textSecondary)
        }
        .padding(AppTheme.Spacing.md)
        .background(AppTheme.Palette.cardBackground)
        .confirmationDialog(
            "Submit your test?",
            isPresented: $isConfirmingSubmit,
            titleVisibility: .visible
        ) {
            Button("Submit", role: .destructive) {
                Task { await viewModel.finish() }
            }
            Button("Keep practising", role: .cancel) {}
        } message: {
            Text("You've answered \(viewModel.answeredCount) of \(viewModel.questions.count) questions.")
        }
    }
}

/// Result summary shown after a test completes.
struct QuizResultView: View {

    let attempt: QuizAttempt
    let onDone: () -> Void

    var body: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.lg) {
                VStack(spacing: AppTheme.Spacing.sm) {
                    ZStack {
                        Circle()
                            .stroke(AppTheme.Palette.primary.opacity(0.15), lineWidth: 12)
                        Circle()
                            .trim(from: 0, to: max(0.001, attempt.accuracy))
                            .stroke(
                                attempt.accuracy >= 0.6
                                    ? AppTheme.Palette.success
                                    : AppTheme.Palette.warning,
                                style: StrokeStyle(lineWidth: 12, lineCap: .round)
                            )
                            .rotationEffect(.degrees(-90))

                        VStack(spacing: 0) {
                            Text(String(format: "%.0f%%", attempt.accuracy * 100))
                                .font(.system(size: 32, weight: .bold, design: .rounded))
                            Text("accuracy")
                                .font(AppTheme.Font.caption)
                                .foregroundStyle(AppTheme.Palette.textSecondary)
                        }
                    }
                    .frame(width: 150, height: 150)
                    .padding(.top, AppTheme.Spacing.lg)

                    Text(attempt.quizTitle.isEmpty ? "Test complete" : attempt.quizTitle)
                        .font(AppTheme.Font.title)
                        .multilineTextAlignment(.center)

                    Text("Finished in \(attempt.durationSeconds / 60)m \(attempt.durationSeconds % 60)s")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }

                LazyVGrid(
                    columns: Array(repeating: GridItem(.flexible(), spacing: AppTheme.Spacing.sm), count: 3),
                    spacing: AppTheme.Spacing.sm
                ) {
                    StatTile(
                        value: "\(attempt.attempted)",
                        label: "Attempted",
                        systemImage: "checklist",
                        tint: AppTheme.Palette.info
                    )
                    StatTile(
                        value: "\(attempt.correct)",
                        label: "Correct",
                        systemImage: "checkmark.circle.fill",
                        tint: AppTheme.Palette.success
                    )
                    StatTile(
                        value: "\(attempt.wrong)",
                        label: "Wrong",
                        systemImage: "xmark.circle.fill",
                        tint: AppTheme.Palette.danger
                    )
                }
                .padding(.horizontal, AppTheme.Spacing.md)

                VStack(spacing: AppTheme.Spacing.sm) {
                    PrimaryButton(title: "Done") { onDone() }
                }
                .padding(.horizontal, AppTheme.Spacing.md)
            }
            .padding(.bottom, AppTheme.Spacing.lg)
        }
        .screenBackground()
        .navigationBarBackButtonHidden(true)
    }
}

#Preview {
    NavigationStack {
        QuizView(quiz: Quiz(id: 1, title: "Anatomy Basics", questionCount: 5, durationSeconds: 300))
            .environmentObject(SessionStore())
            .environment(\.api, .live)
    }
}
