import SwiftUI
import UIKit

/// Password recovery. Ports `ForgotPasswordActivity` and its private
/// `ForgotPasswordScreen` composable — one activity driving a three-step
/// `ForgotStep { MOBILE, OTP, PASSWORD }` state machine over Volley `POST`s to:
///
/// 1. `forgot_password_send_otp.php`   — `{"mobile_no"}`
/// 2. `forgot_password_verify_otp.php` — `{"mobile_no", "otp"}`
/// 3. `reset_password_app.php`         — `{"mobile_no", "password"}`
///
/// Android finishes the activity the moment step 3 succeeds; here the view is
/// popped once the user acknowledges the confirmation, because an alert cannot
/// outlive the view that presents it.
struct ForgotPasswordView: View {

    @Environment(\.api) private var api
    @Environment(\.dismiss) private var dismiss
    @StateObject private var viewModel = ForgotPasswordViewModel()

    var body: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.lg) {
                hero
                stepIndicator

                CardContainer {
                    VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                        stepHeader

                        if let message = viewModel.inlineMessage {
                            Text(message)
                                .font(AppTheme.Font.subheadline.weight(.medium))
                                .foregroundStyle(AppTheme.Palette.error)
                        }

                        stepContent

                        divider
                        backToLogin
                    }
                }
            }
            .padding(AppTheme.Spacing.lg)
        }
        .screenBackground()
        .navigationTitle("Forgot Password")
        .navigationBarTitleDisplayMode(.inline)
        .errorAlert(message: $viewModel.errorMessage)
        .alert(
            "Password updated",
            isPresented: Binding(
                get: { viewModel.notice != nil },
                set: { if !$0 { acknowledgeNotice() } }
            ),
            actions: {
                Button("Back to Login", role: .cancel) { acknowledgeNotice() }
            },
            message: {
                Text(viewModel.notice ?? "")
            }
        )
        .overlay(alignment: .center) {
            if viewModel.isLoading {
                loadingOverlay
            }
        }
        .onAppear {
            RemoteLogger.log(
                tag: "ForgotPassword_Appear",
                message: "User opened Forgot Password recovery screen"
            )
        }
        .onChange(of: viewModel.mobile) { value in
            viewModel.mobile = ForgotPasswordViewModel.digits(value, limit: 10)
        }
        .onChange(of: viewModel.otp) { value in
            viewModel.otp = ForgotPasswordViewModel.digits(value, limit: 6)
        }
    }

    // MARK: - Sections

    /// Ports the `heroColor` `Card` at the top of `ForgotPasswordScreen`.
    private var hero: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            Text("MediGyaan")
                .font(AppTheme.Font.title)
                .foregroundStyle(AppTheme.Palette.onPrimary)
            Text("Reset your password safely")
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Palette.onPrimary.opacity(0.8))
        }
        .frame(maxWidth: .infinity)
        .padding(AppTheme.Spacing.xxl)
        .background(
            RoundedRectangle(
                cornerRadius: AppTheme.Radius.dashboardCard,
                style: .continuous
            )
            .fill(AppTheme.Palette.primary)
        )
    }

    /// iOS-only affordance: Android's three steps share a single card with no
    /// position indicator, so this is an addition rather than a port.
    private var stepIndicator: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            ForEach(0 ..< 3, id: \.self) { index in
                Capsule()
                    .fill(index <= viewModel.stepIndex
                        ? AppTheme.Palette.primary
                        : AppTheme.Palette.primary.opacity(0.18))
                    .frame(height: 5)
            }
        }
    }

    private var stepHeader: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
            Text(viewModel.stepTitle)
                .font(AppTheme.Font.title)
                .foregroundStyle(AppTheme.Palette.textPrimary)
            Text(viewModel.stepSubtitle)
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Palette.textSecondary)
        }
    }

    @ViewBuilder
    private var stepContent: some View {
        switch viewModel.step {
        case .mobile:
            mobileStep
        case .otp:
            otpStep
        case .password:
            passwordStep
        }
    }

    private var mobileStep: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.lg) {
            LabeledField(
                title: "Registered Mobile Number",
                systemImage: "phone",
                text: $viewModel.mobile,
                keyboard: .numberPad,
                contentType: .telephoneNumber
            )

            PrimaryButton(title: "Send OTP", isLoading: viewModel.isLoading) {
                Task { @MainActor in await viewModel.sendOtp(api: api) }
            }
        }
    }

    private var otpStep: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.lg) {
            mobileCaption

            LabeledField(
                title: "Enter OTP",
                systemImage: "number",
                text: $viewModel.otp,
                keyboard: .numberPad
            )

            PrimaryButton(title: "Verify OTP", isLoading: viewModel.isLoading) {
                Task { @MainActor in await viewModel.verifyOtp(api: api) }
            }

            TextActionButton(title: "Change mobile number") {
                viewModel.backToMobile()
            }
            .frame(maxWidth: .infinity)
        }
    }

    private var passwordStep: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.lg) {
            mobileCaption

            LabeledField(
                title: "New Password",
                systemImage: "lock",
                text: $viewModel.password,
                isSecure: true,
                contentType: .newPassword
            )

            LabeledField(
                title: "Confirm Password",
                systemImage: "lock.rotation",
                text: $viewModel.confirmPassword,
                isSecure: true,
                contentType: .newPassword
            )

            PrimaryButton(title: "Update Password", isLoading: viewModel.isLoading) {
                Task { @MainActor in
                    if await viewModel.resetPassword(api: api) {
                        viewModel.notice = "Password updated successfully"
                    }
                }
            }

            TextActionButton(title: "Back to OTP") {
                viewModel.backToOtp()
            }
            .frame(maxWidth: .infinity)
        }
    }

    private var mobileCaption: some View {
        Text(viewModel.mobile)
            .font(AppTheme.Font.subheadline)
            .foregroundStyle(AppTheme.Palette.textPrimary.opacity(0.7))
    }

    private var divider: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            Rectangle().fill(AppTheme.Palette.divider).frame(height: 1)
            Text("OR")
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Palette.textSecondary)
            Rectangle().fill(AppTheme.Palette.divider).frame(height: 1)
        }
    }

    private var backToLogin: some View {
        TextActionButton(title: "Back to Login") { dismiss() }
            .frame(maxWidth: .infinity)
    }

    /// Ports the `if (loading)` full-screen `Surface` overlay with its
    /// `CircularProgressIndicator` and "Please wait…" caption.
    private var loadingOverlay: some View {
        ZStack {
            Color.black.opacity(0.25).ignoresSafeArea()
            HStack(spacing: AppTheme.Spacing.md) {
                ProgressView().tint(AppTheme.Palette.primary)
                Text("Please wait…")
                    .font(AppTheme.Font.callout)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
            }
            .padding(.horizontal, AppTheme.Spacing.xl)
            .padding(.vertical, AppTheme.Spacing.lg)
            .background(
                RoundedRectangle(
                    cornerRadius: AppTheme.Radius.card,
                    style: .continuous
                )
                .fill(AppTheme.Palette.surface)
            )
            .shadow(color: .black.opacity(0.18), radius: 6, y: 3)
        }
    }

    private func acknowledgeNotice() {
        viewModel.notice = nil
        dismiss()
    }
}

/// State and validation behind ``ForgotPasswordView``, porting the
/// `remember { mutableStateOf(...) }` block and the three private Volley helpers
/// (`sendForgotOtp`, `verifyForgotOtp`, `resetPassword`) of
/// `ForgotPasswordActivity`.
///
/// The Android helpers POST a **JSON** body carrying `mobile_no`; the shared
/// `AuthAPI` currently exposes these three scripts with an `email:` label and a
/// form-encoded body. The identifier is therefore passed positionally and the
/// field-name/encoding gap is tracked as a blocker for the networking owner.
@MainActor
final class ForgotPasswordViewModel: ObservableObject {

    /// Ports the private `ForgotStep` enum.
    enum Step {
        case mobile
        case otp
        case password
    }

    @Published var step: Step = .mobile
    @Published var mobile = ""
    @Published var otp = ""
    @Published var password = ""
    @Published var confirmPassword = ""

    /// The Android `message` state, rendered as red inline copy inside the card.
    @Published private(set) var inlineMessage: String?
    /// Every `Toast.makeText` the Android screen fires for a failed attempt.
    @Published var errorMessage: String?
    /// Confirmation shown once, before the view pops back to login.
    @Published var notice: String?

    @Published private(set) var state: LoadState<Acknowledgment> = .idle

    var isLoading: Bool { state.isLoading }

    var stepIndex: Int {
        switch step {
        case .mobile: return 0
        case .otp: return 1
        case .password: return 2
        }
    }

    var stepTitle: String {
        switch step {
        case .mobile: return "Forgot Password"
        case .otp: return "Verify OTP"
        case .password: return "Set New Password"
        }
    }

    var stepSubtitle: String {
        switch step {
        case .mobile: return "Enter your registered mobile number"
        case .otp: return "Enter the OTP sent to your mobile number"
        case .password: return "Create a new password for your account"
        }
    }

    // MARK: - Step transitions

    /// Ports the "Change mobile number" `TextButton` on `ForgotStep.OTP`.
    func backToMobile() {
        state = .idle
        otp = ""
        step = .mobile
        inlineMessage = nil
    }

    /// Ports the "Back to OTP" `TextButton` on `ForgotStep.PASSWORD`.
    func backToOtp() {
        state = .idle
        password = ""
        confirmPassword = ""
        step = .otp
        inlineMessage = nil
    }

    // MARK: - Networking

    /// Ports `ForgotPasswordActivity.sendForgotOtp()`.
    func sendOtp(api: MediGyaanAPI) async {
        guard !isLoading else { return }
        inlineMessage = nil
        errorMessage = nil

        let identifier = mobile.trimmingCharacters(in: .whitespaces)
        guard isValidIndianMobile(identifier) else {
            errorMessage = "Enter valid 10-digit Indian mobile number"
            return
        }

        state = await LoadState.result {
            try await api.auth.forgotPasswordSendOtp(email: identifier)
        }
        apply(
            state,
            blankSuccess: "OTP sent successfully",
            failure: "OTP could not be sent",
            onSuccess: { self.step = .otp }
        )
    }

    /// Ports `ForgotPasswordActivity.verifyForgotOtp()`.
    func verifyOtp(api: MediGyaanAPI) async {
        guard !isLoading else { return }
        inlineMessage = nil
        errorMessage = nil

        let code = otp.trimmingCharacters(in: .whitespaces)
        guard code.count == 6 else {
            errorMessage = "Enter a valid 6-digit OTP"
            return
        }

        state = await LoadState.result {
            try await api.auth.forgotPasswordVerifyOtp(email: mobile, code: code)
        }
        apply(
            state,
            blankSuccess: "OTP verified successfully",
            failure: "OTP verification failed",
            onSuccess: { self.step = .password }
        )
    }

    /// Ports `ForgotPasswordActivity.resetPassword()`. Returns `true` when the
    /// backend accepted the new password, mirroring the Android
    /// `activity.finish()` branch.
    @discardableResult
    func resetPassword(api: MediGyaanAPI) async -> Bool {
        guard !isLoading else { return false }
        inlineMessage = nil
        errorMessage = nil

        guard password.count >= 6 else {
            errorMessage = "Password must be at least 6 characters"
            return false
        }
        guard password == confirmPassword else {
            errorMessage = "Passwords do not match"
            return false
        }

        state = await LoadState.result {
            try await api.auth.resetPassword(
                email: mobile,
                code: otp,
                newPassword: password
            )
        }

        var succeeded = false
        apply(
            state,
            blankSuccess: "Password updated successfully",
            failure: "Password update failed",
            onSuccess: { succeeded = true }
        )
        return succeeded
    }

    // MARK: - Helpers

    /// Ports the Kotlin `^[6-9]\\d{9}$` guard plus its `length != 10` check.
    nonisolated static func isValidIndianMobile(_ value: String) -> Bool {
        guard value.count == 10 else { return false }
        guard value.allSatisfy({ $0.isASCII && $0.isNumber }) else { return false }
        guard let first = value.first else { return false }
        return first == "6" || first == "7" || first == "8" || first == "9"
    }

    /// Ports the `it.filter { c -> c.isDigit() }.take(n)` `onValueChange` in
    /// `ForgotPasswordScreen`.
    nonisolated static func digits(_ value: String, limit: Int) -> String {
        String(value.filter { $0.isNumber }.prefix(limit))
    }

    private func fail(_ message: String) {
        inlineMessage = message
        errorMessage = message
    }

    private func apply(
        _ result: LoadState<Acknowledgment>,
        blankSuccess: String,
        failure: String,
        onSuccess: () -> Void
    ) {
        switch result {
        case .loaded(let acknowledgment):
            guard acknowledgment.success else {
                fail(acknowledgment.message.isEmpty ? failure : acknowledgment.message)
                return
            }
            inlineMessage = acknowledgment.message.isEmpty ? blankSuccess : acknowledgment.message
            onSuccess()
        case .failed(let message):
            fail(message)
        case .idle, .loading:
            break
        }
    }
}

#Preview {
    NavigationStack {
        ForgotPasswordView()
            .environment(\.api, .live)
    }
}