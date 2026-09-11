import SwiftUI

/// Three-step password recovery, porting `ForgotPasswordActivity`.
///
/// 1. `forgot_password_send_otp.php`  — mail the code
/// 2. `forgot_password_verify_otp.php` — check the code
/// 3. `reset_password_app.php`        — set the new password
struct ForgotPasswordView: View {

    @Environment(\.api) private var api
    @Environment(\.dismiss) private var dismiss

    private enum Step {
        case email
        case otp
        case newPassword
    }

    @State private var step: Step = .email
    @State private var email = ""
    @State private var otp = ""
    @State private var newPassword = ""
    @State private var confirmPassword = ""
    @State private var isSubmitting = false
    @State private var errorMessage: String?
    @State private var infoMessage: String?

    var body: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.lg) {
                stepIndicator

                switch step {
                case .email:
                    emailStep
                case .otp:
                    otpStep
                case .newPassword:
                    passwordStep
                }
            }
            .padding(AppTheme.Spacing.lg)
        }
        .screenBackground()
        .navigationTitle("Reset password")
        .navigationBarTitleDisplayMode(.inline)
        .errorAlert(message: $errorMessage)
        .alert("Check your inbox", isPresented: Binding(
            get: { infoMessage != nil },
            set: { if !$0 { infoMessage = nil } }
        )) {
            Button("OK", role: .cancel) { infoMessage = nil }
        } message: {
            Text(infoMessage ?? "")
        }
    }

    // MARK: - Steps

    private var stepIndicator: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            ForEach(0 ..< 3, id: \.self) { index in
                Capsule()
                    .fill(index <= currentStepIndex
                        ? AppTheme.Palette.primary
                        : AppTheme.Palette.primary.opacity(0.18))
                    .frame(height: 5)
            }
        }
        .padding(.top, AppTheme.Spacing.md)
    }

    private var currentStepIndex: Int {
        switch step {
        case .email: return 0
        case .otp: return 1
        case .newPassword: return 2
        }
    }

    private var emailStep: some View {
        VStack(spacing: AppTheme.Spacing.md) {
            Text("Enter the email linked to your account and we'll send a verification code.")
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Palette.textSecondary)
                .multilineTextAlignment(.center)

            LabeledField(
                title: "Email",
                systemImage: "envelope",
                text: $email,
                keyboard: .emailAddress,
                contentType: .emailAddress
            )

            PrimaryButton(title: "Send Code", isLoading: isSubmitting) {
                Task { await sendOtp() }
            }
        }
    }

    private var otpStep: some View {
        VStack(spacing: AppTheme.Spacing.md) {
            Text("Enter the 6-digit code we sent to \(email).")
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Palette.textSecondary)
                .multilineTextAlignment(.center)

            LabeledField(
                title: "Verification code",
                systemImage: "number",
                text: $otp,
                keyboard: .numberPad
            )

            PrimaryButton(title: "Verify Code", isLoading: isSubmitting) {
                Task { await verifyOtp() }
            }

            Button("Use a different email") {
                step = .email
                otp = ""
            }
            .font(AppTheme.Font.caption)
        }
    }

    private var passwordStep: some View {
        VStack(spacing: AppTheme.Spacing.md) {
            Text("Choose a new password for your account.")
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Palette.textSecondary)
                .multilineTextAlignment(.center)

            LabeledField(
                title: "New password",
                systemImage: "lock",
                text: $newPassword,
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

            PrimaryButton(title: "Reset Password", isLoading: isSubmitting) {
                Task { await resetPassword() }
            }
        }
    }

    // MARK: - Networking

    @MainActor
    private func sendOtp() async {
        guard !email.trimmingCharacters(in: .whitespaces).isEmpty else {
            errorMessage = "Enter your email"
            return
        }
        isSubmitting = true
        defer { isSubmitting = false }

        do {
            let response = try await api.auth.forgotPasswordSendOtp(email: email)
            guard response.success else {
                errorMessage = response.message.isEmpty ? "Could not send the code." : response.message
                return
            }
            infoMessage = "We've sent a verification code to \(email)."
            step = .otp
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    @MainActor
    private func verifyOtp() async {
        guard otp.count >= 4 else {
            errorMessage = "Enter the code we sent you"
            return
        }
        isSubmitting = true
        defer { isSubmitting = false }

        do {
            let response = try await api.auth.forgotPasswordVerifyOtp(email: email, code: otp)
            guard response.success else {
                errorMessage = response.message.isEmpty ? "That code is not valid." : response.message
                return
            }
            step = .newPassword
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    @MainActor
    private func resetPassword() async {
        guard newPassword.count >= 6 else {
            errorMessage = "Password must be at least 6 characters"
            return
        }
        guard newPassword == confirmPassword else {
            errorMessage = "Passwords do not match"
            return
        }
        isSubmitting = true
        defer { isSubmitting = false }

        do {
            let response = try await api.auth.resetPassword(
                email: email,
                code: otp,
                newPassword: newPassword
            )
            guard response.success else {
                errorMessage = response.message.isEmpty ? "Could not reset the password." : response.message
                return
            }
            dismiss()
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

#Preview {
    NavigationStack {
        ForgotPasswordView()
            .environment(\.api, .live)
    }
}
