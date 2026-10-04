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
    @AppStorage(AppPreferences.recentSearches) private var recentSearchesJSON = "[]"

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
            .toolbar(.visible, for: .navigationBar)
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

    @State private var activeFilter: String = "ALL"
    @State private var searchResults: [SearchResultItem] = []

    private let filterOptions = ["ALL", "QUESTIONS", "TOPICS", "USERS", "POSTS"]

    private var filteredResults: [SearchResultItem] {
        switch activeFilter {
        case "QUESTIONS":
            return searchResults.filter { if case .question = $0 { return true } else { return false } }
        case "TOPICS":
            return searchResults.filter { if case .topic = $0 { return true } else { return false } }
        case "USERS":
            return searchResults.filter { if case .user = $0 { return true } else { return false } }
        case "POSTS":
            return searchResults.filter { if case .post = $0 { return true } else { return false } }
        default:
            return searchResults
        }
    }

    private var results: some View {
        VStack(spacing: 0) {
            // Filter chips
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: AppTheme.Spacing.xs) {
                    ForEach(filterOptions, id: \.self) { filter in
                        let isSelected = filter == activeFilter
                        Button {
                            activeFilter = filter
                        } label: {
                            Text(filter)
                                .font(AppTheme.Font.caption.weight(.semibold))
                                .padding(.horizontal, 14)
                                .padding(.vertical, 7)
                                .background(Capsule().fill(isSelected ? AppTheme.Palette.primary : AppTheme.Palette.cardBackgroundElevated))
                                .foregroundStyle(isSelected ? Color.white : AppTheme.Palette.textSecondary)
                        }
                    }
                }
                .padding(.horizontal, AppTheme.Spacing.lg)
                .padding(.vertical, AppTheme.Spacing.xs)
            }

            ScrollView {
                LazyVStack(spacing: AppTheme.Spacing.sm) {
                    ForEach(filteredResults) { item in
                        resultRow(item)
                    }
                }
                .padding(AppTheme.Spacing.lg)
            }
        }
    }

    @ViewBuilder
    private func resultRow(_ item: SearchResultItem) -> some View {
        switch item {
        case let .question(id, text, subject, _):
            CardContainer(padding: AppTheme.Spacing.sm) {
                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        TagBadge(text: subject.isEmpty ? "Question" : subject, tint: AppTheme.Palette.primary)
                        Spacer()
                        Text("#\(id)").font(AppTheme.Font.caption2).foregroundStyle(AppTheme.Palette.textMuted)
                    }
                    Text(text)
                        .font(AppTheme.Font.callout)
                        .foregroundStyle(AppTheme.Palette.textPrimary)
                        .lineLimit(3)
                }
            }

        case let .topic(name, subject):
            CardContainer(padding: AppTheme.Spacing.sm) {
                HStack(spacing: AppTheme.Spacing.md) {
                    Image(systemName: "book.fill")
                        .foregroundStyle(AppTheme.Palette.accent)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(name)
                            .font(AppTheme.Font.headline)
                            .foregroundStyle(AppTheme.Palette.textPrimary)
                        Text(subject)
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                    }
                    Spacer()
                    Image(systemName: "chevron.right")
                        .font(.system(size: 12))
                        .foregroundStyle(AppTheme.Palette.textMuted)
                }
            }

        case let .user(id, name, photo, _):
            CardContainer(padding: AppTheme.Spacing.sm) {
                HStack(spacing: AppTheme.Spacing.md) {
                    if let url = URL(string: photo), !photo.isEmpty {
                        AsyncImage(url: url) { img in
                            img.resizable().scaledToFill()
                        } placeholder: {
                            Circle().fill(AppTheme.Palette.cardBackgroundElevated)
                        }
                        .frame(width: 38, height: 38)
                        .clipShape(Circle())
                    } else {
                        Image(systemName: "person.circle.fill")
                            .font(.system(size: 38))
                            .foregroundStyle(AppTheme.Palette.primary)
                    }

                    VStack(alignment: .leading, spacing: 2) {
                        Text(name.isEmpty ? "Doctor" : name)
                            .font(AppTheme.Font.headline)
                            .foregroundStyle(AppTheme.Palette.textPrimary)
                        Text("Warrior #\(id)")
                            .font(AppTheme.Font.caption2)
                            .foregroundStyle(AppTheme.Palette.textMuted)
                    }
                    Spacer()
                }
            }

        case let .post(id, author, _, caption, _, likes, date):
            CardContainer(padding: AppTheme.Spacing.sm) {
                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Text(author).font(AppTheme.Font.caption.weight(.bold)).foregroundStyle(AppTheme.Palette.textPrimary)
                        Spacer()
                        Text(date).font(AppTheme.Font.caption2).foregroundStyle(AppTheme.Palette.textMuted)
                    }
                    Text(caption).font(AppTheme.Font.callout).foregroundStyle(AppTheme.Palette.textSecondary).lineLimit(2)
                    HStack {
                        Image(systemName: "heart.fill").foregroundStyle(Color.red).font(.system(size: 11))
                        Text("\(likes)").font(AppTheme.Font.caption2).foregroundStyle(AppTheme.Palette.textMuted)
                    }
                }
            }

        case let .video(id, title, author, _, _, _, likes, date):
            CardContainer(padding: AppTheme.Spacing.sm) {
                HStack(spacing: AppTheme.Spacing.md) {
                    Image(systemName: "play.rectangle.fill")
                        .font(.title2)
                        .foregroundStyle(Color.red)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(title).font(AppTheme.Font.headline).lineLimit(1)
                        Text("\(author) • \(likes) likes").font(AppTheme.Font.caption2).foregroundStyle(AppTheme.Palette.textMuted)
                    }
                    Spacer()
                }
            }
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
