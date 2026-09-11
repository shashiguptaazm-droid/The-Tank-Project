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
struct MessengerView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api

    @State private var conversationId = "general"
    @State private var state: LoadState<[ChatMessage]> = .idle
    @State private var draft = ""
    @State private var isSending = false
    @State private var errorMessage: String?

    var body: some View {
        VStack(spacing: 0) {
            messageList
            composer
        }
        .background(AppTheme.Palette.chatBackground.ignoresSafeArea())
        .navigationTitle("Messages")
        .navigationBarTitleDisplayMode(.inline)
        .errorAlert(message: $errorMessage)
        .task { await load() }
        .refreshable { await load() }
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

    private func load() async {
        let userId = session.userId
        guard userId > 0 else { return }
        let thread = conversationId
        await state.load { [api] in
            try await api.social.messages(conversationId: thread, userId: userId)
        }
    }

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
