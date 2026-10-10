import SwiftUI

/// Home dashboard (master spec §3 core subset for Phase 1):
/// today's plan, continue-last, quick-start timer, streak, weekly calendar.
struct HomeView: View {
    @Environment(AppModel.self) private var app
    @Environment(ContentStore.self) private var content
    @Environment(ProfileStore.self) private var profile

    @State private var sessionStore: SessionStore?
    @State private var suggestedWorkout: Workout?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    if let workout = suggestedWorkout {
                        todayCard(workout)
                    } else {
                        emptyState
                    }

                    streakCard
                    weeklyCalendarCard
                    quickStartCard
                }
                .padding()
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("FitWorld")
            .onAppear(perform: refresh)
        }
    }

    private func refresh() {
        if sessionStore == nil, let container = try? SessionStore.makeContainer() {
            sessionStore = SessionStore(container: container)
        }
        suggestedWorkout = RecommendationEngine.suggestWorkout(
            content: content, profile: profile.profile)
    }

    // MARK: Sections

    @ViewBuilder
    private func todayCard(_ workout: Workout) -> some View {
        NavigationLink(value: workout.slug) {
            VStack(alignment: .leading, spacing: 8) {
                Label("Today's workout", systemImage: "flame.fill")
                    .font(.footnote).foregroundStyle(.secondary)
                Text(workout.name).font(.title3.bold())
                Text("\(workout.sessionLengthMinutes) min · \(workout.level.displayName) · \(workout.blocks.count) exercises")
                    .font(.subheadline).foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .card()
        }
        .buttonStyle(.plain)
        .navigationDestination(for: String.self) { slug in
            if let workout = content.workout(slug: slug) {
                WorkoutPlayerView(workout: workout)
            } else if let exercise = content.exercise(slug: slug) {
                ExerciseDetailView(exercise: exercise)
            }
        }
    }

    @ViewBuilder
    private var streakCard: some View {
        if let store = sessionStore {
            HStack {
                Label("\(store.currentStreak)", systemImage: "calendar.badge.exclamationmark")
                    .font(.title3.bold())
                Text("day streak — showing up is what counts")
                    .font(.footnote).foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .card()
        }
    }

    @ViewBuilder
    private var weeklyCalendarCard: some View {
        HStack {
            ForEach(0..<7, id: \.self) { offset in
                let day = Calendar.current.date(byAdding: .day, value: offset - 3, to: Date()) ?? Date()
                let isActive = sessionStore.map { store in
                    store.daysActive.contains(CalendarDay(date: day))
                } ?? false
                VStack(spacing: 4) {
                    Text(day, style: .weekday).font(.caption2)
                    Circle()
                        .fill(isActive ? Color.accentColor : Color(.tertiarySystemFill))
                        .frame(width: 10, height: 10)
                }
                .frame(maxWidth: .infinity)
            }
        }
        .card()
    }

    private var quickStartCard: some View {
        NavigationLink {
            QuickTimerView()
        } label: {
            Label("Quick-start timer", systemImage: "timer")
                .font(.headline)
                .frame(maxWidth: .infinity)
                .card()
        }
        .buttonStyle(.plain)
    }

    private var emptyState: some View {
        VStack(spacing: 8) {
            Text("No workout suggested yet")
            Text("Finish onboarding or check the Library tab.")
                .font(.footnote).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .card()
    }
}
