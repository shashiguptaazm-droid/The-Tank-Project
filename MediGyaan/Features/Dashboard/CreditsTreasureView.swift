import SwiftUI

/// iOS equivalent of Android `CreditsTreasureActivity.kt`.
///
/// Treasury and economy screen displaying student credit balance, 24h Daily Mystery Chest
/// with live countdown ticker, rank progression milestones, limited special offers, and store packages.
struct CreditsTreasureView: View {

    @ObservedObject private var credits = CreditsManager.shared
    @EnvironmentObject private var session: SessionStore

    @State private var selectedTab: TreasuryCategory = .all
    @State private var remainingSeconds: TimeInterval = 0
    @State private var rewardAlertMessage: String?
    @State private var showingRewardAlert = false
    @State private var isChestOpening = false

    private let timer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()

    enum TreasuryCategory: String, CaseIterable, Identifiable {
        case all = "All"
        case chest = "Daily Chest"
        case ranks = "Rank Tiers"
        case offers = "Special Offers"
        case store = "Packs"

        var id: String { rawValue }
    }

    var body: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.lg) {
                // Header Balance Card
                treasuryBalanceCard

                // Filter Category Chips
                categorySelector

                // Sections according to filter
                if selectedTab == .all || selectedTab == .chest {
                    dailyChestSection
                }

                if selectedTab == .all || selectedTab == .offers {
                    specialOffersSection
                }

                if selectedTab == .all || selectedTab == .ranks {
                    rankMilestonesSection
                }

                if selectedTab == .all || selectedTab == .store {
                    creditPackagesSection
                }
            }
            .padding(AppTheme.Spacing.md)
        }
        .screenBackground()
        .navigationTitle("Treasury & Store")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            remainingSeconds = credits.dailyChestRemainingSeconds
        }
        .onReceive(timer) { _ in
            remainingSeconds = credits.dailyChestRemainingSeconds
        }
        .alert(isPresented: $showingRewardAlert) {
            Alert(
                title: Text("Bounty Awarded!"),
                message: Text(rewardAlertMessage ?? ""),
                dismissButton: .default(Text("Claim"))
            )
        }
    }

    // MARK: - Balance Card

    private var treasuryBalanceCard: some View {
        CardContainer {
            HStack(spacing: AppTheme.Spacing.md) {
                ZStack {
                    Circle()
                        .fill(AppTheme.Palette.primary.opacity(0.18))
                        .frame(width: 54, height: 54)

                    Image(systemName: "circle.circle.fill")
                        .font(.system(size: 28))
                        .foregroundStyle(Color.yellow)
                }

                VStack(alignment: .leading, spacing: 2) {
                    Text("Treasury Credits")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary)

                    Text("\(credits.currentCredits)")
                        .font(.system(size: 30, weight: .black, design: .rounded))
                        .foregroundStyle(AppTheme.Palette.textPrimary)
                }

                Spacer()

                VStack(alignment: .trailing, spacing: 2) {
                    Text("XP Status")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textMuted)

                    Text("\(session.user?.xp ?? 0) XP")
                        .font(AppTheme.Font.callout.weight(.bold))
                        .foregroundStyle(AppTheme.Palette.primary)
                }
            }
            .padding(.vertical, AppTheme.Spacing.xs)
        }
    }

    // MARK: - Category Chips

    private var categorySelector: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: AppTheme.Spacing.xs) {
                ForEach(TreasuryCategory.allCases) { tab in
                    Button {
                        selectedTab = tab
                    } label: {
                        Text(tab.rawValue)
                            .font(AppTheme.Font.caption.weight(.semibold))
                            .padding(.horizontal, 14)
                            .padding(.vertical, 8)
                            .background(
                                Capsule().fill(
                                    selectedTab == tab
                                        ? AppTheme.Palette.primary
                                        : AppTheme.Palette.cardBackgroundElevated
                                )
                            )
                            .foregroundStyle(
                                selectedTab == tab
                                    ? Color.white
                                    : AppTheme.Palette.textSecondary
                            )
                    }
                }
            }
        }
    }

    // MARK: - Daily Chest Section

    private var dailyChestSection: some View {
        CardContainer {
            VStack(spacing: AppTheme.Spacing.md) {
                HStack {
                    Label("Daily Mystery Chest", systemImage: "archivebox.fill")
                        .font(AppTheme.Font.headline)
                        .foregroundStyle(AppTheme.Palette.warning)
                    Spacer()
                }

                ZStack {
                    Circle()
                        .fill(Color.orange.opacity(0.15))
                        .frame(width: 80, height: 80)

                    Image(systemName: "gift.fill")
                        .font(.system(size: 38))
                        .foregroundStyle(Color.orange)
                        .rotationEffect(.degrees(isChestOpening ? 15 : 0))
                        .animation(isChestOpening ? .easeInOut(duration: 0.1).repeatCount(6, autoreverses: true) : .default, value: isChestOpening)
                }

                if credits.canOpenDailyChest {
                    Text("Chest is ready to unlock! Contains 150 – 350 Credits.")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary)

                    Button {
                        triggerOpenChest()
                    } label: {
                        Text("Open Mystery Chest")
                            .font(AppTheme.Font.headline)
                            .foregroundStyle(Color.white)
                            .frame(maxWidth: .infinity)
                            .frame(height: 46)
                            .background(RoundedRectangle(cornerRadius: AppTheme.Radius.md).fill(Color.orange))
                    }
                } else {
                    VStack(spacing: 4) {
                        Text("Cooldown in progress")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.textMuted)

                        Text(formattedRemainingTime(remainingSeconds))
                            .font(.system(size: 20, weight: .bold, design: .monospaced))
                            .foregroundStyle(AppTheme.Palette.textPrimary)
                    }
                }
            }
            .padding(.vertical, AppTheme.Spacing.xs)
        }
    }

    // MARK: - Special Offers

    private var specialOffersSection: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            Label("Limited Offers", systemImage: "sparkles")
                .font(AppTheme.Font.title3)
                .foregroundStyle(AppTheme.Palette.textPrimary)

            ForEach(credits.specialOffers) { offer in
                CardContainer {
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            if let bonus = offer.bonusText {
                                Text(bonus)
                                    .font(.system(size: 10, weight: .black))
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(Capsule().fill(Color.red.opacity(0.2)))
                                    .foregroundStyle(Color.red)
                            }

                            Text(offer.title)
                                .font(AppTheme.Font.headline)
                                .foregroundStyle(AppTheme.Palette.textPrimary)

                            Text("\(offer.credits) Credits")
                                .font(AppTheme.Font.caption)
                                .foregroundStyle(Color.yellow)
                        }

                        Spacer()

                        Button {
                            // Simulator purchase handler
                            credits.addCredits(offer.credits)
                            rewardAlertMessage = "Purchased \(offer.title)! +\(offer.credits) Credits added to your treasury."
                            showingRewardAlert = true
                        } label: {
                            Text(offer.priceInr)
                                .font(AppTheme.Font.callout.weight(.bold))
                                .foregroundStyle(Color.white)
                                .padding(.horizontal, 16)
                                .padding(.vertical, 8)
                                .background(RoundedRectangle(cornerRadius: AppTheme.Radius.sm).fill(AppTheme.Palette.primary))
                        }
                    }
                }
            }
        }
    }

    // MARK: - Rank Milestones

    private var rankMilestonesSection: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            Label("Rank Progression Bounties", systemImage: "shield.lefthalf.filled")
                .font(AppTheme.Font.title3)
                .foregroundStyle(AppTheme.Palette.textPrimary)

            ForEach(credits.rankMilestones) { milestone in
                let currentXp = session.user?.xp ?? 0
                let isClaimed = credits.isRankClaimed(milestone.tierName)
                let canClaim = credits.canClaimRankReward(milestone, currentXp: currentXp)

                CardContainer {
                    HStack(spacing: AppTheme.Spacing.md) {
                        Image(systemName: milestone.iconSystemName)
                            .font(.system(size: 24))
                            .foregroundStyle(isClaimed ? AppTheme.Palette.success : (canClaim ? AppTheme.Palette.primary : AppTheme.Palette.textMuted))
                            .frame(width: 32)

                        VStack(alignment: .leading, spacing: 2) {
                            Text(milestone.tierName)
                                .font(AppTheme.Font.headline)
                                .foregroundStyle(AppTheme.Palette.textPrimary)

                            Text("\(milestone.requiredXp) XP required • Reward: +\(milestone.creditReward) Credits")
                                .font(AppTheme.Font.caption)
                                .foregroundStyle(AppTheme.Palette.textSecondary)
                        }

                        Spacer()

                        if isClaimed {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundStyle(AppTheme.Palette.success)
                        } else if canClaim {
                            Button {
                                if credits.claimRankReward(milestone, currentXp: currentXp) {
                                    rewardAlertMessage = "Level \(milestone.level) \(milestone.tierName) Achieved! +\(milestone.creditReward) Credits."
                                    showingRewardAlert = true
                                }
                            } label: {
                                Text("Claim")
                                    .font(AppTheme.Font.caption.weight(.bold))
                                    .foregroundStyle(Color.white)
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 6)
                                    .background(Capsule().fill(AppTheme.Palette.success))
                            }
                        } else {
                            Text("Locked")
                                .font(AppTheme.Font.caption2)
                                .foregroundStyle(AppTheme.Palette.textMuted)
                        }
                    }
                }
            }
        }
    }

    // MARK: - Store Packages

    private var creditPackagesSection: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            Label("Credit Packs", systemImage: "bag.fill")
                .font(AppTheme.Font.title3)
                .foregroundStyle(AppTheme.Palette.textPrimary)

            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: AppTheme.Spacing.sm) {
                ForEach(credits.storePackages) { pack in
                    CardContainer {
                        VStack(spacing: AppTheme.Spacing.xs) {
                            if let bonus = pack.bonusText {
                                Text(bonus)
                                    .font(.system(size: 9, weight: .bold))
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(Capsule().fill(Color.orange.opacity(0.2)))
                                    .foregroundStyle(Color.orange)
                            }

                            Text(pack.title)
                                .font(AppTheme.Font.caption.weight(.bold))
                                .foregroundStyle(AppTheme.Palette.textPrimary)
                                .lineLimit(1)

                            Text("\(pack.credits)")
                                .font(.system(size: 20, weight: .black, design: .rounded))
                                .foregroundStyle(Color.yellow)

                            Text("Credits")
                                .font(AppTheme.Font.caption2)
                                .foregroundStyle(AppTheme.Palette.textSecondary)

                            Button {
                                credits.addCredits(pack.credits)
                                rewardAlertMessage = "Purchased \(pack.title)! +\(pack.credits) Credits credited."
                                showingRewardAlert = true
                            } label: {
                                Text(pack.priceInr)
                                    .font(AppTheme.Font.caption.weight(.bold))
                                    .foregroundStyle(Color.white)
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 6)
                                    .background(RoundedRectangle(cornerRadius: AppTheme.Radius.sm).fill(AppTheme.Palette.primary))
                            }
                            .padding(.top, 4)
                        }
                    }
                }
            }
        }
    }

    // MARK: - Helpers

    private func triggerOpenChest() {
        isChestOpening = true
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            let reward = credits.openDailyChest()
            isChestOpening = false
            rewardAlertMessage = "You unlocked the Daily Mystery Chest! Found +\(reward) Credits."
            showingRewardAlert = true
        }
    }

    private func formattedRemainingTime(_ sec: TimeInterval) -> String {
        let hours = Int(sec) / 3600
        let minutes = (Int(sec) % 3600) / 60
        let seconds = Int(sec) % 60
        return String(format: "%02d:%02d:%02d", hours, minutes, seconds)
    }
}
