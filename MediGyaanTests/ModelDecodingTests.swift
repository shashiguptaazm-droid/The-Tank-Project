import XCTest
@testable import MediGyaan

/// Verifies the models tolerate the real payload shapes the PHP backend emits.
///
/// MySQL returns most columns as strings, keys are inconsistently named
/// (`user_id` vs `userId`), and some endpoints omit fields entirely, so these
/// tests pin down each of those variations.
final class ModelDecodingTests: XCTestCase {

    private func decode<T: Decodable>(_ type: T.Type, from json: String) throws -> T {
        try JSONDecoder().decode(T.self, from: Data(json.utf8))
    }

    // MARK: - Login

    /// The exact success shape produced by `api/login.php`.
    func testLoginResponseSuccess() throws {
        let json = #"{"success":true,"user_id":12,"name":"Shashi Kumar","email":"s@example.com"}"#
        let response = try decode(LoginResponse.self, from: json)

        XCTAssertTrue(response.success)
        XCTAssertEqual(response.userId, 12)
        XCTAssertEqual(response.name, "Shashi Kumar")
    }

    /// Verified live: `{"success":false,"error":"Invalid credentials","code":401}`.
    func testLoginResponseFailureCarriesBackendMessage() throws {
        let json = #"{"success":false,"error":"Invalid credentials","code":401}"#
        let response = try decode(LoginResponse.self, from: json)

        XCTAssertFalse(response.success)
        XCTAssertEqual(response.message, "Invalid credentials")
    }

    /// `user_id` arriving as a string, which is what MySQL produces.
    func testNumericStringsAreCoerced() throws {
        let json = #"{"success":true,"user_id":"42","name":"A","email":"a@b.c"}"#
        let response = try decode(LoginResponse.self, from: json)

        XCTAssertEqual(response.userId, 42)
    }

    // MARK: - Dashboard

    /// Verified live: `{"success":false,"message":"Invalid User ID"}`.
    func testDashboardErrorPayload() throws {
        let json = #"{"success":false,"message":"Invalid User ID"}"#
        let stats = try decode(DashboardStats.self, from: json)

        XCTAssertEqual(stats.message, "Invalid User ID")
        XCTAssertEqual(stats.attempted, 0)
    }

    func testDashboardStatisticsAreParsed() throws {
        let json = """
        {"success":true,"user_id":7,"name":"Asha","attempted":"120","correct":"90",
         "wrong":"30","accuracy":"75.0","streak":"5","rank":"12","points":"880"}
        """
        let stats = try decode(DashboardStats.self, from: json)

        XCTAssertEqual(stats.userId, 7)
        XCTAssertEqual(stats.attempted, 120)
        XCTAssertEqual(stats.correct, 90)
        XCTAssertEqual(stats.wrong, 30)
        XCTAssertEqual(stats.streak, 5)
        XCTAssertEqual(stats.accuracy, 75.0)
    }

    // MARK: - Questions

    /// Options delivered as an explicit array with a 1-based correct answer.
    func testQuestionWithOptionsArray() throws {
        let json = """
        {"question_id":"9","question":"Which nerve supplies the deltoid?",
         "options":["Axillary","Radial","Median","Ulnar"],"correct_option":"1","explanation":"Axillary nerve."}
        """
        let question = try decode(Question.self, from: json)

        XCTAssertEqual(question.id, 9)
        XCTAssertEqual(question.options.count, 4)
        XCTAssertEqual(question.options[question.correctIndex], "Axillary")
        XCTAssertEqual(question.explanation, "Axillary nerve.")
    }

    /// Legacy rows use separate `option1..option4` columns.
    func testQuestionWithSeparateOptionColumns() throws {
        let json = """
        {"question_id":3,"question_text":"Q","option1":"A","option2":"B",
         "option3":"C","option4":"D","answer":"C"}
        """
        let question = try decode(Question.self, from: json)

        XCTAssertEqual(question.options, ["A", "B", "C", "D"])
        XCTAssertEqual(question.options[question.correctIndex], "C")
    }

    // MARK: - Topics

    func testTopicArrayAndSingleObject() throws {
        let arrayJSON = #"[{"topic_id":1,"topic_name":"Anatomy"}]"#
        let topics = try decode([Topic].self, from: arrayJSON)
        XCTAssertEqual(topics.first?.name, "Anatomy")

        // Some endpoints return a lone object where an array is expected.
        let singleJSON = #"{"topic_id":2,"topic_name":"Physiology"}"#
        let single = try decode(Topic.self, from: singleJSON)
        XCTAssertEqual(single.id, 2)
    }

    // MARK: - Envelopes

    func testAcknowledgmentPrefersErrorOverMessage() throws {
        let errorJSON = #"{"success":false,"error":"Unauthorized Access","message":"ignored"}"#
        XCTAssertEqual(try decode(Acknowledgment.self, from: errorJSON).message, "Unauthorized Access")

        let okJSON = #"{"success":true,"message":"Saved"}"#
        XCTAssertEqual(try decode(Acknowledgment.self, from: okJSON).message, "Saved")
    }

    // MARK: - Referral

    func testReferralInfoParses() throws {
        let json = #"{"referral_code":"MG1234","total_referrals":"6","successful_referrals":"4","points_earned":"400"}"#
        let info = try decode(ReferralInfo.self, from: json)

        XCTAssertEqual(info.code, "MG1234")
        XCTAssertEqual(info.totalReferrals, 6)
        XCTAssertEqual(info.successfulReferrals, 4)
        XCTAssertEqual(info.pointsEarned, 400)
    }

    // MARK: - Quiz attempt

    /// The attempt aggregates must be self-consistent for the result screen.
    func testQuizAttemptScoring() {
        let attempt = QuizAttempt(
            quizId: 1,
            quizTitle: "Anatomy",
            userId: 5,
            answers: [
                AttemptAnswer(questionId: 1, selectedIndex: 0, correctIndex: 0),
                AttemptAnswer(questionId: 2, selectedIndex: 1, correctIndex: 3),
                AttemptAnswer(questionId: 3, selectedIndex: 2, correctIndex: 2),
            ],
            startedAt: Date(timeIntervalSince1970: 0),
            finishedAt: Date(timeIntervalSince1970: 120)
        )

        XCTAssertEqual(attempt.attempted, 3)
        XCTAssertEqual(attempt.correct, 2)
        XCTAssertEqual(attempt.wrong, 1)
        XCTAssertEqual(attempt.accuracy, 2.0 / 3.0, accuracy: 0.0001)
        XCTAssertEqual(attempt.durationSeconds, 120)
    }

    /// The form fields must match what `api/sync_game_stats.php` reads.
    func testQuizAttemptSyncFieldNames() {
        let attempt = QuizAttempt(
            quizId: 9,
            quizTitle: "Physio",
            userId: 3,
            answers: [AttemptAnswer(questionId: 1, selectedIndex: 0, correctIndex: 0)],
            startedAt: Date(),
            finishedAt: Date()
        )

        let fields = attempt.syncFormFields
        XCTAssertEqual(fields["user_id"], "3")
        XCTAssertEqual(fields["quiz_id"], "9")
        XCTAssertEqual(fields["attempted"], "1")
        XCTAssertEqual(fields["correct"], "1")
        XCTAssertEqual(fields["wrong"], "0")
        XCTAssertNotNil(fields["answers_json"])
    }

    /// `api/sync_user_cache.php` reads `$_POST`, so field names must be exact.
    func testUserCacheFormFieldNames() {
        let payload = UserCachePayload(
            userId: 11,
            dailyStatsJSON: "{}",
            accuracyHistoryJSON: "{}",
            overallAttempted: 10,
            overallCorrect: 8,
            todayAttempted: 2,
            todayCorrect: 2,
            localStreak: 3
        )

        let fields = payload.formFields
        XCTAssertEqual(fields["user_id"], "11")
        XCTAssertEqual(fields["daily_stats_json"], "{}")
        XCTAssertEqual(fields["accuracy_history_json"], "{}")
        XCTAssertEqual(fields["overall_attempted"], "10")
        XCTAssertEqual(fields["overall_correct"], "8")
        XCTAssertEqual(fields["today_attempted"], "2")
        XCTAssertEqual(fields["today_correct"], "2")
        XCTAssertEqual(fields["local_streak"], "3")
    }
}
