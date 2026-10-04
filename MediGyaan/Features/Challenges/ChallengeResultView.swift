import SwiftUI

/// iOS equivalent of Android `ChallengeResultActivity.kt`.
///
/// Displays battle outcome (Victory / Defeat / Draw), score comparison against
/// opponent/bot, exp gain, stats breakdown, and detailed question-by-question review.
struct ChallengeResultView: View {

    let result: BattleResultSummary
    var onHome: (() -> Void)?

    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.lg) {
                // Outcome Header Card
                outcomeBanner

                // Scoreboard Versus Card
                scoreVersusCard

                // Rewards & EXP Card
                rewardsCard

                // Question Review Accordion
                if !result.questionReviews.isEmpty {
                    reviewSection
                }

                // Action buttons
                PrimaryButton(title: "Return to Arena", icon: "house.fill") {
                    if let onHome = onHome {
                        onHome()
                    } else {
                        dismiss()
                    }
                }
                .padding(.top, AppTheme.Spacing.sm)
            }
            .padding(AppTheme.Spacing.md)
        }
        .screenBackground()
        .navigationTitle("Battle Results")
        .navigationBarTitleDisplayMode(.inline)
    }

    // MARK: - Banner

    private var outcomeBanner: some View {
        CardContainer {
            VStack(spacing: AppTheme.Spacing.md) {
                ZStack {
                    Circle()
                        .fill(result.isVictory ? Color.green.opacity(0.15) : (result.isDraw ? Color.orange.opacity(0.15) : Color.red.opacity(0.15)))
                        .frame(width: 90, height: 90)

                    Image(systemName: result.isVictory ? "trophy.fill" : (result.isDraw ? "equal.circle.fill" : "xmark.shield.fill"))
                        .font(.system(size: 44))
                        .foregroundStyle(result.isVictory ? AppTheme.Palette.success : (result.isDraw ? AppTheme.Palette.warning : AppTheme.Palette.error))
                }

                Text(result.outcomeTitle)
                    .font(.system(size: 26, weight: .black, design: .rounded))
                    .foregroundStyle(AppTheme.Palette.textPrimary)

                Text(result.outcomeSubtitle)
                    .font(AppTheme.Font.subheadline)
                    .foregroundStyle(AppTheme.Palette.textSecondary)
                    .multilineTextAlignment(.center)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, AppTheme.Spacing.sm)
        }
    }

    // MARK: - Scoreboard

    private var scoreVersusCard: some View {
        CardContainer {
            HStack(spacing: 0) {
                // User Side
                VStack(spacing: AppTheme.Spacing.xs) {
                    Text(result.userName)
                        .font(AppTheme.Font.headline)
                        .foregroundStyle(AppTheme.Palette.textPrimary)
                        .lineLimit(1)

                    Text("\(result.userScore)")
                        .font(.system(size: 32, weight: .black, design: .rounded))
                        .foregroundStyle(AppTheme.Palette.primary)

                    Text("Correct: \(result.userCorrect)/\(result.totalQuestions)")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textMuted)
                }
                .frame(maxWidth: .infinity)

                // Divider / VS
                VStack(spacing: 4) {
                    Text("VS")
                        .font(.system(size: 14, weight: .black))
                        .foregroundStyle(AppTheme.Palette.accent)
                        .padding(6)
                        .background(Circle().fill(AppTheme.Palette.cardBackgroundElevated))
                }
                .padding(.horizontal, AppTheme.Spacing.xs)

                // Opponent Side
                VStack(spacing: AppTheme.Spacing.xs) {
                    Text(result.opponentName)
                        .font(AppTheme.Font.headline)
                        .foregroundStyle(AppTheme.Palette.textPrimary)
                        .lineLimit(1)

                    Text("\(result.opponentScore)")
                        .font(.system(size: 32, weight: .black, design: .rounded))
                        .foregroundStyle(Color.red)

                    Text("Correct: \(result.opponentCorrect)/\(result.totalQuestions)")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textMuted)
                }
                .frame(maxWidth: .infinity)
            }
            .padding(.vertical, AppTheme.Spacing.sm)
        }
    }

    // MARK: - Rewards Card

    private var rewardsCard: some View {
        CardContainer {
            HStack {
                HStack(spacing: AppTheme.Spacing.sm) {
                    Image(systemName: "sparkles")
                        .font(.title2)
                        .foregroundStyle(AppTheme.Palette.warning)
                    VStack(alignment: .leading, spacing: 2) {
                        Text("+\(result.expGained) XP")
                            .font(AppTheme.Font.headline)
                            .foregroundStyle(AppTheme.Palette.textPrimary)
                        Text("Battle Experience")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                    }
                }

                Spacer()

                HStack(spacing: AppTheme.Spacing.sm) {
                    Image(systemName: "circle.circle.fill")
                        .font(.title2)
                        .foregroundStyle(AppTheme.Palette.accent)
                    VStack(alignment: .leading, spacing: 2) {
                        Text("+\(result.creditsGained) Credits")
                            .font(AppTheme.Font.headline)
                            .foregroundStyle(AppTheme.Palette.textPrimary)
                        Text("Treasure Bounty")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                    }
                }
            }
            .padding(.vertical, AppTheme.Spacing.xs)
        }
    }

    // MARK: - Review Section

    private var reviewSection: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            Text("Question Breakdown")
                .font(AppTheme.Font.title3)
                .foregroundStyle(AppTheme.Palette.textPrimary)

            ForEach(Array(result.questionReviews.enumerated()), id: \.offset) { index, item in
                CardContainer {
                    VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
                        HStack {
                            Text("Q\(index + 1).")
                                .font(AppTheme.Font.headline)
                                .foregroundStyle(AppTheme.Palette.primary)

                            Spacer()

                            Image(systemName: item.isCorrect ? "checkmark.circle.fill" : "xmark.circle.fill")
                                .foregroundStyle(item.isCorrect ? AppTheme.Palette.success : AppTheme.Palette.error)
                        }

                        Text(item.question)
                            .font(AppTheme.Font.callout)
                            .foregroundStyle(AppTheme.Palette.textPrimary)

                        if !item.isCorrect {
                            Text("Your Answer: \(item.userAnswer)")
                                .font(AppTheme.Font.caption)
                                .foregroundStyle(AppTheme.Palette.error)
                        }

                        Text("Correct Answer: \(item.correctAnswer)")
                            .font(AppTheme.Font.caption.weight(.medium))
                            .foregroundStyle(AppTheme.Palette.success)

                        if !item.explanation.isEmpty {
                            Text("Rationale: \(item.explanation)")
                                .font(AppTheme.Font.caption)
                                .foregroundStyle(AppTheme.Palette.textMuted)
                                .padding(.top, 2)
                        }
                    }
                }
            }
        }
    }
}

/// Battle result entity matching Android `ChallengeResultActivity` and Firebase schema.
struct BattleResultSummary: Identifiable, Hashable {
    var id: String { challengeId }
    let challengeId: String
    let userName: String
    let opponentName: String
    let userScore: Int
    let opponentScore: Int
    let userCorrect: Int
    let opponentCorrect: Int
    let totalQuestions: Int
    let expGained: Int
    let creditsGained: Int
    let questionReviews: [QuestionReviewItem]

    var isVictory: Bool { userScore > opponentScore }
    var isDraw: Bool { userScore == opponentScore }

    var outcomeTitle: String {
        if isVictory { return "VICTORY!" }
        if isDraw { return "STALEMATE" }
        return "DEFEAT"
    }

    var outcomeSubtitle: String {
        if isVictory { return "Outstanding medical clinical accuracy! You dominated the arena." }
        if isDraw { return "Evenly matched warriors. Both proved exceptional skills." }
        return "Tough challenge. Review your question breakdown to sharpen your edge."
    }
}

/// Question review model from Android's `loadReviewData`.
struct QuestionReviewItem: Identifiable, Hashable {
    var id: String { question }
    let question: String
    let userAnswer: String
    let correctAnswer: String
    let isCorrect: Bool
    let explanation: String
}
