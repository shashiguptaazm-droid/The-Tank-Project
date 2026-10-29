import SwiftUI
import UniformTypeIdentifiers

/// Ports the hardcoded Compose colour literals of `AiChatScreen` in
/// `AiChatActivity.kt`. They sit outside `AppTheme` because Android never named
/// them — they are literal hex values in the `AiChatScreen` composable.
enum AiChatPalette {

    /// `#0E131F` — screen canvas behind the composer.
    static let canvas = Color(hex: 0x0E131F)
    /// `#111624` — header and tool-chip strip.
    static let chrome = Color(hex: 0x111624)
    /// `#0D111A` — Research OS workspace bar.
    static let chromeDeep = Color(hex: 0x0D111A)
    /// `#081528` — active-skill strip.
    static let skillStrip = Color(hex: 0x081528)
    /// `#2C3140` — header rule.
    static let divider = Color(hex: 0x2C3140)
    /// `#1C2232` — tool chip fill.
    static let chip = Color(hex: 0x1C2232)
    /// `#2E364B` — tool chip stroke.
    static let chipStroke = Color(hex: 0x2E364B)
    /// `#161C2A` — assistant bubble and composer pill fill.
    static let bubble = Color(hex: 0x161C2A)
    /// `#2A3348` — assistant bubble and composer pill stroke.
    static let bubbleStroke = Color(hex: 0x2A3348)
    /// `#151B28` — module card fill.
    static let card = Color(hex: 0x151B28)
    /// `#2E3A52` — module card stroke.
    static let cardStroke = Color(hex: 0x2E3A52)
    /// `#1E2638` — nested row fill inside a module card.
    static let row = Color(hex: 0x1E2638)
    /// `#303E5A` — nested row stroke.
    static let rowStroke = Color(hex: 0x303E5A)
    /// `#252F46` — small tag pill fill.
    static let tag = Color(hex: 0x252F46)
    /// `#252C3E` — sort bar fill.
    static let bar = Color(hex: 0x252C3E)
    /// `#272A52` — MG / AI avatar disc.
    static let badge = Color(hex: 0x272A52)
    /// `#BAC7FF` — user bubble and link accent.
    static let userBubble = Color(hex: 0xBAC7FF)
    /// `#111B21` — user bubble ink.
    static let userBubbleInk = Color(hex: 0x111B21)
    /// `#111927` — skill outcome card fill.
    static let skillCard = Color(hex: 0x111927)
    /// `#00FF41` — the "VERIFIED" pill.
    static let verified = Color(hex: 0x00FF41)
    /// `#1C202B` — model-mode pill fill.
    static let modePill = Color(hex: 0x1C202B)
    /// `#373C4E` — model-mode pill stroke.
    static let modePillStroke = Color(hex: 0x373C4E)
    /// `#4CAF50` — the "Always Active" presence dot.
    static let online = Color(hex: 0x4CAF50)
    /// `#5C6BC0` — filled send button.
    static let sendFill = Color(hex: 0x5C6BC0)
    /// `#252F46` — disabled send button.
    static let sendDisabled = Color(hex: 0x252F46)

    /// `chanceColor` — Dream / Target / Safe band on a counselor college row.
    static func chance(_ value: String) -> Color {
        switch value.lowercased() {
        case "dream": return Color(hex: 0x7C3AED)
        case "target": return Color(hex: 0x2563EB)
        default: return Color(hex: 0x059669)
        }
    }

    /// The monospaced research-console labels — the `sp` weights `AppTheme.Font`
    /// does not name because Android sets them inline on the Compose `Text`.
    enum Monospace {
        /// 11sp black monospaced — the workspace banner title.
        static let label = Font.system(size: 11, weight: .black, design: .monospaced)
        /// 10sp black monospaced — card eyebrows and status pills.
        static let eyebrow = Font.system(size: 10, weight: .black, design: .monospaced)
    }
}

/// Standalone Medical AI Assistant chat screen — the "AI Chat" bottom-nav tab.
///
/// Ports `AiChatActivity` / `AiChatScreen` from Android's `AiChatActivity.kt`:
/// the header with the model-mode pill and history entry, the Research OS
/// workspace bar, the horizontal tool-chip carousel, the message stream with
/// per-turn module cards, the community-posts card, and the composer with
/// attach / voice / send-or-stop.
struct AiChatView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @Environment(\.dismiss) private var dismiss
    @StateObject private var viewModel = AiChatViewModel()
    @State private var isShowingDocPicker = false
    @State private var isWorkspaceExpanded = false
    @State private var isCounselorExpanded = true
    @State private var isThesisExpanded = true
    @State private var isChapterExpanded = true
    @State private var isRenamePrompted = false
    @State private var renameTarget: AiChatSessionMeta?
    @State private var renameText = ""
    @State private var sharePayload: AiChatShareSheet?
    @State private var activePdfViewer: ActivePdfPageViewer? = nil
    @State private var activeFigureDetail: ChatFigureJson? = nil

    /// Ports `shareSession` — the `ACTION_SEND` transcript handed to the share sheet.
    private struct AiChatShareSheet: Identifiable {
        let id = UUID()
        let title: String
        let transcript: String
    }

    private struct ExportItem: Identifiable {
        var id: URL { url }
        let url: URL
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                chatHeader
                workspaceStatusBar

                if let activeSkill = viewModel.activeSkillName {
                    activeSkillIndicator(activeSkill)
                }

                toolChipsBar
                Divider().background(AiChatPalette.divider)
                messageStream

                if !viewModel.documentNote.isEmpty {
                    documentChip
                }

                if !viewModel.posts.isEmpty {
                    communityPostsCard
                }

                if !viewModel.enrichmentNote.isEmpty {
                    enrichmentRow
                }

                inputComposer
            }
            .background(AiChatPalette.canvas.ignoresSafeArea())
            .navigationBarHidden(true)
            .overlay(alignment: .bottom) { toastOverlay }
            .navigationDestination(
                isPresented: Binding(
                    get: { viewModel.activeQuizToLaunch != nil },
                    set: { if !$0 { viewModel.activeQuizToLaunch = nil } }
                )
            ) {
                if let quiz = viewModel.activeQuizToLaunch {
                    QuizView(quiz: quiz)
                }
            }
            .sheet(isPresented: $viewModel.isHistoryPresented) {
                historySheet
            }
            .sheet(item: $sharePayload) { payload in
                shareSheet(payload)
            }
            .sheet(item: Binding(
                get: { viewModel.exportUrlToShare.map { ExportItem(url: $0) } },
                set: { if $0 == nil { viewModel.exportUrlToShare = nil } }
            )) { item in
                ShareSheet(activityItems: [item.url])
            }
            .sheet(isPresented: $viewModel.isVariablesModalPresented) {
                if let pdfContext = viewModel.pdfContext {
                    VariablesEditorSheet(
                        variables: pdfContext.variables,
                        onUpdate: { name, val in viewModel.updateVariable(name: name, value: val) },
                        onAdd: { name, val in viewModel.addVariable(name: name, value: val) },
                        onDismiss: { viewModel.isVariablesModalPresented = false }
                    )
                }
            }
            .sheet(item: $activePdfViewer) { viewer in
                RagPdfPageSheet(viewer: viewer) {
                    activePdfViewer = nil
                }
            }
            .sheet(item: $activeFigureDetail) { fig in
                FigureDetailSheet(figure: fig, onDismiss: {
                    activeFigureDetail = nil
                }, onViewPage: { bookId, page in
                    activeFigureDetail = nil
                    activePdfViewer = ActivePdfPageViewer(bookId: bookId, bookTitle: fig.bookReference, page: page, totalPages: 0)
                })
            }
            .fileImporter(
                isPresented: $isShowingDocPicker,
                allowedContentTypes: Self.documentTypes,
                allowsMultipleSelection: false
            ) { result in
                switch result {
                case let .success(urls):
                    if let url = urls.first { viewModel.attachDocument(at: url) }
                case let .failure(error):
                    viewModel.present(error: error)
                }
            }
            .alert("Rename chat", isPresented: $isRenamePrompted) {
                TextField("Chat title", text: $renameText)
                Button("Cancel", role: .cancel) { renameTarget = nil }
                Button("Save") {
                    if let target = renameTarget {
                        Task { await viewModel.renameSession(target, to: renameText, userId: session.userId) }
                    }
                    renameTarget = nil
                }
            }
            .errorAlert(message: $viewModel.errorMessage)
            .task { await viewModel.restoreLastSession(userId: session.userId) }
            .onAppear {
                RemoteLogger.log(tag: "AiChat_onAppear", message: "Medical AI Chat screen opened")
            }
        }
    }

    /// Ports `ActivityResultContracts.OpenDocument` — the PDF / slides / Word / text
    /// / image filter both pickers launch with on Android.
    private static let wordProcessing: UTType = UTType(mimeType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document") ?? UTType(filenameExtension: "docx") ?? .data
    private static let documentTypes: [UTType] = [.pdf, .presentation, wordProcessing, .plainText, .image, .data]

    // MARK: - Header (ChatHeader)

    /// Ports `ChatHeader` — back, MG badge, model-mode pill, history entry and overflow.
    private var chatHeader: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            Button {
                dismiss()
            } label: {
                Image(systemName: "chevron.left")
                    .font(AppTheme.Font.callout)
                    .foregroundStyle(AppTheme.Ink.iconTint)
                    .frame(width: 32, height: 32)
            }

            ZStack {
                Circle()
                    .fill(AiChatPalette.badge)
                    .frame(width: 36, height: 36)
                Text("MG")
                    .font(AppTheme.Font.cardTitle)
                    .foregroundStyle(Color.white)
            }

            VStack(alignment: .leading, spacing: 2) {
                Text("Medigyaan AI")
                    .font(AppTheme.Font.cardTitle)
                    .foregroundStyle(Color.white)
                HStack(spacing: AppTheme.Spacing.xxs) {
                    Circle()
                        .fill(AiChatPalette.online)
                        .frame(width: 7, height: 7)
                    Text("Always Active")
                        .font(AppTheme.Font.micro)
                        .foregroundStyle(AppTheme.Ink.textSecondary)
                }
            }

            Spacer()

            Button {
                viewModel.cycleModelMode()
            } label: {
                Text(viewModel.modelMode.label)
                    .font(AppTheme.Font.captionBold)
                    .foregroundStyle(AiChatPalette.userBubble)
                    .padding(.horizontal, AppTheme.Spacing.sm)
                    .padding(.vertical, AppTheme.Spacing.xxs)
                    .background(AiChatPalette.modePill)
                    .clipShape(Capsule())
                    .overlay(Capsule().stroke(AiChatPalette.modePillStroke, lineWidth: 1))
            }

            Button {
                Task {
                    await viewModel.refreshSessions(userId: session.userId)
                    viewModel.isHistoryPresented = true
                }
            } label: {
                Image(systemName: "clock.arrow.circlepath")
                    .font(AppTheme.Font.callout)
                    .foregroundStyle(AppTheme.Ink.iconTint)
                    .frame(width: 32, height: 32)
            }

            overflowMenu
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, AppTheme.Spacing.sm)
        .background(AiChatPalette.chrome)
    }

    /// Ports the `ModuleActionRow` overflow attached to the chat header.
    private var overflowMenu: some View {
        Menu {
            Button {
                isShowingDocPicker = true
            } label: {
                Label("📄 Chat with PDF", systemImage: "doc.text.fill")
            }
            Button {
                viewModel.onToolChipTapped("🔬 PubMed")
            } label: {
                Label("🔬 PubMed Validator", systemImage: "cross.case.fill")
            }
            Button {
                viewModel.onToolChipTapped("🎓 Thesis")
            } label: {
                Label("🎓 Thesis Topics", systemImage: "graduationcap.fill")
            }
            Button {
                viewModel.onToolChipTapped("🎯 Counselor")
            } label: {
                Label("🎯 AI College Predictor", systemImage: "target")
            }
            Button {
                viewModel.onToolChipTapped("🖼️ Poster")
            } label: {
                Label("🖼️ AI Poster Gen", systemImage: "photo.fill")
            }
            Button {
                viewModel.onToolChipTapped("📚 Chapter")
            } label: {
                Label("📚 Chapter Draft", systemImage: "book.fill")
            }
            Divider()
            Button(role: .destructive) {
                viewModel.startNewChat()
            } label: {
                Label("New Chat", systemImage: "square.and.pencil")
            }
            Button(role: .destructive) {
                viewModel.clearChat()
            } label: {
                Label("Clear Chat", systemImage: "trash")
            }
        } label: {
            Image(systemName: "ellipsis")
                .font(AppTheme.Font.title3)
                .foregroundStyle(AppTheme.Ink.iconTint)
                .rotationEffect(.degrees(90))
                .frame(width: 32, height: 32)
        }
    }

    // MARK: - Research OS workspace bar

    /// Ports the `showWorkspace` banner — the collapsible Research OS state strip.
    private var workspaceStatusBar: some View {
        DisclosureGroup(isExpanded: $isWorkspaceExpanded) {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
                if !viewModel.workspace.researchQuestion.isEmpty {
                    HStack(alignment: .top, spacing: AppTheme.Spacing.xxs) {
                        Text("Question:")
                            .font(AppTheme.Font.micro)
                            .foregroundStyle(AppTheme.Ink.cyan)
                        Text(viewModel.workspace.researchQuestion)
                            .font(AppTheme.Font.micro)
                            .foregroundStyle(Color.white)
                    }
                }
                let pico = viewModel.workspace.pico
                if !pico.population.isEmpty || !pico.intervention.isEmpty {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("PICO Framework:")
                            .font(AiChatPalette.Monospace.eyebrow)
                            .foregroundStyle(AiChatPalette.verified)
                        Text("P: \(pico.population) | I: \(pico.intervention) | C: \(pico.comparison) | O: \(pico.outcome)")
                            .font(AppTheme.Font.micro)
                            .foregroundStyle(AppTheme.Ink.textPrimary)
                    }
                }
            }
            .padding(.top, AppTheme.Spacing.xxs)
        } label: {
            HStack(spacing: AppTheme.Spacing.xs) {
                Image(systemName: "cube.transparent")
                    .font(AppTheme.Font.callout)
                    .foregroundStyle(AppTheme.Ink.cyan)
                Text("RESEARCH OS WORKSPACE")
                    .font(AiChatPalette.Monospace.label)
                    .foregroundStyle(Color.white)
                Spacer()
                if let count = viewModel.pdfContext?.variables.count, count > 0 {
                    Button {
                        viewModel.isVariablesModalPresented = true
                    } label: {
                        Text("📝 \(count) Vars")
                            .font(AiChatPalette.Monospace.eyebrow)
                            .foregroundStyle(AppTheme.Ink.cyan)
                            .padding(.horizontal, AppTheme.Spacing.xs)
                            .padding(.vertical, 2)
                            .background(Capsule().fill(AppTheme.Ink.cyan.opacity(0.18)))
                    }
                }
                Text(viewModel.workspace.currentSection.uppercased())
                    .font(AiChatPalette.Monospace.eyebrow)
                    .foregroundStyle(AppTheme.Palette.secondary)
                    .padding(.horizontal, AppTheme.Spacing.xs)
                    .padding(.vertical, 2)
                    .background(Capsule().fill(AppTheme.Palette.secondary.opacity(0.15)))
            }
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, AppTheme.Spacing.xs)
        .background(AiChatPalette.chromeDeep)
    }

    /// Ports the `enrichmentNote` "Executing Skill" strip.
    private func activeSkillIndicator(_ skillName: String) -> some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            ProgressView()
                .tint(AppTheme.Ink.cyan)
                .scaleEffect(0.8)
            Text("⚡ Executing Skill: \(skillName)…")
                .font(AiChatPalette.Monospace.label)
                .foregroundStyle(AppTheme.Ink.cyan)
            Spacer()
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, AppTheme.Spacing.xs)
        .background(AiChatPalette.skillStrip)
    }

    // MARK: - Tool chips

    /// Ports the horizontally scrolling `ToolChip(...)` row.
    private var toolChipsBar: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: AppTheme.Spacing.xs) {
                ForEach(viewModel.toolChips, id: \.self) { chip in
                    Button {
                        handleChip(chip)
                    } label: {
                        Text(chip)
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Ink.iconTint)
                            .padding(.horizontal, AppTheme.Spacing.md)
                            .padding(.vertical, AppTheme.Spacing.xs)
                            .background(AiChatPalette.chip)
                            .clipShape(Capsule())
                            .overlay(Capsule().stroke(AiChatPalette.chipStroke, lineWidth: 1))
                    }
                }
            }
            .padding(.horizontal, AppTheme.Spacing.md)
            .padding(.vertical, AppTheme.Spacing.split)
        }
        .background(AiChatPalette.chrome)
    }

    /// Ports the chip callbacks — "📄 Chat PDF" / "📄 Upload Doc" opens the document picker.
    private func handleChip(_ chip: String) {
        if chip == "📄 Chat PDF" || chip == "📄 Upload Doc" {
            isShowingDocPicker = true
            return
        }
        viewModel.onToolChipTapped(chip)
    }

    // MARK: - Message stream

    /// Ports the `LazyColumn` of turns, with the module cards attached to the turn
    /// that produced them and the streaming / thinking / searching rows at the tail.
    private var messageStream: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                    if viewModel.messages.count <= 1 {
                        welcomeHeader
                        suggestionsBar
                    }

                    ForEach(viewModel.messages) { message in
                        messageRow(message).id(message.id)
                    }

                    if let partial = viewModel.streamingText {
                        streamingBubble(partial).id("streaming")
                    } else if viewModel.isThinking {
                        thinkingBubble.id("thinking")
                    }

                    if viewModel.isLoading {
                        typingIndicator.id("typing")
                    }

                    if viewModel.searchPhase == .searching {
                        searchingRow.id("searching")
                    } else if viewModel.searchPhase == .none, !viewModel.isLoading {
                        noQuestionsRow.id("noquestions")
                    }
                }
                .padding(.horizontal, AppTheme.Spacing.md)
                .padding(.vertical, AppTheme.Spacing.md)
            }
            .onChange(of: viewModel.messages.count) { _ in
                scrollToBottom(proxy)
            }
            .onChange(of: viewModel.streamingText) { _ in
                scrollToBottom(proxy)
            }
            .onChange(of: viewModel.isLoading) { _ in
                scrollToBottom(proxy)
            }
        }
    }

    private func scrollToBottom(_ proxy: ScrollViewProxy) {
        withAnimation {
            if let partial = viewModel.streamingText {
                proxy.scrollTo("streaming", anchor: .bottom)
            } else if viewModel.isLoading {
                proxy.scrollTo("typing", anchor: .bottom)
            } else if let last = viewModel.messages.last {
                proxy.scrollTo(last.id, anchor: .bottom)
            }
        }
    }

    /// Ports `ChatWelcomeHint`.
    private var welcomeHeader: some View {
        VStack(spacing: AppTheme.Spacing.xs) {
            Text("🧠")
                .font(AppTheme.Font.display)
                .padding(.top, AppTheme.Spacing.sm)
            Text("How can I help you today?")
                .font(AppTheme.Font.title3)
                .foregroundStyle(Color.white)
            Text("Ask about NEET PG, diseases, drugs — or use the tools above.")
                .font(AppTheme.Font.micro)
                .foregroundStyle(AppTheme.Ink.textSecondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, AppTheme.Spacing.sm)
    }

    /// Ports `SuggestionCard`.
    private var suggestionsBar: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            Text("Suggested Medical Queries")
                .font(AppTheme.Font.micro)
                .foregroundStyle(AppTheme.Ink.textHint)
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: AppTheme.Spacing.sm) {
                    ForEach(viewModel.suggestions) { suggestion in
                        Button {
                            viewModel.selectSuggestion(suggestion, api: api, userId: session.userId)
                        } label: {
                            HStack(spacing: AppTheme.Spacing.xs) {
                                Image(systemName: suggestion.icon)
                                Text(suggestion.title)
                            }
                            .font(AppTheme.Font.caption)
                            .padding(.horizontal, AppTheme.Spacing.md)
                            .padding(.vertical, AppTheme.Spacing.sm)
                            .background(AiChatPalette.chip)
                            .foregroundStyle(AiChatPalette.userBubble)
                            .clipShape(Capsule())
                            .overlay(Capsule().stroke(AiChatPalette.chipStroke, lineWidth: 1))
                        }
                        .disabled(viewModel.isLoading)
                    }
                }
            }
        }
        .padding(.vertical, AppTheme.Spacing.xs)
    }

    @ViewBuilder
    private func messageRow(_ message: AiChatMessage) -> some View {
        if message.isUser {
            userBubble(message)
        } else {
            assistantCard(message)
        }
    }

    // MARK: - Bubbles

    /// Ports `ChatBubble`'s user side — lavender pill, timestamp and the Edit chip.
    private func userBubble(_ message: AiChatMessage) -> some View {
        VStack(alignment: .trailing, spacing: AppTheme.Spacing.xxs) {
            if let document = message.attachmentName {
                HStack(spacing: AppTheme.Spacing.xs) {
                    Image(systemName: "doc.fill")
                    Text(document).lineLimit(1)
                }
                .font(AppTheme.Font.micro)
                .foregroundStyle(AiChatPalette.userBubble)
                .padding(.horizontal, AppTheme.Spacing.sm)
                .padding(.vertical, AppTheme.Spacing.xxs)
                .background(AiChatPalette.badge)
                .clipShape(Capsule())
            }

            Text(message.text)
                .font(AppTheme.Font.body)
                .foregroundStyle(AiChatPalette.userBubbleInk)
                .padding(.horizontal, AppTheme.Spacing.md)
                .padding(.vertical, AppTheme.Spacing.sm)
                .background(
                    UnevenRoundedRectangle(
                        topLeadingRadius: AppTheme.Radius.materialCard,
                        bottomLeadingRadius: AppTheme.Radius.materialCard,
                        bottomTrailingRadius: AppTheme.Radius.xs,
                        topTrailingRadius: AppTheme.Radius.materialCard
                    )
                    .fill(AiChatPalette.userBubble)
                )
                .frame(maxWidth: 300, alignment: .trailing)

            HStack(spacing: AppTheme.Spacing.xs) {
                Text(Self.formattedTime(message.timestamp))
                    .font(AppTheme.Font.micro)
                    .foregroundStyle(AppTheme.Ink.textHint)
                Button {
                    viewModel.startEdit(message: message)
                } label: {
                    Text("✏️ Edit")
                        .font(AppTheme.Font.micro)
                        .foregroundStyle(AiChatPalette.userBubble)
                        .padding(.horizontal, AppTheme.Spacing.sm)
                        .padding(.vertical, 2)
                        .background(AiChatPalette.chip)
                        .clipShape(Capsule())
                        .overlay(Capsule().stroke(AiChatPalette.chipStroke, lineWidth: 0.8))
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .trailing)
    }

    /// Ports `ChatBubble`'s assistant side — dark card, AI badge, and `ReplyActionRow`.
    private func assistantCard(_ message: AiChatMessage) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            HStack(alignment: .top, spacing: AppTheme.Spacing.sm) {
                ZStack {
                    Circle()
                        .fill(AiChatPalette.badge)
                        .frame(width: 30, height: 30)
                    Text("AI")
                        .font(AppTheme.Font.micro)
                        .foregroundStyle(Color.white)
                }
                .padding(.top, 2)

                VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                    Text(cleanAssistantTextForDisplay(message.text))
                        .font(AppTheme.Font.body)
                        .foregroundStyle(AppTheme.Ink.textPrimary)
                        .lineSpacing(3)
                        .fixedSize(horizontal: false, vertical: true)

                    HStack(spacing: AppTheme.Spacing.md) {
                        Button {
                            viewModel.toggleSpeech(for: message)
                        } label: {
                            Label(viewModel.isSpeaking ? "Stop" : "Read", systemImage: "speaker.wave.2")
                                .font(AppTheme.Font.caption2)
                                .foregroundStyle(AppTheme.Ink.textHint)
                        }
                        Button {
                            viewModel.copyMessage(message)
                        } label: {
                            Label("Copy", systemImage: "doc.on.doc")
                                .font(AppTheme.Font.caption2)
                                .foregroundStyle(AppTheme.Ink.textHint)
                        }
                        ShareLink(item: message.text) {
                            Image(systemName: "square.and.arrow.up")
                                .font(AppTheme.Font.caption2)
                                .foregroundStyle(AppTheme.Ink.textHint)
                        }
                        Button {
                            viewModel.toggleFeedback(for: message, like: true)
                        } label: {
                            Image(systemName: message.feedback == 1 ? "hand.thumbsup.fill" : "hand.thumbsup")
                                .font(AppTheme.Font.caption2)
                                .foregroundStyle(message.feedback == 1 ? AppTheme.Ink.success : AppTheme.Ink.textHint)
                        }
                        Button {
                            viewModel.toggleFeedback(for: message, like: false)
                        } label: {
                            Image(systemName: message.feedback == -1 ? "hand.thumbsdown.fill" : "hand.thumbsdown")
                                .font(AppTheme.Font.caption2)
                                .foregroundStyle(message.feedback == -1 ? AppTheme.Palette.error : AppTheme.Ink.textHint)
                        }
                        Button {
                            viewModel.regenerate(message: message, api: api, userId: session.userId)
                        } label: {
                            Image(systemName: "arrow.clockwise")
                                .font(AppTheme.Font.caption2)
                                .foregroundStyle(AppTheme.Ink.textHint)
                        }
                        Menu {
                            Button {
                                viewModel.exportMessage(message: message, format: .pdf)
                            } label: {
                                Label("Export as PDF", systemImage: "doc.richtext")
                            }
                            Button {
                                viewModel.exportMessage(message: message, format: .docx)
                            } label: {
                                Label("Export as Word (.docx)", systemImage: "doc.text")
                            }
                            Button {
                                viewModel.exportMessage(message: message, format: .pptx)
                            } label: {
                                Label("Export as PowerPoint (.pptx)", systemImage: "rectangle.inset.filled.and.person.filled")
                            }
                        } label: {
                            Image(systemName: "arrow.down.doc")
                                .font(AppTheme.Font.caption2)
                                .foregroundStyle(AppTheme.Ink.textHint)
                        }
                        Spacer()
                        if let milliseconds = message.responseTimeMs {
                            Text("⚡ \(milliseconds)ms")
                                .font(AppTheme.Font.micro)
                                .foregroundStyle(AppTheme.Ink.textHint)
                        }
                    }
                    .padding(.top, AppTheme.Spacing.xxs)
                }
                .padding(AppTheme.Spacing.md)
                .background(
                    UnevenRoundedRectangle(
                        topLeadingRadius: AppTheme.Radius.xs,
                        bottomLeadingRadius: AppTheme.Radius.materialCard,
                        bottomTrailingRadius: AppTheme.Radius.materialCard,
                        topTrailingRadius: AppTheme.Radius.materialCard
                    )
                    .fill(AiChatPalette.bubble)
                )
                .overlay(
                    UnevenRoundedRectangle(
                        topLeadingRadius: AppTheme.Radius.xs,
                        bottomLeadingRadius: AppTheme.Radius.materialCard,
                        bottomTrailingRadius: AppTheme.Radius.materialCard,
                        topTrailingRadius: AppTheme.Radius.materialCard
                    )
                    .stroke(AiChatPalette.bubbleStroke, lineWidth: 1)
                )
            }

            if let outcome = message.skillOutcome {
                skillOutcomeCard(outcome, skillName: message.skillName ?? "Clinical Research Skill")
            }
            if let counsel = message.counselCard {
                counselorCard(counsel)
            }
            if let thesis = message.thesisCard {
                thesisCard(thesis)
            }
            if let chapter = message.chapterCard {
                chapterCard(chapter)
            }
            if let chapterDetails = message.chapterDetails {
                chapterGenCard(chapterDetails)
            }
            if let citation = message.citationCard {
                citationValidationCard(citation, message: message)
            }
            if let poster = message.posterCard {
                posterGenCard(poster)
            }
            if let similar = message.similarArticlesCard {
                similarArticlesCard(similar)
            }
            if let pdfAbstracts = message.pdfAbstractsCard {
                pdfAbstractsCard(pdfAbstracts)
            }
            if !message.ragBooks.isEmpty {
                ForEach(message.ragBooks) { ragBook in
                    ragBookCard(ragBook)
                }
            }
            if !message.relatedQuestions.isEmpty {
                relatedQuestionsCard(message.relatedQuestions)
            }
        }
        .padding(.vertical, 2)
    }

    // MARK: - Module cards

    /// Ports `SkillOutcomeCard`.
    private func skillOutcomeCard(_ outcome: SkillOutcome, skillName: String) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            HStack(spacing: AppTheme.Spacing.sm) {
                ZStack {
                    Circle()
                        .fill(AppTheme.Ink.cyan.opacity(0.2))
                        .frame(width: 28, height: 28)
                    Image(systemName: "sparkles")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Ink.cyan)
                }
                VStack(alignment: .leading, spacing: 2) {
                    Text(skillName.uppercased())
                        .font(AiChatPalette.Monospace.eyebrow)
                        .foregroundStyle(AppTheme.Ink.cyan)
                    if !outcome.uiNote.isEmpty {
                        Text(outcome.uiNote)
                            .font(AppTheme.Font.subheadline)
                            .foregroundStyle(Color.white)
                    }
                }
                Spacer()
                Text("VERIFIED")
                    .font(AiChatPalette.Monospace.eyebrow)
                    .foregroundStyle(AiChatPalette.verified)
                    .padding(.horizontal, AppTheme.Spacing.xs)
                    .padding(.vertical, 2)
                    .background(Capsule().fill(AiChatPalette.verified.opacity(0.15)))
            }
            Text(outcome.contextText)
                .font(AppTheme.Font.subheadline)
                .foregroundStyle(AppTheme.Ink.textPrimary)
                .lineSpacing(3)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.field, style: .continuous)
                .fill(AiChatPalette.skillCard)
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.field, style: .continuous)
                        .stroke(AppTheme.Ink.cyan.opacity(0.35), lineWidth: 1)
                )
        )
    }

    /// Ports `AiCounselorCard` + `CounselCollegeRow`.
    private func counselorCard(_ data: CounselCardData) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            Button {
                withAnimation { isCounselorExpanded.toggle() }
            } label: {
                HStack(spacing: AppTheme.Spacing.sm) {
                    ZStack {
                        Circle()
                            .fill(AppTheme.Palette.primaryContainer)
                            .frame(width: 28, height: 28)
                        Text("✨").font(AppTheme.Font.callout)
                    }
                    Text("✨ NEET PG AI Counselor")
                        .font(AppTheme.Font.callout)
                        .foregroundStyle(Color.white)
                    Spacer()
                    Image(systemName: isCounselorExpanded ? "chevron.up" : "chevron.down")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Ink.textHint)
                }
            }

            if isCounselorExpanded {
                if !data.summary.isEmpty {
                    Text(data.summary)
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Ink.iconTint)
                }
                if !data.error.isEmpty {
                    Text(data.error)
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.error)
                }
                HStack {
                    Text("\(data.results.count) options found")
                        .font(AppTheme.Font.caption2)
                        .foregroundStyle(AppTheme.Ink.textHint)
                    Spacer()
                    Text("↕ Recommended")
                        .font(AppTheme.Font.caption2)
                        .foregroundStyle(AiChatPalette.userBubble)
                        .padding(.horizontal, AppTheme.Spacing.sm)
                        .padding(.vertical, 3)
                        .background(AiChatPalette.bar)
                        .clipShape(Capsule())
                }
                ForEach(data.results) { college in
                    collegeRow(college)
                }
            }
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.materialCard, style: .continuous)
                .fill(AiChatPalette.card)
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.materialCard, style: .continuous)
                        .stroke(AiChatPalette.cardStroke, lineWidth: 1)
                )
        )
        .padding(.leading, 40)
    }

    private func collegeRow(_ college: CounselCollege) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(college.institute)
                        .font(AppTheme.Font.subheadline)
                        .foregroundStyle(Color.white)
                        .lineLimit(2)
                    Text(college.course)
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Ink.teal)
                }
                Spacer()
                Text(college.chance)
                    .font(AiChatPalette.Monospace.eyebrow)
                    .foregroundStyle(.white)
                    .padding(.horizontal, AppTheme.Spacing.sm)
                    .padding(.vertical, 3)
                    .background(AiChatPalette.chance(college.chance))
                    .clipShape(Capsule())
            }
            HStack(spacing: AppTheme.Spacing.xs) {
                infoTag(college.state)
                infoTag(college.quota)
                infoTag("Closing: #\(college.closingRank)")
            }
            HStack(spacing: AppTheme.Spacing.md) {
                Text("Fee: \(college.feePerYear)")
                    .font(AppTheme.Font.micro)
                    .foregroundStyle(AppTheme.Ink.gold)
                Text("Stipend: \(college.stipendYear1)")
                    .font(AppTheme.Font.micro)
                    .foregroundStyle(AppTheme.Ink.success)
                Text("Bond: \(college.bondYears)")
                    .font(AppTheme.Font.micro)
                    .foregroundStyle(AppTheme.Ink.textHint)
            }
        }
        .padding(AppTheme.Spacing.sm)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.option, style: .continuous)
                .fill(AiChatPalette.row)
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.option, style: .continuous)
                        .stroke(AiChatPalette.rowStroke, lineWidth: 1)
                )
        )
    }

    /// Ports `ThesisTopicsCard`.
    private func thesisCard(_ data: ThesisCardData) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            Button {
                withAnimation { isThesisExpanded.toggle() }
            } label: {
                HStack(spacing: AppTheme.Spacing.sm) {
                    Text("🎓").font(AppTheme.Font.callout)
                    Text("Thesis Topics Catalog")
                        .font(AppTheme.Font.callout)
                        .foregroundStyle(Color.white)
                    Spacer()
                    Image(systemName: isThesisExpanded ? "chevron.up" : "chevron.down")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Ink.textHint)
                }
            }
            if isThesisExpanded {
                ForEach(data.results) { topic in
                    VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
                        Text(topic.displayTitle)
                            .font(AppTheme.Font.subheadline)
                            .foregroundStyle(Color.white)
                        Text(topic.snippet)
                            .font(AppTheme.Font.micro)
                            .foregroundStyle(AppTheme.Ink.textSecondary)
                            .lineLimit(2)
                        HStack {
                            infoTag(topic.studyType)
                            infoTag("Difficulty: \(topic.difficulty)")
                        }
                    }
                    .padding(AppTheme.Spacing.sm)
                    .background(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.sm, style: .continuous)
                            .fill(AiChatPalette.row)
                    )
                }
            }
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AiChatPalette.card)
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                        .stroke(AiChatPalette.cardStroke, lineWidth: 1)
                )
        )
        .padding(.leading, 40)
    }

    /// Ports `ChapterGenCard`'s section list.
    private func chapterCard(_ data: ChapterCardData) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            Button {
                withAnimation { isChapterExpanded.toggle() }
            } label: {
                HStack(spacing: AppTheme.Spacing.sm) {
                    Text("📚").font(AppTheme.Font.callout)
                    Text("Drafted Chapter: \(data.chapterName)")
                        .font(AppTheme.Font.callout)
                        .foregroundStyle(Color.white)
                    Spacer()
                    Image(systemName: isChapterExpanded ? "chevron.up" : "chevron.down")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Ink.textHint)
                }
            }
            if isChapterExpanded {
                ForEach(data.sections, id: \.self) { section in
                    HStack(spacing: AppTheme.Spacing.xs) {
                        Image(systemName: "checkmark.circle.fill")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Ink.success)
                        Text(section)
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Ink.iconTint)
                    }
                }
            }
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AiChatPalette.card)
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                        .stroke(AiChatPalette.cardStroke, lineWidth: 1)
                )
        )
        .padding(.leading, 40)
    }

    // MARK: - Chapter Generator Card (Full Schema)

    private func chapterGenCard(_ chapter: ChatChapterJson) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
            HStack(spacing: AppTheme.Spacing.sm) {
                Text("📚").font(AppTheme.Font.title3)
                VStack(alignment: .leading, spacing: 2) {
                    Text(chapter.chapterName.isEmpty ? "Thesis Chapter" : chapter.chapterName)
                        .font(AppTheme.Font.callout)
                        .fontWeight(.bold)
                        .foregroundStyle(Color.white)
                    Text("\(chapter.sections.count) Sections · \(chapter.tables.count) Tables · \(chapter.charts.count) Charts · \(chapter.references.count) Refs")
                        .font(AppTheme.Font.micro)
                        .foregroundStyle(AppTheme.Ink.cyan)
                }
                Spacer()
                Button {
                    withAnimation { isChapterExpanded.toggle() }
                } label: {
                    Image(systemName: isChapterExpanded ? "chevron.up" : "chevron.down")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Ink.textHint)
                }
            }

            if isChapterExpanded {
                VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                    ForEach(chapter.sections) { section in
                        chapterSectionBlock(section)
                    }

                    ForEach(chapter.tables) { table in
                        chapterTableBlock(table)
                    }

                    ForEach(chapter.figures) { figure in
                        chapterFigureBlock(figure)
                    }

                    ForEach(chapter.charts) { chart in
                        chapterChartBlock(chart)
                    }

                    if !chapter.abbreviations.isEmpty {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Abbreviations")
                                .font(AiChatPalette.Monospace.eyebrow)
                                .foregroundStyle(AppTheme.Ink.cyan)
                            ForEach(chapter.abbreviations) { ab in
                                Text("\(ab.short) = \(ab.full)")
                                    .font(AppTheme.Font.caption2)
                                    .foregroundStyle(AppTheme.Ink.textSecondary)
                            }
                        }
                        .padding(8)
                        .background(AiChatPalette.row)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                    }

                    if !chapter.references.isEmpty {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("References (\(chapter.references.count))")
                                .font(AiChatPalette.Monospace.eyebrow)
                                .foregroundStyle(AppTheme.Ink.cyan)
                            ForEach(Array(chapter.references.enumerated()), id: \.offset) { i, r in
                                Text("\(i + 1). \(r.referenceText.isEmpty ? r.citation : r.referenceText)")
                                    .font(AppTheme.Font.micro)
                                    .foregroundStyle(AppTheme.Ink.textHint)
                            }
                        }
                        .padding(8)
                        .background(AiChatPalette.row)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                    }

                    // Chapter Export Action Row
                    HStack(spacing: 12) {
                        Button {
                            viewModel.exportChapter(chapter: chapter, format: .pdf)
                        } label: {
                            Label("PDF", systemImage: "arrow.down.doc")
                                .font(AppTheme.Font.caption2)
                                .padding(.horizontal, 10)
                                .padding(.vertical, 4)
                                .background(AiChatPalette.chip)
                                .clipShape(Capsule())
                                .foregroundStyle(AppTheme.Ink.cyan)
                        }

                        Button {
                            viewModel.exportChapter(chapter: chapter, format: .docx)
                        } label: {
                            Label("Word", systemImage: "doc.text")
                                .font(AppTheme.Font.caption2)
                                .padding(.horizontal, 10)
                                .padding(.vertical, 4)
                                .background(AiChatPalette.chip)
                                .clipShape(Capsule())
                                .foregroundStyle(AppTheme.Ink.cyan)
                        }

                        Button {
                            viewModel.exportChapter(chapter: chapter, format: .pptx)
                        } label: {
                            Label("PowerPoint", systemImage: "rectangle.inset.filled.and.person.filled")
                                .font(AppTheme.Font.caption2)
                                .padding(.horizontal, 10)
                                .padding(.vertical, 4)
                                .background(AiChatPalette.chip)
                                .clipShape(Capsule())
                                .foregroundStyle(AppTheme.Ink.cyan)
                        }
                    }
                    .padding(.top, 4)
                }
            }
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AiChatPalette.card)
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                        .stroke(AiChatPalette.cardStroke, lineWidth: 1)
                )
        )
        .padding(.leading, 40)
    }

    private func chapterSectionBlock(_ section: ChatSectionJson) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            if !section.heading.isEmpty {
                Text(section.heading)
                    .font(AppTheme.Font.subheadline)
                    .fontWeight(.bold)
                    .foregroundStyle(AppTheme.Palette.primary)
            }
            if !section.content.isEmpty {
                Text(section.content)
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Ink.textPrimary)
                    .lineSpacing(2)
            }
            ForEach(section.paragraphs, id: \.self) { p in
                Text(p)
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Ink.textSecondary)
                    .lineSpacing(2)
            }
            ForEach(section.bullets, id: \.self) { b in
                HStack(alignment: .top, spacing: 4) {
                    Text("•").foregroundStyle(AppTheme.Palette.primary)
                    Text(b)
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Ink.textSecondary)
                }
            }
            ForEach(Array(section.numberedPoints.enumerated()), id: \.offset) { i, p in
                HStack(alignment: .top, spacing: 4) {
                    Text("\(i + 1).").foregroundStyle(AppTheme.Palette.primary)
                    Text(p)
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Ink.textSecondary)
                }
            }
            ForEach(section.subsections) { sub in
                VStack(alignment: .leading, spacing: 2) {
                    Text(sub.heading)
                        .font(AppTheme.Font.caption)
                        .fontWeight(.semibold)
                        .foregroundStyle(Color.white)
                    Text(sub.content)
                        .font(AppTheme.Font.caption2)
                        .foregroundStyle(AppTheme.Ink.textSecondary)
                }
                .padding(.leading, 8)
            }
            if let t = section.table {
                chapterTableBlock(t)
            }
            ForEach(section.figures) { f in
                chapterFigureBlock(f)
            }
        }
        .padding(8)
        .background(AiChatPalette.row)
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    private func chapterTableBlock(_ table: ChatTableJson) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("📊 \(table.tableNumber.isEmpty ? "Table" : "Table " + table.tableNumber): \(table.title)")
                .font(AppTheme.Font.caption)
                .fontWeight(.bold)
                .foregroundStyle(Color.white)

            if !table.headers.isEmpty {
                HStack(spacing: 4) {
                    ForEach(table.headers, id: \.self) { h in
                        Text(h)
                            .font(AppTheme.Font.micro)
                            .fontWeight(.bold)
                            .foregroundStyle(AppTheme.Ink.cyan)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                .padding(.vertical, 2)
            }

            ForEach(Array(table.rows.prefix(15).enumerated()), id: \.offset) { _, row in
                HStack(spacing: 4) {
                    ForEach(Array(row.enumerated()), id: \.offset) { _, cell in
                        Text(cell)
                            .font(AppTheme.Font.micro)
                            .foregroundStyle(AppTheme.Ink.textPrimary)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                .padding(.vertical, 2)
                Divider().background(AiChatPalette.divider)
            }

            if !table.footnote.isEmpty {
                Text(table.footnote)
                    .font(AppTheme.Font.micro)
                    .foregroundStyle(AppTheme.Ink.textHint)
            }
        }
        .padding(8)
        .background(AiChatPalette.card)
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    private func chapterFigureBlock(_ figure: ChatFigureJson) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text("🖼️ Figure \(figure.figureNumber): \(figure.title)")
                .font(AppTheme.Font.caption)
                .fontWeight(.bold)
                .foregroundStyle(Color.white)
            if !figure.caption.isEmpty {
                Text(figure.caption)
                    .font(AppTheme.Font.caption2)
                    .foregroundStyle(AppTheme.Ink.textSecondary)
            }
            if !figure.imageSearchQuery.isEmpty {
                Text("Search: \(figure.imageSearchQuery)")
                    .font(AppTheme.Font.micro)
                    .foregroundStyle(AppTheme.Ink.cyan)
            }
        }
        .padding(8)
        .background(AiChatPalette.row)
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    private func chapterChartBlock(_ chart: ChatChartJson) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("📈 \(chart.title.isEmpty ? "Chart" : chart.title)")
                .font(AppTheme.Font.caption)
                .fontWeight(.bold)
                .foregroundStyle(Color.white)

            let labels = chart.data.isEmpty ? chart.labels : chart.data.map { $0.label }
            let values = chart.data.isEmpty ? chart.values : chart.data.map { $0.value }
            miniChart(type: chart.type, labels: labels, values: values)
        }
        .padding(8)
        .background(AiChatPalette.row)
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    private func miniChart(type: String, labels: [String], values: [Double]) -> some View {
        let nums = values.filter { !$0.isNaN && $0 > 0 }
        let maxV = max(nums.max() ?? 1.0, 0.0001)
        let total = max(nums.reduce(0, +), 1.0)
        let t = type.lowercased()
        let chartColors: [Color] = [
            AppTheme.Palette.primary,
            AppTheme.Ink.cyan,
            AppTheme.Palette.secondary,
            AppTheme.Ink.teal,
            Color.orange,
            Color.pink
        ]

        return VStack(alignment: .leading, spacing: 6) {
            if t.contains("pie") || t.contains("doughnut") {
                HStack(spacing: 16) {
                    Canvas { context, size in
                        let center = CGPoint(x: size.width / 2, y: size.height / 2)
                        let radius = min(size.width, size.height) / 2
                        var startAngle = Angle(degrees: -90)
                        for (i, val) in nums.enumerated() {
                            let sweep = Angle(degrees: (val / total) * 360)
                            let endAngle = startAngle + sweep
                            var path = Path()
                            path.move(to: center)
                            path.addArc(center: center, radius: radius, startAngle: startAngle, endAngle: endAngle, clockwise: false)
                            context.fill(path, with: .color(chartColors[i % chartColors.count]))
                            startAngle = endAngle
                        }
                    }
                    .frame(width: 80, height: 80)

                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(Array(labels.prefix(4).enumerated()), id: \.offset) { i, label in
                            HStack(spacing: 6) {
                                Circle().fill(chartColors[i % chartColors.count]).frame(width: 8, height: 8)
                                Text(label)
                                    .font(AppTheme.Font.micro)
                                    .foregroundStyle(AppTheme.Ink.textSecondary)
                                    .lineLimit(1)
                            }
                        }
                    }
                }
            } else if t.contains("line") {
                Canvas { context, size in
                    guard nums.count > 1 else { return }
                    let stepX = size.width / CGFloat(nums.count - 1)
                    var path = Path()
                    let points: [CGPoint] = nums.enumerated().map { i, val in
                        let x = CGFloat(i) * stepX
                        let y = size.height - CGFloat(val / maxV) * (size.height * 0.85) - 4
                        return CGPoint(x: x, y: y)
                    }
                    path.move(to: points[0])
                    for pt in points.dropFirst() {
                        path.addLine(to: pt)
                    }
                    context.stroke(path, with: .color(chartColors[0]), lineWidth: 2.5)
                    for pt in points {
                        let rect = CGRect(x: pt.x - 3, y: pt.y - 3, width: 6, height: 6)
                        context.fill(Path(ellipseIn: rect), with: .color(chartColors[1]))
                    }
                }
                .frame(height: 70)
            } else {
                Canvas { context, size in
                    guard !nums.isEmpty else { return }
                    let barWidth = size.width / CGFloat(nums.count)
                    for (i, val) in nums.enumerated() {
                        let h = CGFloat(val / maxV) * (size.height * 0.88)
                        let x = CGFloat(i) * barWidth + (barWidth * 0.15)
                        let y = size.height - h
                        let w = barWidth * 0.70
                        let rect = CGRect(x: x, y: y, width: w, height: h)
                        context.fill(Path(roundedRect: rect, cornerRadius: 3), with: .color(chartColors[i % chartColors.count]))
                    }
                }
                .frame(height: 70)

                if !labels.isEmpty {
                    HStack {
                        ForEach(Array(labels.prefix(nums.count).enumerated()), id: \.offset) { _, label in
                            Text(label)
                                .font(AppTheme.Font.micro)
                                .foregroundStyle(AppTheme.Ink.textHint)
                                .frame(maxWidth: .infinity)
                                .lineLimit(1)
                        }
                    }
                }
            }
        }
    }

    // MARK: - PubMed Citation Validation Card

    private func citationValidationCard(_ state: CitationValidationState, message: AiChatMessage) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            HStack(spacing: AppTheme.Spacing.xs) {
                Image(systemName: "checkmark.shield.fill")
                    .foregroundStyle(AppTheme.Ink.cyan)
                Text("PubMed Verification")
                    .font(AppTheme.Font.subheadline)
                    .fontWeight(.bold)
                    .foregroundStyle(Color.white)
                Spacer()
                if state.running {
                    ProgressView().scaleEffect(0.8)
                }
            }

            if state.running && state.results == nil {
                HStack(spacing: 8) {
                    ProgressView()
                    Text(state.note.isEmpty ? "Checking references against NCBI…" : state.note)
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Ink.textSecondary)
                }
                if state.total > 0 {
                    ProgressView(value: Double(state.current), total: Double(state.total))
                        .tint(AppTheme.Ink.cyan)
                }
            } else if let results = state.results {
                let verifiedCount = results.filter { $0.found }.count
                let failedCount = results.count - verifiedCount
                Text(verifiedCount == results.count ? "✅ All \(verifiedCount) references verified" : "Verification finished: \(verifiedCount) verified, \(failedCount) not found")
                    .font(AppTheme.Font.caption)
                    .fontWeight(.bold)
                    .foregroundStyle(verifiedCount == results.count ? AppTheme.Ink.success : Color.orange)

                ForEach(results) { r in
                    HStack(alignment: .top, spacing: 8) {
                        Image(systemName: r.found ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(r.found ? AppTheme.Ink.success : AppTheme.Palette.error)
                            .padding(.top, 2)

                        VStack(alignment: .leading, spacing: 2) {
                            Text(r.originalText.prefix(120).description)
                                .font(AppTheme.Font.caption2)
                                .foregroundStyle(AppTheme.Ink.textPrimary)

                            if r.found {
                                if let url = URL(string: "https://pubmed.ncbi.nlm.nih.gov/\(r.pmid)/"), !r.pmid.isEmpty {
                                    Link("🔗 PMID: \(r.pmid) ↗", destination: url)
                                        .font(AppTheme.Font.micro)
                                        .foregroundStyle(AppTheme.Ink.cyan)
                                } else {
                                    Text("✅ Verified")
                                        .font(AppTheme.Font.micro)
                                        .foregroundStyle(AppTheme.Ink.success)
                                }
                            } else {
                                Text("❌ Not found — verify spelling")
                                    .font(AppTheme.Font.micro)
                                    .foregroundStyle(AppTheme.Palette.error)
                            }
                        }
                    }
                    .padding(.vertical, 2)
                }

                // Action Row
                let exportText = "PubMed Verification Results:\n" + results.enumerated().map { i, r in
                    "\(i + 1). \(r.originalText) -> \(r.found ? "Verified (PMID: " + r.pmid + ")" : "Not Found")"
                }.joined(separator: "\n")

                HStack(spacing: 12) {
                    Button {
                        UIPasteboard.general.string = exportText
                        viewModel.showToast("Copied validation results 📋")
                    } label: {
                        Label("Copy", systemImage: "doc.on.doc")
                            .font(AppTheme.Font.caption2)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 4)
                            .background(AiChatPalette.chip)
                            .clipShape(Capsule())
                            .foregroundStyle(AppTheme.Ink.cyan)
                    }

                    Button {
                        viewModel.exportText(title: "PubMed Verification", text: exportText, format: .pdf)
                    } label: {
                        Label("Export PDF", systemImage: "arrow.down.doc")
                            .font(AppTheme.Font.caption2)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 4)
                            .background(AiChatPalette.chip)
                            .clipShape(Capsule())
                            .foregroundStyle(AppTheme.Ink.cyan)
                    }
                }
                .padding(.top, 4)
            }
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AiChatPalette.card)
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                        .stroke(AiChatPalette.cardStroke, lineWidth: 1)
                )
        )
        .padding(.leading, 40)
    }

    // MARK: - AI Poster Generation Card

    private func posterGenCard(_ state: PosterGenState) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            HStack(spacing: AppTheme.Spacing.xs) {
                Image(systemName: "photo.artframe")
                    .foregroundStyle(AppTheme.Ink.cyan)
                Text("AI Research Poster")
                    .font(AppTheme.Font.subheadline)
                    .fontWeight(.bold)
                    .foregroundStyle(Color.white)
                Spacer()
                if state.phase == 1 || state.phase == 2 {
                    ProgressView().scaleEffect(0.8)
                }
            }

            if state.phase == 1 || state.phase == 2 {
                HStack(spacing: 8) {
                    ProgressView()
                    Text(state.note.isEmpty ? "Synthesizing poster layout from abstract…" : state.note)
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Ink.textSecondary)
                }
            } else if let d = state.data {
                VStack(alignment: .leading, spacing: 6) {
                    if !d.title.isEmpty {
                        Text(d.title)
                            .font(AppTheme.Font.headline)
                            .fontWeight(.bold)
                            .foregroundStyle(Color.white)
                    }
                    if !d.subtitle.isEmpty {
                        Text(d.subtitle)
                            .font(AppTheme.Font.caption2)
                            .foregroundStyle(AppTheme.Ink.cyan)
                    }

                    Divider().background(AiChatPalette.divider)

                    ForEach(d.sections) { s in
                        VStack(alignment: .leading, spacing: 2) {
                            Text(s.heading)
                                .font(AiChatPalette.Monospace.eyebrow)
                                .foregroundStyle(AppTheme.Palette.primary)
                            Text(s.body)
                                .font(AppTheme.Font.caption)
                                .foregroundStyle(AppTheme.Ink.textPrimary)
                                .lineSpacing(2)
                        }
                        .padding(.vertical, 2)
                    }

                    // Action buttons
                    let posterExport = "Research Poster: \(d.title)\n\n" + d.sections.map { "[\($0.heading)]\n\($0.body)" }.joined(separator: "\n\n")

                    HStack(spacing: 12) {
                        Button {
                            UIPasteboard.general.string = posterExport
                            viewModel.showToast("Saved poster text to clipboard 📋")
                        } label: {
                            Label("Copy", systemImage: "doc.on.doc")
                                .font(AppTheme.Font.caption2)
                                .padding(.horizontal, 10)
                                .padding(.vertical, 4)
                                .background(AiChatPalette.chip)
                                .clipShape(Capsule())
                                .foregroundStyle(AppTheme.Ink.cyan)
                        }

                        Button {
                            viewModel.exportText(title: d.title, text: posterExport, format: .pdf)
                        } label: {
                            Label("Export PDF", systemImage: "arrow.down.doc")
                                .font(AppTheme.Font.caption2)
                                .padding(.horizontal, 10)
                                .padding(.vertical, 4)
                                .background(AiChatPalette.chip)
                                .clipShape(Capsule())
                                .foregroundStyle(AppTheme.Ink.cyan)
                        }
                    }
                    .padding(.top, 4)
                }
            }
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AiChatPalette.card)
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                        .stroke(AiChatPalette.cardStroke, lineWidth: 1)
                )
        )
        .padding(.leading, 40)
    }

    // MARK: - Similar PubMed Articles Card

    private func similarArticlesCard(_ state: SimilarArticlesState) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            HStack(spacing: AppTheme.Spacing.xs) {
                Image(systemName: "magnifyingglass.circle.fill")
                    .foregroundStyle(AppTheme.Ink.cyan)
                Text("Similar PubMed Articles (\(state.entries.count))")
                    .font(AppTheme.Font.subheadline)
                    .fontWeight(.bold)
                    .foregroundStyle(Color.white)
            }

            if !state.note.isEmpty {
                Text(state.note)
                    .font(AppTheme.Font.caption2)
                    .foregroundStyle(AppTheme.Ink.textHint)
            }

            ForEach(state.entries) { entry in
                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Text(entry.citationLabel.isEmpty ? "[S]" : entry.citationLabel)
                            .font(AiChatPalette.Monospace.eyebrow)
                            .foregroundStyle(AppTheme.Ink.cyan)
                        Text(entry.title)
                            .font(AppTheme.Font.caption)
                            .fontWeight(.semibold)
                            .foregroundStyle(Color.white)
                            .lineLimit(2)
                    }

                    if !entry.citation.isEmpty {
                        Text(entry.citation)
                            .font(AppTheme.Font.micro)
                            .foregroundStyle(AppTheme.Ink.textSecondary)
                    }

                    if let url = URL(string: "https://pubmed.ncbi.nlm.nih.gov/\(entry.pmid)/"), !entry.pmid.isEmpty {
                        Link("🔗 Open on PubMed (PMID: \(entry.pmid)) ↗", destination: url)
                            .font(AppTheme.Font.micro)
                            .foregroundStyle(AppTheme.Ink.cyan)
                    }
                }
                .padding(8)
                .background(AiChatPalette.row)
                .clipShape(RoundedRectangle(cornerRadius: 8))
            }
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AiChatPalette.card)
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                        .stroke(AiChatPalette.cardStroke, lineWidth: 1)
                )
        )
        .padding(.leading, 40)
    }

    // MARK: - PDF Abstracts & Variables Card

    private func pdfAbstractsCard(_ state: PdfAbstractsState) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            HStack(spacing: AppTheme.Spacing.xs) {
                Image(systemName: "doc.badge.gearshape.fill")
                    .foregroundStyle(AppTheme.Ink.cyan)
                Text("Extracted PDF Evidence & Variables")
                    .font(AppTheme.Font.subheadline)
                    .fontWeight(.bold)
                    .foregroundStyle(Color.white)
                Spacer()
                Button {
                    viewModel.isVariablesModalPresented = true
                } label: {
                    Text("Variables 📝")
                        .font(AppTheme.Font.caption2)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(AiChatPalette.chip)
                        .clipShape(Capsule())
                        .foregroundStyle(AppTheme.Ink.cyan)
                }
            }

            if !state.note.isEmpty {
                Text(state.note)
                    .font(AppTheme.Font.caption2)
                    .foregroundStyle(AppTheme.Ink.textHint)
            }

            ForEach(state.entries) { entry in
                VStack(alignment: .leading, spacing: 3) {
                    Text(entry.title.isEmpty ? entry.citation : entry.title)
                        .font(AppTheme.Font.caption)
                        .fontWeight(.semibold)
                        .foregroundStyle(Color.white)
                    if !entry.compactedText.isEmpty {
                        Text(entry.compactedText)
                            .font(AppTheme.Font.micro)
                            .foregroundStyle(AppTheme.Ink.textSecondary)
                    }
                }
                .padding(8)
                .background(AiChatPalette.row)
                .clipShape(RoundedRectangle(cornerRadius: 8))
            }
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AiChatPalette.card)
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                        .stroke(AiChatPalette.cardStroke, lineWidth: 1)
                )
        )
        .padding(.leading, 40)
    }

    /// Ports `QuestionSuggestionBlock` — practice MCQs found by the keyword search.
    private func relatedQuestionsCard(_ questions: [Question]) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            HStack(spacing: AppTheme.Spacing.xs) {
                Image(systemName: "checklist")
                    .foregroundStyle(AppTheme.Ink.teal)
                Text("Related Practice MCQs")
                    .font(AppTheme.Font.subheadline)
                    .foregroundStyle(Color.white)
            }
            ForEach(questions) { question in
                relatedQuestionRow(question)
            }
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AiChatPalette.card)
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                        .stroke(AiChatPalette.cardStroke, lineWidth: 1)
                )
        )
        .padding(.leading, 40)
    }

    private func relatedQuestionRow(_ question: Question) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(question.text)
                    .font(AppTheme.Font.caption)
                    .lineLimit(2)
                    .foregroundStyle(AppTheme.Ink.iconTint)
                Text("Topic: \(question.topic.isEmpty ? question.subject : question.topic)")
                    .font(AppTheme.Font.micro)
                    .foregroundStyle(AppTheme.Ink.textHint)
            }
            Spacer()
            Button {
                viewModel.activeQuizToLaunch = Quiz(
                    id: question.id,
                    title: question.topic.isEmpty ? "Related Practice" : question.topic,
                    topic: question.topic,
                    subject: question.subject,
                    questionCount: 1,
                    durationSeconds: 120
                )
            } label: {
                Text("Practice")
                    .font(AppTheme.Font.caption2)
                    .foregroundStyle(AiChatPalette.canvas)
                    .padding(.horizontal, AppTheme.Spacing.sm)
                    .padding(.vertical, AppTheme.Spacing.xxs)
                    .background(AppTheme.Ink.teal)
                    .clipShape(Capsule())
            }
        }
        .padding(AppTheme.Spacing.sm)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.sm, style: .continuous)
                .fill(AiChatPalette.row)
        )
    }

    /// Ports `CommunityPostsCard` — post photos and captions for the reply's topic.
    private var communityPostsCard: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            HStack(spacing: AppTheme.Spacing.xs) {
                Image(systemName: "square.grid.2x2")
                    .foregroundStyle(AppTheme.Ink.gold)
                Text("Related Community Posts")
                    .font(AppTheme.Font.subheadline)
                    .foregroundStyle(Color.white)
            }
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: AppTheme.Spacing.sm) {
                    ForEach(viewModel.posts) { post in
                        VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
                            if let url = URL(string: post.images.first ?? "") {
                                AsyncImage(url: url) { image in
                                    image.resizable().aspectRatio(contentMode: .fill)
                                } placeholder: {
                                    AiChatPalette.divider
                                }
                                .frame(width: 96, height: 96)
                                .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.sm, style: .continuous))
                            }
                            Text(post.caption)
                                .font(AppTheme.Font.micro)
                                .foregroundStyle(AppTheme.Ink.iconTint)
                                .lineLimit(3)
                                .frame(width: 96, alignment: .leading)
                            Text("♥︎ \(post.likes) · \(post.author)")
                                .font(AiChatPalette.Monospace.eyebrow)
                                .foregroundStyle(AppTheme.Ink.textHint)
                        }
                    }
                }
            }
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AiChatPalette.card)
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                        .stroke(AiChatPalette.cardStroke, lineWidth: 1)
                )
        )
    }

    // MARK: - Streaming / status rows

    /// Ports `StreamingBubble` — the ChatGPT-style progressive reveal.
    private func streamingBubble(_ partial: String) -> some View {
        HStack(alignment: .top, spacing: AppTheme.Spacing.sm) {
            ZStack {
                Circle()
                    .fill(AiChatPalette.badge)
                    .frame(width: 30, height: 30)
                Text("AI").font(AppTheme.Font.micro).foregroundStyle(Color.white)
            }
            Text(partial)
                .font(AppTheme.Font.body)
                .foregroundStyle(AppTheme.Ink.textPrimary)
                .lineSpacing(3)
                .padding(AppTheme.Spacing.md)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(
                    UnevenRoundedRectangle(
                        topLeadingRadius: AppTheme.Radius.xs,
                        bottomLeadingRadius: AppTheme.Radius.materialCard,
                        bottomTrailingRadius: AppTheme.Radius.materialCard,
                        topTrailingRadius: AppTheme.Radius.materialCard
                    )
                    .fill(AiChatPalette.bubble)
                )
        }
    }

    /// Ports `ThinkingBubble`.
    private var thinkingBubble: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            ProgressView().scaleEffect(0.8).tint(AiChatPalette.userBubble)
            Text("MediGyaan AI is analyzing clinical evidence…")
                .font(AppTheme.Font.caption)
                .foregroundStyle(AppTheme.Ink.textHint)
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, AppTheme.Spacing.sm)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AiChatPalette.bubble)
        )
        .padding(.leading, 40)
    }

    /// Ports the busy `typingIndicator`.
    private var typingIndicator: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            ProgressView().scaleEffect(0.8).tint(AiChatPalette.userBubble)
            Text("Running clinical research skills…")
                .font(AppTheme.Font.caption)
                .foregroundStyle(AppTheme.Ink.textHint)
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, AppTheme.Spacing.sm)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AiChatPalette.bubble)
        )
        .padding(.leading, 40)
    }

    /// Ports `SearchingRow`.
    private var searchingRow: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            ProgressView().scaleEffect(0.7).tint(AppTheme.Ink.teal)
            Text("Searching the 280k question bank…")
                .font(AppTheme.Font.caption)
                .foregroundStyle(AppTheme.Ink.textHint)
        }
        .padding(.leading, 40)
    }

    /// Ports `NoQuestionsRow`.
    private var noQuestionsRow: some View {
        Text("No matching practice questions in the bank for this topic.")
            .font(AppTheme.Font.micro)
            .foregroundStyle(AppTheme.Ink.textHint)
            .padding(.leading, 40)
    }

    /// Ports `PdfStatusChip`.
    private var documentChip: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            if viewModel.isReadingDocument {
                ProgressView().scaleEffect(0.7).tint(AiChatPalette.userBubble)
            } else {
                Image(systemName: "doc.text.fill")
                    .foregroundStyle(AiChatPalette.userBubble)
            }
            Text(viewModel.documentNote)
                .font(AppTheme.Font.caption)
                .foregroundStyle(Color.white)
                .lineLimit(2)
            Spacer()
            Button {
                viewModel.removeDocument()
            } label: {
                Image(systemName: "xmark.circle.fill")
                    .foregroundStyle(AppTheme.Ink.textHint)
            }
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, AppTheme.Spacing.xs)
        .background(AiChatPalette.chip)
    }

    /// Ports the `enrichmentNote` row under the cards.
    private var enrichmentRow: some View {
        Text(viewModel.enrichmentNote)
            .font(AppTheme.Font.micro)
            .foregroundStyle(AppTheme.Ink.textHint)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, AppTheme.Spacing.md)
            .padding(.bottom, AppTheme.Spacing.xxs)
    }

    private func infoTag(_ text: String) -> some View {
        Text(text)
            .font(AppTheme.Font.micro)
            .foregroundStyle(AiChatPalette.userBubble)
            .padding(.horizontal, AppTheme.Spacing.xs)
            .padding(.vertical, 2)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.xs, style: .continuous)
                    .fill(AiChatPalette.tag)
            )
    }

    // MARK: - Composer (ChatInputBar)

    /// Ports `ChatInputBar` — the 26dp pill with attach, text, mic and send/stop.
    private var inputComposer: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            HStack(spacing: AppTheme.Spacing.xs) {
                Button {
                    isShowingDocPicker = true
                } label: {
                    Image(systemName: "paperclip")
                        .font(AppTheme.Font.subheadline)
                        .foregroundStyle(AppTheme.Ink.textHint)
                        .frame(width: 32, height: 32)
                }

                TextField("Ask anything…", text: $viewModel.input, axis: .vertical)
                    .font(AppTheme.Font.callout)
                    .foregroundStyle(Color.white)
                    .lineLimit(1...4)
                    .disabled(viewModel.isLoading)
                    .padding(.vertical, AppTheme.Spacing.xs)

                Button {
                    viewModel.toggleVoiceRecording()
                } label: {
                    ZStack {
                        if viewModel.isListening {
                            Circle()
                                .fill(Color.red.opacity(0.3))
                                .frame(width: 30, height: 30)
                            Image(systemName: "mic.fill")
                                .font(AppTheme.Font.callout)
                                .foregroundStyle(Color.red)
                        } else {
                            Image(systemName: "mic.fill")
                                .font(AppTheme.Font.callout)
                                .foregroundStyle(AppTheme.Ink.textHint)
                                .frame(width: 30, height: 30)
                        }
                    }
                }
                .disabled(viewModel.isLoading)
            }
            .padding(.horizontal, AppTheme.Spacing.sm)
            .padding(.vertical, AppTheme.Spacing.xxs)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.submitButton, style: .continuous)
                    .fill(AiChatPalette.bubble)
                    .overlay(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.submitButton, style: .continuous)
                            .stroke(AiChatPalette.bubbleStroke, lineWidth: 1)
                    )
            )

            if viewModel.isLoading {
                Button {
                    viewModel.stopGenerating()
                } label: {
                    ZStack {
                        Circle()
                            .fill(AppTheme.Palette.error)
                            .frame(width: 38, height: 38)
                        Rectangle()
                            .fill(Color.white)
                            .frame(width: 12, height: 12)
                    }
                }
            } else {
                Button {
                    viewModel.sendCurrentInput(api: api, userId: session.userId)
                } label: {
                    ZStack {
                        Circle()
                            .fill(viewModel.canSend ? AiChatPalette.sendFill : AiChatPalette.sendDisabled)
                            .frame(width: 38, height: 38)
                        Image(systemName: "arrow.up")
                            .font(AppTheme.Font.callout)
                            .foregroundStyle(Color.white)
                    }
                }
                .disabled(!viewModel.canSend)
            }
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, AppTheme.Spacing.sm)
        .background(AiChatPalette.canvas)
    }

    // MARK: - History drawer

    /// Ports `SessionHistoryDrawerContent` — new chat, list, pin, rename, share, delete.
    private var historySheet: some View {
        NavigationStack {
            List {
                Section {
                    Button {
                        viewModel.startNewChat()
                    } label: {
                        Label("New Chat", systemImage: "square.and.pencil")
                    }
                }
                Section("Recent") {
                    if viewModel.sessions.isEmpty {
                        Text("No saved conversations yet.")
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                    }
                    ForEach(viewModel.sessions) { meta in
                        VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
                            Text(meta.title)
                                .font(AppTheme.Font.callout)
                                .fontWeight(meta.pinned ? .bold : .regular)
                            Text(Self.formattedDate(meta.updatedAt))
                                .font(AppTheme.Font.micro)
                                .foregroundStyle(AppTheme.Palette.textSecondary)
                        }
                        .contentShape(Rectangle())
                        .onTapGesture {
                            Task { await viewModel.loadSession(meta, userId: session.userId) }
                        }
                        .swipeActions(edge: .leading) {
                            Button {
                                Task { await viewModel.togglePin(meta, userId: session.userId) }
                            } label: {
                                Label(meta.pinned ? "Unpin" : "Pin", systemImage: "pin")
                            }
                            .tint(AppTheme.Palette.primary)
                        }
                        .swipeActions(edge: .trailing) {
                            Button(role: .destructive) {
                                Task { await viewModel.deleteSession(meta, userId: session.userId) }
                            } label: {
                                Label("Delete", systemImage: "trash")
                            }
                        }
                        .contextMenu {
                            Button {
                                renameTarget = meta
                                renameText = meta.title
                                isRenamePrompted = true
                            } label: {
                                Label("Rename", systemImage: "pencil")
                            }
                            Button {
                                Task {
                                    let transcript = await viewModel.transcript(for: meta, userId: session.userId)
                                    sharePayload = AiChatShareSheet(title: meta.title, transcript: transcript)
                                }
                            } label: {
                                Label("Share transcript", systemImage: "square.and.arrow.up")
                            }
                            Button(role: .destructive) {
                                Task { await viewModel.deleteSession(meta, userId: session.userId) }
                            } label: {
                                Label("Delete", systemImage: "trash")
                            }
                        }
                    }
                }
            }
            .navigationTitle("Chat History")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { viewModel.isHistoryPresented = false }
                }
            }
        }
        .screenBackground()
    }

    /// Ports the `Intent.createChooser` behind `shareSession`.
    private func shareSheet(_ payload: AiChatShareSheet) -> some View {
        VStack(spacing: AppTheme.Spacing.lg) {
            Text(payload.title)
                .font(AppTheme.Font.title3)
                .foregroundStyle(AppTheme.Palette.textPrimary)
                .multilineTextAlignment(.center)
            ShareLink(item: payload.transcript) {
                Text("Share transcript")
                    .font(AppTheme.Font.callout)
                    .foregroundStyle(AppTheme.Palette.onPrimary)
                    .padding(.horizontal, AppTheme.Spacing.lg)
                    .padding(.vertical, AppTheme.Spacing.sm)
                    .background(AppTheme.Palette.primary)
                    .clipShape(Capsule())
            }
            Spacer()
        }
        .padding(AppTheme.Spacing.xl)
        .screenBackground()
    }

    // MARK: - Toast

    private var toastOverlay: some View {
        Group {
            if let toast = viewModel.toastMessage {
                Text(toast)
                    .font(AppTheme.Font.subheadline)
                    .foregroundStyle(Color.white)
                    .padding(.horizontal, AppTheme.Spacing.lg)
                    .padding(.vertical, AppTheme.Spacing.sm)
                    .background(Color.black.opacity(0.85))
                    .clipShape(Capsule())
                    .padding(.bottom, 72)
                    .transition(.opacity)
            }
        }
    }

    // MARK: - Formatting

    private static func formattedTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "h:mm a"
        return formatter.string(from: date)
    }

    private static func formattedDate(_ millis: Double) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "d MMM yyyy, h:mm a"
        return formatter.string(from: Date(timeIntervalSince1970: millis / 1000))
    }
}

#Preview {
    AiChatView()
        .environmentObject(SessionStore())
        .environment(\.api, .live)
}

// MARK: - Variables Editor Bottom Sheet (Ports VariablesEditorBottomSheet from Android)

struct VariablesEditorSheet: View {
    let variables: [AiChatVariable]
    let onUpdate: (String, String) -> Void
    let onAdd: (String, String) -> Void
    let onDismiss: () -> Void

    @State private var searchQuery: String = ""
    @State private var selectedCategory: String = "All"
    @State private var showAddForm: Bool = false
    @State private var newName: String = ""
    @State private var newValue: String = ""

    let categories = ["All", "Core 52 Schema", "Compacted Abstracts", "References"]

    var filteredVariables: [AiChatVariable] {
        variables.filter { v in
            let n = v.name
            let matchesCat: Bool
            switch selectedCategory {
            case "Core 52 Schema":
                matchesCat = !n.contains("Compacted_") && !n.contains("Pubmed_") && !n.contains("Similar_")
            case "Compacted Abstracts":
                matchesCat = n.contains("Compacted_") || n.contains("Pubmed_") || n.contains("Similar_")
            case "References":
                matchesCat = n.localizedCaseInsensitiveContains("reference") || n.localizedCaseInsensitiveContains("vancouver") || n.localizedCaseInsensitiveContains("citation")
            default:
                matchesCat = true
            }
            let q = searchQuery.trimmingCharacters(in: .whitespaces).lowercased()
            let matchesQuery = q.isEmpty || n.lowercased().contains(q) || v.value.lowercased().contains(q)
            return matchesCat && matchesQuery
        }
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Header & Add trigger
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Thesis & PubMed Variables (\(variables.count))")
                            .font(AppTheme.Font.title3)
                            .fontWeight(.bold)
                            .foregroundStyle(Color.white)
                        Text("Core 52 schema, Vancouver citations & compacted abstracts")
                            .font(AppTheme.Font.caption2)
                            .foregroundStyle(AppTheme.Ink.textHint)
                    }
                    Spacer()
                    Button {
                        withAnimation { showAddForm.toggle() }
                    } label: {
                        Text(showAddForm ? "Cancel" : "+ Add")
                            .font(AppTheme.Font.caption)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 5)
                            .background(AppTheme.Palette.primary)
                            .foregroundStyle(Color.white)
                            .clipShape(Capsule())
                    }
                }
                .padding()

                // Add Form
                if showAddForm {
                    VStack(alignment: .leading, spacing: 8) {
                        TextField("Variable Name (e.g. Title, Methodology, Sample_Size)", text: $newName)
                            .textFieldStyle(.plain)
                            .padding(8)
                            .background(AiChatPalette.bubble)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                            .overlay(RoundedRectangle(cornerRadius: 8).stroke(AiChatPalette.cardStroke, lineWidth: 1))
                            .foregroundStyle(Color.white)

                        TextField("Variable Value...", text: $newValue)
                            .textFieldStyle(.plain)
                            .padding(8)
                            .background(AiChatPalette.bubble)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                            .overlay(RoundedRectangle(cornerRadius: 8).stroke(AiChatPalette.cardStroke, lineWidth: 1))
                            .foregroundStyle(Color.white)

                        Button("Save Variable") {
                            guard !newName.trimmingCharacters(in: .whitespaces).isEmpty else { return }
                            onAdd(newName.trimmingCharacters(in: .whitespaces), newValue.trimmingCharacters(in: .whitespaces))
                            newName = ""
                            newValue = ""
                            showAddForm = false
                        }
                        .font(AppTheme.Font.caption)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 6)
                        .background(AppTheme.Ink.cyan)
                        .foregroundStyle(Color.black)
                        .clipShape(Capsule())
                    }
                    .padding(.horizontal)
                    .padding(.bottom, 8)
                }

                // Category chips
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(categories, id: \.self) { cat in
                            Button {
                                selectedCategory = cat
                            } label: {
                                Text(cat)
                                    .font(AppTheme.Font.caption2)
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 6)
                                    .background(selectedCategory == cat ? AppTheme.Palette.primary : AiChatPalette.chip)
                                    .foregroundStyle(selectedCategory == cat ? Color.white : AppTheme.Ink.textSecondary)
                                    .clipShape(Capsule())
                            }
                        }
                    }
                    .padding(.horizontal)
                    .padding(.vertical, 6)
                }

                // Search Box
                HStack {
                    Image(systemName: "magnifyingglass").foregroundStyle(AppTheme.Ink.textHint)
                    TextField("Search variables...", text: $searchQuery)
                        .textFieldStyle(.plain)
                        .foregroundStyle(Color.white)
                }
                .padding(8)
                .background(AiChatPalette.chip)
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .padding(.horizontal)
                .padding(.vertical, 4)

                // List
                List {
                    ForEach(filteredVariables, id: \.name) { v in
                        VStack(alignment: .leading, spacing: 6) {
                            Text(v.name)
                                .font(AiChatPalette.Monospace.eyebrow)
                                .foregroundStyle(AppTheme.Ink.cyan)
                            Text(v.value)
                                .font(AppTheme.Font.body)
                                .foregroundStyle(AppTheme.Ink.textPrimary)
                        }
                        .padding(.vertical, 4)
                        .listRowBackground(AiChatPalette.card)
                    }
                }
                .listStyle(.plain)
            }
            .background(AiChatPalette.canvas.ignoresSafeArea())
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done", action: onDismiss)
                }
            }
        }
    }
}

// MARK: - Share Sheet (UIActivityViewController)

struct ShareSheet: UIViewControllerRepresentable {
    let activityItems: [Any]
    let applicationActivities: [UIActivity]? = nil

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: activityItems, applicationActivities: applicationActivities)
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}

// MARK: - RAG Textbook & Figures Components

extension AiChatView {
    func cleanAssistantTextForDisplay(_ text: String) -> String {
        // Strip [RAGFIG:...] blocks from displayed text
        let figPattern = #"\b?\[RAGFIG:[^\]]+\]"#
        var cleaned = text.replacingOccurrences(of: figPattern, with: "", options: .regularExpression)
        // Convert [RAGLINK:bid:page:pages|label] to plain label for display
        let linkPattern = #"\b?\[RAGLINK:[^:]+:\d+:\d+\|([^\]]+)\]"#
        cleaned = cleaned.replacingOccurrences(of: linkPattern, with: "$1", options: .regularExpression)
        return cleaned.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    @ViewBuilder
    func ragBookCard(_ ragBook: RagBookSource) -> some View {
        RagBookCardView(
            ragBook: ragBook,
            onViewBookPage: { bookId, page in
                activePdfViewer = ActivePdfPageViewer(
                    bookId: bookId,
                    bookTitle: ragBook.bookTitle,
                    page: page,
                    totalPages: 0
                )
            },
            onFigureClick: { fig in
                activeFigureDetail = fig
            }
        )
    }
}

/// Ports Android's `RagBookCard` from `AiChatActivity.kt`.
struct RagBookCardView: View {
    let ragBook: RagBookSource
    let onViewBookPage: (String, Int) -> Void
    let onFigureClick: (ChatFigureJson) -> Void

    @State private var figurePage: Int = 0
    private let pageSize = 4

    var body: some View {
        let figures = ragBook.figures
        let totalPages = (figures.count + pageSize - 1) / max(1, pageSize)
        let safePage = min(max(0, figurePage), max(0, totalPages - 1))
        let currentFigures = Array(figures.dropFirst(safePage * pageSize).prefix(pageSize))

        VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
            // Book header row
            HStack(alignment: .center, spacing: AppTheme.Spacing.sm) {
                Text("📖")
                    .font(.system(size: 18))

                VStack(alignment: .leading, spacing: 2) {
                    Text(ragBook.bookTitle.isEmpty ? "Medical Reference" : ragBook.bookTitle)
                        .font(AppTheme.Font.subheadline)
                        .fontWeight(.bold)
                        .foregroundStyle(AppTheme.Ink.textPrimary)
                        .lineLimit(1)

                    if !ragBook.pageNumber.isEmpty {
                        Text("Page \(ragBook.pageNumber)")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Ink.textHint)
                    }
                }

                Spacer()

                let bookId = ragBook.bookId.isEmpty ? ragBook.extractedText : ragBook.bookId
                let pageInt = Int(ragBook.pageNumber) ?? 1
                if !bookId.isEmpty {
                    Button {
                        onViewBookPage(bookId, pageInt)
                    } label: {
                        Text("View Page")
                            .font(AppTheme.Font.caption)
                            .fontWeight(.semibold)
                            .foregroundStyle(AppTheme.Ink.primaryCyan)
                            .padding(.horizontal, AppTheme.Spacing.sm)
                            .padding(.vertical, 6)
                            .background(AppTheme.Ink.primaryCyan.opacity(0.15))
                            .clipShape(Capsule())
                    }
                }
            }

            // Figures and diagrams section
            if !figures.isEmpty {
                Divider()
                    .overlay(AiChatPalette.bubbleStroke)

                HStack {
                    Text("Figures & Diagrams (\(figures.count))")
                        .font(AppTheme.Font.caption)
                        .fontWeight(.semibold)
                        .foregroundStyle(AppTheme.Ink.primaryCyan)

                    Spacer()

                    if totalPages > 1 {
                        Text("Page \(safePage + 1) of \(totalPages)")
                            .font(AppTheme.Font.micro)
                            .foregroundStyle(AppTheme.Ink.textHint)
                    }
                }

                // 2x2 grid of 4 figures per page
                LazyVGrid(columns: [GridItem(.flexible(), spacing: 8), GridItem(.flexible(), spacing: 8)], spacing: 8) {
                    ForEach(currentFigures) { fig in
                        Button {
                            onFigureClick(fig)
                        } label: {
                            VStack(alignment: .leading, spacing: 4) {
                                let figUrl = fig.imageUrl.hasPrefix("http") ? fig.imageUrl : "https://medigyaan.com/webai/ragpage/figure?path=\(fig.imageUrl)"
                                AsyncImage(url: URL(string: figUrl)) { phase in
                                    switch phase {
                                    case .empty:
                                        ProgressView()
                                            .frame(maxWidth: .infinity, minHeight: 90)
                                    case .success(let image):
                                        image
                                            .resizable()
                                            .aspectRatio(contentMode: .fill)
                                            .frame(height: 90)
                                            .clipped()
                                    case .failure:
                                        Color.black.opacity(0.2)
                                            .frame(height: 90)
                                            .overlay(Image(systemName: "photo").foregroundStyle(.gray))
                                    @unknown default:
                                        Color.clear.frame(height: 90)
                                    }
                                }
                                .clipShape(RoundedRectangle(cornerRadius: 6))

                                Text(fig.title.isEmpty ? "Figure" : fig.title)
                                    .font(AppTheme.Font.micro)
                                    .fontWeight(.semibold)
                                    .foregroundStyle(AppTheme.Ink.textPrimary)
                                    .lineLimit(1)

                                if !fig.caption.isEmpty {
                                    Text(fig.caption)
                                        .font(.system(size: 10))
                                        .foregroundStyle(AppTheme.Ink.textHint)
                                        .lineLimit(1)
                                }
                            }
                            .padding(6)
                            .background(AiChatPalette.card)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                            .overlay(RoundedRectangle(cornerRadius: 8).stroke(AiChatPalette.chipStroke, lineWidth: 0.8))
                        }
                        .buttonStyle(.plain)
                    }
                }

                // Pagination controls when figures > 4
                if totalPages > 1 {
                    HStack {
                        Button {
                            if safePage > 0 { figurePage = safePage - 1 }
                        } label: {
                            Text("◀ Prev")
                                .font(AppTheme.Font.micro)
                                .foregroundStyle(safePage > 0 ? AppTheme.Ink.primaryCyan : AppTheme.Ink.textHint)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(AiChatPalette.chip)
                                .clipShape(RoundedRectangle(cornerRadius: 6))
                        }
                        .disabled(safePage <= 0)

                        Spacer()

                        Text("\(safePage * pageSize + 1)–\(min((safePage + 1) * pageSize, figures.count)) of \(figures.count)")
                            .font(AppTheme.Font.micro)
                            .foregroundStyle(AppTheme.Ink.textHint)

                        Spacer()

                        Button {
                            if safePage < totalPages - 1 { figurePage = safePage + 1 }
                        } label: {
                            Text("Next ▶")
                                .font(AppTheme.Font.micro)
                                .foregroundStyle(safePage < totalPages - 1 ? AppTheme.Ink.primaryCyan : AppTheme.Ink.textHint)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(AiChatPalette.chip)
                                .clipShape(RoundedRectangle(cornerRadius: 6))
                        }
                        .disabled(safePage >= totalPages - 1)
                    }
                    .padding(.top, 2)
                }
            }
        }
        .padding(AppTheme.Spacing.md)
        .background(AiChatPalette.bubble)
        .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.md))
        .overlay(RoundedRectangle(cornerRadius: AppTheme.Radius.md).stroke(AiChatPalette.bubbleStroke, lineWidth: 1))
    }
}

/// Ports Android's `RagPdfPageDialog` from `AiChatActivity.kt`.
struct RagPdfPageSheet: View {
    let viewer: ActivePdfPageViewer
    let onDismiss: () -> Void

    @State private var currentPage: Int = 1

    init(viewer: ActivePdfPageViewer, onDismiss: @escaping () -> Void) {
        self.viewer = viewer
        self.onDismiss = onDismiss
        _currentPage = State(initialValue: max(1, viewer.page))
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Textbook Page Viewer
                GeometryReader { geo in
                    ScrollView([.horizontal, .vertical]) {
                        let pageUrl = "https://medigyaan.com/webai/ragpage/page?book=\(viewer.bookId)&n=\(currentPage)"
                        AsyncImage(url: URL(string: pageUrl)) { phase in
                            switch phase {
                            case .empty:
                                VStack(spacing: 12) {
                                    ProgressView()
                                        .tint(.cyan)
                                    Text("Loading Textbook Page \(currentPage)…")
                                        .font(AppTheme.Font.caption)
                                        .foregroundStyle(.gray)
                                }
                                .frame(width: geo.size.width, height: geo.size.height)
                            case .success(let image):
                                image
                                    .resizable()
                                    .aspectRatio(contentMode: .fit)
                                    .frame(minWidth: geo.size.width)
                            case .failure:
                                VStack(spacing: 12) {
                                    Image(systemName: "exclamationmark.triangle")
                                        .font(.largeTitle)
                                        .foregroundStyle(.orange)
                                    Text("Could not load page \(currentPage)")
                                        .font(AppTheme.Font.caption)
                                        .foregroundStyle(.gray)
                                }
                                .frame(width: geo.size.width, height: geo.size.height)
                            @unknown default:
                                EmptyView()
                            }
                        }
                    }
                }
                .background(Color(hex: 0x1E1E1E))

                // Bottom pagination bar
                HStack {
                    Button {
                        if currentPage > 1 { currentPage -= 1 }
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: "chevron.left")
                            Text("Prev")
                        }
                        .font(AppTheme.Font.subheadline)
                        .foregroundStyle(currentPage > 1 ? AppTheme.Ink.primaryCyan : .gray)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 8)
                        .background(AiChatPalette.chip)
                        .clipShape(Capsule())
                    }
                    .disabled(currentPage <= 1)

                    Spacer()

                    Text("Page \(currentPage)\(viewer.totalPages > 0 ? " of \(viewer.totalPages)" : "")")
                        .font(AppTheme.Font.subheadline)
                        .fontWeight(.semibold)
                        .foregroundStyle(.white)

                    Spacer()

                    Button {
                        currentPage += 1
                    } label: {
                        HStack(spacing: 4) {
                            Text("Next")
                            Image(systemName: "chevron.right")
                        }
                        .font(AppTheme.Font.subheadline)
                        .foregroundStyle(AppTheme.Ink.primaryCyan)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 8)
                        .background(AiChatPalette.chip)
                        .clipShape(Capsule())
                    }
                }
                .padding()
                .background(AiChatPalette.chrome)
            }
            .navigationTitle(viewer.bookTitle.isEmpty ? "Textbook Reference" : viewer.bookTitle)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        onDismiss()
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.title3)
                            .foregroundStyle(.gray)
                    }
                }
            }
        }
    }
}

/// Ports Android's figure detail dialog from `AiChatActivity.kt`.
struct FigureDetailSheet: View {
    let figure: ChatFigureJson
    let onDismiss: () -> Void
    let onViewPage: (String, Int) -> Void

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                    let figUrl = figure.imageUrl.hasPrefix("http") ? figure.imageUrl : "https://medigyaan.com/webai/ragpage/figure?path=\(figure.imageUrl)"
                    AsyncImage(url: URL(string: figUrl)) { phase in
                        switch phase {
                        case .empty:
                            ProgressView()
                                .frame(maxWidth: .infinity, minHeight: 220)
                        case .success(let image):
                            image
                                .resizable()
                                .aspectRatio(contentMode: .fit)
                                .frame(maxWidth: .infinity)
                                .clipShape(RoundedRectangle(cornerRadius: 12))
                        case .failure:
                            Color.black.opacity(0.3)
                                .frame(height: 200)
                                .overlay(Image(systemName: "photo").font(.largeTitle).foregroundStyle(.gray))
                                .clipShape(RoundedRectangle(cornerRadius: 12))
                        @unknown default:
                            EmptyView()
                        }
                    }

                    VStack(alignment: .leading, spacing: 6) {
                        Text(figure.title.isEmpty ? "Figure" : figure.title)
                            .font(AppTheme.Font.headline)
                            .fontWeight(.bold)
                            .foregroundStyle(AppTheme.Ink.textPrimary)

                        if !figure.caption.isEmpty {
                            Text(figure.caption)
                                .font(AppTheme.Font.body)
                                .foregroundStyle(AppTheme.Ink.textPrimary.opacity(0.85))
                        }

                        if !figure.bookReference.isEmpty {
                            Divider().padding(.vertical, 4)
                            HStack {
                                Text("Source: \(figure.bookReference)")
                                    .font(AppTheme.Font.caption)
                                    .foregroundStyle(AppTheme.Ink.textHint)
                                Spacer()
                                if !figure.pages.isEmpty {
                                    Text("Page \(figure.pages)")
                                        .font(AppTheme.Font.caption)
                                        .foregroundStyle(AppTheme.Ink.primaryCyan)
                                }
                            }
                        }
                    }
                    .padding()
                    .background(AiChatPalette.bubble)
                    .clipShape(RoundedRectangle(cornerRadius: 12))

                    let pageInt = Int(figure.pages) ?? 1
                    if !figure.sourceUrl.isEmpty {
                        Button {
                            onViewPage(figure.sourceUrl, pageInt)
                        } label: {
                            HStack {
                                Image(systemName: "book.fill")
                                Text("View in Textbook (Page \(pageInt))")
                            }
                            .font(AppTheme.Font.subheadline)
                            .fontWeight(.semibold)
                            .foregroundStyle(.black)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 14)
                            .background(AppTheme.Ink.primaryCyan)
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                        }
                        .padding(.top, 4)
                    }
                }
                .padding()
            }
            .background(AiChatPalette.canvas.ignoresSafeArea())
            .navigationTitle("Figure & Diagram")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") {
                        onDismiss()
                    }
                }
            }
        }
    }
}

