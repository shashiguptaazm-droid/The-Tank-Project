import SwiftUI

/// Exam goal selection and target preference manager.
///
/// 1:1 port of Android `GoalActivity.kt`.
/// Controls student target exam preference (e.g., NEET PG, NEET UG), persists
/// to `UserDefaults`, and provides status indications for upcoming exam modules.
struct GoalSelectionView: View {

    @Environment(\.dismiss) private var dismiss
    @AppStorage("selected_subject_preference") private var selectedGoal: String = "NEET PG"

    var onGoalSelected: ((String) -> Void)?

    struct ExamGoal: Identifiable {
        let id: String
        let title: String
        let subtitle: String
        let icon: String
        let isLocked: Bool
        let colorHex: String
    }

    private let goals: [ExamGoal] = [
        ExamGoal(id: "NEET PG", title: "NEET PG", subtitle: "MD / MS / DNB Post-Graduate Clinical & High-Yield", icon: "cross.case.fill", isLocked: false, colorHex: "#3B82F6"),
        ExamGoal(id: "NEET UG", title: "NEET UG", subtitle: "MBBS Undergraduate Entrance / Physics, Chem, Bio", icon: "graduationcap.fill", isLocked: false, colorHex: "#10B981"),
        ExamGoal(id: "BCBR", title: "BCBR", subtitle: "Basic Course in Biomedical Research (ICMR / NBE)", icon: "microscope.fill", isLocked: true, colorHex: "#8B5CF6"),
        ExamGoal(id: "UPSC", title: "UPSC CMS", subtitle: "Combined Medical Services / Central Health Service", icon: "building.columns.fill", isLocked: true, colorHex: "#F59E0B"),
        ExamGoal(id: "CAT", title: "CAT / Healthcare MBA", subtitle: "Hospital Administration & Management", icon: "chart.bar.xaxis", isLocked: true, colorHex: "#EC4899"),
        ExamGoal(id: "Law", title: "Medical Law & Ethics", subtitle: "Medico-Legal Forensics & Jurisprudence", icon: "scalemass.fill", isLocked: true, colorHex: "#6366F1"),
        ExamGoal(id: "Commerce", title: "Health Economics", subtitle: "Healthcare Finance & Hospital Budgeting", icon: "banknote.fill", isLocked: true, colorHex: "#14B8A6"),
        ExamGoal(id: "Computer Software", title: "Health Informatics", subtitle: "AI Diagnostics, HL7, Telemedicine & EMRs", icon: "cpu.fill", isLocked: true, colorHex: "#64748B")
    ]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.lg) {
                // Header
                VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
                    Text("Select Your Target Goal")
                        .font(AppTheme.Font.title)
                        .foregroundStyle(AppTheme.Palette.textPrimary)

                    Text("Tailor questions, arenas, warrior buffs, and predictors to your curriculum.")
                        .font(AppTheme.Font.callout)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }

                // Grid of Exam Cards
                VStack(spacing: AppTheme.Spacing.sm) {
                    ForEach(goals) { exam in
                        let isSelected = selectedGoal == exam.id
                        Button {
                            guard !exam.isLocked else { return }
                            selectedGoal = exam.id
                            onGoalSelected?(exam.id)
                            dismiss()
                        } label: {
                            CardContainer {
                                HStack(spacing: AppTheme.Spacing.md) {
                                    ZStack {
                                        RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                                            .fill(Color(hex: exam.colorHex).opacity(0.18))
                                            .frame(width: 48, height: 48)

                                        Image(systemName: exam.icon)
                                            .font(.system(size: 22))
                                            .foregroundStyle(Color(hex: exam.colorHex))
                                    }

                                    VStack(alignment: .leading, spacing: 3) {
                                        Text(exam.title)
                                            .font(AppTheme.Font.headline)
                                            .foregroundStyle(AppTheme.Palette.textPrimary)

                                        Text(exam.subtitle)
                                            .font(AppTheme.Font.caption)
                                            .foregroundStyle(AppTheme.Palette.textSecondary)
                                            .lineLimit(2)
                                            .multilineTextAlignment(.leading)
                                    }

                                    Spacer()

                                    if exam.isLocked {
                                        Text("COMING SOON")
                                            .font(.system(size: 9, weight: .bold))
                                            .foregroundStyle(Color.orange)
                                            .padding(.horizontal, 8)
                                            .padding(.vertical, 4)
                                            .background(Capsule().fill(Color.orange.opacity(0.15)))
                                    } else if isSelected {
                                        Image(systemName: "checkmark.circle.fill")
                                            .font(.system(size: 20))
                                            .foregroundStyle(AppTheme.Palette.primary)
                                    }
                                }
                                .opacity(exam.isLocked ? 0.55 : 1.0)
                            }
                        }
                        .disabled(exam.isLocked)
                    }
                }
            }
            .padding(AppTheme.Spacing.md)
        .onAppear {
            RemoteLogger.log(tag: "GoalSelection_Appear", message: "Exam Goal Selection screen viewed")
        }
        }
        .screenBackground()
        .navigationTitle("Goal Preference")
        .navigationBarTitleDisplayMode(.inline)
    }
}