import SwiftUI
import AVFoundation

/// 1:1 SwiftUI replication of Android's `MatchmakingActivity.kt`.
///
/// Features:
/// - Continuous background classical audio (`vivaldi_winter.mp3` loop).
/// - Holographic cyber radar scanning animation with rotating sweep gradient and pulsing rings.
/// - Firebase Realtime Database queue integration (`matchmaking_queue/{subject}_{topic}/entries`).
/// - 30-second countdown timer for host matchmaking with automated bot fallback pairing.
/// - Live "Players in Lobby" list.
/// - "⚔ Match Ready!" modal with instant "Fight!" launch into `LoadingActivity`.
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

    @State private var showMatchReadyDialog: Bool = false
    @State private var radarRotation: Double = 0
    @State private var radarPulseScale: CGFloat = 1.0

    // ─── Audio ───────────────────────────────────────────────────────────────
    @State private var audioPlayer: AVAudioPlayer? = nil

    // ─── Timers & Tasks ───────────────────────────────────────────────────────
    @State private var countdownRemaining: Int = 30
    @State private var countdownTimer: Timer? = nil
    @State private var pollingTask: Task<Void, Never>? = nil

    private let dbBaseUrl = "https://medigyaan-11cba-default-rtdb.firebaseio.com"
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
        let uid = session.userId > 0 ? session.userId : Int.random(in: 1000...9999)
        let name = session.currentUser?.name.isEmpty == false ? (session.currentUser?.name ?? "Player") : "Doctor \(uid)"
        queueId = "\(uid)_\(Int(Date().timeIntervalSince1970 * 1000))"

        statusMsg = "Syncing profile..."

        let myPlayer = QueuePlayer(queueKey: queueId, userId: String(uid), userName: name)
        playersInLobby = [myPlayer]

        Task {
            await enterQueue(uid: uid, name: name)
        }
    }

    private func enterQueue(uid: Int, name: String) async {
        statusMsg = "Joining Queue..."

        let queueUrl = URL(string: "\(dbBaseUrl)/matchmaking_queue/\(queuePath)/entries/\(queueId).json")!
        let entry: [String: Any] = [
            "userId": String(uid),
            "userName": name,
            "subject": subject,
            "topic": topic ?? "",
            "timestamp": Int(Date().timeIntervalSince1970 * 1000),
            "status": "waiting",
            "challengeId": ""
        ]

        var request = URLRequest(url: queueUrl)
        request.httpMethod = "PUT"
        request.httpBody = try? JSONSerialization.data(withJSONObject: entry)

        do {
            _ = try await URLSession.shared.data(for: request)
            await claimHostRole(uid: uid, name: name)
        } catch {
            statusMsg = "Simulating queue connection…"
            await fallbackLocalMatchmaking(uid: uid, name: name)
        }
    }

    private func claimHostRole(uid: Int, name: String) async {
        let lockUrl = URL(string: "\(dbBaseUrl)/matchmaking_queue/\(queuePath)/hostLock.json")!

        // Read current lock
        do {
            let (data, _) = try await URLSession.shared.data(from: lockUrl)
            let existing = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
            let now = Int(Date().timeIntervalSince1970 * 1000)
            let createdAt = existing?["createdAt"] as? Int ?? 0

            let lockExpired = (now - createdAt) > 45_000
            if existing == nil || lockExpired {
                // Claim lock as Host
                var req = URLRequest(url: lockUrl)
                req.httpMethod = "PUT"
                let lockPayload: [String: Any] = [
                    "queueId": queueId,
                    "userId": String(uid),
                    "userName": name,
                    "createdAt": now
                ]
                req.httpBody = try? JSONSerialization.data(withJSONObject: lockPayload)
                _ = try await URLSession.shared.data(for: req)

                isHost = true
                statusMsg = "Waiting for players..."
                startHostCountdown()
                startHostPolling()
            } else {
                // Guest Flow
                isHost = false
                statusMsg = "Searching for match..."
                startGuestPolling()
            }
        } catch {
            await fallbackLocalMatchmaking(uid: uid, name: name)
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

    private func startHostPolling() {
        pollingTask?.cancel()
        pollingTask = Task {
            let entriesUrl = URL(string: "\(dbBaseUrl)/matchmaking_queue/\(queuePath)/entries.json")!
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 1_800_000_000)
                guard !Task.isCancelled else { break }

                if let (data, _) = try? await URLSession.shared.data(from: entriesUrl),
                   let entriesDict = (try? JSONSerialization.jsonObject(with: data)) as? [String: [String: Any]] {

                    var activePlayers: [QueuePlayer] = []
                    for (k, v) in entriesDict {
                        if (v["status"] as? String) == "waiting" {
                            let uId = v["userId"] as? String ?? ""
                            let uName = v["userName"] as? String ?? "Doctor"
                            activePlayers.append(QueuePlayer(queueKey: k, userId: uId, userName: uName))
                        }
                    }

                    await MainActor.run {
                        if !activePlayers.isEmpty {
                            self.playersInLobby = activePlayers
                        }
                    }

                    // If 2 or more real players found in lobby!
                    let distinct = activePlayers.filter { $0.userId != String(session.userId) }
                    if let firstOpponent = distinct.first {
                        pollingTask?.cancel()
                        countdownTimer?.invalidate()
                        await createMultiplayerChallenge(opponent: firstOpponent)
                        break
                    }
                }
            }
        }
    }

    private func startGuestPolling() {
        pollingTask?.cancel()
        pollingTask = Task {
            let myEntryUrl = URL(string: "\(dbBaseUrl)/matchmaking_queue/\(queuePath)/entries/\(queueId).json")!
            var attempts = 0
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 1_800_000_000)
                attempts += 1
                guard !Task.isCancelled else { break }

                if let (data, _) = try? await URLSession.shared.data(from: myEntryUrl),
                   let entry = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
                   (entry["status"] as? String) == "matched",
                   let cId = entry["challengeId"] as? String, !cId.isEmpty {
                    pollingTask?.cancel()
                    self.challengeId = cId
                    await waitForChallengeReady(cid: cId)
                    break
                }

                // If guest waits more than 16 seconds without host, pair with bot
                if attempts > 8 {
                    pollingTask?.cancel()
                    await pairWithBot()
                    break
                }
            }
        }
    }

    private func createMultiplayerChallenge(opponent: QueuePlayer) async {
        isBotMatch = false
        opponentId = opponent.userId
        opponentName = opponent.userName
        challengeId = "pvp_\(sanitizeKey(queueId))_\(sanitizeKey(opponent.queueKey))"

        statusMsg = "Preparing battle questions..."
        let qIds = await fetchQuestionIds()
        self.sharedQuestionIds = qIds

        let challengeUrl = URL(string: "\(dbBaseUrl)/challenges/\(challengeId).json")!
        let challengePayload: [String: Any] = [
            "status": "ready",
            "subject": subject,
            "topic": topic ?? "",
            "hostId": String(session.userId),
            "isBotMatch": false,
            "question_ids": qIds,
            "players": [
                String(session.userId): ["name": session.currentUser?.name ?? "Player", "hp": 100, "score": 0, "isFinished": false, "isBot": false],
                opponent.userId: ["name": opponent.userName, "hp": 100, "score": 0, "isFinished": false, "isBot": false]
            ]
        ]

        var req = URLRequest(url: challengeUrl)
        req.httpMethod = "PUT"
        req.httpBody = try? JSONSerialization.data(withJSONObject: challengePayload)
        _ = try? await URLSession.shared.data(for: req)

        // Mark entries as matched
        for p in [queueId, opponent.queueKey] {
            let pUrl = URL(string: "\(dbBaseUrl)/matchmaking_queue/\(queuePath)/entries/\(p).json")!
            var pReq = URLRequest(url: pUrl)
            pReq.httpMethod = "PATCH"
            pReq.httpBody = try? JSONSerialization.data(withJSONObject: ["status": "matched", "challengeId": challengeId])
            _ = try? await URLSession.shared.data(for: pReq)
        }

        await MainActor.run {
            self.showMatchReadyDialog = true
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
        let challengeUrl = URL(string: "\(dbBaseUrl)/challenges/\(cid).json")!
        for _ in 0..<10 {
            try? await Task.sleep(nanoseconds: 1_000_000_000)
            if let (data, _) = try? await URLSession.shared.data(from: challengeUrl),
               let obj = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
               (obj["status"] as? String) == "ready" {

                if let players = obj["players"] as? [String: [String: Any]] {
                    for (uid, info) in players where uid != String(session.userId) {
                        self.opponentId = uid
                        self.opponentName = info["name"] as? String ?? "Opponent"
                    }
                }

                if let qIds = obj["question_ids"] as? [Int] {
                    self.sharedQuestionIds = qIds
                }

                await MainActor.run {
                    self.showMatchReadyDialog = true
                }
                return
            }
        }
    }

    private func fallbackLocalMatchmaking(uid: Int, name: String) async {
        try? await Task.sleep(nanoseconds: 2_500_000_000)
        await pairWithBot()
    }

    private func fetchQuestionIds() async -> [Int] {
        let cleanSub = subject.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "NEET_PG"
        var urlStr = "\(apiBaseUrl)api/getQuestions.php?subject=\(cleanSub)&user_id=\(session.userId)"
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
                let entryUrl = URL(string: "\(dbBaseUrl)/matchmaking_queue/\(qPath)/entries/\(qId).json")!
                var req = URLRequest(url: entryUrl)
                req.httpMethod = "DELETE"
                _ = try? await URLSession.shared.data(for: req)

                if wasHost {
                    let lockUrl = URL(string: "\(dbBaseUrl)/matchmaking_queue/\(qPath)/hostLock.json")!
                    var lockReq = URLRequest(url: lockUrl)
                    lockReq.httpMethod = "DELETE"
                    _ = try? await URLSession.shared.data(for: lockReq)
                }
            }
        }
    }
}
