import SwiftUI

/// 1:1 SwiftUI port of Android's `TopicChallengeSelectionActivity.kt`.
///
/// Features:
/// - Search users across MediGyaan via `api/searchv2.php?keyword=<q>&type=json`
/// - Load followed/connected friends via `messenger_api.php?get_connections&user_id=<userId>`
/// - Multi-select checkboxes for friends to invite
/// - "Send Challenge (N)" action button
/// - Initiates challenge on VPS via `initiate_challenge.php`
/// - Creates real-time Firebase RTDB lobby `lobbies/lobby_<challengeId>`
/// - Generates invite share link (`https://medigyaan.com/Neurons/livebattle.php?challenge_id=<id>`)
/// - Navigates directly into `BattleLobbyView` to await challengers and launch 15-question topic battle
struct TopicChallengeSelectionView: View {

    let subject: String
    let topic: String

    @EnvironmentObject private var session: SessionStore
    @Environment(\.dismiss) private var dismiss

    @State private var searchQuery: String = ""
    @State private var usersList: [ChallengeUserItem] = []
    @State private var selectedUserIds: Set<String> = []
    @State private var isLoading: Bool = false
    @State private var isInitiating: Bool = false
    @State private var errorMessage: String? = nil

    @State private var createdLobbyId: String? = nil
    @State private var navigateToLobby: Bool = false
    @State private var showShareSheet: Bool = false
    @State private var shareText: String = ""

    private let apiBaseUrl = "https://medigyaan.com/Neurons/"

    var body: some View {
        ZStack {
            AppTheme.Palette.background.ignoresSafeArea()

            VStack(spacing: 0) {
                // Header with Subject & Topic
                headerSection

                // Search Bar
                searchBarSection

                // User / Connections List
                if isLoading && usersList.isEmpty {
                    VStack(spacing: 12) {
                        Spacer()
                        ProgressView()
                            .tint(AppTheme.Palette.primary)
                            .scaleEffect(1.2)
                        Text("Loading peers & connections...")
                            .font(AppTheme.Font.subheadline)
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                        Spacer()
                    }
                } else if usersList.isEmpty {
                    emptyStateSection
                } else {
                    userListSection
                }

                // Sticky Bottom Action Bar
                bottomActionBar
            }

            if isInitiating {
                Color.black.opacity(0.6).ignoresSafeArea()
                VStack(spacing: 16) {
                    ProgressView()
                        .tint(Color.yellow)
                        .scaleEffect(1.5)
                    Text("Creating Battle Lobby...")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundStyle(Color.white)
                }
                .padding(28)
                .background(RoundedRectangle(cornerRadius: 16).fill(Color(hex: "#0F172A")))
            }
        }
        .navigationTitle("Challenge Friends")
        .navigationBarTitleDisplayMode(.inline)
        .navigationDestination(isPresented: $navigateToLobby) {
            if let lobbyId = createdLobbyId {
                BattleLobbyView(
                    lobbyId: lobbyId,
                    subject: subject,
                    topicName: topic,
                    isHost: true
                )
            }
        }
        .sheet(isPresented: $showShareSheet) {
            ShareActivitySheet(activityItems: [shareText])
        }
        .task {
            await loadSavedConnections()
        }
    }

    // MARK: - Header Section

    private var headerSection: some View {
        VStack(spacing: 6) {
            HStack(spacing: 8) {
                HStack(spacing: 4) {
                    Image(systemName: "book.fill")
                        .font(.system(size: 11))
                    Text(subject.isEmpty ? "NEET PG" : subject)
                        .font(.system(size: 11, weight: .bold))
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Capsule().fill(Color.blue.opacity(0.18)))
                .foregroundStyle(Color(hex: "#00E5FF"))

                if !topic.isEmpty {
                    HStack(spacing: 4) {
                        Image(systemName: "tag.fill")
                            .font(.system(size: 11))
                        Text(topic)
                            .font(.system(size: 11, weight: .bold))
                            .lineLimit(1)
                    }
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Capsule().fill(Color.orange.opacity(0.18)))
                    .foregroundStyle(Color.orange)
                }
            }

            Text("Select friends to challenge with 15 shuffled topic questions")
                .font(.system(size: 12))
                .foregroundStyle(AppTheme.Palette.textSecondary)
                .multilineTextAlignment(.center)
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.top, 10)
        .padding(.bottom, 8)
    }

    // MARK: - Search Bar Section

    private var searchBarSection: some View {
        HStack(spacing: 10) {
            Image(systemName: "magnifyingglass")
                .foregroundStyle(AppTheme.Palette.textSecondary)

            TextField("Search medical peers by name...", text: $searchQuery)
                .font(.system(size: 14))
                .foregroundStyle(Color.white)
                .autocapitalization(.none)
                .disableAutocorrection(true)
                .onSubmit {
                    Task { await performSearch() }
                }

            if !searchQuery.isEmpty {
                Button {
                    searchQuery = ""
                    Task { await loadSavedConnections() }
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(hex: "#101D33"))
                .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.white.opacity(0.08), lineWidth: 1))
        )
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.bottom, 10)
    }

    // MARK: - User List Section

    private var userListSection: some View {
        ScrollView {
            LazyVStack(spacing: 8) {
                ForEach(usersList) { user in
                    let isSelected = selectedUserIds.contains(user.id)
                    Button {
                        if isSelected {
                            selectedUserIds.remove(user.id)
                        } else {
                            selectedUserIds.insert(user.id)
                        }
                    } label: {
                        HStack(spacing: 12) {
                            // Avatar
                            AsyncImage(url: URL(string: user.photo)) { phase in
                                switch phase {
                                case .success(let image):
                                    image
                                        .resizable()
                                        .aspectRatio(contentMode: .fill)
                                        .frame(width: 44, height: 44)
                                        .clipShape(Circle())
                                default:
                                    Circle()
                                        .fill(Color(hex: "#1E293B"))
                                        .frame(width: 44, height: 44)
                                        .overlay(
                                            Image(systemName: "person.fill")
                                                .foregroundStyle(Color.gray)
                                        )
                                }
                            }

                            // Name & Status
                            VStack(alignment: .leading, spacing: 3) {
                                Text(user.name)
                                    .font(.system(size: 15, weight: .semibold))
                                    .foregroundStyle(Color.white)
                                    .lineLimit(1)

                                Text(user.isCloseFriend ? "Connected Peer" : "Medical Scholar")
                                    .font(.system(size: 11))
                                    .foregroundStyle(user.isCloseFriend ? Color.green.opacity(0.8) : Color.gray)
                            }

                            Spacer()

                            // Checkbox
                            ZStack {
                                Circle()
                                    .fill(isSelected ? Color(hex: "#00E5FF") : Color.clear)
                                    .frame(width: 26, height: 26)
                                    .overlay(
                                        Circle().stroke(isSelected ? Color(hex: "#00E5FF") : Color.gray.opacity(0.5), lineWidth: 1.5)
                                    )

                                if isSelected {
                                    Image(systemName: "checkmark")
                                        .font(.system(size: 13, weight: .black))
                                        .foregroundStyle(Color.black)
                                }
                            }
                        }
                        .padding(.horizontal, 14)
                        .padding(.vertical, 10)
                        .background(
                            RoundedRectangle(cornerRadius: 14)
                                .fill(isSelected ? Color(hex: "#0A2540") : Color(hex: "#0C1527"))
                                .overlay(
                                    RoundedRectangle(cornerRadius: 14)
                                        .stroke(isSelected ? Color(hex: "#00E5FF").opacity(0.4) : Color.white.opacity(0.04), lineWidth: 1)
                                )
                        )
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, AppTheme.Spacing.md)
            .padding(.bottom, 16)
        }
    }

    // MARK: - Empty State

    private var emptyStateSection: some View {
        VStack(spacing: 12) {
            Spacer()
            Image(systemName: "person.2.slash")
                .font(.system(size: 48))
                .foregroundStyle(Color.gray.opacity(0.5))

            Text("No peers found")
                .font(.system(size: 16, weight: .bold))
                .foregroundStyle(Color.white)

            Text("Search by name above to find doctors & peers to challenge.")
                .font(.system(size: 13))
                .foregroundStyle(AppTheme.Palette.textSecondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)
            Spacer()
        }
    }

    // MARK: - Sticky Bottom Action Bar

    private var bottomActionBar: some View {
        VStack(spacing: 0) {
            Divider().background(Color.white.opacity(0.1))

            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(selectedUserIds.isEmpty ? "No opponents selected" : "\(selectedUserIds.count) selected")
                        .font(.system(size: 13, weight: .bold))
                        .foregroundStyle(selectedUserIds.isEmpty ? Color.gray : Color(hex: "#00E5FF"))

                    Text("15 Shuffled Questions")
                        .font(.system(size: 11))
                        .foregroundStyle(Color.gray)
                }

                Spacer()

                Button {
                    Task { await sendFriendChallenge() }
                } label: {
                    HStack(spacing: 6) {
                        Image(systemName: "bolt.fill")
                        Text(selectedUserIds.isEmpty ? "Select Opponent" : "Send Challenge (\(selectedUserIds.count))")
                            .font(.system(size: 15, weight: .black))
                    }
                    .foregroundStyle(selectedUserIds.isEmpty ? Color.gray : Color.black)
                    .padding(.horizontal, 20)
                    .padding(.vertical, 12)
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .fill(selectedUserIds.isEmpty ? Color.gray.opacity(0.3) : Color(hex: "#00E5FF"))
                    )
                }
                .disabled(selectedUserIds.isEmpty || isInitiating)
            }
            .padding(.horizontal, AppTheme.Spacing.md)
            .padding(.vertical, 12)
            .background(Color(hex: "#060A14"))
        }
    }

    // MARK: - API & Networking

    @MainActor
    private func loadSavedConnections() async {
        isLoading = true
        defer { isLoading = false }

        let myId = session.userId
        guard myId > 0, let url = URL(string: "\(apiBaseUrl)messenger_api.php?get_connections&user_id=\(myId)") else {
            return
        }

        var request = URLRequest(url: url)
        request.setValue("EduLabs_Android_App", forHTTPHeaderField: "User-Agent")
        request.setValue("EduLabsRTM_Secure_v1_2026", forHTTPHeaderField: "X-App-Signature")
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard (response as? HTTPURLResponse)?.statusCode == 200 else { return }

            if let jsonArray = try? JSONSerialization.jsonObject(with: data) as? [[String: Any]] {
                var items: [ChallengeUserItem] = []
                for obj in jsonArray {
                    let rawId = "\(obj["user_id"] ?? "")"
                    if rawId.isEmpty || rawId == "\(myId)" { continue }
                    let name = (obj["name"] as? String)?.isEmpty == false ? (obj["name"] as! String) : "Peer \(rawId)"

                    var photo = (obj["photo"] as? String) ?? (obj["profile_pic"] as? String) ?? ""
                    if photo.isEmpty || photo == "null" { photo = "Default.jpg" }
                    if !photo.starts(with: "http") {
                        photo = "\(apiBaseUrl)\(photo.trimmingCharacters(in: CharacterSet(charactersIn: "./")))"
                    }

                    items.append(ChallengeUserItem(id: rawId, name: name, photo: photo, isCloseFriend: true))
                }
                self.usersList = items
                RemoteLogger.log(tag: "TopicChallenge_Connections_Loaded", message: "Loaded \(items.count) connections for user \(myId)")
            }
        } catch {
            RemoteLogger.log(tag: "TopicChallenge_Connections_Error", message: error.localizedDescription)
        }
    }

    @MainActor
    private func performSearch() async {
        let q = searchQuery.trimmingCharacters(in: .whitespaces)
        guard !q.isEmpty else {
            await loadSavedConnections()
            return
        }

        isLoading = true
        defer { isLoading = false }

        let encoded = q.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? q
        guard let url = URL(string: "\(apiBaseUrl)api/searchv2.php?keyword=\(encoded)&type=json") else { return }

        var request = URLRequest(url: url)
        request.setValue("EduLabs_Android_App", forHTTPHeaderField: "User-Agent")
        request.setValue("EduLabsRTM_Secure_v1_2026", forHTTPHeaderField: "X-App-Signature")

        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard (response as? HTTPURLResponse)?.statusCode == 200 else { return }

            if let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let results = root["results"] as? [String: Any],
               let usersArr = results["users"] as? [[String: Any]] {
                var items: [ChallengeUserItem] = []
                for obj in usersArr {
                    let rawId = "\(obj["user_id"] ?? "")"
                    if rawId.isEmpty || rawId == "\(session.userId)" { continue }
                    let name = (obj["name"] as? String) ?? "User"

                    var photo = (obj["photo"] as? String) ?? ""
                    if !photo.isEmpty && !photo.starts(with: "http") {
                        photo = "\(apiBaseUrl)\(photo)"
                    }

                    items.append(ChallengeUserItem(id: rawId, name: name, photo: photo, isCloseFriend: false))
                }
                self.usersList = items
                RemoteLogger.log(tag: "TopicChallenge_Search_Loaded", message: "Found \(items.count) users for query '\(q)'")
            }
        } catch {
            RemoteLogger.log(tag: "TopicChallenge_Search_Error", message: error.localizedDescription)
        }
    }

    @MainActor
    private func sendFriendChallenge() async {
        guard !selectedUserIds.isEmpty else { return }
        isInitiating = true
        defer { isInitiating = false }

        let myId = session.userId
        let myName = session.currentUser?.name ?? "Host"
        let opponents = selectedUserIds.joined(separator: ",")
        let quizId = abs("\(subject.trimmingCharacters(in: .whitespaces))_\(topic.trimmingCharacters(in: .whitespaces))".hashValue)

        guard let url = URL(string: "\(apiBaseUrl)initiate_challenge.php") else { return }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("EduLabsRTM_Secure_v1_2026", forHTTPHeaderField: "X-App-Signature")
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")

        let postBody = "creator_id=\(myId)&quiz_id=\(quizId)&quiz_type=CUSTOM&opponent_ids=\(opponents)"
        request.httpBody = postBody.data(using: .utf8)

        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard (response as? HTTPURLResponse)?.statusCode == 200,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let challengeIdNum = json["challenge_id"] as? Int,
                  challengeIdNum > 0 else {
                errorMessage = "Failed to create challenge"
                return
            }

            let challengeId = "\(challengeIdNum)"
            let lobbyId = "lobby_\(challengeId)"

            // Create Firebase RTDB Lobby
            let lobbyPayload: [String: Any] = [
                "status": "waiting",
                "host_id": "\(myId)",
                "challenge_id": challengeIdNum,
                "subject": subject,
                "topic": topic,
                "quiz_type": "CUSTOM",
                "quiz_id": quizId,
                "players": [
                    "\(myId)": [
                        "name": myName,
                        "status": "ready"
                    ]
                ]
            ]

            try await FirebaseRTDB.shared.put(path: "lobbies/\(lobbyId)", payload: lobbyPayload)

            // Setup Invite Text & Link
            let inviteLink = "\(apiBaseUrl)livebattle.php?challenge_id=\(challengeId)"
            self.shareText = """
            🔥 Challenge Invite!

            \(myName) has invited you to a live quiz battle ⚔️

            👉 Join here:
            \(inviteLink)

            📲 Open in app for best experience
            """

            RemoteLogger.log(tag: "TopicChallenge_Lobby_Created", message: "Created lobby \(lobbyId) for \(selectedUserIds.count) opponents")

            self.createdLobbyId = lobbyId
            self.showShareSheet = true
            self.navigateToLobby = true

        } catch {
            errorMessage = error.localizedDescription
            RemoteLogger.log(tag: "TopicChallenge_Initiate_Error", message: error.localizedDescription)
        }
    }
}

// MARK: - Models & Helpers

struct ChallengeUserItem: Identifiable, Equatable {
    let id: String
    let name: String
    let photo: String
    let isCloseFriend: Bool
}

struct ShareActivitySheet: UIViewControllerRepresentable {
    let activityItems: [Any]
    let applicationActivities: [UIActivity]? = nil

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: activityItems, applicationActivities: applicationActivities)
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}
