import Foundation

/// Authentication, registration, OTP, and profile calls.
///
/// Endpoint choices mirror the Android client exactly:
/// * `manualLogin()` posts JSON to `api/login.php`.
/// * The OTP screens use `send_otp3.php` / `verify_otp12.php`.
/// * Password recovery uses the three `forgot_password_*` / `reset_password_app`
///   scripts.
struct AuthAPI {

    private let client: HTTPClient

    init(client: HTTPClient = .shared) {
        self.client = client
    }

    /// Signs in with e-mail and password.
    ///
    /// Live contract (verified against production):
    /// * success → `{"success":true,"user_id":12,"name":"..."}`
    /// * failure → `{"success":false,"error":"Invalid credentials","code":401}`
    func login(email: String, password: String) async throws -> LoginResponse {
        try await client.post(
            json: ["email": email, "password": password],
            to: .login,
            as: LoginResponse.self
        )
    }

    /// Registers a new account. The Android `RegisterActivity` posts the same
    /// field names to the legacy registration script.
    func register(
        name: String,
        email: String,
        password: String,
        phone: String,
        college: String,
        referralCode: String
    ) async throws -> Acknowledgment {
        try await client.post(
            form: [
                "name": name,
                "email": email,
                "password": password,
                "phone": phone,
                "college": college,
                "referral_code": referralCode,
            ],
            to: .googleCallback,
            as: Acknowledgment.self
        )
    }

    /// Requests a signup/login OTP (`send_otp3.php`).
    func sendOtp(phone: String, email: String) async throws -> Acknowledgment {
        try await client.post(
            form: ["phone": phone, "email": email],
            to: .sendOtp,
            as: Acknowledgment.self
        )
    }

    /// Verifies an OTP (`verify_otp12.php`).
    func verifyOtp(phone: String, email: String, code: String) async throws -> Acknowledgment {
        try await client.post(
            form: ["phone": phone, "email": email, "otp": code, "code": code],
            to: .verifyOtp,
            as: Acknowledgment.self
        )
    }

    /// Starts password recovery by mailing an OTP.
    func forgotPasswordSendOtp(email: String) async throws -> Acknowledgment {
        try await client.post(
            form: ["email": email],
            to: .forgotPasswordSendOtp,
            as: Acknowledgment.self
        )
    }

    /// Verifies the recovery OTP.
    func forgotPasswordVerifyOtp(email: String, code: String) async throws -> Acknowledgment {
        try await client.post(
            form: ["email": email, "otp": code, "code": code],
            to: .forgotPasswordVerifyOtp,
            as: Acknowledgment.self
        )
    }

    /// Completes recovery with a new password.
    func resetPassword(email: String, code: String, newPassword: String) async throws -> Acknowledgment {
        try await client.post(
            form: ["email": email, "otp": code, "code": code, "password": newPassword],
            to: .resetPassword,
            as: Acknowledgment.self
        )
    }

    /// Fetches the full profile (`get_profilev1.php`).
    func profile(userId: Int) async throws -> User {
        try await client.get(.profile, query: ["user_id": String(userId)], as: User.self)
    }

    /// Updates the profile. The backend accepts a form body here.
    func updateProfile(
        userId: Int,
        name: String,
        phone: String,
        college: String,
        course: String
    ) async throws -> Acknowledgment {
        try await client.post(
            form: [
                "user_id": String(userId),
                "name": name,
                "phone": phone,
                "college": college,
                "course": course,
            ],
            to: .profile,
            as: Acknowledgment.self
        )
    }

    /// Reports the push token to `api/update_fcmv2.php` (mirrors the Android
    /// `syncFcmToken(userId)` call made right after login).
    func updatePushToken(userId: Int, token: String) async throws -> Acknowledgment {
        try await client.post(
            form: ["user_id": String(userId), "token": token, "fcm_token": token],
            to: .updateFcm,
            as: Acknowledgment.self
        )
    }
}
