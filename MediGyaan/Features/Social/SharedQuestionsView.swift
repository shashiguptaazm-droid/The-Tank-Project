import SwiftUI

/// Dashboard of questions shared by the user, tracking peer attempts and accuracy.
/// Ports `SharedQuestionsActivity.kt` and `QuestionAttemptsActivity.kt`.
struct SharedQuestionsView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @Environment(\.dismiss) private var dismiss

    @State private var state: LoadState<[SharedQuestion]> = .idle
    @State private var searchText: String = ""
    @State private var selectedQuestionForAttempts: SharedQuestion? = nil

    var body: some View {
        NavigationStack {
            Group {
                switch state {
                case .idle, .loading:
                    LoadingStateView(message: "Loading your shared questions…")

                case let .failed(message):
                    ErrorStateView(message: message) {
                        Task { await load() }
                    }

                case let .loaded(questions):
                    if questions.isEmpty {
                        EmptyStateView(
                            title: "No Shared Questions",
                            message: "When you share questions with peers or community feeds, their attempt analytics and accuracy will appear here.",
                            systemImage: "square.and.arrow.up.trianglebadge.exclamationmark"
                        )
                    } else {
                        content(questions)
                    }
                }
            }
            .screenBackground()
            .navigationTitle("Shared Questions")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") { dismiss() }
                }
            }
            .sheet(item: $selectedQuestionForAttempts) { question in
                QuestionAttemptsSheet(question: question, userId: session.userId)
            }
            .task {
                await load()
            }
        .onAppear {
            RemoteLogger.log(tag: "SharedQuestions_Open", message: "User opened Shared Questions view")
        }
        }
    }

    private func content(_ questions: [SharedQuestion]) -> some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.md) {
                // Summary Stats Cards
                statsOverview(questions)

                // Search Bar
                HStack {
                    Image(systemName: "magnifyingglass")
                        .foregroundStyle(.secondary)
                    TextField("Search by question text or ID…", text: $searchText)
                    if !searchText.isEmpty {
                        Button {
                            searchText = ""
                        } label: {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundStyle(.secondary)
                        }
                    }
                }
                .padding(10)
                .background(AppTheme.Palette.cardBackground)
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(Color.primary.opacity(0.08), lineWidth: 1)
                )

                // Questions List
                LazyVStack(spacing: 12) {
                    ForEach(filteredQuestions(questions)) { question in
                        questionAnalyticsCard(question)
                    }
                }
            }
            .padding(AppTheme.Spacing.md)
        }
        .refreshable {
            await load()
        }
    }

    // MARK: - Overview Cards

    private func statsOverview(_ questions: [SharedQuestion]) -> some View {
        let totalAttempts = questions.reduce(0) { $0 + $1.totalAttempts }
        let totalCorrect = questions.reduce(0) { $0 + $1.totalCorrect }
        let avgAccuracy = questions.isEmpty ? 0.0 : (Double(totalCorrect) / Double(max(1, totalAttempts)) * 100)

        return LazyVGrid(
            columns: [
                GridItem(.flexible()),
                GridItem(.flexible()),
                GridItem(.flexible())
            ],
            spacing: 10
        ) {
            statTile(title: "Shared", value: "\(questions.count)", color: AppTheme.Palette.primary)
            statTile(title: "Attempts", value: "\(totalAttempts)", color: Color(hex: 0x00_89_7B))
            statTile(title: "Avg Accuracy", value: String(format: "%.0f%%", avgAccuracy), color: Color(hex: 0xF5_7C_00))
        }
    }

    private func statTile(title: String, value: String, color: Color) -> some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.system(size: 20, weight: .bold, design: .rounded))
                .foregroundStyle(color)

            Text(title)
                .font(.system(size: 11, weight: .medium))
                .foregroundStyle(Color.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 12)
        .background(AppTheme.Palette.cardBackground)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.primary.opacity(0.06), lineWidth: 1)
        )
    }

    // MARK: - Question Card

    private func questionAnalyticsCard(_ question: SharedQuestion) -> some View {
        CardContainer {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Text("Q#\(question.id)")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(Color(hex: 0x39_49_AB))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(Color(hex: 0xE8_EA_F6))
                        .clipShape(Capsule())

                    Spacer()

                    HStack(spacing: 4) {
                        Image(systemName: "chart.line.uptrend.xyaxis")
                        Text(String(format: "%.0f%% accuracy", question.accuracy > 1 ? question.accuracy : question.accuracy * 100))
                    }
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(question.accuracy >= 0.5 ? Color(hex: 0x2E_7D_32) : Color(hex: 0xC6_28_28))
                }

                Text(cleanQuestionText(question.question))
                    .font(AppTheme.Font.body)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                    .lineLimit(3)

                Divider()

                HStack {
                    HStack(spacing: 12) {
                        Label("\(question.totalAttempts) attempts", systemImage: "person.2.fill")
                            .font(.system(size: 12))
                            .foregroundStyle(Color.secondary)

                        Label("\(question.totalCorrect) correct", systemImage: "checkmark.circle.fill")
                            .font(.system(size: 12))
                            .foregroundStyle(Color(hex: 0x2E_7D_32))
                    }

                    Spacer()

                    Button {
                        selectedQuestionForAttempts = question
                    } label: {
                        HStack(spacing: 4) {
                            Text("Peer Breakdown")
                            Image(systemName: "chevron.right")
                        }
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(Color(hex: 0x39_49_AB))
                    }
                }
            }
        }
    }

    private func filteredQuestions(_ questions: [SharedQuestion]) -> [SharedQuestion] {
        guard !searchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return questions
        }
        let lower = searchText.lowercased()
        return questions.filter {
            $0.question.lowercased().contains(lower) || String($0.id).contains(lower)
        }
    }

    private func cleanQuestionText(_ text: String) -> String {
        text.replacingOccurrences(of: #"^\d+[.\s\-)\]]+\s*"#, with: "", options: .regularExpression)
    }

    // MARK: - Networking

    @MainActor
    private func load() async {
        let userId = session.userId
        guard userId > 0 else { return }

        state = await LoadState.result { [api] in
            try await api.social.sharedQuestions(userId: userId)
        }
    }
}

/// Drill-down modal for peer attempts on a single shared question.
/// Ports `QuestionAttemptsActivity.kt`.
struct QuestionAttemptsSheet: View {

    let question: SharedQuestion
    let userId: Int

    @Environment(\.dismiss) private var dismiss
    @Environment(\.api) private var api
    @State private var state: LoadState<[QuestionAttemptPeer]> = .idle

    var body: some View {
        NavigationStack {
            Group {
                switch state {
                case .idle, .loading:
                    LoadingStateView(message: "Fetching peer attempts…")

                case let .failed(message):
                    ErrorStateView(message: message) {
                        Task { await loadAttempts() }
                    }

                case let .loaded(attempts):
                    if attempts.isEmpty {
                        EmptyStateView(
                            title: "No Attempts Recorded Yet",
                            message: "Share this question to a medical WhatsApp or Telegram study group to see live peer answers.",
                            systemImage: "person.crop.circle.badge.questionmark"
                        )
                    } else {
                        attemptsList(attempts)
                    }
                }
            }
            .screenBackground()
            .navigationTitle("Question #\(question.id) Attempts")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
            }
            .task {
                await loadAttempts()
            }
        }
    }

    private func attemptsList(_ attempts: [QuestionAttemptPeer]) -> some View {
        ScrollView {
            LazyVStack(spacing: 10) {
                ForEach(attempts) { attempt in
                    HStack(spacing: 12) {
                        Circle()
                            .fill(attempt.isCorrect ? Color(hex: 0x4C_AF_50).opacity(0.15) : Color(hex: 0xF4_43_36).opacity(0.15))
                            .frame(width: 42, height: 42)
                            .overlay(
                                Image(systemName: attempt.isCorrect ? "checkmark" : "xmark")
                                    .font(.system(size: 16, weight: .bold))
                                    .foregroundStyle(attempt.isCorrect ? Color(hex: 0x2E_7D_32) : Color(hex: 0xC6_28_28))
                            )

                        VStack(alignment: .leading, spacing: 2) {
                            Text(attempt.name.isEmpty ? "Anonymous Peer" : attempt.name)
                                .font(.system(size: 14, weight: .semibold))
                                .foregroundStyle(Color(hex: 0x1A_1C_2E))

                            Text("Answered Option: \(attempt.userAnswer)")
                                .font(.system(size: 12))
                                .foregroundStyle(Color.secondary)
                        }

                        Spacer()

                        if !attempt.createdAt.isEmpty {
                            Text(attempt.createdAt)
                                .font(.system(size: 11))
                                .foregroundStyle(Color.secondary)
                        }
                    }
                    .padding(12)
                    .background(AppTheme.Palette.cardBackground)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(Color.primary.opacity(0.06), lineWidth: 1)
                    )
                }
            }
            .padding(AppTheme.Spacing.md)
        }
    }

    @MainActor
    private func loadAttempts() async {
        state = await LoadState.result { [api] in
            try await api.social.questionAttempts(questionId: question.id, userId: userId)
        }
    }
}