import SwiftUI

/// Ports `AttemptAdapter` (`com.rankwarz.edulabsrtm.AttemptAdapter.kt`) and the
/// `res/layout/item_attempt.xml` it inflates: the single card that renders one
/// peer attempt on a shared question.
///
/// `onCreateViewHolder()` inflates `item_attempt` for a single view type —
/// `getItemViewType()` is not overridden, so every position shares one holder,
/// and `getItemCount()` is just `list.size`. SwiftUI's `ForEach` covers both:
/// one `View` body, one identifier source.
///
/// `onBindViewHolder()` assigns exactly four `TextView`s and nothing else:
///
/// | view | Kotlin assignment | rendering |
/// |---|---|---|
/// | `nameText` | `item.name` | 15sp bold `#111` |
/// | `answerText` | `"Answer: ${item.user_answer}"` | 14sp `#555` |
/// | `statusText` | `if (item.is_correct == 1) "✅ Correct" else "❌ Wrong"` | 14sp bold, no explicit colour |
/// | `timeText` | `item.created_at` | 12sp `#888` |
///
/// The card is a `CardView` at 12dp corner radius with 3dp elevation, inset by
/// 6dp horizontally and 10dp at the bottom, wrapping a vertical `LinearLayout`
/// with 12dp padding and 4dp between every child.
///
/// **State matrix** — the row has exactly two states and no others. There is no
/// unattempted, in-progress, selected or disabled branch: an attempt only exists
/// once a peer has submitted, and `is_correct` is the sole discriminator.
///
/// | row state | `statusText` | colour |
/// |---|---|---|
/// | `is_correct == 1` | `"✅ Correct"` | inherited text colour |
/// | `is_correct != 1` (including `0`, negative, and absent) | `"❌ Wrong"` | inherited text colour |
///
/// `item_attempt.xml` gives `statusText` **no** `android:textColor`, so on
/// Android the two states are told apart by the emoji glyph alone and both
/// paint in the theme's default text colour. This port keeps that: the state is
/// carried by ``Outcome``'s label and by VoiceOver, not by a tint that Android
/// never drew.
///
/// `user_answer` and `created_at` are interpolated raw. Android performs no
/// date parsing, no letter normalisation and no trimming, so an empty answer
/// renders `"Answer: "` and an unparsable `created_at` renders verbatim.
/// ``formattedAnswer`` and ``timestamp`` reproduce that.
///
/// The adapter registers no click or long-click listener and swallows no
/// exceptions; it contains no `!!`. ``onTap`` exists only so the host can add
/// navigation Android did not have, and is absent by default.
struct AttemptRow: View {

    /// Ports the `if (item.is_correct == 1)` ternary in
    /// `AttemptAdapter.onBindViewHolder()`, including the exact glyphs and
    /// spacing of `"✅ Correct"` / `"❌ Wrong"`.
    enum Outcome: String, Hashable, CaseIterable {

        /// `item.is_correct == 1`.
        case correct = "✅ Correct"

        /// Every other `is_correct` value — Android's `else` branch.
        case wrong = "❌ Wrong"

        /// Ports the ternary itself.
        init(isCorrect: Bool) {
            self = isCorrect ? .correct : .wrong
        }

        /// Convenience for `QuestionAttemptPeer.isCorrect`.
        init(_ attempt: QuestionAttemptPeer) {
            self.init(isCorrect: attempt.isCorrect)
        }

        /// The `true` half of the ternary.
        var isCorrect: Bool { self == .correct }

        /// The text Android assigns to `statusText`, emoji included.
        var label: String { rawValue }

        /// VoiceOver reads the emoji out, so strip it from the spoken string
        /// while leaving the visible label untouched.
        var accessibilityLabel: String {
            switch self {
            case .correct: return "Correct"
            case .wrong: return "Wrong"
            }
        }
    }

    /// The peer attempt being rendered — the port of `AttemptModel`.
    let attempt: QuestionAttemptPeer

    /// Optional host affordance. `AttemptAdapter` registers no listener, so this
    /// is `nil` for a faithful copy of the Kotlin screen.
    var onTap: ((QuestionAttemptPeer) -> Void)?

    init(attempt: QuestionAttemptPeer, onTap: ((QuestionAttemptPeer) -> Void)? = nil) {
        self.attempt = attempt
        self.onTap = onTap
    }

    var body: some View {
        Button {
            onTap?(attempt)
        } label: {
            card(outcome: Outcome(attempt))
                .padding(.horizontal, AppTheme.Spacing.xs)
                .padding(.bottom, AppAttemptMetric.gap)
        }
        .buttonStyle(.plain)
        .allowsHitTesting(onTap != nil)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(
            "\(attempt.name), \(formattedAnswer), \(Outcome(attempt).accessibilityLabel)"
        )
    }

    // MARK: - Card

    /// The `CardView` from `item_attempt.xml` — 12dp radius, 3dp elevation,
    /// wrapping a vertical stack with 12dp padding and 4dp gaps.
    private func card(outcome: Outcome) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
            nameText
            answerText
            statusText(outcome)
            timeText
        }
        .padding(AppAttemptMetric.padding)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(
                cornerRadius: AppTheme.Radius.androidMedium,
                style: .continuous
            )
            .fill(AppTheme.Palette.cardBackground)
        )
        .shadow(
            color: .black.opacity(0.08),
            radius: AppAttemptMetric.elevation,
            y: 1
        )
        .contentShape(Rectangle())
    }

    // MARK: - Bound views

    /// `holder.name.text = item.name` — 15sp bold `#111`.
    private var nameText: some View {
        Text(attempt.name)
            .font(AppTheme.Font.cardTitle)
            .foregroundStyle(AppTheme.Palette.androidAttemptName)
            .lineLimit(2)
            .fixedSize(horizontal: false, vertical: true)
    }

    /// `holder.answer.text = "Answer: ${item.user_answer}"` — 14sp `#555`.
    private var answerText: some View {
        Text(formattedAnswer)
            .font(AppTheme.Font.callout)
            .foregroundStyle(AppTheme.Palette.androidAttemptAnswer)
            .fixedSize(horizontal: false, vertical: true)
    }

    /// `holder.status.text = …` — 14sp bold. `item_attempt.xml` sets no
    /// `android:textColor` here, so the theme's default text colour is used.
    private func statusText(_ outcome: Outcome) -> some View {
        Text(outcome.label)
            .font(AppTheme.Font.callout.weight(.bold))
            .foregroundStyle(AppTheme.Palette.textPrimary)
            .accessibilityLabel(outcome.accessibilityLabel)
    }

    /// `holder.time.text = item.created_at` — 12sp `#888`, verbatim.
    private var timeText: some View {
        Text(timestamp)
            .font(AppTheme.Font.caption)
            .foregroundStyle(AppTheme.Palette.androidAttemptTimestamp)
            .lineLimit(2)
            .fixedSize(horizontal: false, vertical: true)
    }

    // MARK: - Formatting

    /// Ports the Kotlin string template. Android does not trim, upper-case or
    /// validate the answer, so neither does this.
    var formattedAnswer: String {
        "Answer: \(attempt.userAnswer)"
    }

    /// `created_at` is passed straight to `TextView`, with no parsing on
    /// Android; the value is therefore displayed exactly as the API returned it.
    var timestamp: String {
        attempt.createdAt
    }
}

// MARK: - item_attempt.xml literals

private extension AppTheme.Palette {

    /// `#111` — `item_attempt.xml`'s `nameText` `android:textColor`.
    static let androidAttemptName = Color(hex: 0x111)

    /// `#555` — `item_attempt.xml`'s `answerText` `android:textColor`.
    static let androidAttemptAnswer = Color(hex: 0x555)

    /// `#888` — `item_attempt.xml`'s `timeText` `android:textColor`.
    static let androidAttemptTimestamp = Color(hex: 0x888)
}

/// Layout metrics from `item_attempt.xml` that have no `AppTheme` token.
///
/// These three are hardcoded in the layout rather than resolved from a shared
/// resource, and the tokens closest to them (`Spacing.optionGap` for the 12dp
/// padding, `Spacing.md` for the 10dp bottom margin) carry unrelated meanings,
/// so they are declared here under the `android` prefix convention set by
/// `Palette+Android.swift` and `Theme+Android.swift`.
private enum AppAttemptMetric {

    /// 12dp — the inner `LinearLayout`'s `android:padding`.
    static let padding: CGFloat = 12

    /// 10dp — the `CardView`'s `android:layout_marginBottom`.
    static let gap: CGFloat = 10

    /// 3dp — the `CardView`'s `app:cardElevation`.
    static let elevation: CGFloat = 3
}