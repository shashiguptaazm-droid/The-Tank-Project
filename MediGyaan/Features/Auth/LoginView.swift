import Foundation
import SwiftUI
import UIKit

/// Email + password sign-in, plus the entry points to registration and
/// password recovery.
///
/// Ports `LoginActivity`, one Kotlin member at a time:
///
/// | Kotlin | Here |
/// |---|---|
/// | `manualLogin()`'s four inline `EditText.error` guards | ``LoginViewModel/validate()`` |
/// | `setFormEnabled(false)` → disables e-mail, password, login and progress | ``LoginViewModel/isSubmitting`` |
/// | `POST api/login.php` (`{"email","password"}`, both `.trim()`-ed) | ``LoginViewModel/submit(api:session:)`` |
/// | `saveUserSession()` → `prefs` `user_id` / `name` / `email` | `SessionStore.signIn` |
/// | `syncFcmToken(userId)` → `POST api/update_fcmv2.php` | `AuthAPI.updatePushToken` |
/// | `registerBtn` / `forgotPasswordBtn` `Intent`s | `RegisterView` / `ForgotPasswordView` |
/// | `activity_login.xml` header + form `MaterialCardView`s | `headerCard` / `formCard` |
///
/// Not ported — the Google half of the Kotlin (`startGoogleSignIn()`,
/// `firebaseAuthWithGoogle()`, `syncUserWithBackend()`) needs the GoogleSignIn
/// and FirebaseAuth SDKs, which this target deliberately does not link. The
/// auto-login branch (`prefs.getInt("user_id", 0) != 0`) is already covered by
/// `SessionStore.restore()`, which runs before `RootView` ever chooses this
/// screen.
struct LoginView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api

    @StateObject private var viewModel = LoginViewModel()
    /// Stands in for `emailField.requestFocus()` / `passwordField.requestFocus()`.
    @FocusState private var focusedField: LoginField?
    @State private var isShowingRegister = false
    @State private var isShowingForgot = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: AppTheme.Spacing.md) {
                    headerCard
                    formCard
                }
                .padding(.horizontal, AppTheme.Spacing.xl)
                .padding(.top, AppTheme.Spacing.lg)
            }
            .scrollDismissesKeyboard(.interactively)
            .screenBackground()
            .navigationDestination(isPresented: $isShowingRegister) {
                RegisterView()
            }
            .navigationDestination(isPresented: $isShowingForgot) {
                ForgotPasswordView()
            }
        }
        .errorAlert(message: $viewModel.errorMessage)
    }

    // MARK: - Sections

    /// `R.id.topAccent` (220dp `?attr/colorPrimary` block) behind
    /// `R.id.headerCard` (`cardCornerRadius="28dp"`, `colorPrimary` fill):
    /// 96dp logo, the `app_name` wordmark at 28sp `sans-serif-black`, and the
    /// "Empowering Competitive Learning" sub-title at 80% alpha.
    private var headerCard: some View {
        ZStack(alignment: .top) {
            AppTheme.Palette.primary
                .frame(maxWidth: .infinity)
                .frame(height: 220)

            VStack(spacing: AppTheme.Spacing.sm) {
                BrandLogo(size: 96)
                    .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))

                Text("MediGyaan")
                    .font(.system(size: 28, weight: .black))
                    .foregroundStyle(AppTheme.Palette.onPrimary)
                    .tracking(0.56)

                Text("Empowering Competitive Learning")
                    .font(AppTheme.Font.callout)
                    .foregroundStyle(AppTheme.Palette.onPrimary.opacity(0.8))
            }
            .padding(.horizontal, AppTheme.Spacing.xxl)
            .padding(.vertical, AppTheme.Spacing.xxl)
            .frame(maxWidth: .infinity)
            .background(
                RoundedRectangle(cornerRadius: 28, style: .continuous)
                    .fill(AppTheme.Palette.primary)
            )
        }
    }

    /// `R.id.formCard`: 28dp radius, `colorSurface` fill, `colorOutline` stroke
    /// and 8dp elevation, holding the welcome copy, both input layouts, the
    /// trailing "Forgot Password?" button, the login button, the progress bar
    /// and the "Don't have an account? / Register" row.
    private var formCard: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.lg) {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
                Text("Welcome Back")
                    .font(AppTheme.Font.title)
                    .foregroundStyle(AppTheme.Palette.textPrimary)

                Text("Login to continue to your dashboard")
                    .font(AppTheme.Font.callout)
                    .foregroundStyle(AppTheme.Palette.textSecondary)
            }

            LabeledField(
                title: "Email Address",
                systemImage: "envelope",
                text: $viewModel.email,
                keyboard: .emailAddress,
                contentType: .username,
                errorText: viewModel.emailError,
                isEnabled: !viewModel.isSubmitting,
                submitLabel: .next,
                focusBinding: $focusedField,
                focusValue: .email,
                onSubmitAction: { focusedField = .password }
            )

            LabeledField(
                title: "Password",
                systemImage: "lock",
                text: $viewModel.password,
                isSecure: true,
                contentType: .password,
                errorText: viewModel.passwordError,
                isEnabled: !viewModel.isSubmitting,
                submitLabel: .done,
                focusBinding: $focusedField,
                focusValue: .password,
                showsRevealToggle: true,
                onSubmitAction: { Task { await submit() } }
            )

            HStack {
                Spacer()
                Button("Forgot Password?") { isShowingForgot = true }
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Palette.textSecondary)
            }

            // Android leaves the button tappable at all times so that an empty
            // form surfaces the inline field errors; only the in-flight request
            // disables it, via `setFormEnabled(false)`.
            PrimaryButton(title: "Login", isLoading: viewModel.isSubmitting) {
                Task { await submit() }
            }

            // `R.id.progressBar` — `layout_gravity="center"`, visible only while
            // the request is in flight.
            if viewModel.isSubmitting {
                ProgressView()
                    .frame(maxWidth: .infinity)
                    .padding(.top, AppTheme.Spacing.xs)
            }

            registerRow
            guestRow
        }
        .padding(AppTheme.Spacing.xxl)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 28, style: .continuous)
                .fill(AppTheme.Palette.surface)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 28, style: .continuous)
                .stroke(AppTheme.Palette.outline, lineWidth: 1)
        )
        .shadow(color: .black.opacity(0.12), radius: 8, y: 4)
    }

    /// The bottom `LinearLayout` — `gravity="center"` "Don't have an account?"
    /// next to the bold `colorPrimary` "Register" text button.
    private var registerRow: some View {
        HStack(spacing: AppTheme.Spacing.xs) {
            Text("Don't have an account?")
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Palette.textSecondary)

            Button("Register") { isShowingRegister = true }
                .font(AppTheme.Font.callout.weight(.bold))
                .foregroundStyle(AppTheme.Palette.primary)
        }
        .frame(maxWidth: .infinity)
    }

    /// iOS-only affordance with no Android counterpart: `SessionStore` seeds a
    /// demo session on a fresh install, so this button just makes that state
    /// reachable on demand.
    private var guestRow: some View {
        Button {
            session.signInAsGuest()
        } label: {
            HStack(spacing: AppTheme.Spacing.xs) {
                Image(systemName: "sparkles")
                Text("Instant Demo Access (Explore as Guest)")
            }
            .font(AppTheme.Font.callout.weight(.semibold))
            .foregroundStyle(AppTheme.Palette.primary)
            .padding(.vertical, AppTheme.Spacing.sm)
        }
        .frame(maxWidth: .infinity)
    }

    // MARK: - Actions

    @MainActor
    private func submit() async {
        focusedField = nil

        if let invalid = viewModel.validate() {
            focusedField = invalid
            return
        }

        await viewModel.submit(api: api, session: session)
    }
}

/// Which `TextInputEditText` to focus, mirroring the Kotlin's
/// `emailField.requestFocus()` / `passwordField.requestFocus()` calls.
enum LoginField: Hashable {
    case email
    case password
}

/// Ports `LoginActivity.manualLogin()`'s guard clauses and network call.
///
/// Validation order and wording are the Kotlin's, verbatim:
/// `email.isEmpty()` → "Please enter your email";
/// `Patterns.EMAIL_ADDRESS` → "Please enter a valid email address";
/// `pass.isEmpty()` → "Please enter your password";
/// `pass.length < 6` → "Password must be at least 6 characters". Android shows
/// these on the offending `EditText` and returns without a request, so the
/// errors live beside the fields rather than in an alert.
@MainActor
final class LoginViewModel: ObservableObject {

    /// Android's `android.util.Patterns.EMAIL_ADDRESS`, verbatim.
    private static let emailPattern =
        "[a-zA-Z0-9+\\._%\\-]{1,256}@[a-zA-Z0-9][a-zA-Z0-9\\-]{0,64}(\\.[a-zA-Z0-9][a-zA-Z0-9\\-]{0,25})+"

    @Published var email = ""
    @Published var password = ""
    /// `EditText.error` for the e-mail field.
    @Published private(set) var emailError: String?
    /// `EditText.error` for the password field.
    @Published private(set) var passwordError: String?
    /// `setFormEnabled`'s inverse: `true` covers both the disabled inputs and
    /// the visible `progressBar`, and doubles as the double-tap guard.
    @Published private(set) var isSubmitting = false
    /// Stands in for Android's `Toast` on the failure branches.
    @Published var errorMessage: String?

    /// `manualLogin()`'s four validation gates. Returns the field that should
    /// take focus, or `nil` when the form is good to submit.
    @discardableResult
    func validate() -> LoginField? {
        emailError = nil
        passwordError = nil

        let trimmedEmail = email.trimmingCharacters(in: .whitespacesAndNewlines)
        let trimmedPassword = password.trimmingCharacters(in: .whitespacesAndNewlines)

        if trimmedEmail.isEmpty {
            emailError = "Please enter your email"
            return .email
        }

        if !Self.isValidEmail(trimmedEmail) {
            emailError = "Please enter a valid email address"
            return .email
        }

        if trimmedPassword.isEmpty {
            passwordError = "Please enter your password"
            return .password
        }

        if trimmedPassword.count < 6 {
            passwordError = "Password must be at least 6 characters"
            return .password
        }

        return nil
    }

    /// `POST https://medigyaan.com/Neurons/api/login.php` with a JSON
    /// `{"email","password"}` body — both values `.trim()`-ed exactly as the
    /// Kotlin does before they leave the activity, so credentials typed on
    /// either platform interoperate.
    func submit(api: MediGyaanAPI, session: SessionStore) async {
        guard !isSubmitting else { return }
        isSubmitting = true
        defer { isSubmitting = false }

        let email = email.trimmingCharacters(in: .whitespacesAndNewlines)
        let password = password.trimmingCharacters(in: .whitespacesAndNewlines)

        RemoteLogger.log(tag: "Auth_Login_Attempt", message: "User attempting login for email: \(email)")

        do {
            let response = try await api.auth.login(email: email, password: password)

            guard response.success, response.userId > 0 else {
                errorMessage = response.message.isEmpty
                    ? "Invalid email or password"
                    : response.message
                RemoteLogger.log(tag: "Auth_Login_Failed", message: "Login failed: \(errorMessage ?? "")")
                return
            }

            RemoteLogger.log(tag: "Auth_Login_Success", message: "User logged in successfully (id: \(response.userId))")

            // `saveUserSession(userId, name, email, mobile, verified)`. The
            // Kotlin persists the address the user typed, not one echoed back
            // by the script, so the stored e-mail is taken from the form.
            session.signIn(
                userId: response.userId,
                name: response.name,
                email: email,
                token: response.token
            )

            // `syncFcmToken(userId)`. Android gives the Volley request a
            // `DefaultRetryPolicy(10_000, 2, 1.5f)`; the shared `HTTPClient`
            // supplies its own timeout instead. Failures stay silent on both
            // platforms — Android only logs, and a stranded push registration
            // must not block navigation.
            if let token = session.pushToken, !token.isEmpty {
                _ = try? await api.auth.updatePushToken(userId: response.userId, token: token)
            }
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
            RemoteLogger.log(tag: "Auth_Login_Error", message: "Login error: \(errorMessage ?? "")")
        }
    }

    /// Ports `Patterns.EMAIL_ADDRESS.matcher(email).matches()`.
    static func isValidEmail(_ value: String) -> Bool {
        value.range(of: emailPattern, options: .regularExpression) != nil
    }
}

/// Reusable labelled text field used across the auth screens.
///
/// Ports `AppTextInputLayout` + `TextInputEditText`: a floating `hint`, a
/// 16dp `boxCornerRadius`, a start icon (`startIconDrawable`), and — for the
/// password variant — `app:endIconMode="password_toggle"`. The trailing
/// toggle is opt-in so the register and recovery screens keep the plain
/// `SecureField` they use today.
struct LabeledField: View {
    let title: String
    var systemImage: String?
    @Binding var text: String
    var isSecure: Bool = false
    var keyboard: UIKeyboardType = .default
    var contentType: UITextContentType?
    /// `EditText.error` — rendered under the box in the theme's error colour.
    var errorText: String? = nil
    /// `setFormEnabled`'s per-field flag.
    var isEnabled: Bool = true
    /// `android:imeOptions` — `actionNext` on e-mail, `actionDone` on password.
    var submitLabel: SubmitLabel = .return
    /// Supplied by the owning screen so `requestFocus()` has somewhere to land.
    var focusBinding: FocusState<LoginField?>.Binding? = nil
    var focusValue: LoginField? = nil
    /// `app:endIconMode="password_toggle"`.
    var showsRevealToggle: Bool = false
    var onSubmitAction: (() -> Void)? = nil

    @State private var isRevealed = false

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

                decorate(input)

                if isSecure && showsRevealToggle {
                    Button {
                        isRevealed.toggle()
                    } label: {
                        Image(systemName: isRevealed ? "eye.slash" : "eye")
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel(isRevealed ? "Hide password" : "Show password")
                }
            }
            .padding(AppTheme.Spacing.md)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.input, style: .continuous)
                    .fill(AppTheme.Palette.cardBackground)
            )
            .overlay(
                RoundedRectangle(cornerRadius: AppTheme.Radius.input, style: .continuous)
                    .stroke(
                        errorText == nil
                            ? Color.primary.opacity(0.10)
                            : AppTheme.Palette.error,
                        lineWidth: 1
                    )
            )

            if let errorText {
                Text(errorText)
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Palette.error)
            }
        }
    }

    @ViewBuilder
    private var input: some View {
        if isSecure {
            secureInput
        } else {
            plainInput
        }
    }

    private var plainInput: some View {
        TextField(title, text: $text)
            .keyboardType(keyboard)
            .textContentType(contentType)
            .autocorrectionDisabled()
            .textInputAutocapitalization(keyboard == .emailAddress ? .never : .sentences)
    }

    private var secureInput: some View {
        Group {
            if isRevealed {
                TextField(title, text: $text)
                    .textContentType(contentType)
                    .autocorrectionDisabled()
                    .textInputAutocapitalization(.never)
            } else {
                SecureField(title, text: $text)
                    .textContentType(contentType)
            }
        }
    }

    /// Applies the modifiers shared by both input variants. Split in two so
    /// `.focused(_:equals:)` is only attached when the screen opted in.
    @ViewBuilder
    private func decorate<Content: View>(_ content: Content) -> some View {
        if let focusBinding {
            content
                .submitLabel(submitLabel)
                .onSubmit { if let onSubmitAction { onSubmitAction() } }
                .disabled(!isEnabled)
                .focused(focusBinding, equals: focusValue)
        } else {
            content
                .submitLabel(submitLabel)
                .onSubmit { if let onSubmitAction { onSubmitAction() } }
                .disabled(!isEnabled)
        }
    }
}

#Preview {
    LoginView()
        .environmentObject(SessionStore())
        .environment(\.api, .live)
}