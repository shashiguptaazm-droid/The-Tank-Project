import SwiftUI

/// Ports `AccuracyActivity` and its layout `res/layout/activity_accuracy.xml`.
///
/// The screen keeps the blocks Android stacked vertically: the big accuracy
/// figure (`R.id.txtBigAccuracy`), the stat cards (`R.id.txtOverallStats`,
/// `txtTodayStats`, `txtPeriodStats`), the status line (`R.id.txtStatus`) and
/// the `7 Days | 30 Days | Topics` strip (`R.id.tabLayoutAccuracy`) driving the
/// line chart (`R.id.lineChartAccuracy`).
///
/// Two data sources, exactly as on Android:
/// * the overall figures come from the network —
///   `GET get_profilev1.php?user_id=<id>&viewer_id=<id>` — where the first row of
///   `data.attempts` carries `total_attempted` / `correct_attempted`;
/// * today's pair, the trend and the topic breakdown come from
///   ``DailyStatsManager``, the iOS counterpart of the Kotlin object of the same
///   name.
///
/// Android drew this screen on the Material palette; it is hosted inside the
/// dark dashboard shell here, so the chrome uses ``AppTheme/Ink`` while the
/// chart keeps the colours MPAndroidChart was configured with verbatim
/// (`#00E5FF` stroke, white markers, 0…100% left axis, `bg_chart_gradient` fill).
struct AccuracyView: View {

    /// `AccuracyActivity.TAG`.
    private static let logTag = "ACCURACY_DEBUG"

    /// `Toast.LENGTH_LONG`.
    private static let longToastDuration: Double = 3.5

    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var session: SessionStore

    // MARK: - State

    /// `AccuracyActivity.selectedTab`, driven by `setupTabs()`'s listener.
    @State private var selectedTab: AccuracyTab = .sevenDays
    @State private var isLoading: Bool = false
    /// `R.id.txtStatus`.
    @State private var statusMessage: String = "Loading..."
    /// `R.id.txtPeriodStats` once a tab has been rendered.
    @State private var periodStatus: String = ""
    /// The `LineDataSet` name, surfaced through MPAndroidChart's legend.
    @State private var chartTitle: String = ""

    @State private var overallAttempted: Int = 0
    @State private var overallCorrect: Int = 0
    @State private var overallAccuracy: Int = 0

    @State private var todayAttempted: Int = 0
    @State private var todayCorrect: Int = 0
    @State private var todayAccuracy: Int = 0

    @State private var estimatedAttempted: Int = 0
    @State private var estimatedCorrect: Int = 0
    @State private var estimatedAccuracy: Int = 0

    /// `DailyStatsManager.getGraphData(days:)` → `(label, accuracy)` pairs.
    @State private var chartData: [(label: String, accuracy: Int)] = []
    /// `DailyStatsManager.getTopicAccuracyList()`, already sorted by accuracy.
    @State private var topicData: [TopicAccuracyItem] = []
    /// `renderTopicWise()`'s attempt-weighted `overallTopicAccuracy`.
    @State private var topicOverallAccuracy: Int = 0
    /// The index the user last touched. MPAndroidChart only draws
    /// `CustomMarkerView` once a value is highlighted, so nothing is preselected.
    @State private var selectedIndex: Int?

    /// The `Toast`s `AccuracyActivity` raised.
    @State private var toast: String?
    @State private var errorMessage: String?

    var body: some View {
        ZStack(alignment: .top) {
            AppTheme.Ink.background.ignoresSafeArea()

            VStack(spacing: 0) {
                headerBar

                ScrollView(showsIndicators: false) {
                    VStack(spacing: AppTheme.Spacing.lg) {
                        accuracyHeroCard
                        overallAndTodayRow
                        estimatedCard
                        tabSelector
                        trendSection
                        topicSection
                    }
                    .padding(.horizontal, AppTheme.Spacing.lg)
                    .padding(.bottom, AppTheme.Spacing.xxl)
                }
            }

            if let message = toast {
                AccuracyToastBanner(text: message, seconds: Self.longToastDuration) {
                    toast = nil
                }
                .padding(.horizontal, AppTheme.Spacing.lg)
                .padding(.top, AppTheme.Spacing.sm)
                .transition(.move(edge: .top).combined(with: .opacity))
            }
        }
        .toolbar(.hidden, for: .navigationBar)
        .animation(.easeOut(duration: 0.2), value: toast)
        .errorAlert(message: $errorMessage)
        .onAppear {
            RemoteLogger.log(tag: Self.logTag, message: "AccuracyActivity created")
            renderSelectedTab()
            loadAccuracy()
        }
    }

    // MARK: - Header (`R.id.txtStatus`, `R.id.btnRefresh`)

    private var headerBar: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            Button {
                dismiss()
            } label: {
                Image(systemName: "chevron.left")
                    .font(AppTheme.Font.callout.weight(.bold))
                    .foregroundStyle(AppTheme.Ink.iconTint)
                    .frame(width: 44, height: 44)
                    .background(Circle().fill(AppTheme.Ink.tile))
            }
            .buttonStyle(.plain)

            VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
                Text("ACCURACY")
                    .font(AppTheme.Font.cardTitle)
                    .foregroundStyle(AppTheme.Ink.textPrimary)

                Text(statusMessage)
                    .font(AppTheme.Font.micro)
                    .foregroundStyle(AppTheme.Ink.textSecondary)
                    .lineLimit(1)
            }

            Spacer(minLength: 0)

            Button {
                refreshTapped()
            } label: {
                Image(systemName: "arrow.clockwise")
                    .font(AppTheme.Font.callout.weight(.bold))
                    .foregroundStyle(AppTheme.Ink.cyan)
                    .rotationEffect(.degrees(isLoading ? 360 : 0))
                    .animation(
                        isLoading
                            ? .linear(duration: 1).repeatForever(autoreverses: false)
                            : .default,
                        value: isLoading
                    )
                    .frame(width: 44, height: 44)
                    .background(Circle().fill(AppTheme.Ink.tile))
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, AppTheme.Spacing.lg)
        .padding(.vertical, AppTheme.Spacing.sm)
    }

    // MARK: - `R.id.txtBigAccuracy`

    private var accuracyHeroCard: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            ZStack {
                Circle()
                    .stroke(AppTheme.Ink.elevated, lineWidth: 12)

                Circle()
                    .trim(from: 0.0, to: CGFloat(min(max(Double(overallAccuracy) / 100.0, 0.001), 1.0)))
                    .stroke(
                        AngularGradient(
                            gradient: Gradient(colors: [AppTheme.Ink.cyan, AppTheme.Palette.success, AppTheme.Ink.gold]),
                            center: .center,
                            startAngle: .degrees(-90),
                            endAngle: .degrees(270)
                        ),
                        style: StrokeStyle(lineWidth: 12, lineCap: .round)
                    )
                    .rotationEffect(.degrees(-90))

                VStack(spacing: AppTheme.Spacing.xxs) {
                    Text("\(overallAccuracy)%")
                        .font(AppTheme.Font.display)
                        .foregroundStyle(Color.white)

                    Text("ACCURACY")
                        .font(AppTheme.Font.micro)
                        .tracking(1.5)
                        .foregroundStyle(AppTheme.Ink.cyan)
                }
            }
            .frame(width: 140, height: 140)
            .contentShape(Circle())
            .onTapGesture { exportDiagnosticReport() }

            Text("Tap the ring for a diagnostic report")
                .font(AppTheme.Font.micro)
                .foregroundStyle(AppTheme.Ink.textHint)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, AppTheme.Spacing.sm)
    }

    // MARK: - `R.id.txtOverallStats` + `R.id.txtTodayStats`

    private var overallAndTodayRow: some View {
        HStack(alignment: .top, spacing: AppTheme.Spacing.sm) {
            statCard(
                title: "OVERALL",
                tint: AppTheme.Ink.gold,
                value: "Overall: \(overallCorrect) correct / \(overallAttempted) attempted"
            )
            statCard(
                title: "TODAY",
                tint: AppTheme.Ink.cyan,
                value: "Today: \(todayCorrect) correct / \(todayAttempted) attempted • Accuracy \(todayAccuracy)%"
            )
        }
    }

    private func statCard(title: String, tint: Color, value: String) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
            Text(title)
                .font(AppTheme.Font.micro)
                .foregroundStyle(tint)

            Text(value)
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Ink.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AppTheme.Ink.surface)
        )
        .overlay(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .stroke(tint.opacity(0.6), lineWidth: 1)
        )
    }

    // MARK: - `R.id.txtPeriodStats` (estimated end of day)

    private var estimatedCard: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
            Text("ESTIMATED END-OF-DAY")
                .font(AppTheme.Font.micro)
                .foregroundStyle(AppTheme.Ink.gold)

            Text("Estimated end of day: \(estimatedCorrect) correct / \(estimatedAttempted) attempted • Accuracy \(estimatedAccuracy)%")
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Ink.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AppTheme.Ink.surface)
        )
        .overlay(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .stroke(AppTheme.Ink.gold.opacity(0.6), lineWidth: 1)
        )
    }

    // MARK: - `R.id.tabLayoutAccuracy`

    private var tabSelector: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            ForEach(AccuracyTab.allCases) { tab in
                tabButton(tab)
            }
        }
        .padding(AppTheme.Spacing.xxs)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.field, style: .continuous)
                .fill(AppTheme.Ink.surface)
        )
    }

    private func tabButton(_ tab: AccuracyTab) -> some View {
        let isSelected = selectedTab == tab
        return Button {
            withAnimation(.easeInOut(duration: 0.2)) {
                selectedTab = tab
                renderSelectedTab()
            }
        } label: {
            Text(tab.title)
                .font(AppTheme.Font.callout.weight(isSelected ? .bold : .medium))
                .foregroundStyle(isSelected ? AppTheme.Ink.background : AppTheme.Ink.textSecondary)
                .frame(maxWidth: .infinity)
                .frame(height: 38)
                .background(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.option, style: .continuous)
                        .fill(isSelected ? AppTheme.Ink.cyan : Color.clear)
                )
        }
        .buttonStyle(.plain)
    }

    // MARK: - `R.id.lineChartAccuracy` (7 Days / 30 Days)

    @ViewBuilder
    private var trendSection: some View {
        if selectedTab.trendDays != nil {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                sectionHeader(title: chartTitle, detail: periodStatus)

                if chartData.isEmpty {
                    emptyState(
                        icon: "chart.line.uptrend.xyaxis",
                        message: "\(selectedTab.title) • No history yet"
                    )
                } else {
                    AccuracyTrendChart(points: chartData, selectedIndex: $selectedIndex)
                        .frame(height: 220)
                        .padding(AppTheme.Spacing.md)
                        .background(
                            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                                .fill(AppTheme.Ink.surface)
                        )
                }
            }
        }
    }

    // MARK: - `renderTopicWise()`

    @ViewBuilder
    private var topicSection: some View {
        if selectedTab == .topics {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                sectionHeader(title: chartTitle, detail: periodStatus)

                if topicData.isEmpty {
                    emptyState(icon: "books.vertical", message: "Topics • No topic data yet")
                } else {
                    ForEach(topicData) { item in
                        topicRow(item)
                    }
                }
            }
            .padding(AppTheme.Spacing.md)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                    .fill(AppTheme.Ink.surface)
            )
        }
    }

    private func topicRow(_ item: TopicAccuracyItem) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
            HStack(alignment: .firstTextBaseline, spacing: AppTheme.Spacing.xs) {
                Text(item.topic)
                    .font(AppTheme.Font.subheadline.weight(.bold))
                    .foregroundStyle(AppTheme.Ink.textPrimary)
                    .lineLimit(2)

                Spacer(minLength: AppTheme.Spacing.xs)

                Text("\(item.correct)/\(item.attempted)")
                    .font(AppTheme.Font.micro)
                    .foregroundStyle(AppTheme.Ink.textSecondary)

                Text("•  \(item.accuracy)%")
                    .font(AppTheme.Font.callout.weight(.heavy))
                    .foregroundStyle(item.accuracy >= 60 ? AppTheme.Palette.success : AppTheme.Palette.error)
            }

            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    Capsule().fill(AppTheme.Ink.elevated)
                    Capsule()
                        .fill(item.accuracy >= 60 ? AppTheme.Palette.success : AppTheme.Palette.error)
                        .frame(width: geometry.size.width * CGFloat(item.accuracy) / 100.0)
                }
            }
            .frame(height: 6)
        }
        .padding(.vertical, AppTheme.Spacing.xxs)
    }

    // MARK: - Shared chrome

    private func sectionHeader(title: String, detail: String) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: AppTheme.Spacing.sm) {
            Text(title)
                .font(AppTheme.Font.captionBold)
                .foregroundStyle(AppTheme.Ink.textPrimary)

            Spacer(minLength: 0)

            Text(detail)
                .font(AppTheme.Font.micro)
                .foregroundStyle(AppTheme.Ink.cyan)
                .lineLimit(1)
        }
    }

    private func emptyState(icon: String, message: String) -> some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            Image(systemName: icon)
                .font(AppTheme.Font.largeTitle)
                .foregroundStyle(AppTheme.Ink.textHint)

            Text(message)
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Ink.textSecondary)
        }
        .frame(maxWidth: .infinity)
        .frame(height: 180)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AppTheme.Ink.surface)
        )
    }

    // MARK: - Actions

    /// Ports `AccuracyActivity.onCreate`'s `btnRefresh` click listener.
    private func refreshTapped() {
        RemoteLogger.log(tag: Self.logTag, message: "Refresh Accuracy tapped")
        loadAccuracy()
    }

    /// Ports `AccuracyActivity.exportDiagnosticReportPdf()`, reached by tapping
    /// `R.id.txtBigAccuracy`. Android read the cached `name` preference (default
    /// `"Doctor"` — which is what ``SessionStore/userName`` resolves to), showed a
    /// `Toast.LENGTH_LONG` and wrote no file; only the toast is ported.
    private func exportDiagnosticReport() {
        let userName = session.userName
        RemoteLogger.log(tag: Self.logTag, message: "Diagnostic Report Generated for \(userName)")
        toast = "Diagnostic Report Generated for \(userName) (\(overallAccuracy)%)"
    }

    /// Ports `AccuracyActivity.setupTabs()`'s `OnTabSelectedListener` →
    /// `renderSelectedTab()`.
    private func renderSelectedTab() {
        if let days = selectedTab.trendDays {
            renderTrend(days: days)
        } else {
            renderTopicWise()
        }
    }

    /// Ports `AccuracyActivity.renderTrend(days:title:)`: the period line above
    /// the chart, then `setupChart(...)`. An empty list is `clearChart()` plus the
    /// "No history yet" line.
    private func renderTrend(days: Int) {
        let title = selectedTab.title
        chartTitle = "\(title) accuracy trend"
        let stats = DailyStatsManager.shared.getGraphData(days: days)

        guard !stats.isEmpty else {
            chartData = []
            selectedIndex = nil
            periodStatus = "\(title) • No history yet"
            return
        }

        chartData = stats
        selectedIndex = nil
        periodStatus = "\(title) • Showing trend"
    }

    /// Ports `AccuracyActivity.renderTopicWise()`. `overallTopicAccuracy` divides
    /// the summed `accuracy × attempted` by the total attempted, exactly as the
    /// Kotlin expression did. Kotlin's `totalCorrect` local is dropped: it was
    /// computed and never read.
    private func renderTopicWise() {
        chartTitle = "Topic-wise accuracy"
        let items = DailyStatsManager.shared.getTopicAccuracyList()

        guard !items.isEmpty else {
            topicData = []
            topicOverallAccuracy = 0
            periodStatus = "Topics • No topic data yet"
            return
        }

        topicData = items
        let totalAttempted = items.reduce(0) { $0 + $1.attempted }
        topicOverallAccuracy = totalAttempted > 0
            ? items.reduce(0) { $0 + $1.accuracy * $1.attempted } / totalAttempted
            : 0
        periodStatus = "Topics • Overall today \(topicOverallAccuracy)%"
    }

    // MARK: - Network

    /// Ports `AccuracyActivity.loadAccuracy()` plus `updateAccuracyUI(json:)`.
    ///
    /// The response is read as a raw dictionary rather than through
    /// `AuthAPI.profile`, because `get_profilev1.php` wraps its payload in a
    /// `data` envelope that `User`'s tolerant decoder does not unwrap — the same
    /// reason `DashboardViewModel.fetchProfile` reads the dictionary by hand.
    private func loadAccuracy() {
        guard let userId = session.currentUser?.id, userId > 0 else {
            statusMessage = "Invalid user"
            isLoading = false
            return
        }

        isLoading = true
        statusMessage = "Loading accuracy..."
        RemoteLogger.log(
            tag: Self.logTag,
            message: "API CALL: get_profilev1.php?user_id=\(userId)&viewer_id=\(userId)"
        )

        Task {
            do {
                let json = try await HTTPClient.shared.getObject(
                    .profile,
                    query: ["user_id": String(userId), "viewer_id": String(userId)]
                )
                let figures = AccuracyView.profileFigures(from: json)
                await MainActor.run {
                    overallAttempted = figures.attempted
                    overallCorrect = figures.correct
                    overallAccuracy = DailyStatsManager.shared.calculateAccuracy(
                        attempted: figures.attempted,
                        correct: figures.correct
                    )
                    applyLocalStats()
                    statusMessage = "\(figures.name) • Accuracy loaded"
                    isLoading = false
                }
            } catch {
                RemoteLogger.log(tag: Self.logTag, message: "Network error: \(error.localizedDescription)")
                await MainActor.run {
                    statusMessage = "Network error"
                    errorMessage = "Network error"
                    isLoading = false
                }
            }
        }
    }

    /// Ports the local half of `AccuracyActivity.updateAccuracyUI(json:)`: today's
    /// pair, today's accuracy, and the end-of-day projection.
    private func applyLocalStats() {
        let today = DailyStatsManager.shared.getToday()
        todayAttempted = today.attempted
        todayCorrect = today.correct
        todayAccuracy = DailyStatsManager.shared.calculateAccuracy(
            attempted: today.attempted,
            correct: today.correct
        )

        estimatedAttempted = estimateEndOfDay(count: todayAttempted)
        estimatedCorrect = estimateEndOfDay(count: todayCorrect)
        estimatedAccuracy = estimatedAttempted > 0
            ? (estimatedCorrect * 100) / estimatedAttempted
            : 0
    }

    /// Ports `AccuracyActivity.estimateEndOfDay(currentCount:)`: the day's total
    /// is extrapolated from the fraction of it that has elapsed, floored at one
    /// hour so a midnight session cannot divide by zero.
    private func estimateEndOfDay(count: Int) -> Int {
        guard count > 0 else { return 0 }
        let parts = Calendar.current.dateComponents([.hour, .minute], from: Date())
        let minutesPassed = max(60, (parts.hour ?? 0) * 60 + (parts.minute ?? 0))
        let fractionOfDay = Float(minutesPassed) / Float(24 * 60)
        return Int(Float(count) / fractionOfDay)
    }

    /// Ports `AccuracyActivity.loadAccuracy()`'s response handling — `data` with a
    /// root fallback, then `name` and `attempts[0].total_attempted` /
    /// `correct_attempted`. PHP hands these back as strings, so the numbers are
    /// coerced the way `JSONObject.optInt` coerces them.
    private static func profileFigures(from json: [String: Any]) -> (name: String, attempted: Int, correct: Int) {
        let payload = (json["data"] as? [String: Any]) ?? json
        let name = (payload["name"] as? String) ?? "User"

        var attempted = 0
        var correct = 0
        if let rows = payload["attempts"] as? [Any],
           let first = rows.first as? [String: Any] {
            attempted = intValue(first["total_attempted"])
            correct = intValue(first["correct_attempted"])
        }

        return (name, attempted, correct)
    }

    private static func intValue(_ raw: Any?) -> Int {
        if let value = raw as? Int { return value }
        if let value = raw as? Double { return Int(value) }
        if let value = raw as? String { return Int(value) ?? Int(Double(value) ?? 0) }
        return 0
    }
}

// MARK: - Tabs

/// The three tabs `AccuracyActivity.setupTabs()` adds to
/// `R.id.tabLayoutAccuracy`, in the order it adds them.
private enum AccuracyTab: Int, CaseIterable, Identifiable {

    case sevenDays = 0
    case thirtyDays = 1
    case topics = 2

    var id: Int { rawValue }

    /// `tab.newTab().setText(...)`.
    var title: String {
        switch self {
        case .sevenDays: return "7 Days"
        case .thirtyDays: return "30 Days"
        case .topics: return "Topics"
        }
    }

    /// The `renderTrend(days, title:)` window; `nil` for the topic tab, which
    /// `renderSelectedTab()` routes to `renderTopicWise()` instead.
    var trendDays: Int? {
        switch self {
        case .sevenDays: return 7
        case .thirtyDays: return 30
        case .topics: return nil
        }
    }
}

// MARK: - Chart

/// Ports `AccuracyActivity.setupChart(labels:values:chartTitle:)` together with
/// `AccuracyActivity.CustomMarkerView`.
///
/// MPAndroidChart's configuration, one-for-one:
/// * a `#00E5FF` 3dp cubic-bezier line over the `R.drawable.bg_chart_gradient`
///   fill (`#0000E5FF` → `#4D00E5FF`, i.e. transparent at the baseline);
/// * white markers with a cyan ring (`circleRadius = 5f`, `circleHoleRadius = 3f`)
///   and the values hidden, because `CustomMarkerView` shows them instead;
/// * an `axisLeft` pinned to 0…100 with grid lines, and a bottom x-axis whose
///   values map back onto the label array.
private struct AccuracyTrendChart: View {

    /// `DailyStatsManager.getGraphData(days:)` output.
    let points: [(label: String, accuracy: Int)]

    /// `Highlight` — MPAndroidChart only draws the marker for a touched value.
    @Binding var selectedIndex: Int?

    /// Room for the `axisLeft` percentage labels.
    private static let gutter: CGFloat = 32

    var body: some View {
        GeometryReader { geometry in
            let plot = CGSize(
                width: max(1, geometry.size.width - Self.gutter),
                height: max(1, geometry.size.height)
            )
            let coords = plotPoints(in: plot)

            HStack(spacing: 0) {
                gridLabels(height: plot.height)

                ZStack(alignment: .topLeading) {
                    gridLines(height: plot.height)
                    areaPath(coords, height: plot.height)
                    strokePath(coords)
                    markers(coords)
                }
                .frame(width: plot.width, height: plot.height, alignment: .topLeading)
            }
            .contentShape(Rectangle())
            .gesture(dragGesture(stepX: plot.width))
        }
    }

    // MARK: - Axes

    /// `axisLeft.valueFormatter` — `"${value.toInt()}%"` at the 0/25/50/75/100
    /// ticks MPAndroidChart drew for the pinned 0…100 range.
    private func gridLabels(height: CGFloat) -> some View {
        VStack(spacing: 0) {
            ForEach(0..<5, id: \.self) { step in
                Text("\(100 - step * 25)%")
                    .font(AppTheme.Font.micro)
                    .foregroundStyle(AppTheme.Ink.textHint)
                    .frame(width: Self.gutter - 4, height: height / 5, alignment: .trailing)
            }
        }
        .frame(width: Self.gutter, height: height, alignment: .top)
    }

    /// `axisLeft.setDrawGridLines(true)`.
    private func gridLines(height: CGFloat) -> some View {
        VStack(spacing: 0) {
            ForEach(0..<5, id: \.self) { step in
                Rectangle()
                    .fill(AppTheme.Ink.slate.opacity(0.35))
                    .frame(height: 1)
                if step < 4 {
                    Spacer(minLength: 0)
                }
            }
        }
        .frame(maxWidth: .infinity)
        .frame(height: height, alignment: .top)
    }

    /// `setDrawFilled(true)` with `R.drawable.bg_chart_gradient` beneath the line.
    private func areaPath(_ coords: [CGPoint], height: CGFloat) -> some View {
        Path { path in
            guard let first = coords.first, let last = coords.last else { return }
            path.move(to: CGPoint(x: first.x, y: height))
            path.addLine(to: CGPoint(x: first.x, y: first.y))
            if coords.count > 1 {
                for index in 1..<coords.count {
                    let previous = coords[index - 1]
                    let current = coords[index]
                    path.addCurve(
                        to: current,
                        control1: CGPoint(x: (previous.x + current.x) / 2, y: previous.y),
                        control2: CGPoint(x: (previous.x + current.x) / 2, y: current.y)
                    )
                }
            }
            path.addLine(to: CGPoint(x: last.x, y: height))
            path.closeSubpath()
        }
        .fill(
            LinearGradient(
                colors: [AppTheme.Ink.cyan.opacity(0.30), AppTheme.Ink.cyan.opacity(0)],
                startPoint: .top,
                endPoint: .bottom
            )
        )
    }

    /// `lineWidth = 3f`, `mode = CUBIC_BEZIER`, `color = #00E5FF`.
    private func strokePath(_ coords: [CGPoint]) -> some View {
        Path { path in
            guard let first = coords.first else { return }
            path.move(to: first)
            guard coords.count > 1 else { return }
            for index in 1..<coords.count {
                let previous = coords[index - 1]
                let current = coords[index]
                path.addCurve(
                    to: current,
                    control1: CGPoint(x: (previous.x + current.x) / 2, y: previous.y),
                    control2: CGPoint(x: (previous.x + current.x) / 2, y: current.y)
                )
            }
        }
        .stroke(
            AppTheme.Ink.cyan,
            style: StrokeStyle(lineWidth: 3, lineCap: .round, lineJoin: .round)
        )
    }

    /// `setCircleColor(Color.WHITE)`, `circleRadius = 5f`, `circleHoleRadius = 3f`,
    /// plus the bubble `CustomMarkerView` floated above the highlighted point
    /// (`getOffset()` returns `(-(width / 2), -height)`).
    private func markers(_ coords: [CGPoint]) -> some View {
        ForEach(Array(coords.enumerated()), id: \.offset) { index, point in
            Circle()
                .fill(Color.white)
                .frame(width: 6, height: 6)
                .overlay(
                    Circle()
                        .stroke(AppTheme.Ink.cyan, lineWidth: 2)
                        .frame(width: 10, height: 10)
                )
                .position(point)
                .overlay(alignment: .top) {
                    if selectedIndex == index {
                        Text("\(points[index].accuracy)%")
                            .font(AppTheme.Font.caption2)
                            .foregroundStyle(Color.white)
                            .padding(.horizontal, AppTheme.Spacing.sm)
                            .padding(.vertical, AppTheme.Spacing.xxs)
                            .background(
                                RoundedRectangle(cornerRadius: AppTheme.Radius.option, style: .continuous)
                                    .fill(AppTheme.Ink.elevated)
                            )
                            .offset(y: -8)
                            .fixedSize()
                    }
                }
        }
    }

    /// Stands in for MPAndroidChart's pinch-zoom: the nearest x wins, which is
    /// what its highlight indicator did on tap or drag.
    private func dragGesture(stepX: CGFloat) -> some Gesture {
        DragGesture(minimumDistance: 0)
            .onChanged { value in
                guard !points.isEmpty else {
                    selectedIndex = nil
                    return
                }
                guard points.count > 1, stepX > 0 else {
                    selectedIndex = 0
                    return
                }
                let index = Int(((value.location.x - Self.gutter) / stepX).rounded())
                selectedIndex = min(max(index, 0), points.count - 1)
            }
    }

    /// Maps each datum onto the plot box: x is the entry index (MPAndroidChart's
    /// `xAxis.granularity = 1f`), y is the accuracy on the pinned 0…100 axis.
    private func plotPoints(in size: CGSize) -> [CGPoint] {
        guard points.count > 1 else {
            return points.map { _ in CGPoint(x: size.width / 2, y: size.height / 2) }
        }
        let stepX = size.width / CGFloat(points.count - 1)
        return points.enumerated().map { index, point in
            let clamped = max(0, min(100, point.accuracy))
            let y = size.height - (CGFloat(clamped) / 100 * (size.height - 16)) - 8
            return CGPoint(x: CGFloat(index) * stepX, y: y)
        }
    }
}

// MARK: - Toast

/// The stand-in for `Toast.makeText(this, …, duration).show()`, which iOS has no
/// equivalent of. `seconds` follows `Toast.LENGTH_SHORT` (2s) and
/// `Toast.LENGTH_LONG` (3.5s).
private struct AccuracyToastBanner: View {

    let text: String
    let seconds: Double
    var onDismiss: (() -> Void)?

    var body: some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            Image(systemName: "doc.text.fill")
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Ink.cyan)

            Text(text)
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Ink.textPrimary)
                .lineLimit(2)
                .multilineTextAlignment(.leading)

            Spacer(minLength: 0)
        }
        .padding(.horizontal, AppTheme.Spacing.lg)
        .padding(.vertical, AppTheme.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.materialCard, style: .continuous)
                .fill(AppTheme.Ink.elevated)
        )
        .shadow(color: .black.opacity(0.3), radius: AppTheme.Elevation.card, y: 2)
        .task(id: text) {
            try? await Task.sleep(nanoseconds: UInt64(seconds * 1_000_000_000))
            onDismiss?()
        }
    }
}