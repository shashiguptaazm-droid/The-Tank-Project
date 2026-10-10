import Foundation
import Combine

/// Credits and store economy manager for MediGyaan iOS.
///
/// Ports Android `CreditsManager` (`object CreditsManager`, `CreditsManager.kt`)
/// almost line for line. It owns the authoritative credit balance, the
/// character-ownership hierarchy, rank badge milestone awards, the 24-hour daily
/// mystery chest, the store packages / limited offers, and the NEET PG predictor
/// entitlement. Like the Kotlin original it is entirely local: **no network call
/// and no Firebase document is touched here**, so a purchase must be validated
/// by `api/check_predictor_access.php` (or the billing callback) before
/// `grantPredictorPass()` / `grantPredictorAccess()` is called.
///
/// **Thread safety.** Android relies on `SharedPreferences.apply()` plus the
/// fact that every caller is on the main thread. The Swift port keeps a
/// **recursive `NSLock`** because the public entry points compose
/// (`unlockAvatar()` → `deductCredits()` → `addCredits()`), and `UserDefaults`
/// must only be mutated from one thread at a time. Balance mutations are
/// serialised and the authoritative value is always re-read from `UserDefaults`
/// under the lock, exactly mirroring `prefs.getInt(KEY_USER_CREDITS, …)` —
/// `currentCredits` is a published mirror of that value, marshalled to the main
/// queue so SwiftUI never observes a background write. This is strictly
/// stronger than the Kotlin read-modify-write, which is not atomic.
public final class CreditsManager: ObservableObject {

    /// Android's `object CreditsManager` is a process-wide singleton, mirrored 1:1.
    public static let shared = CreditsManager()

    /// Android `CreditsManager.PREFS_NAME` = `"MY_APP"`. iOS has no named
    /// plist, so `UserDefaults.standard` is the equivalent namespace.
    private let userDefaults = UserDefaults.standard

    /// Re-entrant because the credit entry points nest (see the type comment).
    private let lock = NSRecursiveLock()

    /// Android `Log` tag used by every credit mutation (`"PAYMENT_MONITOR"`).
    private static let logTag = "PAYMENT_MONITOR"

    /// Android `KEY_USER_CREDITS`.
    private let keyCredits = "user_credits"
    /// Android `KEY_OWNED_AVATARS`. Android writes a `Set<String>` of indices;
    /// this port writes `[Int]` under the same key.
    private let keyOwnedAvatars = "owned_avatar_indices"
    /// Android `KEY_CLAIMED_RANKS`.
    private let keyClaimedRanks = "claimed_rank_level_rewards"
    /// Android `KEY_LAST_DAILY_CHEST_TIME`. Android stores epoch **milliseconds**;
    /// this port stores epoch **seconds** (pre-existing iOS decision — see
    /// `openDailyChest()`), so the two platforms are not byte-compatible here.
    private let keyLastDailyChest = "last_daily_chest_time_ms"
    /// Android `PREDICTOR_ENTITLEMENT_KEY`, the legacy global entitlement flag.
    private let keyPredictorPass = "predict_college_pass"
    /// Android `KEY_PREDICTOR_ACCESS_PREFIX`; the per-user keys are
    /// `<prefix><userId>` (bool) and `<prefix><userId>_granted_at` (millis).
    private let keyPredictorAccessPrefix = "predict_college_access_"
    /// Android `getCurrentUserId(context)` reads `user_id` from the same
    /// `SharedPreferences("MY_APP")` file; iOS `SessionStore` writes
    /// `mg.user_id`. Mirrored here because that key is private to `SessionStore`
    /// and `SessionStore` is `@MainActor`-isolated, which a non-isolated
    /// economy singleton must not touch.
    private let keySessionUserId = "mg.user_id"

    /// Android `CreditsManager.PREDICTOR_ENTITLEMENT_KEY`.
    static let predictorEntitlementKey = "predict_college_pass"

    /// Android `CreditsManager.STARTER_AVATAR_INDEX` — Anatomy • Axiom,
    /// pre-owned by every student.
    public static let starterAvatarIndex = 1001

    /// Android `CreditsManager.DEFAULT_STARTER_CREDITS`.
    public static let defaultStarterCredits = 250

    /// Ports Android `CreditsManager.getCurrentUserId(context)`: the locally
    /// cached account id, or `0` when signed out.
    func currentUserId() -> Int {
        userDefaults.integer(forKey: keySessionUserId)
    }

    // ─── 1. AVATAR CREDIT PRICING HIERARCHY ───
    /// Ports Android `avatarCreditCosts`: 19 branches, Anatomy pre-owned free,
    /// Derma/Radio at the apex. Unknown indices fall back to 15000 in
    /// `getAvatarCost(_:)`, exactly as in Kotlin.
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
    /// Ports Android `RankLevelReward`. `iconRes: Int` (a `R.drawable.*` id)
    /// becomes `iconSystemName` (SF Symbol) — the only non-mechanical delta,
    /// since drawable ids have no iOS equivalent.
    public struct RankLevelReward: Identifiable, Hashable {
        public var id: Int { level }
        public let level: Int
        public let tierName: String
        public let requiredXp: Int
        public let creditReward: Int
        public let iconSystemName: String
    }

    /// Ports Android `rankMilestones`: nine tiers, one-time credit bounties,
    /// claimed via `claimRankReward(_:currentXp:)`.
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
    /// Ports Android `CreditPackage`. `playProductId` is renamed
    /// `storeProductId` for platform symmetry; the string values are unchanged
    /// and still match the Play Billing / StoreKit product identifiers.
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
        /// Ports Kotlin `CreditPackage.entitlementKey`: non-nil only for the
        /// predictor pass, whose unlock is a flag rather than a credit grant.
        public let entitlementKey: String?

        public init(
            id: String,
            storeProductId: String,
            title: String,
            credits: Int,
            bonusText: String? = nil,
            priceInr: String,
            priceUsd: String,
            isBestValue: Bool = false,
            isSpecialOffer: Bool = false,
            entitlementKey: String? = nil
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
            self.entitlementKey = entitlementKey
        }
    }

    /// Ports Android `storePackages`: six IAP packs, ₹49 → ₹2,699.
    public let storePackages: [CreditPackage] = [
        CreditPackage(id: "pack_1", storeProductId: "medigyaan_credits_1000", title: "Aspirant Pouch", credits: 1000, priceInr: "₹49", priceUsd: "$0.99"),
        CreditPackage(id: "pack_2", storeProductId: "medigyaan_credits_3500", title: "Clinician Sack", credits: 3500, bonusText: "+10% Extra", priceInr: "₹149", priceUsd: "$1.99"),
        CreditPackage(id: "pack_3", storeProductId: "medigyaan_credits_10000", title: "Resident Chest", credits: 10000, bonusText: "+15% Extra", priceInr: "₹399", priceUsd: "$4.99"),
        CreditPackage(id: "pack_4", storeProductId: "medigyaan_credits_25000", title: "Surgeon Vault", credits: 25000, bonusText: "+25% Extra", priceInr: "₹899", priceUsd: "$9.99"),
        CreditPackage(id: "pack_5", storeProductId: "medigyaan_credits_60000", title: "Radiologist Treasury", credits: 60000, bonusText: "+35% Extra", priceInr: "₹1,799", priceUsd: "$19.99", isBestValue: true),
        CreditPackage(id: "pack_6", storeProductId: "medigyaan_credits_100000", title: "Grandmaster Hoard", credits: 100000, bonusText: "+50% Extra", priceInr: "₹2,699", priceUsd: "$29.99")
    ]

    /// Ports Android `specialOffers`: two discounted bundles.
    public let specialOffers: [CreditPackage] = [
        CreditPackage(id: "offer_neet_starter", storeProductId: "medigyaan_offer_neet_starter", title: "NEET PG High-Yield Starter", credits: 5000, bonusText: "60% OFF LIMITED", priceInr: "₹99", priceUsd: "$1.29", isSpecialOffer: true),
        CreditPackage(id: "offer_radio_derma_pass", storeProductId: "medigyaan_offer_radio_derma", title: "Radiology & Derma Rapid Pass", credits: 75000, bonusText: "50% OFF APEX BUNDLE", priceInr: "₹1,499", priceUsd: "$16.99", isSpecialOffer: true)
    ]

    /// Ports Android `allPackagesAndOffers` (`by lazy { storePackages + specialOffers }`).
    var allPackagesAndOffers: [CreditPackage] { storePackages + specialOffers }

    /// Ports Android `predictorPass`: a ₹500 one-time unlock worth **0 credits**
    /// that flips the entitlement flag instead of crediting the treasury.
    let predictorPass = CreditPackage(
        id: "predict_college_pass",
        storeProductId: "medigyaan_predict_college_pass",
        title: "NEET-PG College Predictor Pass",
        credits: 0,
        bonusText: "One-time unlock",
        priceInr: "₹500",
        priceUsd: "",
        isSpecialOffer: true,
        entitlementKey: CreditsManager.predictorEntitlementKey
    )

    /// Ports Android `allPlayProductIds` — the full billing catalogue to hand to
    /// StoreKit `Product.products(for:)`.
    var allPlayProductIds: [String] {
        (allPackagesAndOffers + [predictorPass]).map(\.storeProductId)
    }

    /// Ports Android `CreditsManager.getPackageByPlayProductId`.
    func package(forStoreProductId productId: String) -> CreditPackage? {
        (allPackagesAndOffers + [predictorPass]).first { $0.storeProductId == productId }
    }

    /// Ports Android `CreditsManager.getPackageById`.
    func package(forId packageId: String) -> CreditPackage? {
        (allPackagesAndOffers + [predictorPass]).first { $0.id == packageId }
    }

    /// Ports Android `CreditsManager.getPackageByPlayProductId`, verbatim name.
    func getPackageByPlayProductId(_ productId: String) -> CreditPackage? {
        package(forStoreProductId: productId)
    }

    /// Ports Android `CreditsManager.getPackageById`, verbatim name.
    func getPackageById(_ packageId: String) -> CreditPackage? {
        package(forId: packageId)
    }

    /// Published mirror of the authoritative persisted balance. Mutated only
    /// through `addCredits(_:)` / `deductCredits(_:)` / `synchronizeFromStore()`.
    @Published public private(set) var currentCredits: Int = 250

    private init() {
        currentCredits = readBalanceLocked()
    }

    // ─── 4. CREDITS OPERATIONS ───
    /// Ports Android `CreditsManager.addCredits(context, amount)`: a non-positive
    /// amount is a no-op, and the new balance is both persisted and returned.
    @discardableResult
    public func addCredits(_ amount: Int) -> Int {
        guard amount > 0 else {
            let balance = withLock { readBalanceLocked() }
            return balance
        }
        let entry = withLock { () -> LedgerEntry in
            let previous = readBalanceLocked()
            let updated = previous + amount
            userDefaults.set(updated, forKey: keyCredits)
            publish(updated)
            return LedgerEntry(didApply: true, previous: previous, updated: updated)
        }
        RemoteLogger.log(
            tag: Self.logTag,
            message: "[CREDITS_MANAGER] +\(amount) Credits Added. Previous: \(entry.previous), New Balance: \(entry.updated)"
        )
        return entry.updated
    }

    /// Ports Android `CreditsManager.deductCredits(context, amount)`: refuses when
    /// the balance is short, so the balance can never be driven negative.
    public func deductCredits(_ amount: Int) -> Bool {
        guard amount > 0 else { return true }
        let entry = withLock { () -> LedgerEntry in
            let previous = readBalanceLocked()
            guard previous >= amount else {
                return LedgerEntry(didApply: false, previous: previous, updated: previous)
            }
            let updated = previous - amount
            userDefaults.set(updated, forKey: keyCredits)
            publish(updated)
            return LedgerEntry(didApply: true, previous: previous, updated: updated)
        }
        if entry.didApply {
            RemoteLogger.log(
                tag: Self.logTag,
                message: "[CREDITS_MANAGER] -\(amount) Credits Deducted. Previous: \(entry.previous), New Balance: \(entry.updated)"
            )
        } else {
            RemoteLogger.log(
                tag: Self.logTag,
                message: "[CREDITS_MANAGER] Failed to deduct \(amount) Credits. Current Balance: \(entry.previous)"
            )
        }
        return entry.didApply
    }

    /// Ports Android `CreditsManager.getCredits(context)`: seeds the welcome
    /// balance the first time, then returns the stored integer every time.
    private func readBalanceLocked() -> Int {
        if userDefaults.object(forKey: keyCredits) == nil {
            userDefaults.set(Self.defaultStarterCredits, forKey: keyCredits)
            return Self.defaultStarterCredits
        }
        return userDefaults.integer(forKey: keyCredits)
    }

    /// Re-reads the persisted balance into `currentCredits`. Call after a
    /// sign-out/sign-in swap or when returning to the foreground, since
    /// `currentCredits` is only a published mirror of `UserDefaults`.
    func synchronizeFromStore() {
        let balance = withLock { readBalanceLocked() }
        publish(balance)
    }

    // ─── 5. AVATAR OWNERSHIP ───
    /// Ports Android `CreditsManager.isAvatarOwned(context, avatarIndex)`:
    /// the Anatomy starter (1001) is always owned, everything else is looked
    /// up in the persisted ownership set.
    public func isAvatarOwned(_ avatarIndex: Int) -> Bool {
        if avatarIndex == Self.starterAvatarIndex { return true }
        return withLock { ownedAvatarIndicesLocked().contains(avatarIndex) }
    }

    /// Ports Android `CreditsManager.getAvatarCost(avatarIndex)`; unlisted
    /// branches cost 15000 credits.
    public func getAvatarCost(_ avatarIndex: Int) -> Int {
        avatarCreditCosts[avatarIndex] ?? 15000
    }

    /// Ports Android `CreditsManager.getSubjectPriorityDescription(avatarIndex)`.
    func getSubjectPriorityDescription(_ avatarIndex: Int) -> String {
        switch avatarIndex {
        case 1001: return "Pre-owned Starter • Anatomy Foundation"
        case 1016: return "Top Student Demand • Premium Dermatology"
        case 1018: return "#1 NEET PG Dream Specialty • Apex Radiodiagnosis"
        case 1009: return "Clinical Core • High-Yield Medicine"
        case 1010: return "Operative Mastery • General Surgery"
        default: return "Clinical Specialty"
        }
    }

    /// Ports Android `CreditsManager.unlockAvatar(context, avatarIndex)`.
    /// Re-purchasing an owned branch is a no-op success; the charge happens
    /// before ownership is recorded, and Android has **no refund path** if the
    /// ownership write were to fail afterwards.
    public func unlockAvatar(_ avatarIndex: Int) -> Bool {
        if isAvatarOwned(avatarIndex) { return true }
        let cost = getAvatarCost(avatarIndex)
        guard deductCredits(cost) else { return false }

        withLock {
            var owned = ownedAvatarIndicesLocked()
            guard !owned.contains(avatarIndex) else { return }
            owned.append(avatarIndex)
            userDefaults.set(owned, forKey: keyOwnedAvatars)
        }
        RemoteLogger.log(
            tag: Self.logTag,
            message: "[CREDITS_MANAGER] Unlocked avatar \(avatarIndex) for \(cost) Credits"
        )
        return true
    }

    // ─── 6. DAILY MYSTERY CHEST (24h Cooldown) ───
    /// Ports Android `COOLDOWN_24H_MS` = `24 * 60 * 60 * 1000L`, expressed in
    /// seconds because iOS persists epoch seconds.
    private let cooldown24h: TimeInterval = 24 * 60 * 60

    /// Ports Android `CreditsManager.canOpenDailyChest(context)`.
    public var canOpenDailyChest: Bool {
        withLock { now - lastChestOpenLocked() >= cooldown24h }
    }

    /// Ports Android `CreditsManager.getDailyChestRemainingTimeMs(context)`,
    /// converted to seconds for the HH:MM:SS countdown; `0` when ready.
    public var dailyChestRemainingSeconds: TimeInterval {
        withLock {
            let elapsed = now - lastChestOpenLocked()
            return elapsed >= cooldown24h ? 0 : cooldown24h - elapsed
        }
    }

    /// Ports Android `CreditsManager.openDailyChest(context)`: a repeatable
    /// 150–350 inclusive random bounty on a 24-hour cooldown. The cooldown
    /// timestamp is stamped **before** the credit is granted (same order as
    /// Kotlin) so a re-entrant call can never double-pay.
    public func openDailyChest() -> Int {
        guard canOpenDailyChest else { return 0 }
        let reward = Int.random(in: 150...350)
        withLock {
            userDefaults.set(now, forKey: keyLastDailyChest)
        }
        addCredits(reward)
        RemoteLogger.log(
            tag: Self.logTag,
            message: "[CREDITS_MANAGER] Daily Mystery Chest opened. Reward: \(reward) Credits"
        )
        return reward
    }

    // ─── 7. RANK MILESTONE REWARDS ───
    /// Ports Android `CreditsManager.isRankClaimed(context, tierName)`; tier
    /// names are compared uppercased on both platforms.
    public func isRankClaimed(_ tierName: String) -> Bool {
        withLock { claimedRankTiersLocked().contains(tierName.uppercased()) }
    }

    /// Ports Android `CreditsManager.canClaimRankReward(context, reward, currentXp)`:
    /// unclaimed **and** XP threshold reached.
    public func canClaimRankReward(_ reward: RankLevelReward, currentXp: Int) -> Bool {
        guard !isRankClaimed(reward.tierName) else { return false }
        return currentXp >= reward.requiredXp
    }

    /// Ports Android `CreditsManager.claimRankReward(context, reward, currentXp)`:
    /// a one-time-per-tier bounty. The claim is marked before the credit is
    /// granted so a double tap cannot pay out twice.
    public func claimRankReward(_ reward: RankLevelReward, currentXp: Int) -> Bool {
        guard canClaimRankReward(reward, currentXp: currentXp) else { return false }

        withLock {
            var claimed = claimedRankTiersLocked()
            let tier = reward.tierName.uppercased()
            guard !claimed.contains(tier) else { return }
            claimed.append(tier)
            userDefaults.set(claimed, forKey: keyClaimedRanks)
        }
        addCredits(reward.creditReward)
        return true
    }

    // ─── 8. PREDICTOR PASS ENTITLEMENT ───
    /// Ports Android `CreditsManager.hasPredictorAccess(context, userId)`,
    /// widened to also honour the legacy global `predict_college_pass` flag
    /// written by `grantPredictorPass()`.
    public var hasPredictorPass: Bool {
        if userDefaults.bool(forKey: keyPredictorPass) { return true }
        return hasPredictorAccess()
    }

    /// Ports Android `CreditsManager.hasPredictorAccess(context, userId)`:
    /// per-user entitlement lookup, `false` for a non-positive user id.
    func hasPredictorAccess(userId: Int? = nil) -> Bool {
        let resolved = userId ?? currentUserId()
        guard resolved > 0 else { return false }
        return withLock { userDefaults.bool(forKey: "\(keyPredictorAccessPrefix)\(resolved)") }
    }

    /// Ports Android `grantPredictorAccess(context, userId)` — writes the
    /// boolean plus a `<key>_granted_at` epoch-millisecond stamp. Returns
    /// `false` for a non-positive user id, as in Kotlin.
    @discardableResult
    func grantPredictorAccess(userId: Int? = nil) -> Bool {
        let resolved = userId ?? currentUserId()
        guard resolved > 0 else { return false }
        withLock {
            userDefaults.set(true, forKey: "\(keyPredictorAccessPrefix)\(resolved)")
            userDefaults.set(
                now * 1000,
                forKey: "\(keyPredictorAccessPrefix)\(resolved)_granted_at"
            )
        }
        return true
    }

    /// Ports Android `CreditsManager.revokePredictorAccess(context, userId)`.
    func revokePredictorAccess(userId: Int? = nil) {
        let resolved = userId ?? currentUserId()
        guard resolved > 0 else { return }
        withLock { userDefaults.set(false, forKey: "\(keyPredictorAccessPrefix)\(resolved)") }
    }

    /// Timestamp written by `grantPredictorAccess(userId:)`, decoded from
    /// Android's epoch-millisecond encoding. `nil` when never granted.
    func predictorAccessGrantedAt(userId: Int? = nil) -> Date? {
        let resolved = userId ?? currentUserId()
        guard resolved > 0 else { return nil }
        let millis = withLock {
            userDefaults.double(forKey: "\(keyPredictorAccessPrefix)\(resolved)_granted_at")
        }
        guard millis > 0 else { return nil }
        return Date(timeIntervalSince1970: millis / 1000)
    }

    /// Legacy global grant retained from the first iOS port; `PredictorView`
    /// calls it after `check_predictor_access.php` reports `unlocked: true`.
    /// Also grants the per-user key so both spellings agree.
    public func grantPredictorPass() {
        userDefaults.set(true, forKey: keyPredictorPass)
        grantPredictorAccess()
        RemoteLogger.log(
            tag: Self.logTag,
            message: "[CREDITS_MANAGER] Predictor pass granted for user \(currentUserId())"
        )
    }

    // MARK: - Storage

    /// Outcome of a balance mutation, kept so the `RemoteLogger` line can
    /// report the same before/after pair as Android's `Log.i`/`Log.w` calls.
    private struct LedgerEntry {
        let didApply: Bool
        let previous: Int
        let updated: Int
    }

    private var now: TimeInterval { Date().timeIntervalSince1970 }

    private func withLock<T>(_ body: () throws -> T) rethrows -> T {
        lock.lock()
        defer { lock.unlock() }
        return try body()
    }

    private func publish(_ balance: Int) {
        if Thread.isMainThread {
            currentCredits = balance
        } else {
            DispatchQueue.main.async { [weak self] in
                self?.currentCredits = balance
            }
        }
    }

    private func ownedAvatarIndicesLocked() -> [Int] {
        (userDefaults.array(forKey: keyOwnedAvatars) as? [Int]) ?? []
    }

    private func claimedRankTiersLocked() -> [String] {
        (userDefaults.array(forKey: keyClaimedRanks) as? [String]) ?? []
    }

    private func lastChestOpenLocked() -> TimeInterval {
        userDefaults.double(forKey: keyLastDailyChest)
    }
}

extension CreditsManager: @unchecked Sendable {}