import Foundation

/// Credits and store economy manager for MediGyaan iOS.
///
/// 1:1 port of Android `CreditsManager.kt`.
/// Controls credit balance, character ownership hierarchy, rank badge milestone
/// awards, 24h daily mystery chests, store packages, and NEET PG predictor entitlement.
public final class CreditsManager: ObservableObject {

    public static let shared = CreditsManager()

    private let userDefaults = UserDefaults.standard
    private let keyCredits = "user_credits"
    private let keyOwnedAvatars = "owned_avatar_indices"
    private let keyClaimedRanks = "claimed_rank_level_rewards"
    private let keyLastDailyChest = "last_daily_chest_time_ms"
    private let keyPredictorPass = "predict_college_pass"

    public static let starterAvatarIndex = 1001 // Anatomy • Axiom (Pre-owned free starter)
    public static let defaultStarterCredits = 250 // Initial welcome credits

    // ─── 1. AVATAR CREDIT PRICING HIERARCHY ───
    private let avatarCreditCosts: [Int: Int] = [
        1001: 0,      // Anatomy (Pre-owned Free Starter)
        1002: 500,    // Physiology & Cardiac
        1003: 800,    // Biochemistry & Genetics
        1007: 1200,   // Forensic Medicine & Toxicology
        1006: 1800,   // Microbiology & Immunology
        1005: 2500,   // Pharmacology & Therapeutics
        1004: 3500,   // Pathology & Histopathology
        1008: 5000,   // Community Medicine / PSM
        1015: 6500,   // ENT (Otorhinolaryngology)
        1014: 8000,   // Ophthalmology & Retinal
        1019: 10000,  // Anesthesiology & Critical Care
        1017: 12500,  // Psychiatry & Behavioral Sciences
        1013: 15000,  // Orthopedics & Joint Reconstruction
        1012: 18000,  // Pediatrics & Neonatology
        1011: 22000,  // Obstetrics & Gynecology
        1010: 28000,  // General Surgery & Operative
        1009: 35000,  // General Medicine & Clinical Pearls
        1016: 60000,  // Dermatology & Venereology (Top Student Demand)
        1018: 75000   // Radiodiagnosis & Imaging (Apex Student Priority)
    ]

    // ─── 2. RANK MILESTONES ───
    public struct RankLevelReward: Identifiable, Hashable {
        public var id: Int { level }
        public let level: Int
        public let tierName: String
        public let requiredXp: Int
        public let creditReward: Int
        public let iconSystemName: String
    }

    public let rankMilestones: [RankLevelReward] = [
        RankLevelReward(level: 1, tierName: "ASPIRANT", requiredXp: 0, creditReward: 250, iconSystemName: "leaf.fill"),
        RankLevelReward(level: 2, tierName: "ROOKIE", requiredXp: 500, creditReward: 500, iconSystemName: "shield.fill"),
        RankLevelReward(level: 3, tierName: "SKILLED", requiredXp: 1500, creditReward: 1000, iconSystemName: "bolt.fill"),
        RankLevelReward(level: 4, tierName: "WARRIOR", requiredXp: 3500, creditReward: 2000, iconSystemName: "flame.fill"),
        RankLevelReward(level: 5, tierName: "EXPERT", requiredXp: 7500, creditReward: 3500, iconSystemName: "star.fill"),
        RankLevelReward(level: 6, tierName: "SCHOLAR", requiredXp: 15000, creditReward: 6000, iconSystemName: "book.fill"),
        RankLevelReward(level: 7, tierName: "MASTER", requiredXp: 30000, creditReward: 10000, iconSystemName: "crown.fill"),
        RankLevelReward(level: 8, tierName: "GRANDMASTER", requiredXp: 60000, creditReward: 18000, iconSystemName: "sparkles"),
        RankLevelReward(level: 9, tierName: "LEGEND", requiredXp: 100000, creditReward: 30000, iconSystemName: "trophy.fill")
    ]

    // ─── 3. STORE PACKAGES ───
    public struct CreditPackage: Identifiable, Hashable {
        public let id: String
        public let storeProductId: String
        public let title: String
        public let credits: Int
        public let bonusText: String?
        public let priceInr: String
        public let priceUsd: String
        public let isBestValue: Bool
        public let isSpecialOffer: Bool

        public init(
            id: String,
            storeProductId: String,
            title: String,
            credits: Int,
            bonusText: String? = nil,
            priceInr: String,
            priceUsd: String,
            isBestValue: Bool = false,
            isSpecialOffer: Bool = false
        ) {
            self.id = id
            self.storeProductId = storeProductId
            self.title = title
            self.credits = credits
            self.bonusText = bonusText
            self.priceInr = priceInr
            self.priceUsd = priceUsd
            self.isBestValue = isBestValue
            self.isSpecialOffer = isSpecialOffer
        }
    }

    public let storePackages: [CreditPackage] = [
        CreditPackage(id: "pack_1", storeProductId: "medigyaan_credits_1000", title: "Aspirant Pouch", credits: 1000, priceInr: "₹49", priceUsd: "$0.99"),
        CreditPackage(id: "pack_2", storeProductId: "medigyaan_credits_3500", title: "Clinician Sack", credits: 3500, bonusText: "+10% Extra", priceInr: "₹149", priceUsd: "$1.99"),
        CreditPackage(id: "pack_3", storeProductId: "medigyaan_credits_10000", title: "Resident Chest", credits: 10000, bonusText: "+15% Extra", priceInr: "₹399", priceUsd: "$4.99"),
        CreditPackage(id: "pack_4", storeProductId: "medigyaan_credits_25000", title: "Surgeon Vault", credits: 25000, bonusText: "+25% Extra", priceInr: "₹899", priceUsd: "$9.99"),
        CreditPackage(id: "pack_5", storeProductId: "medigyaan_credits_60000", title: "Radiologist Treasury", credits: 60000, bonusText: "+35% Extra", priceInr: "₹1,799", priceUsd: "$19.99", isBestValue: true),
        CreditPackage(id: "pack_6", storeProductId: "medigyaan_credits_100000", title: "Grandmaster Hoard", credits: 100000, bonusText: "+50% Extra", priceInr: "₹2,699", priceUsd: "$29.99")
    ]

    public let specialOffers: [CreditPackage] = [
        CreditPackage(id: "offer_neet_starter", storeProductId: "medigyaan_offer_neet_starter", title: "NEET PG High-Yield Starter", credits: 5000, bonusText: "60% OFF LIMITED", priceInr: "₹99", priceUsd: "$1.29", isSpecialOffer: true),
        CreditPackage(id: "offer_radio_derma_pass", storeProductId: "medigyaan_offer_radio_derma", title: "Radiology & Derma Rapid Pass", credits: 75000, bonusText: "50% OFF APEX BUNDLE", priceInr: "₹1,499", priceUsd: "$16.99", isSpecialOffer: true)
    ]

    @Published public private(set) var currentCredits: Int = 250

    private init() {
        if userDefaults.object(forKey: keyCredits) == nil {
            userDefaults.set(Self.defaultStarterCredits, forKey: keyCredits)
            currentCredits = Self.defaultStarterCredits
        } else {
            currentCredits = userDefaults.integer(forKey: keyCredits)
        }
    }

    // ─── 4. CREDITS OPERATIONS ───
    @discardableResult
    public func addCredits(_ amount: Int) -> Int {
        guard amount > 0 else { return currentCredits }
        currentCredits += amount
        userDefaults.set(currentCredits, forKey: keyCredits)
        return currentCredits
    }

    public func deductCredits(_ amount: Int) -> Bool {
        guard amount > 0 else { return true }
        guard currentCredits >= amount else { return false }
        currentCredits -= amount
        userDefaults.set(currentCredits, forKey: keyCredits)
        return true
    }

    // ─── 5. AVATAR OWNERSHIP ───
    public func isAvatarOwned(_ avatarIndex: Int) -> Bool {
        if avatarIndex == Self.starterAvatarIndex { return true }
        let owned = (userDefaults.array(forKey: keyOwnedAvatars) as? [Int]) ?? []
        return owned.contains(avatarIndex)
    }

    public func getAvatarCost(_ avatarIndex: Int) -> Int {
        avatarCreditCosts[avatarIndex] ?? 15000
    }

    public func unlockAvatar(_ avatarIndex: Int) -> Bool {
        if isAvatarOwned(avatarIndex) { return true }
        let cost = getAvatarCost(avatarIndex)
        guard deductCredits(cost) else { return false }

        var owned = (userDefaults.array(forKey: keyOwnedAvatars) as? [Int]) ?? []
        owned.append(avatarIndex)
        userDefaults.set(owned, forKey: keyOwnedAvatars)
        return true
    }

    // ─── 6. DAILY MYSTERY CHEST (24h Cooldown) ───
    private let cooldown24h: TimeInterval = 24 * 60 * 60

    public var canOpenDailyChest: Bool {
        let lastTime = userDefaults.double(forKey: keyLastDailyChest)
        let now = Date().timeIntervalSince1970
        return (now - lastTime) >= cooldown24h
    }

    public var dailyChestRemainingSeconds: TimeInterval {
        let lastTime = userDefaults.double(forKey: keyLastDailyChest)
        let now = Date().timeIntervalSince1970
        let elapsed = now - lastTime
        return max(0, cooldown24h - elapsed)
    }

    public func openDailyChest() -> Int {
        guard canOpenDailyChest else { return 0 }
        let reward = Int.random(in: 150...350)
        userDefaults.set(Date().timeIntervalSince1970, forKey: keyLastDailyChest)
        addCredits(reward)
        return reward
    }

    // ─── 7. RANK MILESTONE REWARDS ───
    public func isRankClaimed(_ tierName: String) -> Bool {
        let claimed = (userDefaults.array(forKey: keyClaimedRanks) as? [String]) ?? []
        return claimed.contains(tierName.uppercased())
    }

    public func canClaimRankReward(_ reward: RankLevelReward, currentXp: Int) -> Bool {
        guard !isRankClaimed(reward.tierName) else { return false }
        return currentXp >= reward.requiredXp
    }

    public func claimRankReward(_ reward: RankLevelReward, currentXp: Int) -> Bool {
        guard canClaimRankReward(reward, currentXp: currentXp) else { return false }
        var claimed = (userDefaults.array(forKey: keyClaimedRanks) as? [String]) ?? []
        claimed.append(reward.tierName.uppercased())
        userDefaults.set(claimed, forKey: keyClaimedRanks)
        addCredits(reward.creditReward)
        return true
    }

    // ─── 8. PREDICTOR PASS ENTITLEMENT ───
    public var hasPredictorPass: Bool {
        userDefaults.bool(forKey: keyPredictorPass)
    }

    public func grantPredictorPass() {
        userDefaults.set(true, forKey: keyPredictorPass)
    }
}
