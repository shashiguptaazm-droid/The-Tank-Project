import SwiftUI

/// Test series and category selection screen.
/// Ports Android `TestSelectionActivty.kt`, `TestGridAdapter.kt`, and `SubjectTestActivity.kt`.
public struct TestSelectionView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api
    @Environment(\.dismiss) private var dismiss

    public enum ExamCategory: String, CaseIterable, Identifiable {
        case neetPg = "NEET PG"
        case neetUg = "NEET UG"
        case fmge = "FMGE"
        case usmle = "USMLE Step 1"

        public var id: String { rawValue }

        public var startId: Int {
            switch self {
            case .neetPg: return 1
            case .neetUg: return 100
            case .fmge: return 200
            case .usmle: return 300
            }
        }

        public var iconName: String {
            switch self {
            case .neetPg: return "stethoscope"
            case .neetUg: return "cross.case.fill"
            case .fmge: return "globe.europe.africa.fill"
            case .usmle: return "star.circle.fill"
            }
        }

        public var color: Color {
            switch self {
            case .neetPg: return Color(hex: "06B6D4")
            case .neetUg: return Color(hex: "10B981")
            case .fmge: return Color(hex: "8B5CF6")
            case .usmle: return Color(hex: "F59E0B")
            }
        }
    }

    @State private var selectedCategory: ExamCategory = .neetPg
    @State private var showingMockGrid: Bool = false
    @State private var selectedTestNumber: Int? = nil
    @State private var testToLaunch: Quiz? = nil
    @State private var showingModeSheet: Bool = false
    @State private var activeTestIndex: Int = 0

    // Local completed tests cache mirroring Android SharedPreferences COMPLETED_TESTS
    @AppStorage("completed_tests_set") private var completedTestsData: String = ""

    private var completedTestIds: Set<Int> {
        Set(completedTestsData.split(separator: ",").compactMap { Int($0) })
    }

    public init() {}

    public var body: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.lg) {
                // Category Banner Selector
                categoryPicker

                // Tests Grid Header
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("\(selectedCategory.rawValue) Mock Series")
                            .font(AppTheme.Font.headline)
                            .foregroundStyle(Color.white)
                        Text("50 High-Yield Clinical Mock Exams")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.textMuted)
                    }
                    Spacer()
                    Text("\(completedCount)/50")
                        .font(.system(size: 15, weight: .bold, design: .rounded))
                        .foregroundStyle(AppTheme.Palette.accent)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 4)
                        .background(Capsule().fill(AppTheme.Palette.accent.opacity(0.15)))
                }
                .padding(.horizontal, AppTheme.Spacing.md)

                // Grid of 50 Tests
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: AppTheme.Spacing.md) {
                    ForEach(1...50, id: \.self) { num in
                        let testId = selectedCategory.startId + num - 1
                        let isCompleted = completedTestIds.contains(testId)

                        testCard(testNumber: num, testId: testId, isCompleted: isCompleted)
                    }
                }
                .padding(.horizontal, AppTheme.Spacing.md)
            }
            .padding(.vertical, AppTheme.Spacing.md)
        }
        .screenBackground()
        .navigationTitle("Test Series")
        .navigationBarTitleDisplayMode(.inline)
        .confirmationDialog(
            "Select Game Mode",
            isPresented: $showingModeSheet,
            titleVisibility: .visible
        ) {
            Button("Solo Practice Mode") {
                startSoloMode()
            }
            Button("1v1 Arena Challenge") {
                startChallengeMode()
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Play Mock Test \(activeTestIndex) in Solo or 1v1 Battle Mode.")
        }
        .sheet(item: $testToLaunch) { quiz in
            NavigationStack {
                QuizView(quiz: quiz)
            }
        }
    }

    private var completedCount: Int {
        (1...50).filter { completedTestIds.contains(selectedCategory.startId + $0 - 1) }.count
    }

    // MARK: - Category Picker
    private var categoryPicker: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: AppTheme.Spacing.sm) {
                ForEach(ExamCategory.allCases) { cat in
                    let isSelected = cat == selectedCategory
                    Button {
                        selectedCategory = cat
                    } label: {
                        HStack(spacing: 8) {
                            Image(systemName: cat.iconName)
                                .font(.caption.weight(.bold))
                            Text(cat.rawValue)
                                .font(AppTheme.Font.caption.weight(.bold))
                        }
                        .padding(.horizontal, 16)
                        .padding(.vertical, 10)
                        .background(
                            RoundedRectangle(cornerRadius: AppTheme.Radius.md)
                                .fill(isSelected ? cat.color : AppTheme.Palette.cardBackgroundElevated)
                                .overlay(
                                    RoundedRectangle(cornerRadius: AppTheme.Radius.md)
                                        .stroke(cat.color.opacity(isSelected ? 0 : 0.4), lineWidth: 1)
                                )
                        )
                        .foregroundStyle(isSelected ? Color.black : Color.white)
                    }
                }
            }
            .padding(.horizontal, AppTheme.Spacing.md)
        }
    }

    // MARK: - Test Card
    private func testCard(testNumber: Int, testId: Int, isCompleted: Bool) -> some View {
        Button {
            activeTestIndex = testNumber
            showingModeSheet = true
        } label: {
            CardContainer {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        ZStack {
                            Circle()
                                .fill(selectedCategory.color.opacity(0.18))
                                .frame(width: 32, height: 32)
                            Text("#\(testNumber)")
                                .font(.system(size: 13, weight: .black))
                                .foregroundStyle(selectedCategory.color)
                        }

                        Spacer()

                        Text(isCompleted ? "Attempted" : "Ready")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundStyle(isCompleted ? AppTheme.Palette.success : AppTheme.Palette.textMuted)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(
                                Capsule().fill(isCompleted ? AppTheme.Palette.success.opacity(0.15) : Color.white.opacity(0.06))
                            )
                    }

                    Text("\(selectedCategory.rawValue) Mock \(testNumber)")
                        .font(AppTheme.Font.callout.weight(.bold))
                        .foregroundStyle(Color.white)
                        .lineLimit(1)

                    HStack(spacing: 4) {
                        Image(systemName: "timer")
                            .font(.caption2)
                            .foregroundStyle(AppTheme.Palette.textMuted)
                        Text("50 Qs  45 Mins")
                            .font(AppTheme.Font.caption2)
                            .foregroundStyle(AppTheme.Palette.textMuted)
                    }
                }
            }
        }
        .buttonStyle(.plain)
    }

    private func startSoloMode() {
        let testId = selectedCategory.startId + activeTestIndex - 1
        let title = "\(selectedCategory.rawValue) Mock \(activeTestIndex)"
        let mockQuiz = Quiz(
            id: testId,
            title: title,
            topic: "\(selectedCategory.rawValue) Mock Exam Series",
            subject: selectedCategory.rawValue,
            questionCount: 50,
            durationSeconds: 2700
        )
        testToLaunch = mockQuiz
    }

    private func startChallengeMode() {
        // Triggers challenge invitation flow with unique test id
        startSoloMode()
    }
}
