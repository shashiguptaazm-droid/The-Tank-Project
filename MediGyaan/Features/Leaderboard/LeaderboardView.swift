import SwiftUI

/// Leaderboard. Ports `LeaderboardActivity` / `RankActivity` / `ScoresActivity`.
struct LeaderboardView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api

    private enum Scope: String, CaseIterable, Identifiable {
        case global = "Global"
        case weekly = "This Week"
        case college = "My College"

        var id: String { rawValue }
    }

    @State private var scope: Scope = .global
    @State private var state: LoadState<[LeaderboardEntry]> = .idle

    var body: some View {
        VStack(spacing: 0) {
            Picker("Scope", selection: $scope) {
                ForEach(Scope.allCases) { scope in
                    Text(scope.rawValue).tag(scope)
                }
            }
            .pickerStyle(.segmented)
            .padding(AppTheme.Spacing.md)
            .onChange(of: scope) { _ in Task { await load() } }

            Group {
                switch state {
                case .idle, .loading:
                    LoadingStateView(message: "Loading leaderboard…")
                case let .failed(message):
                    ErrorStateView(message: message) { Task { await load() } }
                case .loaded:
                    if (state.value ?? []).isEmpty {
                        EmptyStateView(
                            title: "No rankings yet",
                            message: "Complete a few tests to appear on the leaderboard.",
                            systemImage: "trophy"
                        )
                    } else {
                        list
                    }
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .screenBackground()
        .navigationTitle("Leaderboard")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
        .refreshable { await load() }
    }

    private var list: some View {
        ScrollView {
            LazyVStack(spacing: AppTheme.Spacing.sm) {
                // Podium for the top three.
                if let entries = state.value, entries.count >= 3 {
                    podium(Array(entries.prefix(3)))
                }

                ForEach(state.value ?? []) { entry in
                    LeaderboardRow(entry: entry, isCurrentUser: entry.id == session.userId)
                }
            }
            .padding(AppTheme.Spacing.md)
        }
    }

    private func podium(_ entries: [LeaderboardEntry]) -> some View {
        HStack(alignment: .bottom, spacing: AppTheme.Spacing.sm) {
            ForEach(Array(entries.enumerated()), id: \.element.id) { index, entry in
                VStack(spacing: AppTheme.Spacing.xs) {
                    AvatarView(url: entry.avatarURL, name: entry.name, size: index == 0 ? 58 : 48)
                    Text(entry.name)
                        .font(AppTheme.Font.caption.weight(.semibold))
                        .lineLimit(1)
                    Text("\(entry.score)")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary)

                    Text("#\(entry.rank)")
                        .font(.system(size: 12, weight: .bold))
                        .padding(.horizontal, AppTheme.Spacing.sm)
                        .padding(.vertical, 3)
                        .background(
                            Capsule().fill(podiumColor(index).opacity(0.18))
                        )
                        .foregroundStyle(podiumColor(index))
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, AppTheme.Spacing.sm)
                .background(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.md, style: .continuous)
                        .fill(podiumColor(index).opacity(0.07))
                )
            }
        }
    }

    private func podiumColor(_ index: Int) -> Color {
        switch index {
        case 0: return AppTheme.Palette.warning
        case 1: return AppTheme.Palette.info
        default: return AppTheme.Palette.accent
        }
    }

    @MainActor
    private func load() async {
        let userId = session.userId
        guard userId > 0 else { return }
        let selectedScope = scope.rawValue
        state = await LoadState.result { [api] in
            try await api.study.leaderboard(userId: userId, scope: selectedScope)
        }
    }
}

/// A single leaderboard row.
struct LeaderboardRow: View {
    let entry: LeaderboardEntry
    var isCurrentUser: Bool = false

    var body: some View {
        CardContainer(padding: AppTheme.Spacing.sm) {
            HStack(spacing: AppTheme.Spacing.md) {
                Text("\(entry.rank)")
                    .font(.system(size: 15, weight: .bold, design: .rounded))
                    .foregroundStyle(AppTheme.Palette.textSecondary)
                    .frame(width: 32)

                AvatarView(url: entry.avatarURL, name: entry.name, size: 38)

                VStack(alignment: .leading, spacing: 2) {
                    Text(entry.name.isEmpty ? "Student" : entry.name)
                        .font(AppTheme.Font.callout.weight(isCurrentUser ? .bold : .medium))
                        .lineLimit(1)
                    Text("\(entry.score) points")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }

                Spacer()

                if isCurrentUser {
                    TagBadge(text: "You", tint: AppTheme.Palette.primary)
                }
            }
        }
    }
}

/// Attempt history. Ports `QuestionAttemptsActivity` / `AccuracyHistoryManager` display.
struct HistoryView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api

    @State private var state: LoadState<[AttemptSummary]> = .idle

    var body: some View {
        Group {
            switch state {
            case .idle, .loading:
                LoadingStateView(message: "Loading history…")
            case let .failed(message):
                ErrorStateView(message: message) { Task { await load() } }
            case .loaded:
                if (state.value ?? []).isEmpty {
                    EmptyStateView(
                        title: "No attempts yet",
                        message: "Your completed tests will show up here.",
                        systemImage: "clock"
                    )
                } else {
                    list
                }
            }
        }
        .screenBackground()
        .navigationTitle("Attempt history")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
        .refreshable { await load() }
    }

    private var list: some View {
        ScrollView {
            LazyVStack(spacing: AppTheme.Spacing.sm) {
                ForEach(state.value ?? []) { attempt in
                    CardContainer(padding: AppTheme.Spacing.sm) {
                        HStack {
                            VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
                                Text(attempt.quizTitle.isEmpty ? "Practice test" : attempt.quizTitle)
                                    .font(AppTheme.Font.callout.weight(.medium))
                                    .lineLimit(1)
                                Text("\(attempt.correct) correct · \(attempt.wrong) wrong")
                                    .font(AppTheme.Font.caption)
                                    .foregroundStyle(AppTheme.Palette.textSecondary)
                                if !attempt.date.isEmpty {
                                    Text(attempt.date)
                                        .font(AppTheme.Font.caption)
                                        .foregroundStyle(AppTheme.Palette.textSecondary)
                                }
                            }
                            Spacer()
                            TagBadge(
                                text: String(format: "%.0f%%", attempt.accuracy),
                                tint: attempt.accuracy >= 60
                                    ? AppTheme.Palette.success
                                    : AppTheme.Palette.warning
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
        state = await LoadState.result { [api] in
            try await api.study.attempts(userId: userId)
        }
    }
}

#Preview {
    NavigationStack {
        LeaderboardView()
            .environmentObject(SessionStore())
            .environment(\.api, .live)
    }
}
