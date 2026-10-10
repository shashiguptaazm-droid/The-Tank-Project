import Foundation
import SwiftUI
import UIKit

/// Account creation. Ports `RegisterActivity` / `RegisterScreen`.
///
/// Two-step signup over the same PHP scripts the Android activity calls:
///
/// | `RegisterActivity.kt` | Here |
/// |---|---|
/// | `RegisterStep` enum (`FORM` / `OTP`) | ``RegisterStep`` |
/// | `normalizeCollegeName()` + `loadColleges()` (assets `predictor_data_new.json`, `colleges.json`) | ``RegisterCollegeDirectory`` |
/// | `SearchableCollegeField` (3-char gate, 20 rows) | ``RegisterCollegeField`` |
/// | `YearSelectionField` (`Calendar.YEAR downTo 2000`) | ``RegisterPickerField`` + ``RegisterYears`` |
/// | `StateDropdownField` (`INDIAN_STATES`) | ``RegisterPickerField`` + ``registerIndianStates`` |
/// | `RegisterTextField` | `LabeledField` |
/// | the nine validation `when` branches | ``RegisterViewModel/validationFailure()`` |
/// | `sendOtp()` → `POST Neurons/send_otp3.php` | `AuthAPI.sendOtp` |
/// | `verifyOtp()` → `POST Neurons/verify_otp12.php` | `AuthAPI.verifyOtp` |
/// | `saveUserSession()` → prefs `user_id` / `name` / `email` | `SessionStore.signIn` |
/// | `applyReferralCode()` → `POST Neurons/api/referral_api.php` | `ReferralAPI.apply` |
/// | `syncFcmToken()` → `POST Neurons/api/update_fcmv2.php` | `AuthAPI.updatePushToken` |
/// | `onDashboard` → `DashboardActivity` + `finishAffinity()` | `SessionStore.signIn` → the `RootView` swap |
///
/// Two Android behaviours are deliberately not reproduced: the "Continue with
/// Google" button only raises a toast on the Kotlin side (there is no
/// `GoogleSignIn` dependency to wire it to), and `RegisterScreen`'s transient
/// `Toast`s become `errorAlert(message:)` presentations, which is how every
/// other ported screen surfaces the same failure.
struct RegisterView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @Environment(\.dismiss) private var dismiss

    @StateObject private var viewModel = RegisterViewModel()

    var body: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.xl) {
                heroCard
                formCard
            }
            .padding(AppTheme.Spacing.xl)
        }
        .scrollDismissesKeyboard(.interactively)
        .screenBackground()
        .navigationTitle("Register")
        .navigationBarTitleDisplayMode(.inline)
        .errorAlert(message: $viewModel.errorMessage)
        .overlay { loadingOverlay }
        .onAppear {
            RemoteLogger.log(tag: "RegisterView_Open", message: "User navigated to Registration screen")
        }
    }

    // MARK: - Sections

    /// The blue brand block: 96dp logo, the "MediGyaan" wordmark, and the
    /// "Empowering Competitive Learning" sub-title at 80% alpha.
    private var heroCard: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            BrandLogo(size: 96)
                .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))

            Text("MediGyaan")
                .font(AppTheme.Font.title)
                .foregroundStyle(AppTheme.Palette.onPrimary)

            Text("Empowering Competitive Learning")
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Palette.onPrimary.opacity(0.8))
        }
        .padding(AppTheme.Spacing.xxl)
        .frame(maxWidth: .infinity)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.dashboardCard, style: .continuous)
                .fill(AppTheme.Palette.primary)
        )
    }

    /// The white form card whose heading flips between "Create Account" and
    /// "Verify OTP", exactly as the Kotlin swaps `RegisterStep`.
    private var formCard: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.lg) {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
                Text(viewModel.step == .form ? "Create Account" : "Verify OTP")
                    .font(AppTheme.Font.title)
                    .foregroundStyle(AppTheme.Palette.textPrimary)

                Text(viewModel.step == .form
                     ? "Register to continue to your dashboard"
                     : "Enter the 6-digit OTP sent to your mobile number")
                    .font(AppTheme.Font.callout)
                    .foregroundStyle(AppTheme.Palette.textSecondary)
            }

            if let notice = viewModel.statusMessage {
                Text(notice)
                    .font(AppTheme.Font.subheadline.weight(.medium))
                    .foregroundStyle(AppTheme.Palette.primary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            if viewModel.step == .form {
                formFields
            } else {
                otpFields
            }

            orDivider

            SecondaryButton(title: "Continue with Google", systemImage: "globe") {
                viewModel.notice("Google registration can be added with your Google backend flow")
            }

            loginFooter
        }
        .padding(AppTheme.Spacing.xxl)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.dashboardCard, style: .continuous)
                .fill(AppTheme.Palette.cardBackground)
        )
        .overlay(
            RoundedRectangle(cornerRadius: AppTheme.Radius.dashboardCard, style: .continuous)
                .stroke(AppTheme.Palette.outline, lineWidth: 1)
        )
        .shadow(color: .black.opacity(0.08), radius: AppTheme.Elevation.dashboardCard, y: 4)
    }

    private var formFields: some View {
        VStack(spacing: AppTheme.Spacing.lg) {
            LabeledField(title: "Full Name", systemImage: "person", text: $viewModel.name, contentType: .name)

            LabeledField(
                title: "Email Address",
                systemImage: "envelope",
                text: $viewModel.email,
                keyboard: .emailAddress,
                contentType: .emailAddress
            )

            // `mobile = it.filter { c -> c.isDigit() }.take(10)` — the Kotlin
            // strips everything that is not a digit before truncating.
            LabeledField(
                title: "Mobile / WhatsApp Number",
                systemImage: "phone",
                text: viewModel.mobileBinding,
                keyboard: .phonePad,
                contentType: .telephoneNumber
            )

            RegisterCollegeField(
                text: $viewModel.college,
                options: viewModel.collegeSuggestions
            )

            RegisterPickerField(
                title: "Batch Year",
                systemImage: "calendar",
                placeholder: "Batch Year",
                options: RegisterYears.all,
                selection: $viewModel.batchYear
            )

            RegisterPickerField(
                title: "Passing Year",
                systemImage: "calendar.badge.clock",
                placeholder: "Passing Year",
                options: RegisterYears.all,
                selection: $viewModel.passingYear
            )

            RegisterPickerField(
                title: "State",
                systemImage: "map",
                placeholder: "State",
                options: registerIndianStates,
                selection: $viewModel.selectedState
            )

            LabeledField(
                title: "Password",
                systemImage: "lock",
                text: $viewModel.password,
                isSecure: true,
                contentType: .newPassword
            )

            LabeledField(
                title: "Repeat Password",
                systemImage: "lock.rotation",
                text: $viewModel.confirmPassword,
                isSecure: true,
                contentType: .newPassword
            )

            LabeledField(
                title: "Referral Code (Optional)",
                systemImage: "gift",
                text: viewModel.referralCodeBinding
            )

            PrimaryButton(title: "Send OTP", isLoading: viewModel.isLoading) {
                Task { await viewModel.sendOtp(api: api) }
            }
        }
    }

    private var otpFields: some View {
        VStack(spacing: AppTheme.Spacing.lg) {
            Text("\(viewModel.name) • \(viewModel.mobile)")
                .font(AppTheme.Font.subheadline)
                .foregroundStyle(AppTheme.Palette.textSecondary)

            LabeledField(
                title: "Enter OTP",
                systemImage: "number",
                text: viewModel.otpBinding,
                keyboard: .numberPad
            )

            PrimaryButton(title: "Verify OTP", isLoading: viewModel.isLoading) {
                Task {
                    if await viewModel.verifyOtp(api: api, session: session) {
                        dismiss()
                    }
                }
            }

            Button("Edit registration details") {
                viewModel.editDetails()
            }
            .font(AppTheme.Font.callout.weight(.semibold))
            .foregroundStyle(AppTheme.Palette.primary)
        }
        .frame(maxWidth: .infinity)
    }

    private var orDivider: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            Rectangle()
                .fill(AppTheme.Palette.divider)
                .frame(height: 1)
            Text("OR")
                .font(AppTheme.Font.subheadline.weight(.medium))
                .foregroundStyle(AppTheme.Palette.textSecondary)
                .fixedSize()
            Rectangle()
                .fill(AppTheme.Palette.divider)
                .frame(height: 1)
        }
    }

    private var loginFooter: some View {
        HStack(spacing: AppTheme.Spacing.xs) {
            Text("Already have an account?")
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Palette.textSecondary)
            TextActionButton(title: "Login") { dismiss() }
        }
        .frame(maxWidth: .infinity)
    }

    /// `if (loading) { Box { Surface { CircularProgressIndicator … } } }` — the
    /// Compose activity dims nothing and floats a "Please wait" card over the
    /// whole form while a request is in flight.
    @ViewBuilder
    private var loadingOverlay: some View {
        if viewModel.isLoading {
            ZStack {
                Color.black.opacity(0.20)
                    .ignoresSafeArea()

                HStack(spacing: AppTheme.Spacing.md) {
                    ProgressView()
                    Text("Please wait…")
                        .font(AppTheme.Font.callout)
                        .foregroundStyle(AppTheme.Palette.textPrimary)
                }
                .padding(AppTheme.Spacing.xl)
                .background(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.materialCard, style: .continuous)
                        .fill(AppTheme.Palette.surface)
                )
                .shadow(color: .black.opacity(0.12), radius: AppTheme.Elevation.dashboardCard, y: 2)
            }
        }
    }
}

// MARK: - Step

/// Ports the Kotlin `private enum class RegisterStep { FORM, OTP }`.
private enum RegisterStep {
    case form
    case otp
}

// MARK: - College directory

/// Ports `RegisterActivity.loadColleges(context)` and `normalizeCollegeName()`.
///
/// The two bundled JSON exports — `predictor_data_new.json` (the `type:"table"`
/// rows' `college_name` column) and `colleges.json` (the `name` column) — are
/// unioned into one de-duplicated, alphabetically sorted list, exactly as the
/// Kotlin's `mutableSetOf` does. Either file failing to parse is non-fatal,
/// matching the per-file `try`/`catch (e: Exception)`.
private enum RegisterCollegeDirectory {

    private static let index: [String] = load()

    /// Ports `normalizeCollegeName(value)`: `\n` and `\r` become spaces, runs of
    /// whitespace collapse to a single space, and the result is trimmed.
    static func normalize(_ value: String) -> String {
        value
            .replacingOccurrences(of: "\n", with: " ")
            .replacingOccurrences(of: "\r", with: " ")
            .split(whereSeparator: { $0 == " " || $0 == "\t" || $0 == "\u{0B}" || $0 == "\u{0C}" })
            .joined(separator: " ")
    }

    /// Ports `SearchableCollegeField`'s `filteredColleges`: nothing is offered
    /// below three characters; a college matches on a case-insensitive substring
    /// or on any of its words starting with the query; at most 20 rows.
    static func matches(query: String) -> [String] {
        let needle = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard needle.count >= 3 else { return [] }
        return Array(index.filter { college in
            if college.range(of: needle, options: [.caseInsensitive]) != nil { return true }
            return college
                .split(separator: " ")
                .contains { $0.hasPrefix(needle, options: [.caseInsensitive]) }
        }.prefix(20))
    }

    private static func load() -> [String] {
        var names = Set<String>()

        if let exported = jsonArray(named: "predictor_data_new") {
            for case let entry as [String: Any] in exported {
                guard (entry["type"] as? String) == "table",
                      let rows = entry["data"] as? [[String: Any]]
                else { continue }
                for row in rows {
                    insert(&names, row["college_name"] as? String)
                }
            }
        }

        if let curated = jsonArray(named: "colleges") {
            for case let entry as [String: Any] in curated {
                insert(&names, entry["name"] as? String)
            }
        }

        return names.filter { !$0.isEmpty }.sorted()
    }

    private static func insert(_ names: inout Set<String>, _ raw: String?) {
        guard let raw else { return }
        let name = normalize(raw.trimmingCharacters(in: .whitespacesAndNewlines))
        guard !name.isEmpty else { return }
        names.insert(name)
    }

    private static func jsonArray(named name: String) -> [Any]? {
        guard let url = Bundle.main.url(forResource: name, withExtension: "json")
            ?? Bundle.main.url(forResource: name, withExtension: "json", subdirectory: "Data"),
              let data = try? Data(contentsOf: url)
        else { return nil }
        return try? JSONSerialization.jsonObject(with: data) as? [Any]
    }
}

// MARK: - Fields

/// Ports `SearchableCollegeField`: an editable box plus the matching colleges
/// listed underneath once three characters have been typed.
private struct RegisterCollegeField: View {

    @Binding var text: String
    let options: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
            LabeledField(title: "College Name", systemImage: "building.columns", text: $text)

            if !options.isEmpty {
                ScrollView {
                    VStack(spacing: 0) {
                        ForEach(options, id: \.self) { college in
                            Button {
                                text = college
                            } label: {
                                Text(college)
                                    .font(AppTheme.Font.subheadline)
                                    .foregroundStyle(AppTheme.Palette.textPrimary)
                                    .multilineTextAlignment(.leading)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .padding(.vertical, AppTheme.Spacing.sm)
                                    .padding(.horizontal, AppTheme.Spacing.md)
                                    .contentShape(Rectangle())
                            }
                            .buttonStyle(.plain)

                            Divider()
                        }
                    }
                    .padding(.vertical, AppTheme.Spacing.xs)
                }
                .frame(maxHeight: 200)
                .background(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.input, style: .continuous)
                        .fill(AppTheme.Palette.cardBackground)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.input, style: .continuous)
                        .stroke(AppTheme.Palette.outline, lineWidth: 1)
                )
            }
        }
    }
}

/// Ports `YearSelectionField` and `StateDropdownField`.
///
/// Both Kotlin composables are read-only `ExposedDropdownMenuBox`es: a
/// `TrailingIcon` chevron, the label as placeholder, and an option list that
/// writes the picked string straight back into the parent's state.
private struct RegisterPickerField: View {

    let title: String
    let systemImage: String
    let placeholder: String
    let options: [String]
    @Binding var selection: String

    var body: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
            Text(title)
                .font(AppTheme.Font.caption.weight(.medium))
                .foregroundStyle(AppTheme.Palette.textSecondary)

            Menu {
                ForEach(options, id: \.self) { option in
                    Button(option) { selection = option }
                }
            } label: {
                HStack(spacing: AppTheme.Spacing.sm) {
                    Image(systemName: systemImage)
                        .foregroundStyle(AppTheme.Palette.primary)
                        .frame(width: 18)

                    Text(selection.isEmpty ? placeholder : selection)
                        .foregroundStyle(selection.isEmpty
                            ? AppTheme.Palette.textSecondary
                            : AppTheme.Palette.textPrimary)

                    Spacer(minLength: 0)

                    Image(systemName: "chevron.down")
                        .font(AppTheme.Font.caption2)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }
                .padding(AppTheme.Spacing.md)
                .background(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.input, style: .continuous)
                        .fill(AppTheme.Palette.cardBackground)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.input, style: .continuous)
                        .stroke(AppTheme.Palette.outline, lineWidth: 1)
                )
            }
            .buttonStyle(.plain)
        }
    }
}

// MARK: - View model

/// Ports the `remember { mutableStateOf(...) }` state of `RegisterScreen` plus
/// its `sendOtp` / `verifyOtp` / `applyReferralCode` / `saveUserSession` /
/// `syncFcmToken` helpers.
@MainActor
private final class RegisterViewModel: ObservableObject {

    /// Android's `SharedPreferences("MY_APP")` key for a referral code picked in
    /// `ReferralActivity` but not yet redeemed here.
    static let pendingReferralKey = "pending_referral_code"

    @Published var name = ""
    @Published var email = ""
    @Published var mobile = ""
    @Published var college = ""
    @Published var batchYear = ""
    @Published var passingYear = ""
    @Published var selectedState = ""
    @Published var password = ""
    @Published var confirmPassword = ""
    @Published private(set) var referralCode: String
    @Published private(set) var otp = ""

    @Published private(set) var step: RegisterStep = .form
    /// Stands in for the Kotlin's inline `message` Text and its `Toast`s; the
    /// failures are raised through ``errorMessage`` instead.
    @Published private(set) var statusMessage: String?
    @Published var errorMessage: String?

    @Published private(set) var otpRequest: LoadState<Acknowledgment> = .idle
    @Published private(set) var verification: LoadState<Int> = .idle

    /// `enabled = !loading` on both buttons, plus the double-submit guard.
    var isLoading: Bool { otpRequest.isLoading || verification.isLoading }

    var collegeSuggestions: [String] {
        RegisterCollegeDirectory.matches(query: college)
    }

    init() {
        referralCode = UserDefaults.standard.string(forKey: Self.pendingReferralKey) ?? ""
    }

    // MARK: - Bindings

    /// `mobile = it.filter { c -> c.isDigit() }.take(10)`
    var mobileBinding: Binding<String> {
        Binding(
            get: { self.mobile },
            set: { self.mobile = Self.digitsOnly($0, limit: 10) }
        )
    }

    /// `otp = it.filter { c -> c.isDigit() }.take(6)`
    var otpBinding: Binding<String> {
        Binding(
            get: { self.otp },
            set: { self.otp = Self.digitsOnly($0, limit: 6) }
        )
    }

    /// `referralCode = it.uppercase().replace("[^A-Z0-9]", "").take(32)` plus the
    /// `prefs.edit().putString("pending_referral_code", …).apply()` that runs
    /// on every keystroke.
    var referralCodeBinding: Binding<String> {
        Binding(
            get: { self.referralCode },
            set: { newValue in
                let cleaned = newValue.uppercased().filter { $0.isASCII && ($0.isLetter || $0.isNumber) }
                self.referralCode = String(cleaned.prefix(32))
                UserDefaults.standard.set(self.referralCode, forKey: Self.pendingReferralKey)
            }
        )
    }

    /// Stands in for the `Toast` on Android.
    func notice(_ text: String) {
        statusMessage = text
    }

    /// The `TextButton` that returns to `RegisterStep.FORM`.
    func editDetails() {
        otpRequest = .idle
        verification = .idle
        otp = ""
        step = .form
        statusMessage = nil
    }

    // MARK: - Validation

    /// Ports the nine `when` branches guarding `Send OTP`, in the Kotlin's order
    /// and with its wording verbatim.
    func validationFailure() -> String? {
        let name = name.registerTrimmed
        let email = email.registerTrimmed

        if name.isEmpty { return "Enter name" }
        if !Self.isValidEmail(email) { return "Invalid email" }
        if mobile.count != 10 || !Self.isValidIndianMobile(mobile) {
            return "Invalid 10-digit Indian mobile number"
        }
        if college.registerTrimmed.isEmpty { return "Enter college name" }
        if batchYear.registerTrimmed.count != 4 { return "Select valid batch year" }
        if passingYear.registerTrimmed.count != 4 { return "Select passing year" }
        if selectedState.registerTrimmed.isEmpty { return "Select your state" }
        if password.count < 6 { return "Password must be at least 6 characters" }
        if password != confirmPassword { return "Passwords do not match" }
        return nil
    }

    /// Ports `Patterns.EMAIL_ADDRESS.matcher(email).matches()`.
    private static let emailPattern =
        "[a-zA-Z0-9+\\._%\\-]{1,256}@[a-zA-Z0-9()]{1,10}(\\.[a-zA-Z0-9()]{1,10}){0,2}"

    static func isValidEmail(_ value: String) -> Bool {
        value.range(of: emailPattern, options: .regularExpression) != nil
    }

    /// Ports `mobile.matches(Regex("^[6-9]\\d{9}$"))`.
    static func isValidIndianMobile(_ value: String) -> Bool {
        guard value.count == 10, let first = value.first else { return false }
        return first >= "6" && first <= "9" && value.allSatisfy(\.isNumber)
    }

    private static func digitsOnly(_ value: String, limit: Int) -> String {
        String(value.filter(\.isNumber).prefix(limit))
    }

    // MARK: - Networking

    /// Ports the `Send OTP` button: validate, then `POST Neurons/send_otp3.php`
    /// and advance to ``RegisterStep/otp``.
    func sendOtp(api: MediGyaanAPI) async {
        guard !isLoading else { return }
        errorMessage = nil
        statusMessage = nil

        if let failure = validationFailure() {
            errorMessage = failure
            return
        }

        otpRequest = await LoadState.result {
            try await api.auth.sendOtp(phone: mobile, email: email.registerTrimmed)
        }

        guard let response = otpRequest.value else {
            errorMessage = otpRequest.errorMessage ?? "OTP could not be sent"
            return
        }

        guard response.success else {
            let message = response.message.isEmpty ? "OTP could not be sent" : response.message
            otpRequest = .failed(message)
            errorMessage = message
            return
        }

        statusMessage = response.message.isEmpty ? "OTP sent successfully" : response.message
        step = .otp
    }

    /// Ports the `Verify OTP` button: check the code, then the whole
    /// `verifyOtp(...) { userId, userName, userEmail -> … }` success chain.
    /// Returns `true` when the session is live and the screen should be
    /// dismissed, which is iOS's stand-in for `onDashboard()`'s
    /// `finishAffinity()`.
    @discardableResult
    func verifyOtp(api: MediGyaanAPI, session: SessionStore) async -> Bool {
        guard !isLoading else { return false }
        errorMessage = nil
        statusMessage = nil

        guard otp.count == 6 else {
            errorMessage = "Enter a valid 6-digit OTP"
            return false
        }

        verification = .loading

        do {
            let response = try await api.auth.verifyOtp(
                phone: mobile,
                email: email.registerTrimmed,
                code: otp
            )
            guard response.success else {
                throw APIError.server(
                    response.message.isEmpty ? "OTP verification failed" : response.message
                )
            }

            let userId = try await resolveUserId(api: api)
            verification = .loaded(userId)
            await completeRegistration(userId: userId, api: api, session: session)
            return true
        } catch {
            let message = LoadState<Never>.message(for: error)
            verification = .failed(message)
            errorMessage = message
            return false
        }
    }

    /// The Kotlin reads `user_id` straight off the `verify_otp12.php` response;
    /// `AuthAPI.verifyOtp` only exposes the envelope, so the id is resolved by
    /// signing in with the credentials the user just supplied.
    ///
    /// `AuthAPI.register` (`google-callback.php`) is attempted first because it
    /// is the only iOS client that carries the password and the college — the
    /// OTP helpers only take phone and e-mail — so without it the account has
    /// no password to sign in with. Its failure is not fatal: the account may
    /// already exist, which is the duplicate-email case the Kotlin surfaces from
    /// `send_otp3.php`.
    private func resolveUserId(api: MediGyaanAPI) async throws -> Int {
        _ = try? await api.auth.register(
            name: name.registerTrimmed,
            email: email.registerTrimmed,
            password: password,
            phone: mobile,
            college: college.registerTrimmed,
            referralCode: referralCode.registerTrimmed
        )

        let login = try await api.auth.login(
            email: email.registerTrimmed,
            password: password
        )
        guard login.success, login.userId > 0 else {
            throw APIError.server("Account created. Please sign in.")
        }
        return login.userId
    }

    /// Ports the Kotlin's success chain, in order: `saveUserSession()`,
    /// `applyReferralCode()`, `syncFcmToken()`.
    private func completeRegistration(
        userId: Int,
        api: MediGyaanAPI,
        session: SessionStore
    ) async {
        session.signIn(userId: userId, name: name.registerTrimmed, email: email.registerTrimmed)

        let code = referralCode.registerTrimmed
        if !code.isEmpty, (try? await api.referral.apply(code: code, userId: userId)) != nil {
            UserDefaults.standard.removeObject(forKey: Self.pendingReferralKey)
        }

        if let token = session.pushToken, !token.isEmpty {
            _ = try? await api.auth.updatePushToken(userId: userId, token: token)
        }
    }
}

// MARK: - Data

/// Ports the year list `YearSelectionField` builds with
/// `(currentYear downTo 2000)` off `Calendar.getInstance().get(Calendar.YEAR)`,
/// shared by the "Batch Year" and "Passing Year" pickers.
private enum RegisterYears {
    static var all: [String] {
        let current = Calendar.current.component(.year, from: Date())
        guard current >= 2000 else { return ["2000"] }
        return (2000 ... current).reversed().map { String($0) }
    }
}

/// Ports the Kotlin `private val INDIAN_STATES`, verbatim.
private let registerIndianStates: [String] = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi", "Puducherry"
]

// MARK: - Support

private extension String {
    /// `String.trim()` — Android trims every character at or below U+0020.
    var registerTrimmed: String {
        trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

#Preview {
    NavigationStack {
        RegisterView()
            .environmentObject(SessionStore())
            .environment(\.api, .live)
    }
}