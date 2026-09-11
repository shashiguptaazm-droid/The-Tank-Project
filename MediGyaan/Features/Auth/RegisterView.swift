import SwiftUI

/// Account creation. Ports `RegisterActivity`.
struct RegisterView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @Environment(\.dismiss) private var dismiss

    @State private var name = ""
    @State private var email = ""
    @State private var phone = ""
    @State private var college = ""
    @State private var password = ""
    @State private var confirmPassword = ""
    @State private var referralCode = ""
    @State private var isSubmitting = false
    @State private var errorMessage: String?

    private var validationError: String? {
        if name.trimmingCharacters(in: .whitespaces).isEmpty { return "Enter your name" }
        if email.trimmingCharacters(in: .whitespaces).isEmpty { return "Enter your email" }
        if !email.contains("@") { return "Enter a valid email" }
        if password.count < 6 { return "Password must be at least 6 characters" }
        if password != confirmPassword { return "Passwords do not match" }
        return nil
    }

    var body: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.lg) {
                VStack(spacing: AppTheme.Spacing.xs) {
                    Text("Create your account")
                        .font(AppTheme.Font.title)
                    Text("Join thousands of medical aspirants")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }
                .padding(.top, AppTheme.Spacing.md)

                VStack(spacing: AppTheme.Spacing.md) {
                    LabeledField(title: "Full name", systemImage: "person", text: $name, contentType: .name)
                    LabeledField(
                        title: "Email",
                        systemImage: "envelope",
                        text: $email,
                        keyboard: .emailAddress,
                        contentType: .emailAddress
                    )
                    LabeledField(
                        title: "Phone",
                        systemImage: "phone",
                        text: $phone,
                        keyboard: .phonePad,
                        contentType: .telephoneNumber
                    )
                    LabeledField(title: "College", systemImage: "building.columns", text: $college)
                    LabeledField(
                        title: "Password",
                        systemImage: "lock",
                        text: $password,
                        isSecure: true,
                        contentType: .newPassword
                    )
                    LabeledField(
                        title: "Confirm password",
                        systemImage: "lock.rotation",
                        text: $confirmPassword,
                        isSecure: true,
                        contentType: .newPassword
                    )
                    LabeledField(
                        title: "Referral code (optional)",
                        systemImage: "gift",
                        text: $referralCode
                    )
                }

                PrimaryButton(title: "Create Account", isLoading: isSubmitting) {
                    Task { await submit() }
                }
            }
            .padding(AppTheme.Spacing.lg)
        }
        .screenBackground()
        .navigationTitle("Register")
        .navigationBarTitleDisplayMode(.inline)
        .errorAlert(message: $errorMessage)
    }

    @MainActor
    private func submit() async {
        if let validationError {
            errorMessage = validationError
            return
        }
        guard !isSubmitting else { return }
        isSubmitting = true
        defer { isSubmitting = false }

        do {
            let response = try await api.auth.register(
                name: name,
                email: email,
                password: password,
                phone: phone,
                college: college,
                referralCode: referralCode
            )

            guard response.success else {
                errorMessage = response.message.isEmpty
                    ? "Registration failed. Please try again."
                    : response.message
                return
            }

            // The registration script returns no session, so sign in with the
            // credentials just created — matching the Android post-register flow.
            let login = try await api.auth.login(email: email, password: password)
            if login.success {
                session.signIn(
                    userId: login.userId,
                    name: login.name.isEmpty ? name : login.name,
                    email: email,
                    token: login.token
                )
            } else {
                errorMessage = "Account created. Please sign in."
                dismiss()
            }
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

#Preview {
    NavigationStack {
        RegisterView()
            .environmentObject(SessionStore())
            .environment(\.api, .live)
    }
}
