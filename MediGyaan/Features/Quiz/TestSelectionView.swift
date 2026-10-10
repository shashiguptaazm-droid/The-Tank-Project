import SwiftUI

/// Test-series category picker and the fifty-mock grid behind it.
///
/// Ports Android `TestSelectionActivty.kt` (note the misspelling — it is the
/// real class name, registered as `TestSelectionActivity` in the manifest) and
/// its layout `res/layout/activity_test_selection.xml`.
///
/// The Kotlin activity is a two-pane, single-activity screen: `onCreate` binds
/// `subjectLayout` / `testSeriesGrid` / `headerTitle`, `setupCategoryClicks()`
/// attaches one listener per `MaterialCardView`, and the panes swap by toggling
/// `View.VISIBLE` / `View.GONE`. Back is intercepted by `onBackPressed()`,
/// which calls `handleBack()` — return to the category list when the grid is
/// open, otherwise `finish()`.
///
/// The fifty rows themselves are **not** drawn here. They are delegated whole to
/// ``TestGridSheet``, which is the faithful port of `TestGridAdapter.kt` and
/// `res/layout/item_test_card.xml` (white 12dp card, "Standard Pattern"
/// subtitle, and the hard-cornered "Attempted" / "Not Attempted" badge). The
/// completed-test badges come from `SharedPreferences("COMPLETED_TESTS")`
/// keys `id_<n>`, mirrored on iOS by the `completed_tests_set` store that
/// ``TestActivityView`` writes.
///
/// `openSoloMode` / `openChallengeMode` build a `Quiz` and present
/// ``TestActivityView`` instead of starting the two Android intents; see the
/// per-method notes for what that changes.
struct TestSelectionView: View {

    // MARK: - Category table

    /// Ports the `categories` map in `TestSelectionActivty.setupCategoryClicks()`.
    ///
    /// Android declares exactly two entries — `cardNeetPg` and `cardNeetUg`.
    /// Earlier drafts of this port invented FMGE and USMLE rows that have no
    /// `R.id.*` counterpart, so they are gone here.
    enum ExamCategory: String, CaseIterable, Identifiable {

        /// `Triple("NEET PG", 1, "NEET_PG")` bound to `R.id.cardNeetPg`.
        case neetPg = "NEET PG"

        /// `Triple("NEET UG", 100, "NEET_UG")` bound to `R.id.cardNeetUg`.
        case neetUg = "NEET UG"

        var id: String { rawValue }

        /// `data.second` — `loadTestGrid(subject, startId)`'s base id. Row
        /// `position` therefore resolves to `startId + position`.
        var startId: Int {
            switch self {
            case .neetPg: return 1
            case .neetUg: return 100
            }
        }

        /// `data.third` — assigned to the activity's `quizType` field and passed
        /// on as the `QUIZ_TYPE` intent extra in `openSoloMode`.
        var quizType: String {
            switch self {
            case .neetPg: return "NEET_PG"
            case .neetUg: return "NEET_UG"
            }
        }

        /// `@drawable/bg_neet_pg_landscape` / `bg_neet_ug_landscape` — the
        /// `centerCrop` `ImageView` behind each category card.
        var backdrop: AndroidAsset {
            switch self {
            case .neetPg: return .bg_neet_pg_landscape
            case .neetUg: return .bg_neet_ug_landscape
            }
        }
    }

    /// Ports the `subject` / `uniqueId` pair `showModeDialog()` builds its
    /// `"$subject • Test $uniqueId"` title from, carried through
    /// `onItemClickListener`'s `finalUniqueId = startId + position`.
    struct ModeTarget: Identifiable {

        /// `showModeDialog(subject: String, uniqueId: Int)`.
        let subject: String

        /// The already-offset `finalUniqueId`, not the 0-based `position`.
        let uniqueId: Int

        var id: Int { uniqueId }
    }

    // MARK: - Android string literals

    /// `android:text="Test Series"` — the `headerTitle` default declared in
    /// `activity_test_selection.xml`; Kotlin never overwrites it before the
    /// first category tap.
    static let defaultHeaderTitle = "Test Series"

    /// `headerTitle.text = "Select Category"` in `handleBack()`.
    static let selectCategoryTitle = "Select Category"

    /// `android:text="Pick a category"` on `R.id.headerSubtitle`. Kotlin never
    /// reassigns it, so it stays constant for the life of the screen.
    static let headerSubtitle = "Pick a category"

    /// `Toast.makeText(this, "Loading tests...", Toast.LENGTH_SHORT)`.
    static let loadingTestsToast = "Loading tests..."

    /// `arrayOf("Practice Solo", "Challenge Friend")` in `showModeDialog()`.
    static let soloOptionTitle = "Practice Solo"

    /// The second `AlertDialog` row.
    static let challengeOptionTitle = "Challenge Friend"

    // MARK: - Environment

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @Environment(\.dismiss) private var dismiss

    // MARK: - State

    /// `subjectLayout.visibility = View.GONE` / `testGrid.visibility =
    /// View.VISIBLE`. `nil` means the category pane is on screen.
    @State private var selectedCategory: ExamCategory?

    /// Distinguishes the two `headerTitle` strings the Kotlin shows while
    /// `selectedCategory == nil`: the XML default before any tap, and
    /// `"Select Category"` once `handleBack()` has fired.
    @State private var hasReturnedToCategories = false

    /// `quizType` — assigned in the category click listener and forwarded as
    /// the `QUIZ_TYPE` extra.
    @State private var quizType: String = ExamCategory.neetPg.quizType

    /// `showModeDialog()`'s pending `(subject, uniqueId)`.
    @State private var modeTarget: ModeTarget?

    /// `startActivity(SinglePlayerTestModeActivity)` / `startActivity(
    /// TopicChallengeSelectionActivity)`, as a presented quiz.
    @State private var testToLaunch: Quiz?

    /// Which branch of `showModeDialog()` was taken.
    @State private var isLaunchingChallenge = false

    /// The transient stand-in for Android's `Toast`.
    @State private var toastMessage: String?

    /// Mirror of `SharedPreferences("COMPLETED_TESTS")`; the keys Android reads
    /// as `id_<n>` are stored here comma-separated, which is the format
    /// ``TestActivityView`` writes on submit.
    @AppStorage("completed_tests_set") private var completedTestsData: String = ""

    // MARK: - Body

    var body: some View {
        VStack(spacing: 0) {
            header
            if let category = selectedCategory {
                TestGridSheet(
                    subject: category.rawValue,
                    startId: category.startId,
                    completedTestIds: visibleCompletedIds(for: category),
                    onSelect: { position in
                        self.showModeDialog(category: category, position: position)
                    }
                )
                .id(gridIdentity)
            } else {
                categoryPane
            }
        }
        .screenBackground()
        .overlay(alignment: .top) { toastLayer }
        .confirmationDialog(
            modeDialogTitle,
            isPresented: modeDialogPresented,
            titleVisibility: .visible
        ) {
            Button(TestSelectionView.soloOptionTitle) {
                if let target = modeTarget { self.openSoloMode(target) }
            }
            Button(TestSelectionView.challengeOptionTitle) {
                if let target = modeTarget { self.openChallengeMode(target) }
            }
            Button("Cancel", role: .cancel) {}
        }
        .fullScreenCover(item: $testToLaunch) { quiz in
            TestActivityView(
                quiz: quiz,
                isChallenge: isLaunchingChallenge,
                opponentName: "Dr. Arena Challenger"
            ) {
                testToLaunch = nil
            }
        }
        .toolbar(.hidden, for: .navigationBar)
    }

    // MARK: - Header

    /// Ports the fixed header `LinearLayout` of `activity_test_selection.xml`:
    /// 117dp tall, `?attr/colorSurface`, 4dp elevation, 16dp padding, a 32dp
    /// leading icon and the `headerTitle` / `headerSubtitle` stack.
    ///
    /// The leading slot is Android's `@drawable/ic_menu` drawer handle while
    /// the category pane is up and a back chevron while the grid is up. iOS
    /// owns the drawer at the host level, so the button runs `handleBack()`
    /// in both states — the same predicate `onBackPressed()` uses.
    private var header: some View {
        HStack(spacing: AppTheme.Spacing.lg) {
            Button(action: handleBack) {
                if selectedCategory == nil {
                    AndroidAsset.ic_menu.image
                        .resizable()
                        .renderingMode(.template)
                        .aspectRatio(contentMode: .fit)
                } else {
                    Image(systemName: "chevron.left")
                        .resizable()
                        .renderingMode(.template)
                        .aspectRatio(contentMode: .fit)
                }
            }
            .foregroundStyle(AppTheme.Palette.textPrimary)
            .frame(
                width: AppTheme.Spacing.headerIconSize,
                height: AppTheme.Spacing.headerIconSize
            )

            VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
                Text(headerTitle)
                    .font(AppTheme.Font.title2)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                Text(TestSelectionView.headerSubtitle)
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Palette.textPrimary.opacity(0.7))
            }

            Spacer(minLength: 0)
        }
        .padding(AppTheme.Spacing.lg)
        .frame(height: AppTheme.Spacing.headerHeight)
        .background(AppTheme.Palette.surface)
        .shadow(color: .black.opacity(0.06), radius: AppTheme.Elevation.androidHeader, y: 1)
    }

    /// `headerTitle` as Kotlin mutates it: the XML default, then the chosen
    /// subject inside `loadTestGrid()`, then `"Select Category"` on back.
    private var headerTitle: String {
        if let category = selectedCategory { return category.rawValue }
        return hasReturnedToCategories
            ? TestSelectionView.selectCategoryTitle
            : TestSelectionView.defaultHeaderTitle
    }

    // MARK: - Category pane

    /// `R.id.subjectLayout` — the `LinearLayout` holding one
    /// `MaterialCardView` per entry of the `categories` map, inside the
    /// layout's `ScrollView` with its 16dp padding.
    private var categoryPane: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.lg) {
                ForEach(ExamCategory.allCases) { category in
                    categoryCard(category)
                }
            }
            .padding(AppTheme.Spacing.lg)
        }
    }

    /// One `R.id.cardNeetPg` / `R.id.cardNeetUg`: a 140dp MaterialCardView with
    /// 12dp corners and 3dp elevation, holding a `centerCrop` landscape
    /// `ImageView`, the `#33000000` scrim laid over it, and the category label
    /// centred at 20sp bold white.
    private func categoryCard(_ category: ExamCategory) -> some View {
        Button {
            loadTestGrid(category)
        } label: {
            ZStack {
                category.backdrop.image
                    .resizable()
                    .aspectRatio(contentMode: .fill)
                TestSelectionAndroidPalette.cardScrim
                Text(category.rawValue)
                    .font(AppTheme.Font.title2)
                    .foregroundStyle(TestSelectionAndroidPalette.label)
            }
            .frame(maxWidth: .infinity)
            .frame(height: AppTheme.Spacing.categoryCardHeight)
            .clipShape(
                RoundedRectangle(
                    cornerRadius: AppTheme.Radius.androidMedium,
                    style: .continuous
                )
            )
            .shadow(
                color: .black.opacity(0.06),
                radius: AppTheme.Elevation.dashboardCard,
                y: 1
            )
        }
        .buttonStyle(.plain)
        .accessibilityLabel(category.rawValue)
    }

    // MARK: - Toast

    /// Android's `Toast.LENGTH_SHORT` is 2 s with no dismissal gesture, so the
    /// banner is driven by `.task(id:)` rather than a tap target.
    @ViewBuilder
    private var toastLayer: some View {
        if let toastMessage {
            Text(toastMessage)
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Palette.textPrimary)
                .padding(.horizontal, AppTheme.Spacing.lg)
                .padding(.vertical, AppTheme.Spacing.sm)
                .background(
                    RoundedRectangle(
                        cornerRadius: AppTheme.Radius.androidMedium,
                        style: .continuous
                    )
                    .fill(AppTheme.Palette.cardBackground)
                )
                .shadow(
                    color: .black.opacity(0.06),
                    radius: AppTheme.Elevation.dashboardCard,
                    y: 1
                )
                .padding(.top, AppTheme.Spacing.lg)
                .transition(.move(edge: .top).combined(with: .opacity))
                .task(id: toastMessage) {
                    try? await Task.sleep(nanoseconds: TestSelectionTiming.toastDuration)
                    withAnimation { self.toastMessage = nil }
                }
        }
    }

    // MARK: - Mode dialog

    /// `AlertDialog.Builder(this).setTitle("$subject • Test $uniqueId")`.
    private var modeDialogTitle: String {
        guard let target = modeTarget else { return TestSelectionView.defaultHeaderTitle }
        return "\(target.subject) • Test \(target.uniqueId)"
    }

    private var modeDialogPresented: Binding<Bool> {
        Binding(
            get: { modeTarget != nil },
            set: { if !$0 { self.modeTarget = nil } }
        )
    }

    /// `TestSelectionActivty.showModeDialog(subject:uniqueId:)`, reached from
    /// `testGrid.onItemClickListener` with `finalUniqueId = startId + position`.
    private func showModeDialog(category: ExamCategory, position: Int) {
        modeTarget = ModeTarget(
            subject: category.rawValue,
            uniqueId: category.startId + position
        )
    }

    // MARK: - Android callbacks

    /// `TestSelectionActivty.loadTestGrid(subject:startId:)`, minus the
    /// `Toast` and the adapter swap that now live in ``TestGridSheet``.
    private func loadTestGrid(_ category: ExamCategory) {
        quizType = category.quizType
        selectedCategory = category
        hasReturnedToCategories = false
        toastMessage = TestSelectionView.loadingTestsToast
    }

    /// `TestSelectionActivty.handleBack()`, driven by `onBackPressed()`.
    private func handleBack() {
        if selectedCategory != nil {
            selectedCategory = nil
            hasReturnedToCategories = true
        } else {
            dismiss()
        }
    }

    // MARK: - Launch

    /// Ports `TestSelectionActivty.openSoloMode(subject:uniqueId:)`.
    ///
    /// Android starts `SinglePlayerTestModeActivity` with `UNIQUE_ID`,
    /// `SELECTED_SUBJECT` and `QUIZ_TYPE`. On iOS the runner is presented as a
    /// ``TestActivityView`` cover instead — that screen consumes the
    /// `completed_tests_set` store this grid reads, which the Compose
    /// `SinglePlayerTestModeScreen` path does not write.
    private func openSoloMode(_ target: ModeTarget) {
        isLaunchingChallenge = false
        RemoteLogger.log(
            tag: "TestSelection_StartSolo",
            message: "Launching Solo Practice for \(target.subject) "
                + "(ID: \(target.uniqueId), QUIZ_TYPE: \(quizType))"
        )
        testToLaunch = makeQuiz(for: target)
    }

    /// Ports `TestSelectionActivty.openChallengeMode(subject:uniqueId:)`.
    ///
    /// Android starts `TopicChallengeSelectionActivity` with `UNIQUE_ID`,
    /// `QUIZ_TYPE = "TEST_SERIES"`, `SELECTED_SUBJECT` and `SUBJECT`. iOS
    /// presents the same quiz as a 1v1 duel rather than opening the topic
    /// picker, because ``TestActivityView`` owns the HP battle this screen's
    /// "Challenge Friend" row advertises.
    private func openChallengeMode(_ target: ModeTarget) {
        isLaunchingChallenge = true
        RemoteLogger.log(
            tag: "TestSelection_StartChallenge",
            message: "Launching 1v1 Battle Mode for \(target.subject) "
                + "(ID: \(target.uniqueId), QUIZ_TYPE: TEST_SERIES)"
        )
        testToLaunch = makeQuiz(for: target)
    }

    /// Android passes the two ids as intent extras and lets the runner build
    /// its own title; the cover needs a concrete `Quiz`, so the grid cell's own
    /// wording — `"<subject> Mock Test <n>"`, from
    /// `List(50) { "$subject Mock Test ${it + 1}" }` — is reused verbatim.
    private func makeQuiz(for target: ModeTarget) -> Quiz {
        Quiz(
            id: target.uniqueId,
            title: "\(target.subject) Mock Test \(target.uniqueId)",
            topic: "\(target.subject) Mock Test Series",
            subject: target.subject,
            questionCount: 50,
            durationSeconds: 2700
        )
    }

    // MARK: - Completed tests

    private var completedTestIds: Set<Int> {
        Set(completedTestsData.split(separator: ",").compactMap { Int($0) })
    }

    /// `TestGridAdapter` reads the whole `COMPLETED_TESTS` map, but the grid
    /// only ever draws the fifty ids of the active category, so the set is
    /// narrowed to that window before it reaches the sheet.
    private func visibleCompletedIds(for category: ExamCategory) -> Set<Int> {
        let lowerBound = category.startId
        let upperBound = lowerBound + TestGridSheetModel.itemCount
        return completedTestIds.filter { $0 >= lowerBound && $0 < upperBound }
    }

    /// `TestGridSheet` builds its `StateObject` in `init`, so it cannot observe
    /// `completed_tests_set` changing underneath it the way `getView()` re-reads
    /// prefs on every bind. Folding the set into the identity makes the sheet
    /// rebuild — and re-read — as soon as a run is submitted.
    private var gridIdentity: String {
        "\(selectedCategory?.rawValue ?? "")|\(completedTestsData)"
    }
}

// MARK: - Verbatim Android literals
//
// `activity_test_selection.xml` hardcodes colours and metrics that `AppTheme`
// has no token for. They are collected here, file-private, rather than inlined
// at each call site, and can be promoted into `Core/DesignSystem` once that
// file is editable.

/// Un-tokened values from `activity_test_selection.xml`.
private enum TestSelectionAndroidPalette {

    /// `android:background="#33000000"` on the scrim `View` that sits over each
    /// category landscape — black at 0x33 alpha.
    static let cardScrim = Color.black.opacity(0.2)

    /// `@android:color/white` on the category label `TextView`.
    static let label = Color(hex: 0xFFFFFFFF)
}

/// Un-tokened metrics from `activity_test_selection.xml`.
private extension AppTheme.Spacing {

    /// `android:layout_height="117dp"` on the header `LinearLayout`.
    static let headerHeight: CGFloat = 117

    /// `android:layout_height="140dp"` on both category `MaterialCardView`s.
    static let categoryCardHeight: CGFloat = 140

    /// The 32x32dp size of `R.id.menuIcon` and of the leading back control that
    /// replaces it once the grid is up.
    static let headerIconSize: CGFloat = 32
}

/// Durations that belong to neither the palette nor the spacing scale.
private enum TestSelectionTiming {

    /// `Toast.LENGTH_SHORT` — 2000 ms.
    static let toastDuration: UInt64 = 2_000_000_000
}

private extension AppTheme.Elevation {

    /// `android:elevation="4dp"` on the header `LinearLayout`.
    static let androidHeader: CGFloat = 4
}