import SwiftUI

/// Profile tab. Ports `ProfileActivity` and `EditProfileActivity`.
struct ProfileView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api

    @State private var profileState: LoadState<User> = .idle
    @State private var isShowingSettings = false
    @State private var isShowingEdit = false

    private var user: User? {
        profileState.value ?? session.currentUser
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: AppTheme.Spacing.lg) {
                    identityCard
                    statistics
                    menu
                }
                .padding(AppTheme.Spacing.md)
            }
            .screenBackground()
            .navigationTitle("Profile")
            .refreshable { await load() }
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        isShowingSettings = true
                    } label: {
                        Image(systemName: "gearshape.fill")
                    }
                }
            }
            .navigationDestination(isPresented: $isShowingSettings) { SettingsView() }
            .navigationDestination(isPresented: $isShowingEdit) { EditProfileView() }
            .task { await load() }
        }
    }

    // MARK: - Sections

    private var identityCard: some View {
        CardContainer {
            HStack(spacing: AppTheme.Spacing.md) {
                AvatarView(url: user?.avatarURL, name: user?.name ?? "Student", size: 64)

                VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
                    Text(user?.name.isEmpty == false ? user!.name : "Student")
                        .font(AppTheme.Font.headline)
                    Text(user?.email ?? "")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                        .lineLimit(1)

                    HStack(spacing: AppTheme.Spacing.xs) {
                        if let college = user?.college, !college.isEmpty {
                            TagBadge(text: college, tint: AppTheme.Palette.accent)
                        }
                        if let course = user?.course, !course.isEmpty {
                            TagBadge(text: course, tint: AppTheme.Palette.info)
                        }
                    }
                }

                Spacer()
            }

            SecondaryButton(title: "Edit profile", systemImage: "pencil") {
                isShowingEdit = true
            }
            .padding(.top, AppTheme.Spacing.sm)
        }
    }

    private var statistics: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            SectionHeader(title: "Statistics")

            LazyVGrid(
                columns: Array(repeating: GridItem(.flexible(), spacing: AppTheme.Spacing.sm), count: 3),
                spacing: AppTheme.Spacing.sm
            ) {
                StatTile(
                    value: "\(user?.streak ?? 0)",
                    label: "Day streak",
                    systemImage: "flame.fill",
                    tint: AppTheme.Palette.warning
                )
                StatTile(
                    value: "\(user?.overallAttempted ?? 0)",
                    label: "Attempted",
                    systemImage: "checklist",
                    tint: AppTheme.Palette.info
                )
                StatTile(
                    value: String(format: "%.0f%%", (user?.accuracy ?? 0) * 100),
                    label: "Accuracy",
                    systemImage: "target",
                    tint: AppTheme.Palette.success
                )
            }
        }
    }

    private var menu: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            SectionHeader(title: "More")

            CardContainer(padding: 0) {
                VStack(spacing: 0) {
                    NavigationLink { ReferralView() } label: {
                        MenuRow(title: "Refer & earn", systemImage: "gift.fill", tint: AppTheme.Palette.accent)
                    }
                    Divider().padding(.leading, 52)

                    NavigationLink { ThesisHomeView() } label: {
                        MenuRow(title: "Thesis Studio", systemImage: "doc.text.magnifyingglass", tint: AppTheme.Palette.primary)
                    }
                    Divider().padding(.leading, 52)

                    NavigationLink { LeaderboardView() } label: {
                        MenuRow(title: "Leaderboard", systemImage: "trophy.fill", tint: AppTheme.Palette.warning)
                    }
                    Divider().padding(.leading, 52)

                    NavigationLink { HistoryView() } label: {
                        MenuRow(title: "Attempt history", systemImage: "clock.arrow.circlepath", tint: AppTheme.Palette.info)
                    }
                    Divider().padding(.leading, 52)

                    NavigationLink { HelpView() } label: {
                        MenuRow(title: "Help & support", systemImage: "questionmark.circle.fill", tint: AppTheme.Palette.textSecondary)
                    }
                }
            }
        }
    }

    private func load() async {
        let userId = session.userId
        guard userId > 0 else { return }
        await profileState.load { [api] in
            try await api.auth.profile(userId: userId)
        }
        if let refreshed = profileState.value {
            session.updateProfile(refreshed)
        }
    }
}

/// A single tappable row inside a grouped menu.
struct MenuRow: View {
    let title: String
    let systemImage: String
    var tint: Color = AppTheme.Palette.primary

    var body: some View {
        HStack(spacing: AppTheme.Spacing.md) {
            Image(systemName: systemImage)
                .font(.system(size: 16, weight: .semibold))
                .foregroundStyle(tint)
                .frame(width: 24)

            Text(title)
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Palette.textPrimary)

            Spacer()

            Image(systemName: "chevron.right")
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(AppTheme.Palette.textSecondary.opacity(0.6))
        }
        .padding(AppTheme.Spacing.md)
        .contentShape(Rectangle())
    }
}

/// Profile editing.
struct EditProfileView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @Environment(\.dismiss) private var dismiss

    @State private var name = ""
    @State private var phone = ""
    @State private var college = ""
    @State private var course = ""
    @State private var isSaving = false
    @State private var errorMessage: String?
    @State private var didPrefill = false

    var body: some View {
        Form {
            Section("Personal") {
                TextField("Full name", text: $name)
                TextField("Phone", text: $phone)
                    .keyboardType(.phonePad)
            }

            Section("Academic") {
                TextField("College", text: $college)
                TextField("Course", text: $course)
            }
        }
        .navigationTitle("Edit profile")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .confirmationAction) {
                Button("Save") { Task { await save() } }
                    .disabled(isSaving || name.trimmingCharacters(in: .whitespaces).isEmpty)
            }
        }
        .overlay {
            if isSaving {
                ProgressView().padding().background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))
            }
        }
        .errorAlert(message: $errorMessage)
        .onAppear {
            guard !didPrefill, let user = session.currentUser else { return }
            didPrefill = true
            name = user.name
            phone = user.phone
            college = user.college
            course = user.course
        }
    }

    private func save() async {
        guard !isSaving else { return }
        isSaving = true
        defer { isSaving = false }

        do {
            let response = try await api.auth.updateProfile(
                userId: session.userId,
                name: name,
                phone: phone,
                college: college,
                course: course
            )
            guard response.success else {
                errorMessage = response.message.isEmpty ? "Could not save your profile." : response.message
                return
            }
            session.updateProfile(
                User(
                    id: session.userId,
                    name: name,
                    email: session.currentUser?.email ?? "",
                    phone: phone,
                    college: college,
                    course: course
                )
            )
            dismiss()
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

#Preview {
    ProfileView()
        .environmentObject(SessionStore())
        .environment(\.api, .live)
}
