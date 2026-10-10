import Foundation
import SwiftUI

// MARK: - Cashfree order

/// A Cashfree order created by `POST /Neurons/api/create_order.php`.
///
/// Ports the five `putExtra` keys `CreditsTreasureActivity.initiateCashfreePayment`
/// handed to `PaymentActivity`: `order_id`, `payment_session_id`, `environment`,
/// `credits_to_add` and `package_title`. iOS has no `ActivityResultLauncher`, so
/// the same payload is published as
/// ``CreditsTreasureViewModel/pendingOrder`` for the Payment module to consume
/// and report back through
/// ``CreditsTreasureViewModel/completeCashfreePurchase(creditsAdded:)``.
struct CashfreeOrder: Identifiable, Hashable {

    let orderID: String
    let paymentSessionID: String
    /// `optString("environment", "PRODUCTION")`.
    let environment: String
    let creditsToAdd: Int
    let packageTitle: String

    var id: String { orderID }
}

/// Stand-in for `Toast.makeText(this, …, Toast.LENGTH_SHORT)`, which has no
/// iOS counterpart short of a `UIAlertController` subclass the app does not use.
struct TreasuryToast: Identifiable, Equatable {

    let id = UUID()
    let message: String
}

/// The modal surfaces of `CreditsTreasureActivity` that survive on iOS.
/// `showBillingErrorDialog` is absent: its only trigger was
/// `PlayBillingManager.onBillingError`, and its two fallbacks (Cashfree, demo
/// unlock) are preserved on the gateway chooser instead.
enum TreasuryDialog: Identifiable {

    /// `showRewardDialog(title:message:rewardCredits:)`.
    case reward(title: String, message: String, award: Int)
    /// `showCashfreeErrorNotice(pack:errorReason:)`.
    case cashfreeFailure(reason: String, offer: CreditsTreasureViewModel.PurchaseOffer)

    var id: String {
        switch self {
        case let .reward(title, _, award):
            return "reward-\(title)-\(award)"
        case let .cashfreeFailure(reason, offer):
            return "cashfree-\(reason)-\(offer.id)"
        }
    }
}

/// `NumberFormat.getNumberInstance(Locale.US)` — grouping is pinned to `en_US`
/// so the treasury renders `71,250` exactly as Android does, whatever the
/// device locale is.
enum TreasuryFormat {

    private static let decimal: NumberFormatter = {
        let formatter = NumberFormatter()
        formatter.locale = Locale(identifier: "en_US")
        formatter.numberStyle = .decimal
        formatter.maximumFractionDigits = 0
        return formatter
    }()

    static func credits(_ value: Int) -> String {
        decimal.string(from: NSNumber(value: value)) ?? "\(value)"
    }
}

// MARK: - View model

/// Ports the state and side effects of `CreditsTreasureActivity`: the chest
/// cooldown ticker, the balance count-up, rank-milestone claiming, the gateway
/// chooser and the Cashfree `create_order.php` round trip.
@MainActor
final class CreditsTreasureViewModel: ObservableObject {

    /// The five `chip*` views of `activity_credits_treasure.xml`, in declaration
    /// order. Android used them purely as scroll anchors; iOS additionally
    /// filters down to the tapped section.
    enum Category: String, CaseIterable, Identifiable {
        case all = "🌟 ALL"
        case chest = "🎁 DAILY CHEST"
        case ranks = "🏆 RANK MILESTONES"
        case packages = "💎 BUY CREDITS"
        case offers = "🔥 OFFERS"

        var id: String { rawValue }
    }

    /// Which `pack_*` / `offer_*` entry the gateway chooser is offering. The
    /// distinction only matters for the sheet's own presentation.
    enum PurchaseOffer: Identifiable, Hashable {
        case store(CreditsManager.CreditPackage)
        case specialOffer(CreditsManager.CreditPackage)

        var id: String {
            switch self {
            case let .store(pack): return "store-\(pack.id)"
            case let .specialOffer(pack): return "offer-\(pack.id)"
            }
        }

        var pack: CreditsManager.CreditPackage {
            switch self {
            case let .store(pack): return pack
            case let .specialOffer(pack): return pack
            }
        }
    }

    // MARK: Published state

    @Published var selectedCategory: Category = .all
    /// `CreditsManager.canOpenDailyChest`, re-sampled on every tick so the
    /// button re-enables the moment `CountDownTimer.onFinish` would have fired.
    @Published private(set) var chestReady = false
    /// `CreditsManager.getDailyChestRemainingTimeMs`.
    @Published private(set) var chestRemainingSeconds: TimeInterval = 0
    /// Drives the 600ms `ValueAnimator` balance count-up.
    @Published private(set) var displayedCredits: Int = 0
    /// `LoadState` for the Cashfree order POST; `isLoading` also stands in for
    /// `ProgressDialog("Initiating secure Cashfree checkout…")`.
    @Published private(set) var orderState: LoadState<CashfreeOrder> = .idle
    /// Hand-off payload for the Payment module.
    @Published private(set) var pendingOrder: CashfreeOrder?
    @Published var dialog: TreasuryDialog?
    @Published private(set) var purchaseOffer: PurchaseOffer?
    @Published private(set) var toast: TreasuryToast?
    /// Re-reads `claimed_rank_level_rewards` after a claim, because the
    /// `SharedPreferences` store behind `CreditsManager` is not observable.
    @Published private(set) var claimedTierNames: [String] = []

    // MARK: Private state

    private let credits: CreditsManager
    private var countUpTask: Task<Void, Never>?
    private var toastTask: Task<Void, Never>?

    /// `pack.priceInr.replace(Regex("[^0-9.]"), "").toDoubleOrNull() ?: 49.0`.
    static let fallbackAmount: Double = 49.0
    /// `prefs.getString("user_phone", "9999999999")`.
    static let fallbackPhone = "9999999999"
    /// `prefs.getString("user_email", "student@medigyaan.com")`.
    static let fallbackEmail = "student@medigyaan.com"
    /// `if (savedUserId != 0) savedUserId else 1001`.
    static let fallbackUserId = 1001
    /// `https://medigyaan.com/Neurons/api/create_order.php`, verbatim.
    static let orderEndpoint = APIConfig.baseURL.appendingPathComponent("api/create_order.php")

    init(credits: CreditsManager = .shared) {
        self.credits = credits
        self.displayedCredits = credits.currentCredits
        self.chestReady = credits.canOpenDailyChest
        self.chestRemainingSeconds = credits.dailyChestRemainingSeconds
        self.claimedTierNames = Self.claimedTierNames(in: credits)
    }

    // MARK: - Lifecycle

    /// `CreditsTreasureActivity.loadUserData()` + `setupDailyChest()`.
    func start() {
        RemoteLogger.log(
            tag: "CreditsTreasure_Appear",
            message: "User opened Credits & Treasure vault",
            metadata: ["balance": String(credits.currentCredits)]
        )
        displayedCredits = credits.currentCredits
        refreshChest()
        refreshRankClaims()
    }

    /// The `CountDownTimer`'s 1000ms `onTick`, plus `onFinish`'s `setupDailyChest()`.
    func tickChest() {
        let ready = credits.canOpenDailyChest
        chestReady = ready
        chestRemainingSeconds = ready ? 0 : credits.dailyChestRemainingSeconds
    }

    /// `CreditsTreasureActivity.onDestroy()` — cancels the ticker and the balance
    /// animator that stood in for the `CountDownTimer` / `ObjectAnimator` pairs.
    func cancelWork() {
        countUpTask?.cancel()
        countUpTask = nil
        toastTask?.cancel()
        toastTask = nil
    }

    // MARK: - Balance

    /// `updateBalanceDisplay(animateFrom:)` — a 600ms `ValueAnimator` from the
    /// pre-mutation balance to the new one.
    private func animateBalance(from previous: Int) {
        countUpTask?.cancel()
        let target = credits.currentCredits
        guard previous != target else {
            displayedCredits = target
            return
        }

        let steps = 12
        let stepDelay: UInt64 = 50_000_000
        let delta = Double(target - previous) / Double(steps)
        let lower = min(previous, target)
        let upper = max(previous, target)
        displayedCredits = previous

        countUpTask = Task { [weak self] in
            for step in 1 ... steps {
                try? await Task.sleep(nanoseconds: stepDelay)
                if Task.isCancelled { return }
                let value = previous + Int((Double(step) * delta).rounded())
                self?.displayedCredits = min(max(value, lower), upper)
            }
            self?.displayedCredits = target
        }
    }

    // MARK: - Daily chest

    /// `btnOpenDailyChest.setOnClickListener` — a zero award is how the Kotlin
    /// signalled "still on cooldown".
    func openChest() {
        let previous = credits.currentCredits
        let awarded = credits.openDailyChest()
        refreshChest()

        guard awarded > 0 else {
            showToast("Daily chest is on cooldown!")
            return
        }

        animateBalance(from: previous)
        showReward(
            title: "🎁 DAILY CHEST UNLOCKED!",
            message: "Congratulations! You opened today's activity chest and received:",
            award: awarded
        )
    }

    /// `⏳ Next chest in: %02dh %02dm %02ds`.
    var chestCountdownText: String {
        let total = Int(chestRemainingSeconds)
        let hours = total / 3600
        let minutes = (total % 3600) / 60
        let seconds = total % 60
        return String(format: "⏳ Next chest in: %02dh %02dm %02ds", hours, minutes, seconds)
    }

    // MARK: - Rank milestones

    /// `RankManager.getCurrentTier(exp)` — `tiers.last { exp >= it.minExp }`.
    /// `CreditsManager.rankMilestones` holds the same nine tiers with the same
    /// thresholds as `RankManager.tiers`, so no second table is kept here.
    func currentTierName(xp: Int) -> String {
        let tiers = credits.rankMilestones
        return tiers.last { xp >= $0.requiredXp }?.tierName
            ?? tiers.first?.tierName
            ?? "ASPIRANT"
    }

    /// `RankManager.getNextTier(exp)` — `tiers.firstOrNull { it.minExp > exp }`.
    func nextTier(xp: Int) -> CreditsManager.RankLevelReward? {
        credits.rankMilestones.first { $0.requiredXp > xp }
    }

    /// `CreditsManager.isRankClaimed`, read through the snapshot the view can
    /// actually observe.
    func isRankClaimed(_ milestone: CreditsManager.RankLevelReward) -> Bool {
        claimedTierNames.contains(milestone.tierName.uppercased())
    }

    /// `CreditsManager.canClaimRankReward` minus the claimed check, which the
    /// view resolves first, exactly as the three-branch `btnAction` does.
    func canClaimRank(_ milestone: CreditsManager.RankLevelReward, xp: Int) -> Bool {
        xp >= milestone.requiredXp
    }

    /// The `canClaim` branch of `createMilestoneView`'s click listener.
    @discardableResult
    func claimRank(_ milestone: CreditsManager.RankLevelReward, xp: Int) -> Bool {
        let previous = credits.currentCredits
        guard credits.claimRankReward(milestone, currentXp: xp) else { return false }
        refreshRankClaims()
        animateBalance(from: previous)
        showReward(
            title: "🏆 LEVEL MILESTONE CLAIMED!",
            message: "Clinical mastery rewarded! You attained \(milestone.tierName) and earned:",
            award: milestone.creditReward
        )
        return true
    }

    // MARK: - Purchases

    /// `confirmPurchase(pack)` — the gateway `AlertDialog`.
    func beginPurchase(_ offer: PurchaseOffer) {
        purchaseOffer = offer
    }

    func cancelPurchase() {
        purchaseOffer = nil
    }

    /// `initiateCashfreePayment(pack, amount)`: POST `create_order.php`.
    func startCashfreeCheckout(
        _ offer: PurchaseOffer,
        userId: Int,
        phone: String,
        email: String
    ) {
        let pack = offer.pack
        purchaseOffer = nil
        orderState = .loading

        let amount = Self.amount(fromPriceLabel: pack.priceInr)

        Task {
            let result: LoadState<CashfreeOrder> = await LoadState.result {
                try await Self.createCashfreeOrder(
                    userId: userId,
                    pack: pack,
                    amount: amount,
                    phone: phone,
                    email: email
                )
            }
            self.orderState = result

            switch result {
            case let .loaded(order):
                self.pendingOrder = order
            case let .failed(message):
                self.dialog = .cashfreeFailure(reason: message, offer: offer)
            case .idle, .loading:
                break
            }
        }
    }

    /// The `paymentLauncher`'s `RESULT_OK` branch: the Payment module reports
    /// the verified `credits_added` extra back through here.
    func completeCashfreePurchase(creditsAdded: Int) {
        displayedCredits = credits.currentCredits
        guard creditsAdded > 0 else {
            showToast("Payment Successful!")
            return
        }
        showReward(
            title: "💎 CASHFREE PAYMENT VERIFIED!",
            message: "Your payment was processed successfully via Cashfree SDK! Account credited with:",
            award: creditsAdded
        )
    }

    /// `showCashfreeErrorNotice`'s RETRY button.
    func retryLastCashfreeOrder(userId: Int, phone: String, email: String) {
        guard let current = dialog else { return }
        if case let .cashfreeFailure(_, offer) = current {
            dialog = nil
            startCashfreeCheckout(offer, userId: userId, phone: phone, email: email)
        }
    }

    /// The 🧪 neutral button of `showBillingErrorDialog`, preserved as a third
    /// gateway choice now that Play Billing is gone.
    func applyDemoUnlock(_ pack: CreditsManager.CreditPackage) {
        purchaseOffer = nil
        let previous = credits.currentCredits
        let newBalance = credits.addCredits(pack.credits)
        animateBalance(from: previous)
        showReward(
            title: "🧪 DEMO / TEST CREDITS UNLOCKED!",
            message: "Delivered \(pack.credits) test credits for '\(pack.title)'.\nNew Balance: \(newBalance)",
            award: pack.credits
        )
    }

    /// `pack.priceInr.replace(Regex("[^0-9.]"), "").toDoubleOrNull() ?: 49.0`.
    nonisolated static func amount(fromPriceLabel label: String) -> Double {
        let digits = label.filter { $0.isNumber || $0 == "." }
        return Double(digits) ?? fallbackAmount
    }

    // MARK: - Dialog plumbing

    private func showReward(title: String, message: String, award: Int) {
        dialog = .reward(title: title, message: message, award: award)
    }

    private func showToast(_ message: String) {
        toastTask?.cancel()
        let entry = TreasuryToast(message: message)
        toast = entry
        toastTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 2_000_000_000)
            if Task.isCancelled { return }
            if self?.toast?.id == entry.id { self?.toast = nil }
        }
    }

    func dismissDialog() {
        dialog = nil
    }

    func dismissPendingOrder() {
        pendingOrder = nil
    }

    private func refreshChest() {
        let ready = credits.canOpenDailyChest
        chestReady = ready
        chestRemainingSeconds = ready ? 0 : credits.dailyChestRemainingSeconds
    }

    private func refreshRankClaims() {
        claimedTierNames = Self.claimedTierNames(in: credits)
    }

    private static func claimedTierNames(in credits: CreditsManager) -> [String] {
        credits.rankMilestones
            .filter { credits.isRankClaimed($0.tierName) }
            .map { $0.tierName.uppercased() }
    }

    // MARK: - Networking

    /// Ports the Volley `JsonObjectRequest` in `initiateCashfreePayment`,
    /// including its `getHeaders()` override. `HTTPClient` cannot reach this
    /// script because `APIConfig.Endpoint` has no `create_order` case, so the
    /// request is assembled here the way `SocialAPI.connections` does.
    nonisolated static func createCashfreeOrder(
        userId: Int,
        pack: CreditsManager.CreditPackage,
        amount: Double,
        phone: String,
        email: String
    ) async throws -> CashfreeOrder {
        let payload: [String: Any] = [
            "user_id": userId,
            "customer_id": String(userId),
            "pack_id": pack.id,
            "pack": pack.id,
            "amount": amount,
            "phone": phone,
            "email": email
        ]

        var request = URLRequest(url: orderEndpoint)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue(APIConfig.appSignature, forHTTPHeaderField: "X-App-Signature")
        request.setValue(APIConfig.userAgent, forHTTPHeaderField: "User-Agent")
        request.httpBody = try JSONSerialization.data(withJSONObject: payload)

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await URLSession.shared.data(for: request)
        } catch {
            throw APIError.transport(message: error.localizedDescription)
        }

        let object = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] ?? [:]
        let serverMessage = Self.serverMessage(from: object, raw: data)

        guard let http = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200 ..< 300).contains(http.statusCode) else {
            throw APIError.server(
                message: serverMessage ?? "Network error connecting to Cashfree",
                code: http.statusCode
            )
        }
        guard Self.boolValue(object["success"]) else {
            throw APIError.server(
                message: serverMessage ?? "Cashfree order creation failed",
                code: nil
            )
        }
        guard
            let orderID = Self.stringValue(object["order_id"]),
            let sessionID = Self.stringValue(object["payment_session_id"])
        else {
            throw APIError.decoding(
                underlying: "create_order.php response is missing order_id / payment_session_id"
            )
        }

        return CashfreeOrder(
            orderID: orderID,
            paymentSessionID: sessionID,
            environment: Self.stringValue(object["environment"]) ?? "PRODUCTION",
            creditsToAdd: pack.credits,
            packageTitle: pack.title
        )
    }

    /// `errObj.optString("error", errObj.optString("message", jsonStr))`.
    nonisolated private static func serverMessage(from object: [String: Any], raw data: Data) -> String? {
        if let error = stringValue(object["error"]) { return error }
        if let message = stringValue(object["message"]) { return message }
        guard let body = String(data: data, encoding: .utf8), !body.isEmpty else { return nil }
        return body
    }

    /// `JSONObject.optString` — PHP also emits numbers for these fields.
    nonisolated private static func stringValue(_ value: Any?) -> String? {
        if let text = value as? String { return text.isEmpty ? nil : text }
        if let number = value as? NSNumber { return number.stringValue }
        return nil
    }

    /// `JSONObject.optBoolean`.
    nonisolated private static func boolValue(_ value: Any?) -> Bool {
        if let flag = value as? Bool { return flag }
        if let number = value as? NSNumber { return number.boolValue }
        if let text = value as? String { return (text as NSString).boolValue }
        return false
    }
}

// MARK: - Screen

/// iOS equivalent of Android `CreditsTreasureActivity.kt`.
///
/// Treasury and economy screen: the credit-balance pill in the top bar, the
/// category quick-jump chips, the 24h Daily Clinical Mystery Chest with its
/// cooldown ticker and floating animation, rank milestone bounties, limited-time
/// special offers, and the two-column credit-package store with Cashfree
/// checkout.
struct CreditsTreasureView: View {

    @EnvironmentObject private var session: SessionStore

    @StateObject private var viewModel = CreditsTreasureViewModel()
    @ObservedObject private var credits = CreditsManager.shared

    /// Drives the chest's `ObjectAnimator` breathing loop (2000ms, infinite,
    /// `AccelerateDecelerateInterpolator`).
    @State private var chestPulse = false
    /// The one-shot shake played when the chest is claimed.
    @State private var isChestShaking = false

    private let timer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()

    /// `prefs.getInt("user_exp", 0)`. Android keeps a dedicated XP counter in
    /// `SharedPreferences`; iOS has no equivalent store yet, so clinical mastery
    /// is derived from the profile's lifetime correct-answer count.
    private var clinicalMasteryXP: Int {
        (session.currentUser?.overallCorrect ?? 0) * 10
    }

    /// `if (savedUserId != 0) savedUserId else 1001`.
    private var resolvedUserId: Int {
        let stored = session.currentUser?.id ?? 0
        return stored != 0 ? stored : CreditsTreasureViewModel.fallbackUserId
    }

    private var resolvedPhone: String {
        let phone = session.currentUser?.phone ?? ""
        return phone.isEmpty ? CreditsTreasureViewModel.fallbackPhone : phone
    }

    private var resolvedEmail: String {
        let email = session.currentUser?.email ?? ""
        return email.isEmpty ? CreditsTreasureViewModel.fallbackEmail : email
    }

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(spacing: AppTheme.Spacing.xxl) {
                    dailyChestSection
                        .id(CreditsTreasureViewModel.Category.chest.rawValue)

                    rankMilestonesSection
                        .id(CreditsTreasureViewModel.Category.ranks.rawValue)

                    specialOffersSection
                        .id(CreditsTreasureViewModel.Category.offers.rawValue)

                    creditPackagesSection
                        .id(CreditsTreasureViewModel.Category.packages.rawValue)
                }
                .padding(AppTheme.Spacing.lg)
                .padding(.bottom, AppTheme.Spacing.xxl)
            }
            .safeAreaInset(edge: .top) {
                categorySelector(proxy: proxy)
            }
        }
        .overlay(alignment: .top) {
            if let toast = viewModel.toast {
                toastBanner(toast.message)
                    .padding(.horizontal, AppTheme.Spacing.xl)
                    .padding(.top, AppTheme.Spacing.sm)
                    .transition(.move(edge: .top).combined(with: .opacity))
            }
        }
        .animation(.easeOut(duration: 0.2), value: viewModel.toast)
        .overlay {
            if viewModel.orderState.isLoading {
                checkoutProgressOverlay
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .principal) {
                VStack(spacing: 0) {
                    Text("TREASURY & VAULT")
                        .font(AppTheme.Font.callout)
                        .foregroundStyle(AppTheme.Ink.textPrimary)
                    Text("Unlock Guardians & Powers")
                        .font(AppTheme.Font.micro)
                        .foregroundStyle(AppTheme.Ink.cyan)
                }
            }
            ToolbarItem(placement: .topBarTrailing) {
                balancePill
            }
        }
        .sheet(isPresented: pendingOrderPresented) {
            if let order = viewModel.pendingOrder {
                CashfreeCheckoutSheet(order: order) {
                    viewModel.dismissPendingOrder()
                }
                .presentationDetents([.medium])
            }
        }
        .confirmationDialog(
            Text(purchaseDialogTitle),
            isPresented: purchaseDialogPresented,
            titleVisibility: .visible,
            actions: { purchaseDialogActions },
            message: { Text(purchaseDialogMessage) }
        )
        .alert(
            alertTitle,
            isPresented: alertPresented,
            actions: { alertActions },
            message: { Text(alertMessage) }
        )
        .onAppear {
            viewModel.start()
            chestPulse = true
        }
        .onDisappear { viewModel.cancelWork() }
        .onReceive(timer) { _ in viewModel.tickChest() }
        .baseScreen("CreditsTreasureActivity", style: .ink, title: "TREASURY & VAULT")
    }

    // MARK: - Top bar balance

    /// `pillBalance` / `tvCreditBalanceTop`, updated by `updateBalanceDisplay`.
    private var balancePill: some View {
        HStack(spacing: AppTheme.Spacing.xs) {
            AndroidIcon(.ic_credit_coin, size: 20)
            Text(TreasuryFormat.credits(viewModel.displayedCredits))
                .font(AppTheme.Font.captionBold)
                .foregroundStyle(AppTheme.Ink.gold)
                .contentTransition(.numericText())
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, AppTheme.Spacing.sm)
        .background(Capsule().fill(AppTheme.Ink.surface))
        .accessibilityLabel("Credit balance")
    }

    // MARK: - Category chips

    /// `setupCategoryChips()` — the chip strip plus its
    /// `smoothScrollTo(section.top - 20dp)` jump.
    private func categorySelector(proxy: ScrollViewProxy) -> some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: AppTheme.Spacing.sm) {
                ForEach(CreditsTreasureViewModel.Category.allCases) { category in
                    Button {
                        viewModel.selectedCategory = category
                        if category != .all {
                            proxy.scrollTo(category.rawValue, anchor: .top)
                        }
                    } label: {
                        Text(category.rawValue)
                            .font(AppTheme.Font.captionBold)
                            .foregroundStyle(
                                viewModel.selectedCategory == category
                                    ? AppTheme.Ink.background
                                    : AppTheme.Ink.textSecondary
                            )
                            .padding(.horizontal, AppTheme.Spacing.md)
                            .padding(.vertical, AppTheme.Spacing.xs)
                            .background(
                                Capsule().fill(
                                    viewModel.selectedCategory == category
                                        ? AppTheme.Ink.gold
                                        : AppTheme.Ink.tile
                                )
                            )
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, AppTheme.Spacing.lg)
            .padding(.vertical, AppTheme.Spacing.sm)
        }
        .background(AppTheme.Ink.background)
    }

    // MARK: - Daily chest

    /// `sectionDailyChest` + `setupDailyChest()`.
    private var dailyChestSection: some View {
        InkCard(
            fill: AppTheme.Ink.surface,
            stroke: AppTheme.Ink.gold,
            radius: AppTheme.Radius.materialCard
        ) {
            VStack(spacing: AppTheme.Spacing.sm) {
                AndroidIcon(.ic_treasure_chest, size: 64)
                    .scaleEffect(chestScale)
                    .offset(y: chestOffset)
                    .rotationEffect(.degrees(isChestShaking ? 12 : 0))
                    .animation(chestBreathing, value: chestPulse)

                Text("DAILY CLINICAL MYSTERY CHEST")
                    .font(AppTheme.Font.cardTitle)
                    .foregroundStyle(AppTheme.Ink.gold)

                Text("Open 1x daily for 150 – 350 Free Credits!")
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Ink.textPrimary)
                    .multilineTextAlignment(.center)

                Text(chestStatusText)
                    .font(AppTheme.Font.captionBold)
                    .foregroundStyle(
                        viewModel.chestReady ? AppTheme.Palette.success : AppTheme.Ink.textSecondary
                    )
                    .padding(.horizontal, AppTheme.Spacing.md)
                    .padding(.vertical, AppTheme.Spacing.xxs)
                    .background(Capsule().fill(AppTheme.Ink.surface))

                Button {
                    viewModel.openChest()
                    isChestShaking = true
                    Task {
                        try? await Task.sleep(nanoseconds: 700_000_000)
                        isChestShaking = false
                    }
                } label: {
                    Text(viewModel.chestReady ? "🎁 OPEN MYSTERY CHEST" : "CHEST ON COOLDOWN")
                        .font(AppTheme.Font.captionBold)
                        .foregroundStyle(AppTheme.Ink.background)
                        .frame(maxWidth: .infinity)
                        .frame(height: 46)
                        .background(
                            RoundedRectangle(cornerRadius: AppTheme.Radius.md, style: .continuous)
                                .fill(viewModel.chestReady ? AppTheme.Ink.gold : AppTheme.Ink.tile)
                        )
                        .opacity(viewModel.chestReady ? 1 : 0.5)
                }
                .buttonStyle(.plain)
                .disabled(!viewModel.chestReady)
                .padding(.top, AppTheme.Spacing.sm)
            }
            .frame(maxWidth: .infinity)
        }
    }

    /// `1.0f → 1.08f → 1.0f` and `0f → -6f → 0f` over 2000ms, infinite,
    /// `AccelerateDecelerateInterpolator`.
    private var chestBreathing: Animation? {
        viewModel.chestReady
            ? .easeInOut(duration: 1.0).repeatForever(autoreverses: true)
            : .default
    }

    private var chestScale: CGFloat {
        viewModel.chestReady && chestPulse ? 1.08 : 1.0
    }

    private var chestOffset: CGFloat {
        viewModel.chestReady && chestPulse ? -6 : 0
    }

    /// `tvDailyChestTimer`.
    private var chestStatusText: String {
        viewModel.chestReady ? "✨ Ready to open now!" : viewModel.chestCountdownText
    }

    // MARK: - Rank milestones

    /// `sectionRankMilestones`: header, XP status card, milestone list.
    private var rankMilestonesSection: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            HStack {
                Text("🏆 RANK LEVEL MILESTONES")
                    .font(AppTheme.Font.callout)
                    .foregroundStyle(AppTheme.Ink.cyan)
                Spacer()
                Text("Up to 71,250 🪙")
                    .font(AppTheme.Font.captionBold)
                    .foregroundStyle(AppTheme.Ink.gold)
            }

            InkCard(
                fill: AppTheme.Ink.surface,
                stroke: AppTheme.Ink.slate,
                radius: AppTheme.Radius.md,
                padding: AppTheme.Spacing.md
            ) {
                VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
                    Text("Clinical Mastery: \(TreasuryFormat.credits(clinicalMasteryXP)) XP (\(viewModel.currentTierName(xp: clinicalMasteryXP)))")
                        .font(AppTheme.Font.subheadline)
                        .foregroundStyle(AppTheme.Ink.textPrimary)

                    Text(nextRankHintText)
                        .font(AppTheme.Font.caption2)
                        .foregroundStyle(AppTheme.Ink.textSecondary)
                }
            }

            VStack(spacing: AppTheme.Spacing.sm) {
                ForEach(credits.rankMilestones) { milestone in
                    milestoneRow(milestone)
                }
            }
        }
    }

    /// `tvNextRankHint`.
    private var nextRankHintText: String {
        guard let next = viewModel.nextTier(xp: clinicalMasteryXP) else {
            return "🏆 Supreme Pinnacle! You have achieved Legend Rank!"
        }
        let needed = next.requiredXp - clinicalMasteryXP
        return "Need \(TreasuryFormat.credits(needed)) more XP to reach \(next.tierName) milestone!"
    }

    /// `createMilestoneView(milestone)`.
    private func milestoneRow(_ milestone: CreditsManager.RankLevelReward) -> some View {
        let isClaimed = viewModel.isRankClaimed(milestone)
        let canClaim = viewModel.canClaimRank(milestone, xp: clinicalMasteryXP)

        return InkCard(
            fill: AppTheme.Ink.surface,
            stroke: canClaim ? AppTheme.Palette.success : AppTheme.Ink.slate,
            radius: AppTheme.Radius.md,
            padding: AppTheme.Spacing.md
        ) {
            HStack(spacing: AppTheme.Spacing.md) {
                Image(systemName: milestone.iconSystemName)
                    .font(AppTheme.Font.title2)
                    .foregroundStyle(
                        isClaimed
                            ? AppTheme.Palette.success
                            : (canClaim ? AppTheme.Ink.gold : AppTheme.Ink.textHint)
                    )
                    .frame(width: 42, height: 42)

                VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
                    Text("Lvl \(milestone.level) • \(milestone.tierName)")
                        .font(AppTheme.Font.subheadline)
                        .foregroundStyle(AppTheme.Ink.textPrimary)

                    Text(milestoneRequirement(milestone))
                        .font(AppTheme.Font.caption2)
                        .foregroundStyle(AppTheme.Ink.textSecondary)

                    Text("+\(TreasuryFormat.credits(milestone.creditReward)) 🪙")
                        .font(AppTheme.Font.captionBold)
                        .foregroundStyle(AppTheme.Ink.gold)
                }

                Spacer(minLength: 0)

                milestoneAction(milestone, isClaimed: isClaimed, canClaim: canClaim)
            }
        }
    }

    /// `if (milestone.requiredXp == 0) "Aspirant Starter" else "Req: $req XP"`.
    private func milestoneRequirement(_ milestone: CreditsManager.RankLevelReward) -> String {
        if milestone.requiredXp == 0 { return "Aspirant Starter" }
        return "Req: \(TreasuryFormat.credits(milestone.requiredXp)) XP"
    }

    /// The three `btnAction` states of `createMilestoneView`.
    @ViewBuilder
    private func milestoneAction(
        _ milestone: CreditsManager.RankLevelReward,
        isClaimed: Bool,
        canClaim: Bool
    ) -> some View {
        if isClaimed {
            milestoneBadge(text: "CLAIMED ✓", fill: AppTheme.Ink.tile, foreground: AppTheme.Ink.textHint)
        } else if canClaim {
            Button {
                viewModel.claimRank(milestone, xp: clinicalMasteryXP)
            } label: {
                milestoneBadge(
                    text: "CLAIM",
                    fill: AppTheme.Palette.success,
                    foreground: AppTheme.Ink.background
                )
            }
            .buttonStyle(.plain)
        } else {
            milestoneBadge(
                text: "🔒 \(TreasuryFormat.credits(milestone.requiredXp - clinicalMasteryXP)) XP",
                fill: AppTheme.Ink.tile,
                foreground: AppTheme.Ink.textHint
            )
        }
    }

    private func milestoneBadge(text: String, fill: Color, foreground: Color) -> some View {
        Text(text)
            .font(AppTheme.Font.caption2)
            .foregroundStyle(foreground)
            .padding(.horizontal, AppTheme.Spacing.md)
            .padding(.vertical, AppTheme.Spacing.sm)
            .background(RoundedRectangle(cornerRadius: AppTheme.Radius.sm, style: .continuous).fill(fill))
    }

    // MARK: - Special offers

    /// `sectionSpecialOffers` + `setupSpecialOffers()`.
    private var specialOffersSection: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            Text("🔥 LIMITED-TIME SPECIAL OFFERS")
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Palette.danger)

            Text("Massive discount bundles with instant Cashfree checkout")
                .font(AppTheme.Font.caption2)
                .foregroundStyle(AppTheme.Ink.textSecondary)

            VStack(spacing: AppTheme.Spacing.md) {
                ForEach(credits.specialOffers) { offer in
                    offerCard(offer)
                }
            }
        }
    }

    private func offerCard(_ offer: CreditsManager.CreditPackage) -> some View {
        InkCard(
            fill: AppTheme.Ink.streakCard,
            stroke: AppTheme.Palette.danger,
            radius: AppTheme.Radius.card
        ) {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                Text("🔥 \(offer.bonusText ?? "SPECIAL OFFER")")
                    .font(AppTheme.Font.micro)
                    .foregroundStyle(AppTheme.Palette.danger)
                    .padding(.horizontal, AppTheme.Spacing.sm)
                    .padding(.vertical, AppTheme.Spacing.xxs)
                    .background(Capsule().fill(AppTheme.Ink.streakCard))

                HStack(spacing: AppTheme.Spacing.md) {
                    VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
                        Text(offer.title)
                            .font(AppTheme.Font.callout)
                            .foregroundStyle(AppTheme.Ink.textPrimary)

                        Text("\(TreasuryFormat.credits(offer.credits)) Credits 🪙")
                            .font(AppTheme.Font.callout)
                            .foregroundStyle(AppTheme.Ink.gold)
                    }

                    Spacer(minLength: 0)

                    Button {
                        viewModel.beginPurchase(.specialOffer(offer))
                    } label: {
                        Text("\(offer.priceInr) (\(offer.priceUsd))")
                            .font(AppTheme.Font.captionBold)
                            .foregroundStyle(AppTheme.Ink.textPrimary)
                            .padding(.horizontal, AppTheme.Spacing.md)
                            .frame(height: 42)
                            .background(
                                RoundedRectangle(cornerRadius: AppTheme.Radius.md, style: .continuous)
                                    .fill(AppTheme.Palette.danger)
                            )
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    // MARK: - Store packages

    /// `sectionCreditPackages` + `setupCreditPackages()` — the 2-column
    /// `GridLayout` of `item_treasure_store_card.xml`.
    private var creditPackagesSection: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            Text("💎 BUY CREDIT PACKAGES")
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Ink.gold)

            Text("Instant UPI, Cards & NetBanking via Cashfree Gateway")
                .font(AppTheme.Font.caption2)
                .foregroundStyle(AppTheme.Ink.textSecondary)

            LazyVGrid(
                columns: [
                    GridItem(.flexible(), spacing: AppTheme.Spacing.sm),
                    GridItem(.flexible(), spacing: AppTheme.Spacing.sm)
                ],
                spacing: AppTheme.Spacing.sm
            ) {
                ForEach(credits.storePackages) { pack in
                    packageCard(pack)
                }
            }
        }
    }

    private func packageCard(_ pack: CreditsManager.CreditPackage) -> some View {
        InkCard(
            fill: AppTheme.Ink.surface,
            stroke: pack.isBestValue ? AppTheme.Ink.cyan : AppTheme.Ink.slate,
            radius: AppTheme.Radius.md,
            padding: AppTheme.Spacing.md
        ) {
            VStack(spacing: AppTheme.Spacing.xs) {
                packTag(pack)

                AndroidIcon(.ic_credit_coin, size: 44)
                    .padding(.top, AppTheme.Spacing.xxs)

                Text(pack.title)
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Ink.textPrimary)
                    .lineLimit(1)

                Text("\(TreasuryFormat.credits(pack.credits)) 🪙")
                    .font(AppTheme.Font.callout)
                    .foregroundStyle(AppTheme.Ink.gold)

                Button {
                    viewModel.beginPurchase(.store(pack))
                } label: {
                    Text("\(pack.priceInr) (\(pack.priceUsd))")
                        .font(AppTheme.Font.captionBold)
                        .foregroundStyle(AppTheme.Ink.background)
                        .frame(maxWidth: .infinity)
                        .frame(height: 36)
                        .background(
                            RoundedRectangle(cornerRadius: AppTheme.Radius.sm, style: .continuous)
                                .fill(pack.isBestValue ? AppTheme.Ink.cyan : AppTheme.Ink.gold)
                        )
                }
                .buttonStyle(.plain)
                .padding(.top, AppTheme.Spacing.xs)
            }
            .frame(maxWidth: .infinity)
        }
    }

    /// `tvPackTag` — `bonusText`, or "BEST VALUE" when the pack has no bonus.
    @ViewBuilder
    private func packTag(_ pack: CreditsManager.CreditPackage) -> some View {
        if let bonus = pack.bonusText, !bonus.isEmpty {
            tagLabel(bonus, isBestValue: pack.isBestValue)
        } else if pack.isBestValue {
            tagLabel("BEST VALUE", isBestValue: true)
        }
    }

    private func tagLabel(_ text: String, isBestValue: Bool) -> some View {
        Text(text)
            .font(AppTheme.Font.micro)
            .foregroundStyle(AppTheme.Ink.background)
            .padding(.horizontal, AppTheme.Spacing.xs)
            .padding(.vertical, AppTheme.Spacing.xxs)
            .background(Capsule().fill(isBestValue ? AppTheme.Ink.cyan : AppTheme.Ink.gold))
    }

    // MARK: - Transient surfaces

    /// `ProgressDialog("Initiating secure Cashfree checkout…")`.
    private var checkoutProgressOverlay: some View {
        ZStack {
            AppTheme.Ink.background.opacity(0.6).ignoresSafeArea()
            VStack(spacing: AppTheme.Spacing.md) {
                ProgressView()
                Text("Initiating secure Cashfree checkout…")
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Ink.textPrimary)
            }
            .padding(AppTheme.Spacing.xl)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.materialCard, style: .continuous)
                    .fill(AppTheme.Ink.surface)
            )
        }
    }

    private func toastBanner(_ message: String) -> some View {
        Text(message)
            .font(AppTheme.Font.caption)
            .foregroundStyle(AppTheme.Ink.textPrimary)
            .padding(.horizontal, AppTheme.Spacing.lg)
            .padding(.vertical, AppTheme.Spacing.md)
            .frame(maxWidth: .infinity)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.materialCard, style: .continuous)
                    .fill(AppTheme.Ink.elevated)
            )
            .shadow(color: .black.opacity(0.25), radius: AppTheme.Elevation.card, y: 2)
    }

    // MARK: - Gateway chooser

    private var purchaseDialogPresented: Binding<Bool> {
        Binding(
            get: { viewModel.purchaseOffer != nil },
            set: { isPresented in
                if !isPresented { viewModel.cancelPurchase() }
            }
        )
    }

    private var pendingOrderPresented: Binding<Bool> {
        Binding(
            get: { viewModel.pendingOrder != nil },
            set: { isPresented in
                if !isPresented { viewModel.dismissPendingOrder() }
            }
        )
    }

    /// `AlertDialog.Builder.setTitle("Acquire ${pack.title}")`.
    private var purchaseDialogTitle: String {
        guard let offer = viewModel.purchaseOffer else { return "Acquire" }
        return "Acquire \(offer.pack.title)"
    }

    /// `setMessage("Package: $credStr Credits 🪙\n\nChoose payment gateway:")`.
    private var purchaseDialogMessage: String {
        guard let offer = viewModel.purchaseOffer else { return "" }
        return "Package: \(TreasuryFormat.credits(offer.pack.credits)) Credits 🪙\n\nChoose payment gateway:"
    }

    @ViewBuilder
    private var purchaseDialogActions: some View {
        if let offer = viewModel.purchaseOffer {
            Button("💳 PAY VIA CASHFREE (\(offer.pack.priceInr))") {
                viewModel.startCashfreeCheckout(
                    offer,
                    userId: resolvedUserId,
                    phone: resolvedPhone,
                    email: resolvedEmail
                )
            }
            Button("🧪 DEMO / TEST UNLOCK") {
                viewModel.applyDemoUnlock(offer.pack)
            }
        }
        Button("CANCEL", role: .cancel) { viewModel.cancelPurchase() }
    }

    // MARK: - Alerts

    private var alertPresented: Binding<Bool> {
        Binding(
            get: { viewModel.dialog != nil },
            set: { isPresented in
                if !isPresented { viewModel.dismissDialog() }
            }
        )
    }

    private var alertTitle: String {
        switch viewModel.dialog {
        case let .reward(title, _, _): return title
        case let .cashfreeFailure(reason, _):
            return isCashfreeKYCFailure(reason)
                ? "Cashfree Merchant Activation Required"
                : "Cashfree Gateway Notice"
        case nil: return ""
        }
    }

    /// `errorReason.contains("transactions are not enabled", ignoreCase = true)`.
    private func isCashfreeKYCFailure(_ reason: String) -> Bool {
        reason.localizedCaseInsensitiveContains("transactions are not enabled")
    }

    /// `showRewardDialog`'s message, and both branches of
    /// `showCashfreeErrorNotice` — including the merchant-KYC notice triggered
    /// by "transactions are not enabled".
    private var alertMessage: String {
        switch viewModel.dialog {
        case let .reward(_, message, award):
            return """
            \(message)

            ✨ +\(TreasuryFormat.credits(award)) CREDITS ✨

            Your new treasury balance: \(TreasuryFormat.credits(credits.currentCredits)) 🪙
            """
        case let .cashfreeFailure(reason, _):
            if isCashfreeKYCFailure(reason) {
                return "Cashfree Gateway Notice:\n\n\"Transactions are not enabled for your payment gateway account.\"\n\nPlease log in to the Cashfree Merchant Dashboard (merchant.cashfree.com) to complete KYC and activate live payment collections."
            }
            return "The payment gateway returned the following notice:\n\n\(reason)\n\nIf you were charged, your credits will be updated automatically upon verification."
        case nil:
            return ""
        }
    }

    @ViewBuilder
    private var alertActions: some View {
        switch viewModel.dialog {
        case .reward:
            Button("AWESOME!") { viewModel.dismissDialog() }
        case .cashfreeFailure:
            Button("RETRY") {
                viewModel.retryLastCashfreeOrder(
                    userId: resolvedUserId,
                    phone: resolvedPhone,
                    email: resolvedEmail
                )
            }
            Button("DISMISS", role: .cancel) { viewModel.dismissDialog() }
        case nil:
            Button("OK", role: .cancel) { viewModel.dismissDialog() }
        }
    }
}

// MARK: - Cashfree hand-off sheet

/// Surfaces the `CashfreeOrder` created by `create_order.php` until the Payment
/// module takes the session through its checkout.
private struct CashfreeCheckoutSheet: View {

    let order: CashfreeOrder
    let onClose: () -> Void

    var body: some View {
        VStack(spacing: AppTheme.Spacing.lg) {
            Text("💳 Cashfree Order Created")
                .font(AppTheme.Font.title3)
                .foregroundStyle(AppTheme.Ink.textPrimary)

            Text("Your checkout session is ready. Complete the secure payment in the payment module — credits are applied automatically once the gateway verifies the order.")
                .font(AppTheme.Font.caption)
                .foregroundStyle(AppTheme.Ink.textSecondary)
                .multilineTextAlignment(.center)

            VStack(spacing: AppTheme.Spacing.sm) {
                detailRow("Package", order.packageTitle)
                detailRow("Credits", "+ \(TreasuryFormat.credits(order.creditsToAdd))")
                detailRow("Order ID", order.orderID)
                detailRow("Session ID", order.paymentSessionID)
                detailRow("Environment", order.environment)
            }

            PrimaryButton(title: "Close", action: onClose)
        }
        .padding(AppTheme.Spacing.xl)
        .frame(maxWidth: .infinity)
        .background(AppTheme.Ink.background.ignoresSafeArea())
    }

    private func detailRow(_ label: String, _ value: String) -> some View {
        HStack {
            Text(label)
                .font(AppTheme.Font.caption2)
                .foregroundStyle(AppTheme.Ink.textSecondary)
            Spacer(minLength: AppTheme.Spacing.sm)
            Text(value)
                .font(AppTheme.Font.caption)
                .foregroundStyle(AppTheme.Ink.textPrimary)
                .multilineTextAlignment(.trailing)
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, AppTheme.Spacing.sm)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.sm, style: .continuous)
                .fill(AppTheme.Ink.surface)
        )
    }
}