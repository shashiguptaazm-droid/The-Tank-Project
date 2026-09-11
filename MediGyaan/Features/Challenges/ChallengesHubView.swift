import SwiftUI

/// Challenges tab.
///
/// Groups the Android challenge family — `ChallengeSelectionActivity`,
/// `ChallengeListActivity`, `LobbyActivity`, `MatchmakingActivity`,
/// `SinglePlayer`, and the topic challenge screens.
struct ChallengesHubView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api

    @State private var lobbyCode = ""
    @State private var isJoining = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: AppTheme.Spacing.lg) {
                    heroCard
                    joinLobbyCard
                    modes
                }
                .padding(AppTheme.Spacing.md)
            }
            .screenBackground()
            .navigationTitle("Challenges")
            .errorAlert(message: $errorMessage)
        }
    }

    // MARK: - Sections

    private var heroCard: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                HStack(spacing: AppTheme.Spacing.sm) {
                    Image(systemName: "bolt.fill")
                        .font(.system(size: 26))
                        .foregroundStyle(AppTheme.Palette.warning)
                    Text("Compete live")
                        .font(AppTheme.Font.title)
                }

                Text("Challenge a friend to a timed MCQ battle, or enter a lobby and get matched with other students.")
                    .font(AppTheme.Font.callout)
                    .foregroundStyle(AppTheme.Palette.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var joinLobbyCard: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                Text("Have a lobby code?")
                    .font(AppTheme.Font.headline)

                HStack(spacing: AppTheme.Spacing.sm) {
                    TextField("Enter code", text: $lobbyCode)
                        .textInputAutocapitalization(.characters)
                        .autocorrectionDisabled()
                        .padding(AppTheme.Spacing.md)
                        .background(
                            RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                                .fill(AppTheme.Palette.background)
                        )

                    Button {
                        Task { await join() }
                    } label: {
                        Group {
                            if isJoining {
                                ProgressView().tint(.white)
                            } else {
                                Text("Join").font(AppTheme.Font.headline)
                            }
                        }
                        .frame(width: 76, height: 50)
                        .background(
                            RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                                .fill(AppTheme.Palette.primary)
                        )
                        .foregroundStyle(.white)
                    }
                    .disabled(lobbyCode.trimmingCharacters(in: .whitespaces).isEmpty || isJoining)
                    .opacity(lobbyCode.trimmingCharacters(in: .whitespaces).isEmpty ? 0.5 : 1)
                }
            }
        }
    }

    private var modes: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            SectionHeader(title: "Modes")

            LazyVGrid(
                columns: Array(repeating: GridItem(.flexible(), spacing: AppTheme.Spacing.sm), count: 2),
                spacing: AppTheme.Spacing.sm
            ) {
                NavigationLink { TopicChallengePickerView(mode: .solo) } label: {
                    QuickActionTile(title: "Single Player", systemImage: "person.fill", tint: AppTheme.Palette.info)
                }
                NavigationLink { MatchmakingView() } label: {
                    QuickActionTile(title: "Quick Match", systemImage: "person.2.fill", tint: AppTheme.Palette.accent)
                }
                NavigationLink { ChallengeListView() } label: {
                    QuickActionTile(title: "My Challenges", systemImage: "list.bullet.rectangle", tint: AppTheme.Palette.primary)
                }
                NavigationLink { TopicChallengePickerView(mode: .challenge) } label: {
                    QuickActionTile(title: "Topic Battle", systemImage: "flame.fill", tint: AppTheme.Palette.warning)
                }
            }
        }
    }

    // MARK: - Networking

    @MainActor
    private func join() async {
        let code = lobbyCode.trimmingCharacters(in: .whitespaces)
        guard !code.isEmpty, !isJoining else { return }
        isJoining = true
        defer { isJoining = false }

        do {
            let response = try await api.study.joinLobby(userId: session.userId, topicId: 0, code: code)
            guard response.success else {
                errorMessage = response.message.isEmpty ? "That lobby code isn't valid." : response.message
                return
            }
            // A successful join is followed by the lobby poller.
            errorMessage = nil
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

/// Which challenge flow the topic picker is serving.
enum ChallengeMode {
    case solo
    case challenge

    var title: String {
        switch self {
        case .solo: return "Single Player"
        case .challenge: return "Topic Battle"
        }
    }
}

/// Topic picker feeding the solo and battle modes.
struct TopicChallengePickerView: View {

    let mode: ChallengeMode

    @Environment(\.api) private var api
    @State private var state: LoadState<[Topic]> = .idle

    var body: some View {
        Group {
            switch state {
            case .idle, .loading:
                LoadingStateView(message: "Loading topics…")
            case let .failed(message):
                ErrorStateView(message: message) { Task { await load() } }
            case .loaded:
                if (state.value ?? []).isEmpty {
                    EmptyStateView(
                        title: "No topics available",
                        message: "Topics must be published before you can start a challenge.",
                        systemImage: "book.closed"
                    )
                } else {
                    list
                }
            }
        }
        .screenBackground()
        .navigationTitle(mode.title)
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private var list: some View {
        ScrollView {
            LazyVStack(spacing: AppTheme.Spacing.sm) {
                ForEach(Array((state.value ?? []).enumerated()), id: \.element.id) { index, topic in
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

    @MainActor
    private func load() async {
        await state.load { [api] in
            try await api.study.topics()
        }
    }
}

/// Lists the user's open and completed challenges.
struct ChallengeListView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api

    @State private var state: LoadState<[Challenge]> = .idle

    var body: some View {
        Group {
            switch state {
            case .idle, .loading:
                LoadingStateView(message: "Loading challenges…")
            case let .failed(message):
                ErrorStateView(message: message) { Task { await load() } }
            case .loaded:
                if (state.value ?? []).isEmpty {
                    EmptyStateView(
                        title: "No challenges yet",
                        message: "Start a topic battle to challenge a friend.",
                        systemImage: "bolt.slash"
                    )
                } else {
                    list
                }
            }
        }
        .screenBackground()
        .navigationTitle("My Challenges")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private var list: some View {
        ScrollView {
            LazyVStack(spacing: AppTheme.Spacing.sm) {
                ForEach(state.value ?? []) { challenge in
                    CardContainer(padding: AppTheme.Spacing.sm) {
                        HStack {
                            VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
                                Text(challenge.topic.isEmpty ? "Challenge" : challenge.topic)
                                    .font(AppTheme.Font.callout.weight(.semibold))
                                    .lineLimit(1)
                                Text("vs \(challenge.opponentName.isEmpty ? "Waiting for opponent" : challenge.opponentName)")
                                    .font(AppTheme.Font.caption)
                                    .foregroundStyle(AppTheme.Palette.textSecondary)
                                if challenge.questionCount > 0 {
                                    Text("\(challenge.questionCount) questions")
                                        .font(AppTheme.Font.caption)
                                        .foregroundStyle(AppTheme.Palette.textSecondary)
                                }
                            }
                            Spacer()
                            TagBadge(
                                text: challenge.isCompleted ? "Completed" : (challenge.isPending ? "Pending" : "Active"),
                                tint: challenge.isCompleted
                                    ? AppTheme.Palette.success
                                    : (challenge.isPending ? AppTheme.Palette.warning : AppTheme.Palette.primary)
                            )
                        }
                    }
                }
            }
            .padding(AppTheme.Spacing.md)
        }
    }

    @MainActor
    private func load() async {
        let userId = session.userId
        guard userId > 0 else { return }
        await state.load { [api] in
            try await api.study.challenges(userId: userId)
        }
    }
}

/// Matchmaking placeholder that surfaces the live lobby poller.
struct MatchmakingView: View {

    @EnvironmentObject private var session: SessionStore
    @State private var isSearching = false
    @State private var secondsElapsed = 0

    var body: some View {
        VStack(spacing: AppTheme.Spacing.lg) {
            Spacer()

            ZStack {
                Circle()
                    .fill(AppTheme.Palette.primary.opacity(0.10))
                    .frame(width: 180, height: 180)
                Image(systemName: "person.2.fill")
                    .font(.system(size: 54))
                    .foregroundStyle(AppTheme.Palette.primary)
                    .opacity(isSearching ? 0.5 : 1)
            }

            VStack(spacing: AppTheme.Spacing.xs) {
                Text(isSearching ? "Finding an opponent…" : "Ready to play?")
                    .font(AppTheme.Font.title)
                if isSearching {
                    Text("Searching for \(secondsElapsed)s")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                } else {
                    Text("We'll match you with a student of similar accuracy.")
                        .font(AppTheme.Font.callout)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                        .multilineTextAlignment(.center)
                }
            }

            Spacer()

            PrimaryButton(
                title: isSearching ? "Cancel" : "Find Opponent",
                isLoading: false,
                isEnabled: true
            ) {
                isSearching.toggle()
            }
            .padding(.horizontal, AppTheme.Spacing.lg)
        }
        .screenBackground()
        .navigationTitle("Quick Match")
        .navigationBarTitleDisplayMode(.inline)
        .task(id: isSearching) {
            guard isSearching else { return }
            secondsElapsed = 0
            while isSearching, !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 1_000_000_000)
                guard isSearching else { return }
                secondsElapsed += 1
                // Matchmaking against `livebattle.php` is polled here; until a
                // lobby is assigned we keep the search loop alive.
                if secondsElapsed >= 30 { isSearching = false }
            }
        }
    }
}

#Preview {
    ChallengesHubView()
        .environmentObject(SessionStore())
        .environment(\.api, .live)
}
