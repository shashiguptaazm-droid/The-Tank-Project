import SwiftUI

// MARK: - TopicSelector.kt

/// Ports `TopicSelector.SearchItem`: one `subject → topic` row as returned by
/// `https://medigyaan.com/Neurons/api/topicsearch.php` under the `data` key.
///
/// Android declared it as a `data class` whose `toString()` produced the row
/// label; that string is reproduced by ``label``.
struct TopicSearchItem: Hashable, Identifiable {

    let subject: String
    let topic: String
    /// Optional `count` / `question_count` column, used by the
    /// King-of-the-Topic lock. `topicsearch.php` sends only `subject` and
    /// `topic`, so this is `0` for that endpoint and the lock therefore holds —
    /// an unknown question count is never enough to unlock a battle.
    let questionCount: Int

    /// Android's `ArrayAdapter` had no stable ids, so this is derived rather
    /// than server-assigned.
    var id: String { "\(subject) \u{2192} \(topic)" }

    init(subject: String, topic: String, questionCount: Int = 0) {
        self.subject = subject
        self.topic = topic
        self.questionCount = questionCount
    }

    /// `SearchItem.toString()` — `"\(subject) → \(topic)"`, used verbatim as the
    /// row text and as the mode-dialog title in `showModeDialog`.
    var label: String { "\(subject) \u{2192} \(topic)" }

    /// Bridges a search hit to the catalogue model `QuizListView` consumes.
    var topicModel: Topic {
        Topic(
            id: topic.hashValue,
            name: topic,
            subject: subject,
            iconName: "book.fill",
            questionCount: questionCount
        )
    }
}

/// Ports the three entries of `TopicSelector.showModeDialog`'s `modes` array,
/// plus the extra `MODE` strings `DashboardActivity.showTopicSelectorForMode`
/// passes alongside them. `rawValue` is the Android `putExtra("MODE", …)` value
/// verbatim.
enum TopicLaunchMode: String, CaseIterable, Hashable {

    // Raw values are the Android `putExtra("MODE", …)` strings verbatim, so
    // `TopicLaunchMode(rawValue:)` round-trips a literal MODE extra.

    /// `showModeDialog` index 0 → `ClassicGameActivity`, `MODE = "MATCHMAKING"`.
    case matchmaking = "MATCHMAKING"
    /// `showModeDialog` index 1 → `TopicChallengeSelectionActivity`, `MODE = "CHALLENGE"`.
    case challenge = "CHALLENGE"
    /// `showModeDialog` index 2 → `MCQActivity`, `MODE = "PRACTICE"`.
    case practice = "PRACTICE"
    /// `DashboardActivity.cardKingOfTopic`, `MODE = "KING_OF_TOPIC"`.
    case kingOfTopic = "KING_OF_TOPIC"
    /// `DashboardActivity` subject-survival card, `MODE = "SURVIVAL"`.
    case survival = "SURVIVAL"
    /// `DashboardActivity.showCustomModeBattleDialog`, `MODE = "CUSTOM_BATTLE"`.
    case customBattle = "CUSTOM_BATTLE"

    /// The string `showModeDialog` writes into the AlertDialog items array.
    var title: String {
        switch self {
        case .matchmaking: return "Matchmaking"
        case .challenge: return "Challenge Mode"
        case .practice: return "Practice Mode"
        case .kingOfTopic: return "King of the Topic"
        case .survival: return "Subject Survival"
        case .customBattle: return "Custom Mode Battle"
        }
    }

    /// The literal written to the `MODE` intent extra.
    var androidMode: String {
        rawValue
    }
}

/// Ports the King-of-the-Topic eligibility gate from
/// `DashboardActivity.TopicSelectorList`.
///
/// Kotlin, verbatim:
///
/// ```kotlin
/// val isLocked = mode == "KING_OF_TOPIC" && topic.count < 200
/// …
/// Text(text = "Need 200 Qs (${topic.count} now)", color = Color.Red)
/// ```
///
/// Only ``TopicLaunchMode/kingOfTopic`` locks; every other mode is ungated.
enum TopicLockPolicy {

    /// `topic.count < 200` — the minimum question bank a topic needs to be
    /// crowned.
    static let kingOfTopicQuestionThreshold = 200

    static func isLocked(mode: TopicLaunchMode, questionCount: Int) -> Bool {
        mode == .kingOfTopic && questionCount < kingOfTopicQuestionThreshold
    }

    /// Android bridges a `String` mode here; this overload keeps the literal
    /// `MODE` extra usable from call sites that only carry the raw value.
    static func isLocked(androidMode: String, questionCount: Int) -> Bool {
        guard let mode = TopicLaunchMode(rawValue: androidMode) else { return false }
        return isLocked(mode: mode, questionCount: questionCount)
    }

    /// `"Need 200 Qs (42 now)"` — the red 9sp caption under a locked chip.
    static func lockNote(questionCount: Int) -> String {
        "Need \(kingOfTopicQuestionThreshold) Qs (\(questionCount) now)"
    }
}

/// Ports `TopicSelector` (`activity_topicsearch.xml`) in full: the 400 ms
/// debounce, the two-character minimum, the Firestore-backed 24-hour response
/// cache, the `success`/`data` envelope, and the three-way mode dialog that
/// hands the picked topic to matchmaking, challenge or practice.
struct TopicSearchView: View {

    /// Android had no mode on this screen; the default keeps the
    /// `showModeDialog` three-option behaviour for every existing call site.
    var mode: TopicLaunchMode = .matchmaking

    @State private var searchText = ""
    @State private var results: [TopicSearchItem] = []
    @State private var isSearching = false
    @State private var pendingSelection: TopicSearchItem?
    @State private var path: [TopicLaunchRoute] = []
    @State private var errorMessage: String?

    /// `handler.postDelayed(runnable, 400)`.
    private static let debounceNanoseconds: UInt64 = 400_000_000

    /// `if (query.length >= 2)` — anything shorter clears the list.
    private static let minimumQueryLength = 2

    var body: some View {
        Group {
            if results.isEmpty {
                if isSearching {
                    LoadingStateView(message: "Searching topics…")
                } else {
                    // `emptyText` in activity_topicsearch.xml carries exactly
                    // this string; Kotlin declared the view but never toggled it.
                    EmptyStateView(
                        title: "No results found",
                        message: self.hint,
                        systemImage: "magnifyingglass"
                    )
                }
            } else {
                resultList
            }
        }
        .screenBackground()
        .navigationTitle("Find a Topic")
        .toolbar(.visible, for: .navigationBar)
        .navigationBarTitleDisplayMode(.inline)
        .searchable(text: $searchText, prompt: Text(Self.searchPrompt))
        .errorAlert(message: $errorMessage)
        .onChange(of: searchText) { newValue in
            Task { await runSearch(newValue) }
        }
        .navigationDestination(for: TopicLaunchRoute.self) { route in
            destination(for: route)
        }
        .confirmationDialog(dialogTitle, isPresented: modeDialogBinding, titleVisibility: .visible) {
            ForEach(TopicLaunchMode.allCases, id: \.self) { option in
                Button(option.title) { choose(option) }
            }
            Button("Cancel", role: .cancel) {}
        }
    }

    // MARK: - Rows

    private var resultList: some View {
        ScrollView {
            LazyVStack(spacing: 0) {
                ForEach(results.indices, id: \.self) { index in
                    resultRow(at: index)
                    if index < results.count - 1 {
                        Divider().background(AppTheme.Palette.divider)
                    }
                }
            }
            // `android:paddingTop="8dp"` on the ListView.
            .padding(.top, AppTheme.Spacing.sm)
        }
    }

    private func resultRow(at index: Int) -> some View {
        let item = results[index]
        let locked = TopicLockPolicy.isLocked(mode: mode, questionCount: item.questionCount)
        return Button {
            showModeDialog(for: item)
        } label: {
            TopicSearchResultRow(item: item, isLocked: locked)
        }
        .buttonStyle(.plain)
        .disabled(locked)
        .opacity(locked ? 0.5 : 1)
    }

    /// `showModeDialog` — tapping a row opens the mode chooser for that row.
    private func showModeDialog(for item: TopicSearchItem) {
        RemoteLogger.log(
            tag: "TopicSelector_Select",
            message: "User picked topic: \(item.label)"
        )
        pendingSelection = item
    }

    private var dialogTitle: String {
        pendingSelection?.label ?? ""
    }

    private var modeDialogBinding: Binding<Bool> {
        Binding(
            get: { self.pendingSelection != nil },
            set: { if !$0 { self.pendingSelection = nil } }
        )
    }

    private func choose(_ option: TopicLaunchMode) {
        guard let item = pendingSelection else { return }
        RemoteLogger.log(
            tag: "TopicSelector_Mode",
            message: "Mode '\(option.androidMode)' chosen for \(item.label)"
        )
        path.append(TopicLaunchRoute(mode: option, item: item))
    }

    /// The three intent targets of `openClassicGame` / `openChallengeSelection`
    /// / `openPracticeMode`, plus `DashboardActivity`'s four extra modes.
    @ViewBuilder
    private func destination(for route: TopicLaunchRoute) -> some View {
        switch route.mode {
        case .matchmaking, .challenge:
            MatchmakingArenaFlowView(subject: route.item.subject, topic: route.item.topic)
        case .practice, .kingOfTopic, .survival, .customBattle:
            QuizListView(topic: route.item.topicModel)
        }
    }

    // MARK: - Search

    /// `TextWatcher.onTextChanged` → debounce 400 ms → require two characters.
    @MainActor
    private func runSearch(_ text: String) async {
        let trimmed = text.trimmingCharacters(in: .whitespaces)
        guard trimmed.count >= Self.minimumQueryLength else {
            results = []
            isSearching = false
            return
        }
        isSearching = true
        try? await Task.sleep(nanoseconds: Self.debounceNanoseconds)
        guard !Task.isCancelled else { return }
        await performSearch(trimmed)
    }

    /// `TopicSelector.search(query)`: paint the cached body first (errors
    /// suppressed, exactly as `showErrors = false`), then refresh from the
    /// network and write that body back through the 24-hour cache.
    @MainActor
    private func performSearch(_ query: String) async {
        let cacheKey = "GET:\(BackendEndpoints.base)api/topicsearch.php?q=\(Self.escapedQuery(query))"

        if let cached = await FirebaseOnlineCache.getString(
            key: cacheKey,
            maxAgeMs: FirebaseOnlineCache.TTL.topics
        ), let object = Self.jsonObject(from: cached) {
            apply(object, showErrors: false)
        }

        do {
            let json = try await HTTPClient.shared.getObject(.topicSearch, query: ["q": query])
            FirebaseOnlineCache.putString(key: cacheKey, response: Self.jsonString(from: json))
            apply(json, showErrors: true)
        } catch {
            // Android showed a Toast here rather than an empty list.
            errorMessage = "Error fetching data"
        }
        isSearching = false
    }

    /// `applySearchResponse`: `success == true` reads `data`, `success == false`
    /// clears the list, and a malformed body only surfaces a message when
    /// `showErrors` is set.
    private func apply(_ json: [String: Any], showErrors: Bool) {
        guard let parsed = Self.parse(json) else {
            if showErrors { errorMessage = "Invalid server response" }
            return
        }
        results = parsed
    }

    /// Returns `nil` when the envelope or any row is malformed, which is how
    /// Kotlin's `try/catch` around `getString("subject")` / `getString("topic")`
    /// surfaced.
    private static func parse(_ json: [String: Any]) -> [TopicSearchItem]? {
        guard (json["success"] as? Bool) == true else { return [] }
        guard let rows = json["data"] as? [[String: Any]] else { return nil }
        var items: [TopicSearchItem] = []
        items.reserveCapacity(rows.count)
        for row in rows {
            guard let subject = row["subject"] as? String,
                  let topic = row["topic"] as? String else { return nil }
            let count = row["count"] as? Int ?? row["question_count"] as? Int ?? 0
            items.append(TopicSearchItem(subject: subject, topic: topic, questionCount: count))
        }
        return items
    }

    /// `query.replace(" ", "%20")` — the only escaping `TopicSelector` applied
    /// before building the cache key.
    private static func escapedQuery(_ query: String) -> String {
        query.replacingOccurrences(of: " ", with: "%20")
    }

    private static func jsonObject(from body: String) -> [String: Any]? {
        guard let data = body.data(using: .utf8),
              let parsed = try? JSONSerialization.jsonObject(with: data) else { return nil }
        return parsed as? [String: Any]
    }

    private static func jsonString(from json: [String: Any]) -> String {
        guard JSONSerialization.isValidJSONObject(json),
              let data = try? JSONSerialization.data(withJSONObject: json) else { return "" }
        return String(decoding: data, as: UTF8.self)
    }

    // MARK: - Strings

    /// `android:hint` on the `TextInputLayout` in activity_topicsearch.xml.
    private static let searchPrompt = "Search subject or topic..."

    private var hint: String {
        searchText.trimmingCharacters(in: .whitespaces).count < Self.minimumQueryLength
            ? "Type at least \(Self.minimumQueryLength) characters to search subjects and topics."
            : "Try a different search term."
    }

    // MARK: - Route

    /// Stands in for the three `Intent`s: SwiftUI needs the chosen subject and
    /// topic to travel with the destination, where Android carried them as
    /// `putExtra` values.
    private struct TopicLaunchRoute: Hashable {
        let mode: TopicLaunchMode
        let item: TopicSearchItem
    }
}

/// Ports the `android.R.layout.simple_list_item_1` row `TopicSelector` fed from
/// its `ArrayAdapter`, plus the red `Need 200 Qs (n now)` caption and dimming
/// that `TopicSelectorList` applied to a locked King-of-the-Topic chip.
struct TopicSearchResultRow: View {

    let item: TopicSearchItem
    var isLocked: Bool = false

    var body: some View {
        HStack(spacing: AppTheme.Spacing.md) {
            AndroidIcon(.ic_search, size: 20, tint: AppTheme.Palette.textSecondary)

            Text(item.label)
                .font(AppTheme.Font.body)
                .foregroundStyle(isLocked ? AppTheme.Palette.textMuted : AppTheme.Palette.textPrimary)
                .lineLimit(2)
                .multilineTextAlignment(.leading)

            Spacer(minLength: 0)

            if isLocked {
                Text(TopicLockPolicy.lockNote(questionCount: item.questionCount))
                    .font(AppTheme.Font.micro)
                    .foregroundStyle(AppTheme.Palette.danger)
                    .multilineTextAlignment(.trailing)
            }
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, AppTheme.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .contentShape(Rectangle())
    }
}

// MARK: - Topic catalogue

/// Topic catalogue backed by `get_topics.php` and `api/topicsearch.php`.
///
/// The searchable full-catalogue list. The Android activity this file pairs
/// with — `TopicSelector`, whose three-mode search is ported by
/// ``TopicSearchView`` above — is reachable from the "Find" toolbar action.
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
            .toolbar(.visible, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    NavigationLink {
                        TopicSearchView()
                    } label: {
                        Text("Find").font(AppTheme.Font.callout)
                    }
                }
            }
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
                    .simultaneousGesture(TapGesture().onEnded {
                        RemoteLogger.log(
                            tag: "TopicsView_Select",
                            message: "User tapped topic: \(topic.name) (ID: \(topic.id))"
                        )
                    })
                }
            }
            .padding(AppTheme.Spacing.md)
        }
    }

    // MARK: - Networking

    @MainActor
    private func load() async {
        RemoteLogger.log(tag: "TopicsView_load", message: "Fetching curriculum topics catalogue")
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
        RemoteLogger.log(tag: "TopicsView_search", message: "Searching topics for query: '\(trimmed)'")
        searchResults = (try? await api.study.searchTopics(query: trimmed)) ?? []
        isSearching = false
    }
}

/// A single row in the topic list.
///
/// `lockNote` is the King-of-the-Topic affordance ported from
/// `DashboardActivity.TopicSelectorList`; when it is non-`nil` the row is
/// painted in the muted Android `Color.Gray` style and is not tappable.
struct TopicRow: View {
    let topic: Topic
    var tint: Color = AppTheme.Palette.primary
    var lockNote: String? = nil

    private var isLocked: Bool { lockNote != nil || topic.isLocked }

    var body: some View {
        CardContainer(padding: AppTheme.Spacing.sm) {
            HStack(spacing: AppTheme.Spacing.md) {
                ZStack {
                    RoundedRectangle(cornerRadius: AppTheme.Radius.sm, style: .continuous)
                        .fill(isLocked ? AppTheme.Palette.textMuted.opacity(0.15) : tint.opacity(0.15))
                    Image(systemName: isLocked ? "lock.fill" : (topic.iconName.isEmpty ? "book.fill" : topic.iconName))
                        .font(.system(size: 20, weight: .semibold))
                        .foregroundStyle(isLocked ? AppTheme.Palette.textMuted : tint)
                }
                .frame(width: 44, height: 44)

                VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
                    Text(topic.name)
                        .font(AppTheme.Font.callout.weight(.semibold))
                        .foregroundStyle(isLocked ? AppTheme.Palette.textMuted : AppTheme.Palette.textPrimary)
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

                    if let lockNote {
                        Text(lockNote)
                            .font(AppTheme.Font.micro)
                            .foregroundStyle(AppTheme.Palette.danger)
                    }
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(AppTheme.Palette.textSecondary.opacity(0.6))
            }
            .opacity(isLocked ? 0.5 : 1)
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
        .toolbar(.visible, for: .navigationBar)
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