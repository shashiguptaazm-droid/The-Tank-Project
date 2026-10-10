import SwiftUI

/// The MCQ test runner. Ports `QuizViewerActivity` / `MCQActivity` / `TestActivity`.
///
/// Also hosts the **single player test mode** ported from `SinglePlayer.kt`
/// (`SinglePlayerTestModeActivity` / `SinglePlayerTestModeScreen`), which is
/// entered by passing a ``SinglePlayerSeries``. Callers that omit it keep the
/// original MCQ behaviour and signature.
struct QuizView: View {

    let quiz: Quiz

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @Environment(\.dismiss) private var dismiss
    @Environment(\.scenePhase) private var scenePhase

    @StateObject private var viewModel: QuizViewModel
    @State private var isConfirmingSubmit = false
    @State private var isShowingShareSheet = false
    @State private var isShowingAskAiSheet = false
    @State private var isShowingJumpSheet = false
    @State private var selectedFullscreenImage: URL? = nil

    init(quiz: Quiz, singlePlayerSeries: SinglePlayerSeries? = nil) {
        self.quiz = quiz
        _viewModel = StateObject(wrappedValue: QuizViewModel(quiz: quiz, singlePlayerSeries: singlePlayerSeries))
    }

    var body: some View {
        Group {
            if viewModel.isSinglePlayerMode {
                singlePlayerRoot
            } else if let result = viewModel.result {
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
            ToolbarItem(placement: .topBarLeading) {
                Button {
                    dismiss()
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundStyle(AppTheme.Palette.textPrimary)
                }
            }

            ToolbarItemGroup(placement: .topBarTrailing) {
                if viewModel.activeQuestion != nil {
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

                    // Question Grid Jump (MCQ pool only — single-player runs hold one question at a time)
                    if !viewModel.isSinglePlayerMode {
                        Button {
                            isShowingJumpSheet = true
                        } label: {
                            Image(systemName: "square.grid.3x3")
                        }
                    }
                }
            }
        }
        .sheet(isPresented: $isShowingShareSheet) {
            if let question = viewModel.activeQuestion {
                QuestionShareSheet(question: question, userId: session.userId)
            }
        }
        .sheet(isPresented: $isShowingAskAiSheet) {
            if let question = viewModel.activeQuestion {
                AskAiSheet(question: question)
            }
        }
        .sheet(isPresented: $isShowingJumpSheet) {
            jumpGridSheet
        }
        .fullScreenCover(isPresented: Binding(
            get: { selectedFullscreenImage != nil },
            set: { if !$0 { selectedFullscreenImage = nil } }
        )) {
            if let url = selectedFullscreenImage {
                FullScreenImageView(imageURL: url)
            }
        }
        .task {
            // `@StateObject` is built before the environment exists, so the API
            // client and session user are supplied here instead.
            RemoteLogger.log(tag: "QuizView_task", message: "QuizView task running, hasStarted=\(viewModel.hasStarted)")
            if !viewModel.hasStarted {
                await viewModel.start(api: api, userId: session.userId)
            }
        }
        .onAppear {
            RemoteLogger.log(tag: "QuizView_onAppear", message: "QuizView appeared on screen")
        }
        .onChange(of: scenePhase) { phase in
            // Ports the ON_RESUME branch of SinglePlayer.kt's LifecycleEventObserver.
            if phase == .active {
                viewModel.registerSeriesBackgroundResume()
            }
        }
        .errorAlert(message: $viewModel.seriesErrorMessage)
        .interactiveDismissDisabled(viewModel.result == nil && !viewModel.questions.isEmpty && !viewModel.isSinglePlayerMode)
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
                    } else if viewModel.isLoadingQuestion {
                        LoadingStateView(message: "Loading question…")
                            .frame(maxWidth: .infinity, minHeight: 200)
                    }
                }
                .padding(AppTheme.Spacing.md)
            }

            footer
        }
        .screenBackground()
    }

    // MARK: - Single player test mode (SinglePlayer.kt)

    /// Ports the top-level `if (finished)` split of `SinglePlayerTestModeScreen`.
    @ViewBuilder
    private var singlePlayerRoot: some View {
        if viewModel.isSeriesFinished {
            SinglePlayerResultView(
                uniqueId: viewModel.seriesUniqueId,
                score: viewModel.seriesScore,
                maxScore: viewModel.seriesMaxScore,
                correctPoints: viewModel.seriesCorrectPoints,
                wrongPoints: viewModel.seriesWrongPoints,
                correctCount: viewModel.seriesCorrectCount,
                wrongCount: viewModel.seriesWrongCount,
                attemptedCount: viewModel.seriesAttemptedCount,
                totalLoaded: viewModel.seriesQuestionIds.count,
                reviewItems: viewModel.seriesReviewItems,
                isRestartNoticeVisible: viewModel.seriesRestartNotice,
                onExit: { dismiss() },
                onRestart: { viewModel.seriesRestartNotice = true }
            )
        } else {
            singlePlayerBody
        }
    }

    private var singlePlayerBody: some View {
        VStack(spacing: 0) {
            singlePlayerHeader

            ScrollView {
                VStack(alignment: .leading, spacing: AppTheme.Spacing.lg) {
                    singlePlayerBattleSummary

                    if viewModel.isSeriesPenalized && !viewModel.isSeriesAnswerLocked {
                        singlePlayerPenaltyNotice
                    }

                    singlePlayerQuestionArea

                    if viewModel.isSeriesFeedbackVisible {
                        singlePlayerFeedbackCard
                    }

                    singlePlayerFooter

                    Text(
                        "Max score: \(viewModel.seriesMaxScore) • "
                        + "\(viewModel.seriesCorrectPoints) correct • \(viewModel.seriesWrongPoints) wrong"
                    )
                    .font(AppTheme.Font.micro)
                    .foregroundStyle(AppTheme.Palette.textSecondary)
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                }
                .padding(AppTheme.Spacing.lg)
            }
        }
        .screenBackground()
    }

    /// Ports `TopHeader` — the three metric chips and the score meter.
    private var singlePlayerHeader: some View {
        VStack(spacing: AppTheme.Spacing.md) {
            HStack(alignment: .top, spacing: AppTheme.Spacing.sm) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Single Player Test Mode")
                        .font(AppTheme.Font.title3)
                        .foregroundStyle(AppTheme.Palette.textPrimary)
                    Text("Unique ID: \(viewModel.seriesUniqueId) • Same series for every user")
                        .font(AppTheme.Font.micro)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }
                Spacer(minLength: 0)
                Button {
                    viewModel.finishSeriesEarly()
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundStyle(AppTheme.Palette.textPrimary)
                        .padding(AppTheme.Spacing.sm)
                        .background(Circle().fill(AppTheme.Palette.cardBackgroundElevated))
                }
            }

            HStack(spacing: AppTheme.Spacing.sm) {
                singlePlayerMetricChip(title: "Progress", value: viewModel.seriesProgressText)
                singlePlayerMetricChip(
                    title: "Score",
                    value: "\(viewModel.seriesScore) / \(viewModel.seriesMaxScore)"
                )
                singlePlayerMetricChip(title: "Total EXP", value: "⭐ \(viewModel.seriesExp)")
            }

            ProgressRow(
                title: "Score Meter",
                value: viewModel.seriesScoreRatio,
                tint: AppTheme.Palette.primary,
                caption: "\(Int(viewModel.seriesScoreRatio * 100))%"
            )
        }
        .padding(.horizontal, AppTheme.Spacing.lg)
        .padding(.vertical, AppTheme.Spacing.md)
        .background(AppTheme.Palette.cardBackground)
    }

    /// Ports `MetricChip`.
    private func singlePlayerMetricChip(title: String, value: String) -> some View {
        VStack(spacing: AppTheme.Spacing.xxs) {
            Text(title)
                .font(AppTheme.Font.micro.weight(.semibold))
                .foregroundStyle(AppTheme.Palette.textSecondary)
            Text(value)
                .font(AppTheme.Font.bodyBold)
                .foregroundStyle(AppTheme.Palette.textPrimary)
                .lineLimit(1)
                .minimumScaleFactor(0.6)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, AppTheme.Spacing.sm)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AppTheme.Palette.cardBackgroundElevated)
        )
    }

    /// Ports `BattleSummaryCard` — collapsed until tapped.
    private var singlePlayerBattleSummary: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
            Button {
                viewModel.toggleSeriesSummary()
            } label: {
                HStack {
                    Text("Battle Summary")
                        .font(AppTheme.Font.headline)
                        .foregroundStyle(AppTheme.Palette.textPrimary)
                    Spacer()
                    Image(
                        systemName: viewModel.isSeriesSummaryExpanded ? "chevron.up" : "chevron.down"
                    )
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                }
            }
            .buttonStyle(.plain)

            if viewModel.isSeriesSummaryExpanded {
                VStack(spacing: AppTheme.Spacing.sm) {
                    HStack(spacing: AppTheme.Spacing.xs) {
                        singlePlayerSummaryPill(
                            title: "Loaded",
                            value: "\(viewModel.seriesQuestionIds.count)",
                            tint: AppTheme.Palette.info
                        )
                        singlePlayerSummaryPill(
                            title: "Attempted",
                            value: "\(viewModel.seriesAttemptedCount)",
                            tint: AppTheme.Palette.textSecondary
                        )
                        singlePlayerSummaryPill(
                            title: "Correct",
                            value: "\(viewModel.seriesCorrectCount)",
                            tint: AppTheme.Palette.success
                        )
                    }
                    HStack(spacing: AppTheme.Spacing.xs) {
                        singlePlayerSummaryPill(
                            title: "Wrong",
                            value: "\(viewModel.seriesWrongCount)",
                            tint: AppTheme.Palette.danger
                        )
                        singlePlayerSummaryPill(
                            title: "Remaining",
                            value: "\(viewModel.seriesRemainingCount)",
                            tint: AppTheme.Palette.textPrimary
                        )
                    }
                }
            }
        }
        .padding(AppTheme.Spacing.lg)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AppTheme.Palette.cardBackground)
        )
    }

    /// Ports `SummaryPill`.
    private func singlePlayerSummaryPill(title: String, value: String, tint: Color) -> some View {
        HStack(spacing: AppTheme.Spacing.xxs) {
            Text("\(title): ")
                .font(AppTheme.Font.micro.weight(.semibold))
            Text(value)
                .font(AppTheme.Font.captionBold)
        }
        .foregroundStyle(tint)
        .padding(.horizontal, AppTheme.Spacing.sm)
        .padding(.vertical, AppTheme.Spacing.xs)
        .background(Capsule().fill(tint.opacity(0.15)))
    }

    /// Ports `PenaltyNotice`.
    private var singlePlayerPenaltyNotice: some View {
        HStack(alignment: .top, spacing: AppTheme.Spacing.md) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 20))
                .foregroundStyle(AppTheme.Palette.danger)
            VStack(alignment: .leading, spacing: 2) {
                Text("Background Penalty: -1 Point")
                    .font(AppTheme.Font.callout.weight(.bold))
                    .foregroundStyle(AppTheme.Palette.danger)
                Text("Leaving the app during an active question results in a point deduction.")
                    .font(AppTheme.Font.micro)
                    .foregroundStyle(AppTheme.Palette.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 0)
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AppTheme.Palette.danger.opacity(0.12))
        )
        .overlay(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .stroke(AppTheme.Palette.danger, lineWidth: 1)
        )
    }

    /// Ports the `LoadingCard` / `QuestionCard` branch of the runner.
    @ViewBuilder
    private var singlePlayerQuestionArea: some View {
        if viewModel.isLoadingSeriesIds {
            LoadingStateView(message: "Loading your test series…")
                .frame(maxWidth: .infinity, minHeight: 220)
        } else if let question = viewModel.seriesQuestion {
            singlePlayerQuestionCard(question)
            singlePlayerOptionsList(question)
        } else if viewModel.seriesQuestionIds.isEmpty {
            EmptyStateView(
                title: "No questions found",
                message: "This test series has no questions published yet.",
                systemImage: "questionmark.square.dashed"
            )
        } else {
            LoadingStateView(message: "Loading question…")
                .frame(maxWidth: .infinity, minHeight: 220)
        }
    }

    private func singlePlayerQuestionCard(_ question: Question) -> some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                HStack {
                    Text("QUESTION \(viewModel.currentIndex + 1)")
                        .font(AppTheme.Font.captionBold)
                        .foregroundStyle(AppTheme.Palette.primary)
                    Spacer()
                    Text("\(viewModel.currentIndex + 1) / \(viewModel.seriesQuestionCap)")
                        .font(AppTheme.Font.caption.weight(.semibold))
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }

                Text(question.text.isEmpty ? "Question" : question.text)
                    .font(AppTheme.Font.body)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)

                if let imageURL = question.imageURL {
                    Button {
                        selectedFullscreenImage = imageURL
                    } label: {
                        AsyncImage(url: imageURL) { phase in
                            switch phase {
                            case .empty:
                                ProgressView()
                                    .frame(maxWidth: .infinity, minHeight: 160)
                            case .success(let image):
                                image
                                    .resizable()
                                    .scaledToFit()
                                    .frame(maxWidth: .infinity, maxHeight: 220)
                                    .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.md))
                            case .failure:
                                Label("Image could not be loaded", systemImage: "photo.badge.exclamationmark")
                                    .font(AppTheme.Font.caption)
                                    .foregroundStyle(AppTheme.Palette.textSecondary)
                                    .frame(maxWidth: .infinity, minHeight: 80)
                            @unknown default:
                                EmptyView()
                            }
                        }
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private func singlePlayerOptionsList(_ question: Question) -> some View {
        VStack(spacing: 0) {
            ForEach(Array(question.options.enumerated()), id: \.offset) { index, option in
                OptionRow(
                    text: option,
                    index: index,
                    isSelected: viewModel.seriesDraftIndex == index,
                    reviewState: singlePlayerReviewState(for: question, index: index)
                ) {
                    viewModel.selectSeriesOption(index: index)
                }
            }
        }
    }

    /// Ports `QuizOption`'s four-way colour rule: green on the locked correct
    /// option, red on a locked wrong pick, otherwise neutral.
    private func singlePlayerReviewState(for question: Question, index: Int) -> OptionReviewState {
        guard viewModel.isSeriesAnswerLocked else { return .neutral }
        if index == question.correctIndex { return .correct }
        if index == viewModel.seriesDraftIndex { return .wrong }
        return .neutral
    }

    /// Ports `FeedbackCard`.
    private var singlePlayerFeedbackCard: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                Label(
                    viewModel.seriesFeedbackTitle,
                    systemImage: viewModel.seriesFeedbackIsCorrect ? "checkmark.circle.fill" : "xmark.circle.fill"
                )
                .font(AppTheme.Font.headline)
                .foregroundStyle(
                    viewModel.seriesFeedbackIsCorrect ? AppTheme.Palette.success : AppTheme.Palette.danger
                )
                Text(viewModel.seriesFeedbackText)
                    .font(AppTheme.Font.body)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    /// Ports the Previous / Submit-or-Next / Finish Early row.
    private var singlePlayerFooter: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            HStack(spacing: AppTheme.Spacing.md) {
                SecondaryButton(title: "Previous", systemImage: "chevron.left") {
                    viewModel.goToPreviousSeriesQuestion()
                }
                .disabled(viewModel.currentIndex == 0 || viewModel.isSeriesAnswerLocked)
                .opacity(viewModel.currentIndex == 0 || viewModel.isSeriesAnswerLocked ? 0.4 : 1)

                if viewModel.seriesOffersNextButton {
                    PrimaryButton(title: "Next") {
                        viewModel.goToNextSeriesQuestion()
                    }
                } else {
                    PrimaryButton(
                        title: viewModel.isSeriesAnswerLocked ? "Submitted" : "Submit",
                        isEnabled: !viewModel.isSeriesAnswerLocked && viewModel.seriesDraftIndex != nil
                    ) {
                        Task { await viewModel.submitSeriesAnswer() }
                    }
                }
            }

            TextActionButton(title: "Finish Early") {
                viewModel.finishSeriesEarly()
            }
        }
    }

    // MARK: - Header with Gamification Badges

    private var header: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            HStack {
                Text("Question \(viewModel.currentIndex + 1) of \(viewModel.totalQuestionsCount)")
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

                if viewModel.secondsRemaining > 0 {
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
                } else {
                    HStack(spacing: 3) {
                        Image(systemName: "bolt.fill")
                            .font(.system(size: 10))
                        Text("Rapid Fire")
                            .font(.system(size: 11, weight: .bold))
                    }
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(Color.purple.opacity(0.15))
                    .foregroundStyle(Color.purple)
                    .clipShape(Capsule())
                }
            }

            ProgressView(value: viewModel.progress)
                .tint(AppTheme.Palette.primary)

            // In-Session Topic Selector Bar (matching Android MCQActivity topicSpinner)
            if !viewModel.topicsList.isEmpty {
                HStack {
                    Label(viewModel.selectedTopic, systemImage: "folder.fill")
                        .font(AppTheme.Font.caption.weight(.semibold))
                        .foregroundStyle(AppTheme.Palette.primary)
                        .lineLimit(1)

                    Spacer()

                    Menu {
                        ForEach(viewModel.topicsList, id: \.self) { topicName in
                            Button {
                                Task { await viewModel.selectTopic(topicName) }
                            } label: {
                                HStack {
                                    Text(topicName)
                                    if topicName == viewModel.selectedTopic {
                                        Image(systemName: "checkmark")
                                    }
                                }
                            }
                        }
                    } label: {
                        HStack(spacing: 4) {
                            Text("Switch Topic")
                                .font(AppTheme.Font.caption.weight(.bold))
                            Image(systemName: "chevron.up.chevron.down")
                                .font(.system(size: 10, weight: .bold))
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 5)
                        .background(Capsule().fill(AppTheme.Palette.primary.opacity(0.12)))
                        .foregroundStyle(AppTheme.Palette.primary)
                    }
                }
                .padding(.top, 2)
            }
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
                    Button {
                        selectedFullscreenImage = imageURL
                    } label: {
                        AsyncImage(url: imageURL) { phase in
                            switch phase {
                            case .empty:
                                HStack {
                                    Spacer()
                                    ProgressView()
                                    Spacer()
                                }
                                .frame(height: 180)
                                .background(Color.secondary.opacity(0.06))
                                .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.sm))
                            case .success(let image):
                                ZStack(alignment: .bottomTrailing) {
                                    image
                                        .resizable()
                                        .scaledToFit()
                                        .frame(maxWidth: .infinity, maxHeight: 280)
                                        .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.sm))

                                    HStack(spacing: 4) {
                                        Image(systemName: "plus.magnifyingglass")
                                            .font(.system(size: 10, weight: .bold))
                                        Text("Tap to zoom")
                                            .font(.system(size: 11, weight: .medium))
                                    }
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(.ultraThinMaterial)
                                    .clipShape(Capsule())
                                    .padding(8)
                                }
                            case .failure(let error):
                                HStack {
                                    Spacer()
                                    VStack(spacing: 6) {
                                        Image(systemName: "photo.badge.exclamationmark")
                                            .font(.system(size: 24))
                                        Text("Image could not be loaded")
                                            .font(AppTheme.Font.caption)
                                    }
                                    .foregroundStyle(AppTheme.Palette.textSecondary)
                                    .padding(.vertical, AppTheme.Spacing.md)
                                    Spacer()
                                }
                                .frame(maxWidth: .infinity)
                                .background(Color.secondary.opacity(0.06))
                                .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.sm))
                                .onAppear {
                                    RemoteLogger.log(
                                        tag: "Question_Image_Failed",
                                        message: "Failed to load image for Q#\(question.id) at URL: \(imageURL.absoluteString). Error: \(error.localizedDescription)"
                                    )
                                }
                            @unknown default:
                                EmptyView()
                            }
                        }
                    }
                    .buttonStyle(.plain)
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
                    let totalCount = viewModel.totalQuestionsCount
                    let itemsCount = min(totalCount, 200) // Render up to first 200 for smooth performance
                    ForEach(0..<itemsCount, id: \.self) { index in
                        let question = viewModel.questions.indices.contains(index) ? viewModel.questions[index] : nil
                        let isAnswered = question.map { viewModel.isQuestionAnswered($0) } ?? false
                        let isCorrect = question.flatMap { viewModel.answers[$0.id]?.isCorrect } ?? false
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

            Text("\(viewModel.answeredCount) of \(viewModel.totalQuestionsCount) answered")
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
                    if !attempt.answers.isEmpty {
                        NavigationLink {
                            ReviewView(questions: reviewQuestions(from: attempt))
                        } label: {
                            HStack {
                                Image(systemName: "list.bullet.clipboard")
                                Text("Review Answers")
                            }
                            .font(AppTheme.Font.headline)
                            .frame(maxWidth: .infinity)
                            .frame(height: 50)
                            .background(
                                RoundedRectangle(cornerRadius: AppTheme.Radius.md)
                                    .fill(AppTheme.Palette.cardBackgroundElevated)
                                    .overlay(
                                        RoundedRectangle(cornerRadius: AppTheme.Radius.md)
                                            .stroke(AppTheme.Palette.primary.opacity(0.4), lineWidth: 1)
                                    )
                            )
                            .foregroundStyle(Color.white)
                        }
                    }

                    PrimaryButton(title: "Done") { onDone() }
                }
                .padding(.horizontal, AppTheme.Spacing.md)
            }
            .padding(.bottom, AppTheme.Spacing.lg)
        }
        .screenBackground()
        .navigationBarBackButtonHidden(true)
    }

    private func reviewQuestions(from attempt: QuizAttempt) -> [ReviewQuestionItem] {
        return attempt.answers.map { ans in
            let letters = ["A", "B", "C", "D", "E"]
            let userLetter = letters.indices.contains(ans.selectedIndex) ? letters[ans.selectedIndex] : ""
            let correctLetter = letters.indices.contains(ans.correctIndex) ? letters[ans.correctIndex] : ""
            return ReviewQuestionItem(
                question_id: ans.questionId,
                question: "Question #\(ans.questionId)",
                option_a: "",
                option_b: "",
                option_c: "",
                option_d: "",
                option_e: "",
                selected_option: userLetter,
                correct_option: correctLetter,
                selected_answer_text: "",
                correct_answer_text: "",
                score_change: ans.isCorrect ? 1 : 0,
                explanation: "",
                image_url: "",
                is_correct: ans.isCorrect ? 1 : 0
            )
        }
    }
}

/// Ports `ResultScreen` / `ReviewQuestionCard` from `SinglePlayer.kt`: the
/// `score / 800` headline, the percentage ring, the collapsible review section
/// and the two exit affordances.
///
/// Reached only through ``QuizView``'s single-player branch, so the existing
/// ``QuizResultView`` and its call sites are untouched.
struct SinglePlayerResultView: View {

    let uniqueId: Int
    let score: Int
    let maxScore: Int
    let correctPoints: Int
    let wrongPoints: Int
    let correctCount: Int
    let wrongCount: Int
    let attemptedCount: Int
    let totalLoaded: Int
    let reviewItems: [ReviewQuestionItem]
    let isRestartNoticeVisible: Bool
    let onExit: () -> Void
    let onRestart: () -> Void

    @State private var isShowingReview = false
    @State private var isPresentingReview = false

    /// `score.coerceAtLeast(0)` — the ring itself uses the raw, possibly negative, score.
    private var displayScore: Int { max(0, score) }

    /// `((score / maxScore) * 100).coerceIn(0f, 100f)`.
    private var percentage: Double {
        guard maxScore > 0 else { return 0 }
        return min(max(Double(score) / Double(maxScore) * 100, 0), 100)
    }

    private var ringTint: Color {
        if percentage >= 75 { return AppTheme.Palette.success }
        if percentage >= 50 { return AppTheme.Palette.warning }
        return AppTheme.Palette.danger
    }

    var body: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.lg) {
                summaryCard

                performanceCard

                resultNotesCard

                if isRestartNoticeVisible {
                    Text("Restart by reopening this test")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }

                PrimaryButton(title: "Exit", icon: "rectangle.portrait.and.arrow.right", action: onExit)
                SecondaryButton(title: "Open Again", systemImage: "arrow.clockwise", action: onRestart)
            }
            .padding(AppTheme.Spacing.lg)
            .padding(.bottom, AppTheme.Spacing.xxl)
        }
        .screenBackground()
        .navigationBarBackButtonHidden(true)
        .sheet(isPresented: $isPresentingReview) {
            NavigationStack {
                ReviewView(questions: reviewItems)
            }
        }
    }

    // MARK: - Cards

    private var summaryCard: some View {
        CardContainer {
            VStack(spacing: AppTheme.Spacing.md) {
                Text("Test Completed")
                    .font(AppTheme.Font.title3)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                Text("Unique ID: \(uniqueId)")
                    .font(AppTheme.Font.micro)
                    .foregroundStyle(AppTheme.Palette.textSecondary)

                ZStack {
                    Circle()
                        .stroke(AppTheme.Palette.primary.opacity(0.15), lineWidth: 10)
                    Circle()
                        .trim(from: 0, to: max(0.001, percentage / 100))
                        .stroke(ringTint, style: StrokeStyle(lineWidth: 10, lineCap: .round))
                        .rotationEffect(.degrees(-90))
                    Text(String(format: "%.0f%%", percentage))
                        .font(.system(size: 26, weight: .bold, design: .rounded))
                        .foregroundStyle(ringTint)
                }
                .frame(width: 120, height: 120)

                Text("Score \(displayScore) / \(maxScore)")
                    .font(AppTheme.Font.title2)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                Text("Max score is \(maxScore) • +\(correctPoints) right • \(wrongPoints) wrong")
                    .font(AppTheme.Font.micro)
                    .foregroundStyle(AppTheme.Palette.textSecondary)
            }
            .frame(maxWidth: .infinity)
        }
    }

    private var performanceCard: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                Text("Performance")
                    .font(AppTheme.Font.headline)
                    .foregroundStyle(AppTheme.Palette.textPrimary)

                LazyVGrid(
                    columns: Array(repeating: GridItem(.flexible(), spacing: AppTheme.Spacing.sm), count: 2),
                    spacing: AppTheme.Spacing.sm
                ) {
                    StatTile(value: "\(attemptedCount)", label: "Attempted", systemImage: "checklist", tint: AppTheme.Palette.textSecondary)
                    StatTile(value: "\(correctCount)", label: "Correct", systemImage: "checkmark.circle.fill", tint: AppTheme.Palette.success)
                    StatTile(value: "\(wrongCount)", label: "Wrong", systemImage: "xmark.circle.fill", tint: AppTheme.Palette.danger)
                    StatTile(value: "\(totalLoaded)", label: "Loaded", systemImage: "tray.full", tint: AppTheme.Palette.info)
                }

                Button {
                    isShowingReview.toggle()
                } label: {
                    VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
                        Text(isShowingReview ? "Hide Review Questions" : "Show Review Questions")
                            .font(AppTheme.Font.bodyBold)
                            .foregroundStyle(AppTheme.Palette.primary)
                        Text("\(reviewItems.count) Questions Attempted")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.accent)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(AppTheme.Spacing.lg)
                    .background(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                            .fill(AppTheme.Palette.primary.opacity(0.08))
                    )
                }
                .buttonStyle(.plain)

                if isShowingReview {
                    if reviewItems.isEmpty {
                        Text("Review data not available")
                            .font(AppTheme.Font.callout)
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                            .frame(maxWidth: .infinity)
                            .padding(AppTheme.Spacing.lg)
                            .background(
                                RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                                    .fill(AppTheme.Palette.cardBackgroundElevated)
                            )
                    } else {
                        Button {
                            isPresentingReview = true
                        } label: {
                            Label("Open full review (\(reviewItems.count))", systemImage: "list.bullet.clipboard")
                                .font(AppTheme.Font.callout.weight(.semibold))
                                .foregroundStyle(AppTheme.Palette.textPrimary)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, AppTheme.Spacing.md)
                                .background(
                                    RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                                        .fill(AppTheme.Palette.cardBackgroundElevated)
                                )
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }

    private var resultNotesCard: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                Text("Result Notes")
                    .font(AppTheme.Font.headline)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                Text(
                    "Your answers were stored in review JSON for later analysis. "
                    + "The same unique test series can be reused for all players."
                )
                .font(AppTheme.Font.caption)
                .foregroundStyle(AppTheme.Palette.textSecondary)
                .fixedSize(horizontal: false, vertical: true)
            }
        }
    }
}

#Preview {
    NavigationStack {
        QuizView(quiz: Quiz(id: 1, title: "Anatomy Basics", questionCount: 5, durationSeconds: 300))
            .environmentObject(SessionStore())
            .environment(\.api, .live)
    }
}
