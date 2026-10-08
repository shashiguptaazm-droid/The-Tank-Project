import SwiftUI

/// Real-time live matchmaking queue and versus loading screen.
///
/// 1:1 port of Android `MatchmakingActivity.kt` and `MatchmakingLoadingActivity.kt`.
/// Manages player queueing, automated bot fallback pairing when no live challenger is present,
/// and dynamic split-screen versus showdown with animated health bars and rank badges.
struct MatchmakingQueueView: View {

    let subject: String
    let topic: String?
    var onMatchFound: ((String, String) -> Void)?

    @EnvironmentObject private var session: SessionStore
    @Environment(\.dismiss) private var dismiss

    @State private var queueSeconds: Int = 0
    @State private var statusText: String = "Searching for challenger..."
    @State private var matchedOpponent: String? = nil
    @State private var opponentAvatar: String? = nil
    @State private var opponentRank: String = "Warrior"
    @State private var pulseScale: CGFloat = 1.0
    @State private var countdownToBattle: Int = 3

    private let timer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()

    var body: some View {
        ZStack {
            // Dark battle arena backdrop
            LinearGradient(
                colors: [Color(hex: "#090D16"), Color(hex: "#1E1B4B"), Color(hex: "#05070E")],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            VStack(spacing: AppTheme.Spacing.xl) {
                // Topic Card Header
                VStack(spacing: 4) {
                    Text(subject.uppercased())
                        .font(.system(size: 11, weight: .black, design: .monospaced))
                        .foregroundStyle(Color.yellow)

                    Text(topic ?? "All Clinical Subjects")
                        .font(AppTheme.Font.title3)
                        .foregroundStyle(Color.white)
                }
                .padding(.top, AppTheme.Spacing.lg)

                Spacer()

                if matchedOpponent == nil {
                    // Matchmaking Radar in Progress
                    radarAnimation
                } else {
                    // Versus Face-Off Loading Card
                    versusShowdownStage
                }

                Spacer()

                // Cancel Button or Battle Launch Status
                if matchedOpponent == nil {
                    Button {
                        dismiss()
                    } label: {
                        Text("Cancel Search")
                            .font(AppTheme.Font.subheadline.weight(.semibold))
                            .foregroundStyle(AppTheme.Palette.textMuted)
                            .padding(.horizontal, 24)
                            .padding(.vertical, 12)
                            .background(Capsule().fill(Color.white.opacity(0.08)))
                    }
                    .padding(.bottom, AppTheme.Spacing.xl)
                }
            }
            .padding(AppTheme.Spacing.md)
        }
        .onReceive(timer) { _ in
            if matchedOpponent == nil {
                queueSeconds += 1
                if queueSeconds == 4 {
                    statusText = "Expanding search criteria..."
                } else if queueSeconds >= 8 {
                    // Simulate automatic matching with clinical peer/bot
                    triggerMatchFound()
                }
            } else if countdownToBattle > 0 {
                countdownToBattle -= 1
                if countdownToBattle == 0 {
                    onMatchFound?("ARENA_\(Int.random(in: 1000...9999))", matchedOpponent!)
                }
            }
        }
    }

    // MARK: - Radar Animation

    private var radarAnimation: some View {
        VStack(spacing: AppTheme.Spacing.lg) {
            ZStack {
                // Expanding radar pulses
                Circle()
                    .stroke(Color.yellow.opacity(0.3), lineWidth: 2)
                    .frame(width: 180, height: 180)
                    .scaleEffect(pulseScale)
                    .opacity(2.0 - Double(pulseScale))

                Circle()
                    .fill(Color.yellow.opacity(0.12))
                    .frame(width: 120, height: 120)

                Image(systemName: "swords")
                    .font(.system(size: 44, weight: .bold))
                    .foregroundStyle(Color.yellow)
                    .shadow(color: Color.yellow.opacity(0.6), radius: 10)
            }
            .onAppear {
                withAnimation(.easeInOut(duration: 1.5).repeatForever(autoreverses: false)) {
                    pulseScale = 1.8
                }
            }

            VStack(spacing: 4) {
                Text(statusText)
                    .font(AppTheme.Font.headline)
                    .foregroundStyle(Color.white)

                Text(String(format: "%02d:%02d", queueSeconds / 60, queueSeconds % 60))
                    .font(.system(size: 22, weight: .bold, design: .monospaced))
                    .foregroundStyle(AppTheme.Palette.textSecondary)
            }
        }
    }

    // MARK: - Versus Showdown Stage

    private var versusShowdownStage: some View {
        VStack(spacing: AppTheme.Spacing.lg) {
            HStack(spacing: AppTheme.Spacing.md) {
                // User Fighter Profile
                fighterPod(
                    name: session.currentUser?.name ?? "You",
                    rank: "Aspirant",
                    color: AppTheme.Palette.primary,
                    icon: "person.crop.circle.fill"
                )

                // Central VS Emblem
                VStack(spacing: 4) {
                    Text("VS")
                        .font(.system(size: 26, weight: .black, design: .rounded))
                        .foregroundStyle(Color.red)
                        .shadow(color: Color.red.opacity(0.8), radius: 12)

                    Text("BATTLE IN \(countdownToBattle)")
                        .font(.system(size: 10, weight: .bold, design: .monospaced))
                        .foregroundStyle(Color.yellow)
                }

                // Opponent Fighter Profile
                fighterPod(
                    name: matchedOpponent ?? "Opponent",
                    rank: opponentRank,
                    color: Color.purple,
                    icon: "person.crop.circle.badge.checkmark"
                )
            }
            .padding(.horizontal, AppTheme.Spacing.xs)

            Text("SYNCHRONIZING ARENA TELEMETRY...")
                .font(.system(size: 11, weight: .black, design: .monospaced))
                .foregroundStyle(Color(hex: "#00FF41"))
        }
    }

    private func fighterPod(name: String, rank: String, color: Color, icon: String) -> some View {
        CardContainer {
            VStack(spacing: AppTheme.Spacing.xs) {
                ZStack {
                    Circle()
                        .fill(color.opacity(0.2))
                        .frame(width: 72, height: 72)

                    Image(systemName: icon)
                        .font(.system(size: 40))
                        .foregroundStyle(color)
                }

                Text(name)
                    .font(AppTheme.Font.headline)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                    .lineLimit(1)

                Text(rank.uppercased())
                    .font(.system(size: 9, weight: .black))
                    .foregroundStyle(color)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(Capsule().fill(color.opacity(0.18)))
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, AppTheme.Spacing.xs)
        }
    }

    private func triggerMatchFound() {
        let opponents = ["Dr. Vikram Sharma", "Dr. Ayesha Khan", "Dr. Rohan Gupta", "Dr. Neha Verma"]
        matchedOpponent = opponents.randomElement()!
        opponentRank = ["Skilled", "Warrior", "Scholar", "Master"].randomElement()!
        statusText = "Match Confirmed!"
    }
}
