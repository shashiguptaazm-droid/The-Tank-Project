import SwiftUI

/// Widget configuration and customization settings screen.
///
/// 1:1 port of Android `WidgetSettingsActivity.kt`.
/// Lets students select target medical exams, specify exam dates, preview the
/// home screen countdown widget, and choose themed wallpaper backgrounds.
struct WidgetSettingsView: View {

    @ObservedObject private var widgetManager = NeetWidgetManager.shared
    @Environment(\.dismiss) private var dismiss

    @State private var examName: String = "NEET PG"
    @State private var targetDate: Date = Date()
    @State private var selectedThemeIndex: Int = 0
    @State private var showSavedToast: Bool = false

    private let availableExams = ["NEET PG", "NEET UG", "UPSC CMS", "INICET", "FMGE"]
    private let themeNames = ["Deep Navy", "Surgical Teal", "Royal Gold", "Crimson Apex"]
    private let themeGradients = [
        [Color(hex: "#0F172A"), Color(hex: "#1E293B")],
        [Color(hex: "#064E3B"), Color(hex: "#047857")],
        [Color(hex: "#78350F"), Color(hex: "#B45309")],
        [Color(hex: "#881337"), Color(hex: "#BE123C")]
    ]

    var body: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.lg) {
                // Interactive Widget Live Preview
                widgetLivePreview

                // Exam Target Picker
                examSelectionCard

                // Date Picker Card
                datePickerCard

                // Theme Card
                themeSelectionCard

                // Save Action
                PrimaryButton(title: "Save & Update Widget", icon: "checkmark.circle.fill") {
                    let formatter = DateFormatter()
                    formatter.dateFormat = "yyyy-MM-dd"
                    let dateStr = formatter.string(from: targetDate)
                    widgetManager.saveSettings(name: examName, dateString: dateStr)
                    showSavedToast = true
                }
            }
            .padding(AppTheme.Spacing.md)
        }
        .screenBackground()
        .navigationTitle("Widget Customization")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            RemoteLogger.log(tag: "WidgetSettings_Open", message: "Widget Settings configuration opened")
            examName = widgetManager.examName
            let formatter = DateFormatter()
            formatter.dateFormat = "yyyy-MM-dd"
            if let d = formatter.date(from: widgetManager.examDateString) {
                targetDate = d
            }
        }
        .alert("Widget Updated!", isPresented: $showSavedToast) {
            Button("Done", role: .cancel) { dismiss() }
        } message: {
            Text("Home screen countdown widget has been refreshed with \(examName) target.")
        }
    }

    // MARK: - Live Preview Card

    private var widgetLivePreview: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                Text("HOME SCREEN PREVIEW")
                    .font(.system(size: 10, weight: .black, design: .monospaced))
                    .foregroundStyle(AppTheme.Palette.textMuted)

                // Simulated iOS Widget Box
                ZStack {
                    RoundedRectangle(cornerRadius: 18)
                        .fill(
                            LinearGradient(
                                colors: themeGradients[selectedThemeIndex],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .frame(height: 140)
                        .shadow(color: Color.black.opacity(0.3), radius: 8, y: 4)

                    HStack(spacing: AppTheme.Spacing.lg) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(examName.uppercased())
                                .font(.system(size: 14, weight: .black, design: .rounded))
                                .foregroundStyle(Color.yellow)

                            Text("COUNTDOWN")
                                .font(.system(size: 10, weight: .bold, design: .monospaced))
                                .foregroundStyle(Color.white.opacity(0.8))

                            Spacer()

                            HStack(spacing: 4) {
                                Image(systemName: "calendar")
                                    .font(.caption2)
                                Text(formattedExamDate(targetDate))
                                    .font(.system(size: 11, weight: .medium))
                            }
                            .foregroundStyle(Color.white.opacity(0.7))
                        }

                        Spacer()

                        VStack(alignment: .trailing, spacing: 0) {
                            Text("\(calculateDays())")
                                .font(.system(size: 48, weight: .black, design: .rounded))
                                .foregroundStyle(Color.white)

                            Text("DAYS LEFT")
                                .font(.system(size: 10, weight: .black, design: .monospaced))
                                .foregroundStyle(Color.yellow)
                        }
                    }
                    .padding(AppTheme.Spacing.lg)
                }
            }
        }
    }

    // MARK: - Exam Selection Card

    private var examSelectionCard: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                Label("Target Examination", systemImage: "graduationcap.fill")
                    .font(AppTheme.Font.headline)
                    .foregroundStyle(AppTheme.Palette.primary)

                Picker("Exam", selection: $examName) {
                    ForEach(availableExams, id: \.self) { exam in
                        Text(exam).tag(exam)
                    }
                }
                .pickerStyle(.segmented)
            }
        }
    }

    // MARK: - Date Picker Card

    private var datePickerCard: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                Label("Scheduled Exam Date", systemImage: "clock.fill")
                    .font(AppTheme.Font.headline)
                    .foregroundStyle(Color.orange)

                DatePicker("Exam Date", selection: $targetDate, displayedComponents: .date)
                    .datePickerStyle(.graphical)
                    .tint(AppTheme.Palette.primary)
            }
        }
    }

    // MARK: - Theme Card

    private var themeSelectionCard: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                Label("Widget Color Theme", systemImage: "paintpalette.fill")
                    .font(AppTheme.Font.headline)
                    .foregroundStyle(Color.purple)

                HStack(spacing: AppTheme.Spacing.md) {
                    ForEach(0..<themeNames.count, id: \.self) { index in
                        let isSelected = selectedThemeIndex == index
                        Button {
                            selectedThemeIndex = index
                        } label: {
                            VStack(spacing: 4) {
                                Circle()
                                    .fill(themeGradients[index].first!)
                                    .frame(width: 36, height: 36)
                                    .overlay(
                                        Circle().stroke(isSelected ? Color.white : Color.clear, lineWidth: 2)
                                    )

                                Text(themeNames[index])
                                    .font(.system(size: 9, weight: .bold))
                                    .foregroundStyle(isSelected ? Color.white : AppTheme.Palette.textMuted)
                            }
                        }
                        .frame(maxWidth: .infinity)
                    }
                }
            }
        }
    }

    private func calculateDays() -> Int {
        let cal = Calendar.current
        let diff = cal.dateComponents([.day], from: Date(), to: targetDate)
        return max(0, diff.day ?? 0)
    }

    private func formattedExamDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "dd MMM yyyy"
        return formatter.string(from: date)
    }
}
