import SwiftUI

/// The MCQ test runner. Ports `QuizViewerActivity` / `MCQActivity` / `TestActivity`.
struct QuizView: View {

    let quiz: Quiz

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @Environment(\.dismiss) private var dismiss

    @StateObject private var viewModel: QuizViewModel
    @State private var isConfirmingSubmit = false

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
                    }
                }
                .padding(AppTheme.Spacing.md)
            }

            footer
        }
        .screenBackground()
    }

    // MARK: - Header

    private var header: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            HStack {
                Text("Question \(viewModel.currentIndex + 1) of \(viewModel.questions.count)")
                    .font(AppTheme.Font.caption.weight(.medium))
                    .foregroundStyle(AppTheme.Palette.textSecondary)

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

    // MARK: - Question

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

    /// Uses `OptionRow`, which ports `PrepLadderOptionStyle` +
    /// `option_selector_rounded` (12dp radius, 16dp padding, 16sp text and a
    /// 2dp `@color/primary` stroke when checked).
    private func optionsList(_ question: Question) -> some View {
        VStack(spacing: 0) {
            ForEach(Array(question.options.enumerated()), id: \.offset) { index, option in
                OptionRow(
                    text: option,
                    index: index,
                    isSelected: viewModel.selectedIndex(for: question) == index
                ) {
                    viewModel.answer(selectedIndex: index, question: question)
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
