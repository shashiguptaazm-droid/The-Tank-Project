import SwiftUI
import UIKit

/// Email/password sign-in.
///
/// Ports `LoginActivity.manualLogin()`: posts `{"email","password"}` as JSON to
/// `api/login.php`, and on `success` stores the session then syncs the push
/// token exactly as the Android flow does.
struct LoginView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api

    @State private var email = ""
    @State private var password = ""
    @State private var isSubmitting = false
    @State private var errorMessage: String?
    @State private var isShowingRegister = false
    @State private var isShowingForgot = false

    private var canSubmit: Bool {
        !email.trimmingCharacters(in: .whitespaces).isEmpty && !password.isEmpty
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: AppTheme.Spacing.lg) {
                    header
                    credentialsForm
                    actions
                    divider
                    secondaryActions
                }
                .padding(AppTheme.Spacing.lg)
            }
            .screenBackground()
            .navigationDestination(isPresented: $isShowingRegister) {
                RegisterView()
            }
            .navigationDestination(isPresented: $isShowingForgot) {
                ForgotPasswordView()
            }
        }
        .errorAlert(message: $errorMessage)
    }

    // MARK: - Sections

    private var header: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            Image(systemName: "cross.case.fill")
                .font(.system(size: 46))
                .foregroundStyle(AppTheme.Palette.primary)
                .padding(.top, AppTheme.Spacing.xl)
            Text("Welcome back")
                .font(AppTheme.Font.largeTitle)
            Text("Sign in to continue your preparation")
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Palette.textSecondary)
        }
    }

    private var credentialsForm: some View {
        VStack(spacing: AppTheme.Spacing.md) {
            LabeledField(
                title: "Email",
                systemImage: "envelope",
                text: $email,
                keyboard: .emailAddress,
                contentType: .username
            )

            LabeledField(
                title: "Password",
                systemImage: "lock",
                text: $password,
                isSecure: true,
                contentType: .password
            )
        }
    }

    private var actions: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            PrimaryButton(title: "Sign In", isLoading: isSubmitting, isEnabled: canSubmit) {
                Task { await submit() }
            }

            Button("Forgot password?") { isShowingForgot = true }
                .font(AppTheme.Font.callout)
        }
    }

    private var divider: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            Rectangle().fill(Color.primary.opacity(0.12)).frame(height: 1)
            Text("New to MediGyaan?").font(AppTheme.Font.caption)
                .foregroundStyle(AppTheme.Palette.textSecondary)
                .fixedSize()
            Rectangle().fill(Color.primary.opacity(0.12)).frame(height: 1)
        }
    }

    private var secondaryActions: some View {
        SecondaryButton(title: "Create an account", systemImage: "person.badge.plus") {
            isShowingRegister = true
        }
    }

    // MARK: - Networking

    @MainActor
    private func submit() async {
        guard canSubmit, !isSubmitting else { return }
        isSubmitting = true
        defer { isSubmitting = false }

        do {
            let response = try await api.auth.login(
                email: email.trimmingCharacters(in: .whitespaces),
                password: password
            )

            guard response.success else {
                // `api/login.php` mirrors the Android "Invalid credentials" text.
                errorMessage = response.message.isEmpty ? "Invalid credentials" : response.message
                return
            }

            session.signIn(
                userId: response.userId,
                name: response.name,
                email: response.email.isEmpty ? email : response.email,
                token: response.token
            )

            // Mirrors LoginActivity.syncFcmToken(userId) after a successful login.
            if let token = session.pushToken, !token.isEmpty {
                _ = try? await api.auth.updatePushToken(userId: response.userId, token: token)
            }
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

/// Reusable labelled text field used across the auth screens.
struct LabeledField: View {
    let title: String
    var systemImage: String?
    @Binding var text: String
    var isSecure: Bool = false
    var keyboard: UIKeyboardType = .default
    var contentType: UITextContentType?

    var body: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
            Text(title)
                .font(AppTheme.Font.caption.weight(.medium))
                .foregroundStyle(AppTheme.Palette.textSecondary)

            HStack(spacing: AppTheme.Spacing.sm) {
                if let systemImage {
                    Image(systemName: systemImage)
                        .foregroundStyle(AppTheme.Palette.primary)
                        .frame(width: 18)
                }

                if isSecure {
                    SecureField(title, text: $text)
                        .textContentType(contentType)
                } else {
                    TextField(title, text: $text)
                        .keyboardType(keyboard)
                        .textContentType(contentType)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(
                            keyboard == .emailAddress ? .never : .sentences
                        )
                }
            }
            .padding(AppTheme.Spacing.md)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.sm, style: .continuous)
                    .fill(AppTheme.Palette.cardBackground)
            )
            .overlay(
                RoundedRectangle(cornerRadius: AppTheme.Radius.sm, style: .continuous)
                    .stroke(Color.primary.opacity(0.10), lineWidth: 1)
            )
        }
    }
}

#Preview {
    LoginView()
        .environmentObject(SessionStore())
        .environment(\.api, .live)
}
