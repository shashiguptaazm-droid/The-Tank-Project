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

    private func predict() async {
        guard let score = Double(scoreText) else { return }
        let userId = session.userId
        await predictionState.load { [api] in
            try await api.predictor.predictRank(userId: userId, score: score)
        }

        if let prediction = predictionState.value {
            await collegesState.load { [api] in
                try await api.predictor.colleges(rank: prediction.predictedRank)
            }
        }
    }
}

/// A college row in the predictor results.
struct CollegeRow: View {
    let college: College

    var body: some View {
        CardContainer(padding: AppTheme.Spacing.sm) {
            HStack(spacing: AppTheme.Spacing.md) {
                Image(systemName: "building.columns.fill")
                    .font(.system(size: 18))
                    .foregroundStyle(AppTheme.Palette.primary)
                    .frame(width: 38, height: 38)
                    .background(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                            .fill(AppTheme.Palette.primary.opacity(0.12))
                    )

                VStack(alignment: .leading, spacing: 2) {
                    Text(college.name.isEmpty ? "College" : college.name)
                        .font(AppTheme.Font.callout.weight(.semibold))
                        .lineLimit(2)
                    if !college.state.isEmpty {
                        Text(college.state)
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                    }
                    if college.closingRank > 0 {
                        Text("Closing rank \(college.closingRank)")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                    }
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(AppTheme.Palette.textSecondary.opacity(0.6))
            }
        }
    }
}

/// Detailed college information. Ports `CollegeDetailActivity`.
struct CollegeDetailView: View {

    let college: College

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                CardContainer {
                    VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                        Text(college.name.isEmpty ? "College" : college.name)
                            .font(AppTheme.Font.title)

                        if !college.state.isEmpty {
                            Label(college.state, systemImage: "mappin.and.ellipse")
                                .font(AppTheme.Font.callout)
                                .foregroundStyle(AppTheme.Palette.textSecondary)
                        }
                    }
                }

                LazyVGrid(
                    columns: Array(repeating: GridItem(.flexible(), spacing: AppTheme.Spacing.sm), count: 2),
                    spacing: AppTheme.Spacing.sm
                ) {
                    StatTile(value: "\(college.seats)", label: "Seats", systemImage: "chair.fill", tint: AppTheme.Palette.info)
                    StatTile(value: "\(college.openingRank)", label: "Opening rank", systemImage: "arrow.up", tint: AppTheme.Palette.success)
                    StatTile(value: "\(college.closingRank)", label: "Closing rank", systemImage: "arrow.down", tint: AppTheme.Palette.warning)
                    StatTile(value: college.fees.isEmpty ? "—" : college.fees, label: "Fees", systemImage: "indianrupeesign", tint: AppTheme.Palette.accent)
                }

                if let website = college.website {
                    Link(destination: website) {
                        Label("Visit website", systemImage: "safari.fill")
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
        .navigationTitle("College")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    NavigationStack {
        PredictorView()
            .environmentObject(SessionStore())
            .environment(\.api, .live)
    }
}
