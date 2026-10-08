import SwiftUI

/// iOS equivalent of Android `LobbyActivity.kt` and `LobbyPlayerAdapter.kt`.
///
/// Real-time battle staging arena where host and opponent ready-up,
/// display lobby pin codes, share invitations, and trigger synchronous battle start.
struct BattleLobbyView: View {

    let lobbyId: String
    let topicName: String
    let isHost: Bool

    @EnvironmentObject private var session: SessionStore
    @Environment(\.dismiss) private var dismiss

    @State private var isReady: Bool = false
    @State private var opponentName: String = "Waiting for challenger..."
    @State private var opponentAvatar: String = ""
    @State private var isOpponentReady: Bool = false
    @State private var isStartingBattle: Bool = false
    @State private var showCopiedAlert: Bool = false

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
    }

    // MARK: - Arena Header

    private var arenaHeader: some View {
        VStack(spacing: 4) {
            Text("ARENA CODE")
                .font(.system(size: 11, weight: .black, design: .monospaced))
                .foregroundStyle(AppTheme.Palette.textMuted)

            Text(lobbyId.isEmpty ? "ARENA-998" : lobbyId)
                .font(.system(size: 32, weight: .black, design: .monospaced))
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
                            .frame(width: 80, height: 80)

                        Image(systemName: "person.crop.circle.fill")
                            .font(.system(size: 76))
                            .foregroundStyle(AppTheme.Palette.primary)

                        Image(systemName: isReady ? "checkmark.circle.fill" : "clock.fill")
                            .font(.system(size: 20))
                            .foregroundStyle(isReady ? Color.green : Color.orange)
                            .background(Circle().fill(Color.black))
                    }

                    Text(session.currentUser?.name ?? "Warrior")
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
                        .fill(Color.red.opacity(0.2))
                        .frame(width: 48, height: 48)

                    Text("VS")
                        .font(.system(size: 18, weight: .black, design: .rounded))
                        .foregroundStyle(Color.red)
                }

                // Opponent / Challenger
                VStack(spacing: AppTheme.Spacing.xs) {
                    ZStack(alignment: .bottomTrailing) {
                        Circle()
                            .fill(Color.purple.opacity(0.2))
                            .frame(width: 80, height: 80)

                        Image(systemName: "person.crop.circle.badge.questionmark")
                            .font(.system(size: 68))
                            .foregroundStyle(Color.purple)

                        Image(systemName: isOpponentReady ? "checkmark.circle.fill" : "clock.fill")
                            .font(.system(size: 20))
                            .foregroundStyle(isOpponentReady ? Color.green : Color.orange)
                            .background(Circle().fill(Color.black))
                    }

                    Text(opponentName)
                        .font(AppTheme.Font.headline)
                        .foregroundStyle(AppTheme.Palette.textPrimary)
                        .lineLimit(1)

                    Text(isOpponentReady ? "READY" : "STANDBY")
                        .font(.system(size: 10, weight: .black))
                        .foregroundStyle(isOpponentReady ? Color.green : Color.orange)
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
                    Text("Topic Target")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                    Spacer()
                    Text(topicName.isEmpty ? "Clinical Mixed Arena" : topicName)
                        .font(AppTheme.Font.callout.weight(.bold))
                        .foregroundStyle(AppTheme.Palette.textPrimary)
                }

                Divider().background(AppTheme.Palette.divider)

                HStack {
                    Image(systemName: "bolt.shield.fill")
                        .foregroundStyle(Color.yellow)
                    Text("Battle Format")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                    Spacer()
                    Text("1v1 Rapid MCQ Duel")
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
                    isStartingBattle = true
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
                .disabled(!isReady || !isOpponentReady)
            }

            ShareLink(item: "Join my MediGyaan medical arena battle using code: \(lobbyId)!") {
                HStack {
                    Image(systemName: "square.and.arrow.up")
                    Text("Invite Friends")
                }
                .font(AppTheme.Font.subheadline.weight(.semibold))
                .foregroundStyle(AppTheme.Palette.textSecondary)
                .frame(maxWidth: .infinity)
                .frame(height: 44)
            }
        }
    }
}
