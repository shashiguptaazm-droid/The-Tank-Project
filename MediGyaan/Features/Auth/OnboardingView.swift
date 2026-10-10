import SwiftUI
import UIKit

/// A single card in the onboarding carousel.
///
/// Ports the `data class OnboardingPage` declared at the bottom of
/// `OnboardingActivity.kt`: the same six entries, in the same order, carrying
/// the same copy, glyph and accent. `ImageVector` becomes an SF Symbol name
/// because the Android glyphs come from `material-icons-extended` rather than
/// from `res/drawable`, so there is no ported artwork to reuse.
struct OnboardingPage: Identifiable {

    /// Stable identity: the page's position in the carousel.
    let id: Int
    let title: String
    let description: String
    /// Stand-in for the Android `Icons.Filled.*` vector.
    let systemImage: String
    /// Page accent, reused by the aura, badge, pill indicator and CTA fill.
    let glow: Color
    let badgeTag: String

    /// The fixed six-page list, mirroring `OnboardingScreen()`'s `remember { listOf(...) }`.
    static let all: [OnboardingPage] = [
        OnboardingPage(
            id: 0,
            title: "Welcome to MediGyaan",
            description: "Your AI-powered NEET PG & clinical learning warrior companion",
            systemImage: "sparkles",
            glow: AppTheme.Ink.cyan,
            badgeTag: "Anatomy & Physiology Foundation"
        ),
        OnboardingPage(
            id: 1,
            title: "24/7 Medical AI Chat",
            description: "Instant differential diagnoses, PubMed citations & clinical pearls",
            systemImage: "bubble.left.and.bubble.right.fill",
            glow: OnboardingPalette.azure,
            badgeTag: "Clinical AI Assistant"
        ),
        OnboardingPage(
            id: 2,
            title: "NEET PG College Predictor",
            description: "AI admission chance analyzer based on rank, category & quotas",
            systemImage: "house.fill",
            glow: OnboardingPalette.gold,
            badgeTag: "College Admission Engine"
        ),
        OnboardingPage(
            id: 3,
            title: "Rank Badge Hierarchy",
            description: "Ascend from Aspirant to Legend with every correct diagnosis",
            systemImage: "heart.fill",
            glow: OnboardingPalette.pink,
            badgeTag: "Gamified Mastery Tiers"
        ),
        OnboardingPage(
            id: 4,
            title: "Tactical 4-Power MCQs",
            description: "Activate Fascial Scan, Defibrillator Shock & High-Yield Surge",
            systemImage: "magnifyingglass",
            glow: OnboardingPalette.green,
            badgeTag: "Interactive Combat MCQs"
        ),
        OnboardingPage(
            id: 5,
            title: "1v1 Spire Battle Arena",
            description: "Challenge peer residents, claim credits & conquer leaderboards",
            systemImage: "message.fill",
            glow: AppTheme.Ink.gold,
            badgeTag: "Multiplayer Arena"
        )
    ]
}

/// Accent colours carried over verbatim from `OnboardingActivity.kt`'s page list.
///
/// `#00E5FF` and `#F4C95D` already exist as `AppTheme.Ink.cyan` and
/// `AppTheme.Ink.gold`, so those two are referenced instead of redeclared. The
/// rest have no token in `AppTheme`, so they are declared here rather than
/// silently swapped for a lookalike.
fileprivate enum OnboardingPalette {
    /// `#38BDF8` — page 2, "24/7 Medical AI Chat".
    static let azure = Color(hex: 0x38BDF8)
    /// `#FFD700` — page 3, "NEET PG College Predictor".
    static let gold = Color(hex: 0xFFD700)
    /// `#FF4081` — page 4, "Rank Badge Hierarchy".
    static let pink = Color(hex: 0xFF4081)
    /// `#00E676` — page 5, "Tactical 4-Power MCQs".
    static let green = Color(hex: 0x00E676)
    /// `#050816` — the Android `Scaffold(containerColor = Color(0xFF050816))` canvas.
    static let canvas = Color(hex: 0x050816)
    /// `#0F172A` — fill of the 110dp icon disc.
    static let disc = Color(hex: 0x0F172A)
    /// `#1E293B` — inactive page-indicator pill.
    static let pillIdle = Color(hex: 0x1E293B)
    /// `#94A3B8` — SKIP label and subtitle copy.
    static let muted = Color(hex: 0x94A3B8)
}

/// Paged onboarding carousel. Ports `OnboardingScreen()` from
/// `OnboardingActivity.kt`.
///
/// Replaces Compose `HorizontalPager` with `TabView`'s `.page` style so the
/// swipe gesture, the spring pill indicators and the per-page accent colour
/// all behave as they do on Android. The "MEDIGYAAN / SKIP" header and the
/// indicator-plus-CTA footer are fixed chrome, matching the Android `Scaffold`
/// `topBar` and `bottomBar` slots.
///
/// Writing the completion flag is this view's job (Android's
/// `completeOnboarding()`); deciding *when* the screen appears is `RootView`'s.
struct OnboardingView: View {

    /// `UserDefaults` key behind Android's
    /// `SharedPreferences("MY_APP").putBoolean("onboarding_complete", true)`.
    ///
    /// `AppPreferences` has no token for it yet, so the literal lives here
    /// pending promotion alongside the rest of the keys. The value is chosen so
    /// that promotion is a move, not a rewrite.
    static let defaultsKey = "mg.onboardingComplete"

    /// Mirrors the `prefs.getBoolean("onboarding_complete", false)` gate read by
    /// both `OnboardingActivity.onCreate` and `SplashActivity.checkNavigationState()`.
    static var hasCompletedOnboarding: Bool {
        UserDefaults.standard.bool(forKey: defaultsKey)
    }

    /// Index of the visible page. Drives the pill indicators and the CTA label,
    /// exactly as `pagerState.currentPage` does on Android.
    @State private var selection: Int = 0

    /// Called after the flag is written, so the host can swap its root screen.
    var onFinished: (() -> Void)? = nil

    private var isLastPage: Bool {
        selection >= OnboardingPage.all.count - 1
    }

    /// Android indexes `pages[pagerState.currentPage]` unguarded; the clamp is
    /// kept because a stale `selection` would otherwise trap at runtime.
    private var currentPage: OnboardingPage {
        let pages = OnboardingPage.all
        return pages[min(max(selection, 0), pages.count - 1)]
    }

    var body: some View {
        ZStack {
            OnboardingPalette.canvas.ignoresSafeArea()

            VStack(spacing: 0) {
                topBar

                TabView(selection: $selection) {
                    ForEach(OnboardingPage.all) { page in
                        pageBody(page)
                            .tag(page.id)
                    }
                }
                .tabViewStyle(.page(indexDisplayMode: .never))

                bottomBar
            }
        }
        .onAppear {
            RemoteLogger.log(tag: "OnboardingView_onAppear", message: "Onboarding pager shown")
        }
    }

    // MARK: - Chrome

    private var topBar: some View {
        HStack(alignment: .center) {
            Text("MEDIGYAAN")
                .font(AppTheme.Font.callout.weight(.bold))
                .tracking(2)
                .foregroundStyle(.white.opacity(0.85))

            Spacer(minLength: 0)

            Button(action: { complete() }) {
                Text("SKIP")
                    .font(AppTheme.Font.captionBold)
                    .tracking(1)
                    .foregroundStyle(OnboardingPalette.muted)
            }
            .accessibilityLabel("Skip onboarding")
        }
        .padding(.horizontal, AppTheme.Spacing.xl)
        .padding(.vertical, AppTheme.Spacing.md)
    }

    private var bottomBar: some View {
        HStack(alignment: .center) {
            HStack(spacing: AppTheme.Spacing.xs) {
                ForEach(OnboardingPage.all) { page in
                    Capsule()
                        .fill(page.id == selection ? page.glow : OnboardingPalette.pillIdle)
                        .frame(width: page.id == selection ? 24 : 8, height: 8)
                }
            }

            Spacer(minLength: 0)

            Button(action: { advance() }) {
                Text(isLastPage ? "GET STARTED \u{1F680}" : "NEXT \u{2192}")
                    .font(AppTheme.Font.subheadline.weight(.bold))
                    .tracking(1)
                    .foregroundStyle(OnboardingPalette.canvas)
                    .padding(.horizontal, AppTheme.Spacing.xl)
                    .padding(.vertical, AppTheme.Spacing.sm)
                    .background(
                        RoundedRectangle(
                            cornerRadius: AppTheme.Radius.dashboardCard,
                            style: .continuous
                        )
                        .fill(currentPage.glow)
                    )
            }
            .accessibilityLabel(isLastPage ? "Get started" : "Next")
        }
        .padding(.horizontal, AppTheme.Spacing.xxl)
        .padding(.vertical, AppTheme.Spacing.xl)
    }

    // MARK: - Page

    private func pageBody(_ page: OnboardingPage) -> some View {
        VStack(spacing: 0) {
            aura(for: page)

            Spacer().frame(height: AppTheme.Spacing.xxl)

            badge(for: page)

            Spacer().frame(height: AppTheme.Spacing.lg)

            Text(page.title)
                .font(AppTheme.Font.title)
                .foregroundStyle(.white)
                .multilineTextAlignment(.center)
                .accessibilityLabel(page.title)

            Spacer().frame(height: AppTheme.Spacing.sm)

            Text(page.description)
                .font(AppTheme.Font.body)
                .foregroundStyle(OnboardingPalette.muted)
                .multilineTextAlignment(.center)
                .lineSpacing(6)
                .accessibilityLabel(page.description)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(.horizontal, AppTheme.Spacing.xxl)
    }

    private func aura(for page: OnboardingPage) -> some View {
        ZStack {
            Circle()
                .fill(
                    RadialGradient(
                        colors: [page.glow.opacity(0.35), page.glow.opacity(0.08), .clear],
                        center: .center,
                        startRadius: 0,
                        endRadius: 95
                    )
                )
                .frame(width: 190, height: 190)

            Circle()
                .fill(OnboardingPalette.disc)
                .frame(width: 110, height: 110)
                .overlay(
                    Circle().stroke(
                        LinearGradient(
                            colors: [page.glow, page.glow.opacity(0.3)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ),
                        lineWidth: 1
                    )
                )

            Image(systemName: page.systemImage)
                .font(.system(size: 54))
                .foregroundStyle(page.glow)
        }
        .frame(width: 190, height: 190)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(page.title) - \(page.badgeTag)")
    }

    private func badge(for page: OnboardingPage) -> some View {
        Text(page.badgeTag.uppercased())
            .font(AppTheme.Font.micro.weight(.bold))
            .tracking(1.5)
            .foregroundStyle(page.glow)
            .padding(.horizontal, AppTheme.Spacing.md)
            .padding(.vertical, AppTheme.Spacing.xxs)
            .background(
                RoundedRectangle(
                    cornerRadius: AppTheme.Radius.option,
                    style: .continuous
                )
                .fill(page.glow.opacity(0.12))
            )
            .overlay(
                RoundedRectangle(
                    cornerRadius: AppTheme.Radius.option,
                    style: .continuous
                )
                .stroke(
                    LinearGradient(
                        colors: [page.glow.opacity(0.5), page.glow.opacity(0.2)],
                        startPoint: .leading,
                        endPoint: .trailing
                    ),
                    lineWidth: 1
                )
            )
    }

    // MARK: - Actions

    /// Android's button lambda: haptic tap, then either `animateScrollToPage`
    /// or `completeOnboarding()` on the final page.
    private func advance() {
        UIImpactFeedbackGenerator(style: .light).impactOccurred()

        guard isLastPage else {
            withAnimation(.spring(response: 0.45, dampingFraction: 0.8)) {
                selection += 1
            }
            return
        }

        complete()
    }

    /// Android's `completeOnboarding()`: `CONFIRM` haptic, persist
    /// `onboarding_complete`, then hand off to the login screen.
    private func complete() {
        UINotificationFeedbackGenerator().notificationOccurred(.success)
        UserDefaults.standard.set(true, forKey: Self.defaultsKey)
        onFinished?()
    }
}

#Preview {
    OnboardingView()
}