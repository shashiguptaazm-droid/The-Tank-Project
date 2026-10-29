import SwiftUI

/// iOS equivalent of Android `LobbyActivity.kt` and `TopicLobbyActivity.kt`.
///
/// Real-time battle staging arena where host and opponent ready-up,
/// display lobby pin codes, share invitations, and trigger synchronous battle start
/// with 15 shuffled topic questions routed to `SubjectTestActivityView`.
struct BattleLobbyView: View {

    let lobbyId: String
    var subject: String = "NEET PG"
    let topicName: String
    let isHost: Bool

    @EnvironmentObject private var session: SessionStore
    @Environment(\.dismiss) private var dismiss

    @State private var isReady: Bool = false
    @State private var opponentId: String = ""
    @State private var opponentName: String = "Waiting for challenger..."
    @State private var opponentAvatar: String = ""
    @State private var isOpponentReady: Bool = false
    @State private var isStartingBattle: Bool = false
    @State private var showCopiedAlert: Bool = false
    @State private var navigateToGame: Bool = false

    @State private var pollingTask: Task<Void, Never>? = nil

    private let apiBaseUrl = "https://medigyaan.com/Neurons/"

    var body: some View {
        ZStack {
            // Battle backdrop gradient
            LinearGradient(
                colors: [Color(hex: "#0F172A"), Color(hex: "#1E1B4B"), Color(hex: "#020617")],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            VStack(spacing: AppTheme.Spacing.lg) {
                // Header Arena Banner
                arenaHeader

                // 1v1 Staging Arena Versus Layout
                versusArenaStage

                // Match Metadata Card
                lobbyDetailsCard

                Spacer()

                // Bottom Action Triggers
                actionControls
            }
            .padding(AppTheme.Spacing.md)

            if isStartingBattle {
                Color.black.opacity(0.6).ignoresSafeArea()
                VStack(spacing: 14) {
                    ProgressView()
                        .tint(Color.yellow)
                        .scaleEffect(1.4)
                    Text("Preparing 15 Shuffled Battle Questions...")
                        .font(.system(size: 15, weight: .bold))
                        .foregroundStyle(Color.white)
                }
                .padding(24)
                .background(RoundedRectangle(cornerRadius: 16).fill(Color(hex: "#0C1527")))
            }
        }
        .navigationTitle("Battle Lobby")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    UIPasteboard.general.string = lobbyId
                    showCopiedAlert = true
                } label: {
                    Image(systemName: "doc.on.doc.fill")
                        .foregroundStyle(Color.yellow)
                }
            }
        }
        .alert("Lobby Code Copied!", isPresented: $showCopiedAlert) {
            Button("OK", role: .cancel) {}
        } message: {
            Text("Code: \(lobbyId)\nShare this with a friend to duel!")
        }
        .navigationDestination(isPresented: $navigateToGame) {
            SubjectTestActivityView(
                subject: subject.isEmpty ? "NEET PG" : subject,
                topic: topicName,
                challengeId: lobbyId,
                isChallenge: true,
                isHost: isHost,
                opponentId: opponentId,
                opponentName: opponentName
            )
        }
        .onAppear {
            startLobbyPolling()
        }
        .onDisappear {
            pollingTask?.cancel()
            pollingTask = nil
        }
    }

    // MARK: - Arena Header

    private var arenaHeader: some View {
        VStack(spacing: 4) {
            Text("ARENA LOBBY")
                .font(.system(size: 11, weight: .black, design: .monospaced))
                .foregroundStyle(AppTheme.Palette.textMuted)

            Text(lobbyId.isEmpty ? "ARENA-998" : lobbyId)
                .font(.system(size: 26, weight: .black, design: .monospaced))
                .foregroundStyle(Color.yellow)
                .shadow(color: Color.yellow.opacity(0.4), radius: 8)
        }
        .padding(.top, AppTheme.Spacing.sm)
    }

    // MARK: - Versus Arena Stage

    private var versusArenaStage: some View {
        CardContainer {
            HStack(spacing: 0) {
                // Host / Current User
                VStack(spacing: AppTheme.Spacing.xs) {
                    ZStack(alignment: .bottomTrailing) {
                        Circle()
                            .fill(AppTheme.Palette.primary.opacity(0.2))
                            .frame(width: 76, height: 76)

                        Image(systemName: "person.crop.circle.fill")
                            .font(.system(size: 72))
                            .foregroundStyle(AppTheme.Palette.primary)

                        Image(systemName: isReady ? "checkmark.circle.fill" : "clock.fill")
                            .font(.system(size: 20))
                            .foregroundStyle(isReady ? Color.green : Color.orange)
                            .background(Circle().fill(Color.black))
                    }

                    Text(session.currentUser?.name ?? "Host")
                        .font(AppTheme.Font.headline)
                        .foregroundStyle(AppTheme.Palette.textPrimary)
                        .lineLimit(1)

                    Text(isReady ? "READY" : "WAITING")
                        .font(.system(size: 10, weight: .black))
                        .foregroundStyle(isReady ? Color.green : Color.orange)
                }
                .frame(maxWidth: .infinity)

                // VS Crest
                ZStack {
                    Circle()
                        .fill(Color.yellow.opacity(0.12))
                        .frame(width: 44, height: 44)

                    Text("VS")
                        .font(.system(size: 18, weight: .black, design: .rounded))
                        .foregroundStyle(Color.yellow)
                }

                // Opponent
                VStack(spacing: AppTheme.Spacing.xs) {
                    ZStack(alignment: .bottomTrailing) {
                        Circle()
                            .fill(AppTheme.Palette.accent.opacity(0.2))
                            .frame(width: 76, height: 76)

                        Image(systemName: opponentId.isEmpty ? "person.crop.circle.badge.questionmark" : "person.crop.circle.fill")
                            .font(.system(size: 72))
                            .foregroundStyle(opponentId.isEmpty ? Color.gray : Color(hex: "#00E5FF"))

                        if !opponentId.isEmpty {
                            Image(systemName: isOpponentReady ? "checkmark.circle.fill" : "clock.fill")
                                .font(.system(size: 20))
                                .foregroundStyle(isOpponentReady ? Color.green : Color.orange)
                                .background(Circle().fill(Color.black))
                        }
                    }

                    Text(opponentName)
                        .font(AppTheme.Font.headline)
                        .foregroundStyle(opponentId.isEmpty ? AppTheme.Palette.textMuted : AppTheme.Palette.textPrimary)
                        .lineLimit(1)

                    Text(!opponentId.isEmpty ? (isOpponentReady ? "READY" : "STANDBY") : "INVITING")
                        .font(.system(size: 10, weight: .black))
                        .foregroundStyle(!opponentId.isEmpty ? (isOpponentReady ? Color.green : Color.orange) : Color.gray)
                }
                .frame(maxWidth: .infinity)
            }
            .padding(.vertical, AppTheme.Spacing.sm)
        }
    }

    // MARK: - Match Metadata Card

    private var lobbyDetailsCard: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                HStack {
                    Image(systemName: "book.fill")
                        .foregroundStyle(AppTheme.Palette.accent)
                    Text("Subject")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                    Spacer()
                    Text(subject.isEmpty ? "NEET PG" : subject)
                        .font(AppTheme.Font.callout.weight(.bold))
                        .foregroundStyle(AppTheme.Palette.textPrimary)
                }

                Divider().background(AppTheme.Palette.divider)

                HStack {
                    Image(systemName: "tag.fill")
                        .foregroundStyle(Color.orange)
                    Text("Topic Target")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                    Spacer()
                    Text(topicName.isEmpty ? "High-Yield Clinical" : topicName)
                        .font(AppTheme.Font.callout.weight(.bold))
                        .foregroundStyle(Color.orange)
                }

                Divider().background(AppTheme.Palette.divider)

                HStack {
                    Image(systemName: "bolt.shield.fill")
                        .foregroundStyle(Color.yellow)
                    Text("Battle Format")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                    Spacer()
                    Text("15 Shuffled Questions Duel")
                        .font(AppTheme.Font.callout.weight(.bold))
                        .foregroundStyle(Color.yellow)
                }
            }
        }
    }

    // MARK: - Action Controls

    private var actionControls: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            Button {
                isReady.toggle()
                Task {
                    try? await FirebaseRTDB.shared.patch(
                        path: "lobbies/\(lobbyId)/players/\(session.userId)",
                        payload: ["status": isReady ? "ready" : "waiting"]
                    )
                }
                RemoteLogger.log(
                    tag: "BattleLobby_Ready",
                    message: "User toggled ready state: \(isReady) (lobby: \(lobbyId), isHost: \(isHost))"
                )
            } label: {
                HStack {
                    Image(systemName: isReady ? "checkmark.circle.fill" : "bolt.circle.fill")
                    Text(isReady ? "Ready to Fight!" : "Tap When Ready")
                }
                .font(AppTheme.Font.headline)
                .foregroundStyle(Color.white)
                .frame(maxWidth: .infinity)
                .frame(height: 52)
                .background(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.md)
                        .fill(isReady ? Color.green : AppTheme.Palette.primary)
                )
            }

            if isHost {
                Button {
                    Task { await startBattleAsHost() }
                } label: {
                    Text("START BATTLE")
                        .font(.system(size: 16, weight: .black))
                        .foregroundStyle(Color.white)
                        .frame(maxWidth: .infinity)
                        .frame(height: 52)
                        .background(
                            RoundedRectangle(cornerRadius: AppTheme.Radius.md)
                                .fill(isReady && isOpponentReady ? Color.orange : Color.gray.opacity(0.4))
                        )
                }
                .disabled(!isReady || !isOpponentReady || isStartingBattle)
            }

            let shareLinkUrl = "\(apiBaseUrl)livebattle.php?challenge_id=\(lobbyId.replacingOccurrences(of: "lobby_", with: ""))"
            ShareLink(item: "Join my MediGyaan medical arena battle on '\(topicName)'!\n👉 \(shareLinkUrl)") {
                HStack {
                    Image(systemName: "square.and.arrow.up")
                    Text("Invite More Friends")
                }
                .font(AppTheme.Font.subheadline.weight(.semibold))
                .foregroundStyle(AppTheme.Palette.textSecondary)
                .frame(maxWidth: .infinity)
                .frame(height: 44)
            }
        }
    }

    // MARK: - Real-Time Firebase RTDB Synchronization

    private func startLobbyPolling() {
        pollingTask?.cancel()
        pollingTask = Task {
            let myUid = "\(session.userId)"

            // Auto-ready host on enter
            try? await FirebaseRTDB.shared.patch(
                path: "lobbies/\(lobbyId)/players/\(myUid)",
                payload: ["status": "ready", "name": session.currentUser?.name ?? "Host"]
            )
            await MainActor.run { self.isReady = true }

            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 1_200_000_000)
                guard !navigateToGame else { break }

                guard let lobbyData = try? await FirebaseRTDB.shared.get(path: "lobbies/\(lobbyId)") as? [String: Any] else {
                    continue
                }

                let status = lobbyData["status"] as? String ?? ""
                if status == "started" {
                    RemoteLogger.log(tag: "BattleLobby_Started", message: "Lobby \(lobbyId) marked started! Transitioning to battle arena...")
                    await MainActor.run {
                        self.navigateToGame = true
                    }
                    break
                }

                // Parse players
                if let playersDict = lobbyData["players"] as? [String: [String: Any]] {
                    for (pId, pData) in playersDict {
                        if pId != myUid {
                            let oppName = pData["name"] as? String ?? "Opponent"
                            let oppStatus = pData["status"] as? String ?? "waiting"
                            let isReadyFlag = (oppStatus == "ready")

                            await MainActor.run {
                                self.opponentId = pId
                                self.opponentName = oppName
                                self.isOpponentReady = isReadyFlag
                            }
                        }
                    }
                }
            }
        }
    }

    @MainActor
    private func startBattleAsHost() async {
        isStartingBattle = true
        defer { isStartingBattle = false }

        // 1. Fetch Question IDs for this Subject & Topic
        let myId = "\(session.userId)"
        let myName = session.currentUser?.name ?? "Host"
        let encSub = subject.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "NEET%20PG"
        let encTop = topicName.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""

        var qIds: [Int] = []
        if let url = URL(string: "\(apiBaseUrl)api/getQuestions.php?subject=\(encSub)&topic=\(encTop)&user_id=\(myId)") {
            var request = URLRequest(url: url)
            request.setValue("EduLabs_Android_App", forHTTPHeaderField: "User-Agent")
            request.setValue("EduLabsRTM_Secure_v1_2026", forHTTPHeaderField: "X-App-Signature")

            if let (data, response) = try? await URLSession.shared.data(for: request),
               (response as? HTTPURLResponse)?.statusCode == 200,
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let arr = json["all_question_ids"] as? [Int], !arr.isEmpty {
                qIds = arr
            }
        }

        // Shuffle & select 15 questions
        let battle15 = Array(qIds.shuffled().prefix(15))
        RemoteLogger.log(tag: "BattleLobby_Questions_Ready", message: "Selected \(battle15.count) questions for lobby \(lobbyId)")

        // 2. Write to Firebase RTDB challenges node
        let challengePayload: [String: Any] = [
            "hostId": myId,
            "status": "started",
            "subject": subject,
            "topic": topicName,
            "isBotMatch": false,
            "question_ids": battle15,
            "players": [
                myId: ["name": myName, "hp": 100, "score": 0, "isFinished": false, "isBot": false, "skin": "Axiom"],
                opponentId: ["name": opponentName, "hp": 100, "score": 0, "isFinished": false, "isBot": false, "skin": "Verdict"]
            ]
        ]

        try? await FirebaseRTDB.shared.put(path: "challenges/\(lobbyId)", payload: challengePayload)

        // 3. Mark lobby as started
        try? await FirebaseRTDB.shared.patch(
            path: "lobbies/\(lobbyId)",
            payload: ["status": "started", "challenge_id": lobbyId]
        )

        self.navigateToGame = true
    }
}
