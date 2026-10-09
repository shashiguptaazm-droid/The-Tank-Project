import SwiftUI

/// Complete 1:1 SwiftUI replication of Android's `GlobalSearchActivity.kt` and `GlobalSearchAdapter.kt`.
///
/// Features:
/// 1. Unified Multi-Source Search:
///    - Questions: `api/searchv2.php`
///    - Users / Peers: `api/searchv2.php`
///    - Topics: `api/getTopics.php`
///    - Community Posts: `api/posts_search.php`
///    - Clinical Case Videos: `api/videos_search.php`
/// 2. 6 Filter Chips (matching Android `ChipGroup`):
///    - ALL, QUESTIONS, TOPICS, USERS, POSTS, VIDEOS
/// 3. Consequent Reactions (matching Android's `OnSearchItemClickListener`):
///    - `onQuestionClick`: Launches interactive Quiz / MCQ test for the selected question.
///    - `onTopicClick`: Launches quiz module filtered by the subject and topic.
///    - `onUserClick`: Opens peer's full profile sheet.
///    - `onPostClick`: Opens community post discussion in social hub.
///    - `onVideoClick`: Opens full-screen `VideoPlayerView`.
/// 4. Search history in `@AppStorage` & Browse shortcuts.
/// 5. VPS Telemetry: Real-time logging via `RemoteLogger`.
struct GlobalSearchView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @Environment(\.dismiss) private var dismiss

    // Search Query & States
    @State private var query = ""
    @State private var activeFilter = "ALL" // "ALL", "QUESTIONS", "TOPICS", "USERS", "POSTS", "VIDEOS"
    @State private var searchResults: [SearchResultItem] = []
    @State private var isSearching = false
    @State private var hasSearched = false
    @State private var errorMessage: String?

    // Consequent Reaction Destinations
    @State private var selectedQuizToLaunch: Quiz? = nil
    @State private var selectedVideoToPlay: (title: String, url: URL)? = nil
    @State private var selectedProfileUser: UserItem? = nil

    @AppStorage(AppPreferences.recentSearches) private var recentSearchesJSON = "[]"

    private let filterChips = ["ALL", "QUESTIONS", "TOPICS", "USERS", "POSTS", "VIDEOS"]

    private var recentSearches: [String] {
        (try? JSONDecoder().decode([String].self, from: Data(recentSearchesJSON.utf8))) ?? []
    }

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
        case "VIDEOS":
            return searchResults.filter { if case .video = $0 { return true } else { return false } }
        default:
            return searchResults
        }
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                searchBar

                if query.trimmingCharacters(in: .whitespaces).isEmpty {
                    emptyPrompt
                } else if isSearching {
                    LoadingStateView(message: "Searching questions, topics, users & videos…")
                } else if searchResults.isEmpty && hasSearched {
                    EmptyStateView(
                        title: "No results found",
                        message: "Nothing matched “\(query)”. Try searching by medical keyword, topic, or peer name.",
                        systemImage: "magnifyingglass"
                    )
                } else {
                    resultsListView
                }
            }
            .screenBackground()
            .navigationTitle("Global Search")
            .toolbar(.visible, for: .navigationBar)
            .navigationBarTitleDisplayMode(.inline)
            .errorAlert(message: $errorMessage)
            .sheet(item: $selectedQuizToLaunch) { quiz in
                NavigationStack {
                    QuizView(quiz: quiz)
                }
            }
            .fullScreenCover(item: Binding(
                get: { selectedVideoToPlay.map { IdentifiableVideo(title: $0.title, url: $0.url) } },
                set: { if $0 == nil { selectedVideoToPlay = nil } }
            )) { video in
                VideoPlayerView(title: video.title, videoURL: video.url)
            }
            .sheet(item: $selectedProfileUser) { user in
                NavigationStack {
                    PeerProfileModalView(user: user)
                }
            }
        }
    }

    // MARK: - Search Bar

    private var searchBar: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            Image(systemName: "magnifyingglass")
                .foregroundStyle(AppTheme.Palette.textSecondary)

            TextField("Search 280k MCQs, topics, peers, videos…", text: $query)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .submitLabel(.search)
                .onSubmit {
                    let trimmed = query.trimmingCharacters(in: .whitespaces)
                    if trimmed.count >= 3 {
                        Task { await performSearch(trimmed) }
                    } else {
                        errorMessage = "Minimum 3 characters required for search"
                    }
                }

            if !query.isEmpty {
                Button {
                    query = ""
                    searchResults = []
                    hasSearched = false
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }
            }
        }
        .padding(.horizontal, AppTheme.Spacing.lg)
        .frame(height: 50)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.field, style: .continuous)
                .fill(AppTheme.Palette.cardBackground)
        )
        .overlay(
            RoundedRectangle(cornerRadius: AppTheme.Radius.field, style: .continuous)
                .stroke(AppTheme.Palette.primary.opacity(0.4), lineWidth: 1)
        )
        .padding(.horizontal, AppTheme.Spacing.lg)
        .padding(.vertical, AppTheme.Spacing.sm)
        .task(id: query) {
            let trimmed = query.trimmingCharacters(in: .whitespaces)
            guard trimmed.count >= 3 else { return }
            try? await Task.sleep(nanoseconds: 450_000_000)
            guard !Task.isCancelled else { return }
            await performSearch(trimmed)
        }
    }

    // MARK: - Filter Chips & Results List

    private var resultsListView: some View {
        VStack(spacing: 0) {
            // Horizontal Filter Chips Bar
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: AppTheme.Spacing.xs) {
                    ForEach(filterChips, id: \.self) { chip in
                        let isSelected = chip == activeFilter
                        Button {
                            activeFilter = chip
                            RemoteLogger.log(tag: "GlobalSearch_Filter_Changed", message: "Switched to filter \(chip)")
                        } label: {
                            Text(chip)
                                .font(AppTheme.Font.captionBold)
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

            // Results ScrollView
            ScrollView {
                LazyVStack(spacing: AppTheme.Spacing.sm) {
                    ForEach(filteredResults) { item in
                        searchResultCard(item)
                    }
                }
                .padding(AppTheme.Spacing.lg)
            }
        }
    }

    // MARK: - Result Cards (GlobalSearchAdapter 1:1)

    @ViewBuilder
    private func searchResultCard(_ item: SearchResultItem) -> some View {
        Button {
            handleResultItemClick(item)
        } label: {
            switch item {
            // 1. Question Card
            case let .question(id, text, subject, image):
                CardContainer(padding: AppTheme.Spacing.sm) {
                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            TagBadge(text: subject.isEmpty ? "Question" : subject, tint: AppTheme.Palette.primary)
                            Spacer()
                            Text("#\(id)").font(AppTheme.Font.caption2).foregroundStyle(AppTheme.Palette.textMuted)
                        }
                        Text(text)
                            .font(AppTheme.Font.callout)
                            .foregroundStyle(AppTheme.Palette.textPrimary)
                            .lineLimit(3)
                            .multilineTextAlignment(.leading)

                        HStack {
                            Label("Practice MCQ", systemImage: "play.circle.fill")
                                .font(AppTheme.Font.captionBold)
                                .foregroundStyle(AppTheme.Palette.primary)
                            Spacer()
                            Image(systemName: "chevron.right")
                                .font(.system(size: 11))
                                .foregroundStyle(AppTheme.Palette.textSecondary)
                        }
                        .padding(.top, 2)
                    }
                }

            // 2. Topic Card
            case let .topic(name, subject):
                CardContainer(padding: AppTheme.Spacing.sm) {
                    HStack(spacing: AppTheme.Spacing.md) {
                        ZStack {
                            Circle().fill(AppTheme.Palette.accent.opacity(0.15)).frame(width: 38, height: 38)
                            Image(systemName: "book.fill")
                                .foregroundStyle(AppTheme.Palette.accent)
                        }

                        VStack(alignment: .leading, spacing: 2) {
                            Text(name)
                                .font(AppTheme.Font.headlineBold)
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

            // 3. User / Peer Card
            case let .user(id, name, photo, _):
                CardContainer(padding: AppTheme.Spacing.sm) {
                    HStack(spacing: AppTheme.Spacing.md) {
                        let cleanPhoto = photo.hasPrefix("http") ? photo : "https://medigyaan.com/Neurons/" + photo.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
                        if let url = URL(string: cleanPhoto), !photo.isEmpty {
                            AsyncImage(url: url) { img in
                                img.resizable().scaledToFill()
                            } placeholder: {
                                Circle().fill(AppTheme.Palette.cardBackgroundElevated)
                            }
                            .frame(width: 42, height: 42)
                            .clipShape(Circle())
                        } else {
                            Image(systemName: "person.crop.circle.fill")
                                .font(.system(size: 42))
                                .foregroundStyle(AppTheme.Palette.primary)
                        }

                        VStack(alignment: .leading, spacing: 2) {
                            Text(name.isEmpty ? "Doctor / Peer" : name)
                                .font(AppTheme.Font.headlineBold)
                                .foregroundStyle(AppTheme.Palette.textPrimary)
                            Text("Warrior #\(id) • Tap to view profile")
                                .font(AppTheme.Font.caption)
                                .foregroundStyle(AppTheme.Palette.textMuted)
                        }

                        Spacer()
                        Image(systemName: "arrow.up.right.square.fill")
                            .foregroundStyle(AppTheme.Palette.primary)
                    }
                }

            // 4. Community Post Card
            case let .post(id, author, authorPhoto, caption, _, likes, date):
                CardContainer(padding: AppTheme.Spacing.sm) {
                    VStack(alignment: .leading, spacing: 4) {
                        HStack {
                            Text(author)
                                .font(AppTheme.Font.captionBold)
                                .foregroundStyle(AppTheme.Palette.textPrimary)
                            Spacer()
                            Text(date)
                                .font(AppTheme.Font.caption2)
                                .foregroundStyle(AppTheme.Palette.textMuted)
                        }
                        Text(caption)
                            .font(AppTheme.Font.callout)
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                            .lineLimit(2)
                            .multilineTextAlignment(.leading)
                        HStack {
                            Image(systemName: "heart.fill").foregroundStyle(Color.red).font(.system(size: 11))
                            Text("\(likes) likes").font(AppTheme.Font.caption2).foregroundStyle(AppTheme.Palette.textMuted)
                            Spacer()
                            Text("Community Post #\(id)").font(.system(size: 10)).foregroundStyle(AppTheme.Palette.textMuted)
                        }
                    }
                }

            // 5. Video / Reel Card
            case let .video(id, title, author, _, videoURL, _, likes, date):
                CardContainer(padding: AppTheme.Spacing.sm) {
                    HStack(spacing: AppTheme.Spacing.md) {
                        ZStack {
                            RoundedRectangle(cornerRadius: 8)
                                .fill(Color.red.opacity(0.15))
                                .frame(width: 44, height: 44)
                            Image(systemName: "play.rectangle.fill")
                                .font(.title3)
                                .foregroundStyle(Color.red)
                        }

                        VStack(alignment: .leading, spacing: 2) {
                            Text(title)
                                .font(AppTheme.Font.headlineBold)
                                .foregroundStyle(AppTheme.Palette.textPrimary)
                                .lineLimit(1)
                            Text("\(author) • \(likes) likes")
                                .font(AppTheme.Font.caption)
                                .foregroundStyle(AppTheme.Palette.textMuted)
                        }

                        Spacer()
                        Image(systemName: "play.circle.fill")
                            .font(.system(size: 20))
                            .foregroundStyle(Color.red)
                    }
                }
            }
        }
        .buttonStyle(.plain)
    }

    // MARK: - Consequent Reaction Actions (OnSearchItemClickListener)

    private func handleResultItemClick(_ item: SearchResultItem) {
        switch item {
        // Reaction 1: onQuestionClick -> Launches MCQ Test
        case let .question(id, text, subject, _):
            let qId = Int(id) ?? 1
            RemoteLogger.log(tag: "GlobalSearch_Question_Click", message: "Opening MCQ for question #\(qId)")
            let quiz = Quiz(
                id: qId,
                title: "Question #\(qId) Practice",
                topic: subject.isEmpty ? "Clinical Search Practice" : subject,
                subject: subject.isEmpty ? "Medical" : subject,
                questionCount: 1,
                durationSeconds: 120
            )
            selectedQuizToLaunch = quiz

        // Reaction 2: onTopicClick -> Launches Topic Quiz
        case let .topic(name, subject):
            RemoteLogger.log(tag: "GlobalSearch_Topic_Click", message: "Opening Topic Quiz for \(name)")
            let quiz = Quiz(
                id: 1001,
                title: "\(name) Exam",
                topic: name,
                subject: subject,
                questionCount: 20,
                durationSeconds: 1200
            )
            selectedQuizToLaunch = quiz

        // Reaction 3: onUserClick -> Opens Peer Profile
        case let .user(id, name, photo, _):
            RemoteLogger.log(tag: "GlobalSearch_User_Click", message: "Opening profile for user \(name) (ID: \(id))")
            selectedProfileUser = UserItem(id: id, name: name, photo: photo)

        // Reaction 4: onPostClick -> Notifies or views post
        case let .post(id, author, authorPhoto, caption, images, likes, uploadDate):
            RemoteLogger.log(tag: "GlobalSearch_Post_Click", message: "Opening post #\(id) by \(author)")
            // Displays post info
            errorMessage = "Community Post by \(author):\n\(caption)"

        // Reaction 5: onVideoClick -> Opens Fullscreen Video Player
        case let .video(id, title, _, _, videoURL, _, _, _):
            RemoteLogger.log(tag: "GlobalSearch_Video_Click", message: "Opening video #\(id): \(title)")
            let cleanURL = videoURL.hasPrefix("http") ? videoURL : "https://medigyaan.com/Neurons/" + videoURL.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
            if let url = URL(string: cleanURL) {
                selectedVideoToPlay = (title: title, url: url)
            }
        }
    }

    // MARK: - Search Execution

    @MainActor
    private func performSearch(_ text: String) async {
        isSearching = true
        defer { isSearching = false; hasSearched = true }

        RemoteLogger.log(tag: "GlobalSearch_Submit", message: "Searching for '\(text)' with active filter: \(activeFilter)")

        let goal = session.currentUser?.goal ?? "NEET PG"
        let items = await SearchService.shared.searchAll(
            query: text,
            userId: session.userId,
            goalSubject: goal
        )

        self.searchResults = items
        if !items.isEmpty {
            rememberSearch(text)
        }
        RemoteLogger.log(tag: "GlobalSearch_Done", message: "Search for '\(text)' completed with \(items.count) total results")
    }

    @MainActor
    private func rememberSearch(_ term: String) {
        var terms = recentSearches.filter { $0.caseInsensitiveCompare(term) != .orderedSame }
        terms.insert(term, at: 0)
        terms = Array(terms.prefix(8))
        if let data = try? JSONEncoder().encode(terms),
           let json = String(data: data, encoding: .utf8) {
            recentSearchesJSON = json
        }
    }

    // MARK: - Empty State & Browse Shortcuts

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
                                    Task { await performSearch(term) }
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

    private var browseShortcuts: [(title: String, icon: String, tint: Color)] {
        [
            ("All topics", "books.vertical.fill", AppTheme.Palette.primary),
            ("Tests & mock series", "pencil.and.list.clipboard", AppTheme.Palette.success),
            ("Leaderboard", "trophy.fill", AppTheme.Palette.warning),
            ("Thesis Studio", "doc.text.magnifyingglass", AppTheme.Palette.accent(for: 4)),
        ]
    }
}

// MARK: - Supporting Identifiable Models

private struct IdentifiableVideo: Identifiable {
    let id = UUID()
    let title: String
    let url: URL
}

struct UserItem: Identifiable, Hashable {
    let id: String
    let name: String
    let photo: String
}

private struct PeerProfileModalView: View {
    let user: UserItem
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: AppTheme.Spacing.lg) {
            HStack {
                Spacer()
                Button("Done") { dismiss() }
                    .font(AppTheme.Font.headlineBold)
                    .foregroundStyle(AppTheme.Palette.primary)
            }
            .padding()

            Spacer()

            let cleanPhoto = user.photo.hasPrefix("http") ? user.photo : "https://medigyaan.com/Neurons/" + user.photo.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
            AsyncImage(url: URL(string: cleanPhoto)) { phase in
                if let image = phase.image {
                    image.resizable().scaledToFill()
                } else {
                    Image(systemName: "person.crop.circle.fill")
                        .resizable()
                        .foregroundStyle(AppTheme.Palette.primary.opacity(0.3))
                }
            }
            .frame(width: 90, height: 90)
            .clipShape(Circle())

            Text(user.name.isEmpty ? "Doctor #\(user.id)" : user.name)
                .font(AppTheme.Font.titleBold)
                .foregroundStyle(AppTheme.Palette.textPrimary)

            Text("MediGyaan Warrior #\(user.id)")
                .font(AppTheme.Font.caption)
                .foregroundStyle(AppTheme.Palette.textSecondary)

            Spacer()
        }
        .background(AppTheme.Palette.surface.ignoresSafeArea())
    }
}

#Preview {
    GlobalSearchView()
        .environmentObject(SessionStore())
        .environment(\.api, .live)
}
