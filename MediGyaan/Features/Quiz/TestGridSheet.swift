import SwiftUI

/// Test-series grid, ported from Android's `TestGridAdapter`.
///
/// The adapter is a `BaseAdapter` (not a `RecyclerView.Adapter`) that inflates
/// `R.layout.item_test_card` for a `List<String>` of generated test names. Its
/// host is `TestSelectionActivty.loadTestGrid()`, which builds fifty entries —
/// `List(50) { "$subject Mock Test ${it + 1}" }` — and drops them into
/// `R.id.testSeriesGrid`, an `android.widget.GridView` declared in
/// `activity_test_selection.xml` with `numColumns="2"`,
/// `horizontalSpacing="12dp"` and `verticalSpacing="12dp"`.
///
/// `getView()` reads `SharedPreferences("COMPLETED_TESTS")` on every bind and
/// derives the badge from the key `id_${startId + position}`. That one Boolean
/// is the entire state matrix; there is no per-question correct/wrong/review
/// state anywhere in this file. ``TestGridSheetModel`` therefore holds only the
/// completed-id set and the tap callback that the activity installs on the host
/// view via `AdapterView.OnItemClickListener` — the adapter itself never
/// registers a listener, and `getItemId()` is a bare `position.toLong()` that
/// nothing reads.
struct TestGridSheet: View {

    /// `headerTitle.text = subject` in `loadTestGrid()`.
    let subject: String

    /// Owns the completed-test set. `@StateObject` keeps the badge stable across
    /// the sheet's own redraws, mirroring the adapter reading prefs per bind.
    @StateObject private var model: TestGridSheetModel

    init(
        subject: String,
        startId: Int,
        completedTestIds: Set<Int> = [],
        onSelect: @escaping (Int) -> Void
    ) {
        self.subject = subject
        _model = StateObject(
            wrappedValue: TestGridSheetModel(
                subject: subject,
                startId: startId,
                completedTestIds: completedTestIds,
                onSelect: onSelect
            )
        )
    }

    var body: some View {
        ScrollView {
            header
            LazyVGrid(
                columns: [
                    GridItem(.flexible(), spacing: AppTheme.Spacing.optionGap),
                    GridItem(.flexible(), spacing: AppTheme.Spacing.optionGap)
                ],
                spacing: AppTheme.Spacing.optionGap
            ) {
                ForEach(model.entries, id: \.uniqueId) { entry in
                    TestGridSheet.TestGridCell(
                        title: entry.title,
                        subtitle: Self.subtitle,
                        isCompleted: model.completedTestIds.contains(entry.uniqueId)
                    ) {
                        model.onSelect(entry.index)
                    }
                }
            }
            .padding(AppTheme.Spacing.xs)
        }
    }

    /// `headerTitle.text = subject` from `loadTestGrid()`.
    ///
    /// The trailing `x/50` tally has no Android counterpart —
    /// `activity_test_selection.xml` gives the screen only a static
    /// `headerSubtitle` — and is added here to match `TestSelectionView`.
    private var header: some View {
        HStack(alignment: .firstTextBaseline) {
            Text(subject)
                .font(AppTheme.Font.title3)
                .foregroundStyle(AppTheme.Palette.textPrimary)
            Spacer()
            Text("\(model.completedTestIds.count)/\(TestGridSheetModel.itemCount)")
                .font(AppTheme.Font.captionBold)
                .foregroundStyle(AppTheme.Palette.textSecondary)
        }
        .padding(.horizontal, AppTheme.Spacing.lg)
        .padding(.bottom, AppTheme.Spacing.md)
    }

    /// `subtitle.text = "Standard Pattern"` — a constant in `getView()`; every
    /// row renders it regardless of the test it stands for.
    private static let subtitle = "Standard Pattern"

    /// One `getView()` call: `R.layout.item_test_card` bound to a single row.
    ///
    /// The card paints a white surface at 12dp with 3dp elevation, holding the
    /// test name (15sp bold, two lines, tail-truncated), the constant subtitle
    /// (12sp, 4dp above), and the attempt badge (10sp bold, 12dp above,
    /// 10x4dp inset).
    struct TestGridCell: View {

        let title: String
        let subtitle: String
        let isCompleted: Bool
        let onTap: () -> Void

        var body: some View {
            Button(action: onTap) {
                VStack(alignment: .leading, spacing: 0) {
                    Text(title)
                        .font(AppTheme.Font.cardTitle)
                        .foregroundStyle(TestGridSheetAndroidPalette.cardTitle)
                        .multilineTextAlignment(.leading)
                        .lineLimit(2)
                        .truncationMode(.tail)

                    Text(subtitle)
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(TestGridSheetAndroidPalette.subtitle)
                        .padding(.top, AppTheme.Spacing.xxs)

                    attemptBadge
                        .padding(.top, AppTheme.Spacing.optionGap)
                }
                .padding(AppTheme.Spacing.lg)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(
                    RoundedRectangle(
                        cornerRadius: AppTheme.Radius.androidMedium,
                        style: .continuous
                    )
                    .fill(TestGridSheetAndroidPalette.cardBackground)
                )
                .shadow(
                    color: .black.opacity(0.06),
                    radius: AppTheme.Elevation.dashboardCard,
                    y: 1
                )
            }
            .buttonStyle(.plain)
            .accessibilityLabel(title)
            .accessibilityValue(isCompleted ? "Attempted" : "Not Attempted")
        }

        /// The `if (isCompleted) … else …` block in `getView()`.
        ///
        /// `setBackgroundColor()` overwrites the `android:background` the layout
        /// declares, so the 20dp `bg_status_badge` gradient never reaches the
        /// screen and the badge draws as a hard-cornered solid — reproduced
        /// here as a `Rectangle` rather than a capsule.
        private var attemptBadge: some View {
            Text(isCompleted ? "Attempted" : "Not Attempted")
                .font(AppTheme.Font.androidStatusBadge)
                .foregroundStyle(isCompleted
                    ? TestGridSheetAndroidPalette.completedText
                    : TestGridSheetAndroidPalette.pendingText)
                .padding(.horizontal, AppTheme.Spacing.androidBadgeHorizontal)
                .padding(.vertical, AppTheme.Spacing.xxs)
                .background(
                    Rectangle().fill(isCompleted
                        ? TestGridSheetAndroidPalette.completedFill
                        : TestGridSheetAndroidPalette.pendingFill)
                )
        }
    }
}

/// The completed-test bookkeeping behind ``TestGridSheet``.
///
/// Mirrors the adapter's constructor arguments (`testList`, `startId`) and the
/// one piece of state it reads, `SharedPreferences("COMPLETED_TESTS")`. The
/// Android keys are written by whichever activity finishes a test; on iOS the
/// caller seeds ``completedTestIds`` and later calls ``markCompleted(at:)``.
final class TestGridSheetModel: ObservableObject {

    /// One grid row, paired with the row index the click listener receives.
    struct Entry: Identifiable {
        let index: Int
        let title: String
        let uniqueId: Int

        var id: Int { uniqueId }
    }

    /// `List(50)` in `TestSelectionActivty.loadTestGrid()`.
    static let itemCount = 50

    /// `Triple("NEET PG", 1, "NEET_PG")` in `setupCategoryClicks()`.
    static let neetPostGraduateStartId = 1

    /// `Triple("NEET UG", 100, "NEET_UG")` in `setupCategoryClicks()`.
    static let neetUnderGraduateStartId = 100

    let subject: String
    let startId: Int
    let onSelect: (Int) -> Void

    /// The `id_<n>` keys of `COMPLETED_TESTS`.
    @Published private(set) var completedTestIds: Set<Int>

    init(
        subject: String,
        startId: Int,
        completedTestIds: Set<Int> = [],
        onSelect: @escaping (Int) -> Void
    ) {
        self.subject = subject
        self.startId = startId
        self.completedTestIds = completedTestIds
        self.onSelect = onSelect
    }

    /// `testList`, zipped with `position` so the tap handler can report the
    /// same `AdapterView` position the Android listener receives.
    var entries: [Entry] {
        (0..<Self.itemCount).map { index in
            let uniqueId = startId + index
            return Entry(
                index: index,
                title: "\(subject) Mock Test \(index + 1)",
                uniqueId: uniqueId
            )
        }
    }

    /// Writes the `id_<n>` key the Android activity writes when a test ends.
    func markCompleted(at index: Int) {
        guard Self.itemCount > 0, (0..<Self.itemCount).contains(index) else { return }
        completedTestIds.insert(startId + index)
    }
}

// MARK: - Verbatim Android literals
//
// `item_test_card.xml` and `getView()` hardcode six colours that `AppTheme`
// has no token for. They are collected here, file-private, rather than
// inlined at each call site, and should be promoted into
// `Core/DesignSystem/Palette+Android.swift` once that file is editable.

private enum TestGridSheetAndroidPalette {

    /// `@color/white` — `cardBackgroundColor` in `item_test_card.xml`. Fixed
    /// `#FFFFFF` in `values-night` too, so unlike `AppTheme.Palette.surface`
    /// it does not flip to `#1E1E1E` at night.
    static let cardBackground = Color(hex: 0xFFFFFF)

    /// `android:textColor="#212121"` on `R.id.testTitle`.
    static let cardTitle = Color(hex: 0x212121)

    /// `android:textColor="#757575"` on `R.id.testSubtitle`.
    static let subtitle = Color(hex: 0x757575)

    /// `setBackgroundColor(Color.parseColor("#4CAF50"))` on the completed badge.
    static let completedFill = Color(hex: 0x4CAF50)

    /// `setTextColor(Color.WHITE)` on the completed badge.
    static let completedText = Color(hex: 0xFFFFFF)

    /// `setBackgroundColor(Color.parseColor("#E0E0E0"))` on the pending badge.
    static let pendingFill = Color(hex: 0xE0E0E0)

    /// `setTextColor(Color.parseColor("#757575"))` on the pending badge.
    static let pendingText = Color(hex: 0x757575)
}

// MARK: - Un-tokened metrics

private extension AppTheme.Font {

    /// `android:textSize="10sp"` with `android:textStyle="bold"` on
    /// `R.id.attemptStatus`. `AppTheme.Font` bottoms out at `micro` (11sp).
    static let androidStatusBadge = SwiftUI.Font.system(size: 10, weight: .bold)
}

private extension AppTheme.Spacing {

    /// `android:paddingHorizontal="10dp"` on `R.id.attemptStatus`.
    static let androidBadgeHorizontal: CGFloat = 10
}