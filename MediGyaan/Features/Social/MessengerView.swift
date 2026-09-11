import SwiftUI

/// Messenger, backed by `messenger_api.php`.
///
/// The Android `MessengerActivity` deliberately mimics WhatsApp, so the bubble
/// and input colours come from the `whatsapp_*` tokens in `colors.xml` rather
/// than the app's Material palette:
///
/// | token | day | night |
/// |---|---|---|
/// | `whatsapp_chat_bg` | `#E5DDD5` | `#0B141A` |
/// | `whatsapp_bubble_sent` | `#D9FDD3` | `#005C4B` |
/// | `whatsapp_bubble_received` | `#FFFFFF` | `#202C33` |
/// | `message_input_bg` | `#F1F3F5` | `#1E2C33` |
///
/// This view does not own a `NavigationStack` — it is both a tab root (wrapped
/// by `AppTabView`) and a push destination from the dashboard.
///
/// Calling replaces the Android app's Jitsi Meet SDK integration: `phone` and
/// `video` toolbar buttons open a LiveKit room named from the two user ids, using
/// the same `edu_lab_rtm_<low>_<high>` scheme `MessengerActivity.getRoomName`
/// builds.
struct MessengerView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api

    @State private var conversationId = "general"
    @State private var state: LoadState<[ChatMessage]> = .idle
    @State private var draft = ""
    @State private var isSending = false
    @State private var errorMessage: String?
    @State private var pendingCall: PendingCall?

    var body: some View {
        VStack(spacing: 0) {
            messageList
            composer
        }
        .background(AppTheme.Palette.chatBackground.ignoresSafeArea())
        .navigationTitle("Messages")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItemGroup(placement: .navigationBarTrailing) {
                Button { start(.audio) } label: {
                    Image(systemName: "phone")
                }
                .disabled(peer == nil)
                .accessibilityLabel("Voice call")

                Button { start(.video) } label: {
                    Image(systemName: "video")
                }
                .disabled(peer == nil)
                .accessibilityLabel("Video call")
            }
        }
        .errorAlert(message: $errorMessage)
        .task { await load() }
        .refreshable { await load() }
        .fullScreenCover(item: $pendingCall) { call in
            CallView(
                model: CallViewModel(
                    roomName: call.room,
                    kind: call.kind,
                    peerName: call.peerName,
                    api: api,
                    session: session
                )
            )
        }
    }

    // MARK: - Calling

    /// The other person in this thread, inferred from the messages on screen.
    ///
    /// `messenger_api.php` returns a thread rather than a peer record, so the
    /// most recent message that is not ours is the only available source for the
    /// peer's id — and the peer's id is what makes the 1-on-1 room deterministic
    /// and shared with the other platform.
    private var peer: (id: Int, name: String)? {
        guard case let .loaded(messages) = state else { return nil }
        guard let last = messages.last(where: { !$0.isMine && $0.senderId > 0 }) else { return nil }
        let name = last.senderName.isEmpty ? "MediGyaan user" : last.senderName
        return (last.senderId, name)
    }

    private func start(_ kind: CallKind) {
        guard let peer else { return }
        pendingCall = PendingCall.oneToOne(
            myId: session.userId,
            peerId: peer.id,
            peerName: peer.name,
            kind: kind
        )
    }

    // MARK: - Messages

    private var messageList: some View {
        Group {
            switch state {
            case .idle, .loading:
                LoadingStateView(message: "Loading messages…")
            case let .failed(message):
                ErrorStateView(message: message) { Task { await load() } }
            case let .loaded(messages):
                if messages.isEmpty {
                    EmptyStateView(
                        title: "No messages yet",
                        message: "Start the conversation below.",
                        systemImage: "bubble.left"
                    )
                } else {
                    ScrollViewReader { proxy in
                        ScrollView {
                            LazyVStack(spacing: AppTheme.Spacing.sm) {
                                ForEach(messages) { message in
                                    MessageBubble(message: message)
                                        .id(message.id)
                                }
                            }
                            .padding(AppTheme.Spacing.md)
                        }
                        .onChange(of: messages.count) { _ in
                            if let last = messages.last {
                                withAnimation { proxy.scrollTo(last.id, anchor: .bottom) }
                            }
                        }
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Composer

    private var composer: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            TextField("Message", text: $draft, axis: .vertical)
                .lineLimit(1 ... 4)
                .padding(.horizontal, AppTheme.Spacing.lg)
                .padding(.vertical, AppTheme.Spacing.sm)
                .background(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.button, style: .continuous)
                        .fill(AppTheme.Palette.messageInput)
                )

            Button {
                Task { await send() }
            } label: {
                Group {
                    if isSending {
                        ProgressView().tint(.white)
                    } else {
                        Image(systemName: "paperplane.fill")
                    }
                }
                .frame(width: 44, height: 44)
                .background(Circle().fill(AppTheme.Palette.primary))
                .foregroundStyle(.white)
            }
            .disabled(draft.trimmingCharacters(in: .whitespaces).isEmpty || isSending)
            .opacity(draft.trimmingCharacters(in: .whitespaces).isEmpty ? 0.5 : 1)
        }
        .padding(AppTheme.Spacing.md)
        .background(AppTheme.Palette.cardBackground)
    }

    // MARK: - Networking

    @MainActor
    private func load() async {
        let userId = session.userId
        guard userId > 0 else { return }
        let thread = conversationId
        state = await LoadState.result { [api] in
            try await api.social.messages(conversationId: thread, userId: userId)
        }
    }

    @MainActor
    private func send() async {
        let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !isSending else { return }
        isSending = true
        defer { isSending = false }

        do {
            let response = try await api.social.sendMessage(
                conversationId: conversationId,
                userId: session.userId,
                text: text
            )
            guard response.success else {
                errorMessage = response.message.isEmpty ? "Message could not be sent." : response.message
                return
            }
            draft = ""
            await load()
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

/// A single chat bubble, coloured from the `whatsapp_bubble_*` tokens.
struct MessageBubble: View {
    let message: ChatMessage

    private var bubbleFill: Color {
        message.isMine ? AppTheme.Palette.bubbleSent : AppTheme.Palette.bubbleReceived
    }

    private var textColor: Color {
        // Sent bubbles keep the WhatsApp readable-dark text in both appearances.
        message.isMine
            ? AppTheme.Palette.adaptive(
                light: Color(hex: 0x111B21),
                dark: Color(hex: 0xE9EDEF)
            )
            : AppTheme.Palette.adaptive(
                light: Color(hex: 0x111B21),
                dark: Color(hex: 0xE9EDEF)
            )
    }

    var body: some View {
        HStack {
            if message.isMine { Spacer(minLength: 48) }

            VStack(alignment: message.isMine ? .trailing : .leading, spacing: 3) {
                if !message.isMine, !message.senderName.isEmpty {
                    Text(message.senderName)
                        .font(AppTheme.Font.captionBold)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }

                Text(message.text)
                    .font(AppTheme.Font.body)
                    .foregroundStyle(textColor)
                    .padding(.horizontal, AppTheme.Spacing.md)
                    .padding(.vertical, AppTheme.Spacing.sm)
                    .background(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.option, style: .continuous)
                            .fill(bubbleFill)
                    )
                    .fixedSize(horizontal: false, vertical: true)

                Text(message.sentAt, style: .time)
                    .font(.system(size: 10))
                    .foregroundStyle(AppTheme.Palette.textSecondary)
            }

            if !message.isMine { Spacer(minLength: 48) }
        }
    }
}

#Preview {
    NavigationStack {
        MessengerView()
            .environmentObject(SessionStore())
            .environment(\.api, .live)
    }
}
