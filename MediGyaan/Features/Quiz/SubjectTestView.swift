import SwiftUI

// MARK: - Launch contract

/// Ports the launch contract `SubjectTestActivity.onCreate` reads off its intent
/// and off `SharedPreferences("MY_APP")`
/// (`SubjectTestActivity.kt:236-283`, `:195-241`).
///
/// Kotlin accepts a wide spread of extra spellings because several activities
/// (`TopicSelector`, `TopicLobbyActivity`, `TopicLoadingActivity`,
/// `SinglePlayer`) each build the intent themselves. Every alias is preserved
/// here so a caller can pass whichever it has; the resolution order is the same.
struct SubjectTestSession {

    /// `intent.getIntExtra("UNIQUE_ID", 0)` (`SubjectTestActivity.kt:236`).
    /// This is the id the runner reads back as `Quiz.id`.
    var uniqueId: Int = 0

    /// `intent.getStringExtra("SUBJECT")`
    /// (`:238-241`), the documented fallback chain being `SELECTED_SUBJECT`,
    /// then the `selected_subject_preference` preference, then `""`.
    var subject: String = ""

    /// `intent.getStringExtra("TOPIC") ?: ""` (`:243`). `nil` means "every
    /// topic in the subject", which is also why the request omits `&topic=`.
    var topic: String? = nil

    /// The `CHALLENGE_ID` / `challenge_id` string, or the stringified
    /// `CHALLENGE_ID_INT` / `challenge_id_int`, whichever survived the `when`
    /// at `:255-269`. `""` means "no challenge".
    var rawChallengeID: String = ""

    /// `IS_CHALLENGE || IS_CREATOR || is_challenge || challengeId.isNotBlank()`
    /// (`:274-278`). Note the last clause: a non-blank challenge id implies a
    /// battle even when no flag was set.
    var isChallenge: Bool = false

    /// `IS_HOST || IS_CREATOR || is_host` (`:280-283`).
    var isHost: Bool = false

    /// `intent.getIntegerArrayListExtra("QUESTION_ID_LIST")` (`:328`). A
    /// non-empty list takes precedence over every other mode.
    var questionIdList: [Int] = []

    /// Applies the exact alias chain and `||` chain of `onCreate`.
    init(
        uniqueId: Int = 0,
        subjectExtra: String? = nil,
        selectedSubjectExtra: String? = nil,
        savedSubjectPreference: String? = nil,
        topicExtra: String? = nil,
        challengeIDStringExtra: String? = nil,
        challengeIDIntExtra: Int = 0,
        isChallengeExtra: Bool = false,
        isCreatorExtra: Bool = false,
        isHostExtra: Bool = false,
        questionIdList: [Int] = []
    ) {
        self.uniqueId = uniqueId

        let resolvedSubject = subjectExtra
            ?? selectedSubjectExtra
            ?? savedSubjectPreference
            ?? ""
        subject = resolvedSubject

        topic = topicExtra

        // `challengeId = when { !challengeIdString.isNullOrBlank() &&
        // challengeIdString != "0" -> …  challengeIdInt != 0 -> …  else -> "" }`
        let trimmedChallenge = challengeIDStringExtra?.trimmingCharacters(in: .whitespacesAndNewlines)
        if let trimmedChallenge, !trimmedChallenge.isEmpty, trimmedChallenge != "0" {
            rawChallengeID = trimmedChallenge
        } else if challengeIDIntExtra != 0 {
            rawChallengeID = String(challengeIDIntExtra)
        } else {
            rawChallengeID = ""
        }

        isChallenge = isChallengeExtra
            || isCreatorExtra
            || !rawChallengeID.isEmpty

        isHost = isHostExtra || isCreatorExtra

        self.questionIdList = questionIdList
    }

    /// Ports the `if / else if / else` mode ladder at
    /// `SubjectTestActivity.kt:327-394`.
    var mode: SubjectTestMode {
        if !questionIdList.isEmpty { return .fixedTest }
        if isChallenge && !rawChallengeID.isEmpty { return .multiplayer }
        return .singlePlayer
    }

    /// Ports `parseChallengeIdToInt(raw)` (`:2404-2408`):
    /// `raw.toIntOrNull() ?: raw.removePrefix("lobby_").toIntOrNull() ?: 0`.
    var challengeId: Int {
        SubjectTestSession.parseChallengeIdToInt(rawChallengeID)
    }

    static func parseChallengeIdToInt(_ raw: String) -> Int {
        if let value = Int(raw) { return value }
        if raw.hasPrefix("lobby_") {
            return Int(raw.dropFirst("lobby_".count)) ?? 0
        }
        return 0
    }

    /// `prefs.getString("selected_subject_preference", "")` — the preference
    /// name is kept verbatim so an existing install picks up the same value.
    static let subjectPreferenceKey = "selected_subject_preference"

    /// The `name` key of `SharedPreferences("MY_APP")`, mirrored by
    /// `SessionStore.userName`; `"Doctor"` is the Kotlin fallback (`:212`).
    static let fallbackUserName = "Doctor"
}

/// Ports the three mutually exclusive branches of `SubjectTestActivity.onCreate`
/// (`:327-394`), each of which hid a different slice of
/// `res/layout/activity_test_mode.xml`.
enum SubjectTestMode: String, CaseIterable, Identifiable {

    /// `incomingIds != null && incomingIds.isNotEmpty` (`:330`). Hides
    /// `R.id.topicLayout` and `R.id.powersContainer`, and blanks the battle card
    /// through `setBattleStatusVisible(false)`.
    case fixedTest

    /// `isChallenge && challengeId.isNotBlank()` (`:356`). Keeps the battle
    /// card and the four Guardian powers, and seeds the shared question order.
    case multiplayer

    /// The `else` branch (`:377`). Battle card and powers hidden, questions
    /// pulled from `api/getQuestions.php`.
    case singlePlayer

    var id: String { rawValue }

    /// `startTimer(30 * 60 * 1000L)` (`:352`, `:391`).
    static let soloDurationSeconds: Int = 30 * 60

    /// `startTimer(15 * 60 * 1000L)` (`:375`).
    static let multiplayerDurationSeconds: Int = 15 * 60

    var baseDurationSeconds: Int {
        self == .multiplayer ? Self.multiplayerDurationSeconds : Self.soloDurationSeconds
    }

    /// `setBattleStatusVisible(false)` / `findViewById(R.id.battleCard).GONE`.
    var showsBattleChrome: Bool { self == .multiplayer }

    /// `powersContainer.visibility = View.GONE` (`:349`, `:388`).
    var showsPowerRow: Bool { self == .multiplayer }

    /// `findViewById(R.id.topicLayout)?.visibility = View.GONE` (`:344`).
    var showsTopicHeader: Bool { self != .fixedTest }

    var title: String {
        switch self {
        case .fixedTest: return "Fixed Test"
        case .multiplayer: return "1v1 Arena"
        case .singlePlayer: return "Solo Practice"
        }
    }

    var subtitle: String {
        switch self {
        case .fixedTest: return "A preset question list handed down by the launcher."
        case .multiplayer: return "Shared 15-question duel against another doctor."
        case .singlePlayer: return "Shuffled question pool drawn from this subject."
        }
    }

    var systemImage: String {
        switch self {
        case .fixedTest: return "list.number"
        case .multiplayer: return "bolt.horizontal.circle.fill"
        case .singlePlayer: return "stethoscope"
        }
    }
}

/// Ports `playRemoteActionAnimation`'s `when (type)` colour table
/// (`:1632-1641`) and `localFallback(type, actorName, amount)` (`:1465-1476`).
enum SubjectTestTauntKind: String, CaseIterable, Identifiable {

    case attack = "ATTACK"
    case shield = "SHIELD"
    case adrenaline = "ADRENALINE"
    case shock = "SHOCK"
    case confuse = "CONFUSE"
    case selfHit = "SELF_HIT"
    case blocked = "BLOCKED"
    /// The `else -> Color.WHITE` branch; no `localFallback` case matches it.
    case other = "UNKNOWN"

    var id: String { rawValue }

    /// Kotlin: `Color.parseColor("#FF5252")` for attacks and self-hits.
    var tint: Color {
        switch self {
        case .attack, .selfHit: return AppTheme.Palette.error
        case .shield, .blocked: return AppTheme.Ink.cyan
        case .shock: return AppTheme.Ink.gold
        case .confuse: return AppTheme.Palette.accent(for: 4)
        case .adrenaline: return AppTheme.Palette.success
        case .other: return AppTheme.Ink.textPrimary
        }
    }

    /// Kotlin's `!actorName.isNullOrBlank()` guard on the taunt cache key.
    var actorFallbackName: String { "Opponent" }

    /// Ports `localFallback` verbatim (`:1465-1476`).
    func fallback(actorName: String, amount: Int) -> String {
        switch self {
        case .attack: return "\(actorName) strikes hard!"
        case .shield: return "\(actorName) blocks the attack!"
        case .adrenaline: return "\(actorName) heals +\(amount)!"
        case .shock: return "\(actorName) charges energy!"
        case .confuse: return "\(actorName) disrupts an opponent!"
        case .selfHit: return "\(actorName) messed up!"
        case .blocked: return "Attack blocked!"
        case .other: return "\(actorName) makes a move!"
        }
    }

    /// Maps the raw `type` string off a Firebase `last_action` node. Kotlin
    /// uses `else` for anything unrecognised, including the `UNKNOWN` value it
    /// itself writes when broadcasting an action it has no case for.
    static func kind(for raw: String) -> SubjectTestTauntKind {
        SubjectTestTauntKind(rawValue: raw) ?? .other
    }
}

/// Ports `parseQuestionContent(text)` (`SubjectTestActivity.kt:2339-2361`) and
/// the reflection that decides whether a fifth option row exists at all
/// (`resources.getIdentifier("optionE", "id", packageName)`, `:414-416`).
///
/// The five-group `A…E` split is preserved because it is the only place in the
/// runner that can recover a fifth choice — the layout treats `optionE` as
/// optional and hides it whenever the id is absent.
struct SubjectTestQuestionText: Equatable {

    let question: String
    let optionA: String
    let optionB: String
    let optionC: String
    let optionD: String
    let optionE: String

    /// `(?is)^(.*?)\bA[\)\.\:]?\s*(.*?)\s*\bB[\)\.\:]?\s*(.*?)\s*\bC[\)\.\:]?\s*(.*?)\s*\bD[\)\.\:]?\s*(.*?)(?:\s*\bE[\)\.\:]?\s*(.*?))?$`
    private static let pattern =
        "(?is)^(.*?)\\bA[\\)\\.\\:]?\\s*(.*?)\\s*\\bB[\\)\\.\\:]?\\s*(.*?)\\s*\\bC[\\)\\.\\:]?\\s*(.*?)\\s*\\bD[\\)\\.\\:]?\\s*(.*?)(?:\\s*\\bE[\\)\\.\\:]?\\s*(.*?))?$"

    /// `regex.find(text) ?: return null` (`:2344`).
    static func parse(_ text: String) -> SubjectTestQuestionText? {
        guard let regex = try? NSRegularExpression(pattern: pattern) else { return nil }
        let ns = text as NSString
        let full = NSRange(location: 0, length: ns.length)
        guard let match = regex.firstMatch(in: text, range: full), match.numberOfRanges > 5 else {
            return nil
        }

        func group(_ index: Int) -> String {
            let range = match.range(at: index)
            guard range.location != NSNotFound else { return "" }
            return ns.substring(with: range).trimmingCharacters(in: .whitespacesAndNewlines)
        }

        return SubjectTestQuestionText(
            question: group(1),
            optionA: group(2),
            optionB: group(3),
            optionC: group(4),
            optionD: group(5),
            optionE: group(6)
        )
    }

    /// The `optionE?.visibility = View.GONE` branch — a fifth choice is only
    /// ever drawn when the stem actually carries one.
    var hasFifthOption: Bool { !optionE.isEmpty }
}

// MARK: - View model

/// One row of `bindHeroPowerKit`'s four `ImageButton`s (`SubjectTestActivity.kt:598-611`),
/// listed in Android's slot order: `btnConfuse`, `btnShock`, `btnShield`,
/// `btnAdrenaline`.
fileprivate struct SubjectTestPowerSlot: Identifiable {

    let slot: String
    let powerName: String
    let charges: Int
    let systemImage: String

    var id: String { slot }
}

/// Ports the session bootstrap of `SubjectTestActivity`: the intent/preference
/// reads, the hero-kit charge seeding, the three-way mode ladder, the
/// `api/getQuestions.php` id fetch, the shuffle, the 15-question battle cap,
/// the AI taunt pipeline and the final-sync/history writes.
///
/// The exam runner itself — the question card, the radio group, the countdown,
/// the Guardian power buttons, the review JSON — lives in ``TestActivityView``,
/// which this view model hands a prepared ``Quiz`` to.
@MainActor
final class SubjectTestViewModel: ObservableObject {

    // MARK: Android constants

    /// `shuffledPool.take(15)` in `fetchOrCreateSharedQuestionList` (`:806-810`).
    static let battleQuestionCap: Int = 15

    /// `DefaultRetryPolicy(10000, 2, …)` on the question-id request (`:904-908`).
    /// Recorded for parity; `HTTPClient` owns the actual timeout.
    static let questionListRetryCount: Int = 2

    /// `coerceAtLeast(30_000L)` in `startTimer` (`:2157`).
    static let minimumTimerSeconds: Int = 30

    /// `UserDefaults` key `selected_avatar_id`, read by
    /// `AvatarManager.getSelectedAvatarIndex(this)` (`:305`).
    static let selectedAvatarKey = "selected_avatar_id"

    /// The `allQuestionIds` list Kotlin publishes to
    /// `challenges/{id}/question_ids`; iOS keeps it locally instead.
    static let sharedOrderKeyPrefix = "subject_test_shared_order_"

    // MARK: Session

    /// The resolved launch contract.
    let launch: SubjectTestSession

    /// The branch `onCreate` took, exposed so the launcher can show which
    /// chrome the runner will use.
    @Published private(set) var mode: SubjectTestMode

    @Published private(set) var state: LoadState<[Int]> = .idle

    /// `allQuestionIds` (`:169`).
    @Published private(set) var questionIds: [Int] = []

    // MARK: Equipped loadout

    /// `equippedHeroKit` (`:157`) — `GuardianRegistry.getHeroKit(index) ?:
    /// getHeroKit(1001)`.
    @Published private(set) var heroKit: GuardianHeroKit? = nil

    @Published private(set) var intelCharges: Int = 3
    @Published private(set) var strikeCharges: Int = 2
    @Published private(set) var defenseCharges: Int = 3
    @Published private(set) var surgeCharges: Int = 1

    /// `combatEngine = AvatarCombatEngine.createForUser(this)` (`:301`). Drives
    /// the per-warrior timer adjustment in ``timerDurationSeconds``.
    @Published private(set) var combatEngine: AvatarCombatEngine? = nil

    // MARK: Presentation

    /// The last taunt resolved through ``fetchTaunt(kind:actorName:amount:)``.
    @Published private(set) var lastTaunt: String? = nil

    private var api: MediGyaanAPI = .live
    private var userId: Int = 1
    private var hasStarted: Bool = false
    private var tauntCache: [String: String] = [:]
    private var inFlightTaunts: [String: Task<String, Never>] = [:]

    init(launch: SubjectTestSession = SubjectTestSession()) {
        self.launch = launch
        self.mode = launch.mode
    }

    // MARK: - Derived state

    /// `displayQuestion`'s `topicLayout`, hidden for a fixed test.
    var showsTopic: Bool {
        mode.showsTopicHeader && !(launch.topic ?? "").isEmpty
    }

    /// `historyTitle` for `QuizHistoryManager` — Android passes the literal
    /// `"Challenge Match"` for a battle and nothing at all for a solo run.
    var historyTitle: String {
        mode == .multiplayer ? "Challenge Match" : "Subject Test"
    }

    /// The `topic = currentTopic ?: currentSubject` fallback
    /// `launchResultScreen` passes to `HistoryManager.saveHistory` (`:2073`).
    var historyTopic: String {
        let topic = launch.topic ?? ""
        return topic.isEmpty ? launch.subject : topic
    }

    /// The `title` `TestActivityView` shows in its header. Kotlin has no
    /// equivalent string — `activity_test_mode.xml` never labels the run.
    var displayTitle: String {
        if let topic = launch.topic, !topic.isEmpty { return topic }
        if launch.subject.isEmpty { return "Subject Test" }
        return launch.subject
    }

    /// Ports `startTimer(millis)` (`:2153-2158`): the base duration plus the
    /// equipped warrior's adjustment, never dropping below 30 seconds.
    var timerDurationSeconds: Int {
        let baseMillis = mode.baseDurationSeconds * 1000
        guard baseMillis > 10_000, let engine = combatEngine else {
            return mode.baseDurationSeconds
        }
        let adjusted = engine.getTimerAdjustmentSeconds() * 1000
        let adjustedMillis = max(
            Self.minimumTimerSeconds * 1000,
            baseMillis + Int(adjusted.rounded())
        )
        return adjustedMillis / 1000
    }

    /// The four powers in Android's button order (`btnConfuse`, `btnShock`,
    /// `btnShield`, `btnAdrenaline` — slot 1 through slot 4).
    fileprivate var loadout: [SubjectTestPowerSlot] {
        guard let kit = heroKit else { return [] }
        return [
            SubjectTestPowerSlot(
                slot: "Intel",
                powerName: kit.intelPower.powerName,
                charges: intelCharges,
                systemImage: kit.intelPower.systemIconName
            ),
            SubjectTestPowerSlot(
                slot: "Strike",
                powerName: kit.strikePower.powerName,
                charges: strikeCharges,
                systemImage: kit.strikePower.systemIconName
            ),
            SubjectTestPowerSlot(
                slot: "Defense",
                powerName: kit.defensePower.powerName,
                charges: defenseCharges,
                systemImage: kit.defensePower.systemIconName
            ),
            SubjectTestPowerSlot(
                slot: "Surge",
                powerName: kit.surgePower.powerName,
                charges: surgeCharges,
                systemImage: kit.surgePower.systemIconName
            )
        ]
    }

    // MARK: - Lifecycle

    /// Ports `onCreate` (`:192-398`) minus the view binding, the Firebase
    /// wiring and the TTS bootstrap, all of which belong to the runner.
    func start(api: MediGyaanAPI, userId: Int) async {
        guard !hasStarted else { return }
        hasStarted = true
        self.api = api
        self.userId = userId
        state = .loading

        RemoteLogger.log(
            tag: "CHALLENGE_DEBUG",
            message: "SubjectTest onCreate -> userId=\(userId) uniqueId=\(launch.uniqueId) challengeId='\(launch.rawChallengeID)' isChallenge=\(launch.isChallenge) isHost=\(launch.isHost)",
            metadata: ["subject": launch.subject, "mode": mode.rawValue]
        )

        // `if (userId == 0) { Toast("Session expired…"); finish() }` (`:219-231`).
        guard userId > 0 else {
            hasStarted = false
            state = .failed("Session expired. Please login again.")
            return
        }

        resolveLoadout()
        await resolveQuestionIds()
    }

    /// Cancels anything still in flight — the Kotlin analogue of the
    /// `onDestroy` teardown at `:2418-2456`.
    func stop() {
        for task in inFlightTaunts.values { task.cancel() }
        inFlightTaunts.removeAll()
    }

    // MARK: - Loadout

    /// Ports `AvatarManager.getSelectedAvatarIndex(this)` and the
    /// `GuardianRegistry.getHeroKit(equippedAvatarIndex) ?:
    /// GuardianRegistry.getHeroKit(1001)` chain, plus the per-quiz charge
    /// seeding at `:305-312`.
    private func resolveLoadout() {
        let equippedIndex = UserDefaults.standard.integer(forKey: Self.selectedAvatarKey)
        let kit = GuardianRegistry.getHeroKit(for: GuardianRegistry.avatarIndex(for: max(equippedIndex, 1)))
            ?? GuardianRegistry.getHeroKit(for: 1001)
        heroKit = kit

        if let kit {
            intelCharges = kit.intelPower.chargesPerQuiz
            strikeCharges = kit.strikePower.chargesPerQuiz
            defenseCharges = kit.defensePower.chargesPerQuiz
            surgeCharges = kit.surgePower.chargesPerQuiz
        }

        if let warrior = Warrior.allWarriors.first(where: { $0.id == equippedIndex }) {
            combatEngine = AvatarCombatEngine(warrior: warrior)
        }
    }

    // MARK: - Question list

    /// Dispatches the three `onCreate` branches.
    private func resolveQuestionIds() async {
        var ids: [Int] = []

        switch mode {
        case .fixedTest:
            ids = launch.questionIdList
        case .multiplayer:
            ids = await resolveSharedQuestionOrder()
        case .singlePlayer:
            ids = await fetchQuestionListSinglePlayer()
        }

        guard !ids.isEmpty else {
            hasStarted = false
            // `Toast("No questions available")` (`:928`) and the multiplayer
            // `Toast("No questions found for this topic")` (`:828-832`).
            state = .failed(noQuestionsMessage)
            return
        }

        questionIds = ids
        state = .loaded(ids)
    }

    /// `Toast("No questions available")` versus
    /// `Toast("No questions found for this topic")` — the two `else` branches
    /// of the mode ladder use different copy.
    private var noQuestionsMessage: String {
        mode == .multiplayer ? "No questions found for this topic" : "No questions available"
    }

    /// Ports `fetchQuestionListSinglePlayer` (`:920-937`): take the whole pool,
    /// shuffle it, then start at index 0.
    private func fetchQuestionListSinglePlayer() async -> [Int] {
        var ids = await fetchQuestionIdsFromBackend()
        guard !ids.isEmpty else { return [] }
        shuffleQuestionIds(&ids)
        return ids
    }

    /// Ports `fetchOrCreateSharedQuestionList` (`:771-849`).
    ///
    /// Kotlin reads `challenges/{id}/question_ids`; when the node is missing and
    /// the local user is the host it shuffles the backend pool, keeps 15 and
    /// writes them back for the other players, and when the local user is a
    /// client it simply waits. iOS has no Realtime Database, so the published
    /// order is cached in `UserDefaults` under ``sharedOrderKeyPrefix`` instead
    /// — same read/write/host-only-if-absent semantics on one device.
    private func resolveSharedQuestionOrder() async -> [Int] {
        let orderKey = Self.sharedOrderKeyPrefix + launch.rawChallengeID

        if let stored = UserDefaults.standard.string(forKey: orderKey) {
            let ids = stored
                .split(separator: ",")
                .compactMap { Int($0) }
                .filter { $0 > 0 }
            if !ids.isEmpty {
                return Array(ids.prefix(Self.battleQuestionCap))
            }
        }

        // "Client waiting for host to create shared question list…" (`:837`).
        guard launch.isHost else { return [] }

        let pool = await fetchQuestionIdsFromBackend()
        guard !pool.isEmpty else { return [] }

        let battle = Array(pool.shuffled().prefix(Self.battleQuestionCap))
        UserDefaults.standard.set(battle.map(String.init).joined(separator: ","), forKey: orderKey)

        RemoteLogger.log(
            tag: "CHALLENGE_DEBUG",
            message: "Shared list of \(battle.count) questions published for challenge \(launch.rawChallengeID)"
        )
        return battle
    }

    /// Ports `shuffleQuestionIds` (`:915-918`).
    private func shuffleQuestionIds(_ ids: inout [Int]) {
        ids.shuffle()
    }

    /// Ports `fetchQuestionIdsFromBackend` (`:851-913`):
    /// `GET api/getQuestions.php?subject=<encoded>&user_id=<id>[&topic=<encoded>]`,
    /// guarded on `success`, reading `all_question_ids`.
    private func fetchQuestionIdsFromBackend() async -> [Int] {
        var query: [String: String] = [
            "subject": launch.subject,
            "user_id": String(userId)
        ]
        if let topic = launch.topic, !topic.isEmpty {
            query["topic"] = topic
        }

        RemoteLogger.log(
            tag: "CHALLENGE_DEBUG",
            message: "STEP 1: Fetching question IDs from backend -> subject=\(launch.subject) topic=\(launch.topic ?? "-") userId=\(userId)"
        )

        guard let object = try? await HTTPClient.shared.getObject(.questionsApi, query: query) else {
            RemoteLogger.log(tag: "CHALLENGE_DEBUG", message: "STEP ERROR: Question ID request failed")
            return []
        }

        guard (object["success"] as? Bool) ?? false else {
            let reason = (object["error"] as? String) ?? ""
            RemoteLogger.log(tag: "CHALLENGE_DEBUG", message: "STEP 3: Backend returned failure -> \(reason)")
            return []
        }

        guard let raw = object["all_question_ids"] as? [Any] else {
            RemoteLogger.log(tag: "CHALLENGE_DEBUG", message: "STEP 4: 'all_question_ids' missing")
            return []
        }

        var ids: [Int] = []
        for entry in raw {
            if let value = entry as? Int {
                ids.append(value)
            } else if let value = entry as? NSNumber {
                ids.append(value.intValue)
            } else if let text = entry as? String, let value = Int(text) {
                ids.append(value)
            }
        }

        if let data = object["data"] as? [String: Any],
           let preview = data["question"] as? String, !preview.isEmpty {
            RemoteLogger.log(
                tag: "CHALLENGE_DEBUG",
                message: "STEP 6: First question preview -> \(preview.prefix(60))"
            )
        }

        RemoteLogger.log(
            tag: "CHALLENGE_DEBUG",
            message: "STEP 5: Parsed \(ids.count) question IDs for mode \(mode.rawValue)"
        )
        return ids
    }

    // MARK: - Launch

    /// Builds the ``Quiz`` handed to ``TestActivityView``. `UNIQUE_ID` becomes
    /// `Quiz.id`, which the runner reads back as its `uniqueId`.
    func buildLaunchQuiz() -> Quiz {
        Quiz(
            id: launch.uniqueId,
            title: displayTitle,
            topic: historyTopic,
            subject: launch.subject,
            questionCount: questionIds.count,
            durationSeconds: timerDurationSeconds
        )
    }

    /// Ports `executeIntelScanClue(powerName)` (`:646-657`): scan the stem for
    /// the eleven high-yield phrases the strike/intel powers highlight.
    ///
    /// `text` is the question stem in the runner; the launcher passes the
    /// subject/topic header as a preview.
    static func intelScanClue(questionText: String, powerName: String) -> String {
        let highYieldTerms = [
            "triad", "most common", "pathognomonic", "gold standard", "first line",
            "sign", "acute", "artery", "nerve", "mutation", "receptor"
        ]
        let haystack = questionText.lowercased()
        let found = highYieldTerms.filter { haystack.contains($0) }

        if found.isEmpty {
            return "🔍 \(powerName): Clinical hallmark points towards core presentation!"
        }
        return "🔍 \(powerName): Focus on [\(found.joined(separator: ", "))]"
    }

    // MARK: - Taunts

    /// Ports `fetchTaunt(type, actorName, amount, callback)` (`:1385-1464`):
    /// cache by `type|actor|amount`, collapse concurrent requests onto one, POST
    /// `taunt_ai.php`, and fall back to ``SubjectTestTauntKind/fallback(actorName:amount:)``
    /// on an empty body, a parse error or a transport error.
    func fetchTaunt(
        kind: SubjectTestTauntKind,
        actorName: String?,
        amount: Int
    ) async -> String {
        let safeName = (actorName?.isEmpty == false) ? (actorName ?? "") : kind.actorFallbackName
        let key = "\(kind.rawValue)|\(safeName)|\(amount)"

        if let cached = tauntCache[key] { return cached }
        if let inFlight = inFlightTaunts[key] { return await inFlight.value }

        let task = Task<String, Never> { [weak self] in
            guard let self else { return kind.fallback(actorName: safeName, amount: amount) }
            let remote = (try? await self.requestRemoteTaunt(kind: kind, actorName: safeName, amount: amount)) ?? ""
            if remote.isEmpty {
                return kind.fallback(actorName: safeName, amount: amount)
            }
            return remote
        }
        inFlightTaunts[key] = task

        let resolved = await task.value
        inFlightTaunts[key] = nil
        tauntCache[key] = resolved
        lastTaunt = resolved
        return resolved
    }

    /// The `StringRequest` body of `fetchTaunt` (`:1451-1457`).
    private func requestRemoteTaunt(
        kind: SubjectTestTauntKind,
        actorName: String,
        amount: Int
    ) async throws -> String {
        let object = try await HTTPClient.shared.postObject(
            form: [
                "type": kind.rawValue,
                "actor": actorName,
                "amount": String(amount)
            ],
            to: .tauntAi
        )
        return (object["taunt"] as? String)?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
    }

    // MARK: - Teardown writes

    /// Ports `launchResultScreen(won)`'s `HistoryManager.saveHistory` call
    /// (`:2069-2083`).
    func recordHistory(score: Int, correctAnswers: Int, wrongAnswers: Int) {
        QuizHistoryManager.shared.saveHistory(
            userId: userId,
            mode: mode == .multiplayer ? "CHALLENGE" : "SINGLE_PLAYER",
            title: historyTitle,
            topic: historyTopic,
            score: score,
            totalQuestions: questionIds.count,
            correctAnswers: correctAnswers,
            wrongAnswers: wrongAnswers,
            challengeId: launch.rawChallengeID
        )
    }

    /// Ports the `finalizeChallenge` POST body (`:2044-2051`): Kotlin sends
    /// `challenge_id`, `user_id`, `finish_test` and `score`, and launches the
    /// result screen on success *or* failure.
    func postFinalSync(score: Int) async {
        guard mode == .multiplayer else { return }
        _ = try? await HTTPClient.shared.postObject(
            form: [
                "challenge_id": launch.rawChallengeID,
                "user_id": String(userId),
                "finish_test": "true",
                "score": String(score)
            ],
            to: .syncChallenge
        )
    }
}

// MARK: - Screen

/// The subject/topic test launcher.
///
/// Ports the entry half of `SubjectTestActivity.kt`: it resolves the launch
/// contract, prepares the question list and the equipped Guardian loadout, and
/// then presents ``TestActivityView`` with the assembled ``Quiz`` — the runner
/// that owns the question card, the countdown, the Guardian powers, the duel
/// and the review screen.
struct SubjectTestView: View {

    /// The resolved `UNIQUE_ID` / `SUBJECT` / `TOPIC` / `CHALLENGE_ID` contract.
    let launch: SubjectTestSession

    @Environment(\.api) private var api
    @EnvironmentObject private var session: SessionStore

    @StateObject private var viewModel: SubjectTestViewModel
    @State private var activeQuiz: Quiz?
    @State private var errorMessage: String?
    @State private var hasStarted = false

    init(launch: SubjectTestSession = SubjectTestSession()) {
        self.launch = launch
        _viewModel = StateObject(wrappedValue: SubjectTestViewModel(launch: launch))
    }

    var body: some View {
        content
            .screenBackground()
            .navigationTitle("Subject Test")
            .navigationBarTitleDisplayMode(.inline)
            .task {
                guard !hasStarted else { return }
                hasStarted = true
                await run()
            }
            .onDisappear {
                viewModel.stop()
            }
            .fullScreenCover(item: $activeQuiz) { quiz in
                TestActivityView(
                    quiz: quiz,
                    isChallenge: viewModel.mode == .multiplayer,
                    opponentName: "Dr. Opponent",
                    challengeId: launch.challengeId,
                    isHost: launch.isHost
                ) {
                    activeQuiz = nil
                }
            }
            .errorAlert(message: $errorMessage)
    }

    private func run() async {
        await viewModel.start(api: api, userId: session.userId)
        if let message = viewModel.state.errorMessage {
            hasStarted = false
            errorMessage = message
        }
    }

    // MARK: - States

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .idle, .loading:
            LoadingStateView(message: "Preparing \(viewModel.displayTitle)…")

        case .failed(let message):
            ErrorStateView(message: message) {
                hasStarted = false
                Task { await run() }
            }

        case .loaded:
            launcher
        }
    }

    private var launcher: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.md) {
                headerCard
                modeCard
                loadoutCard
                intelPreview
                PrimaryButton(title: startTitle, isSubmit: true) {
                    activeQuiz = viewModel.buildLaunchQuiz()
                }
            }
            .padding(AppTheme.Spacing.lg)
        }
    }

    private var startTitle: String {
        switch viewModel.mode {
        case .fixedTest: return "START FIXED TEST"
        case .multiplayer: return "ENTER THE ARENA"
        case .singlePlayer: return "START SOLO TEST"
        }
    }

    // MARK: - Header

    /// The `topicLayout` row plus `tvQuestionProgress` / `statusText`.
    private var headerCard: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                HStack(spacing: AppTheme.Spacing.xs) {
                    if !launch.subject.isEmpty {
                        TagBadge(text: launch.subject, tint: AppTheme.Ink.cyan)
                    }
                    if viewModel.showsTopic, let topic = launch.topic, !topic.isEmpty {
                        TagBadge(text: topic, tint: AppTheme.Ink.gold)
                    }
                    Spacer(minLength: 0)
                }

                Text(viewModel.displayTitle)
                    .font(AppTheme.Font.title3)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)

                HStack(spacing: AppTheme.Spacing.md) {
                    headerStat(value: "\(viewModel.questionIds.count)", label: "Questions")
                    headerStat(
                        value: String(format: "%d:%02d", viewModel.timerDurationSeconds / 60, viewModel.timerDurationSeconds % 60),
                        label: "Time limit"
                    )
                    headerStat(value: "Q 1 / \(viewModel.questionIds.count)", label: "Progress")
                }
            }
        }
    }

    private func headerStat(value: String, label: String) -> some View {
        InkStatTile(value: value, label: label)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.sm, style: .continuous)
                    .fill(AppTheme.Ink.tile)
            )
    }

    // MARK: - Mode

    /// The single branch `onCreate` took, spelled out so the doctor can see
    /// which question pool and which chrome the runner will use.
    private var modeCard: some View {
        InkCard(fill: AppTheme.Ink.surface, stroke: AppTheme.Ink.slate) {
            HStack(alignment: .top, spacing: AppTheme.Spacing.md) {
                Image(systemName: viewModel.mode.systemImage)
                    .font(.system(size: 20, weight: .semibold))
                    .foregroundStyle(AppTheme.Ink.gold)

                VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
                    Text(viewModel.mode.title)
                        .font(AppTheme.Font.bodyBold)
                        .foregroundStyle(AppTheme.Ink.textPrimary)
                    Text(viewModel.mode.subtitle)
                        .font(AppTheme.Font.micro)
                        .foregroundStyle(AppTheme.Ink.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                Spacer(minLength: 0)
            }
        }
    }

    // MARK: - Loadout

    /// The four `ImageButton`s `bindHeroPowerKit` icons and captions, listed in
    /// Android's slot order.
    private var loadoutCard: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            SectionHeader(title: "Equipped Arsenal", subtitle: viewModel.heroKit?.championName ?? "Axiom")

            if viewModel.mode.showsPowerRow, !viewModel.loadout.isEmpty {
                ForEach(viewModel.loadout) { entry in
                    HStack(spacing: AppTheme.Spacing.md) {
                        Image(systemName: entry.systemImage)
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(AppTheme.Ink.cyan)
                            .frame(width: 28, height: 28)
                            .background(Circle().fill(AppTheme.Ink.elevated))

                        VStack(alignment: .leading, spacing: 1) {
                            Text(entry.powerName)
                                .font(AppTheme.Font.callout.weight(.semibold))
                                .foregroundStyle(AppTheme.Ink.textPrimary)
                                .lineLimit(1)
                            Text(entry.slot)
                                .font(AppTheme.Font.micro)
                                .foregroundStyle(AppTheme.Ink.textSecondary)
                        }

                        Spacer(minLength: 0)

                        Text("x\(entry.charges)")
                            .font(AppTheme.Font.captionBold)
                            .foregroundStyle(entry.charges > 0 ? AppTheme.Ink.success : AppTheme.Palette.textMuted)
                    }
                    .padding(.vertical, AppTheme.Spacing.xxs)
                }
            } else {
                Text("Guardian powers are disabled outside the 1v1 arena.")
                    .font(AppTheme.Font.micro)
                    .foregroundStyle(AppTheme.Palette.textSecondary)
            }
        }
    }

    // MARK: - Intel preview

    /// `executeIntelScanClue` run over the header text, so the doctor can see
    /// the high-yield phrase scanner before the first question arrives.
    private var intelPreview: some View {
        let powerName = viewModel.heroKit?.intelPower.powerName ?? "Fascial Plane Scan"
        let clue = SubjectTestViewModel.intelScanClue(
            questionText: "\(launch.subject) \(launch.topic ?? "")",
            powerName: powerName
        )

        return InkCard(fill: AppTheme.Ink.elevated, padding: AppTheme.Spacing.md) {
            HStack(alignment: .top, spacing: AppTheme.Spacing.sm) {
                Image(systemName: "eye.fill")
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(AppTheme.Ink.cyan)

                Text(clue)
                    .font(AppTheme.Font.micro)
                    .foregroundStyle(AppTheme.Ink.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }
}