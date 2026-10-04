import SwiftUI

/// Full Accuracy & Analytics View, strictly porting Android's `AccuracyActivity.kt`.
/// Features:
/// - Big accuracy ring & percentage display with real-time server/local calculation
/// - Overall stats (Correct / Attempted)
/// - Today's stats & estimated end-of-day projection
/// - Interactive Segment Tabs ("7 Days", "30 Days", "Topics")
/// - Interactive Cubic Bezier Trend Chart with neon glow gradient & point markers
/// - Topic-wise mastery breakdown list with progress bars
/// - Refresh action connected to backend (`get_profilev1.php`)
struct AccuracyView: View {

    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var session: SessionStore

    @State private var selectedTab: Int = 0 // 0: 7 Days, 1: 30 Days, 2: Topics
    @State private var isLoading: Bool = false
    @State private var statusMessage: String = "Ready"

    // Overall metrics from server & local DailyStatsManager
    @State private var overallAccuracy: Int = 0
    @State private var overallAttempted: Int = 0
    @State private var overallCorrect: Int = 0

    @State private var todayAttempted: Int = 0
    @State private var todayCorrect: Int = 0
    @State private var todayAccuracy: Int = 0

    @State private var estimatedAttempted: Int = 0
    @State private var estimatedCorrect: Int = 0
    @State private var estimatedAccuracy: Int = 0

    // Chart Trend Points
    @State private var chartData: [(label: String, accuracy: Int)] = []
    @State private var topicData: [TopicAccuracyItem] = []
    @State private var selectedDataPoint: (label: String, accuracy: Int)? = nil

    var body: some View {
        ZStack {
            AppTheme.Palette.surface.ignoresSafeArea()

            VStack(spacing: 0) {
                headerBar

                ScrollView(showsIndicators: false) {
                    VStack(spacing: AppTheme.Spacing.lg) {
                        // Big Circular Accuracy & Summary Card
                        accuracyHeroCard

                        // Today & Estimated End-of-Day Projection Card
                        projectionCard

                        // Tabs Selector: 7 Days | 30 Days | Topics
                        tabSelector

                        // Interactive Chart or Topic Breakdown
                        if selectedTab == 2 {
                            topicBreakdownSection
                        } else {
                            trendChartSection
                        }
                    }
                    .padding(.horizontal, AppTheme.Spacing.md)
                    .padding(.bottom, 40)
                }
            }
        }
        .navigationBarHidden(true)
        .onAppear {
            loadAccuracyData()
        }
    }

    // MARK: - Header Bar

    private var headerBar: some View {
        HStack {
            Button {
                dismiss()
            } label: {
                Image(systemName: "chevron.left")
                    .font(.system(size: 17, weight: .bold))
                    .foregroundStyle(AppTheme.Ink.teal)
                    .frame(width: 44, height: 44)
                    .background(Circle().fill(Color(hex: "#101D33")))
            }

            Spacer()

            VStack(spacing: 2) {
                Text("ACCURACY & ANALYTICS")
                    .font(.system(size: 13, weight: .black))
                    .tracking(2.0)
                    .foregroundStyle(AppTheme.Ink.gold)

                Text(statusMessage)
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundStyle(AppTheme.Palette.textSecondary)
            }

            Spacer()

            Button {
                loadAccuracyData()
            } label: {
                Image(systemName: "arrow.clockwise")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(AppTheme.Ink.teal)
                    .rotationEffect(.degrees(isLoading ? 360 : 0))
                    .animation(isLoading ? .linear(duration: 1).repeatForever(autoreverses: false) : .default, value: isLoading)
                    .frame(width: 44, height: 44)
                    .background(Circle().fill(Color(hex: "#101D33")))
            }
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.top, 8)
        .padding(.bottom, 6)
    }

    // MARK: - Accuracy Hero Card

    private var accuracyHeroCard: some View {
        CardContainer {
            VStack(spacing: AppTheme.Spacing.md) {
                ZStack {
                    // Outer Ring
                    Circle()
                        .stroke(Color(hex: "#10233D"), lineWidth: 12)
                        .frame(width: 140, height: 140)

                    // Progress Ring
                    Circle()
                        .trim(from: 0.0, to: CGFloat(min(max(Double(overallAccuracy) / 100.0, 0.001), 1.0)))
                        .stroke(
                            AngularGradient(
                                gradient: Gradient(colors: [Color(hex: "#00E5FF"), Color(hex: "#00E676"), Color(hex: "#FFD700")]),
                                center: .center,
                                startAngle: .degrees(-90),
                                endAngle: .degrees(270)
                            ),
                            style: StrokeStyle(lineWidth: 12, lineCap: .round)
                        )
                        .rotationEffect(.degrees(-90))
                        .frame(width: 140, height: 140)

                    VStack(spacing: 2) {
                        Text("\(overallAccuracy)%")
                            .font(.system(size: 36, weight: .black, design: .rounded))
                            .foregroundStyle(Color.white)

                        Text("ACCURACY")
                            .font(.system(size: 10, weight: .heavy))
                            .tracking(1.5)
                            .foregroundStyle(AppTheme.Ink.teal)
                    }
                }
                .padding(.top, 6)

                VStack(spacing: 4) {
                    Text("Overall Performance")
                        .font(AppTheme.Font.headline)
                        .foregroundStyle(Color.white)

                    Text("\(overallCorrect) correct / \(overallAttempted) attempted")
                        .font(AppTheme.Font.subheadline)
                        .foregroundStyle(AppTheme.Palette.textSecondary)

                    HStack(spacing: 6) {
                        Image(systemName: "crown.fill")
                            .font(.system(size: 12))
                            .foregroundStyle(AppTheme.Ink.gold)
                        Text(DailyStatsManager.shared.getRankBadge())
                            .font(.system(size: 12, weight: .bold))
                            .foregroundStyle(AppTheme.Ink.gold)
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 4)
                    .background(Capsule().fill(AppTheme.Ink.gold.opacity(0.12)))
                    .padding(.top, 4)
                }
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 8)
        }
    }

    // MARK: - Projection Card

    private var projectionCard: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Label("Today's Momentum", systemImage: "bolt.fill")
                        .font(.system(size: 13, weight: .bold))
                        .foregroundStyle(AppTheme.Ink.teal)

                    Spacer()

                    Text("\(todayAccuracy)%")
                        .font(.system(size: 15, weight: .black))
                        .foregroundStyle(Color(hex: "#00E676"))
                }

                Text("\(todayCorrect) correct / \(todayAttempted) attempted today")
                    .font(.system(size: 12))
                    .foregroundStyle(AppTheme.Palette.textSecondary)

                Divider().background(Color.white.opacity(0.1))

                HStack {
                    Label("Estimated End-of-Day", systemImage: "clock.arrow.circlepath")
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundStyle(AppTheme.Ink.gold)

                    Spacer()

                    Text("\(estimatedAccuracy)% projected")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(AppTheme.Ink.gold)
                }

                Text("\(estimatedCorrect) correct / \(estimatedAttempted) projected questions by midnight")
                    .font(.system(size: 11))
                    .foregroundStyle(AppTheme.Palette.textSecondary)
            }
        }
    }

    // MARK: - Tab Selector

    private var tabSelector: some View {
        HStack(spacing: 8) {
            tabButton(title: "7 Days", index: 0)
            tabButton(title: "30 Days", index: 1)
            tabButton(title: "Topics", index: 2)
        }
        .padding(4)
        .background(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(Color(hex: "#0A172C"))
        )
    }

    private func tabButton(title: String, index: Int) -> some View {
        let isSelected = selectedTab == index
        return Button {
            withAnimation(.easeInOut(duration: 0.2)) {
                selectedTab = index
                refreshTabContent()
            }
        } label: {
            Text(title)
                .font(.system(size: 13, weight: isSelected ? .bold : .medium))
                .foregroundStyle(isSelected ? Color(hex: "#050816") : Color.white)
                .frame(maxWidth: .infinity)
                .frame(height: 38)
                .background(
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .fill(isSelected ? Color(hex: "#00E5FF") : Color.clear)
                )
        }
        .buttonStyle(.plain)
    }

    // MARK: - Trend Chart Section

    private var trendChartSection: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Text(selectedTab == 0 ? "7-DAY ACCURACY TREND" : "30-DAY ACCURACY TREND")
                        .font(.system(size: 12, weight: .heavy))
                        .foregroundStyle(AppTheme.Palette.textSecondary)

                    Spacer()

                    if let selected = selectedDataPoint {
                        Text("\(selected.label): \(selected.accuracy)%")
                            .font(.system(size: 12, weight: .bold))
                            .foregroundStyle(Color(hex: "#00E5FF"))
                            .padding(.horizontal, 8)
                            .padding(.vertical, 2)
                            .background(Capsule().fill(Color(hex: "#00E5FF").opacity(0.15)))
                    }
                }

                if chartData.isEmpty {
                    VStack(spacing: 8) {
                        Image(systemName: "chart.line.uptrend.xyaxis")
                            .font(.system(size: 32))
                            .foregroundStyle(Color.gray.opacity(0.4))
                        Text("No history recorded yet.")
                            .font(.system(size: 13))
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 180)
                } else {
                    // Custom Cubic Bezier Line Chart in SwiftUI
                    GeometryReader { geo in
                        let width = geo.size.width
                        let height = geo.size.height

                        ZStack {
                            // Grid Lines (0%, 25%, 50%, 75%, 100%)
                            VStack(spacing: 0) {
                                ForEach(0..<5) { step in
                                    HStack {
                                        Text("\(100 - step * 25)%")
                                            .font(.system(size: 9))
                                            .foregroundStyle(Color.gray.opacity(0.5))
                                            .frame(width: 28, alignment: .leading)
                                        Rectangle()
                                            .fill(Color(hex: "#1A1F38"))
                                            .frame(height: 1)
                                    }
                                    if step < 4 { Spacer() }
                                }
                            }

                            // Chart Neon Area & Stroke Path
                            let points = computePoints(in: CGSize(width: width - 32, height: height), values: chartData.map { $0.accuracy })

                            // Gradient Area Fill
                            Path { path in
                                guard points.count > 1 else { return }
                                path.move(to: CGPoint(x: points[0].x + 32, y: height))
                                path.addLine(to: CGPoint(x: points[0].x + 32, y: points[0].y))
                                for i in 1..<points.count {
                                    let prev = points[i - 1]
                                    let curr = points[i]
                                    let control1 = CGPoint(x: (prev.x + curr.x) / 2 + 32, y: prev.y)
                                    let control2 = CGPoint(x: (prev.x + curr.x) / 2 + 32, y: curr.y)
                                    path.addCurve(to: CGPoint(x: curr.x + 32, y: curr.y), control1: control1, control2: control2)
                                }
                                path.addLine(to: CGPoint(x: points.last!.x + 32, y: height))
                                path.closeSubpath()
                            }
                            .fill(
                                LinearGradient(
                                    colors: [Color(hex: "#00E5FF").opacity(0.35), Color(hex: "#00E5FF").opacity(0.0)],
                                    startPoint: .top,
                                    endPoint: .bottom
                                )
                            )

                            // Stroke Line
                            Path { path in
                                guard points.count > 1 else { return }
                                path.move(to: CGPoint(x: points[0].x + 32, y: points[0].y))
                                for i in 1..<points.count {
                                    let prev = points[i - 1]
                                    let curr = points[i]
                                    let control1 = CGPoint(x: (prev.x + curr.x) / 2 + 32, y: prev.y)
                                    let control2 = CGPoint(x: (prev.x + curr.x) / 2 + 32, y: curr.y)
                                    path.addCurve(to: CGPoint(x: curr.x + 32, y: curr.y), control1: control1, control2: control2)
                                }
                            }
                            .stroke(Color(hex: "#00E5FF"), style: StrokeStyle(lineWidth: 3, lineCap: .round, lineJoin: .round))

                            // Data Point Circles & Tap Target
                            ForEach(Array(points.enumerated()), id: \.offset) { idx, pt in
                                let dataPoint = chartData[idx]
                                Circle()
                                    .fill(Color.white)
                                    .frame(width: 8, height: 8)
                                    .overlay(Circle().stroke(Color(hex: "#00E5FF"), lineWidth: 2))
                                    .position(x: pt.x + 32, y: pt.y)
                                    .onTapGesture {
                                        selectedDataPoint = dataPoint
                                    }
                            }
                        }
                    }
                    .frame(height: 200)

                    // Bottom Dates Label strip
                    HStack {
                        Spacer().frame(width: 32)
                        ForEach(chartData.indices, id: \.self) { idx in
                            if chartData.count <= 7 || idx % 5 == 0 || idx == chartData.count - 1 {
                                Text(chartData[idx].label)
                                    .font(.system(size: 9))
                                    .foregroundStyle(Color.gray)
                                    .frame(maxWidth: .infinity)
                            }
                        }
                    }
                }
            }
        }
    }

    private func computePoints(in size: CGSize, values: [Int]) -> [CGPoint] {
        guard values.count > 1 else {
            return values.map { _ in CGPoint(x: size.width / 2, y: size.height / 2) }
        }
        let stepX = size.width / CGFloat(values.count - 1)
        return values.enumerated().map { idx, val in
            let clampedVal = max(0, min(100, val))
            let y = size.height - (CGFloat(clampedVal) / 100.0 * (size.height - 16)) - 8
            return CGPoint(x: CGFloat(idx) * stepX, y: y)
        }
    }

    // MARK: - Topic Breakdown Section

    private var topicBreakdownSection: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    Text("TOPIC-WISE ACCURACY")
                        .font(.system(size: 12, weight: .heavy))
                        .foregroundStyle(AppTheme.Palette.textSecondary)

                    Spacer()

                    Text("\(topicData.count) Topics")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundStyle(AppTheme.Ink.teal)
                }

                if topicData.isEmpty {
                    VStack(spacing: 8) {
                        Image(systemName: "books.vertical.fill")
                            .font(.system(size: 32))
                            .foregroundStyle(Color.gray.opacity(0.4))
                        Text("No topic attempts recorded today.")
                            .font(.system(size: 13))
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 140)
                } else {
                    ForEach(topicData) { item in
                        VStack(alignment: .leading, spacing: 5) {
                            HStack {
                                Text(item.topic)
                                    .font(.system(size: 13, weight: .bold))
                                    .foregroundStyle(Color.white)

                                Spacer()

                                Text("\(item.correct)/\(item.attempted)")
                                    .font(.system(size: 11))
                                    .foregroundStyle(AppTheme.Palette.textSecondary)

                                Text("•  \(item.accuracy)%")
                                    .font(.system(size: 13, weight: .heavy))
                                    .foregroundStyle(item.accuracy >= 60 ? Color(hex: "#00E676") : Color(hex: "#FF5252"))
                            }

                            GeometryReader { g in
                                ZStack(alignment: .leading) {
                                    Capsule().fill(Color(hex: "#10233D"))
                                    Capsule().fill(item.accuracy >= 60 ? Color(hex: "#00E676") : Color(hex: "#FF5252"))
                                        .frame(width: g.size.width * CGFloat(item.accuracy) / 100.0)
                                }
                            }
                            .frame(height: 6)
                        }
                        .padding(.vertical, 3)
                    }
                }
            }
        }
    }

    // MARK: - Data Loading & Calculations

    private func refreshTabContent() {
        if selectedTab == 0 {
            chartData = DailyStatsManager.shared.getGraphData(days: 7)
            selectedDataPoint = chartData.last
        } else if selectedTab == 1 {
            chartData = DailyStatsManager.shared.getGraphData(days: 30)
            selectedDataPoint = chartData.last
        } else {
            topicData = DailyStatsManager.shared.getTopicAccuracyList()
        }
    }

    private func loadAccuracyData() {
        isLoading = true
        statusMessage = "Loading..."

        // 1. Compute local DailyStatsManager figures
        let today = DailyStatsManager.shared.getToday()
        todayAttempted = today.attempted
        todayCorrect = today.correct
        todayAccuracy = DailyStatsManager.shared.calculateAccuracy(attempted: todayAttempted, correct: todayCorrect)

        let estAtt = estimateEndOfDay(count: todayAttempted)
        let estCorr = estimateEndOfDay(count: todayCorrect)
        estimatedAttempted = estAtt
        estimatedCorrect = estCorr
        estimatedAccuracy = estAtt > 0 ? (estCorr * 100) / estAtt : 0

        let overall = DailyStatsManager.shared.getOverallStats()
        overallAttempted = overall.attempted
        overallCorrect = overall.correct
        overallAccuracy = DailyStatsManager.shared.calculateAccuracy(attempted: overallAttempted, correct: overallCorrect)

        refreshTabContent()

        // 2. Fetch remote accuracy profile from backend API (get_profilev1.php)
        Task {
            do {
                if let user = session.currentUser {
                    let stats = try await ApiClient.shared.fetchDashboard(userId: user.id)
                    await MainActor.run {
                        if stats.attempted > 0 {
                            overallAttempted = stats.attempted
                            overallCorrect = stats.correct
                            overallAccuracy = Int(stats.accuracy > 1 ? stats.accuracy : stats.accuracy * 100)
                        }
                        isLoading = false
                        statusMessage = "Updated"
                    }
                } else {
                    await MainActor.run {
                        isLoading = false
                        statusMessage = "Local Data"
                    }
                }
            } catch {
                await MainActor.run {
                    isLoading = false
                    statusMessage = "Offline / Local"
                }
            }
        }
    }

    private func estimateEndOfDay(count: Int) -> Int {
        guard count > 0 else { return 0 }
        let now = Calendar.current.dateComponents([.hour, .minute], from: Date())
        let minutesPassed = max(60, (now.hour ?? 12) * 60 + (now.minute ?? 0))
        let fraction = Float(minutesPassed) / Float(24 * 60)
        return Int(Float(count) / fraction)
    }
}
