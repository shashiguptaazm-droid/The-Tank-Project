import SwiftUI

/// Thesis Studio home.
///
/// Ports the Android thesis cluster: `ThesisAnalyzerActivity`,
/// `thesis_workspace`, `TopicSelector`, `ExportThemeSelectionActivity`, and the
/// PDF/DOCX exporters, all backed by `thesis_session_backend.php`.
struct ThesisHomeView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api

    @State private var state: LoadState<ThesisSession> = .idle
    @State private var errorMessage: String?
    @State private var isCreating = false

    var body: some View {
        Group {
            switch state {
            case .idle, .loading:
                LoadingStateView(message: "Opening your thesis workspace…")

            case let .failed(message):
                ErrorStateView(message: message) { Task { await load() } }

            case let .loaded(thesis):
                if thesis.chapters.isEmpty {
                    EmptyStateView(
                        title: "Start your thesis",
                        message: "Create a workspace and MediGyaan will help you draft each chapter.",
                        systemImage: "doc.text",
                        actionTitle: isCreating ? nil : "Create workspace"
                    ) {
                        Task { await createWorkspace() }
                    }
                } else {
                    workspace(thesis)
                }
            }
        }
        .screenBackground()
        .navigationTitle("Thesis Studio")
        .navigationBarTitleDisplayMode(.inline)
        .errorAlert(message: $errorMessage)
        .task { await load() }
        .refreshable { await load() }
    }

    // MARK: - Sections

    private func workspace(_ thesis: ThesisSession) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.lg) {
                CardContainer {
                    VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                        Text(thesis.title.isEmpty ? "Untitled thesis" : thesis.title)
                            .font(AppTheme.Font.title)

                        if !thesis.topic.isEmpty {
                            Text(thesis.topic)
                                .font(AppTheme.Font.callout)
                                .foregroundStyle(AppTheme.Palette.textSecondary)
                                .fixedSize(horizontal: false, vertical: true)
                        }

                        HStack(spacing: AppTheme.Spacing.xs) {
                            if !thesis.speciality.isEmpty {
                                TagBadge(text: thesis.speciality, tint: AppTheme.Palette.accent)
                            }
                            if !thesis.studyType.isEmpty {
                                TagBadge(text: thesis.studyType, tint: AppTheme.Palette.info)
                            }
                        }

                        ProgressRow(
                            title: "Chapters complete",
                            value: thesis.progress,
                            caption: "\(thesis.completedChapters)/\(thesis.chapters.count)"
                        )
                        .padding(.top, AppTheme.Spacing.xs)
                    }
                }

                VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                    SectionHeader(title: "Chapters")

                    ForEach(thesis.chapters.sorted { $0.index < $1.index }) { chapter in
                        NavigationLink {
                            ThesisChapterView(session: thesis, chapter: chapter)
                        } label: {
                            ChapterRow(chapter: chapter)
                        }
                        .buttonStyle(.plain)
                    }
                }

                VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                    SectionHeader(title: "Tools")

                    LazyVGrid(
                        columns: Array(repeating: GridItem(.flexible(), spacing: AppTheme.Spacing.sm), count: 2),
                        spacing: AppTheme.Spacing.sm
                    ) {
                        NavigationLink {
                            ReferenceLibraryView(session: thesis)
                        } label: {
                            QuickActionTile(title: "References", systemImage: "books.vertical.fill", tint: AppTheme.Palette.info)
                        }
                        NavigationLink {
                            PrismaView(session: thesis)
                        } label: {
                            QuickActionTile(title: "PRISMA flow", systemImage: "flowchart.fill", tint: AppTheme.Palette.accent)
                        }
                        NavigationLink {
                            ThemeExportView(session: thesis)
                        } label: {
                            QuickActionTile(title: "Export theme", systemImage: "paintbrush.fill", tint: AppTheme.Palette.warning)
                        }
                        NavigationLink {
                            ThesisChecklistView(session: thesis)
                        } label: {
                            QuickActionTile(title: "Checklist", systemImage: "checklist", tint: AppTheme.Palette.success)
                        }
                    }
                }
            }
            .padding(AppTheme.Spacing.md)
        }
    }

    // MARK: - Networking

    private func load() async {
        let userId = session.userId
        guard userId > 0 else { return }
        await state.load { [api] in
            try await api.thesis.session(userId: userId)
        }
    }

    private func createWorkspace() async {
        guard !isCreating else { return }
        isCreating = true
        defer { isCreating = false }

        do {
            // The backend creates the workspace implicitly on first load with an
            // explicit action, then returns the seeded chapter list.
            let thesis = try await api.thesis.session(userId: session.userId)
            state = .loaded(thesis)
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

/// One chapter row with completion state.
struct ChapterRow: View {
    let chapter: ThesisChapter

    var body: some View {
        CardContainer(padding: AppTheme.Spacing.sm) {
            HStack(spacing: AppTheme.Spacing.md) {
                ZStack {
                    Circle()
                        .fill(chapter.isComplete
                            ? AppTheme.Palette.success.opacity(0.15)
                            : AppTheme.Palette.primary.opacity(0.12))
                    Image(systemName: chapter.isComplete ? "checkmark" : "doc.text")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(chapter.isComplete
                            ? AppTheme.Palette.success
                            : AppTheme.Palette.primary)
                }
                .frame(width: 34, height: 34)

                VStack(alignment: .leading, spacing: 2) {
                    Text(chapter.title.isEmpty ? "Chapter \(chapter.index + 1)" : chapter.title)
                        .font(AppTheme.Font.callout.weight(.medium))
                        .lineLimit(1)
                    Text(chapter.wordCount > 0
                        ? "\(chapter.wordCount) words"
                        : (chapter.isComplete ? "Complete" : "Not started"))
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(AppTheme.Palette.textSecondary.opacity(0.6))
            }
        }
    }
}

/// Chapter editor with AI drafting.
struct ThesisChapterView: View {

    let session: ThesisSession
    let chapter: ThesisChapter

    @Environment(\.api) private var api
    @EnvironmentObject private var appSession: SessionStore

    @State private var content = ""
    @State private var isGenerating = false
    @State private var isSaving = false
    @State private var errorMessage: String?
    @State private var didPrefill = false

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                    TextEditor(text: $content)
                        .frame(minHeight: 320)
                        .padding(AppTheme.Spacing.sm)
                        .background(
                            RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                                .fill(AppTheme.Palette.cardBackground)
                        )
                        .overlay(alignment: .topLeading) {
                            if content.isEmpty {
                                Text("Write, or let MediGyaan draft this chapter for you…")
                                    .font(AppTheme.Font.callout)
                                    .foregroundStyle(AppTheme.Palette.textSecondary)
                                    .padding(AppTheme.Spacing.md)
                                    .allowsHitTesting(false)
                            }
                        }

                    HStack {
                        Text("\(content.split(separator: " ").count) words")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                        Spacer()
                    }

                    VStack(spacing: AppTheme.Spacing.sm) {
                        PrimaryButton(title: "Save", isLoading: isSaving) {
                            Task { await save() }
                        }
                        SecondaryButton(title: "Generate with AI", systemImage: "wand.and.stars") {
                            Task { await generate() }
                        }
                        .disabled(isGenerating)
                        .overlay {
                            if isGenerating {
                                ProgressView()
                            }
                        }
                    }
                }
                .padding(AppTheme.Spacing.md)
            }
        }
        .screenBackground()
        .navigationTitle(chapter.title.isEmpty ? "Chapter" : chapter.title)
        .navigationBarTitleDisplayMode(.inline)
        .errorAlert(message: $errorMessage)
        .onAppear {
            guard !didPrefill else { return }
            didPrefill = true
            content = chapter.content
        }
    }

    private func save() async {
        guard !isSaving else { return }
        isSaving = true
        defer { isSaving = false }

        do {
            let response = try await api.thesis.saveChapter(
                userId: appSession.userId,
                sessionId: session.id,
                chapterIndex: chapter.index,
                content: content
            )
            if !response.success {
                errorMessage = response.message.isEmpty ? "Could not save the chapter." : response.message
            }
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func generate() async {
        guard !isGenerating else { return }
        isGenerating = true
        defer { isGenerating = false }

        do {
            let response = try await api.thesis.generateChapter(
                userId: appSession.userId,
                sessionId: session.id,
                chapterIndex: chapter.index,
                chapterTitle: chapter.title,
                instructions: ""
            )
            guard response.success else {
                errorMessage = response.message.isEmpty
                    ? "Chapter generation failed. Please try again."
                    : response.message
                return
            }
            // Generation runs asynchronously on the server; refresh the session
            // to pick up the drafted text.
            let refreshed = try await api.thesis.session(userId: appSession.userId, sessionId: session.id)
            if let updated = refreshed.chapters.first(where: { $0.index == chapter.index }) {
                content = updated.content
            }
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

#Preview {
    NavigationStack {
        ThesisHomeView()
            .environmentObject(SessionStore())
            .environment(\.api, .live)
    }
}
