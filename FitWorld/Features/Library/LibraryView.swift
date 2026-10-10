import SwiftUI

/// Exercise library: browse by muscle group, search, filter (§6 core).
struct LibraryView: View {
    @Environment(ContentStore.self) private var content
    @State private var filter = ContentStore.ExerciseFilter()

    var body: some View {
        NavigationStack {
            List {
                if filter.isEmpty {
                    muscleBrowser
                }
                resultsSection
            }
            .searchable(text: $filter.searchText, prompt: "Search exercises")
            .navigationTitle("Library")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    NavigationLink {
                        FilterSheet(filter: $filter)
                    } label: {
                        Image(systemName: filter.isEmpty ? "line.3.horizontal.circle" : "line.3.horizontal.circle.fill")
                    }
                }
            }
        }
    }

    @ViewBuilder
    private var muscleBrowser: some View {
        Section("Browse by muscle group") {
            let counts = content.muscleGroupCounts
            ForEach(MuscleGroup.allCases) { group in
                NavigationLink {
                    MuscleGroupListView(group: group)
                } label: {
                    HStack {
                        Image(systemName: group.systemImage)
                            .frame(width: 28)
                        Text(group.displayName)
                        Spacer()
                        Text("\(counts[group] ?? 0)")
                            .foregroundStyle(.secondary)
                            .font(.subheadline.monospacedDigit())
                    }
                }
            }
        }
    }

    private var matchingSearch: Bool { !filter.searchText.isEmpty }

    private var sectionTitle: String {
        let results = content.filteredExercises(filter)
        return (matchingSearch || !filter.isEmpty) ? "Results (\(results.count))" : "Popular"
    }

    @ViewBuilder
    private var resultsSection: some View {
        let results = content.filteredExercises(filter)
        Section(sectionTitle) {
            if results.isEmpty {
                Text(matchingSearch ? "No matches. Try another term." : "Start typing to search the library.")
                    .foregroundStyle(.secondary)
            }
            ForEach(results.prefix(30)) { exercise in
                NavigationLink {
                    ExerciseDetailView(exercise: exercise)
                } label: {
                    ExerciseRow(exercise: exercise)
                }
            }
            if results.count > 30 {
                Text("+ \(results.count - 30) more — refine your search")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
    }
}

// MARK: - Row

struct ExerciseRow: View {
    let exercise: Exercise

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(exercise.name)
                .font(.body)
            Text("\(exercise.difficulty.displayName) · \(exercise.equipmentSummary)")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }
}

// MARK: - Muscle-group drill-down

struct MuscleGroupListView: View {
    @Environment(ContentStore.self) private var content
    let group: MuscleGroup

    var body: some View {
        let matches = content.exercises.filter { ex in
            ex.primaryMuscles.contains(group) || ex.secondaryMuscles.contains(group)
        }
        List(matches) { exercise in
            NavigationLink {
                ExerciseDetailView(exercise: exercise)
            } label: {
                ExerciseRow(exercise: exercise)
            }
        }
        .navigationTitle(group.displayName)
        .navigationBarTitleDisplayMode(.inline)
    }
}

// MARK: - Filter sheet

struct FilterSheet: View {
    @Binding var filter: ContentStore.ExerciseFilter
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            Form {
                Picker("Level", selection: $filter.level) {
                    Text("Any").tag(DifficultyLevel?.none)
                    ForEach(DifficultyLevel.allCases) { level in
                        Text(level.displayName).tag(DifficultyLevel?.some(level))
                    }
                }
                Picker("Equipment", selection: $filter.equipment) {
                    Text("Any").tag(Equipment?.none)
                    ForEach(Equipment.allCases) { equipment in
                        Text(equipment.displayName).tag(Equipment?.some(equipment))
                    }
                }
                Picker("Max impact", selection: $filter.maxImpact) {
                    Text("Any").tag(ImpactLevel?.none)
                    ForEach(ImpactLevel.allCases, id: \.self) { impact in
                        Text(impact.rawValue.capitalized).tag(ImpactLevel?.some(impact))
                    }
                }
                Button("Clear filters") {
                    filter = ContentStore.ExerciseFilter()
                }
            }
            .navigationTitle("Filters")
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}
