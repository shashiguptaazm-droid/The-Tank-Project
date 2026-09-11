import SwiftUI

/// Topic catalogue backed by `get_topics.php` and `api/topicsearch.php`.
struct TopicsView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api

    @State private var state: LoadState<[Topic]> = .idle
    @State private var searchText = ""
    @State private var searchResults: [Topic] = []
    @State private var isSearching = false

    private var displayedTopics: [Topic] {
        searchText.trimmingCharacters(in: .whitespaces).isEmpty ? (state.value ?? []) : searchResults
    }

    var body: some View {
        NavigationStack {
            Group {
                switch state {
                case .idle, .loading:
                    LoadingStateView(message: "Loading topics…")

                case let .failed(message):
                    ErrorStateView(message: message) {
                        Task { await load() }
                    }

                case .loaded:
                    if displayedTopics.isEmpty {
                        EmptyStateView(
                            title: searchText.isEmpty ? "No topics yet" : "No matches",
                            message: searchText.isEmpty
                                ? "Topics will appear here once your curriculum is published."
                                : "Try a different search term.",
                            systemImage: "book.closed"
                        )
                    } else {
                        topicList
                    }
                }
            }
            .screenBackground()
            .navigationTitle("Learn")
            .searchable(text: $searchText, prompt: "Search topics")
            .onChange(of: searchText) { newValue in
                Task { await runSearch(newValue) }
            }
            .task { await load() }
            .refreshable { await load() }
        }
    }

    private var topicList: some View {
        ScrollView {
            LazyVStack(spacing: AppTheme.Spacing.sm) {
                ForEach(Array(displayedTopics.enumerated()), id: \.element.id) { index, topic in
                    NavigationLink {
                        QuizListView(topic: topic)
                    } label: {
                        TopicRow(topic: topic, tint: AppTheme.Palette.color(for: index))
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(AppTheme.Spacing.md)
        }
    }

    // MARK: - Networking

    @MainActor
    private func load() async {
        state = await LoadState.result { [api] in
            try await api.study.topics()
        }
    }

    @MainActor
    private func runSearch(_ text: String) async {
        let trimmed = text.trimmingCharacters(in: .whitespaces)
        guard !trimmed.isEmpty else {
            searchResults = []
            return
        }
        // Debounce so a fast typist does not hammer the endpoint.
        isSearching = true
        try? await Task.sleep(nanoseconds: 350_000_000)
        guard !Task.isCancelled else { return }
        searchResults = (try? await api.study.searchTopics(query: trimmed)) ?? []
        isSearching = false
    }
}

/// A single row in the topic list.
struct TopicRow: View {
    let topic: Topic
    var tint: Color = AppTheme.Palette.primary

    var body: some View {
        CardContainer(padding: AppTheme.Spacing.sm) {
            HStack(spacing: AppTheme.Spacing.md) {
                ZStack {
                    RoundedRectangle(cornerRadius: AppTheme.Radius.sm, style: .continuous)
                        .fill(tint.opacity(0.15))
                    Image(systemName: topic.iconName.isEmpty ? "book.fill" : topic.iconName)
                        .font(.system(size: 20, weight: .semibold))
                        .foregroundStyle(tint)
                }
                .frame(width: 44, height: 44)

                VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
                    Text(topic.name)
                        .font(AppTheme.Font.callout.weight(.semibold))
                        .foregroundStyle(AppTheme.Palette.textPrimary)
                        .lineLimit(1)

                    HStack(spacing: AppTheme.Spacing.xs) {
                        if !topic.subject.isEmpty {
                            Text(topic.subject)
                                .font(AppTheme.Font.caption)
                                .foregroundStyle(AppTheme.Palette.textSecondary)
                        }
                        if topic.questionCount > 0 {
                            Text("· \(topic.questionCount) questions")
                                .font(AppTheme.Font.caption)
                                .foregroundStyle(AppTheme.Palette.textSecondary)
                        }
                    }

                    if !topic.description.isEmpty {
                        Text(topic.description)
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                            .lineLimit(2)
                    }
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(AppTheme.Palette.textSecondary.opacity(0.6))
            }
        }
    }
}

/// Lists the quizzes available inside one topic.
struct QuizListView: View {

    let topic: Topic

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api

    @State private var state: LoadState<[Quiz]> = .idle

    var body: some View {
        Group {
            switch state {
            case .idle, .loading:
                LoadingStateView(message: "Loading quizzes…")
            case let .failed(message):
                ErrorStateView(message: message) { Task { await load() } }
            case .loaded:
                if (state.value ?? []).isEmpty {
                    EmptyStateView(
                        title: "No quizzes available",
                        message: "This topic doesn't have any quizzes published yet.",
                        systemImage: "doc.questionmark"
                    )
                } else {
                    quizList
                }
            }
        }
        .screenBackground()
        .navigationTitle(topic.name)
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private var quizList: some View {
        ScrollView {
            LazyVStack(spacing: AppTheme.Spacing.sm) {
                ForEach(state.value ?? []) { quiz in
                    NavigationLink {
                        QuizView(quiz: quiz)
                    } label: {
                        CardContainer(padding: AppTheme.Spacing.sm) {
                            HStack {
                                VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
                                    Text(quiz.title.isEmpty ? "Practice quiz" : quiz.title)
                                        .font(AppTheme.Font.callout.weight(.semibold))
                                        .foregroundStyle(AppTheme.Palette.textPrimary)
                                        .lineLimit(2)

                                    HStack(spacing: AppTheme.Spacing.xs) {
                                        if quiz.questionCount > 0 {
                                            Text("\(quiz.questionCount) questions")
                                        }
                                        if quiz.durationSeconds > 0 {
                                            Text("· \(quiz.durationSeconds / 60) min")
                                        }
                                    }
                                    .font(AppTheme.Font.caption)
                                    .foregroundStyle(AppTheme.Palette.textSecondary)
                                }

                                Spacer()

                                if !quiz.difficulty.isEmpty {
                                    TagBadge(
                                        text: quiz.difficulty.capitalized,
                                        tint: quiz.difficulty.lowercased() == "hard"
                                            ? AppTheme.Palette.danger
                                            : AppTheme.Palette.accent
                                    )
                                }
                            }
                        }
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(AppTheme.Spacing.md)
        }
    }

    @MainActor
    private func load() async {
        let userId = session.userId
        state = await LoadState.result { [api] in
            try await api.study.quizzes(topicId: topic.id, userId: userId)
        }
    }
}

#Preview {
    TopicsView()
        .environmentObject(SessionStore())
        .environment(\.api, .live)
}
