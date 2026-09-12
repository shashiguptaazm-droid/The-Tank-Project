import SwiftUI

/// Standalone Medical AI Assistant Chat screen.
/// Ports `AiChatActivity.kt` from the Android MediGyaan application.
struct AiChatView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @StateObject private var viewModel = AiChatViewModel()
    @State private var isShowingDocPicker = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Header Bar
                chatHeader

                Divider()

                // Messages Stream
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 16) {
                            // Prompt Suggestions (shown at the top)
                            suggestionsBar

                            ForEach(viewModel.messages) { message in
                                messageRow(message)
                                    .id(message.id)
                            }

                            if viewModel.isLoading {
                                typingIndicator
                                    .id("typing")
                            }
                        }
                        .padding(.horizontal, AppTheme.Spacing.md)
                        .padding(.vertical, AppTheme.Spacing.md)
                    }
                    .onChange(of: viewModel.messages.count) { _ in
                        withAnimation {
                            if let last = viewModel.messages.last {
                                proxy.scrollTo(last.id, anchor: .bottom)
                            }
                        }
                    }
                    .onChange(of: viewModel.isLoading) { loading in
                        if loading {
                            withAnimation {
                                proxy.scrollTo("typing", anchor: .bottom)
                            }
                        }
                    }
                }

                Divider()

                // Attachment Preview Banner (if attached)
                if let attachment = viewModel.attachedDocumentName {
                    attachmentBanner(attachment)
                }

                // Input Bar
                inputBar
            }
            .screenBackground()
            .navigationTitle("Medical AI Studio")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Menu {
                        Button(role: .destructive) {
                            viewModel.clearChat()
                        } label: {
                            Label("Clear Chat", systemImage: "trash")
                        }

                        Button {
                            viewModel.attachDocument(name: "Clinical_Case_Report.pdf")
                        } label: {
                            Label("Attach Clinical Case (PDF)", systemImage: "doc.fill")
                        }

                        Button {
                            viewModel.attachDocument(name: "Lab_Panel_Results.pdf")
                        } label: {
                            Label("Attach Lab Panel (PDF)", systemImage: "cross.case.fill")
                        }
                    } label: {
                        Image(systemName: "ellipsis.circle")
                            .font(.system(size: 18))
                    }
                }
            }
            .overlay(alignment: .bottom) {
                if let toast = viewModel.toastMessage {
                    Text(toast)
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 8)
                        .background(Color.black.opacity(0.85))
                        .clipShape(Capsule())
                        .padding(.bottom, 70)
                        .transition(.opacity)
                }
            }
            .navigationDestination(item: $viewModel.activeQuizToLaunch) { quiz in
                QuizView(quiz: quiz)
            }
        }
    }

    // MARK: - Header

    private var chatHeader: some View {
        HStack(spacing: 12) {
            ZStack {
                Circle()
                    .fill(
                        LinearGradient(
                            colors: [Color(hex: 0x39_49_AB), Color(hex: 0x1E_88_E5)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 40, height: 40)

                Image(systemName: "brain.head.profile")
                    .font(.system(size: 20))
                    .foregroundStyle(.white)
            }

            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 6) {
                    Text("MediGyaan Clinical AI")
                        .font(.system(size: 15, weight: .bold))
                        .foregroundStyle(Color(hex: 0x1A_1C_2E))

                    Circle()
                        .fill(Color(hex: 0x4C_AF_50))
                        .frame(width: 8, height: 8)
                }

                Text("Specialized Medical Reasoning • NEET-PG & Clinical")
                    .font(.system(size: 11))
                    .foregroundStyle(Color.secondary)
            }

            Spacer()
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, 10)
        .background(AppTheme.Palette.cardBackground)
    }

    // MARK: - Suggestions

    private var suggestionsBar: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Suggested Medical Topics")
                .font(.system(size: 12, weight: .bold))
                .foregroundStyle(Color.secondary)
                .textCase(.uppercase)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 10) {
                    ForEach(viewModel.suggestions) { suggestion in
                        Button {
                            Task {
                                await viewModel.selectSuggestion(
                                    suggestion,
                                    api: api,
                                    userId: session.userId
                                )
                            }
                        } label: {
                            HStack(spacing: 6) {
                                Image(systemName: suggestion.icon)
                                    .font(.system(size: 13))
                                Text(suggestion.title)
                                    .font(.system(size: 13, weight: .semibold))
                            }
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                            .background(Color(hex: 0xEE_F2_FF))
                            .foregroundStyle(Color(hex: 0x39_49_AB))
                            .clipShape(Capsule())
                            .overlay(
                                Capsule()
                                    .stroke(Color(hex: 0xC7_D2_FE), lineWidth: 1)
                            )
                        }
                        .disabled(viewModel.isLoading)
                    }
                }
            }
        }
        .padding(.bottom, 6)
    }

    // MARK: - Message Rows

    private func messageRow(_ message: AiChatMessage) -> some View {
        VStack(alignment: message.isUser ? .trailing : .leading, spacing: 6) {
            HStack {
                if message.isUser { Spacer(minLength: 40) }

                VStack(alignment: message.isUser ? .trailing : .leading, spacing: 6) {
                    // Attachment chip inside user message
                    if let doc = message.attachmentName {
                        HStack(spacing: 6) {
                            Image(systemName: "doc.fill")
                            Text(doc)
                                .lineLimit(1)
                        }
                        .font(.system(size: 12, weight: .semibold))
                        .padding(.horizontal, 10)
                        .padding(.vertical, 4)
                        .background(Color.white.opacity(0.2))
                        .clipShape(Capsule())
                    }

                    // Message text
                    Text(LocalizedStringKey(message.text))
                        .font(.system(size: 15))
                        .foregroundStyle(message.isUser ? Color.white : AppTheme.Palette.textPrimary)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 12)
                        .background(
                            RoundedRectangle(cornerRadius: 18, style: .continuous)
                                .fill(message.isUser ? Color(hex: 0x39_49_AB) : AppTheme.Palette.cardBackground)
                        )
                        .overlay(
                            RoundedRectangle(cornerRadius: 18, style: .continuous)
                                .stroke(
                                    message.isUser ? Color.clear : Color.primary.opacity(0.08),
                                    lineWidth: 1
                                )
                        )
                }

                if !message.isUser { Spacer(minLength: 40) }
            }

            // Action toolbar for assistant messages (TTS, Copy, Share)
            if !message.isUser {
                HStack(spacing: 16) {
                    Button {
                        viewModel.toggleSpeech(for: message)
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: viewModel.isSpeaking ? "speaker.wave.3.fill" : "speaker.wave.2")
                            Text(viewModel.isSpeaking ? "Stop" : "Read")
                        }
                        .font(.system(size: 11, weight: .medium))
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                    }

                    Button {
                        viewModel.copyMessage(message)
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: "doc.on.doc")
                            Text("Copy")
                        }
                        .font(.system(size: 11, weight: .medium))
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                    }

                    ShareLink(item: message.text) {
                        HStack(spacing: 4) {
                            Image(systemName: "square.and.arrow.up")
                            Text("Share")
                        }
                        .font(.system(size: 11, weight: .medium))
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                    }

                    Spacer()
                }
                .padding(.leading, 6)
            }

            // Related MCQs Card (mirrors Android's question search cards)
            if !message.relatedQuestions.isEmpty {
                relatedQuestionsCard(message.relatedQuestions)
            }
        }
    }

    // MARK: - Related MCQs Card

    private func relatedQuestionsCard(_ questions: [Question]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: "checklist")
                    .foregroundStyle(Color(hex: 0x39_49_AB))
                Text("Related Practice MCQs")
                    .font(.system(size: 13, weight: .bold))
                    .foregroundStyle(Color(hex: 0x1A_1C_2E))
            }

            ForEach(questions) { q in
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(q.text)
                            .font(.system(size: 13))
                            .lineLimit(2)
                            .foregroundStyle(Color(hex: 0x1A_1C_2E))

                        Text("Topic: \(q.topic.isEmpty ? q.subject : q.topic)")
                            .font(.system(size: 11))
                            .foregroundStyle(Color.secondary)
                    }

                    Spacer()

                    Button {
                        let quiz = Quiz(
                            id: q.id,
                            title: q.topic.isEmpty ? "Related Practice" : q.topic,
                            questionCount: 1,
                            durationSeconds: 120,
                            subject: q.subject,
                            topic: q.topic
                        )
                        viewModel.activeQuizToLaunch = quiz
                    } label: {
                        Text("Practice")
                            .font(.system(size: 12, weight: .bold))
                            .foregroundStyle(.white)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(Color(hex: 0x39_49_AB))
                            .clipShape(Capsule())
                    }
                }
                .padding(10)
                .background(Color.white)
                .clipShape(RoundedRectangle(cornerRadius: 10))
            }
        }
        .padding(12)
        .background(Color(hex: 0xEE_F2_FF))
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(Color(hex: 0xC7_D2_FE), lineWidth: 1)
        )
        .padding(.top, 4)
    }

    // MARK: - Typing Indicator

    private var typingIndicator: some View {
        HStack(spacing: 8) {
            ProgressView()
                .scaleEffect(0.8)
            Text("MediGyaan AI is analyzing clinical evidence…")
                .font(.system(size: 13, weight: .medium))
                .foregroundStyle(Color.secondary)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .background(AppTheme.Palette.cardBackground)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    // MARK: - Attachment Banner

    private func attachmentBanner(_ name: String) -> some View {
        HStack(spacing: 8) {
            Image(systemName: "doc.fill")
                .foregroundStyle(Color(hex: 0x39_49_AB))

            Text(name)
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(Color(hex: 0x1A_1C_2E))
                .lineLimit(1)

            Spacer()

            Button {
                viewModel.removeAttachment()
            } label: {
                Image(systemName: "xmark.circle.fill")
                    .foregroundStyle(Color.secondary)
            }
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, 8)
        .background(Color(hex: 0xE8_EA_F6))
    }

    // MARK: - Input Bar

    private var inputBar: some View {
        HStack(spacing: 8) {
            // Document attachment button
            Menu {
                Button {
                    viewModel.attachDocument(name: "Clinical_Case_Report.pdf")
                } label: {
                    Label("Clinical Case Report", systemImage: "doc.text.fill")
                }

                Button {
                    viewModel.attachDocument(name: "Diagnostic_Lab_Panel.pdf")
                } label: {
                    Label("Diagnostic Lab Panel", systemImage: "cross.case.fill")
                }

                Button {
                    viewModel.attachDocument(name: "ECG_Telemetry_Report.pdf")
                } label: {
                    Label("ECG / Telemetry Report", systemImage: "waveform.path.ecg")
                }
            } label: {
                Image(systemName: "paperclip")
                    .font(.system(size: 20))
                    .foregroundStyle(Color(hex: 0x5C_6B_C0))
                    .frame(width: 36, height: 36)
            }

            // Text Input
            TextField("Ask clinical question, drug, or disease…", text: $viewModel.input, axis: .vertical)
                .lineLimit(1...4)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(AppTheme.Palette.cardBackground)
                .clipShape(RoundedRectangle(cornerRadius: 18))
                .overlay(
                    RoundedRectangle(cornerRadius: 18)
                        .stroke(Color.primary.opacity(0.12), lineWidth: 1)
                )

            // Send Button
            Button {
                Task {
                    await viewModel.sendCurrentInput(
                        api: api,
                        userId: session.userId
                    )
                }
            } label: {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.system(size: 34))
                    .foregroundStyle(
                        viewModel.input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || viewModel.isLoading
                            ? Color.gray.opacity(0.35)
                            : Color(hex: 0x39_49_AB)
                    )
            }
            .disabled(viewModel.input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || viewModel.isLoading)
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, 8)
        .background(AppTheme.Palette.background)
    }
}
