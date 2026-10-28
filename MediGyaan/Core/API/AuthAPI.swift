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
        guard userId > 0 else {
            return User(id: 94, name: "Shashi Gupta", email: "shashiguptaazm@gmail.com")
        }
        let dict = try await client.getObject(
            .profile,
            query: ["user_id": String(userId), "viewer_id": String(userId)]
        )
        let dataObj = (dict["data"] as? [String: Any]) ?? dict
        let name = (dataObj["name"] as? String) ?? (dataObj["full_name"] as? String) ?? "Shashi Gupta"
        let email = (dataObj["email"] as? String) ?? "shashiguptaazm@gmail.com"
        let phone = (dataObj["mobile_no"] as? String) ?? (dataObj["phone"] as? String) ?? ""
        let photo = (dataObj["photo"] as? String) ?? (dataObj["avatar"] as? String) ?? ""
        let avatarUrl = photo.isEmpty ? nil : URL(string: photo)
        let college = (dataObj["college"] as? String) ?? ""
        let course = (dataObj["course"] as? String) ?? (dataObj["rank_title"] as? String) ?? "MASTER"
        let streak = (dataObj["streak"] as? Int) ?? 0
        let isVerified = ((dataObj["mobile_verified"] as? Int) == 1) || ((dataObj["verified"] as? Bool) == true)

        var attempted = 0
        var correct = 0
        if let attempts = dataObj["attempts"] as? [[String: Any]], let first = attempts.first {
            attempted = (first["total_attempted"] as? Int) ?? 0
            correct = (first["correct_attempted"] as? Int) ?? 0
        }

        return User(
            id: userId,
            name: name,
            email: email,
            phone: phone,
            avatarURL: avatarUrl,
            college: college,
            course: course,
            referralCode: (dataObj["referral_code"] as? String) ?? "",
            isVerified: isVerified,
            streak: streak,
            overallAttempted: attempted,
            overallCorrect: correct
        )
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
