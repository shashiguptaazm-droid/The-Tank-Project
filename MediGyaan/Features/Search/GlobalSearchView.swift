import SwiftUI

/// "Search" tab — ports `GlobalSearchActivity` / `activity_search.xml`,
/// backed by `api/searchv2.php` and `api/topicsearch.php`.
///
/// The Android screen searches topics and questions, with recent searches kept
/// in `SharedPreferences`; recent terms are mirrored here in `@AppStorage`.
struct GlobalSearchView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @Environment(\.dismiss) private var dismiss

    @State private var query = ""
    @State private var topicResults: [Topic] = []
    @State private var isSearching = false
    @State private var hasSearched = false
    @State private var errorMessage: String?
    @AppStorage("mg.recentSearches") private var recentSearchesJSON = "[]"

    private var recentSearches: [String] {
        (try? JSONDecoder().decode([String].self, from: Data(recentSearchesJSON.utf8))) ?? []
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                searchBar

                if query.trimmingCharacters(in: .whitespaces).isEmpty {
                    emptyPrompt
                } else if isSearching {
                    LoadingStateView(message: "Searching…")
                } else if topicResults.isEmpty, hasSearched {
                    EmptyStateView(
                        title: "No results",
                        message: "Nothing matched “\(query)”. Try a different term.",
                        systemImage: "magnifyingglass"
                    )
                } else {
                    results
                }
            }
            .screenBackground()
            .navigationTitle("Search")
            .navigationBarTitleDisplayMode(.inline)
            .errorAlert(message: $errorMessage)
        }
    }

    // MARK: - Search bar

    private var searchBar: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            Image(systemName: "magnifyingglass")
                .foregroundStyle(AppTheme.Palette.textSecondary)

            TextField("Search questions, topics, users", text: $query)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .submitLabel(.search)
                .onSubmit { Task { await search(query) } }

            if !query.isEmpty {
                Button {
                    query = ""
                    topicResults = []
                    hasSearched = false
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }
            }
        }
        .padding(.horizontal, AppTheme.Spacing.lg)
        .frame(height: 52)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.field, style: .continuous)
                .fill(AppTheme.Palette.cardBackground)
        )
        .overlay(
            RoundedRectangle(cornerRadius: AppTheme.Radius.field, style: .continuous)
                .stroke(AppTheme.Palette.primary, lineWidth: 1)
        )
        .padding(AppTheme.Spacing.lg)
        .task(id: query) {
            // Debounce so a fast typist does not hammer the endpoint.
            let trimmed = query.trimmingCharacters(in: .whitespaces)
            guard trimmed.count >= 2 else { return }
            try? await Task.sleep(nanoseconds: 400_000_000)
            guard !Task.isCancelled else { return }
            await search(trimmed)
        }
    }

    // MARK: - States

    private var emptyPrompt: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                if !recentSearches.isEmpty {
                    SectionHeader(title: "Recent searches")

                    CardContainer(padding: 0) {
                        VStack(spacing: 0) {
                            ForEach(recentSearches, id: \.self) { term in
                                Button {
                                    query = term
                                    Task { await search(term) }
                                } label: {
                                    HStack(spacing: AppTheme.Spacing.md) {
                                        Image(systemName: "clock.arrow.circlepath")
                                            .foregroundStyle(AppTheme.Palette.textSecondary)
                                        Text(term)
                                            .font(AppTheme.Font.callout)
                                            .foregroundStyle(AppTheme.Palette.textPrimary)
                                        Spacer()
                                        Image(systemName: "arrow.up.left")
                                            .font(.system(size: 12))
                                            .foregroundStyle(AppTheme.Palette.textSecondary)
                                    }
                                    .padding(AppTheme.Spacing.lg)
                                    .contentShape(Rectangle())
                                }
                                .buttonStyle(.plain)
                                Divider().padding(.leading, 52)
                            }
                        }
                    }
                }

                SectionHeader(title: "Browse by subject")
                CardContainer(padding: 0) {
                    VStack(spacing: 0) {
                        ForEach(browseShortcuts, id: \.title) { item in
                            NavigationLink { TopicsView() } label: {
                                MenuRow(title: item.title, systemImage: item.icon, tint: item.tint)
                            }
                            .buttonStyle(.plain)
                            if item.title != browseShortcuts.last?.title {
                                Divider().padding(.leading, 52)
                            }
                        }
                    }
                }
            }
            .padding(AppTheme.Spacing.lg)
        }
    }

    private var results: some View {
        ScrollView {
            LazyVStack(spacing: AppTheme.Spacing.sm) {
                ForEach(Array(topicResults.enumerated()), id: \.element.id) { index, topic in
                    NavigationLink { QuizListView(topic: topic) } label: {
                        TopicRow(topic: topic, tint: AppTheme.Palette.accent(for: index))
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(AppTheme.Spacing.lg)
        }
    }

    private var browseShortcuts: [(title: String, icon: String, tint: Color)] {
        [
            ("All topics", "books.vertical.fill", AppTheme.Palette.primary),
            ("Tests & quizzes", "pencil.and.list.clipboard", AppTheme.Palette.success),
            ("Leaderboard", "trophy.fill", AppTheme.Palette.warning),
            ("Thesis Studio", "doc.text.magnifyingglass", AppTheme.Palette.accent(for: 4)),
        ]
    }

    // MARK: - Networking

    @MainActor
    private func search(_ text: String) async {
        let trimmed = text.trimmingCharacters(in: .whitespaces)
        guard !trimmed.isEmpty else { return }

        isSearching = true
        defer { isSearching = false; hasSearched = true }

        do {
            // `api/searchv2.php` covers questions and users; topic names come
            // from `api/topicsearch.php`. Both are unioned into one result list.
            async let global = api.study.globalSearch(query: trimmed, userId: session.userId)
            async let topics = api.study.searchTopics(query: trimmed)

            let combined = try await (global + topics)
            topicResults = dedupe(combined)
            if !topicResults.isEmpty { remember(trimmed) }
        } catch {
            // A search with no hits is not an error worth an alert on a
            // debounced keystroke; only surface it when the user submitted.
            if !hasSearched {
                errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
            }
        }
    }

    private func dedupe(_ topics: [Topic]) -> [Topic] {
        var seen = Set<Int>()
        return topics.filter { seen.insert($0.id).inserted }
    }

    @MainActor
    private func remember(_ term: String) {
        var terms = recentSearches.filter { $0.caseInsensitiveCompare(term) != .orderedSame }
        terms.insert(term, at: 0)
        terms = Array(terms.prefix(8))
        if let data = try? JSONEncoder().encode(terms),
           let json = String(data: data, encoding: .utf8) {
            recentSearchesJSON = json
        }
    }
}

#Preview {
    GlobalSearchView()
        .environmentObject(SessionStore())
        .environment(\.api, .live)
}
