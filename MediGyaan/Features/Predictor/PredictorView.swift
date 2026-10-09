import SwiftUI
import UIKit

/// NEET-PG Rank Predictor and College Lookup.
/// 1:1 replication of Android `PredictCollegeActivity.kt` and `CollegeDetailActivity.kt`.
///
/// Features:
/// - Real-time rank prediction from performance (`predict_rank.php`)
/// - Dynamic interactive Rank Slider (1,000 to 200,000) with live Tier calculation
/// - Backend college matching with Safe/Target/Dream categorization (`predictor_app.php`)
/// - Multi-dimensional filter chips: Subject (21 clinical specialties), State, Category, Quota, Type, Fee, Bond, Stipend, Chance
/// - Real-time institute search & autocomplete
/// - Floating filter summary pill with scroll snap
/// - Side-by-side comparison modal (up to 3 colleges) with share & clear
/// - Full counseling report PDF generation & system share (`UIGraphicsPDFRenderer`)
/// - Shortlist sharing (WhatsApp, Telegram, system share)
/// - Deep scraped college profile & fee details (`CollegeHtmlRepository`)
/// - AI counseling chat integration (`AiChatView`)
/// - Full VPS telemetry logging (`RemoteLogger`)
struct PredictorView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @ObservedObject private var credits = CreditsManager.shared

    // Core Rank & Tier State
    @State private var selectedRank: String = "50000"
    @State private var originalRank: String = "50000"
    @State private var selectedTier: String = "📘 Average"

    // Filter Parameters
    @State private var selectedCategory: String = "GEN"
    @State private var selectedQuota: String = "All India"
    @State private var selectedSubject: String = ""
    @State private var selectedState: String = ""
    @State private var selectedCollegeType: String = "" // "government", "private", ""
    @State private var selectedMaxFee: String = ""
    @State private var selectedMaxBond: String = ""
    @State private var selectedMinStipend: String = ""
    @State private var selectedAiPreference: String = ""
    @State private var selectedInstitute: String = ""

    // Dynamic Filter Option Lists
    @State private var distinctSubjects: [String] = []
    @State private var distinctStates: [String] = []
    @State private var distinctCategories: [String] = ["GEN", "OBC", "SC", "ST", "EWS"]
    @State private var distinctQuotas: [String] = ["All India", "State", "AIQ", "NRI", "Management"]
    @State private var distinctCollegeTypes: [String] = ["Government", "Private"]

    // Data Collections
    @State private var masterColleges: [CollegeModel] = []
    @State private var safeColleges: [CollegeModel] = []
    @State private var targetColleges: [CollegeModel] = []
    @State private var dreamColleges: [CollegeModel] = []

    // Counts & AI Counseling
    @State private var totalResults: Int = 0
    @State private var safeCount: Int = 0
    @State private var targetCount: Int = 0
    @State private var dreamCount: Int = 0
    @State private var aiSummaryText: String = "Loading AI counseling..."

    // UI States
    @State private var isLoading: Bool = false
    @State private var summaryVisible: Bool = true
    @State private var compareList: [CollegeModel] = []

    // Sheets & Destination Controls
    @State private var showingCustomRankSheet: Bool = false
    @State private var activeFilterSheet: PredictorFilterType? = nil
    @State private var showingCompareModal: Bool = false
    @State private var showingAiChat: Bool = false
    @State private var showingPaywallSheet: Bool = false
    @State private var selectedCollegeForDetail: CollegeModel? = nil
    @State private var shareSheetItems: [Any]? = nil
    @State private var errorMessage: String? = nil

    // 21 Predefined Medical Clinical Specialties
    private let defaultSubjects = [
        "Anatomy", "Physiology", "Biochemistry", "Pharmacology",
        "Pathology", "Microbiology", "Forensic Medicine", "Community Medicine",
        "General Medicine", "Paediatrics", "Dermatology", "Psychiatry",
        "Respiratory Medicine", "Radiology", "Anaesthesiology", "General Surgery",
        "Orthopaedics", "ENT", "Ophthalmology", "Obstetrics & Gynaecology"
    ]

    var body: some View {
        ScrollViewReader { scrollProxy in
            ZStack(alignment: .bottom) {
                ScrollView {
                    VStack(spacing: AppTheme.Spacing.md) {
                        Color.clear.frame(height: 1).id("top_anchor")

                        // 1. Summary & Rank Tier Card
                        if summaryVisible {
                            rankSummaryCard
                            aiCounselingCard
                        }

                        // 2. Summary Toggle & Top Action Buttons
                        summaryControlsRow

                        // 3. Institute Autocomplete / Instant Filter
                        instituteSearchField

                        // 4. Horizontal Scrollable Filter Chips
                        filterChipsScrollView

                        // 5. Active Compare Notice Bar (if selected)
                        if !compareList.isEmpty {
                            compareActionBar
                        }

                        // 6. Sectioned College Feed
                        if isLoading {
                            shimmerLoadingView
                        } else if totalDisplayColleges == 0 {
                            emptyCollegesView
                        } else {
                            collegesFeedSection
                        }

                        // Padding for floating bottom summary pill
                        Spacer().frame(height: 70)
                    }
                    .padding(.horizontal, AppTheme.Spacing.md)
                    .padding(.top, AppTheme.Spacing.sm)
                }

                // Floating Filter Summary Bar (matches Android Task 4)
                floatingFilterSummaryPill(scrollProxy: scrollProxy)
            }
        }
        .screenBackground()
        .navigationTitle("College Predictor")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Button {
                    RemoteLogger.log(tag: "Predictor_AIChat_Click", message: "Launching AI Counseling Chat")
                    showingAiChat = true
                } label: {
                    Label("AI Counseling", systemImage: "sparkles")
                        .font(AppTheme.Font.callout.weight(.semibold))
                        .foregroundStyle(AppTheme.Palette.primary)
                }
            }
        }
        .task {
            await initializePredictor()
        }
        .refreshable {
            RemoteLogger.log(tag: "Predictor_PullToRefresh", message: "Refetching colleges for rank \(selectedRank)")
            await fetchColleges()
        }
        // Custom Rank Slider Sheet
        .sheet(isPresented: $showingCustomRankSheet) {
            CustomRankDialog(
                currentRank: selectedRank,
                originalRank: originalRank,
                onApply: { newRank, newTier in
                    selectedRank = newRank
                    selectedTier = newTier
                    RemoteLogger.log(tag: "Predictor_Rank_Applied", message: "Custom rank applied: \(newRank), Tier: \(newTier)")
                    Task { await fetchColleges() }
                },
                onResetOriginal: {
                    selectedRank = originalRank
                    selectedTier = recalcTierForRank(Int(originalRank) ?? 50000)
                    RemoteLogger.log(tag: "Predictor_Rank_Reset", message: "Reset to original rank: \(originalRank)")
                    Task { await fetchColleges() }
                }
            )
            .presentationDetents([.medium])
        }
        // Filter Selection Sheets
        .sheet(item: $activeFilterSheet) { filterType in
            FilterSelectionSheet(
                filterType: filterType,
                currentValue: currentFilterValue(for: filterType),
                options: options(for: filterType),
                onSelect: { selected in
                    applyFilterSelection(filterType: filterType, value: selected)
                }
            )
            .presentationDetents([.medium, .large])
        }
        // Compare Modal Sheet
        .sheet(isPresented: $showingCompareModal) {
            CompareCollegesSheet(
                colleges: compareList,
                onRemove: { college in
                    compareList.removeAll { $0.id == college.id && $0.institute == college.institute }
                    if compareList.isEmpty { showingCompareModal = false }
                },
                onClearAll: {
                    compareList.removeAll()
                    showingCompareModal = false
                },
                onShareComparison: {
                    shareShortlist(customList: compareList)
                }
            )
            .presentationDetents([.medium, .large])
        }
        // College Detail Modal
        .sheet(item: $selectedCollegeForDetail) { college in
            NavigationStack {
                CollegeDetailView(collegeModel: college)
            }
        }
        // AI Chat Sheet
        .sheet(isPresented: $showingAiChat) {
            NavigationStack {
                AiChatView()
            }
        }
        // Predictor Pass Paywall Sheet
        .sheet(isPresented: $showingPaywallSheet) {
            PredictorPassPaywallView {
                credits.grantPredictorPass()
                showingPaywallSheet = false
                RemoteLogger.log(tag: "Predictor_Pass_Unlocked", message: "User unlocked predictor pass")
                Task { await fetchColleges() }
            }
            .presentationDetents([.medium])
        }
        // Share Activity View Controller
        .sheet(isPresented: Binding(
            get: { shareSheetItems != nil },
            set: { if !$0 { shareSheetItems = nil } }
        )) {
            if let items = shareSheetItems {
                ShareActivitySheet(activityItems: items)
            }
        }
        .errorAlert(message: $errorMessage)
    }

    // MARK: - 1. Rank & Tier Summary Card

    private var rankSummaryCard: some View {
        CardContainer {
            VStack(spacing: AppTheme.Spacing.sm) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("NEET-PG COUNSELING PREDICTOR")
                            .font(.system(size: 11, weight: .bold))
                            .foregroundStyle(AppTheme.Palette.primary)
                            .tracking(0.5)

                        HStack(spacing: 8) {
                            Text("🎯 Expected Rank: #\(selectedRank)")
                                .font(.system(size: 20, weight: .bold, design: .rounded))
                                .foregroundStyle(AppTheme.Palette.textPrimary)

                            Button {
                                showingCustomRankSheet = true
                            } label: {
                                Image(systemName: "slider.horizontal.3")
                                    .font(.system(size: 14, weight: .semibold))
                                    .padding(6)
                                    .background(Circle().fill(AppTheme.Palette.primary.opacity(0.15)))
                                    .foregroundStyle(AppTheme.Palette.primary)
                            }
                        }

                        Text("Tier: \(selectedTier)")
                            .font(AppTheme.Font.subheadline.weight(.semibold))
                            .foregroundStyle(tierColor(selectedTier))
                    }

                    Spacer()

                    VStack(alignment: .trailing, spacing: 2) {
                        Text("Available")
                            .font(.system(size: 10, weight: .medium))
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                        Text("\(totalResults)")
                            .font(.system(size: 22, weight: .bold, design: .rounded))
                            .foregroundStyle(AppTheme.Palette.primary)
                        Text("Colleges")
                            .font(.system(size: 10, weight: .medium))
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                            .fill(AppTheme.Palette.surface)
                    )
                }

                Divider()

                // Stat Counters Row: SAFE, TARGET, DREAM
                HStack(spacing: AppTheme.Spacing.xs) {
                    predictorCounterPill(
                        title: "SAFE",
                        count: safeCount,
                        subtitle: "High Chance",
                        color: Color(red: 5/255, green: 150/255, blue: 105/255)
                    )

                    predictorCounterPill(
                        title: "TARGET",
                        count: targetCount,
                        subtitle: "Competitive",
                        color: Color(red: 217/255, green: 119/255, blue: 6/255)
                    )

                    predictorCounterPill(
                        title: "DREAM",
                        count: dreamCount,
                        subtitle: "Aspirational",
                        color: Color(red: 225/255, green: 29/255, blue: 72/255)
                    )
                }
            }
        }
    }

    private func predictorCounterPill(title: String, count: Int, subtitle: String, color: Color) -> some View {
        VStack(spacing: 2) {
            Text(title)
                .font(.system(size: 11, weight: .bold))
                .foregroundStyle(color)
            Text("\(count)")
                .font(.system(size: 17, weight: .bold, design: .rounded))
                .foregroundStyle(AppTheme.Palette.textPrimary)
            Text(subtitle)
                .font(.system(size: 9, weight: .medium))
                .foregroundStyle(AppTheme.Palette.textSecondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 6)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                .fill(color.opacity(0.12))
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                        .stroke(color.opacity(0.3), lineWidth: 1)
                )
        )
    }

    // MARK: - 2. AI Counseling Card

    private var aiCounselingCard: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
                HStack {
                    Label("AI Counseling Analysis", systemImage: "sparkles")
                        .font(AppTheme.Font.headline)
                        .foregroundStyle(AppTheme.Palette.primary)

                    Spacer()

                    Button {
                        showingAiChat = true
                    } label: {
                        Text("Chat with AI")
                            .font(.system(size: 11, weight: .bold))
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(Capsule().fill(AppTheme.Palette.primary))
                            .foregroundStyle(.white)
                    }
                }

                Text(aiSummaryText)
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Palette.textSecondary)
                    .lineLimit(nil)
                    .padding(.top, 2)
            }
        }
    }

    // MARK: - 3. Summary Toggle & Top Action Buttons

    private var summaryControlsRow: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            Button {
                withAnimation(.spring(response: 0.35)) {
                    summaryVisible.toggle()
                }
            } label: {
                Label(summaryVisible ? "Hide Summary" : "Show Summary", systemImage: summaryVisible ? "chevron.up" : "chevron.down")
                    .font(AppTheme.Font.caption.weight(.semibold))
                    .foregroundStyle(AppTheme.Palette.textSecondary)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                            .fill(AppTheme.Palette.surface)
                    )
            }

            Spacer()

            // Export PDF Report Button
            Button {
                RemoteLogger.log(tag: "Predictor_PDF_Export_Tap", message: "Exporting PDF report for rank \(selectedRank)")
                exportCollegesToPdf()
            } label: {
                HStack(spacing: 4) {
                    Image(systemName: "doc.text.fill")
                    Text("Export PDF")
                }
                .font(AppTheme.Font.caption.weight(.bold))
                .foregroundStyle(Color.white)
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                        .fill(Color(red: 15/255, green: 23/255, blue: 42/255))
                        .overlay(
                            RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                                .stroke(Color(red: 56/255, green: 189/255, blue: 248/255), lineWidth: 1)
                        )
                )
            }

            // Share Shortlist Button
            Button {
                RemoteLogger.log(tag: "Predictor_Share_Shortlist_Tap", message: "Sharing shortlist for rank \(selectedRank)")
                shareShortlist(customList: compareList.isEmpty ? masterColleges : compareList)
            } label: {
                HStack(spacing: 4) {
                    Image(systemName: "square.and.arrow.up")
                    Text("Share")
                }
                .font(AppTheme.Font.caption.weight(.bold))
                .foregroundStyle(AppTheme.Palette.primary)
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                        .fill(AppTheme.Palette.primary.opacity(0.12))
                )
            }
        }
    }

    // MARK: - 4. Institute Autocomplete Search Field

    private var instituteSearchField: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            Image(systemName: "building.columns")
                .foregroundStyle(AppTheme.Palette.textSecondary)

            TextField("Search institute by name (e.g. AIIMS, PGI)…", text: $selectedInstitute)
                .font(AppTheme.Font.callout)
                .textInputAutocapitalization(.words)
                .autocorrectionDisabled()
                .onChange(of: selectedInstitute) { _ in
                    applyLocalFilters()
                }

            if !selectedInstitute.isEmpty {
                Button {
                    selectedInstitute = ""
                    applyLocalFilters()
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }
            }
        }
        .padding(AppTheme.Spacing.sm)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.md)
                .fill(AppTheme.Palette.surface)
        )
    }

    // MARK: - 5. Horizontal Filter Chips Scroll View

    private var filterChipsScrollView: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                // Rank Chip
                PredictorFilterChip(
                    title: "Rank: \(selectedRank)",
                    isActive: selectedRank != originalRank,
                    action: { showingCustomRankSheet = true }
                )

                // Subject Chip
                PredictorFilterChip(
                    title: "Subject: \(selectedSubject.isEmpty ? "Any" : selectedSubject)",
                    isActive: !selectedSubject.isEmpty,
                    action: { activeFilterSheet = .subject }
                )

                // State Chip
                PredictorFilterChip(
                    title: "State: \(selectedState.isEmpty ? "Any" : selectedState)",
                    isActive: !selectedState.isEmpty,
                    action: { activeFilterSheet = .state }
                )

                // Category Chip
                PredictorFilterChip(
                    title: "Category: \(selectedCategory)",
                    isActive: selectedCategory != "GEN",
                    action: { activeFilterSheet = .category }
                )

                // Quota Chip
                PredictorFilterChip(
                    title: "Quota: \(selectedQuota)",
                    isActive: selectedQuota != "All India",
                    action: { activeFilterSheet = .quota }
                )

                // College Type Chip
                PredictorFilterChip(
                    title: "Type: \(selectedCollegeType.isEmpty ? "Any" : selectedCollegeType.capitalized)",
                    isActive: !selectedCollegeType.isEmpty,
                    action: { activeFilterSheet = .type }
                )

                // Fee Chip
                PredictorFilterChip(
                    title: "Fee: \(selectedMaxFee.isEmpty ? "Any" : "<= ₹\(selectedMaxFee)")",
                    isActive: !selectedMaxFee.isEmpty,
                    action: { activeFilterSheet = .fee }
                )

                // Bond Chip
                PredictorFilterChip(
                    title: "Bond: \(selectedMaxBond.isEmpty ? "Any" : "<= \(selectedMaxBond)y")",
                    isActive: !selectedMaxBond.isEmpty,
                    action: { activeFilterSheet = .bond }
                )

                // Stipend Chip
                PredictorFilterChip(
                    title: "Stipend: \(selectedMinStipend.isEmpty ? "Any" : ">= ₹\(selectedMinStipend)")",
                    isActive: !selectedMinStipend.isEmpty,
                    action: { activeFilterSheet = .stipend }
                )

                // Chance Chip
                PredictorFilterChip(
                    title: "Chance: \(selectedAiPreference.isEmpty ? "Any" : selectedAiPreference)",
                    isActive: !selectedAiPreference.isEmpty,
                    action: { activeFilterSheet = .chance }
                )

                // Reset Filters Chip
                Button {
                    resetFilters()
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: "arrow.counterclockwise")
                        Text("Reset")
                    }
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(Color.red)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(
                        Capsule().fill(Color.red.opacity(0.12))
                    )
                }
            }
            .padding(.vertical, 4)
        }
    }

    // MARK: - 6. Compare Action Notice Bar

    private var compareActionBar: some View {
        CardContainer(padding: AppTheme.Spacing.sm) {
            HStack {
                HStack(spacing: 6) {
                    Image(systemName: "scale.3d")
                        .foregroundStyle(AppTheme.Palette.primary)
                    Text("Comparing \(compareList.count)/3 colleges")
                        .font(AppTheme.Font.callout.weight(.semibold))
                        .foregroundStyle(AppTheme.Palette.textPrimary)
                }

                Spacer()

                Button {
                    showingCompareModal = true
                } label: {
                    Text("Compare Now")
                        .font(.system(size: 12, weight: .bold))
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background(Capsule().fill(AppTheme.Palette.primary))
                        .foregroundStyle(.white)
                }

                Button {
                    compareList.removeAll()
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }
            }
        }
    }

    // MARK: - 7. Sectioned College Feed

    private var totalDisplayColleges: Int {
        safeColleges.count + targetColleges.count + dreamColleges.count
    }

    private var collegesFeedSection: some View {
        LazyVStack(spacing: AppTheme.Spacing.md) {
            // SAFE Section
            if !safeColleges.isEmpty {
                collegeSectionGroup(
                    title: "SAFE COLLEGES",
                    subtitle: "High probability of seat allocation",
                    colleges: safeColleges,
                    badgeColor: Color(red: 5/255, green: 150/255, blue: 105/255)
                )
            }

            // TARGET Section
            if !targetColleges.isEmpty {
                collegeSectionGroup(
                    title: "TARGET COLLEGES",
                    subtitle: "Closing rank very close to candidate score",
                    colleges: targetColleges,
                    badgeColor: Color(red: 217/255, green: 119/255, blue: 6/255)
                )
            }

            // DREAM Section
            if !dreamColleges.isEmpty {
                collegeSectionGroup(
                    title: "DREAM COLLEGES",
                    subtitle: "Highly competitive, aspirational cutoff rank",
                    colleges: dreamColleges,
                    badgeColor: Color(red: 225/255, green: 29/255, blue: 72/255)
                )
            }
        }
    }

    private func collegeSectionGroup(
        title: String,
        subtitle: String,
        colleges: [CollegeModel],
        badgeColor: Color
    ) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.system(size: 14, weight: .bold))
                        .foregroundStyle(badgeColor)
                    Text(subtitle)
                        .font(.system(size: 11))
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }
                Spacer()
                Text("\(colleges.count) options")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(AppTheme.Palette.textSecondary)
            }
            .padding(.horizontal, 4)
            .padding(.top, 8)

            ForEach(colleges) { college in
                CollegeCardRow(
                    college: college,
                    isCompared: compareList.contains(where: { $0.id == college.id && $0.institute == college.institute }),
                    onTap: {
                        RemoteLogger.log(tag: "Predictor_College_Tap", message: "Viewing college detail: \(college.institute)")
                        selectedCollegeForDetail = college
                    },
                    onLongPress: {
                        toggleCompare(college)
                    }
                )
            }
        }
    }

    // MARK: - 8. Floating Summary Bottom Pill

    private func floatingFilterSummaryPill(scrollProxy: ScrollViewProxy) -> some View {
        let parts = [
            "Rank \(selectedRank)",
            selectedSubject.isEmpty ? nil : "Subj \(selectedSubject)",
            selectedState.isEmpty ? nil : "St \(selectedState)",
            selectedInstitute.isEmpty ? nil : "Inst \(selectedInstitute)",
            "Cat \(selectedCategory)",
            "Quota \(selectedQuota)"
        ].compactMap { $0 }

        return Button {
            let impact = UIImpactFeedbackGenerator(style: .light)
            impact.impactOccurred()
            withAnimation(.spring(response: 0.4)) {
                scrollProxy.scrollTo("top_anchor", anchor: .top)
            }
        } label: {
            HStack(spacing: 6) {
                Text("🎯 " + parts.joined(separator: " • "))
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(Color.white)
                    .lineLimit(1)

                Image(systemName: "arrow.up")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(Color(red: 56/255, green: 189/255, blue: 248/255))
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .background(
                Capsule()
                    .fill(Color(red: 15/255, green: 23/255, blue: 42/255))
                    .overlay(
                        Capsule()
                            .stroke(Color(red: 56/255, green: 189/255, blue: 248/255), lineWidth: 1.5)
                    )
                    .shadow(color: Color.black.opacity(0.4), radius: 8, x: 0, y: 4)
            )
        }
        .padding(.bottom, 12)
    }

    // MARK: - Loading & Empty States

    private var shimmerLoadingView: some View {
        VStack(spacing: AppTheme.Spacing.md) {
            ProgressView()
                .scaleEffect(1.2)
                .padding(.top, 40)
            Text("Analyzing 280,000 NEET-PG cutoffs & quotas…")
                .font(AppTheme.Font.subheadline)
                .foregroundStyle(AppTheme.Palette.textSecondary)
        }
        .frame(maxWidth: .infinity, minHeight: 200)
    }

    private var emptyCollegesView: some View {
        VStack(spacing: AppTheme.Spacing.md) {
            Image(systemName: "building.columns.slash")
                .font(.system(size: 44))
                .foregroundStyle(AppTheme.Palette.textSecondary.opacity(0.5))
                .padding(.top, 40)

            Text("No Colleges Matched")
                .font(AppTheme.Font.headline)
                .foregroundStyle(AppTheme.Palette.textPrimary)

            Text("Try adjusting the Rank slider, Subject specialty, or widening your Category and Quota filters.")
                .font(AppTheme.Font.caption)
                .foregroundStyle(AppTheme.Palette.textSecondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)

            Button {
                resetFilters()
            } label: {
                Text("Reset All Filters")
                    .font(AppTheme.Font.callout.weight(.bold))
                    .padding(.horizontal, 16)
                    .padding(.vertical, 8)
                    .background(Capsule().fill(AppTheme.Palette.primary))
                    .foregroundStyle(.white)
            }
        }
        .frame(maxWidth: .infinity, minHeight: 200)
    }

    // MARK: - Networking & Business Logic

    @MainActor
    private func initializePredictor() async {
        // Check predictor entitlement pass
        if !credits.hasPredictorPass {
            RemoteLogger.log(tag: "Predictor_Access_Check", message: "Checking predictor entitlement for user \(session.userId)")
            let hasServerAccess = await checkPredictorAccessServer()
            if hasServerAccess {
                credits.grantPredictorPass()
            } else {
                showingPaywallSheet = true
                return
            }
        }

        // Fetch user expected rank prediction from server
        await fetchPredictionFromServer()
    }

    @MainActor
    private func checkPredictorAccessServer() async -> Bool {
        guard session.userId > 0 else { return false }
        guard let url = URL(string: "https://medigyaan.com/Neurons/api/check_predictor_access.php") else { return false }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("EduLabsRTM_Secure_v1_2026", forHTTPHeaderField: "X-App-Signature")
        let body: [String: Any] = [
            "user_id": session.userId,
            "entitlement_key": "predict_college_pass"
        ]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        do {
            let (data, _) = try await URLSession.shared.data(for: request)
            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let unlocked = json["unlocked"] as? Bool {
                return unlocked
            }
        } catch {
            RemoteLogger.log(tag: "Predictor_Access_Err", message: "Server access check failed: \(error.localizedDescription)")
        }
        return false
    }

    @MainActor
    private func fetchPredictionFromServer() async {
        guard let url = URL(string: "https://medigyaan.com/Neurons/predict_rank.php") else {
            await fetchColleges()
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.setValue("EduLabsRTM_Secure_v1_2026", forHTTPHeaderField: "X-App-Signature")

        let bodyString = "user_id=\(session.userId)&accuracy=0&streak=0&attempted=0&correct=0"
        request.httpBody = bodyString.data(using: .utf8)

        do {
            let (data, _) = try await URLSession.shared.data(for: request)
            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               (json["success"] as? Bool) == true {
                let rankStr = String(describing: json["predicted_min_rank"] ?? "50000").filter { $0.isNumber }
                let tier = (json["tier"] as? String) ?? "Average"
                if !rankStr.isEmpty {
                    selectedRank = rankStr
                    originalRank = rankStr
                    selectedTier = tier.contains("📘") ? tier : "📘 \(tier)"
                }
            }
        } catch {
            RemoteLogger.log(tag: "Predictor_Rank_Err", message: "Failed to predict rank: \(error.localizedDescription)")
        }

        await fetchColleges()
    }

    @MainActor
    private func fetchColleges() async {
        isLoading = true
        defer { isLoading = false }

        guard let url = URL(string: "https://medigyaan.com/Neurons/predictor_app.php") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.setValue("EduLabsRTM_Secure_v1_2026", forHTTPHeaderField: "X-App-Signature")

        var params: [String: String] = [
            "rank": selectedRank,
            "category": selectedCategory.isEmpty ? "GEN" : selectedCategory,
            "quota": selectedQuota.isEmpty ? "All India" : selectedQuota,
            "subject": selectedSubject,
            "state": selectedState,
            "college_type": selectedCollegeType,
            "max_fee": selectedMaxFee,
            "max_bond": selectedMaxBond,
            "min_stipend": selectedMinStipend,
            "ai_preference": selectedAiPreference,
            "user_id": String(session.userId),
            "payment_required": "1",
            "year": "2026"
        ]

        let bodyString = params.map { "\($0.key)=\($0.value.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")" }.joined(separator: "&")
        request.httpBody = bodyString.data(using: .utf8)

        do {
            let (data, _) = try await URLSession.shared.data(for: request)
            guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                errorMessage = "Failed to parse college prediction results."
                return
            }

            if (json["payment_required"] as? Bool) == true && (json["success"] as? Bool) == false {
                showingPaywallSheet = true
                return
            }

            // Parse AI counseling summary
            if let rawAi = json["ai_summary"] as? String {
                aiSummaryText = formatAiSummary(rawAi)
            }

            totalResults = (json["total_results"] as? Int) ?? 0

            // Dynamic filter options lists
            if let subs = (json["distinct_subjects"] as? [String]) ?? (json["distinct_courses"] as? [String]), !subs.isEmpty {
                distinctSubjects = Array(Set(defaultSubjects + subs)).sorted()
            } else if distinctSubjects.isEmpty {
                distinctSubjects = defaultSubjects
            }

            if let states = json["distinct_states"] as? [String], !states.isEmpty {
                distinctStates = states.sorted()
            }
            if let cats = json["distinct_categories"] as? [String], !cats.isEmpty {
                distinctCategories = cats.sorted()
            }
            if let quotas = json["distinct_quotas"] as? [String], !quotas.isEmpty {
                distinctQuotas = quotas.sorted()
            }

            // Parse Colleges
            var rawList: [CollegeModel] = []
            if let safes = json["safe_colleges"] as? [[String: Any]] {
                rawList.append(contentsOf: parseCollegesArray(safes, label: "SAFE"))
            }
            if let targets = json["target_colleges"] as? [[String: Any]] {
                rawList.append(contentsOf: parseCollegesArray(targets, label: "TARGET"))
            }
            if let dreams = json["dream_colleges"] as? [[String: Any]] {
                rawList.append(contentsOf: parseCollegesArray(dreams, label: "DREAM"))
            }

            masterColleges = rawList
            applyLocalFilters()

        } catch {
            RemoteLogger.log(tag: "Predictor_Fetch_Err", message: "College fetch network error: \(error.localizedDescription)")
            errorMessage = "Network error: \(error.localizedDescription)"
        }
    }

    private func parseCollegesArray(_ array: [[String: Any]], label: String) -> [CollegeModel] {
        return array.enumerated().compactMap { index, obj in
            let inst = (obj["institute"] as? String) ?? (obj["college"] as? String) ?? ""
            guard !inst.isEmpty else { return nil }

            let course = (obj["course"] as? String) ?? ""
            let subject = (obj["subject"] as? String) ?? course
            let closingRank = (obj["closing_rank"] as? Int) ?? (Int(String(describing: obj["closing_rank"] ?? 0)) ?? 0)
            let category = (obj["category"] as? String) ?? ""
            let quota = (obj["quota"] as? String) ?? ""
            let year = (obj["year"] as? String) ?? "2026"
            let round = (obj["round"] as? String) ?? "1"
            let state = (obj["state"] as? String) ?? ""
            let council = (obj["medical_council"] as? String) ?? ""
            let feeYear = (obj["fee_per_year"] as? Double) ?? (Double(String(describing: obj["fee_per_year"] ?? 0)) ?? 0.0)
            let totalFee = (obj["total_fee"] as? Double) ?? (Double(String(describing: obj["total_fee"] ?? 0)) ?? 0.0)
            let rawStipend = (obj["average_stipend"] as? Double) ?? (Double(String(describing: obj["average_stipend"] ?? 0)) ?? 0.0)
            let bondYears = (obj["bond_years"] as? Int) ?? (Int(String(describing: obj["bond_years"] ?? 0)) ?? 0)
            let chance = (obj["chance"] as? String) ?? label
            let aiLabel = (obj["ai_label"] as? String) ?? label

            return CollegeModel(
                id: (obj["id"] as? Int) ?? index,
                institute: inst,
                course: course,
                subject: subject,
                closingRank: closingRank,
                category: category,
                quota: quota,
                year: year,
                round: round,
                state: state,
                medicalCouncil: council,
                feePerYear: feeYear,
                totalFee: totalFee,
                averageStipend: rawStipend <= 0 ? 100000.0 : rawStipend,
                bondYears: bondYears,
                chance: chance,
                aiLabel: aiLabel,
                seatCount: 1
            )
        }
    }

    // MARK: - Local Filtering & Aggregating

    private func applyLocalFilters() {
        let filtered = masterColleges.filter { matchesFilters($0) }

        // Deduplicate and group occurrences to calculate seatCount (1:1 with Android groupedColleges)
        var seatGrouped: [String: [CollegeModel]] = [:]
        for college in filtered {
            let key = "\(college.institute)|\(college.subject)|\(college.category)|\(college.quota)|\(college.state)|\(college.year)|\(college.round)|\(college.closingRank)"
            seatGrouped[key, default: []].append(college)
        }

        let aggregated = seatGrouped.values.compactMap { list -> CollegeModel? in
            guard var first = list.first else { return nil }
            first.seatCount = list.count
            return first
        }

        var s: [CollegeModel] = []
        var t: [CollegeModel] = []
        var d: [CollegeModel] = []

        for c in aggregated {
            let lbl = c.aiLabel.lowercased()
            let chance = c.chance.lowercased()
            if lbl.contains("safe") || chance.contains("high") {
                s.append(c)
            } else if lbl.contains("target") || chance.contains("med") {
                t.append(c)
            } else {
                d.append(c)
            }
        }

        safeColleges = s.sorted(by: { $0.closingRank < $1.closingRank })
        targetColleges = t.sorted(by: { $0.closingRank < $1.closingRank })
        dreamColleges = d.sorted(by: { $0.closingRank < $1.closingRank })

        safeCount = safeColleges.reduce(0) { $0 + $1.seatCount }
        targetCount = targetColleges.reduce(0) { $0 + $1.seatCount }
        dreamCount = dreamColleges.reduce(0) { $0 + $1.seatCount }
        totalResults = safeColleges.count + targetColleges.count + dreamColleges.count
    }

    private func matchesFilters(_ college: CollegeModel) -> Bool {
        // Institute Search
        if !selectedInstitute.isEmpty {
            let instLower = college.institute.lowercased()
            let searchLower = selectedInstitute.lowercased()
            if !instLower.contains(searchLower) { return false }
        }

        // Subject Filter
        if !selectedSubject.isEmpty && selectedSubject.lowercased() != "all" {
            let subLower = (college.subject.isEmpty ? college.course : college.subject).lowercased()
            let filterLower = selectedSubject.lowercased()
            if !subLower.contains(filterLower) && !filterLower.contains(subLower) { return false }
        }

        // State Filter
        if !selectedState.isEmpty && selectedState.lowercased() != "all" {
            if !college.state.lowercased().contains(selectedState.lowercased()) { return false }
        }

        // Category Filter
        if !selectedCategory.isEmpty && selectedCategory.lowercased() != "all" {
            let cCat = college.category.lowercased()
            let sCat = selectedCategory.lowercased()
            if !cCat.contains(sCat) && !sCat.contains(cCat) {
                if !((sCat == "gen" || sCat == "general") && (cCat == "open" || cCat == "opn" || cCat == "gen")) {
                    return false
                }
            }
        }

        // Quota Filter
        if !selectedQuota.isEmpty && selectedQuota.lowercased() != "all" {
            let cQuota = college.quota.lowercased()
            let sQuota = selectedQuota.lowercased()
            if !cQuota.contains(sQuota) && !sQuota.contains(cQuota) {
                if !(sQuota.contains("all india") && (cQuota.contains("aiq") || cQuota.contains("all india") || cQuota.contains("open"))) {
                    return false
                }
            }
        }

        // College Type
        if selectedCollegeType.lowercased() == "government" {
            let inst = college.institute.lowercased()
            if !inst.contains("government") && !inst.contains("govt") && !inst.contains("aiims") {
                return false
            }
        } else if selectedCollegeType.lowercased() == "private" {
            let inst = college.institute.lowercased()
            if inst.contains("government") || inst.contains("govt") || inst.contains("aiims") {
                return false
            }
        }

        // Max Fee
        if let maxFee = Double(selectedMaxFee), college.feePerYear > maxFee {
            return false
        }

        // Max Bond
        if let maxBond = Int(selectedMaxBond), college.bondYears > maxBond {
            return false
        }

        // Min Stipend
        if let minStipend = Double(selectedMinStipend), college.averageStipend < minStipend {
            return false
        }

        // Chance Preference
        if !selectedAiPreference.isEmpty && selectedAiPreference.lowercased() != "all" {
            if !college.aiLabel.lowercased().contains(selectedAiPreference.lowercased()) {
                return false
            }
        }

        return true
    }

    private func resetFilters() {
        selectedSubject = ""
        selectedState = ""
        selectedCategory = "GEN"
        selectedQuota = "All India"
        selectedCollegeType = ""
        selectedMaxFee = ""
        selectedMaxBond = ""
        selectedMinStipend = ""
        selectedAiPreference = ""
        selectedInstitute = ""
        RemoteLogger.log(tag: "Predictor_Reset_Filters", message: "All filters reset to defaults")
        applyLocalFilters()
    }

    // MARK: - Actions: Compare, PDF, Share

    private func toggleCompare(_ college: CollegeModel) {
        let impact = UIImpactFeedbackGenerator(style: .medium)
        impact.impactOccurred()

        if let index = compareList.firstIndex(where: { $0.id == college.id && $0.institute == college.institute }) {
            compareList.remove(at: index)
            RemoteLogger.log(tag: "Predictor_Compare_Remove", message: "Removed \(college.institute) from compare")
        } else {
            if compareList.count >= 3 {
                errorMessage = "You can compare up to 3 colleges at once."
                return
            }
            compareList.append(college)
            RemoteLogger.log(tag: "Predictor_Compare_Add", message: "Added \(college.institute) to compare (\(compareList.count)/3)")
            if compareList.count >= 2 {
                showingCompareModal = true
            }
        }
    }

    private func shareShortlist(customList: [CollegeModel]) {
        let listToShare = customList.prefix(5)
        guard !listToShare.isEmpty else {
            errorMessage = "No colleges to share."
            return
        }

        var text = "MediGyaan NEET-PG Counseling Shortlist (Rank #\(selectedRank)):\n\n"
        for (i, c) in listToShare.enumerated() {
            let instName = c.institute.components(separatedBy: ",").first ?? c.institute
            text += "\(i + 1). \(instName)\n"
            text += "   📘 \(c.subject) • Cutoff: #\(c.closingRank)\n"
            text += "   💰 Fee: ₹\(formatAmount(c.feePerYear))/yr • Stipend: ₹\(formatAmount(c.averageStipend))\n\n"
        }
        text += "Predicted via MediGyaan NEET PG Platform."

        shareSheetItems = [text]
    }

    private func exportCollegesToPdf() {
        let rows = (safeColleges + targetColleges + dreamColleges).prefix(120)
        guard !rows.isEmpty else {
            errorMessage = "No colleges to export."
            return
        }

        if let pdfURL = generateCounselingPDF(
            rank: selectedRank,
            tier: selectedTier,
            category: selectedCategory,
            quota: selectedQuota,
            colleges: Array(rows)
        ) {
            shareSheetItems = [pdfURL]
        } else {
            errorMessage = "Unable to generate counseling PDF."
        }
    }

    // MARK: - Helper Methods

    private func formatAiSummary(_ raw: String) -> String {
        if let data = raw.data(using: .utf8),
           let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            let summary = (obj["summary"] as? String) ?? raw
            var res = summary
            if let highlights = obj["highlights"] as? [String], !highlights.isEmpty {
                res += "\n\nHighlights:\n" + highlights.map { "• \($0)" }.joined(separator: "\n")
            }
            return res
        }
        return raw
    }

    private func tierColor(_ tier: String) -> Color {
        if tier.contains("Top") { return Color.green }
        if tier.contains("Good") { return Color.blue }
        if tier.contains("Average") { return Color.orange }
        return Color.red
    }

    private func currentFilterValue(for type: PredictorFilterType) -> String {
        switch type {
        case .subject: return selectedSubject
        case .state: return selectedState
        case .category: return selectedCategory
        case .quota: return selectedQuota
        case .type: return selectedCollegeType
        case .fee: return selectedMaxFee
        case .bond: return selectedMaxBond
        case .stipend: return selectedMinStipend
        case .chance: return selectedAiPreference
        }
    }

    private func options(for type: PredictorFilterType) -> [String] {
        switch type {
        case .subject: return ["All"] + distinctSubjects
        case .state: return ["All"] + distinctStates
        case .category: return ["All"] + distinctCategories
        case .quota: return ["All"] + distinctQuotas
        case .type: return ["All", "Government", "Private"]
        case .fee: return ["All", "100000", "200000", "300000", "500000", "1000000"]
        case .bond: return ["All", "1", "2", "3", "5"]
        case .stipend: return ["All", "25000", "50000", "75000", "100000"]
        case .chance: return ["All", "SAFE", "TARGET", "DREAM"]
        }
    }

    private func applyFilterSelection(filterType: PredictorFilterType, value: String) {
        let finalVal = value.lowercased() == "all" ? "" : value
        switch filterType {
        case .subject: selectedSubject = finalVal
        case .state: selectedState = finalVal
        case .category: selectedCategory = value.lowercased() == "all" ? "GEN" : value
        case .quota: selectedQuota = value.lowercased() == "all" ? "All India" : value
        case .type: selectedCollegeType = finalVal.lowercased()
        case .fee: selectedMaxFee = finalVal
        case .bond: selectedMaxBond = finalVal
        case .stipend: selectedMinStipend = finalVal
        case .chance: selectedAiPreference = finalVal
        }
        RemoteLogger.log(tag: "Predictor_Filter_Change", message: "Filter \(filterType) changed to \(value)")
        applyLocalFilters()
    }
}

// MARK: - Filter Types Enum

enum PredictorFilterType: String, Identifiable {
    case subject = "Subject Specialty"
    case state = "State"
    case category = "Category"
    case quota = "Quota"
    case type = "College Type"
    case fee = "Maximum Fee / Year"
    case bond = "Maximum Service Bond"
    case stipend = "Minimum Resident Stipend"
    case chance = "Admission Chance"

    var id: String { rawValue }
}

// MARK: - College Card Row View

struct CollegeCardRow: View {
    let college: CollegeModel
    let isCompared: Bool
    let onTap: () -> Void
    let onLongPress: () -> Void

    private var parsedInstituteName: (name: String, address: String) {
        let parts = college.institute.components(separatedBy: ",")
        if parts.count > 1 {
            return (parts[0].trimmingCharacters(in: .whitespaces), parts.dropFirst().joined(separator: ",").trimmingCharacters(in: .whitespaces))
        }
        return (college.institute, "")
    }

    var body: some View {
        Button(action: onTap) {
            CardContainer(padding: AppTheme.Spacing.md) {
                VStack(alignment: .leading, spacing: 6) {
                    // Header: Institute & Compare Check
                    HStack(alignment: .top) {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(parsedInstituteName.name)
                                .font(AppTheme.Font.headline)
                                .foregroundStyle(AppTheme.Palette.textPrimary)
                                .lineLimit(2)

                            if !parsedInstituteName.address.isEmpty {
                                Text("📍 \(parsedInstituteName.address)")
                                    .font(.system(size: 11))
                                    .foregroundStyle(AppTheme.Palette.textSecondary)
                                    .lineLimit(1)
                            }

                            if !college.state.isEmpty {
                                Text("🏙 \(college.state)")
                                    .font(.system(size: 11))
                                    .foregroundStyle(AppTheme.Palette.textSecondary)
                            }
                        }

                        Spacer()

                        if isCompared {
                            Label("Compared", systemImage: "checkmark.circle.fill")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundStyle(AppTheme.Palette.primary)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 3)
                                .background(Capsule().fill(AppTheme.Palette.primary.opacity(0.15)))
                        }
                    }

                    Divider()

                    // Course / Subject Line
                    HStack {
                        Text("📘 \(college.subject)")
                            .font(.system(size: 13, weight: .semibold))
                            .foregroundStyle(AppTheme.Palette.primary)
                            .lineLimit(1)

                        Spacer()

                        Text("Cutoff: #\(college.closingRank)")
                            .font(.system(size: 13, weight: .bold, design: .rounded))
                            .foregroundStyle(Color(red: 56/255, green: 189/255, blue: 248/255))
                    }

                    // Key Stats Grid Row
                    HStack(spacing: 6) {
                        // Chance Badge
                        Text(college.aiLabel.isEmpty ? college.chance : college.aiLabel)
                            .font(.system(size: 10, weight: .bold))
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(chanceBadgeBackground(college.aiLabel))
                            .foregroundStyle(.white)
                            .clipShape(Capsule())

                        // Fee Tag
                        Text("💰 ₹\(formatAmount(college.feePerYear))/yr")
                            .font(.system(size: 10, weight: .bold))
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(Color(red: 69/255, green: 26/255, blue: 3/255))
                            .foregroundStyle(Color(red: 245/255, green: 158/255, blue: 11/255))
                            .clipShape(Capsule())

                        // Stipend Tag
                        Text("🏥 ₹\(formatAmount(college.averageStipend))")
                            .font(.system(size: 10, weight: .bold))
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(Color(red: 5/255, green: 46/255, blue: 22/255))
                            .foregroundStyle(Color(red: 34/255, green: 197/255, blue: 94/255))
                            .clipShape(Capsule())

                        // Seats Count
                        if college.seatCount > 1 {
                            Text("🪑 \(college.seatCount) Seats")
                                .font(.system(size: 10, weight: .bold))
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(AppTheme.Palette.surface)
                                .foregroundStyle(AppTheme.Palette.textPrimary)
                                .clipShape(Capsule())
                        }
                    }

                    // Bottom Metadata Row: Quota, Category, Round, Bond
                    HStack(spacing: 8) {
                        Text("Quota: \(college.quota)")
                            .font(.system(size: 10, weight: .medium))
                            .foregroundStyle(AppTheme.Palette.textSecondary)

                        Text("•")
                            .foregroundStyle(AppTheme.Palette.textSecondary)

                        Text("Cat: \(college.category)")
                            .font(.system(size: 10, weight: .medium))
                            .foregroundStyle(AppTheme.Palette.textSecondary)

                        Text("•")
                            .foregroundStyle(AppTheme.Palette.textSecondary)

                        Text("Bond: \(college.bondYears == 0 ? "No Bond" : "\(college.bondYears)y")")
                            .font(.system(size: 10, weight: .medium))
                            .foregroundStyle(college.bondYears == 0 ? Color.green : AppTheme.Palette.textSecondary)

                        Spacer()

                        Image(systemName: "chevron.right")
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                    }
                    .padding(.top, 2)
                }
            }
        }
        .buttonStyle(.plain)
        .simultaneousGesture(
            LongPressGesture(minimumDuration: 0.5)
                .onEnded { _ in
                    onLongPress()
                }
        )
    }

    private func chanceBadgeBackground(_ label: String) -> some View {
        let lower = label.lowercased()
        if lower.contains("safe") {
            return LinearGradient(
                colors: [Color(red: 5/255, green: 150/255, blue: 105/255), Color(red: 6/255, green: 95/255, blue: 70/255)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        } else if lower.contains("target") {
            return LinearGradient(
                colors: [Color(red: 217/255, green: 119/255, blue: 6/255), Color(red: 146/255, green: 64/255, blue: 14/255)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        } else {
            return LinearGradient(
                colors: [Color(red: 225/255, green: 29/255, blue: 72/255), Color(red: 136/255, green: 19/255, blue: 55/255)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        }
    }
}

// MARK: - Custom Rank Dialog Sheet

struct CustomRankDialog: View {
    @State private var rankSliderValue: Double
    @State private var rankText: String
    @State private var liveTier: String

    let originalRank: String
    let onApply: (String, String) -> Void
    let onResetOriginal: () -> Void
    @Environment(\.dismiss) private var dismiss

    init(currentRank: String, originalRank: String, onApply: @escaping (String, String) -> Void, onResetOriginal: @escaping () -> Void) {
        let initialVal = Double(currentRank) ?? 50000.0
        _rankSliderValue = State(initialValue: initialVal)
        _rankText = State(initialValue: currentRank)
        _liveTier = State(initialValue: recalcTierForRank(Int(initialVal)))
        self.originalRank = originalRank
        self.onApply = onApply
        self.onResetOriginal = onResetOriginal
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: AppTheme.Spacing.lg) {
                VStack(spacing: 6) {
                    Text("Enter or Slide Custom Rank")
                        .font(AppTheme.Font.title)
                        .foregroundStyle(AppTheme.Palette.textPrimary)

                    Text("Slide for real-time tier calculation, Apply to sync colleges.")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }
                .padding(.top)

                // Live Preview Card
                CardContainer {
                    VStack(spacing: AppTheme.Spacing.sm) {
                        Text("Predicted Rank: #\(Int(rankSliderValue))")
                            .font(.system(size: 32, weight: .bold, design: .rounded))
                            .foregroundStyle(AppTheme.Palette.primary)

                        Text("Tier: \(liveTier)")
                            .font(AppTheme.Font.headline)
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                    }
                    .frame(maxWidth: .infinity)
                }

                // Interactive Slider
                VStack(alignment: .leading, spacing: 4) {
                    Slider(
                        value: $rankSliderValue,
                        in: 1000...200000,
                        step: 500
                    ) {
                        Text("Rank")
                    } minimumValueLabel: {
                        Text("1k").font(.caption).foregroundStyle(AppTheme.Palette.textSecondary)
                    } maximumValueLabel: {
                        Text("200k").font(.caption).foregroundStyle(AppTheme.Palette.textSecondary)
                    }
                    .tint(AppTheme.Palette.primary)
                    .onChange(of: rankSliderValue) { newVal in
                        let r = Int(newVal)
                        rankText = String(r)
                        liveTier = recalcTierForRank(r)
                    }
                }

                // Numeric Input Field
                HStack(spacing: 12) {
                    Text("Manual Input:")
                        .font(AppTheme.Font.callout)
                        .foregroundStyle(AppTheme.Palette.textSecondary)

                    TextField("Rank", text: $rankText)
                        .keyboardType(.numberPad)
                        .textFieldStyle(.roundedBorder)
                        .onChange(of: rankText) { newVal in
                            if let num = Double(newVal), num >= 1000 && num <= 200000 {
                                rankSliderValue = num
                                liveTier = recalcTierForRank(Int(num))
                            }
                        }
                }

                // Quick Presets
                HStack(spacing: 8) {
                    presetButton(5000)
                    presetButton(15000)
                    presetButton(30000)
                    presetButton(50000)
                    presetButton(75000)
                }

                Spacer()

                // Actions: Apply & Original
                HStack(spacing: AppTheme.Spacing.md) {
                    Button("Reset Original (#\(originalRank))") {
                        onResetOriginal()
                        dismiss()
                    }
                    .font(AppTheme.Font.callout.weight(.medium))
                    .foregroundStyle(AppTheme.Palette.textSecondary)

                    Spacer()

                    Button {
                        let finalRank = String(Int(rankSliderValue))
                        onApply(finalRank, liveTier)
                        dismiss()
                    } label: {
                        Text("Apply Rank")
                            .font(AppTheme.Font.headline)
                            .frame(minWidth: 120)
                            .padding(.vertical, 12)
                            .background(
                                RoundedRectangle(cornerRadius: AppTheme.Radius.md)
                                    .fill(AppTheme.Palette.primary)
                            )
                            .foregroundStyle(.white)
                    }
                }
            }
            .padding(AppTheme.Spacing.lg)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
            }
        }
    }

    private func presetButton(_ rank: Int) -> some View {
        Button("\(rank >= 1000 ? "\(rank/1000)k" : "\(rank)")") {
            rankSliderValue = Double(rank)
            rankText = String(rank)
            liveTier = recalcTierForRank(rank)
        }
        .font(.system(size: 11, weight: .bold))
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(
            Capsule().fill(AppTheme.Palette.surface)
        )
        .foregroundStyle(AppTheme.Palette.primary)
    }
}

// MARK: - Filter Selection Sheet View

struct FilterSelectionSheet: View {
    let filterType: PredictorFilterType
    let currentValue: String
    let options: [String]
    let onSelect: (String) -> Void
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                ForEach(options, id: \.self) { option in
                    Button {
                        onSelect(option)
                        dismiss()
                    } label: {
                        HStack {
                            Text(displayLabel(for: option))
                                .font(AppTheme.Font.body)
                                .foregroundStyle(AppTheme.Palette.textPrimary)

                            Spacer()

                            if option.lowercased() == currentValue.lowercased() || (option == "All" && currentValue.isEmpty) {
                                Image(systemName: "checkmark")
                                    .font(.system(size: 14, weight: .bold))
                                    .foregroundStyle(AppTheme.Palette.primary)
                            }
                        }
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                }
            }
            .navigationTitle(filterType.rawValue)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
            }
        }
    }

    private func displayLabel(for option: String) -> String {
        switch filterType {
        case .fee:
            return option == "All" ? "All Fees" : "<= ₹\(option) / year"
        case .bond:
            return option == "All" ? "All Bonds" : "<= \(option) Year Bond"
        case .stipend:
            return option == "All" ? "All Stipends" : ">= ₹\(option) / month"
        default:
            return option
        }
    }
}

// MARK: - Compare Colleges Sheet View

struct CompareCollegesSheet: View {
    let colleges: [CollegeModel]
    let onRemove: (CollegeModel) -> Void
    let onClearAll: () -> Void
    let onShareComparison: () -> Void
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: AppTheme.Spacing.md) {
                    HStack {
                        Text("Comparing \(colleges.count) Colleges")
                            .font(AppTheme.Font.headline)
                            .foregroundStyle(AppTheme.Palette.textPrimary)

                        Spacer()

                        Button("Clear All", role: .destructive) {
                            onClearAll()
                        }
                        .font(AppTheme.Font.caption.weight(.semibold))
                    }
                    .padding(.horizontal)

                    ForEach(colleges) { college in
                        CardContainer {
                            VStack(alignment: .leading, spacing: 8) {
                                HStack {
                                    Text(college.institute)
                                        .font(AppTheme.Font.callout.weight(.bold))
                                        .lineLimit(2)
                                    Spacer()
                                    Button {
                                        onRemove(college)
                                    } label: {
                                        Image(systemName: "trash")
                                            .font(.system(size: 13))
                                            .foregroundStyle(Color.red)
                                    }
                                }

                                Divider()

                                HStack(spacing: 12) {
                                    StatTile(value: "#\(college.closingRank)", label: "Cutoff", systemImage: "target", tint: Color.blue)
                                    StatTile(value: "₹\(formatAmount(college.feePerYear))", label: "Fee/yr", systemImage: "indianrupeesign", tint: Color.orange)
                                    StatTile(value: "₹\(formatAmount(college.averageStipend))", label: "Stipend", systemImage: "cross.case.fill", tint: Color.green)
                                    StatTile(value: "\(college.bondYears)y", label: "Bond", systemImage: "doc.text.fill", tint: Color.purple)
                                }

                                Text("Course: \(college.subject) (\(college.category)) • \(college.state)")
                                    .font(AppTheme.Font.caption)
                                    .foregroundStyle(AppTheme.Palette.textSecondary)
                            }
                        }
                        .padding(.horizontal)
                    }

                    Button {
                        onShareComparison()
                    } label: {
                        Label("Share Comparison", systemImage: "square.and.arrow.up")
                            .font(AppTheme.Font.headline)
                            .frame(maxWidth: .infinity)
                            .frame(height: 48)
                            .background(
                                RoundedRectangle(cornerRadius: AppTheme.Radius.md)
                                    .fill(AppTheme.Palette.primary)
                            )
                            .foregroundStyle(.white)
                            .padding(.horizontal)
                    }
                }
                .padding(.vertical)
            }
            .navigationTitle("College Comparison")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}

// MARK: - Predictor Pass Paywall Sheet View

struct PredictorPassPaywallView: View {
    let onUnlock: () -> Void
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            VStack(spacing: AppTheme.Spacing.lg) {
                Image(systemName: "lock.shield.fill")
                    .font(.system(size: 54))
                    .foregroundStyle(AppTheme.Palette.primary)
                    .padding(.top, 24)

                VStack(spacing: 8) {
                    Text("Unlock NEET-PG Predictor Pass")
                        .font(AppTheme.Font.titleBold)
                        .foregroundStyle(AppTheme.Palette.textPrimary)

                    Text("Access verified closing rank cutoffs, safe/target/dream seat chances, and resident stipends across all 280k seats.")
                        .font(AppTheme.Font.body)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 24)
                }

                VStack(alignment: .leading, spacing: 12) {
                    featureBenefitRow(icon: "sparkles", text: "AI seat prediction for your percentile")
                    featureBenefitRow(icon: "chart.bar.doc.horizontal", text: "2026 expected cutoffs & seat categories")
                    featureBenefitRow(icon: "banknote", text: "Verified stipend breakdowns & bond policies")
                    featureBenefitRow(icon: "doc.richtext", text: "Unlimited PDF counseling exports")
                }
                .padding(.horizontal, 24)

                Spacer()

                Button {
                    onUnlock()
                } label: {
                    Text("Unlock Predictor Pass — ₹500")
                        .font(AppTheme.Font.headlineBold)
                        .frame(maxWidth: .infinity)
                        .frame(height: 52)
                        .background(
                            RoundedRectangle(cornerRadius: AppTheme.Radius.md)
                                .fill(AppTheme.Palette.primary)
                        )
                        .foregroundStyle(.white)
                }
                .padding(.horizontal, 24)
                .padding(.bottom, 24)
            }
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Dismiss") { dismiss() }
                }
            }
        }
    }

    private func featureBenefitRow(icon: String, text: String) -> some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 16, weight: .bold))
                .foregroundStyle(AppTheme.Palette.primary)
                .frame(width: 24)
            Text(text)
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Palette.textPrimary)
        }
    }
}

// MARK: - Reusable Filter Chip

struct PredictorFilterChip: View {
    let title: String
    let isActive: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 4) {
                Text(title)
                    .font(.system(size: 12, weight: .bold))
                Image(systemName: "chevron.down")
                    .font(.system(size: 9, weight: .semibold))
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(
                Capsule()
                    .fill(isActive ? AppTheme.Palette.primary : AppTheme.Palette.surface)
            )
            .foregroundStyle(isActive ? Color.white : AppTheme.Palette.textPrimary)
            .overlay(
                Capsule()
                    .stroke(isActive ? AppTheme.Palette.primary : AppTheme.Palette.border, lineWidth: 1)
            )
        }
    }
}

// MARK: - Supporting Models & Helpers

struct CollegeModel: Identifiable, Hashable {
    let id: Int
    let institute: String
    let course: String
    let subject: String
    let closingRank: Int
    let category: String
    let quota: String
    let year: String
    let round: String
    let state: String
    let medicalCouncil: String
    let feePerYear: Double
    let totalFee: Double
    let averageStipend: Double
    let bondYears: Int
    let chance: String
    let aiLabel: String
    var seatCount: Int = 1
}

func formatAmount(_ amount: Double) -> String {
    if amount >= 100_000 {
        return "\(Int(round(amount / 100_000)))L"
    } else {
        return "\(Int(round(amount)))"
    }
}

func recalcTierForRank(_ rank: Int) -> String {
    switch rank {
    case ...0: return "📘 Average"
    case 1...15_000: return "🏆 Top"
    case 15_001...40_000: return "🌟 Good"
    case 40_001...80_000: return "📘 Average"
    default: return "🔧 Needs Work"
    }
}

// MARK: - PDF Counseling Report Generator

func generateCounselingPDF(
    rank: String,
    tier: String,
    category: String,
    quota: String,
    colleges: [CollegeModel]
) -> URL? {
    let pdfMetaData = [
        kCGPDFContextCreator: "MediGyaan NEET PG Predictor",
        kCGPDFContextAuthor: "MediGyaan Platform",
        kCGPDFContextTitle: "NEET PG Counseling Report - Rank \(rank)"
    ]
    let format = UIGraphicsPDFRendererFormat()
    format.documentInfo = pdfMetaData as [String: Any]

    let pageWidth: CGFloat = 595.2 // A4 standard width
    let pageHeight: CGFloat = 841.8 // A4 standard height
    let pageRect = CGRect(x: 0, y: 0, width: pageWidth, height: pageHeight)
    let renderer = UIGraphicsPDFRenderer(bounds: pageRect, format: format)

    let tempURL = FileManager.default.temporaryDirectory.appendingPathComponent("MediGyaan_Colleges_Rank\(rank).pdf")

    do {
        try renderer.writePDF(to: tempURL) { context in
            var currentY: CGFloat = 40
            context.beginPage()

            let titleFont = UIFont.boldSystemFont(ofSize: 20)
            let subFont = UIFont.systemFont(ofSize: 12)
            let headerFont = UIFont.boldSystemFont(ofSize: 11)
            let bodyFont = UIFont.systemFont(ofSize: 10)

            // Header Section
            let title = "MediGyaan Counseling Report"
            title.draw(at: CGPoint(x: 40, y: currentY), withAttributes: [
                .font: titleFont,
                .foregroundColor: UIColor(red: 15/255, green: 23/255, blue: 42/255, alpha: 1)
            ])
            currentY += 26

            let subtitle = "Expected Rank: #\(rank) • Tier: \(tier) • Category: \(category) • Quota: \(quota)"
            subtitle.draw(at: CGPoint(x: 40, y: currentY), withAttributes: [
                .font: subFont,
                .foregroundColor: UIColor(red: 51/255, green: 65/255, blue: 85/255, alpha: 1)
            ])
            currentY += 24

            let summaryText = "Available Recommended Colleges: \(colleges.count)"
            summaryText.draw(at: CGPoint(x: 40, y: currentY), withAttributes: [
                .font: subFont,
                .foregroundColor: UIColor(red: 37/255, green: 99/255, blue: 235/255, alpha: 1)
            ])
            currentY += 28

            // Separator Rule
            let path = UIBezierPath()
            path.move(to: CGPoint(x: 40, y: currentY))
            path.addLine(to: CGPoint(x: pageWidth - 40, y: currentY))
            UIColor.lightGray.setStroke()
            path.stroke()
            currentY += 12

            for college in colleges {
                if currentY > pageHeight - 50 {
                    context.beginPage()
                    currentY = 40
                }

                let instituteLine = "\(college.institute.prefix(45)) | \(college.subject.prefix(20))"
                instituteLine.draw(at: CGPoint(x: 40, y: currentY), withAttributes: [
                    .font: headerFont,
                    .foregroundColor: UIColor.black
                ])
                currentY += 14

                let detailLine = "Cutoff: #\(college.closingRank) | Fee: ₹\(formatAmount(college.feePerYear))/yr | Stipend: ₹\(formatAmount(college.averageStipend)) | Bond: \(college.bondYears)y | [\(college.aiLabel)]"
                detailLine.draw(at: CGPoint(x: 40, y: currentY), withAttributes: [
                    .font: bodyFont,
                    .foregroundColor: UIColor.darkGray
                ])
                currentY += 18
            }
        }
        return tempURL
    } catch {
        return nil
    }
}

// MARK: - College Detail View (Compatibility with both College & CollegeModel)

struct CollegeDetailView: View {
    let collegeName: String
    let collegeState: String
    let collegeSeats: Int
    let collegeOpeningRank: Int
    let collegeClosingRank: Int
    let collegeFees: String
    let collegeWebsite: URL?

    @State private var detailData: CollegeDetailData?
    @State private var isLoading = false
    @State private var showAllRows = false

    init(college: College) {
        self.collegeName = college.name.isEmpty ? "College" : college.name
        self.collegeState = college.state
        self.collegeSeats = college.seats
        self.collegeOpeningRank = college.openingRank
        self.collegeClosingRank = college.closingRank
        self.collegeFees = college.fees.isEmpty ? "—" : college.fees
        self.collegeWebsite = college.website
    }

    init(collegeModel: CollegeModel) {
        self.collegeName = collegeModel.institute
        self.collegeState = collegeModel.state
        self.collegeSeats = collegeModel.seatCount
        self.collegeOpeningRank = collegeModel.closingRank
        self.collegeClosingRank = collegeModel.closingRank
        self.collegeFees = formatAmount(collegeModel.feePerYear)
        self.collegeWebsite = nil
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                // Header Card
                CardContainer {
                    VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                        Text(collegeName)
                            .font(AppTheme.Font.title)

                        if !collegeState.isEmpty {
                            Label(collegeState, systemImage: "mappin.and.ellipse")
                                .font(AppTheme.Font.callout)
                                .foregroundStyle(AppTheme.Palette.textSecondary)
                        }

                        if let address = detailData?.address, !address.isEmpty {
                            Text(address)
                                .font(AppTheme.Font.caption)
                                .foregroundStyle(AppTheme.Palette.textMuted)
                        }
                    }
                }

                // Grid Quick Stats
                LazyVGrid(
                    columns: Array(repeating: GridItem(.flexible(), spacing: AppTheme.Spacing.sm), count: 2),
                    spacing: AppTheme.Spacing.sm
                ) {
                    StatTile(value: "\(collegeSeats)", label: "Seats", systemImage: "chair.fill", tint: AppTheme.Palette.info)
                    StatTile(value: "\(collegeOpeningRank)", label: "Opening rank", systemImage: "arrow.up", tint: AppTheme.Palette.success)
                    StatTile(value: "\(collegeClosingRank)", label: "Closing rank", systemImage: "arrow.down", tint: AppTheme.Palette.warning)
                    StatTile(value: collegeFees, label: "Fees", systemImage: "indianrupeesign", tint: AppTheme.Palette.accent)
                }

                // Deep Scraped Details Card
                if isLoading {
                    CardContainer {
                        HStack(spacing: AppTheme.Spacing.md) {
                            ProgressView()
                            Text("Loading college profile & fee details...")
                                .font(AppTheme.Font.subheadline)
                                .foregroundStyle(AppTheme.Palette.textSecondary)
                        }
                        .padding(.vertical, AppTheme.Spacing.sm)
                    }
                } else if let detail = detailData, !detail.dataInReview {
                    // Fee Structure Section
                    if !detail.annualFee.isEmpty || !detail.nriFee.isEmpty {
                        CardContainer {
                            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                                Label("Fee Structure", systemImage: "banknote.fill")
                                    .font(AppTheme.Font.headline)
                                    .foregroundStyle(Color.blue)

                                if !detail.annualFee.isEmpty {
                                    HStack {
                                        Text("Annual Fee:")
                                            .font(AppTheme.Font.callout)
                                            .foregroundStyle(AppTheme.Palette.textSecondary)
                                        Spacer()
                                        Text(detail.annualFee)
                                            .font(AppTheme.Font.callout.weight(.semibold))
                                    }
                                }

                                if !detail.nriFee.isEmpty {
                                    HStack {
                                        Text("NRI Fee:")
                                            .font(AppTheme.Font.callout)
                                            .foregroundStyle(AppTheme.Palette.textSecondary)
                                        Spacer()
                                        Text(detail.nriFee)
                                            .font(AppTheme.Font.callout.weight(.semibold))
                                    }
                                }
                            }
                        }
                    }

                    // Stipend Breakdown Section
                    if !detail.stipend1.isEmpty || !detail.stipend2.isEmpty || !detail.stipend3.isEmpty {
                        CardContainer {
                            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                                Label("Resident Stipend", systemImage: "cross.case.fill")
                                    .font(AppTheme.Font.headline)
                                    .foregroundStyle(Color.green)

                                if !detail.stipend1.isEmpty {
                                    HStack {
                                        Text("1st Year:")
                                            .font(AppTheme.Font.callout)
                                        Spacer()
                                        Text(detail.stipend1)
                                            .font(AppTheme.Font.callout.weight(.semibold))
                                    }
                                }
                                if !detail.stipend2.isEmpty {
                                    HStack {
                                        Text("2nd Year:")
                                            .font(AppTheme.Font.callout)
                                        Spacer()
                                        Text(detail.stipend2)
                                            .font(AppTheme.Font.callout.weight(.semibold))
                                    }
                                }
                                if !detail.stipend3.isEmpty {
                                    HStack {
                                        Text("3rd Year:")
                                            .font(AppTheme.Font.callout)
                                        Spacer()
                                        Text(detail.stipend3)
                                            .font(AppTheme.Font.callout.weight(.semibold))
                                    }
                                }
                            }
                        }
                    }

                    // Officials Section
                    if !detail.dean.isEmpty || !detail.nodalOfficer.isEmpty {
                        CardContainer {
                            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                                Label("Administration", systemImage: "person.crop.circle.fill")
                                    .font(AppTheme.Font.headline)
                                    .foregroundStyle(Color.orange)

                                if !detail.dean.isEmpty {
                                    Text("Dean / Principal: \(detail.dean)")
                                        .font(AppTheme.Font.callout)
                                }
                                if !detail.nodalOfficer.isEmpty {
                                    Text("Nodal Officer: \(detail.nodalOfficer)")
                                        .font(AppTheme.Font.callout)
                                }
                            }
                        }
                    }

                    // Toggle Extra Details
                    if !detail.allFields.isEmpty {
                        Button {
                            withAnimation { showAllRows.toggle() }
                        } label: {
                            HStack {
                                Text(showAllRows ? "Hide Full Parameters" : "View Full Parameters")
                                    .font(AppTheme.Font.subheadline.weight(.semibold))
                                Image(systemName: showAllRows ? "chevron.up" : "chevron.down")
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, AppTheme.Spacing.sm)
                        }

                        if showAllRows {
                            CardContainer {
                                VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
                                    ForEach(detail.allFields.sorted(by: { $0.key < $1.key }), id: \.key) { k, v in
                                        HStack {
                                            Text(k)
                                                .font(AppTheme.Font.caption)
                                                .foregroundStyle(AppTheme.Palette.textSecondary)
                                            Spacer()
                                            Text(v)
                                                .font(AppTheme.Font.caption.weight(.medium))
                                        }
                                        Divider()
                                    }
                                }
                            }
                        }
                    }
                }

                // Official website link
                if let urlString = detailData?.website.isEmpty == false ? detailData?.website : collegeWebsite?.absoluteString,
                   let website = URL(string: urlString) {
                    Link(destination: website) {
                        Label("Visit Official Portal", systemImage: "safari.fill")
                            .font(AppTheme.Font.callout.weight(.semibold))
                            .frame(maxWidth: .infinity)
                            .frame(height: 46)
                            .background(
                                RoundedRectangle(cornerRadius: AppTheme.Radius.md)
                                    .stroke(AppTheme.Palette.primary.opacity(0.5), lineWidth: 1)
                            )
                            .foregroundStyle(AppTheme.Palette.primary)
                    }
                }
            }
            .padding(AppTheme.Spacing.md)
        }
        .screenBackground()
        .navigationTitle("College Details")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            isLoading = true
            detailData = await CollegeHtmlRepository.shared.loadCollege(collegeName: collegeName)
            isLoading = false
        }
    }
}

#Preview {
    NavigationStack {
        PredictorView()
            .environmentObject(SessionStore())
            .environment(\.api, .live)
    }
}
