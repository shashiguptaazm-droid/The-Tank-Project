import XCTest
@testable import MediGyaan

/// Session persistence tests.
///
/// Each test uses its own `UserDefaults` suite and keychain service so runs do
/// not interfere with each other or with the real app.
///
/// The class itself is deliberately *not* `@MainActor`: marking it so would
/// conflict with `XCTestCase.setUp()`/`tearDown()`, which are nonisolated.
/// Only the members that touch `SessionStore` are main-actor isolated.
final class SessionStoreTests: XCTestCase {

    private var defaults: UserDefaults!
    private var keychain: KeychainStore!
    private var suiteName: String!

    override func setUp() {
        super.setUp()
        suiteName = "MediGyaanTests.\(UUID().uuidString)"
        defaults = UserDefaults(suiteName: suiteName)
        keychain = KeychainStore(service: suiteName)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suiteName)
        keychain.removeAll()
        super.tearDown()
    }

    @MainActor
    private func makeStore() -> SessionStore {
        SessionStore(keychain: keychain, defaults: defaults)
    }

    // MARK: - Session lifecycle

    @MainActor
    func testStartsSignedOutWhenNothingIsStored() {
        let store = makeStore()

        XCTAssertFalse(store.isAuthenticated)
        XCTAssertNil(store.currentUser)
    }

    /// Mirrors the Android behaviour of persisting `user_id`/`name`/`email`
    /// after a successful login.
    @MainActor
    func testSignInPersistsAndRestoresTheSession() {
        let store = makeStore()
        store.signIn(userId: 42, name: "Shashi", email: "s@example.com", token: "tok_123")

        XCTAssertTrue(store.isAuthenticated)
        XCTAssertEqual(store.currentUser?.id, 42)
        XCTAssertEqual(store.userId, 42)
        XCTAssertEqual(store.authToken, "tok_123")

        // A fresh store over the same storage simulates an app relaunch.
        let restored = makeStore()
        XCTAssertTrue(restored.isAuthenticated)
        XCTAssertEqual(restored.currentUser?.id, 42)
        XCTAssertEqual(restored.currentUser?.name, "Shashi")
        XCTAssertEqual(restored.authToken, "tok_123")
    }

    @MainActor
    func testSignOutClearsEverything() {
        let store = makeStore()
        store.signIn(userId: 7, name: "A", email: "a@b.c", token: "tok")

        store.signOut()

        XCTAssertFalse(store.isAuthenticated)
        XCTAssertNil(store.currentUser)
        XCTAssertEqual(store.userId, 0)
        XCTAssertNil(store.authToken)
        // The token must not survive into a new store either.
        XCTAssertNil(makeStore().authToken)
    }

    @MainActor
    func testUpdateProfileRefreshesCachedFields() {
        let store = makeStore()
        store.signIn(userId: 5, name: "Old", email: "old@example.com")

        store.updateProfile(
            User(id: 5, name: "New Name", email: "new@example.com", college: "AIIMS")
        )

        XCTAssertEqual(store.currentUser?.name, "New Name")
        XCTAssertEqual(store.currentUser?.college, "AIIMS")

        let restored = makeStore()
        XCTAssertEqual(restored.currentUser?.name, "New Name")
    }

    @MainActor
    func testPushTokenRoundTrips() {
        let store = makeStore()
        store.storePushToken("fcm-abc")

        XCTAssertEqual(store.pushToken, "fcm-abc")
    }

    /// A missing or empty token must not be treated as a valid session.
    @MainActor
    func testEmptyTokenDoesNotAuthenticate() {
        keychain.set("", forKey: .authToken)
        let store = makeStore()

        XCTAssertFalse(store.isAuthenticated)
    }

    // MARK: - User model helpers

    func testUserAccuracyCalculation() {
        let user = User(id: 1, name: "A", email: "a@b.c", overallAttempted: 4, overallCorrect: 3)
        XCTAssertEqual(user.accuracy, 0.75, accuracy: 0.0001)

        let empty = User(id: 2, name: "B", email: "b@c.d")
        XCTAssertEqual(empty.accuracy, 0)
    }

    func testUserInitials() {
        XCTAssertEqual(User(id: 1, name: "Shashi Kumar", email: "a@b.c").initials, "SK")
        XCTAssertEqual(User(id: 2, name: "Madonna", email: "a@b.c").initials, "M")
        XCTAssertEqual(User(id: 3, name: "", email: "a@b.c").initials, "")
    }
}
