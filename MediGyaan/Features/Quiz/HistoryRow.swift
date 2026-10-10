import SwiftUI

// MARK: - Fixed Compose literals

// `HistoryAdapter.kt` paints its Compose screen with hardcoded `Color(0xFF…)`
// literals rather than theme roles, so every value below is a byte-for-byte
// transcription of a Kotlin original. They live under `AppTheme.Palette` so no
// screen has to hardcode a hex, and the `history` prefix keeps them from
// colliding with the adaptive tokens in `Theme.swift`.

extension AppTheme.Palette {

    // MARK: Screen gradient (LazyColumn background of `HistoryScreen`)

    /// `#0F172A` — top stop of `Brush.verticalGradient`.
    static let historyBackgroundTop = Color(hex: 0xFF0F172A)
    /// `#111827` — middle stop of `Brush.verticalGradient`.
    static let historyBackgroundMid = Color(hex: 0xFF111827)
    /// `#1E293B` — bottom stop of `Brush.verticalGradient`.
    static let historyBackgroundBottom = Color(hex: 0xFF1E293B)

    // MARK: Card

    /// `#111827` — `CardDefaults.cardColors(containerColor = Color(0xFF111827))`.
    static let historyCardSurface = Color(hex: 0xFF111827)

    // MARK: Mode accent (`modeColor`)

    /// `#EF4444` — `"CHALLENGE"`.
    static let historyModeChallenge = Color(hex: 0xFFEF4444)
    /// `#8B5CF6` — `"FINAL_TEST"`.
    static let historyModeFinalTest = Color(hex: 0xFF8B5CF6)
    /// `#06B6D4` — `"SINGLE_PLAYER"`.
    static let historyModeSinglePlayer = Color(hex: 0xFF06B6D4)
    /// `#22C55E` — the `else` branch (PRACTICE and any unknown mode).
    static let historyModeDefault = Color(hex: 0xFF22C55E)

    // MARK: Supporting text

    /// `#94A3B8` — subtitle and footer timestamp colour.
    static let historySubtitle = Color(hex: 0xFF94A3B8)
    /// `#64748B` — `"#N"` ordinal.
    static let historyOrdinal = Color(hex: 0xFF64748B)
    /// `#1E293B` — `HorizontalDivider` colour.
    static let historyDivider = Color(hex: 0xFF1E293B)
    /// `#334155` — `LinearProgressIndicator(trackColor = Color(0xFF334155))`.
    static let historyProgressTrack = Color(hex: 0xFF334155)

    // MARK: Stat chip fills

    /// `#082F49` — "Score" chip background.
    static let historyScoreBackground = Color(hex: 0xFF082F49)
    /// `#38BDF8` — "Score" chip foreground.
    static let historyScoreForeground = Color(hex: 0xFF38BDF8)
    /// `#052E16` — "Correct" chip background.
    static let historyCorrectBackground = Color(hex: 0xFF052E16)
    /// `#4ADE80` — "Correct" chip foreground.
    static let historyCorrectForeground = Color(hex: 0xFF4ADE80)
    /// `#450A0A` — "Wrong" chip background.
    static let historyWrongBackground = Color(hex: 0xFF450A0A)
    /// `#F87171` — "Wrong" chip foreground.
    static let historyWrongForeground = Color(hex: 0xFFF87171)
    /// `#1E1B4B` — "Mode" chip background.
    static let historyModeBackground = Color(hex: 0xFF1E1B4B)
    /// `#A78BFA` — "Mode" chip foreground.
    static let historyModeForeground = Color(hex: 0xFFA78BFA)
}

extension AppTheme.Spacing {

    /// 18dp — the `Column` padding inside `HistoryCard`, and the two gaps that
    /// separate its progress bar and chip stack.
    static let historyCardInset: CGFloat = 18
    /// 52dp — the square mode-icon `Box` in `HistoryCard`.
    static let historyIconWell: CGFloat = 52
    /// 3dp — the gap between the row title and its topic subtitle.
    static let historyTitleGap: CGFloat = 3
    /// 10dp — the gap between chips inside a row and between the two chip rows.
    static let historyChipGap: CGFloat = 10
    /// 9dp — the `LinearProgressIndicator` track height.
    static let historyProgressHeight: CGFloat = 9
}

extension AppTheme.Radius {

    /// 28dp — `Card(shape = RoundedCornerShape(28.dp))` on `HistoryCard`.
    static let historyCard: CGFloat = 28
    /// 12dp — `cardCornerRadius` on `res/layout/item_challenge_simple.xml`.
    static let historyCompactCard: CGFloat = 12
}

extension AppTheme.Elevation {

    /// 7dp — `CardDefaults.cardElevation(defaultElevation = 7.dp)`.
    static let historyCard: CGFloat = 7
}

// MARK: - Row

/// Ports the two history-row renderers that live in Android `HistoryAdapter.kt`.
///
/// * ``Style/card`` ports `HistoryCard` (the Compose `@Composable`, lines 89–273)
///   together with its `HistoryStatChip` children (lines 275–312): a 28dp
///   `#111827` card whose accent colour, icon and progress track are all driven
///   by `item.mode.uppercased()`, plus the Score / Correct / Wrong / Mode chip grid.
/// * ``Style/compact`` ports `HistoryAdapter.onBindViewHolder()` (lines 327–332)
///   against `res/layout/item_challenge_simple.xml`: the three-`TextView`
///   Material card — bold title, topic subtitle, and the
///   `"Score: n | Correct: n/n"` status line in `@color/colorPrimary`.
///
/// One row never mixes the two title fallbacks, which differ in the Kotlin
/// source: `HistoryCard` falls back `title → mode`, while `onBindViewHolder`
/// falls back `title → topic`. Both are implemented; each style uses its own.
///
/// The percentage is recomputed from `correctAnswers / totalQuestions` exactly as
/// `HistoryCard` does, rather than read from `item.percentage`, which
/// `QuizHistoryManager.saveHistory` derives from `correctAnswers + wrongAnswers`.
struct HistoryRow: View {

    /// Which of the two Kotlin renderers this row reproduces.
    enum Style {
        /// `HistoryCard` — the full Compose card with the four stat chips.
        case card
        /// `onBindViewHolder` + `item_challenge_simple.xml` — the compact row.
        case compact
    }

    let item: QuizHistoryItem
    /// 0-based list position; `HistoryCard` prints `"#\(index + 1)"`.
    var index: Int = 0
    var style: Style = .card
    /// `holder.itemView.setOnClickListener { onItemClick(item) }`.
    var onTap: () -> Void = {}

    var body: some View {
        Button(action: onTap) {
            switch style {
            case .card: cardBody
            case .compact: compactBody
            }
        }
        .buttonStyle(.plain)
    }

    // MARK: - Compose card

    private var cardBody: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.historyCardInset) {
            header

            progressBar

            HStack(spacing: AppTheme.Spacing.historyChipGap) {
                StatChip(
                    title: "Score",
                    value: "\(item.score)",
                    background: AppTheme.Palette.historyScoreBackground,
                    foreground: AppTheme.Palette.historyScoreForeground
                )
                StatChip(
                    title: "Correct",
                    value: "\(item.correctAnswers)/\(item.totalQuestions)",
                    background: AppTheme.Palette.historyCorrectBackground,
                    foreground: AppTheme.Palette.historyCorrectForeground
                )
            }

            HStack(spacing: AppTheme.Spacing.historyChipGap) {
                StatChip(
                    title: "Wrong",
                    value: "\(item.wrongAnswers)",
                    background: AppTheme.Palette.historyWrongBackground,
                    foreground: AppTheme.Palette.historyWrongForeground
                )
                StatChip(
                    title: "Mode",
                    value: item.mode,
                    background: AppTheme.Palette.historyModeBackground,
                    foreground: AppTheme.Palette.historyModeForeground
                )
            }

            Rectangle()
                .fill(AppTheme.Palette.historyDivider)
                .frame(height: 1)

            Text(formattedTimestamp)
                .font(AppTheme.Font.caption)
                .foregroundStyle(AppTheme.Palette.historySubtitle)
        }
        .padding(AppTheme.Spacing.historyCardInset)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(
                cornerRadius: AppTheme.Radius.historyCard,
                style: .continuous
            )
            .fill(AppTheme.Palette.historyCardSurface)
        )
        .shadow(
            color: .black.opacity(0.28),
            radius: AppTheme.Elevation.historyCard,
            y: 3
        )
    }

    /// The `Row` holding the 52dp mode-icon well, the title block, and the
    /// percentage / ordinal column.
    private var header: some View {
        HStack(spacing: AppTheme.Spacing.md) {
            AndroidIcon(modeGlyph, size: 24, tint: modeColor)
                .frame(
                    width: AppTheme.Spacing.historyIconWell,
                    height: AppTheme.Spacing.historyIconWell
                )
                .background(
                    RoundedRectangle(
                        cornerRadius: AppTheme.Radius.materialCard,
                        style: .continuous
                    )
                    .fill(modeColor.opacity(0.15))
                )

            VStack(alignment: .leading, spacing: AppTheme.Spacing.historyTitleGap) {
                Text(cardTitle)
                    .font(AppTheme.Font.title3)
                    .foregroundStyle(.white)
                    .lineLimit(1)
                    .truncationMode(.tail)

                Text(item.topic)
                    .font(AppTheme.Font.subheadline)
                    .foregroundStyle(AppTheme.Palette.historySubtitle)
                    .lineLimit(1)
                    .truncationMode(.tail)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            VStack(alignment: .trailing, spacing: 0) {
                Text("\(Int(percentage))%")
                    .font(AppTheme.Font.title2.weight(.black))
                    .foregroundStyle(modeColor)

                Text("#\(index + 1)")
                    .font(AppTheme.Font.micro)
                    .foregroundStyle(AppTheme.Palette.historyOrdinal)
            }
            .fixedSize(horizontal: true, vertical: false)
        }
    }

    private var progressBar: some View {
        GeometryReader { geometry in
            ZStack(alignment: .leading) {
                Capsule()
                    .fill(AppTheme.Palette.historyProgressTrack)
                Capsule()
                    .fill(modeColor)
                    .frame(width: progressFraction * geometry.size.width)
            }
        }
        .frame(height: AppTheme.Spacing.historyProgressHeight)
    }

    // MARK: - RecyclerView compact row

    private var compactBody: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
            Text(compactTitle)
                .font(AppTheme.Font.bodyBold)
                .foregroundStyle(AppTheme.Palette.textPrimary)

            Text(item.topic)
                .font(AppTheme.Font.subheadline)
                .foregroundStyle(AppTheme.Palette.textSecondary)

            Text(compactStatus)
                .font(AppTheme.Font.caption)
                .foregroundStyle(AppTheme.Palette.primary)
        }
        .padding(AppTheme.Spacing.lg)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(
                cornerRadius: AppTheme.Radius.historyCompactCard,
                style: .continuous
            )
            .fill(AppTheme.Palette.cardBackground)
        )
        .overlay(
            RoundedRectangle(
                cornerRadius: AppTheme.Radius.historyCompactCard,
                style: .continuous
            )
            .stroke(AppTheme.Palette.outline, lineWidth: 1)
        )
        .shadow(
            color: .black.opacity(0.06),
            radius: AppTheme.Elevation.card,
            y: 1
        )
    }

    // MARK: - Stat chip

    /// Ports `HistoryStatChip` (lines 275–312): a 18dp-radius `Surface` on `bg`,
    /// 14dp/12dp padding, an 11sp `fg`-at-80% caption over a 15sp bold value.
    struct StatChip: View {
        let title: String
        let value: String
        let background: Color
        let foreground: Color

        var body: some View {
            VStack(spacing: AppTheme.Spacing.xxs) {
                Text(title)
                    .font(AppTheme.Font.micro)
                    .foregroundStyle(foreground.opacity(0.8))

                Text(value)
                    .font(AppTheme.Font.cardTitle)
                    .foregroundStyle(foreground)
                    .lineLimit(1)
            }
            .frame(maxWidth: .infinity)
            .padding(.horizontal, AppTheme.Spacing.md)
            .padding(.vertical, AppTheme.Spacing.optionGap)
            .background(
                RoundedRectangle(
                    cornerRadius: AppTheme.Radius.materialCard,
                    style: .continuous
                )
                .fill(background)
            )
        }
    }

    // MARK: - Derived values

    /// `"CHALLENGE"`, `"FINAL_TEST"`, `"SINGLE_PLAYER"`, or anything else.
    private var normalizedMode: String {
        item.mode.uppercased()
    }

    /// The `modeColor` / `animateColorAsState` target and the icon tint.
    private var modeColor: Color {
        switch normalizedMode {
        case "CHALLENGE": return AppTheme.Palette.historyModeChallenge
        case "FINAL_TEST": return AppTheme.Palette.historyModeFinalTest
        case "SINGLE_PLAYER": return AppTheme.Palette.historyModeSinglePlayer
        default: return AppTheme.Palette.historyModeDefault
        }
    }

    /// Stands in for `Icons.Default.SportsEsports / Quiz / Star / History`; the
    /// mode-coloured `Icon` tint is reproduced through `AndroidIcon`.
    private var modeGlyph: AndroidAsset {
        switch normalizedMode {
        case "CHALLENGE": return .ic_challenge_swords
        case "FINAL_TEST": return .ic_quiz
        case "SINGLE_PLAYER": return .ic_star_new
        default: return .ic_history
        }
    }

    /// `item.totalQuestions > 0 ? correctAnswers * 100f / totalQuestions : 0f`.
    private var percentage: Float {
        item.totalQuestions > 0
            ? (Float(item.correctAnswers) * 100.0) / Float(item.totalQuestions)
            : 0
    }

    /// `(percentage / 100f).coerceIn(0f, 1f)`.
    private var progressFraction: CGFloat {
        CGFloat(min(max(percentage / 100.0, 0), 1))
    }

    /// `item.title.ifBlank { item.mode }` — the `HistoryCard` fallback chain.
    private var cardTitle: String {
        isBlank(item.title) ? item.mode : item.title
    }

    /// `item.title.ifBlank { item.topic }` — the `onBindViewHolder` fallback chain.
    private var compactTitle: String {
        isBlank(item.title) ? item.topic : item.title
    }

    /// `holder.status.text = "Score: ${item.score} | Correct: …"`.
    private var compactStatus: String {
        "Score: \(item.score) | Correct: \(item.correctAnswers)/\(item.totalQuestions)"
    }

    /// `SimpleDateFormat("dd MMM yyyy • hh:mm a", Locale.getDefault())`.
    ///
    /// Android's `HistoryModel.timestamp` is in milliseconds while the iOS
    /// `QuizHistoryItem.timestamp` is in seconds, so the divisor is inverted
    /// relative to `Date(item.timestamp)`.
    private var formattedTimestamp: String {
        let formatter = DateFormatter()
        formatter.locale = Locale.current
        formatter.dateFormat = "dd MMM yyyy • hh:mm a"
        return formatter.string(from: Date(timeIntervalSince1970: item.timestamp))
    }

    private func isBlank(_ value: String) -> Bool {
        value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }
}
