import SwiftUI

/// Social hub: feed and messenger.
///
/// Groups the Android `NewsFeedActivity` and `MessengerActivity` screens. The
/// messenger itself lives in `MessengerView.swift` — it is also a top-level tab.
struct SocialHubView: View {

    private enum Section: String, CaseIterable, Identifiable {
        case feed = "Feed"
        case messages = "Messages"

        var id: String { rawValue }
    }

    @State private var section: Section = .feed

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                Picker("Section", selection: $section) {
                    ForEach(Section.allCases) { section in
                        Text(section.rawValue).tag(section)
                    }
                }
                .pickerStyle(.segmented)
                .padding(AppTheme.Spacing.md)

                switch section {
                case .feed:
                    NewsFeedView()
                case .messages:
                    MessengerView()
                }
            }
            .screenBackground()
            .navigationTitle("Social")
        }
    }
}

/// The news feed, backed by `api/fetch_posts.php`.
struct NewsFeedView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api

    @State private var state: LoadState<[Post]> = .idle
    @State private var isComposing = false
    @State private var draft = ""
    @State private var isPosting = false
    @State private var errorMessage: String?

    var body: some View {
        Group {
            switch state {
            case .idle, .loading:
                LoadingStateView(message: "Loading feed…")
            case let .failed(message):
                ErrorStateView(message: message) { Task { await load() } }
            case .loaded:
                if (state.value ?? []).isEmpty {
                    EmptyStateView(
                        title: "Nothing here yet",
                        message: "Be the first to share something with the community.",
                        systemImage: "newspaper",
                        actionTitle: "Create a post"
                    ) {
                        isComposing = true
                    }
                } else {
                    feed
                }
            }
        }
        .sheet(isPresented: $isComposing) { composer }
        .errorAlert(message: $errorMessage)
        .task { await load() }
    }

    private var feed: some View {
        ScrollView {
            LazyVStack(spacing: AppTheme.Spacing.md) {
                ForEach(state.value ?? []) { post in
                    PostCard(post: post) { liked in
                        Task { await setLiked(post: post, liked: liked) }
                    }
                }
            }
            .padding(AppTheme.Spacing.lg)
        }
        .refreshable { await load() }
    }

    private var composer: some View {
        NavigationStack {
            VStack(spacing: AppTheme.Spacing.md) {
                TextEditor(text: $draft)
                    .frame(minHeight: 160)
                    .padding(AppTheme.Spacing.sm)
                    .background(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.field, style: .continuous)
                            .fill(AppTheme.Palette.background)
                    )
                    .overlay(alignment: .topLeading) {
                        if draft.isEmpty {
                            Text("Share an update with your peers…")
                                .font(AppTheme.Font.body)
                                .foregroundStyle(AppTheme.Palette.textSecondary)
                                .padding(AppTheme.Spacing.md)
                                .allowsHitTesting(false)
                        }
                    }

                PrimaryButton(
                    title: "Post",
                    isLoading: isPosting,
                    isEnabled: !draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                ) {
                    Task { await createPost() }
                }

                Spacer()
            }
            .padding(AppTheme.Spacing.lg)
            .navigationTitle("New post")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        isComposing = false
                        draft = ""
                    }
                }
            }
        }
    }

    // MARK: - Networking

    private func load() async {
        let userId = session.userId
        guard userId > 0 else { return }
        await state.load { [api] in
            try await api.social.posts(userId: userId)
        }
    }

    private func setLiked(post: Post, liked: Bool) async {
        _ = try? await api.social.setLiked(
            postId: post.id,
            userId: session.userId,
            liked: liked
        )
        // Refresh so server-side counts stay authoritative.
        await load()
    }

    private func createPost() async {
        let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !isPosting else { return }
        isPosting = true
        defer { isPosting = false }

        do {
            let response = try await api.social.createPost(userId: session.userId, content: text)
            guard response.success else {
                errorMessage = response.message.isEmpty ? "Could not publish your post." : response.message
                return
            }
            draft = ""
            isComposing = false
            await load()
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

/// A feed post with a local like toggle for optimistic feedback.
struct PostCard: View {

    let post: Post
    let onLike: (Bool) -> Void

    @State private var isLiked: Bool
    @State private var likeCount: Int

    init(post: Post, onLike: @escaping (Bool) -> Void) {
        self.post = post
        self.onLike = onLike
        _isLiked = State(initialValue: post.isLiked)
        _likeCount = State(initialValue: post.likeCount)
    }

    var body: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                HStack(spacing: AppTheme.Spacing.sm) {
                    AvatarView(url: post.authorAvatarURL, name: post.authorName, size: 42)
                    VStack(alignment: .leading, spacing: 1) {
                        Text(post.authorName.isEmpty ? "Student" : post.authorName)
                            .font(AppTheme.Font.callout.weight(.semibold))
                        if !post.createdAt.isEmpty {
                            Text(post.createdAt)
                                .font(AppTheme.Font.caption)
                                .foregroundStyle(AppTheme.Palette.textSecondary)
                        }
                    }
                    Spacer()
                }

                if !post.content.isEmpty {
                    Text(post.content)
                        .font(AppTheme.Font.body)
                        .fixedSize(horizontal: false, vertical: true)
                }

                if let imageURL = post.imageURL {
                    AsyncImage(url: imageURL) { image in
                        image.resizable().scaledToFill()
                    } placeholder: {
                        Rectangle().fill(AppTheme.Palette.background)
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 200)
                    .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.option, style: .continuous))
                }

                Divider()

                HStack(spacing: AppTheme.Spacing.xxl) {
                    Button {
                        isLiked.toggle()
                        likeCount += isLiked ? 1 : -1
                        onLike(isLiked)
                    } label: {
                        Label(
                            "\(max(0, likeCount))",
                            systemImage: isLiked ? "heart.fill" : "heart"
                        )
                        .font(AppTheme.Font.caption.weight(.medium))
                        .foregroundStyle(isLiked ? AppTheme.Palette.error : AppTheme.Palette.textSecondary)
                    }

                    Label("\(post.commentCount)", systemImage: "bubble.right")
                        .font(AppTheme.Font.caption.weight(.medium))
                        .foregroundStyle(AppTheme.Palette.textSecondary)

                    Label("\(post.shareCount)", systemImage: "square.and.arrow.up")
                        .font(AppTheme.Font.caption.weight(.medium))
                        .foregroundStyle(AppTheme.Palette.textSecondary)

                    Spacer()
                }
                .buttonStyle(.plain)
            }
        }
    }
}

#Preview {
    SocialHubView()
        .environmentObject(SessionStore())
        .environment(\.api, .live)
}
