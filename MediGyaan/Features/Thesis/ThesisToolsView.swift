import SwiftUI

/// Reference library backed by `reference_cache_backend.php`.
///
/// Ports the Android `thesis_references.php` / `reference_cache.php` screens
/// and the Vancouver-style citation preview used by the exporters.
struct ReferenceLibraryView: View {

    let session: ThesisSession

    @Environment(\.api) private var api

    @State private var state: LoadState<[ThesisReference]> = .idle
    @State private var searchText = ""

    var body: some View {
        VStack(spacing: 0) {
            Group {
                switch state {
                case .idle, .loading:
                    LoadingStateView(message: "Loading references…")
                case let .failed(message):
                    ErrorStateView(message: message) { Task { await load() } }
                case let .loaded(references):
                    if references.isEmpty {
                        EmptyStateView(
                            title: "No references",
                            message: "References you add or import will appear here.",
                            systemImage: "books.vertical"
                        )
                    } else {
                        list(references)
                    }
                }
            }
        }
        .screenBackground()
        .navigationTitle("References")
        .navigationBarTitleDisplayMode(.inline)
        .searchable(text: $searchText, prompt: "Search references")
        .task { await load() }
        .refreshable { await load() }
    }

    private func list(_ references: [ThesisReference]) -> some View {
        let filtered = searchText.trimmingCharacters(in: .whitespaces).isEmpty
            ? references
            : references.filter {
                $0.title.localizedCaseInsensitiveContains(searchText)
                    || $0.authors.localizedCaseInsensitiveContains(searchText)
            }

        return ScrollView {
            LazyVStack(spacing: AppTheme.Spacing.sm) {
                ForEach(filtered) { reference in
                    CardContainer(padding: AppTheme.Spacing.sm) {
                        VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
                            Text(reference.title.isEmpty ? "Untitled reference" : reference.title)
                                .font(AppTheme.Font.callout.weight(.medium))
                                .fixedSize(horizontal: false, vertical: true)

                            if !reference.authors.isEmpty {
                                Text(reference.authors)
                                    .font(AppTheme.Font.caption)
                                    .foregroundStyle(AppTheme.Palette.textSecondary)
                                    .lineLimit(2)
                            }

                            HStack(spacing: AppTheme.Spacing.xs) {
                                if !reference.journal.isEmpty {
                                    TagBadge(text: reference.journal, tint: AppTheme.Palette.info)
                                }
                                if !reference.year.isEmpty {
                                    TagBadge(text: reference.year, tint: AppTheme.Palette.accent)
                                }
                            }

                            Text(reference.citation)
                                .font(AppTheme.Font.caption)
                                .foregroundStyle(AppTheme.Palette.textSecondary)
                                .lineLimit(3)
                                .textSelection(.enabled)
                        }
                    }
                }
            }
            .padding(AppTheme.Spacing.md)
        }
    }

    private func load() async {
        await state.load { [api] in
            try await api.thesis.references(sessionId: session.id)
        }
    }
}

/// PRISMA flow-diagram counts.
struct PrismaView: View {

    let session: ThesisSession

    @Environment(\.api) private var api

    @State private var counts = PrismaCounts.empty
    @State private var isSaving = false
    @State private var errorMessage: String?
    @State private var didSave = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.lg) {
                CardContainer {
                    Text("Record how many records moved through each screening stage. MediGyaan builds the PRISMA flow diagram from these numbers.")
                        .font(AppTheme.Font.callout)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                VStack(spacing: AppTheme.Spacing.md) {
                    countField("Records identified", value: $counts.identified, tint: AppTheme.Palette.info)
                    countField("Records screened", value: $counts.screened, tint: AppTheme.Palette.primary)
                    countField("Records excluded", value: $counts.excluded, tint: AppTheme.Palette.danger)
                    countField("Full-text eligible", value: $counts.eligible, tint: AppTheme.Palette.warning)
                    countField("Studies included", value: $counts.included, tint: AppTheme.Palette.success)
                }

                PrimaryButton(
                    title: didSave ? "Saved" : "Save PRISMA counts",
                    isLoading: isSaving
                ) {
                    Task { await save() }
                }

                if didSave {
                    Label("PRISMA data saved", systemImage: "checkmark.circle.fill")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.success)
                }
            }
            .padding(AppTheme.Spacing.md)
        }
        .screenBackground()
        .navigationTitle("PRISMA flow")
        .navigationBarTitleDisplayMode(.inline)
        .errorAlert(message: $errorMessage)
    }

    private func countField(_ title: String, value: Binding<Int>, tint: Color) -> some View {
        HStack {
            Text(title)
                .font(AppTheme.Font.callout)
            Spacer()
            TextField(
                "0",
                value: value,
                format: .number
            )
            .keyboardType(.numberPad)
            .multilineTextAlignment(.trailing)
            .frame(width: 90)
            .padding(AppTheme.Spacing.sm)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                    .fill(tint.opacity(0.10))
            )
        }
    }

    private func save() async {
        guard !isSaving else { return }
        isSaving = true
        defer { isSaving = false }

        do {
            let response = try await api.thesis.prisma(sessionId: session.id, counts: counts)
            if response.success {
                didSave = true
            } else {
                errorMessage = response.message.isEmpty ? "Could not save PRISMA data." : response.message
            }
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

/// Export theme selection. Ports `ExportThemeSelectionActivity`.
struct ThemeExportView: View {

    let session: ThesisSession

    @Environment(\.api) private var api

    @State private var selectedTheme = "classic"
    @State private var isExporting = false
    @State private var errorMessage: String?
    @State private var didExport = false

    private let themes: [(id: String, title: String, subtitle: String, icon: String)] = [
        ("classic", "Classic", "Times New Roman, standard university format", "textformat"),
        ("modern", "Modern", "Clean sans-serif with wider spacing", "textformat.size"),
        ("compact", "Compact", "Reduced margins to fit page limits", "arrow.down.right.and.arrow.up.left"),
    ]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.lg) {
                VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                    SectionHeader(title: "Choose a layout")

                    ForEach(themes, id: \.id) { theme in
                        Button {
                            selectedTheme = theme.id
                        } label: {
                            CardContainer(padding: AppTheme.Spacing.sm) {
                                HStack(spacing: AppTheme.Spacing.md) {
                                    Image(systemName: theme.icon)
                                        .font(.system(size: 18, weight: .semibold))
                                        .foregroundStyle(AppTheme.Palette.primary)
                                        .frame(width: 38, height: 38)
                                        .background(
                                            RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                                                .fill(AppTheme.Palette.primary.opacity(0.12))
                                        )

                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(theme.title)
                                            .font(AppTheme.Font.callout.weight(.semibold))
                                            .foregroundStyle(AppTheme.Palette.textPrimary)
                                        Text(theme.subtitle)
                                            .font(AppTheme.Font.caption)
                                            .foregroundStyle(AppTheme.Palette.textSecondary)
                                    }

                                    Spacer()

                                    Image(systemName: selectedTheme == theme.id
                                        ? "checkmark.circle.fill"
                                        : "circle")
                                    .foregroundStyle(selectedTheme == theme.id
                                        ? AppTheme.Palette.primary
                                        : Color.primary.opacity(0.2))
                                }
                            }
                        }
                        .buttonStyle(.plain)
                    }
                }

                PrimaryButton(
                    title: didExport ? "Theme applied" : "Apply theme",
                    isLoading: isExporting
                ) {
                    Task { await apply() }
                }
            }
            .padding(AppTheme.Spacing.md)
        }
        .screenBackground()
        .navigationTitle("Export theme")
        .navigationBarTitleDisplayMode(.inline)
        .errorAlert(message: $errorMessage)
    }

    private func apply() async {
        guard !isExporting else { return }
        isExporting = true
        defer { isExporting = false }

        do {
            let response = try await api.thesis.themeLayout(sessionId: session.id, themeId: selectedTheme)
            if response.success {
                didExport = true
            } else {
                errorMessage = response.message.isEmpty ? "Could not apply the theme." : response.message
            }
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

/// Thesis completion checklist. Ports `thesis_checklist.php`.
struct ThesisChecklistView: View {

    let session: ThesisSession

    @Environment(\.api) private var api

    @State private var state: LoadState<[ThesisChecklistItem]> = .idle

    var body: some View {
        Group {
            switch state {
            case .idle, .loading:
                LoadingStateView(message: "Loading checklist…")
            case let .failed(message):
                ErrorStateView(message: message) { Task { await load() } }
            case let .loaded(items):
                if items.isEmpty {
                    EmptyStateView(
                        title: "Checklist unavailable",
                        message: "The checklist is generated once your chapters exist.",
                        systemImage: "checklist"
                    )
                } else {
                    list(items)
                }
            }
        }
        .screenBackground()
        .navigationTitle("Checklist")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
        .refreshable { await load() }
    }

    private func list(_ items: [ThesisChecklistItem]) -> some View {
        let done = items.filter(\.isDone).count

        return ScrollView {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                CardContainer {
                    ProgressRow(
                        title: "Completion",
                        value: items.isEmpty ? 0 : Double(done) / Double(items.count),
                        caption: "\(done)/\(items.count)"
                    )
                }

                ForEach(items) { item in
                    CardContainer(padding: AppTheme.Spacing.sm) {
                        HStack(spacing: AppTheme.Spacing.sm) {
                            Image(systemName: item.isDone ? "checkmark.circle.fill" : "circle")
                                .foregroundStyle(item.isDone
                                    ? AppTheme.Palette.success
                                    : Color.primary.opacity(0.2))

                            Text(item.title.isEmpty ? "Task" : item.title)
                                .font(AppTheme.Font.callout)
                                .foregroundStyle(AppTheme.Palette.textPrimary)
                                .fixedSize(horizontal: false, vertical: true)

                            Spacer()
                        }
                    }
                }
            }
            .padding(AppTheme.Spacing.md)
        }
    }

    private func load() async {
        await state.load { [api] in
            try await api.thesis.checklist(sessionId: session.id)
        }
    }
}

#Preview {
    NavigationStack {
        ReferenceLibraryView(
            session: ThesisSession(userId: 1, title: "Sample thesis")
        )
        .environment(\.api, .live)
    }
}
