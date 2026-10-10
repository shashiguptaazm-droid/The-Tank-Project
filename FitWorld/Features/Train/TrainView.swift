import SwiftUI

/// Train tab: all workouts and programs grouped by goal (§3/§6).
struct TrainView: View {
    @Environment(ContentStore.self) private var content

    var body: some View {
        NavigationStack {
            List {
                Section("Workouts") {
                    ForEach(content.workouts) { workout in
                        NavigationLink {
                            WorkoutDetailPreView(workout: workout)
                        } label: {
                            WorkoutRow(workout: workout)
                        }
                    }
                    if content.workouts.isEmpty {
                        Text("No workouts yet — seed content coming.")
                            .foregroundStyle(.secondary)
                    }
                }
                Section("Programs") {
                    ForEach(content.programs) { program in
                        NavigationLink {
                            ProgramDetailView(program: program)
                        } label: {
                            ProgramRow(program: program)
                        }
                    }
                    if content.programs.isEmpty {
                        Text("Programs arriving with the generator milestone.")
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .navigationTitle("Train")
        }
    }
}

struct WorkoutRow: View {
    let workout: Workout

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(workout.name).font(.body)
            Text("\(workout.sessionLengthMinutes) min · \(workout.level.displayName)")
                .font(.caption).foregroundStyle(.secondary)
        }
    }
}

struct ProgramRow: View {
    let program: Program

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(program.name).font(.body)
            Text("\(program.duration.dayCount) days · \(program.level.displayName) · \(program.trainingDaysPerWeek)/wk")
                .font(.caption).foregroundStyle(.secondary)
        }
    }
}
