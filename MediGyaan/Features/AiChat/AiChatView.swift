import SwiftUI

/// Standalone Medical AI Assistant Chat screen.
/// Ports `AiChatActivity.kt` from the Android MediGyaan application 1:1.
struct AiChatView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @Environment(\.dismiss) private var dismiss
    @StateObject private var viewModel = AiChatViewModel()
    @State private var isShowingDocPicker = false
    @State private var isWorkspaceExpanded = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Header Bar matching Android's ChatHeader
                chatHeader

                // Research OS Workspace Bar
                workspaceStatusBar

                if let activeSkill = viewModel.activeSkillName {
                    activeSkillIndicator(activeSkill)
                }

                Divider()
                    .background(Color(hex: 0x2C3140))

                // Horizontal Tool Chips Carousel
                toolChipsBar

                Divider()
                    .background(Color(hex: 0x2C3140).opacity(0.5))

                // Messages Stream
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 14) {
                            // Prompt Suggestions (shown when few messages)
                            if viewModel.messages.count <= 1 {
                                welcomeHeader
                                suggestionsBar
                            }

                            ForEach(viewModel.messages) { message in
                                messageRow(message)
                                    .id(message.id)
                            }

                            if viewModel.isLoading {
                                typingIndicator
                                    .id("typing")
                            }
                        }
                        .padding(.horizontal, 14)
                        .padding(.vertical, 12)
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

                // Attachment Preview Banner (if attached)
                if let attachment = viewModel.attachedDocumentName {
                    attachmentBanner(attachment)
                }

                // Input Composer Bar
                inputComposer
            }
            .background(Color(hex: 0x0E131F).ignoresSafeArea())
            .navigationBarHidden(true)
            .overlay(alignment: .bottom) {
                if let toast = viewModel.toastMessage {
                    Text(toast)
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 8)
                        .background(Color.black.opacity(0.85))
                        .clipShape(Capsule())
                        .padding(.bottom, 72)
                        .transition(.opacity)
                }
            }
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
            .onAppear {
                RemoteLogger.log(tag: "AiChat_onAppear", message: "Medical AI Chat screen opened")
            }
        }
    }

    // MARK: - Top Header (ChatHeader)

    private var chatHeader: some View {
        HStack(spacing: 10) {
            Button {
                dismiss()
            } label: {
                Image(systemName: "chevron.left")
                    .font(.system(size: 17, weight: .semibold))
                    .foregroundStyle(Color(hex: 0xDDE7F5))
                    .frame(width: 32, height: 32)
            }

            // Circular MG Avatar Badge
            ZStack {
                Circle()
                    .fill(Color(hex: 0x272A52))
                    .frame(width: 36, height: 36)

                Text("MG")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(Color.white)
            }

            // Title and Always Active pulse
            VStack(alignment: .leading, spacing: 2) {
                Text("Medigyaan AI")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(Color.white)

                HStack(spacing: 5) {
                    Circle()
                        .fill(Color(hex: 0x4CAF50))
                        .frame(width: 7, height: 7)

                    Text("Always Active")
                        .font(.system(size: 11, weight: .medium))
                        .foregroundStyle(Color(hex: 0x9FB1C7))
                }
            }

            Spacer()

            // Model Mode Pill Button (cycles Balanced -> Fast -> Reasoning)
            Button {
                viewModel.cycleModelMode()
            } label: {
                Text(viewModel.modelMode.rawValue)
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(Color(hex: 0xBAC7FF))
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(Color(hex: 0x1C202B))
                    .clipShape(Capsule())
                    .overlay(
                        Capsule()
                            .stroke(Color(hex: 0x373C4E), lineWidth: 1)
                    )
            }

            // History Button
            Button {
                viewModel.clearChat()
            } label: {
                Image(systemName: "clock.arrow.circlepath")
                    .font(.system(size: 16))
                    .foregroundStyle(Color(hex: 0xDDE7F5))
                    .frame(width: 32, height: 32)
            }

            // Overflow Menu
            Menu {
                Button {
                    viewModel.attachDocument(name: "Clinical_Case_Report.pdf")
                } label: {
                    Label("📄 Upload Document", systemImage: "doc.fill")
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
                    viewModel.clearChat()
                } label: {
                    Label("Clear Chat", systemImage: "trash")
                }
            } label: {
                Image(systemName: "ellipsis")
                    .font(.system(size: 18))
                    .foregroundStyle(Color(hex: 0xDDE7F5))
                    .rotationEffect(.degrees(90))
                    .frame(width: 32, height: 32)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(Color(hex: 0x111624))
    }

    // MARK: - Research OS Workspace Status Bar (Collapsible)

    private var workspaceStatusBar: some View {
        DisclosureGroup(isExpanded: $isWorkspaceExpanded) {
            VStack(alignment: .leading, spacing: 6) {
                if !viewModel.workspace.researchQuestion.isEmpty {
                    HStack(alignment: .top, spacing: 4) {
                        Text("Question:")
                            .font(.system(size: 11, weight: .bold))
                            .foregroundStyle(Color(hex: 0x00E5FF))
                        Text(viewModel.workspace.researchQuestion)
                            .font(.system(size: 11))
                            .foregroundStyle(Color.white)
                    }
                }

                if let pico = viewModel.workspace.pico {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("PICO Framework:")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundStyle(Color(hex: 0x00FF41))
                        Text("P: \(pico.population) | I: \(pico.intervention) | C: \(pico.comparison) | O: \(pico.outcome)")
                            .font(.system(size: 10))
                            .foregroundStyle(Color(hex: 0xCBD5E1))
                    }
                }
            }
            .padding(.top, 4)
        } label: {
            HStack(spacing: 6) {
                Image(systemName: "cube.transparent")
                    .font(.system(size: 13, weight: .bold))
                    .foregroundStyle(Color(hex: 0x00E5FF))

                Text("RESEARCH OS WORKSPACE")
                    .font(.system(size: 10, weight: .black, design: .monospaced))
                    .foregroundStyle(Color.white)

                Spacer()

                Text(viewModel.workspace.currentSection.uppercased())
                    .font(.system(size: 9, weight: .black))
                    .foregroundStyle(Color.yellow)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Capsule().fill(Color.yellow.opacity(0.15)))
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(Color(hex: 0x0D111A))
    }

    private func activeSkillIndicator(_ skillName: String) -> some View {
        HStack(spacing: 8) {
            ProgressView()
                .tint(Color(hex: 0x00E5FF))
                .scaleEffect(0.8)
            Text("⚡ Executing Skill: \(skillName)...")
                .font(.system(size: 12, weight: .bold, design: .monospaced))
                .foregroundStyle(Color(hex: 0x00E5FF))
            Spacer()
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 6)
        .background(Color(hex: 0x081528))
    }

    // MARK: - Tool Chips Bar (Matches Android's Horizontal Tool Chips)

    private var toolChipsBar: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(viewModel.toolChips, id: \.self) { chip in
                    Button {
                        viewModel.onToolChipTapped(chip)
                    } label: {
                        Text(chip)
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundStyle(Color(hex: 0xDDE7F5))
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .background(Color(hex: 0x1C2232))
                            .clipShape(Capsule())
                            .overlay(
                                Capsule()
                                    .stroke(Color(hex: 0x2E364B), lineWidth: 1)
                            )
                    }
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 7)
        }
        .background(Color(hex: 0x111624))
    }

    // MARK: - Welcome Header

    private var welcomeHeader: some View {
        VStack(spacing: 6) {
            Text("🧠")
                .font(.system(size: 38))
                .padding(.top, 8)

            Text("How can I help you today?")
                .font(.system(size: 18, weight: .bold))
                .foregroundStyle(Color.white)

            Text("Ask about NEET PG, diseases, drugs — or use the tools above.")
                .font(.system(size: 12))
                .foregroundStyle(Color(hex: 0x9FB1C7))
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 8)
    }

    // MARK: - Suggestions

    private var suggestionsBar: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Suggested Medical Queries")
                .font(.system(size: 11, weight: .bold))
                .foregroundStyle(Color(hex: 0x8FA3BD))
                .textCase(.uppercase)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 10) {
                    ForEach(viewModel.suggestions) { suggestion in
                        Button {
                            viewModel.selectSuggestion(
                                suggestion,
                                api: api,
                                userId: session.userId
                            )
                        } label: {
                            HStack(spacing: 6) {
                                Image(systemName: suggestion.icon)
                                    .font(.system(size: 12))
                                Text(suggestion.title)
                                    .font(.system(size: 12, weight: .semibold))
                            }
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                            .background(Color(hex: 0x1C2232))
                            .foregroundStyle(Color(hex: 0xBAC7FF))
                            .clipShape(Capsule())
                            .overlay(
                                Capsule()
                                    .stroke(Color(hex: 0x2E364B), lineWidth: 1)
                            )
                        }
                        .disabled(viewModel.isLoading)
                    }
                }
            }
        }
        .padding(.vertical, 6)
    }

    // MARK: - Message Rows

    @ViewBuilder
    private func messageRow(_ message: AiChatMessage) -> some View {
        if message.isUser {
            userMessageBubble(message)
        } else {
            assistantMessageCard(message)
        }
    }

    // MARK: - User Message Bubble (Lavender Pill with Edit button)

    private func userMessageBubble(_ message: AiChatMessage) -> some View {
        VStack(alignment: .trailing, spacing: 4) {
            // Attachment badge if attached
            if let doc = message.attachmentName {
                HStack(spacing: 6) {
                    Image(systemName: "doc.fill")
                    Text(doc)
                        .lineLimit(1)
                }
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(Color(hex: 0xBAC7FF))
                .padding(.horizontal, 10)
                .padding(.vertical, 4)
                .background(Color(hex: 0x272A52))
                .clipShape(Capsule())
            }

            // Message text container
            Text(message.text)
                .font(.system(size: 14))
                .foregroundStyle(Color(hex: 0x111B21))
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
                .background(
                    UnevenRoundedRectangle(
                        topLeadingRadius: 18,
                        bottomLeadingRadius: 18,
                        bottomTrailingRadius: 3,
                        topTrailingRadius: 18
                    )
                    .fill(Color(hex: 0xBAC7FF))
                )
                .frame(maxWidth: 300, alignment: .trailing)

            // Sub-row: timestamp + Edit chip
            HStack(spacing: 6) {
                Text(formattedTime(message.timestamp))
                    .font(.system(size: 11))
                    .foregroundStyle(Color(hex: 0x8FA3BD))

                Button {
                    viewModel.startEdit(message: message)
                } label: {
                    Text("✏️ Edit")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(Color(hex: 0xBAC7FF))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 2)
                        .background(Color(hex: 0x1C2232))
                        .clipShape(Capsule())
                        .overlay(
                            Capsule().stroke(Color(hex: 0x2E364B), lineWidth: 0.8)
                        )
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .trailing)
        .padding(.vertical, 2)
    }

    // MARK: - Assistant Message Card (Dark Card with AI badge)

    private func assistantMessageCard(_ message: AiChatMessage) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top, spacing: 10) {
                // AI circular avatar
                ZStack {
                    Circle()
                        .fill(Color(hex: 0x272A52))
                        .frame(width: 30, height: 30)

                    Text("AI")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundStyle(Color.white)
                }
                .padding(.top, 2)

                // Dark card container
                VStack(alignment: .leading, spacing: 8) {
                    Text(LocalizedStringKey(message.text))
                        .font(.system(size: 14))
                        .foregroundStyle(Color(hex: 0xF2F6FC))
                        .lineSpacing(3)

                    // Action row: TTS, Copy, Share, Feedback, Regenerate, Response Time
                    HStack(spacing: 12) {
                        Button {
                            viewModel.toggleSpeech(for: message)
                        } label: {
                            HStack(spacing: 3) {
                                Image(systemName: viewModel.isSpeaking ? "speaker.wave.3.fill" : "speaker.wave.2")
                                Text(viewModel.isSpeaking ? "Stop" : "Read")
                            }
                            .font(.system(size: 11, weight: .medium))
                            .foregroundStyle(Color(hex: 0x8FA3BD))
                        }

                        Button {
                            viewModel.copyMessage(message)
                        } label: {
                            HStack(spacing: 3) {
                                Image(systemName: "doc.on.doc")
                                Text("Copy")
                            }
                            .font(.system(size: 11, weight: .medium))
                            .foregroundStyle(Color(hex: 0x8FA3BD))
                        }

                        ShareLink(item: message.text) {
                            Image(systemName: "square.and.arrow.up")
                                .font(.system(size: 11))
                                .foregroundStyle(Color(hex: 0x8FA3BD))
                        }

                        Button {
                            viewModel.toggleFeedback(for: message, like: true)
                        } label: {
                            Image(systemName: message.feedback == 1 ? "hand.thumbsup.fill" : "hand.thumbsup")
                                .font(.system(size: 11))
                                .foregroundStyle(message.feedback == 1 ? Color(hex: 0x62E49D) : Color(hex: 0x8FA3BD))
                        }

                        Button {
                            viewModel.toggleFeedback(for: message, like: false)
                        } label: {
                            Image(systemName: message.feedback == -1 ? "hand.thumbsdown.fill" : "hand.thumbsdown")
                                .font(.system(size: 11))
                                .foregroundStyle(message.feedback == -1 ? Color(hex: 0xEF5350) : Color(hex: 0x8FA3BD))
                        }

                        Button {
                            viewModel.regenerate(message: message, api: api, userId: session.userId)
                        } label: {
                            Image(systemName: "arrow.clockwise")
                                .font(.system(size: 11))
                                .foregroundStyle(Color(hex: 0x8FA3BD))
                        }

                        Spacer()

                        if let ms = message.responseTimeMs {
                            Text("⚡ \(ms)ms")
                                .font(.system(size: 10, weight: .semibold))
                                .foregroundStyle(Color(hex: 0x8FA3BD))
                        }
                    }
                    .padding(.top, 4)
                }
                .padding(12)
                .background(
                    UnevenRoundedRectangle(
                        topLeadingRadius: 3,
                        bottomLeadingRadius: 18,
                        bottomTrailingRadius: 18,
                        topTrailingRadius: 18
                    )
                    .fill(Color(hex: 0x161C2A))
                )
                .overlay(
                    UnevenRoundedRectangle(
                        topLeadingRadius: 3,
                        bottomLeadingRadius: 18,
                        bottomTrailingRadius: 18,
                        topTrailingRadius: 18
                    )
                    .stroke(Color(hex: 0x2A3348), lineWidth: 1)
                )
            }

            if let outcome = message.skillOutcome {
                skillOutcomeFeatureCard(outcome, skillName: message.skillName ?? "Clinical Research Skill")
            }

            // Attached Feature Cards (matching Android)
            if let counsel = message.counselCard {
                counselorFeatureCard(counsel)
            }

            if let thesis = message.thesisCard {
                thesisFeatureCard(thesis)
            }

            if let chapter = message.chapterCard {
                chapterFeatureCard(chapter)
            }

            if !message.relatedQuestions.isEmpty {
                relatedQuestionsCard(message.relatedQuestions)
            }
        }
        .padding(.vertical, 2)
    }

    // MARK: - Research Skill Outcome Card

    private func skillOutcomeFeatureCard(_ outcome: SkillOutcome, skillName: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                ZStack {
                    Circle()
                        .fill(Color(hex: 0x00E5FF).opacity(0.2))
                        .frame(width: 28, height: 28)
                    Image(systemName: "sparkles")
                        .font(.system(size: 13, weight: .bold))
                        .foregroundStyle(Color(hex: 0x00E5FF))
                }

                VStack(alignment: .leading, spacing: 2) {
                    Text(skillName.uppercased())
                        .font(.system(size: 11, weight: .black, design: .monospaced))
                        .foregroundStyle(Color(hex: 0x00E5FF))

                    if !outcome.uiNote.isEmpty {
                        Text(outcome.uiNote)
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundStyle(Color.white)
                    }
                }

                Spacer()

                Text("VERIFIED")
                    .font(.system(size: 9, weight: .black))
                    .foregroundStyle(Color(hex: 0x00FF41))
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Capsule().fill(Color(hex: 0x00FF41).opacity(0.15)))
            }

            Text(LocalizedStringKey(outcome.contextText))
                .font(.system(size: 13))
                .foregroundStyle(Color(hex: 0xE2E8F0))
                .lineSpacing(3)
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 14)
                .fill(Color(hex: 0x111927))
                .overlay(
                    RoundedRectangle(cornerRadius: 14)
                        .stroke(Color(hex: 0x00E5FF).opacity(0.35), lineWidth: 1)
                )
        )
    }

    // MARK: - NEET PG AI Counselor Card (Collapsible)

    @State private var isCounselorExpanded = true

    private func counselorFeatureCard(_ data: CounselCardData) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            // Card Header
            Button {
                withAnimation { isCounselorExpanded.toggle() }
            } label: {
                HStack(spacing: 8) {
                    ZStack {
                        Circle()
                            .fill(Color(hex: 0x2A325F))
                            .frame(width: 28, height: 28)
                        Text("✨")
                            .font(.system(size: 14))
                    }

                    Text("✨ NEET PG AI Counselor")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundStyle(Color.white)

                    Spacer()

                    Image(systemName: isCounselorExpanded ? "chevron.up" : "chevron.down")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(Color(hex: 0x8FA3BD))
                }
            }

            if isCounselorExpanded {
                if !data.summary.isEmpty {
                    Text(data.summary)
                        .font(.system(size: 12))
                        .foregroundStyle(Color(hex: 0xDDE7F5))
                        .padding(.vertical, 2)
                }

                // Options count & Sort bar
                HStack {
                    Text("\(data.results.count) options found")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(Color(hex: 0x8FA3BD))

                    Spacer()

                    HStack(spacing: 4) {
                        Text("↕ Recommended")
                            .font(.system(size: 11, weight: .bold))
                            .foregroundStyle(Color(hex: 0xBAC7FF))
                    }
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(Color(hex: 0x252C3E))
                    .clipShape(Capsule())
                }

                // List of Colleges
                ForEach(data.results) { college in
                    collegeCard(college)
                }
            }
        }
        .padding(14)
        .background(Color(hex: 0x151B28))
        .clipShape(RoundedRectangle(cornerRadius: 18))
        .overlay(
            RoundedRectangle(cornerRadius: 18)
                .stroke(Color(hex: 0x2E3A52), lineWidth: 1)
        )
        .padding(.leading, 40)
    }

    private func collegeCard(_ college: CounselCollege) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(college.institute)
                        .font(.system(size: 13, weight: .bold))
                        .foregroundStyle(Color.white)
                        .lineLimit(2)

                    Text(college.course)
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundStyle(Color(hex: 0x48D6C8))
                }

                Spacer()

                // Chance pill
                Text(college.chance)
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(chanceColor(college.chance))
                    .clipShape(Capsule())
            }

            HStack(spacing: 6) {
                infoTag(college.state)
                infoTag(college.quota)
                infoTag("Closing: #\(college.closingRank)")
            }

            HStack(spacing: 12) {
                Text("Fee: \(college.feePerYear)")
                    .font(.system(size: 11))
                    .foregroundStyle(Color(hex: 0xF4C95D))

                Text("Stipend: \(college.stipendYear1)")
                    .font(.system(size: 11))
                    .foregroundStyle(Color(hex: 0x62E49D))

                Text("Bond: \(college.bondYears)")
                    .font(.system(size: 11))
                    .foregroundStyle(Color(hex: 0x8FA3BD))
            }
        }
        .padding(10)
        .background(Color(hex: 0x1E2638))
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color(hex: 0x303E5A), lineWidth: 1)
        )
    }

    private func infoTag(_ text: String) -> some View {
        Text(text)
            .font(.system(size: 10, weight: .medium))
            .foregroundStyle(Color(hex: 0xBAC7FF))
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(Color(hex: 0x252F46))
            .clipShape(RoundedRectangle(cornerRadius: 6))
    }

    private func chanceColor(_ chance: String) -> Color {
        switch chance.lowercased() {
        case "dream": return Color(hex: 0x7C3AED)
        case "target": return Color(hex: 0x2563EB)
        default: return Color(hex: 0x059669)
        }
    }

    // MARK: - Thesis Feature Card

    private func thesisFeatureCard(_ data: ThesisCardData) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Text("🎓")
                    .font(.system(size: 16))
                Text("Thesis Topics Catalog")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(Color.white)
            }

            ForEach(data.results) { topic in
                VStack(alignment: .leading, spacing: 4) {
                    Text(topic.displayTitle)
                        .font(.system(size: 13, weight: .bold))
                        .foregroundStyle(Color.white)

                    Text(topic.snippet)
                        .font(.system(size: 11))
                        .foregroundStyle(Color(hex: 0x9FB1C7))
                        .lineLimit(2)

                    HStack {
                        infoTag(topic.studyType)
                        infoTag("Difficulty: \(topic.difficulty)")
                    }
                }
                .padding(8)
                .background(Color(hex: 0x1E2638))
                .clipShape(RoundedRectangle(cornerRadius: 10))
            }
        }
        .padding(12)
        .background(Color(hex: 0x151B28))
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .overlay(
            RoundedRectangle(cornerRadius: 16).stroke(Color(hex: 0x2E3A52), lineWidth: 1)
        )
        .padding(.leading, 40)
    }

    // MARK: - Chapter Feature Card

    private func chapterFeatureCard(_ data: ChapterCardData) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Text("📚")
                    .font(.system(size: 16))
                Text("Drafted Chapter: \(data.chapterName)")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(Color.white)
            }

            ForEach(data.sections, id: \.self) { sec in
                HStack(spacing: 6) {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 12))
                        .foregroundStyle(Color(hex: 0x62E49D))
                    Text(sec)
                        .font(.system(size: 12))
                        .foregroundStyle(Color(hex: 0xDDE7F5))
                }
            }
        }
        .padding(12)
        .background(Color(hex: 0x151B28))
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .overlay(
            RoundedRectangle(cornerRadius: 16).stroke(Color(hex: 0x2E3A52), lineWidth: 1)
        )
        .padding(.leading, 40)
    }

    // MARK: - Related MCQs Card

    private func relatedQuestionsCard(_ questions: [Question]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 6) {
                Image(systemName: "checklist")
                    .foregroundStyle(Color(hex: 0x48D6C8))
                Text("Related Practice MCQs")
                    .font(.system(size: 13, weight: .bold))
                    .foregroundStyle(Color.white)
            }

            ForEach(questions) { q in
                relatedQuestionRow(q)
            }
        }
        .padding(12)
        .background(Color(hex: 0x151B28))
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .overlay(
            RoundedRectangle(cornerRadius: 16).stroke(Color(hex: 0x2E3A52), lineWidth: 1)
        )
        .padding(.leading, 40)
    }

    private func relatedQuestionRow(_ q: Question) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(q.text)
                    .font(.system(size: 12))
                    .lineLimit(2)
                    .foregroundStyle(Color(hex: 0xDDE7F5))

                let topicTitle = q.topic.isEmpty ? q.subject : q.topic
                Text("Topic: \(topicTitle)")
                    .font(.system(size: 11))
                    .foregroundStyle(Color(hex: 0x8FA3BD))
            }

            Spacer()

            Button {
                let quiz = Quiz(
                    id: q.id,
                    title: q.topic.isEmpty ? "Related Practice" : q.topic,
                    topic: q.topic,
                    subject: q.subject,
                    questionCount: 1,
                    durationSeconds: 120
                )
                viewModel.activeQuizToLaunch = quiz
            } label: {
                Text("Practice")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(Color(hex: 0x07111F))
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(Color(hex: 0x48D6C8))
                    .clipShape(Capsule())
            }
        }
        .padding(8)
        .background(Color(hex: 0x1E2638))
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }

    // MARK: - Typing Indicator

    private var typingIndicator: some View {
        HStack(spacing: 8) {
            ProgressView()
                .scaleEffect(0.8)
                .tint(Color(hex: 0xBAC7FF))

            Text("MediGyaan AI is analyzing clinical evidence…")
                .font(.system(size: 12, weight: .medium))
                .foregroundStyle(Color(hex: 0x8FA3BD))
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 8)
        .background(Color(hex: 0x161C2A))
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .padding(.leading, 40)
    }

    // MARK: - Attachment Banner

    private func attachmentBanner(_ name: String) -> some View {
        HStack(spacing: 8) {
            Image(systemName: "doc.fill")
                .foregroundStyle(Color(hex: 0xBAC7FF))

            Text(name)
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(Color.white)
                .lineLimit(1)

            Spacer()

            Button {
                viewModel.removeAttachment()
            } label: {
                Image(systemName: "xmark.circle.fill")
                    .foregroundStyle(Color(hex: 0x8FA3BD))
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 6)
        .background(Color(hex: 0x1C2232))
    }

    // MARK: - Input Composer Bar (Matches Android's 26dp pill)

    private var inputComposer: some View {
        HStack(spacing: 8) {
            // Pill container
            HStack(spacing: 6) {
                // Document attachment paperclip
                Menu {
                    Button {
                        viewModel.attachDocument(name: "Clinical_Case_Report.pdf")
                    } label: {
                        Label("Clinical Case Report (PDF)", systemImage: "doc.text.fill")
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
                        .font(.system(size: 18))
                        .foregroundStyle(Color(hex: 0x8FA3BD))
                        .frame(width: 32, height: 32)
                }

                // Text Input
                TextField("Ask anything…", text: $viewModel.input, axis: .vertical)
                    .font(.system(size: 14))
                    .foregroundStyle(Color.white)
                    .lineLimit(1...4)
                    .padding(.vertical, 6)

                // Mic voice button
                Button {
                    viewModel.showToast("Voice input activated 🎙️")
                } label: {
                    Image(systemName: "mic.fill")
                        .font(.system(size: 16))
                        .foregroundStyle(Color(hex: 0x8FA3BD))
                        .frame(width: 30, height: 30)
                }
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(Color(hex: 0x161C2A))
            .clipShape(RoundedRectangle(cornerRadius: 24))
            .overlay(
                RoundedRectangle(cornerRadius: 24)
                    .stroke(Color(hex: 0x2A3348), lineWidth: 1)
            )

            // Circular Send / Stop Button
            if viewModel.isLoading {
                Button {
                    viewModel.stopGenerating()
                } label: {
                    ZStack {
                        Circle()
                            .fill(Color(hex: 0xEF5350))
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
                            .fill(
                                viewModel.input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                                    ? Color(hex: 0x252F46)
                                    : Color(hex: 0x5C6BC0)
                            )
                            .frame(width: 38, height: 38)

                        Image(systemName: "arrow.up")
                            .font(.system(size: 16, weight: .bold))
                            .foregroundStyle(Color.white)
                    }
                }
                .disabled(viewModel.input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(Color(hex: 0x0E131F))
    }

    private func formattedTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "h:mm a"
        return formatter.string(from: date)
    }
}

#Preview {
    AiChatView()
        .environmentObject(SessionStore())
        .environment(\.api, .live)
}
