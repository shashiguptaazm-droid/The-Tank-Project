import SwiftUI

/// Full exercise page per master spec §5 (Line item template), Phase 1 subset:
/// demo, steps, form cues, breathing, mistakes, contraindications, guidance.
struct ExerciseDetailView: View {
    @Environment(ContentStore.self) private var content
    let exercise: Exercise

    @State private var gender: DemonstratorGender = .male
    @State private var demoView: DemoAsset.DemoView = .front
    @State private var playbackSpeed: Double = 1.0

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                demoHeader
                safetyBanner
                stepsSection
                guidanceSection
                mistakesSection
                contraindicationsSection
                variantSection
                reviewFooter
            }
            .padding()
        }
        .navigationTitle(exercise.name)
        .navigationBarTitleDisplayMode(.inline)
    }

    // MARK: Demo

    @ViewBuilder
    private var demoHeader: some View {
        VStack(alignment: .leading, spacing: 8) {
            LottieDemoPlayer(exercise: exercise,
                             gender: gender,
                             view: demoView,
                             speed: playbackSpeed)
                .frame(height: 260)
                .background(Color(.secondarySystemGroupedBackground))
                .clipShape(RoundedRectangle(cornerRadius: 20))

            // Demonstrator + angle + speed controls (§4 requirements)
            HStack {
                Picker("Demonstrator", selection: $gender) {
                    ForEach(DemonstratorGender.allCases) { g in
                        Text(g.displayName).tag(g)
                    }
                }
                .pickerStyle(.segmented)

                Picker("View", selection: $demoView) {
                    Text("Front").tag(DemoAsset.DemoView.front)
                    Text("Side").tag(DemoAsset.DemoView.side)
                    Text("Rear").tag(DemoAsset.DemoView.rear)
                }
                .pickerStyle(.menu)

                Menu {
                    ForEach([0.5, 0.75, 1.0, 1.5, 2.0], id: \.self) { speed in
                        Button("\(Int(speed * 100))%") { playbackSpeed = speed }
                    }
                } label: {
                    Label("\(Int(playbackSpeed * 100))%", systemImage: "speedometer")
                }
            }

            Text("\(exercise.musclesSummary) · \(exercise.equipmentSummary) · \(exercise.difficulty.displayName)")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
    }

    // MARK: Safety banner (always visible where instruction exists — §24)

    private var safetyBanner: some View {
        Label("Educational content. Stop if you feel sharp pain, dizziness or numbness, and seek professional advice for persistent or worsening symptoms.",
              systemImage: "cross.case.fill")
            .font(.footnote)
            .padding(10)
            .background(Color.orange.opacity(0.15))
            .clipShape(RoundedRectangle(cornerRadius: 10))
    }

    // MARK: Steps

    @ViewBuilder
    private var stepsSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Starting position").font(.headline)
            Text(exercise.startPosition).font(.subheadline)

            Text("Execution").font(.headline)
            ForEach(Array(exercise.steps.enumerated()), id: \.offset) { index, step in
                HStack(alignment: .top) {
                    Text("\(index + 1).").font(.subheadline.monospacedDigit().bold())
                    Text(step).font(.subheadline)
                }
            }

            Text("Breathing").font(.headline)
            Text(exercise.breathing).font(.subheadline)
        }
    }

    // MARK: Sets/reps per user's level

    @ViewBuilder
    private var guidanceSection: some View {
        let guidance = exercise.guidance(for: exercise.difficulty)
        VStack(alignment: .leading, spacing: 6) {
            Text("Sets & reps").font(.headline)
            if let guidance {
                Text("Sets: \(guidance.sets)")
                if let reps = guidance.repsDisplay { Text(reps) }
                Text("Rest: \(guidance.restSeconds)s")
                if let load = guidance.loadGuidance { Text(load).foregroundStyle(.secondary) }
            } else {
                Text("Guidance coming soon.").foregroundStyle(.secondary)
            }
        }
    }

    // MARK: Mistakes

    @ViewBuilder
    private var mistakesSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Common mistakes").font(.headline)
            ForEach(exercise.commonMistakes) { mistake in
                VStack(alignment: .leading, spacing: 2) {
                    Text("✗ \(mistake.mistake)").font(.subheadline)
                    Text("✓ \(mistake.correction)")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 3)
            }
        }
    }

    // MARK: Contraindications

    @ViewBuilder
    private var contraindicationsSection: some View {
        if !exercise.contraindications.isEmpty {
            VStack(alignment: .leading, spacing: 6) {
                Text("Check before doing").font(.headline)
                ForEach(exercise.contraindications, id: \.self) { note in
                    Label(note, systemImage: "exclamationmark.triangle")
                        .font(.subheadline)
                }
            }
            .padding(10)
            .background(Color.yellow.opacity(0.12))
            .clipShape(RoundedRectangle(cornerRadius: 10))
        }
    }

    // MARK: Variants and substitutions

    @ViewBuilder
    private var variantSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            if let easier = exercise.easierVariantSlug.flatMap({ content.exercise(slug: $0) }) {
                NavigationLink("Easier: \(easier.name)") {
                    ExerciseDetailView(exercise: easier)
                }
            }
            if let harder = exercise.harderVariantSlug.flatMap({ content.exercise(slug: $0) }) {
                NavigationLink("Harder: \(harder.name)") {
                    ExerciseDetailView(exercise: harder)
                }
            }
        }
        .font(.subheadline)
    }

    // MARK: Review status (governance requirement — visible to users, §16/§21)

    @ViewBuilder
    private var reviewFooter: some View {
        HStack(spacing: 12) {
            Image(systemName: "seal")
            VStack(alignment: .leading, spacing: 2) {
                Text("Status: \(exercise.reviewStatus.rawValue.capitalized)")
                    .font(.caption.bold())
                if let reviewer = exercise.reviewedBy {
                    Text("Reviewed by \(reviewer)").font(.caption)
                }
                if let date = exercise.reviewDate {
                    Text(date, style: .date).font(.caption)
                }
            }
            Spacer()
        }
        .font(.caption)
        .foregroundStyle(.secondary)
        .padding(.top, 8)
    }
}
