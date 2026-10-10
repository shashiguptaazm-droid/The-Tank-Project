import SwiftUI

/// Me tab: history, profile, settings, auth state (§3 + §22 Phase-1 subset).
struct MeView: View {
    @Environment(AppModel.self) private var app
    @Environment(ProfileStore.self) private var profile
    @State private var sessionStore: SessionStore?
    @State private var showSignIn = false

    var body: some View {
        NavigationStack {
            List {
                historySection
                profileSection
                settingsSection
                accountSection
            }
            .navigationTitle("Me")
            .onAppear {
                if sessionStore == nil {
                    let container = try? SessionStore.makeContainer()
                    if let container {
                        let store = SessionStore(container: container)
                        store.prime()
                        sessionStore = store
                    }
                }
            }
            .sheet(isPresented: $showSignIn) { SignInSheet() }
        }
    }

    // MARK: History

    @ViewBuilder
    private var historySection: some View {
        Section("History & streaks") {
            if let store = sessionStore {
                LabeledContent("Current streak",
                               value: "\(store.currentStreak) days")
                let sessions = store.fetchAll()
                if sessions.isEmpty {
                    Text("Completed workouts will appear here.")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(sessions.prefix(10)) { session in
                        VStack(alignment: .leading, spacing: 2) {
                            Text(session.workoutName).font(.subheadline)
                            HStack {
                                Text(session.startedAt, style: .date)
                                if let d = session.duration {
                                    Text("· \(Int(d / 60)) min")
                                }
                                Text("· \(session.completedSets) sets")
                            }
                            .font(.caption).foregroundStyle(.secondary)
                        }
                    }
                    NavigationLink("See all") { HistoryDetailView(store: store) }
                }
            }
        }
    }

    @ViewBuilder
    private var profileSection: some View {
        Section("Profile") {
            NavigationLink("Edit profile") { ProfileEditorView() }
            LabeledContent("Level", value: profile.profile.fitnessLevel.displayName)
            if let goal = profile.profile.primaryGoal {
                LabeledContent("Goal", value: goal.displayName)
            }
        }
    }

    @ViewBuilder
    private var settingsSection: some View {
        Section("Accessibility & preferences") {
            NavigationLink("Preferences") { PreferencesEditorView() }
        }
    }

    @ViewBuilder
    private var accountSection: some View {
        Section("Account") {
            if let auth = appSignedIn {
                LabeledContent("Signed in", value: auth)
                Button("Sign out", role: .destructive) {
                    app.authService.signOut()
                }
            } else {
                Button("Sign in / Register") { showSignIn = true }
            }
            NavigationLink("About & safety") { AboutSafetyView() }
            Button("Erase local profile", role: .destructive) {
                profile.eraseProfile()
                app.resetOnboarding()
            }
        }
    }

    private var appSignedIn: String? {
        app.authService.currentUser?.email
    }
}

// MARK: - History detail

struct HistoryDetailView: View {
    let store: SessionStore

    var body: some View {
        List {
            ForEach(store.fetchAll()) { session in
                VStack(alignment: .leading, spacing: 2) {
                    Text(session.workoutName)
                    Text("\(session.startedAt, style: .date) · \(session.completedSets) sets")
                        .font(.caption).foregroundStyle(.secondary)
                }
            }
        }
        .navigationTitle("All sessions")
    }
}

// MARK: - Sign-in sheet

struct SignInSheet: View {
    @Environment(AppModel.self) private var app
    @Environment(\.dismiss) private var dismiss
    @State private var email = ""
    @State private var password = ""
    @State private var name = ""
    @State private var isRegistering = false
    @State private var busy = false

    var body: some View {
        NavigationStack {
            Form {
                if isRegistering {
                    TextField("Name (optional)", text: $name)
                }
                TextField("Email", text: $email)
                    .keyboardType(.emailAddress)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                SecureField("Password", text: $password)

                Button(isRegistering ? "Create account" : "Sign in") {
                    busy = true
                    Task {
                        let success: Bool
                        if isRegistering {
                            success = await app.authService.register(
                                email: email, password: password,
                                name: name.isEmpty ? nil : name)
                        } else {
                            success = await app.authService.login(
                                email: email, password: password)
                        }
                        busy = false
                        if success { dismiss() }
                    }
                }
                .disabled(busy || email.isEmpty || password.count < 8)

                Button(isRegistering ? "I already have an account" : "New here? Create an account") {
                    isRegistering.toggle()
                }

                if let error = app.authService.lastError {
                    Text(error).font(.caption).foregroundStyle(.red)
                }
            }
            .navigationTitle(isRegistering ? "Register" : "Sign in")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
            }
        }
    }
}
