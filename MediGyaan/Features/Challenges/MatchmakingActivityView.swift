import SwiftUI
import AVFoundation

/// 1:1 SwiftUI replication of Android's `MatchmakingActivity.kt`.
///
/// Features:
/// - Real-time profile details synchronization from `get_profilev1.php` before queue entry.
/// - Continuous background classical audio (`vivaldi_winter.mp3` loop).
/// - Holographic cyber radar scanning animation with rotating sweep gradient and pulsing rings.
/// - Firebase Realtime Database queue integration (`matchmaking_queue/{subject}_{topic}/entries`) with authenticated token.
/// - Deterministic tie-breaker multiplayer pairing (`pvp_{k1}_{k2}`) preventing split lobbies.
/// - 30-second countdown timer for host matchmaking with automated bot fallback pairing.
/// - Live "Players in Lobby" list.
/// - "⚔ Match Ready!" modal with instant "Fight!" launch into 15-question duel.
struct MatchmakingActivityView: View {

    let subject: String
    let topic: String?
    var onLaunchGame: ((_ challengeId: String, _ isHost: Bool, _ isBotMatch: Bool, _ opponentId: String, _ opponentName: String, _ questionIds: [Int]) -> Void)?

    @EnvironmentObject private var session: SessionStore
    @Environment(\.dismiss) private var dismiss

    // ─── State ───────────────────────────────────────────────────────────────
    @State private var statusMsg: String = "Initializing..."
    @State private var timerMsg: String = ""
    @State private var playersInLobby: [QueuePlayer] = []
    @State private var isHost: Bool = false
    @State private var isBotMatch: Bool = false
    @State private var queueId: String = ""
    @State private var challengeId: String = ""
    @State private var opponentId: String = ""
    @State private var opponentName: String = "Opponent"
    @State private var sharedQuestionIds: [Int] = []
    @State private var userId: Int = 94
    @State private var queueUserId: String = "94_ios"
    @State private var userName: String = "Shashi Gupta"
    @State private var isLaunchingGame: Bool = false

    @State private var showMatchReadyDialog: Bool = false
    @State private var radarRotation: Double = 0
    @State private var radarPulseScale: CGFloat = 1.0

    // ─── Audio ───────────────────────────────────────────────────────────────
    @State private var audioPlayer: AVAudioPlayer? = nil

    // ─── Timers & Tasks ───────────────────────────────────────────────────────
    @State private var countdownRemaining: Int = 30
    @State private var countdownTimer: Timer? = nil
    @State private var pollingTask: Task<Void, Never>? = nil

    private let apiBaseUrl = "https://medigyaan.com/Neurons/"

    struct QueuePlayer: Identifiable, Equatable, Hashable {
        var id: String { queueKey }
        let queueKey: String
        let userId: String
        let userName: String
    }

    var body: some View {
        ZStack {
            // Layer 1: Dark gradient arena backdrop
            LinearGradient(
                colors: [Color(hex: 0x050816), Color(hex: 0x0A1028), Color(hex: 0x050816)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            // Layer 2: Cyber Grid Background Pattern
            cyberGridOverlay

            // Layer 3: Foreground Content & Countdown UI
            VStack(spacing: 0) {
                // Top Subject Banner
                VStack(spacing: 4) {
                    Text(subject.uppercased())
                        .font(.system(size: 11, weight: .black, design: .monospaced))
                        .foregroundStyle(Color.yellow)

                    if let t = topic, !t.isEmpty {
                        Text(t)
                            .font(AppTheme.Font.subheadline)
                            .foregroundStyle(Color.white.opacity(0.8))
                    }
                }
                .padding(.top, 24)

                Spacer()

                // Header Title & Status
                Text("Matchmaking")
                    .font(.system(size: 28, weight: .bold))
                    .foregroundStyle(Color.white)

                Spacer().frame(height: 8)

                Text(statusMsg)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(Color(hex: 0x00E5FF))
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)

                Spacer().frame(height: 24)

                // Holographic Cyber Radar Graphic
                radarHologram

                Spacer().frame(height: 20)

                // 30s Host Countdown Timer
                if !timerMsg.isEmpty {
                    Text(timerMsg)
                        .font(.system(size: 24, weight: .bold))
                        .foregroundStyle(Color(hex: 0xFFD54F))
                        .transition(.scale)
                }

                Spacer().frame(height: 28)

                // Players in Lobby Card
                VStack(spacing: 6) {
                    Text("Players in Lobby:")
                        .font(AppTheme.Font.caption)
                        .fontWeight(.bold)
                        .foregroundStyle(Color.white.opacity(0.9))

                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(playersInLobby) { player in
                            HStack(spacing: 6) {
                                Circle()
                                    .fill(Color(hex: 0x00E5FF))
                                    .frame(width: 6, height: 6)
                                Text(player.userName)
                                    .font(AppTheme.Font.caption)
                                    .fontWeight(.medium)
                                    .foregroundStyle(Color(hex: 0x00E5FF))
                            }
                        }
                    }
                    .frame(minHeight: 44)
                }
                .padding(.horizontal, 24)
                .padding(.vertical, 12)
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(Color.black.opacity(0.35))
                        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.white.opacity(0.1), lineWidth: 1))
                )

                Spacer()

                // Cancel Search Button
                Button {
                    handleCancelSearch()
                } label: {
                    Text("Cancel Search")
                        .font(.system(size: 15, weight: .bold))
                        .foregroundStyle(Color.white)
                        .padding(.horizontal, 32)
                        .padding(.vertical, 14)
                        .background(
                            RoundedRectangle(cornerRadius: 24)
                                .fill(Color(hex: 0xD32F2F))
                        )
                        .shadow(color: Color(hex: 0xD32F2F).opacity(0.4), radius: 8, y: 3)
                }
                .padding(.bottom, 36)
            }
            .padding(.horizontal, 24)
        }
        .navigationBarHidden(true)
        .alert("⚔ Match Ready!", isPresented: $showMatchReadyDialog) {
            Button("Fight!") {
                launchGame()
            }
            Button("Cancel", role: .cancel) {
                handleCancelSearch()
            }
        } message: {
            Text("Opponent Found:\n\(opponentName)")
        }
        .onAppear {
            startContinuousMusic()
            startMatchmakingEngine()
        }
        .onDisappear {
            stopContinuousMusic()
            cleanupQueue()
        }
    }

    // MARK: - Radar Visual

    private var radarHologram: some View {
        ZStack {
            // Pulse wave
            Circle()
                .stroke(Color(hex: 0x00E5FF).opacity(0.4), lineWidth: 2)
                .frame(width: 140, height: 140)
                .scaleEffect(radarPulseScale)
                .opacity(2.0 - Double(radarPulseScale))

            // Radar Base
            Circle()
                .fill(Color(hex: 0x0A1B2A).opacity(0.8))
                .frame(width: 130, height: 130)

            // Scanning Sweeper
            Circle()
                .trim(from: 0, to: 0.25)
                .stroke(
                    AngularGradient(
                        colors: [Color(hex: 0x00E5FF).opacity(0.0), Color(hex: 0x00E5FF)],
                        center: .center
                    ),
                    lineWidth: 50
                )
                .frame(width: 100, height: 100)
                .rotationEffect(.degrees(radarRotation))

            // Radar Border
            Circle()
                .stroke(
                    AngularGradient(
                        colors: [Color(hex: 0x48D6C8), Color(hex: 0x00E5FF), Color(hex: 0x48D6C8).opacity(0.2), Color(hex: 0x48D6C8)],
                        center: .center
                    ),
                    lineWidth: 2.5
                )
                .frame(width: 130, height: 130)

            // Crosshair Reticle
            Image(systemName: "cross.circle")
                .font(.system(size: 24, weight: .light))
                .foregroundStyle(Color(hex: 0x00E5FF).opacity(0.6))
        }
        .onAppear {
            withAnimation(.linear(duration: 2.5).repeatForever(autoreverses: false)) {
                radarRotation = 360
            }
            withAnimation(.easeInOut(duration: 1.6).repeatForever(autoreverses: false)) {
                radarPulseScale = 1.6
            }
        }
    }

    private var cyberGridOverlay: some View {
        Canvas { context, size in
            let step: CGFloat = 36
            var path = Path()
            for x in stride(from: 0, through: size.width, by: step) {
                path.move(to: CGPoint(x: x, y: 0))
                path.addLine(to: CGPoint(x: x, y: size.height))
            }
            for y in stride(from: 0, through: size.height, by: step) {
                path.move(to: CGPoint(x: 0, y: y))
                path.addLine(to: CGPoint(x: size.width, y: y))
            }
            context.stroke(path, with: .color(Color.cyan.opacity(0.04)), lineWidth: 0.8)
        }
        .ignoresSafeArea()
    }

    // MARK: - Audio Player (vivaldi_winter loop)

    private func startContinuousMusic() {
        guard let url = Bundle.main.url(forResource: "vivaldi_winter", withExtension: "mp3") else { return }
        do {
            try AVAudioSession.sharedInstance().setCategory(.playback, mode: .default, options: .mixWithOthers)
            try AVAudioSession.sharedInstance().setActive(true)
            audioPlayer = try AVAudioPlayer(contentsOf: url)
            audioPlayer?.numberOfLoops = -1
            audioPlayer?.volume = 0.85
            audioPlayer?.play()
        } catch {
            print("Matchmaking music error: \(error)")
        }
    }

    private func stopContinuousMusic() {
        audioPlayer?.stop()
        audioPlayer = nil
    }

    // MARK: - Firebase Matchmaking Engine

    private func sanitizeKey(_ value: String) -> String {
        return value
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
            .replacingOccurrences(of: #"[.#$\[\]/]"#, with: "_", options: .regularExpression)
            .replacingOccurrences(of: #"\s+"#, with: "_", options: .regularExpression)
    }

    private var queuePath: String {
        let cleanSubject = sanitizeKey(subject)
        if let top = topic, !top.trimmingCharacters(in: .whitespaces).isEmpty {
            return "\(cleanSubject)_\(sanitizeKey(top))"
        }
        return cleanSubject
    }

    private func startMatchmakingEngine() {
        let uid = session.userId > 0 ? session.userId : 94
        self.userId = uid
        self.queueUserId = "\(uid)_ios"
        self.userName = session.userName.isEmpty ? "Shashi Gupta" : session.userName
        statusMsg = "Syncing profile..."

        Task {
            await fetchUserDetailsFromServer(uid: uid)
        }
    }

    /// Mirrors Android's `fetchUserDetailsFromServer` (lines 500-530 of MatchmakingActivity.kt)
    private func fetchUserDetailsFromServer(uid: Int) async {
        guard let profileUrl = URL(string: "\(apiBaseUrl)get_profilev1.php?user_id=\(uid)&viewer_id=\(uid)") else {
            await enterQueue()
            return
        }

        var request = URLRequest(url: profileUrl)
        request.setValue("EduLabs_Android_App", forHTTPHeaderField: "User-Agent")
        request.setValue("EduLabsRTM_Secure_v1_2026", forHTTPHeaderField: "X-App-Signature")

        if let (data, _) = try? await URLSession.shared.data(for: request),
           let root = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] {
            let dataObj = (root["data"] as? [String: Any]) ?? root
            if let fetchedName = dataObj["name"] as? String, !fetchedName.trimmingCharacters(in: .whitespaces).isEmpty {
                await MainActor.run {
                    self.userName = fetchedName
                    let rank = (dataObj["rank_title"] as? String) ?? "MASTER"
                    let user = User(id: uid, name: fetchedName, email: session.currentUser?.email ?? "shashiguptaazm@gmail.com", course: rank)
                    session.updateProfile(user)
                }
                RemoteLogger.log(tag: "Matchmaking_Profile_Loaded", message: "Authoritative name loaded: \(fetchedName)")
            }
        }

        await enterQueue()
    }

    private func enterQueue() async {
        await MainActor.run {
            statusMsg = "Joining Queue..."
        }
        queueId = "\(queueUserId)_\(Int(Date().timeIntervalSince1970 * 1000))"

        let myPlayer = QueuePlayer(queueKey: queueId, userId: queueUserId, userName: userName)
        await MainActor.run {
            self.playersInLobby = [myPlayer]
        }

        let entry: [String: Any] = [
            "userId": queueUserId,
            "userName": userName,
            "subject": subject,
            "topic": topic ?? "",
            "timestamp": Int(Date().timeIntervalSince1970 * 1000),
            "status": "waiting",
            "challengeId": ""
        ]

        do {
            try await FirebaseRTDB.shared.put(path: "matchmaking_queue/\(queuePath)/entries/\(queueId)", payload: entry)
            RemoteLogger.log(tag: "Matchmaking_Queue_Entered", message: "Entered queue \(queuePath) with queueId \(queueId)")
            await claimHostRole()
        } catch {
            RemoteLogger.log(tag: "Matchmaking_Queue_Error", message: error.localizedDescription)
            await MainActor.run {
                statusMsg = "Queue connection error, switching to bot..."
            }
            await pairWithBot()
        }
    }

    private func claimHostRole() async {
        do {
            let existing = try await FirebaseRTDB.shared.get(path: "matchmaking_queue/\(queuePath)/hostLock") as? [String: Any]
            let now = Int(Date().timeIntervalSince1970 * 1000)
            let createdAt = existing?["createdAt"] as? Int ?? 0

            let lockExpired = (now - createdAt) > 45_000
            if existing == nil || lockExpired {
                let lockPayload: [String: Any] = [
                    "queueId": queueId,
                    "userId": queueUserId,
                    "userName": userName,
                    "createdAt": now
                ]
                try await FirebaseRTDB.shared.put(path: "matchmaking_queue/\(queuePath)/hostLock", payload: lockPayload)

                isHost = true
                statusMsg = "Waiting for players..."
                startHostCountdown()
                startLobbyPolling()
            } else {
                isHost = false
                statusMsg = "Searching for match..."
                startLobbyPolling()
            }
        } catch {
            isHost = false
            startLobbyPolling()
        }
    }

    // MARK: - Host Timer & Polling

    private func startHostCountdown() {
        countdownRemaining = 30
        timerMsg = "Starting in: \(countdownRemaining)s"

        countdownTimer?.invalidate()
        countdownTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [self] timer in
            if countdownRemaining > 1 {
                countdownRemaining -= 1
                timerMsg = "Starting in: \(countdownRemaining)s"
            } else {
                timer.invalidate()
                timerMsg = ""
                // Countdown expired: Pair with bot fallback!
                Task {
                    await pairWithBot()
                }
            }
        }
    }

    private func startLobbyPolling() {
        pollingTask?.cancel()
        pollingTask = Task {
            var guestAttempts = 0
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 1_500_000_000)
                guard !Task.isCancelled else { break }

                // 1. Check if our queue entry was marked 'matched' by another host
                if let myEntry = try? await FirebaseRTDB.shared.get(path: "matchmaking_queue/\(queuePath)/entries/\(queueId)") as? [String: Any],
                   (myEntry["status"] as? String) == "matched",
                   let cId = myEntry["challengeId"] as? String, !cId.isEmpty {
                    pollingTask?.cancel()
                    countdownTimer?.invalidate()
                    self.challengeId = cId
                    self.isHost = false
                    RemoteLogger.log(tag: "Matchmaking_Matched_As_Guest", message: "Assigned challenge: \(cId)")
                    await waitForChallengeReady(cid: cId)
                    break
                }

                // 2. Fetch all entries in queue to detect other real players
                if let entriesDict = try? await FirebaseRTDB.shared.get(path: "matchmaking_queue/\(queuePath)/entries") as? [String: [String: Any]] {
                    var activePlayers: [QueuePlayer] = [
                        QueuePlayer(queueKey: queueId, userId: queueUserId, userName: userName)
                    ]

                    for (k, v) in entriesDict {
                        if k == queueId { continue }
                        if (v["status"] as? String) == "waiting" {
                            let uId = v["userId"] as? String ?? ""
                            let uName = v["userName"] as? String ?? "Player"
                            activePlayers.append(QueuePlayer(queueKey: k, userId: uId, userName: uName))
                        }
                    }

                    await MainActor.run {
                        self.playersInLobby = activePlayers
                    }

                    // If 2 or more distinct real players in lobby!
                    if activePlayers.count >= 2 {
                        pollingTask?.cancel()
                        countdownTimer?.invalidate()

                        // Deterministic tie-breaker matching Android
                        let sortedPair = Array(activePlayers.sorted { $0.queueKey < $1.queueKey }.prefix(2))
                        let deterministicCid = "pvp_\(sanitizeKey(sortedPair[0].queueKey))_\(sanitizeKey(sortedPair[1].queueKey))"

                        RemoteLogger.log(tag: "Matchmaking_TieBreaker", message: "Canonical host is \(sortedPair[0].queueKey), cid=\(deterministicCid)")

                        let amIHost = (sortedPair[0].queueKey == queueId)
                        if amIHost {
                            // This device is the canonical host!
                            self.isHost = true
                            await createMultiplayerChallenge(challengeId: deterministicCid, opponent: sortedPair[1])
                        } else {
                            // This device is guest
                            self.isHost = false
                            self.challengeId = deterministicCid
                            await waitForChallengeReady(cid: deterministicCid)
                        }
                        break
                    }
                }

                // If non-host guest waits without match for > 20s, pair with bot
                if !isHost {
                    guestAttempts += 1
                    if guestAttempts > 35 {
                        pollingTask?.cancel()
                        await pairWithBot()
                        break
                    }
                }
            }
        }
    }

    private func createMultiplayerChallenge(challengeId: String, opponent: QueuePlayer) async {
        isBotMatch = false
        self.challengeId = challengeId
        self.opponentId = opponent.userId
        self.opponentName = opponent.userName

        statusMsg = "Preparing battle questions..."
        let qIds = await fetchQuestionIds()
        self.sharedQuestionIds = qIds

        let challengePayload: [String: Any] = [
            "status": "ready",
            "subject": subject,
            "topic": topic ?? "",
            "hostId": queueUserId,
            "isBotMatch": false,
            "question_ids": qIds,
            "players": [
                queueUserId: ["name": userName, "hp": 100, "score": 0, "isFinished": false, "isBot": false],
                opponent.userId: ["name": opponent.userName, "hp": 100, "score": 0, "isFinished": false, "isBot": false]
            ]
        ]

        do {
            try await FirebaseRTDB.shared.put(path: "challenges/\(challengeId)", payload: challengePayload)

            // Mark queue entries as matched
            for pKey in [queueId, opponent.queueKey] {
                try await FirebaseRTDB.shared.patch(
                    path: "matchmaking_queue/\(queuePath)/entries/\(pKey)",
                    payload: ["status": "matched", "challengeId": challengeId]
                )
            }

            RemoteLogger.log(tag: "Matchmaking_Challenge_Ready", message: "Challenge \(challengeId) created with \(qIds.count) questions")
            await MainActor.run {
                self.countdownTimer?.invalidate()
                self.statusMsg = "⚔ Match Found: \(self.opponentName)!"
                self.timerMsg = "Entering Battle Arena..."
                self.showMatchReadyDialog = true
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) {
                    if !self.isLaunchingGame {
                        self.launchGame()
                    }
                }
            }
        } catch {
            RemoteLogger.log(tag: "Matchmaking_Create_Error", message: error.localizedDescription)
            await pairWithBot()
        }
    }

    private func pairWithBot() async {
        isBotMatch = true
        let botPool = ["Dr. Vihaan", "Dr. Ayesha", "Dr. Rohan", "Dr. Neha", "Dr. Arjun", "Dr. Kavya", "Dr. Kabir", "Dr. Ananya"]
        opponentName = botPool.randomElement() ?? "Dr. AI Challenger"
        opponentId = "BOT_\(Int.random(in: 100...999))"
        challengeId = "bot_\(Int(Date().timeIntervalSince1970 * 1000))"

        let qIds = await fetchQuestionIds()
        self.sharedQuestionIds = qIds

        await MainActor.run {
            self.showMatchReadyDialog = true
        }
    }

    private func waitForChallengeReady(cid: String) async {
        statusMsg = "Joining opponent's arena..."
        for _ in 0..<45 {
            try? await Task.sleep(nanoseconds: 1_000_000_000)
            if let obj = try? await FirebaseRTDB.shared.get(path: "challenges/\(cid)") as? [String: Any] {
                let st = obj["status"] as? String ?? ""
                if st == "ready" || st == "started" {
                    if let players = obj["players"] as? [String: [String: Any]] {
                        for (uid, info) in players where uid != queueUserId && uid != queueId {
                            self.opponentId = uid
                            self.opponentName = info["name"] as? String ?? "Opponent"
                            self.isBotMatch = false
                            break
                        }
                    }

                    if let qIds = obj["question_ids"] as? [Int] {
                        self.sharedQuestionIds = qIds
                    }

                    RemoteLogger.log(tag: "Matchmaking_Guest_Joined", message: "Joined ready challenge \(cid) vs \(opponentName) (status=\(st))")
                    await MainActor.run {
                        self.countdownTimer?.invalidate()
                        self.statusMsg = "⚔ Match Found: \(self.opponentName)!"
                        self.timerMsg = "Entering Battle Arena..."
                        self.showMatchReadyDialog = true
                        DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) {
                            if !self.isLaunchingGame {
                                self.launchGame()
                            }
                        }
                    }
                    return
                }
            }
        }

        // Fallback if host abandoned
        await pairWithBot()
    }

    private func fetchQuestionIds() async -> [Int] {
        let cleanSub = subject.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "NEET_PG"
        var urlStr = "\(apiBaseUrl)api/getQuestions.php?subject=\(cleanSub)&user_id=\(userId)"
        if let top = topic, !top.isEmpty {
            let cleanTopic = top.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""
            urlStr += "&topic=\(cleanTopic)"
        }
        guard let url = URL(string: urlStr),
              let (data, _) = try? await URLSession.shared.data(from: url),
              let json = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
              let arr = json["all_question_ids"] as? [Int], !arr.isEmpty else {
            return Array(201...215).shuffled()
        }
        return Array(arr.shuffled().prefix(15))
    }

    // MARK: - Game Launch

    private func launchGame() {
        guard !isLaunchingGame else { return }
        isLaunchingGame = true
        stopContinuousMusic()
        cleanupQueue()

        onLaunchGame?(
            challengeId,
            isHost,
            isBotMatch,
            opponentId,
            opponentName,
            sharedQuestionIds
        )
    }

    private func handleCancelSearch() {
        stopContinuousMusic()
        cleanupQueue()
        dismiss()
    }

    private func cleanupQueue() {
        countdownTimer?.invalidate()
        countdownTimer = nil
        pollingTask?.cancel()
        pollingTask = nil

        // Clean queue entry & lock from Firebase RTDB in background
        if !queueId.isEmpty {
            let qPath = queuePath
            let qId = queueId
            let wasHost = isHost
            Task.detached {
                try? await FirebaseRTDB.shared.delete(path: "matchmaking_queue/\(qPath)/entries/\(qId)")
                if wasHost {
                    try? await FirebaseRTDB.shared.delete(path: "matchmaking_queue/\(qPath)/hostLock")
                }
            }
        }
    }
}
