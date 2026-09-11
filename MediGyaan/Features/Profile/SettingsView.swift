import SwiftUI

/// Settings, backed by local preferences the way the Android
/// `SettingsActivity` used `SharedPreferences`.
struct SettingsView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.dismiss) private var dismiss

    @AppStorage("mg.darkMode") private var darkMode = false
    @AppStorage("mg.notifications") private var notifications = true
    @AppStorage("mg.soundEffects") private var soundEffects = true
    @AppStorage("mg.autoSync") private var autoSync = true

    @State private var isConfirmingSignOut = false

    var body: some View {
        Form {
            Section("Account") {
                if let user = session.currentUser {
                    LabeledContent("Name", value: user.name.isEmpty ? "—" : user.name)
                    LabeledContent("Email", value: user.email.isEmpty ? "—" : user.email)
                }
                NavigationLink("Edit profile") { EditProfileView() }
            }

            Section("Appearance") {
                Toggle("Dark mode", isOn: $darkMode)
            }

            Section("Notifications") {
                Toggle("Push notifications", isOn: $notifications)
                Toggle("Sound effects", isOn: $soundEffects)
            }

            Section("Data") {
                Toggle("Auto-sync progress", isOn: $autoSync)
                LabeledContent("Backend", value: "medigyaan.xyz")
                LabeledContent("App version", value: Bundle.main.shortVersion)
            }

            Section("Support") {
                NavigationLink("Help & support") { HelpView() }
                NavigationLink("About MediGyaan") { AboutView() }
            }

            Section {
                Button("Sign out", role: .destructive) {
                    isConfirmingSignOut = true
                }
            }
        }
        .navigationTitle("Settings")
        .navigationBarTitleDisplayMode(.inline)
        .confirmationDialog(
            "Sign out of MediGyaan?",
            isPresented: $isConfirmingSignOut,
            titleVisibility: .visible
        ) {
            Button("Sign out", role: .destructive) {
                session.signOut()
                dismiss()
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("You'll need to sign in again to access your progress.")
        }
    }
}

/// Help and support, porting `HelpActivity` / `SupportActivity`.
struct HelpView: View {

    private let faqs: [(question: String, answer: String)] = [
        ("How is my accuracy calculated?", "Accuracy is the number of correct answers divided by the total questions you have attempted across every test."),
        ("Why is my streak not updating?", "A streak day counts once you answer at least one question. Make sure you're signed in when you practise."),
        ("How do referrals work?", "Share your referral code from the Refer & earn screen. You earn points when someone signs up with it."),
        ("Offline practice?", "Your answers are queued on the device and synced to the server when you reconnect."),
    ]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                ForEach(faqs, id: \.question) { faq in
                    CardContainer {
                        VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
                            Text(faq.question)
                                .font(AppTheme.Font.callout.weight(.semibold))
                            Text(faq.answer)
                                .font(AppTheme.Font.caption)
                                .foregroundStyle(AppTheme.Palette.textSecondary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }

                CardContainer {
                    VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
                        Label("support@medigyaan.xyz", systemImage: "envelope.fill")
                            .font(AppTheme.Font.callout)
                        Label("Response within 24 hours", systemImage: "clock.fill")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                    }
                }
            }
            .padding(AppTheme.Spacing.md)
        }
        .screenBackground()
        .navigationTitle("Help & support")
        .navigationBarTitleDisplayMode(.inline)
    }
}

/// About screen.
struct AboutView: View {
    var body: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.md) {
                Image(systemName: "cross.case.fill")
                    .font(.system(size: 52))
                    .foregroundStyle(AppTheme.Palette.primary)

                Text("MediGyaan")
                    .font(AppTheme.Font.title)
                Text("Version \(Bundle.main.shortVersion) (\(Bundle.main.buildNumber))")
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Palette.textSecondary)

                CardContainer {
                    Text("MediGyaan is a medical exam preparation platform offering topic-wise MCQs, live challenges, rank prediction, and a thesis-writing studio for postgraduate students.")
                        .font(AppTheme.Font.callout)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .padding(AppTheme.Spacing.md)
        }
        .screenBackground()
        .navigationTitle("About")
        .navigationBarTitleDisplayMode(.inline)
    }
}

extension Bundle {
    /// Marketing version, e.g. `4.0`.
    var shortVersion: String {
        object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "—"
    }

    /// Build number.
    var buildNumber: String {
        object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "—"
    }
}

#Preview {
    NavigationStack {
        SettingsView().environmentObject(SessionStore())
    }
}
