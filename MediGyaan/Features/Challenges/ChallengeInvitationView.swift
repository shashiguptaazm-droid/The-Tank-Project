import SwiftUI

/// iOS equivalent of Android `ChallengeInvitationActivity.kt`.
///
/// Presents a real-time prompt when an incoming battle challenge arrives from a friend
/// with duel metadata, accepting/rejecting the battle, and routing to live battle / lobby.
struct ChallengeInvitationView: View {

    let invitation: ChallengeInvitation
    var onAccept: ((ChallengeInvitation) -> Void)?
    var onDecline: ((ChallengeInvitation) -> Void)?

    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api

    @State private var isProcessing = false
    @State private var errorMessage: String?

    var body: some View {
        ZStack {
            AppTheme.Palette.background
                .ignoresSafeArea()

            VStack(spacing: AppTheme.Spacing.xl) {
                Spacer()

                // Combat Duel Crest
                ZStack {
                    Circle()
                        .fill(
                            RadialGradient(
                                colors: [
                                    AppTheme.Palette.primary.opacity(0.4),
                                    AppTheme.Palette.primary.opacity(0.0)
                                ],
                                center: .center,
                                startRadius: 20,
                                endRadius: 90
                            )
                        )
                        .frame(width: 180, height: 180)

                    Image(systemName: "swords")
                        .font(.system(size: 64, weight: .bold))
                        .foregroundStyle(
                            LinearGradient(
                                colors: [Color(hex: "#FFD700"), Color(hex: "#FF8C00")],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .shadow(color: Color.orange.opacity(0.6), radius: 16)
                }

                // Headline
                VStack(spacing: AppTheme.Spacing.xs) {
                    Text("Battle Challenge!")
                        .font(.system(size: 28, weight: .black, design: .rounded))
                        .foregroundStyle(AppTheme.Palette.textPrimary)

                    Text("\(invitation.hostName) has challenged you to a duel")
                        .font(AppTheme.Font.subheadline)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                        .multilineTextAlignment(.center)
                }

                // Match details card
                CardContainer {
                    VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                        detailRow(icon: "book.fill", title: "Subject", value: invitation.subject.isEmpty ? "All Subjects" : invitation.subject)
                        Divider().background(AppTheme.Palette.divider)
                        detailRow(icon: "tag.fill", title: "Topic", value: invitation.topic.isEmpty ? "General High-Yield" : invitation.topic)
                        Divider().background(AppTheme.Palette.divider)
                        detailRow(icon: "gamecontroller.fill", title: "Mode", value: invitation.mode.uppercased())
                        if !invitation.lobbyId.isEmpty {
                            Divider().background(AppTheme.Palette.divider)
                            detailRow(icon: "number", title: "Lobby Code", value: invitation.lobbyId)
                        }
                    }
                    .padding(.vertical, AppTheme.Spacing.xs)
                }
                .padding(.horizontal, AppTheme.Spacing.lg)

                Spacer()

                // Action Buttons
                VStack(spacing: AppTheme.Spacing.sm) {
                    PrimaryButton(
                        title: isProcessing ? "Entering Arena..." : "Accept Duel",
                        icon: "bolt.fill",
                        isLoading: isProcessing
                    ) {
                        handleAccept()
                    }

                    Button {
                        handleDecline()
                    } label: {
                        Text("Decline")
                            .font(AppTheme.Font.headline)
                            .foregroundStyle(AppTheme.Palette.textMuted)
                            .frame(maxWidth: .infinity)
                            .frame(height: 50)
                    }
                    .disabled(isProcessing)
                }
                .padding(.horizontal, AppTheme.Spacing.lg)
                .padding(.bottom, AppTheme.Spacing.lg)
            }
        .onAppear {
            RemoteLogger.log(tag: "ChallengeInvitation_Appear", message: "Challenge invitation screen viewed")
        }
        }
        .errorAlert(message: $errorMessage)
    }

    private func detailRow(icon: String, title: String, value: String) -> some View {
        HStack(spacing: AppTheme.Spacing.md) {
            Image(systemName: icon)
                .foregroundStyle(AppTheme.Palette.primary)
                .frame(width: 24)

            Text(title)
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Palette.textSecondary)

            Spacer()

            Text(value)
                .font(AppTheme.Font.callout.weight(.semibold))
                .foregroundStyle(AppTheme.Palette.textPrimary)
        }
    }

    private func handleAccept() {
        isProcessing = true
        onAccept?(invitation)
        dismiss()
    }

    private func handleDecline() {
        onDecline?(invitation)
        dismiss()
    }
}

/// Invitation data model corresponding to Android's Intent extras in `ChallengeInvitationActivity`.
struct ChallengeInvitation: Identifiable, Hashable {
    var id: String { "\(challengeId)_\(lobbyId)" }
    let challengeId: Int
    let lobbyId: String
    let uniqueId: Int
    let quizType: String
    let mode: String
    let subject: String
    let topic: String
    let hostName: String

    init(
        challengeId: Int = 0,
        lobbyId: String = "",
        uniqueId: Int = 0,
        quizType: String = "TEST_SERIES",
        mode: String = "1v1",
        subject: String = "Pathology",
        topic: String = "General Pathology",
        hostName: String = "Warrior"
    ) {
        self.challengeId = challengeId
        self.lobbyId = lobbyId
        self.uniqueId = uniqueId
        self.quizType = quizType
        self.mode = mode
        self.subject = subject
        self.topic = topic
        self.hostName = hostName
    }
}