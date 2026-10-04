import SwiftUI

/// Rank prediction and college lookup. Ports `PredictCollegeActivity`,
/// `CollegeDetailActivity`, and `RankActivity`.
struct PredictorView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api

    @State private var scoreText = ""
    @State private var predictionState: LoadState<RankPrediction> = .idle
    @State private var collegesState: LoadState<[College]> = .idle

    var body: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.lg) {
                inputCard

                if case let .loaded(prediction) = predictionState {
                    predictionCard(prediction)
                    collegesSection
                }

                if let message = predictionState.errorMessage {
                    ErrorStateView(message: message) {
                        Task { await predict() }
                    }
                }
            }
            .padding(AppTheme.Spacing.md)
        }
        .screenBackground()
        .navigationTitle("Rank Predictor")
        .toolbar(.visible, for: .navigationBar)
        .navigationBarTitleDisplayMode(.inline)
    }

    // MARK: - Sections

    private var inputCard: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
                    Text("Predict your rank")
                        .font(AppTheme.Font.headline)
                    Text("Enter your expected score to see where you might stand.")
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }

                HStack(spacing: AppTheme.Spacing.sm) {
                    TextField("Expected score", text: $scoreText)
                        .keyboardType(.decimalPad)
                        .padding(AppTheme.Spacing.md)
                        .background(
                            RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                                .fill(AppTheme.Palette.background)
                        )

                    Button {
                        Task { await predict() }
                    } label: {
                        Image(systemName: "chart.line.uptrend.xyaxis")
                            .font(.system(size: 17, weight: .semibold))
                            .frame(width: 50, height: 50)
                            .background(
                                RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                                    .fill(AppTheme.Palette.primary)
                            )
                            .foregroundStyle(.white)
                    }
                    .disabled(Double(scoreText) == nil)
                    .opacity(Double(scoreText) == nil ? 0.5 : 1)
                }

                if predictionState.isLoading {
                    HStack(spacing: AppTheme.Spacing.sm) {
                        ProgressView()
                        Text("Calculating…")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                    }
                }
            }
        }
    }

    private func predictionCard(_ prediction: RankPrediction) -> some View {
        CardContainer {
            VStack(spacing: AppTheme.Spacing.md) {
                Text("Predicted Rank")
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Palette.textSecondary)

                Text("#\(prediction.predictedRank)")
                    .font(.system(size: 42, weight: .bold, design: .rounded))
                    .foregroundStyle(AppTheme.Palette.primary)

                HStack(spacing: AppTheme.Spacing.sm) {
                    StatTile(
                        value: String(format: "%.1f", prediction.predictedScore),
                        label: "Score",
                        systemImage: "star.fill",
                        tint: AppTheme.Palette.warning
                    )
                    StatTile(
                        value: String(format: "%.1f", prediction.percentile),
                        label: "Percentile",
                        systemImage: "chart.bar.fill",
                        tint: AppTheme.Palette.success
                    )
                }

                if !prediction.message.isEmpty {
                    Text(prediction.message)
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                        .multilineTextAlignment(.center)
                }
            }
        }
    }

    private var collegesSection: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            SectionHeader(title: "Colleges you may get")

            switch collegesState {
            case .idle, .loading:
                LoadingStateView(message: "Finding colleges…")
                    .frame(height: 120)

            case let .failed(message):
                ErrorStateView(message: message)

            case let .loaded(colleges):
                if colleges.isEmpty {
                    EmptyStateView(
                        title: "No colleges matched",
                        message: "Try a different score range.",
                        systemImage: "building.columns"
                    )
                } else {
                    ForEach(colleges) { college in
                        NavigationLink {
                            CollegeDetailView(college: college)
                        } label: {
                            CollegeRow(college: college)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }

    // MARK: - Networking

    @MainActor
    private func predict() async {
        guard let score = Double(scoreText) else { return }
        let userId = session.userId
        predictionState = await LoadState.result { [api] in
            try await api.predictor.predictRank(userId: userId, score: score)
        }

        if let prediction = predictionState.value {
            collegesState = await LoadState.result { [api] in
                try await api.predictor.colleges(rank: prediction.predictedRank)
            }
        }
    }
}

/// A college row in the predictor results.
struct CollegeRow: View {
    let college: College

    private var logoURL: URL? {
        guard !college.collegeLogo.isEmpty else { return nil }
        if college.collegeLogo.starts(with: "http") {
            return URL(string: college.collegeLogo)
        }
        let clean = college.collegeLogo.trimmingCharacters(in: CharacterSet(charactersIn: "./"))
        return URL(string: "https://medigyaan.com/Neurons/" + clean)
    }

    var body: some View {
        CardContainer(padding: AppTheme.Spacing.sm) {
            HStack(spacing: AppTheme.Spacing.md) {
                if let logoURL {
                    AsyncImage(url: logoURL) { phase in
                        switch phase {
                        case .success(let image):
                            image
                                .resizable()
                                .scaledToFit()
                                .frame(width: 38, height: 38)
                                .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.sm))
                        default:
                            fallbackIcon
                        }
                    }
                } else {
                    fallbackIcon
                }

                VStack(alignment: .leading, spacing: 3) {
                    Text(college.name.isEmpty ? "College" : college.name)
                        .font(AppTheme.Font.callout.weight(.semibold))
                        .lineLimit(2)
                    if !college.state.isEmpty {
                        Text(college.state)
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                    }

                    // Chips row
                    HStack(spacing: 6) {
                        if college.closingRank > 0 {
                            Text("Cutoff: \(college.closingRank)")
                                .font(.system(size: 10, weight: .bold))
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(Capsule().fill(Color.orange.opacity(0.18)))
                                .foregroundStyle(Color.orange)
                        }

                        if !college.fees.isEmpty && college.fees != "0" {
                            Text("₹\(college.fees)")
                                .font(.system(size: 10, weight: .bold))
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(Capsule().fill(AppTheme.Palette.primary.opacity(0.18)))
                                .foregroundStyle(AppTheme.Palette.primary)
                        }

                        if !college.averageStipend.isEmpty && college.averageStipend != "0" {
                            Text("Stipend: ₹\(college.averageStipend)")
                                .font(.system(size: 10, weight: .bold))
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(Capsule().fill(Color.green.opacity(0.18)))
                                .foregroundStyle(Color.green)
                        }

                        if !college.bondYears.isEmpty {
                            let bondText = college.bondYears == "0" ? "No Bond" : "\(college.bondYears) yr bond"
                            let bondColor = college.bondYears == "0" ? Color.blue : Color.red
                            Text(bondText)
                                .font(.system(size: 10, weight: .bold))
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(Capsule().fill(bondColor.opacity(0.18)))
                                .foregroundStyle(bondColor)
                        }
                    }
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(AppTheme.Palette.textSecondary.opacity(0.6))
            }
        }
    }

    private var fallbackIcon: some View {
        Image(systemName: "building.columns.fill")
            .font(.system(size: 18))
            .foregroundStyle(AppTheme.Palette.primary)
            .frame(width: 38, height: 38)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                    .fill(AppTheme.Palette.primary.opacity(0.12))
            )
    }
}

/// Detailed college information. Ports Android `CollegeDetailActivity.kt` and `CollegeHtmlRepository.kt`.
struct CollegeDetailView: View {

    let college: College

    @State private var detailData: CollegeDetailData?
    @State private var isLoading = false
    @State private var showAllRows = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                // Header Card
                CardContainer {
                    VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                        Text(college.name.isEmpty ? "College" : college.name)
                            .font(AppTheme.Font.title)

                        if !college.state.isEmpty {
                            Label(college.state, systemImage: "mappin.and.ellipse")
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
                    StatTile(value: "\(college.seats)", label: "Seats", systemImage: "chair.fill", tint: AppTheme.Palette.info)
                    StatTile(value: "\(college.openingRank)", label: "Opening rank", systemImage: "arrow.up", tint: AppTheme.Palette.success)
                    StatTile(value: "\(college.closingRank)", label: "Closing rank", systemImage: "arrow.down", tint: AppTheme.Palette.warning)
                    StatTile(value: college.fees.isEmpty ? "—" : college.fees, label: "Fees", systemImage: "indianrupeesign", tint: AppTheme.Palette.accent)
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
                if let urlString = detailData?.website.isEmpty == false ? detailData?.website : college.website?.absoluteString,
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
            detailData = await CollegeHtmlRepository.shared.loadCollege(collegeName: college.name)
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
