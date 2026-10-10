import SwiftUI
import Foundation

// MARK: - Tier table

/// Ports the Android `data class RankTier` from `RankActivity.kt` — one rung of
/// the nine-step XP ladder.
///
/// `accentHex` carries Kotlin's `accentColor: Color` literal (`0xFF81C784` etc.)
/// as data rather than as a literal in the view layer, the same way
/// `Warrior.glowColorHex` works.
struct RankProgressionTier: Identifiable, Hashable {

    /// `RankTier.name` — the uppercase rank title shown under the badge.
    let name: String
    /// `RankTier.minExp` — cumulative XP required to unlock the rung.
    let minExp: Int
    /// `RankTier.iconRes`, resolved to the ported `ic_*` portrait drawable.
    let icon: AndroidAsset
    /// Packed `0xAARRGGBB` literal for `RankTier.accentColor`.
    let accentHex: UInt64
    /// `RankTier.description` — the one-line flavour text under the rank title.
    let summary: String

    var id: Int { minExp }

    var accentColor: Color { Color(hex: accentHex) }
}

/// Ports the Kotlin `object RankManager`: the static nine-rung ladder plus the
/// `getCurrentTier` / `getNextTier` lookups that drive the progress ring and the
/// progression card.
///
/// Deliberately **not** `RankTier` — `Components.swift` already owns an enum by
/// that name for the six drawable-backed battle rank portraits (`RankTier.beginner`
/// … `.legend`), which is a different concept from these XP thresholds.
enum RankProgression {

    /// `RankManager.tiers`, verbatim: name, minExp, `ic_*` drawable, accent,
    /// description. Order is significant — `getCurrentTier` relies on ascending
    /// `minExp`.
    static let tiers: [RankProgressionTier] = [
        RankProgressionTier(name: "ASPIRANT", minExp: 0, icon: .ic_beginner,
                            accentHex: 0xFF81C784, summary: "The first step of many."),
        RankProgressionTier(name: "ROOKIE", minExp: 500, icon: .ic_rookie,
                            accentHex: 0xFFCD7F32, summary: "Learning the ropes."),
        RankProgressionTier(name: "SKILLED", minExp: 1500, icon: .ic_skilled,
                            accentHex: 0xFFC0C0C0, summary: "A rising talent."),
        RankProgressionTier(name: "WARRIOR", minExp: 3500, icon: .ic_warrior,
                            accentHex: 0xFFFFD700, summary: "Battle-hardened student."),
        RankProgressionTier(name: "EXPERT", minExp: 7500, icon: .ic_expert,
                            accentHex: 0xFF00BFA5, summary: "Deep mastery of concepts."),
        RankProgressionTier(name: "SCHOLAR", minExp: 15000, icon: .ic_scholar,
                            accentHex: 0xFFB9F2FF, summary: "A true academic force."),
        RankProgressionTier(name: "MASTER", minExp: 30000, icon: .ic_master,
                            accentHex: 0xFFFF4081, summary: "Leading by example."),
        RankProgressionTier(name: "GRANDMASTER", minExp: 60000, icon: .ic_grandmaster,
                            accentHex: 0xFF7B1FFF, summary: "Virtuoso of knowledge."),
        RankProgressionTier(name: "LEGEND", minExp: 100000, icon: .ic_legend,
                            accentHex: 0xFF00E5FF, summary: "The ultimate pinnacle.")
    ]

    /// Ports `RankManager.getCurrentTier(exp)`: the highest rung whose
    /// `minExp` the user has reached.
    ///
    /// Kotlin's `tiers.last { … }` throws for a negative `exp`, crashing the
    /// activity; the clamp keeps the ASPIRANT floor instead.
    static func currentTier(exp: Int) -> RankProgressionTier {
        tiers.last { exp >= $0.minExp } ?? tiers[0]
    }

    /// Ports `RankManager.getNextTier(exp)`: the first rung strictly above
    /// `exp`, or `nil` once LEGEND is reached.
    static func nextTier(exp: Int) -> RankProgressionTier? {
        tiers.first { $0.minExp > exp }
    }

    /// Fraction of the way from `current` to `next`, clamped to `0...1`; `1` at
    /// the top rung. Kotlin computes this twice — once keyed on `userExp` for
    /// the ring, once inside `ProgressionCard` behind a keyless `remember {}`
    /// that froze the bar at its first composition.
    static func progress(exp: Int) -> Double {
        let current = currentTier(exp: exp)
        guard let next = nextTier(exp: exp) else { return 1 }
        let span = Double(next.minExp - current.minExp)
        guard span > 0 else { return 1 }
        return min(max(Double(exp - current.minExp) / span, 0), 1)
    }
}

/// `SharedPreferences("MY_APP")` key for the cached lifetime XP, shared with
/// `MCQActivity` / `DashboardActivity` / `SinglePlayer` on Android.
enum RankProgressStore {
    /// `prefs.getInt("user_exp", 0)`.
    static let userExpKey = "user_exp"

    static func exp(defaults: UserDefaults = .standard) -> Int {
        defaults.integer(forKey: userExpKey)
    }

    /// Mirrors `prefs.edit().putInt("user_exp", currentExp).apply()`.
    static func setExp(_ value: Int, defaults: UserDefaults = .standard) {
        defaults.set(max(0, value), forKey: userExpKey)
    }
}

// MARK: - View model

/// Ports `RankActivity.onCreate` / `RankActivity.onResume`: the two places that
/// re-read `user_exp` from `SharedPreferences` so the badge is never stale after
/// earning XP in a quiz.
///
/// The activity made no network calls, so neither does this — ``load()`` is the
/// `onCreate` read and ``refresh()`` the `onResume` read.
@MainActor
final class RankViewModel: ObservableObject {

    @Published private(set) var state: LoadState<Int> = .idle

    /// Drives the screen's `.errorAlert(...)`. Held on the model rather than in
    /// `@State` so the assignment happens inside a `@MainActor` method instead
    /// of inside a `@Sendable` `.task` closure.
    @Published var alertMessage: String?

    /// The freshly read EXP. Defaults to the last known value so the screen can
    /// paint a tier before the async read lands, matching the activity's
    /// `userExpState` initialiser.
    @Published private(set) var exp: Int = RankProgressStore.exp()

    /// `RankActivity.onCreate` — first read of `user_exp`.
    func load() async {
        RemoteLogger.log(tag: "RankActivity_exp", message: "Reading user_exp from SharedPreferences(\"MY_APP\")")
        state = await LoadState.result { RankProgressStore.exp() }
        exp = state.value ?? exp
        alertMessage = state.errorMessage
    }

    /// `RankActivity.onResume` — re-read on every foreground, which is what
    /// kept the badge fresh after a quiz awarded XP.
    func refresh() async {
        let latest = RankProgressStore.exp()
        state = .loaded(latest)
        exp = latest
    }

    /// Write-through hook for the screens that award XP
    /// (`MCQActivity`'s `putInt("user_exp", …)`), so the next `refresh()` — or
    /// the next `RankView` appearance — already shows the new tier.
    func setExp(_ value: Int) {
        RankProgressStore.setExp(value)
        exp = max(0, value)
        state = .loaded(exp)
    }

    var currentTier: RankProgressionTier { RankProgression.currentTier(exp: exp) }
    var nextTier: RankProgressionTier? { RankProgression.nextTier(exp: exp) }
    var progress: Double { RankProgression.progress(exp: exp) }
}

// MARK: - Screen

/// Rank progression. Ports `RankActivity` / `RankScreen` / `ProgressionCard` /
/// `RankBadgesGrid` / `BadgeSmallItem`.
///
/// **This is not the leaderboard.** `RankActivity` shows the student's own XP
/// ladder: a swept progress ring around the current tier's portrait, the XP
/// needed for the next rung, and a grid of every badge with the locked ones
/// dimmed. `LeaderboardView` (batch 26) shows other students' scores; the two
/// share nothing but the word "rank".
struct RankView: View {

    /// Android rebuilt the whole five-item `BottomNavigation` inside
    /// `RankActivity`'s `Scaffold`. iOS already hosts this screen under the
    /// shell's shared `BottomNavBar`, so that bar is not duplicated here —
    /// ``onOpenTab`` carries the activity's `startActivity` fan-out instead.
    let onOpenTab: (BaseNavigationItem) -> Void

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.dismiss) private var dismiss

    @StateObject private var viewModel = RankViewModel()

    init(onOpenTab: @escaping (BaseNavigationItem) -> Void = { _ in }) {
        self.onOpenTab = onOpenTab
    }

    var body: some View {
        Group {
            switch viewModel.state {
            case .idle, .loading:
                LoadingStateView(message: "Loading your rank…")
            case .failed, .loaded:
                // Kotlin had no error surface at all — the screen reads a local
                // preference and always renders the last known rung — so a failed
                // read keeps the tier on screen and only raises the alert.
                content
            }
        }
        .screenBackground()
        .baseScreen("RankActivity", style: .material)
        .navigationBarBackButtonHidden(true)
        .task { await viewModel.load() }
        .onChange(of: scenePhase) { phase in
            guard phase == .active else { return }
            Task { await viewModel.refresh() }
        }
        .refreshable { await viewModel.refresh() }
        .errorAlert(message: $viewModel.alertMessage)
    }

    // MARK: - Content

    private var content: some View {
        ScrollView {
            VStack(spacing: 0) {
                header

                RankProgressRing(
                    tier: viewModel.currentTier,
                    progress: viewModel.progress
                )
                .padding(.top, AppTheme.Spacing.rankBadgeTop)

                tierCaption

                RankProgressionCard(
                    exp: viewModel.exp,
                    current: viewModel.currentTier,
                    next: viewModel.nextTier
                )
                .padding(.top, AppTheme.Spacing.rankSectionTop)

                VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                    Text("ALL RANK BADGES")
                        .font(AppTheme.Font.bodyBold)
                        .foregroundStyle(AppTheme.Palette.textPrimary)

                    RankBadgesGrid(exp: viewModel.exp)
                }
                .padding(.top, AppTheme.Spacing.rankBadgesTop)

                Spacer(minLength: AppTheme.Spacing.rankScrollTail)
            }
            .padding(AppTheme.Spacing.lg)
        }
    }

    /// `RankScreen`'s header `Row`: back chevron, centred title, and a trailing
    /// spacer the same width as the button so the title stays optically centred.
    private var header: some View {
        HStack(spacing: AppTheme.Spacing.lg) {
            Button {
                self.dismiss()
            } label: {
                Image(systemName: "chevron.backward")
                    .font(.system(size: 17, weight: .semibold))
                    .foregroundStyle(AppTheme.Palette.textPrimary)
            }
            .accessibilityLabel("Back")

            Text("RANK PROGRESSION")
                .font(AppTheme.Font.rankTitle)
                .foregroundStyle(AppTheme.Palette.textPrimary)
                .frame(maxWidth: .infinity)

            // Balances the back button, as in Kotlin.
            Spacer().frame(width: AppTheme.Spacing.rankHeaderBalance)
        }
    }

    private var tierCaption: some View {
        VStack {
            Text(viewModel.currentTier.name)
                .font(AppTheme.Font.rankTierName)
                .foregroundStyle(viewModel.currentTier.accentColor)
                .multilineTextAlignment(.center)

            Text(viewModel.currentTier.summary)
                .font(AppTheme.Font.rankDescription)
                .foregroundStyle(AppTheme.Palette.textSecondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, AppTheme.Spacing.xxl)
        }
        .padding(.top, AppTheme.Spacing.lg)
    }
}

// MARK: - Progress ring

/// Ports the `Box(Modifier.drawBehind { … })` badge: a 15%-alpha accent track
/// circle with the tier accent swept round it from 12 o'clock, round-capped.
private struct RankProgressRing: View {

    let tier: RankProgressionTier
    let progress: Double

    var body: some View {
        ZStack {
            Circle()
                .stroke(
                    tier.accentColor.opacity(0.15),
                    lineWidth: AppTheme.Spacing.rankRingWidth
                )

            Circle()
                .trim(from: 0, to: progress)
                .stroke(
                    tier.accentColor,
                    style: StrokeStyle(
                        lineWidth: AppTheme.Spacing.rankRingWidth,
                        lineCap: .round
                    )
                )
                .rotationEffect(.degrees(-90))

            Image(tier.icon.rawValue)
                .resizable()
                .scaledToFit()
                .frame(
                    width: AppTheme.Spacing.rankBadgeArt,
                    height: AppTheme.Spacing.rankBadgeArt
                )
                .accessibilityLabel(tier.name)
        }
        .frame(
            width: AppTheme.Spacing.rankRingDiameter,
            height: AppTheme.Spacing.rankRingDiameter
        )
    }
}

// MARK: - Progression card

/// Ports `ProgressionCard(userExp, current, next)`: current XP, the goal for the
/// next rung, the gradient bar and the "N XP needed for X" line.
private struct RankProgressionCard: View {

    let exp: Int
    let current: RankProgressionTier
    let next: RankProgressionTier?

    private var progress: Double {
        guard let next else { return 1 }
        let span = Double(next.minExp - current.minExp)
        guard span > 0 else { return 1 }
        return min(max(Double(exp - current.minExp) / span, 0), 1)
    }

    var body: some View {
        VStack(spacing: AppTheme.Spacing.rankGap) {
            HStack {
                Text("\(exp) XP")
                    .font(AppTheme.Font.bodyBold)
                    .foregroundStyle(AppTheme.Palette.textSecondary)
                Spacer()
                if let next {
                    Text("Goal: \(next.minExp) XP")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary.opacity(0.6))
                }
            }

            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    Capsule()
                        .fill(AppTheme.Palette.outline.opacity(0.2))
                    Capsule()
                        .fill(
                            LinearGradient(
                                colors: [AppTheme.Palette.primary, AppTheme.Palette.secondary],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(width: geometry.size.width * progress)
                }
            }
            .frame(height: AppTheme.Spacing.rankBarHeight)

            if let next {
                Text("\(next.minExp - exp) XP needed for \(next.name)")
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Palette.primary)
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
            }
        }
        .padding(AppTheme.Spacing.xxl)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.rankProgressionCard, style: .continuous)
                .fill(AppTheme.Palette.cardBackgroundElevated)
        )
        .overlay(
            RoundedRectangle(cornerRadius: AppTheme.Radius.rankProgressionCard, style: .continuous)
                .stroke(AppTheme.Palette.outline.opacity(0.2), lineWidth: 1)
        )
    }
}

// MARK: - Badge grid

/// Ports `RankBadgesGrid(userExp)`: nine badges in rows of three, laid out as
/// `Column` + `Row` because Kotlin needed the whole thing inside one vertical
/// scroll state.
private struct RankBadgesGrid: View {

    let exp: Int

    /// Kotlin's `chunked(3)`; nine tiers make three full rows.
    private var rows: [[RankProgressionTier]] {
        stride(from: 0, to: RankProgression.tiers.count, by: 3).map { start in
            Array(RankProgression.tiers[start..<min(start + 3, RankProgression.tiers.count)])
        }
    }

    var body: some View {
        VStack(spacing: AppTheme.Spacing.lg) {
            ForEach(Array(rows.enumerated()), id: \.offset) { _, row in
                HStack(spacing: AppTheme.Spacing.lg) {
                    ForEach(Array(row.enumerated()), id: \.offset) { _, tier in
                        RankBadgeCell(tier: tier, isUnlocked: exp >= tier.minExp)
                    }
                    if row.count < 3 {
                        ForEach(0..<(3 - row.count), id: \.self) { _ in
                            Spacer()
                        }
                    }
                }
            }
        }
    }
}

/// Ports `BadgeSmallItem(tier, isUnlocked)`: dimmed portrait plus the rung name
/// and its XP threshold.
private struct RankBadgeCell: View {

    let tier: RankProgressionTier
    let isUnlocked: Bool

    var body: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            ZStack {
                if !isUnlocked {
                    Color.black.opacity(0.6)
                }
                Image(tier.icon.rawValue)
                    .resizable()
                    .scaledToFit()
                    .frame(
                        width: AppTheme.Spacing.rankBadgeCellArt,
                        height: AppTheme.Spacing.rankBadgeCellArt
                    )
            }
            .frame(
                width: AppTheme.Spacing.rankBadgeCellArt,
                height: AppTheme.Spacing.rankBadgeCellArt
            )
            .opacity(isUnlocked ? 1 : 0.3)

            Text(tier.name)
                .font(AppTheme.Font.rankBadgeName)
                .foregroundStyle(
                    isUnlocked
                        ? AppTheme.Palette.textSecondary
                        : AppTheme.Palette.textSecondary.opacity(0.4)
                )
                .lineLimit(1)

            Text("\(tier.minExp) XP")
                .font(AppTheme.Font.rankBadgeXP)
                .foregroundStyle(
                    isUnlocked ? tier.accentColor : AppTheme.Palette.textSecondary.opacity(0.2)
                )
        }
        .frame(maxWidth: .infinity)
        .padding(AppTheme.Spacing.rankGap)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(
                    isUnlocked
                        ? AppTheme.Palette.cardBackgroundElevated
                        : AppTheme.Palette.surface.opacity(0.5)
                )
        )
    }
}

// MARK: - Local design tokens

/// Sizes Kotlin wrote as bare `dp` literals inside `RankActivity.kt`. Declared
/// here — rather than inlined — so no spacing value in this screen is a magic
/// number.
private extension AppTheme.Spacing {
    /// 48dp — the spacer that balances the back button in the header row.
    static let rankHeaderBalance: CGFloat = 48
    /// 30dp — gap between the header and the badge ring.
    static let rankBadgeTop: CGFloat = 30
    /// 220dp — outer diameter of the progress ring.
    static let rankRingDiameter: CGFloat = 220
    /// 140dp — portrait art inside the ring.
    static let rankBadgeArt: CGFloat = 140
    /// 6dp — ring stroke width.
    static let rankRingWidth: CGFloat = 6
    /// 40dp — gap above the progression card.
    static let rankSectionTop: CGFloat = 40
    /// 32dp — gap above the badge grid.
    static let rankBadgesTop: CGFloat = 32
    /// 50dp — tail padding under the last row of badges.
    static let rankScrollTail: CGFloat = 50
    /// 12dp — `ProgressionCard`'s inner gap and the badge cell's padding.
    static let rankGap: CGFloat = 12
    /// 12dp — progression bar height.
    static let rankBarHeight: CGFloat = 12
    /// 50dp — portrait art in a grid cell.
    static let rankBadgeCellArt: CGFloat = 50
}

/// 24dp — `ProgressionCard`'s `RoundedCornerShape(24.dp)`.
private extension AppTheme.Radius {
    static let rankProgressionCard: CGFloat = 24
}

/// Weights and sizes `RankActivity.kt` specified inline (`FontWeight.Black`,
/// `FontWeight.ExtraBold`, 10sp and 9sp captions) and that the shared scale does
/// not yet cover.
private extension AppTheme.Font {
    /// 20sp Black — "RANK PROGRESSION".
    static let rankTitle = SwiftUI.Font.system(size: 20, weight: .black)
    /// 32sp ExtraBold — the current tier's name.
    static let rankTierName = SwiftUI.Font.system(size: 32, weight: .heavy)
    /// 14sp — the tier's flavour line.
    static let rankDescription = SwiftUI.Font.system(size: 14)
    /// 10sp Bold — a badge's name in the grid.
    static let rankBadgeName = SwiftUI.Font.system(size: 10, weight: .bold)
    /// 9sp — a badge's XP threshold.
    static let rankBadgeXP = SwiftUI.Font.system(size: 9)
}

#Preview {
    NavigationStack {
        RankView()
            .environmentObject(SessionStore())
            .environment(\.api, .live)
    }
}
