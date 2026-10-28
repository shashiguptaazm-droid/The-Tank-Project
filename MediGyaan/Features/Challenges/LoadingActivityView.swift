import SwiftUI

/// 1:1 SwiftUI replication of Android's `LoadingActivity.kt` and `TopicLoadingActivity.kt`.
///
/// Features:
/// - Split-screen 1v1 face-off presentation (YOU vs OPPONENT) with animated entrance scaling.
/// - 3D Animal Warrior avatar presentation (authoritative 27 MediGyaan warriors) with 3-level hero zoom controls:
///   `🔍 1.0x (FIT)`, `🔍 1.35x (COMBAT)`, `🔍 1.75x (CLOSE)`.
/// - Rank title pills and badges (Aspirant, Warrior, Scholar, Master, Grandmaster).
/// - Dynamic status ticker cycling Android's 8 telemetry messages every 2.0 seconds:
///   "Preparing battle...", "Loading player data...", "Fetching opponents...", "Connecting to server...", "Analyzing skills..."
/// - Animated pulsating "VS" emblem with bounce-back animation.
/// - Calibrated loading progress bar and automatic transition into `ClassicGameActivity`.
struct LoadingActivityView: View {

    let challengeId: String
    let userId: String
    let userName: String
    let opponentId: String
    let opponentName: String
    let subject: String
    let topic: String?
    let isHost: Bool
    let isBotMatch: Bool
    let questionIds: [Int]
    var userRank: String = "Master"
    var onProceedToGame: (() -> Void)?

    @EnvironmentObject private var session: SessionStore
    @Environment(\.dismiss) private var dismiss

    // ─── Visual & Animation States ────────────────────────────────────────────
    @State private var zoomLevel: CGFloat = 1.0
    @State private var zoomPresetIndex: Int = 0
    private let zoomPresets: [CGFloat] = [1.0, 1.35, 1.75]

    @State private var playerCardScale: CGFloat = 0.0
    @State private var opponentCardScale: CGFloat = 0.0
    @State private var vsScale: CGFloat = 0.0
    @State private var loadingProgress: Double = 0.0

    // ─── Dynamic Telemetry Messages ───────────────────────────────────────────
    private let dynamicMessages = [
        "Preparing battle...",
        "Loading player data...",
        "Fetching opponents...",
        "Connecting to server...",
        "Analyzing skills...",
        "Almost ready...",
        "Loading maps...",
        "Calibrating match..."
    ]
    @State private var currentMessageIndex: Int = 0
    @State private var statusText: String = "Preparing battle..."

    // ─── Warriors ─────────────────────────────────────────────────────────────
    @State private var playerWarrior: Warrior = Warrior.all.first!
    @State private var opponentWarrior: Warrior = Warrior.all.randomElement()!
    @State private var opponentRank: String = "Warrior"

    // ─── Timers ───────────────────────────────────────────────────────────────
    private let messageTimer = Timer.publish(every: 1.8, on: .main, in: .common).autoconnect()
    private let progressTimer = Timer.publish(every: 0.1, on: .main, in: .common).autoconnect()

    var body: some View {
        ZStack {
            // Layer 1: Background Arena Backdrop
            Image("bg_battle")
                .resizable()
                .scaledToFill()
                .ignoresSafeArea()
                .overlay(
                    LinearGradient(
                        colors: [
                            Color(hex: 0x050816).opacity(0.85),
                            Color(hex: 0x0A1028).opacity(0.75),
                            Color(hex: 0x050816).opacity(0.92)
                        ],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                    .ignoresSafeArea()
                )

            // Layer 2: Main Loading Stage
            VStack(spacing: 0) {
                // Top Subject & Topic Header
                VStack(spacing: 4) {
                    Text(subject.uppercased())
                        .font(.system(size: 11, weight: .black, design: .monospaced))
                        .foregroundStyle(Color.yellow)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 4)
                        .background(Capsule().fill(Color.yellow.opacity(0.12)))

                    Text(topic?.isEmpty == false ? topic! : "Clinical Challenge Arena")
                        .font(AppTheme.Font.title3)
                        .fontWeight(.bold)
                        .foregroundStyle(Color.white)
                        .lineLimit(1)
                }
                .padding(.top, 20)

                Spacer()

                // Hero Zoom Controls Strip (Ports setupHeroZoomControls)
                heroZoomControlsBar
                    .padding(.bottom, 12)

                // Face-Off Split Stage: YOU vs OPPONENT
                HStack(spacing: 12) {
                    // Left: YOU Pod
                    playerFighterCard(
                        name: userName.isEmpty ? session.userName : userName,
                        rank: userRank,
                        warrior: playerWarrior,
                        isMe: true,
                        accentColor: Color(hex: 0x00E5FF)
                    )
                    .scaleEffect(playerCardScale)

                    // Center: Animated VS Emblem
                    vsCenterEmblem
                        .scaleEffect(vsScale)

                    // Right: OPPONENT Pod
                    playerFighterCard(
                        name: opponentName,
                        rank: opponentRank,
                        warrior: opponentWarrior,
                        isMe: false,
                        accentColor: Color(hex: 0xE040FB)
                    )
                    .scaleEffect(opponentCardScale)
                }
                .padding(.horizontal, 14)

                Spacer()

                // Status Message Ticker
                VStack(spacing: 10) {
                    Text(statusText)
                        .font(AppTheme.Font.headline)
                        .fontWeight(.bold)
                        .foregroundStyle(Color(hex: 0x00E5FF))
                        .transition(.opacity)

                    // Progress Bar
                    ZStack(alignment: .leading) {
                        Capsule()
                            .fill(Color.white.opacity(0.12))
                            .frame(height: 8)

                        Capsule()
                            .fill(
                                LinearGradient(
                                    colors: [Color(hex: 0x48D6C8), Color(hex: 0x00E5FF), Color.yellow],
                                    startPoint: .leading,
                                    endPoint: .trailing
                                )
                            )
                            .frame(width: max(16, CGFloat(loadingProgress) * 280), height: 8)
                            .animation(.linear(duration: 0.1), value: loadingProgress)
                    }
                    .frame(width: 280)
                }
                .padding(.bottom, 40)
            }
        }
        .navigationBarHidden(true)
        .onAppear {
            setupFighters()
            startEntranceAnimation()
        }
        .onReceive(messageTimer) { _ in
            currentMessageIndex = (currentMessageIndex + 1) % dynamicMessages.count
            withAnimation(.easeInOut(duration: 0.3)) {
                statusText = dynamicMessages[currentMessageIndex]
            }
        }
        .onReceive(progressTimer) { _ in
            if loadingProgress < 1.0 {
                loadingProgress += 0.025
            } else {
                statusText = "Match Confirmed! Entering Arena…"
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
                    onProceedToGame?()
                }
            }
        }
    }

    // MARK: - Fighter Pods

    private func playerFighterCard(
        name: String,
        rank: String,
        warrior: Warrior,
        isMe: Bool,
        accentColor: Color
    ) -> some View {
        VStack(spacing: 8) {
            // Rank Badge Pill
            Text(rank.uppercased())
                .font(.system(size: 9, weight: .black, design: .monospaced))
                .foregroundStyle(accentColor)
                .padding(.horizontal, 8)
                .padding(.vertical, 3)
                .background(Capsule().fill(accentColor.opacity(0.18)))

            // Avatar Container with Hero Zoom
            ZStack {
                Circle()
                    .fill(accentColor.opacity(0.12))
                    .frame(width: 90, height: 90)

                Image(warrior.avatarImageName)
                    .resizable()
                    .scaledToFit()
                    .frame(width: 80 * zoomLevel, height: 80 * zoomLevel)
                    .clipShape(Circle())
                    .scaleEffect(zoomLevel)
            }
            .frame(width: 90, height: 90)
            .clipped()

            // Name
            Text(name)
                .font(AppTheme.Font.subheadline)
                .fontWeight(.bold)
                .foregroundStyle(Color.white)
                .lineLimit(1)

            // Warrior Title & Specialty
            Text(warrior.displayName)
                .font(.system(size: 10, weight: .semibold))
                .foregroundStyle(accentColor.opacity(0.9))
                .lineLimit(1)

            // Stat Badge
            HStack(spacing: 6) {
                Label("\(warrior.vitality) HP", systemImage: "heart.fill")
                    .font(.system(size: 9, weight: .bold))
                    .foregroundStyle(Color.red.opacity(0.9))
                Label("\(warrior.assault) ATK", systemImage: "bolt.fill")
                    .font(.system(size: 9, weight: .bold))
                    .foregroundStyle(Color.yellow.opacity(0.9))
            }
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(RoundedRectangle(cornerRadius: 6).fill(Color.black.opacity(0.4)))
        }
        .padding(.vertical, 16)
        .padding(.horizontal, 10)
        .frame(maxWidth: .infinity)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color(hex: 0x111624).opacity(0.9))
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(accentColor.opacity(0.4), lineWidth: 1.5)
                )
        )
    }

    // MARK: - Center VS Emblem

    private var vsCenterEmblem: some View {
        VStack(spacing: 4) {
            ZStack {
                Circle()
                    .fill(Color.red.opacity(0.2))
                    .frame(width: 44, height: 44)

                Text("VS")
                    .font(.system(size: 22, weight: .black, design: .rounded))
                    .foregroundStyle(Color.red)
                    .shadow(color: Color.red.opacity(0.8), radius: 8)
            }

            Text("DUEL")
                .font(.system(size: 8, weight: .black, design: .monospaced))
                .foregroundStyle(Color.yellow)
        }
        .frame(width: 48)
    }

    // MARK: - Hero Zoom Controls Bar

    private var heroZoomControlsBar: some View {
        HStack(spacing: 12) {
            // Zoom Out
            Button {
                withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                    zoomLevel = max(0.8, zoomLevel - 0.2)
                }
            } label: {
                Image(systemName: "minus.magnifyingglass")
                    .font(.system(size: 13, weight: .bold))
                    .foregroundStyle(Color.white)
                    .frame(width: 32, height: 32)
                    .background(Circle().fill(Color.white.opacity(0.12)))
            }

            // Preset Indicator Button (Cycles Fit -> Combat -> Close)
            Button {
                zoomPresetIndex = (zoomPresetIndex + 1) % zoomPresets.count
                withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                    zoomLevel = zoomPresets[zoomPresetIndex]
                }
            } label: {
                Text(zoomLabel)
                    .font(.system(size: 10, weight: .bold, design: .monospaced))
                    .foregroundStyle(Color(hex: 0x00E5FF))
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(Capsule().fill(Color(hex: 0x00E5FF).opacity(0.15)))
                    .overlay(Capsule().stroke(Color(hex: 0x00E5FF).opacity(0.4), lineWidth: 1))
            }

            // Zoom In
            Button {
                withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                    zoomLevel = min(2.0, zoomLevel + 0.2)
                }
            } label: {
                Image(systemName: "plus.magnifyingglass")
                    .font(.system(size: 13, weight: .bold))
                    .foregroundStyle(Color.white)
                    .frame(width: 32, height: 32)
                    .background(Circle().fill(Color.white.opacity(0.12)))
            }
        }
    }

    private var zoomLabel: String {
        if abs(zoomLevel - 1.0) < 0.05 { return "🔍 1.0x (FIT)" }
        if abs(zoomLevel - 1.35) < 0.05 { return "🔍 1.35x (COMBAT)" }
        if abs(zoomLevel - 1.75) < 0.05 { return "🔍 1.75x (CLOSE)" }
        return String(format: "🔍 %.1fx", zoomLevel)
    }

    // MARK: - Setup & Animations

    private func setupFighters() {
        playerWarrior = Warrior.all.randomElement() ?? Warrior.all.first!
        var potentialOpponents = Warrior.all.filter { $0.id != playerWarrior.id }
        opponentWarrior = potentialOpponents.randomElement() ?? Warrior.all.last!
        opponentRank = ["Warrior", "Scholar", "Master", "Grandmaster"].randomElement() ?? "Warrior"
    }

    private func startEntranceAnimation() {
        // Player pod flies in
        withAnimation(.easeOut(duration: 0.5)) {
            playerCardScale = 1.0
        }
        // Opponent pod flies in with slight delay
        withAnimation(.easeOut(duration: 0.5).delay(0.2)) {
            opponentCardScale = 1.0
        }
        // VS emblem bounces in
        withAnimation(.spring(response: 0.4, dampingFraction: 0.5).delay(0.4)) {
            vsScale = 1.0
        }
    }
}
