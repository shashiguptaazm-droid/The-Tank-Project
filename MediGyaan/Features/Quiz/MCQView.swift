import SwiftUI

/// The gamified MCQ practice screen — the one Activity Android opens for plain
/// practice, sudden-death survival, King of the Topic, Today's 10-minute
/// challenge and the 15-question custom battle.
///
/// Ports `com.rankwarz.edulabsrtm.MCQActivity.kt` (plus the `activity_mcq.xml`
/// layout it inflates). Navigation, timers, battle-mode branching, the combo /
/// streak / speed XP rules, the topic picker, the question navigator and the
/// local answer cache all live in ``MCQViewModel``.
///
/// Question and option rendering deliberately reuse `OptionRow`,
/// `CardContainer`, `AskAiSheet`, `QuestionShareSheet`, `FullScreenImageView`
/// and `ReviewView` rather than duplicating them.
struct MCQView: View {

    /// The launch parameters — see ``MCQSessionConfig``.
    let configuration: MCQSessionConfig

    @Environment(\.api) private var api
    @EnvironmentObject private var session: SessionStore
    @Environment(\.dismiss) private var dismiss

    @StateObject private var viewModel: MCQViewModel

    @State private var errorMessage: String?
    @State private var zoomedImageURL: URL?
    @State private var modal: MCQModal?
    @State private var reportReason = MCQReportReason.all[0]
    @State private var reportDetails = ""
    @State private var hasStarted = false

    /// The five `MCQActivity` modals plus the four end-of-run dialogs.
    /// SwiftUI honours only the last `.sheet` attached to a given view, so they
    /// are routed through one enum rather than five `isPresented` flags.
    private enum MCQModal: Identifiable {
        case askAI
        case share
        case picker
        case review
        case report
        case terminal(MCQTerminalEvent)

        var id: String {
            switch self {
            case .askAI: return "askAI"
            case .share: return "share"
            case .picker: return "picker"
            case .review: return "review"
            case .report: return "report"
            case .terminal(let event): return "terminal-\(event.id)"
            }
        }
    }

    init(configuration: MCQSessionConfig = MCQSessionConfig()) {
        self.configuration = configuration
        _viewModel = StateObject(wrappedValue: MCQViewModel(configuration: configuration))
    }

    var body: some View {
        ZStack(alignment: .bottom) {
            content
            toastBar
        }
        .screenBackground()
        .navigationBarHidden(true)
        .task {
            guard !hasStarted else { return }
            hasStarted = true
            await viewModel.start(api: api, userId: session.userId)
        }
        .onDisappear {
            viewModel.stop()
        }
        .onChange(of: viewModel.terminalEvent) { event in
            if let event = event {
                modal = .terminal(event)
            }
        }
        .sheet(item: $modal) { destination in
            modalContent(for: destination)
        }
        .fullScreenCover(
            isPresented: Binding(
                get: { zoomedImageURL != nil },
                set: { if !$0 { zoomedImageURL = nil } }
            )
        ) {
            FullScreenImageView(imageURL: zoomedImageURL)
        }
        .errorAlert(message: $errorMessage)
    }

    @ViewBuilder
    private func modalContent(for destination: MCQModal) -> some View {
        switch destination {
        case .askAI:
            if let question = viewModel.question {
                AskAiSheet(question: question)
            }
        case .share:
            if let question = viewModel.question {
                QuestionShareSheet(question: question, userId: session.userId)
            }
        case .picker:
            questionPicker
        case .review:
            ReviewView(reviewJson: viewModel.reviewJSON)
        case .report:
            reportSheet
        case .terminal(let event):
            terminalSheet(event)
        }
    }

    // MARK: - Content

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .idle, .loading:
            LoadingStateView(message: "Loading question...")

        case let .failed(message):
            ErrorStateView(message: message) {
                Task {
                    await viewModel.fetchQuestion(id: nil)
                    if case .failed = viewModel.state {
                        errorMessage = message
                    }
                }
            }

        case .loaded:
            if let question = viewModel.question {
                runner(question)
            } else {
                EmptyStateView(
                    title: "No questions found",
                    message: "This subject has no questions published yet.",
                    systemImage: "questionmark.square.dashed"
                )
            }
        }
    }

    private func runner(_ question: Question) -> some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.md) {
                if viewModel.mode.isBattleMode {
                    battleHeader
                }
                if viewModel.showsTopicPicker {
                    topicPicker
                }
                utilityRow
                questionCard(question)
                optionsList(question)
                actionButtons
                if viewModel.revealed {
                    secondaryButtons
                    explanationCard
                }
                progressCaption
            }
            .padding(AppTheme.Spacing.lg)
        }
        .overlay(alignment: .top) {
            rewardOverlays
        }
    }

    // MARK: - Battle header (`battleModeHeaderCard`)

    private var battleHeader: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
            HStack {
                Text(viewModel.mode.badge)
                    .font(AppTheme.Font.captionBold)
                    .foregroundStyle(.white)
                    .padding(.horizontal, AppTheme.Spacing.sm)
                    .padding(.vertical, AppTheme.Spacing.xxs)
                    .background(Capsule().fill(.white.opacity(0.20)))

                Spacer(minLength: 0)

                Text(viewModel.battleTimerText)
                    .font(AppTheme.Font.captionBold)
                    .foregroundStyle(.white)
                    .monospacedDigit()
            }

            Text(viewModel.battleTitle)
                .font(AppTheme.Font.title3)
                .foregroundStyle(.white)
                .lineLimit(2)

            Text(viewModel.battleSubtitle)
                .font(AppTheme.Font.callout)
                .foregroundStyle(.white.opacity(0.85))
                .lineLimit(2)

            if viewModel.mode.showsProgressBar {
                ProgressView(
                    value: Double(min(viewModel.currentIndex + 1, viewModel.mode.progressBarMaximum)),
                    total: Double(viewModel.mode.progressBarMaximum)
                )
                .tint(.white)
                .padding(.top, AppTheme.Spacing.xxs)
            }
        }
        .padding(AppTheme.Spacing.lg)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            LinearGradient(
                colors: battleGradient,
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        )
        .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous))
    }

    /// Android hardcodes a two-stop diagonal gradient per mode; the stops map
    /// onto the palette tokens that already carry those hues.
    private var battleGradient: [Color] {
        switch viewModel.mode {
        case .survival:
            return [AppTheme.Palette.error, AppTheme.Palette.danger]
        case .kingOfTopic:
            return [AppTheme.Palette.warning, AppTheme.Palette.secondaryVariant]
        case .customBattle:
            return [AppTheme.Palette.primary, AppTheme.Palette.primaryDark]
        case .todayChallenge:
            return [AppTheme.Ink.invitation, AppTheme.Ink.ranked]
        case .practice:
            return [AppTheme.Palette.primary, AppTheme.Palette.primaryDark]
        }
    }

    // MARK: - Topic picker (`topicLayout` / `topicSpinner`)

    private var topicPicker: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
            Text("Select Topic")
                .font(AppTheme.Font.callout.weight(.semibold))
                .foregroundStyle(AppTheme.Palette.primary)

            Menu {
                ForEach(viewModel.topicsList, id: \.self) { topic in
                    Button {
                        Task { await viewModel.selectTopic(topic) }
                    } label: {
                        if topic == viewModel.selectedTopic {
                            Label(topic, systemImage: "checkmark")
                        } else {
                            Text(topic)
                        }
                    }
                }
            } label: {
                HStack(spacing: AppTheme.Spacing.sm) {
                    Text(viewModel.selectedTopic)
                        .font(AppTheme.Font.body)
                        .lineLimit(1)
                    Spacer(minLength: 0)
                    Image(systemName: "chevron.down")
                        .font(.system(size: 10, weight: .bold))
                }
                .padding(.horizontal, AppTheme.Spacing.md)
                .padding(.vertical, AppTheme.Spacing.sm)
                .background(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.input, style: .continuous)
                        .fill(AppTheme.Palette.optionBackground)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.input, style: .continuous)
                        .stroke(AppTheme.Palette.optionStroke, lineWidth: 1)
                )
                .foregroundStyle(AppTheme.Palette.textPrimary)
            }
        }
    }

    // MARK: - Utility row (`topActionRow`)

    private var utilityRow: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            if viewModel.revealed {
                utilityButton(systemImage: viewModel.isSpeaking ? "speaker.wave.3.fill" : "speaker.wave.2") {
                    viewModel.toggleExplanationSpeech()
                }
            }
            if !viewModel.mode.isBattleMode {
                utilityButton(systemImage: "square.grid.3x3") { modal = .picker }
            }
            utilityButton(systemImage: "square.and.arrow.up") { modal = .share }
            utilityButton(systemImage: "list.bullet.clipboard") { modal = .review }
            Spacer(minLength: 0)
        }
    }

    private func utilityButton(systemImage: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: systemImage)
                .font(.system(size: 17, weight: .semibold))
                .foregroundStyle(AppTheme.Palette.primary)
                .frame(width: 44, height: 44)
                .background(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.input, style: .continuous)
                        .fill(AppTheme.Palette.primary.opacity(0.10))
                )
        }
        .buttonStyle(.plain)
    }

    // MARK: - Question card (`questionCard`)

    private func questionCard(_ question: Question) -> some View {
        CardContainer(isDashboardCard: true) {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                if let url = question.imageURL {
                    questionImage(url)
                }

                Text(cleanLeadingNumber(question.text))
                    .font(AppTheme.Font.title3)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                    .lineSpacing(AppTheme.Spacing.xxs)
                    .fixedSize(horizontal: false, vertical: true)

                Text(viewModel.statusText)
                    .font(AppTheme.Font.callout)
                    .foregroundStyle(AppTheme.Palette.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)

                ProgressView(value: viewModel.dailyProgress)
                    .tint(AppTheme.Palette.primary)
            }
        }
        .scaleEffect(viewModel.comboCount > 0 ? 1.01 : 1)
        .animation(.easeOut(duration: 0.15), value: viewModel.popTrigger)
        .shake(trigger: viewModel.shakeTrigger)
    }

    private func questionImage(_ url: URL) -> some View {
        Button {
            zoomedImageURL = url
        } label: {
            AsyncImage(url: url) { phase in
                switch phase {
                case .success(let image):
                    image
                        .resizable()
                        .scaledToFit()
                        .frame(maxWidth: .infinity, maxHeight: 220)
                        .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.option, style: .continuous))
                case .failure:
                    placeholderImage(systemImage: "photo.badge.exclamationmark", caption: "Image could not be loaded")
                case .empty:
                    ProgressView()
                        .frame(maxWidth: .infinity)
                        .frame(height: 160)
                @unknown default:
                    EmptyView()
                }
            }
        }
        .buttonStyle(.plain)
    }

    private func placeholderImage(systemImage: String, caption: String) -> some View {
        VStack(spacing: AppTheme.Spacing.xs) {
            Image(systemName: systemImage)
                .font(.system(size: 24))
            Text(caption)
                .font(AppTheme.Font.caption)
        }
        .foregroundStyle(AppTheme.Palette.textSecondary)
        .frame(maxWidth: .infinity)
        .padding(.vertical, AppTheme.Spacing.lg)
        .background(AppTheme.Palette.divider.opacity(0.25))
        .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.option, style: .continuous))
    }

    // MARK: - Options (`radioGroup` / `optionA..optionD`)

    private func optionsList(_ question: Question) -> some View {
        VStack(spacing: 0) {
            ForEach(Array(question.options.enumerated()), id: \.offset) { index, option in
                OptionRow(
                    text: cleanLeadingNumber(option),
                    index: index,
                    isSelected: viewModel.selectedLetter == MCQViewModel.letter(for: index),
                    reviewState: reviewState(for: index, question: question)
                ) {
                    viewModel.selectOption(at: index)
                }
                .allowsHitTesting(!viewModel.revealed)
            }
        }
    }

    /// Kotlin's post-submit recolouring: the correct row goes green, and the
    /// row the candidate actually picked goes red when it was wrong.
    private func reviewState(for index: Int, question: Question) -> OptionReviewState {
        guard viewModel.revealed else { return .neutral }
        if index == question.correctIndex { return .correct }
        if let letter = viewModel.selectedLetter, MCQViewModel.letter(for: index) == letter {
            return .wrong
        }
        return .neutral
    }

    // MARK: - Actions (`actionButtonsRow` / `secondaryButtonsRow`)

    private var actionButtons: some View {
        Group {
            if viewModel.mode.isBattleMode {
                PrimaryButton(
                    title: viewModel.revealed ? battleAdvanceTitle : "Submit Answer",
                    isEnabled: viewModel.revealed || viewModel.selectedLetter != nil,
                    isSubmit: true
                ) {
                    if viewModel.revealed {
                        viewModel.navigate(1)
                    } else {
                        viewModel.submit()
                    }
                }
            } else {
                HStack(spacing: AppTheme.Spacing.sm) {
                    stepButton(systemImage: "chevron.left", isEnabled: !viewModel.isFirstQuestion) {
                        viewModel.navigate(-1)
                    }

                    PrimaryButton(
                        title: viewModel.revealed ? "Next" : "Submit",
                        isEnabled: viewModel.revealed || viewModel.selectedLetter != nil,
                        isSubmit: true
                    ) {
                        if viewModel.revealed {
                            viewModel.navigate(1)
                        } else {
                            viewModel.submit()
                        }
                    }

                    stepButton(systemImage: "chevron.right", isEnabled: !viewModel.isLastQuestion) {
                        viewModel.navigate(1)
                    }
                }
            }
        }
    }

    private var battleAdvanceTitle: String {
        viewModel.isLastQuestion ? "Finish" : "Next Question"
    }

    private func stepButton(systemImage: String, isEnabled: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: systemImage)
                .font(.system(size: 16, weight: .bold))
                .foregroundStyle(AppTheme.Palette.primary)
                .frame(width: 46, height: 48)
                .background(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.button, style: .continuous)
                        .stroke(AppTheme.Palette.outline, lineWidth: 1)
                )
        }
        .buttonStyle(.plain)
        .disabled(!isEnabled)
        .opacity(isEnabled ? 1 : 0.4)
    }

    private var secondaryButtons: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            Button {
                modal = .report
            } label: {
                Label("Report", systemImage: "exclamationmark.triangle")
                    .font(AppTheme.Font.callout.weight(.semibold))
                    .frame(maxWidth: .infinity)
                    .frame(height: 46)
                    .background(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.button, style: .continuous)
                            .stroke(AppTheme.Palette.outline, lineWidth: 1)
                    )
                    .foregroundStyle(AppTheme.Palette.textPrimary)
            }
            .buttonStyle(.plain)

            Button {
                modal = .askAI
            } label: {
                Label("Ask AI Companion", systemImage: "brain.head.profile")
                    .font(AppTheme.Font.callout.weight(.semibold))
                    .frame(maxWidth: .infinity)
                    .frame(height: 46)
                    .background(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.button, style: .continuous)
                            .fill(AppTheme.Palette.primary.opacity(0.12))
                    )
                    .foregroundStyle(AppTheme.Palette.primary)
            }
            .buttonStyle(.plain)
        }
    }

    // MARK: - Explanation (`explanationCard`)

    private var explanationCard: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                HStack {
                    Label("Explanation", systemImage: "lightbulb.fill")
                        .font(AppTheme.Font.headline)
                        .foregroundStyle(AppTheme.Palette.textPrimary)

                    Spacer(minLength: 0)

                    Button {
                        viewModel.toggleExplanationSpeech()
                    } label: {
                        Image(systemName: viewModel.isSpeaking ? "speaker.wave.3.fill" : "speaker.wave.2")
                            .foregroundStyle(AppTheme.Palette.accent)
                    }
                    .buttonStyle(.plain)
                }

                Text(viewModel.currentExplanation.isEmpty
                     ? "Correct option: \(MCQViewModel.letter(for: viewModel.question?.correctIndex ?? 0))."
                     : viewModel.currentExplanation)
                    .font(AppTheme.Font.callout)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                    .lineSpacing(AppTheme.Spacing.xxs)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var progressCaption: some View {
        Text("\(viewModel.answeredPoolCount) of \(viewModel.totalCount) answered - \(viewModel.currentExp) XP")
            .font(AppTheme.Font.caption)
            .foregroundStyle(AppTheme.Palette.textSecondary)
            .frame(maxWidth: .infinity)
            .padding(.vertical, AppTheme.Spacing.xs)
    }

    // MARK: - Overlays (`showFloatingXp`, `showBadgePopup`)

    @ViewBuilder
    private var rewardOverlays: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            if let xp = viewModel.floatingXP {
                Text("+\(xp) XP!")
                    .font(AppTheme.Font.title2)
                    .foregroundStyle(AppTheme.Ink.gold)
                    .padding(.horizontal, AppTheme.Spacing.lg)
                    .padding(.vertical, AppTheme.Spacing.sm)
                    .background(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.button, style: .continuous)
                            .fill(AppTheme.Ink.elevated)
                    )
                    .task(id: xp) {
                        try? await Task.sleep(nanoseconds: 1_000_000_000)
                        viewModel.clearFloatingXP()
                    }
            }

            if let badge = viewModel.badgeEvent {
                VStack(spacing: AppTheme.Spacing.xxs) {
                    Text(badge.title)
                        .font(AppTheme.Font.cardTitle)
                        .foregroundStyle(AppTheme.Ink.gold)
                    Text(badge.message)
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Ink.textSecondary)
                }
                .padding(.horizontal, AppTheme.Spacing.xl)
                .padding(.vertical, AppTheme.Spacing.lg)
                .background(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.materialCard, style: .continuous)
                        .fill(AppTheme.Ink.elevated)
                )
                .task(id: badge.id) {
                    try? await Task.sleep(nanoseconds: 3_000_000_000)
                    viewModel.clearBadgeEvent()
                }
            }
        }
        .padding(.horizontal, AppTheme.Spacing.xl)
    }

    @ViewBuilder
    private var toastBar: some View {
        if let message = viewModel.toastMessage {
            Text(message)
                .font(AppTheme.Font.callout.weight(.semibold))
                .foregroundStyle(.white)
                .padding(.horizontal, AppTheme.Spacing.lg)
                .padding(.vertical, AppTheme.Spacing.sm)
                .background(Capsule().fill(AppTheme.Palette.warning))
                .padding(.horizontal, AppTheme.Spacing.xl)
                .padding(.bottom, AppTheme.Spacing.xxl)
                .transition(.move(edge: .bottom).combined(with: .opacity))
                .task(id: message) {
                    try? await Task.sleep(nanoseconds: 2_200_000_000)
                    if viewModel.toastMessage == message {
                        viewModel.toastMessage = nil
                    }
                }
        }
    }

    // MARK: - Modals

    private var questionPicker: some View {
        NavigationStack {
            ScrollView {
                LazyVGrid(
                    columns: Array(repeating: GridItem(.flexible(), spacing: AppTheme.Spacing.sm), count: 5),
                    spacing: AppTheme.Spacing.sm
                ) {
                    ForEach(Array(viewModel.allQuestionIds.enumerated()), id: \.offset) { index, id in
                        Button {
                            viewModel.jump(to: index)
                            modal = nil
                        } label: {
                            Text("\(index + 1)")
                                .font(AppTheme.Font.callout.weight(.bold))
                                .frame(maxWidth: .infinity)
                                .frame(height: 44)
                                .background(
                                    RoundedRectangle(cornerRadius: AppTheme.Radius.input, style: .continuous)
                                        .fill(pickerFill(for: index))
                                )
                                .foregroundStyle(pickerForeground(for: index))
                                .overlay(
                                    RoundedRectangle(cornerRadius: AppTheme.Radius.input, style: .continuous)
                                        .stroke(
                                            viewModel.currentIndex == index
                                                ? AppTheme.Palette.primary
                                                : Color.clear,
                                            lineWidth: 2
                                        )
                                )
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("Question \(index + 1), id \(id)")
                    }
                }
                .padding(AppTheme.Spacing.lg)
            }
            .screenBackground()
            .navigationTitle("Jump to Question")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { modal = nil }
                }
            }
        }
    }

    /// Android's `QuestionPickerAdapter` paints an attempted id green and an
    /// unattempted one grey.
    private func pickerFill(for index: Int) -> Color {
        if index == viewModel.currentIndex { return AppTheme.Palette.primary.opacity(0.18) }
        if viewModel.isAnsweredLocally(viewModel.allQuestionIds[index]) {
            return AppTheme.Palette.success.opacity(0.18)
        }
        return AppTheme.Palette.divider.opacity(0.4)
    }

    private func pickerForeground(for index: Int) -> Color {
        if index == viewModel.currentIndex { return AppTheme.Palette.primary }
        if viewModel.isAnsweredLocally(viewModel.allQuestionIds[index]) {
            return AppTheme.Palette.success
        }
        return AppTheme.Palette.textMuted
    }

    private var reportSheet: some View {
        NavigationStack {
            Form {
                Section("Reason") {
                    Picker("Reason", selection: $reportReason) {
                        ForEach(MCQReportReason.all, id: \.self) { reason in
                            Text(reason).tag(reason)
                        }
                    }
                    .pickerStyle(.inline)
                }
                Section("Details (optional)") {
                    TextField("Optional details", text: $reportDetails, axis: .vertical)
                        .lineLimit(3...6)
                }
            }
            .navigationTitle("Report question #\(viewModel.question?.id ?? 0)")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { modal = nil }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Send report") {
                        viewModel.submitReport(
                            reason: reportReason,
                            details: reportDetails.trimmingCharacters(in: .whitespacesAndNewlines)
                        )
                        reportDetails = ""
                        modal = nil
                    }
                }
            }
        }
    }

    /// The four non-cancelable `AlertDialog`s, rendered as a card so they can
    /// coexist with the app's error alert.
    private func terminalSheet(_ event: MCQTerminalEvent) -> some View {
        VStack(spacing: AppTheme.Spacing.lg) {
            Spacer()

            Image(systemName: terminalIcon(event))
                .font(.system(size: 44))
                .foregroundStyle(AppTheme.Ink.gold)

            Text(event.title)
                .font(AppTheme.Font.title)
                .multilineTextAlignment(.center)

            Text(event.message)
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Palette.textSecondary)
                .multilineTextAlignment(.center)

            Spacer()

            if case .survivalEnded = event {
                SecondaryButton(title: "Review Session") {
                    viewModel.dismissTerminalEvent()
                    modal = .review
                }
            }

            PrimaryButton(title: "Back to Dashboard") {
                viewModel.dismissTerminalEvent()
                modal = nil
                dismiss()
            }
        }
        .padding(AppTheme.Spacing.xl)
        .screenBackground()
        .presentationDetents([.medium])
        .interactiveDismissDisabled()
    }

    private func terminalIcon(_ event: MCQTerminalEvent) -> String {
        switch event {
        case .survivalEnded: return "skull"
        case .challengeTimedOut: return "timer"
        case .customBattleComplete: return "trophy"
        case .notEnoughQuestions: return "exclamationmark.triangle"
        }
    }

    // MARK: - Helpers

    /// Kotlin's `leadingNumberRegex` strips the `1.` / `2)` prefix some rows
    /// carry. Same pattern the shared renderer already applies.
    private func cleanLeadingNumber(_ text: String) -> String {
        text.replacingOccurrences(of: #"^\d+[.\s\-)\]]+\s*"#, with: "", options: .regularExpression)
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

#Preview {
    NavigationStack {
        MCQView(configuration: MCQSessionConfig(
            mode: .survival,
            subject: "NEET PG",
            topic: "Cardiology"
        ))
        .environmentObject(SessionStore())
        .environment(\.api, .live)
    }
}
