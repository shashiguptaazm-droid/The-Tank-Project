import SwiftUI

/// Preview of a workout before starting it (blocks list, length, level).
struct WorkoutDetailPreView: View {
    @Environment(ContentStore.self) private var content
    let workout: Workout

    var body: some View {
        List {
            Section {
                ForEach(workout.blocks) { block in
                    VStack(alignment: .leading, spacing: 2) {
                        Text(content.exercise(slug: block.exerciseSlug)?.name
                             ?? block.exerciseSlug)
                            .font(.subheadline)
                        Text(block.targetDisplay)
                            .font(.caption.monospacedDigit())
                            .foregroundStyle(.secondary)
                        if let notes = block.notes {
                            Text(notes).font(.caption2).foregroundStyle(.tertiary)
                        }
                    }
                }
            } header: {
                Text("\(workout.blocks.count) exercises · ~\(workout.sessionLengthMinutes) min")
            }
            Section {
                NavigationLink("Start workout") {
                    WorkoutPlayerView(workout: workout)
                }
                .buttonStyle(.plain)
            }
        }
        .navigationTitle(workout.name)
        .navigationBarTitleDisplayMode(.inline)
    }
}

/// Program calendar (§6): day-by-day listing by week, rest days + deloads shown.
struct ProgramDetailView: View {
    @Environment(ContentStore.self) private var content
    let program: Program

    var body: some View {
        List {
            ForEach(program.weeks, id: \.weekIndex) { week in
                Section(week.isDeload
                        ? "Week \(week.weekIndex) (deload)"
                        : "Week \(week.weekIndex)") {
                    ForEach(week.days) { day in
                        HStack {
                            Text("Day \(day.dayIndex)")
                            Spacer()
                            if day.isRestDay {
                                Text("Rest").foregroundStyle(.secondary)
                            } else if let workout = content.workout(slug: day.workoutSlug!) {
                                NavigationLink(workout.name) {
                                    WorkoutDetailPreView(workout: workout)
                                }
                            } else {
                                Text(day.workoutSlug ?? "TBD")
                                    .foregroundStyle(.tertiary)
                            }
                        }
                        .font(.subheadline)
                    }
                }
            }
            Section {
                Text(program.progressionRules)
                    .font(.footnote).foregroundStyle(.secondary)
            } header: {
                Text("Progression")
            }
        }
        .navigationTitle(program.name)
        .navigationBarTitleDisplayMode(.inline)
    }
}
