import Foundation

/// Aggregate facade over every backend client.
///
/// Injected through the SwiftUI environment (`\.api`) so views and view models
/// never reach for a singleton, which keeps them testable against a stub
/// `HTTPClient`.
struct MediGyaanAPI {

    let auth: AuthAPI
    let study: StudyAPI
    let social: SocialAPI
    let thesis: ThesisAPI
    let predictor: PredictorAPI
    let referral: ReferralAPI
    let ai: AIAPI

    init(client: HTTPClient = .shared) {
        auth = AuthAPI(client: client)
        study = StudyAPI(client: client)
        social = SocialAPI(client: client)
        thesis = ThesisAPI(client: client)
        predictor = PredictorAPI(client: client)
        referral = ReferralAPI(client: client)
        ai = AIAPI(client: client)
    }

    /// Live backend instance used by the running app.
    static let live = MediGyaanAPI()

    /// Points every client at a different host, for tests and staging.
    static func pointing(at baseURL: URL) -> MediGyaanAPI {
        let client = HTTPClient()
        client.baseURL = baseURL
        return MediGyaanAPI(client: client)
    }
}
