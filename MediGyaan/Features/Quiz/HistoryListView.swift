import SwiftUI

/// Quiz & Battle history browser screen.
///
/// 1:1 port of Android `HistoryAdapter.kt` and `ChallengeListActivity` History mode.
struct HistoryListView: View {

    @ObservedObject private var historyManager = QuizHistoryManager.shared
    @State private var filterMode: String = "ALL"

    private let filterOptions = ["ALL", "PRACTICE", "CHALLENGE", "SINGLE_PLAYER"]

    private var filteredList: [QuizHistoryItem] {
        if filterMode == "ALL" { return historyManager.historyItems }
        return historyManager.historyItems.filter { $0.mode.caseInsensitiveCompare(filterMode) == .orderedSame }
    }

    var body: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.md) {
                // Filter chips
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: AppTheme.Spacing.xs) {
                        ForEach(filterOptions, id: \.self) { mode in
                            let isSelected = mode == filterMode
                            Button {
                                filterMode = mode
                            } label: {
                                Text(mode)
                                    .font(AppTheme.Font.caption.weight(.semibold))
                                    .padding(.horizontal, 14)
                                    .padding(.vertical, 7)
                                    .background(Capsule().fill(isSelected ? AppTheme.Palette.primary : AppTheme.Palette.cardBackgroundElevated))
                                    .foregroundStyle(isSelected ? Color.white : AppTheme.Palette.textSecondary)
                            }
                        }
                    }
                    .padding(.horizontal, AppTheme.Spacing.sm)
                }

                if filteredList.isEmpty {
                    VStack(spacing: AppTheme.Spacing.sm) {
                        Image(systemName: "clock.arrow.circlepath")
                            .font(.system(size: 48))
                            .foregroundStyle(AppTheme.Palette.textMuted)
                            .padding(.top, 40)

                        Text("No Session History Yet")
                            .font(AppTheme.Font.headline)
                            .foregroundStyle(AppTheme.Palette.textPrimary)

                        Text("Complete a practice quiz or arena battle to review past performance.")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, 30)
                    }
                } else {
                    LazyVStack(spacing: AppTheme.Spacing.sm) {
                        ForEach(filteredList) { item in
                            historyCard(item)
                        }
                    }
                }
            }
            .padding(AppTheme.Spacing.md)
        }
        .screenBackground()
        .navigationTitle("Attempt History")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func historyCard(_ item: QuizHistoryItem) -> some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
                HStack {
                    Text(item.mode.uppercased())
                        .font(.system(size: 10, weight: .black))
                        .foregroundStyle(badgeColor(item.mode))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(Capsule().fill(badgeColor(item.mode).opacity(0.18)))

                    Spacer()

                    Text(formattedDate(item.timestamp))
                        .font(AppTheme.Font.caption2)
                        .foregroundStyle(AppTheme.Palette.textMuted)
                }

                Text(item.title.isEmpty ? (item.topic.isEmpty ? "Clinical Review" : item.topic) : item.title)
                    .font(AppTheme.Font.headline)
                    .foregroundStyle(AppTheme.Palette.textPrimary)

                HStack {
                    HStack(spacing: 4) {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundStyle(AppTheme.Palette.success)
                            .font(.caption)
                        Text("\(item.correctAnswers) correct")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                    }

                    Spacer()

                    HStack(spacing: 4) {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundStyle(AppTheme.Palette.error)
                            .font(.caption)
                        Text("\(item.wrongAnswers) wrong")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                    }

                    Spacer()

                    Text("\(Int(item.percentage))%")
                        .font(.system(size: 16, weight: .black, design: .rounded))
                        .foregroundStyle(item.percentage >= 70 ? AppTheme.Palette.success : (item.percentage >= 50 ? AppTheme.Palette.warning : AppTheme.Palette.error))
                }
                .padding(.top, 2)
            }
        }
    }

    private func badgeColor(_ mode: String) -> Color {
        switch mode.uppercased() {
        case "CHALLENGE": return Color.orange
        case "SINGLE_PLAYER": return Color.purple
        case "FINAL_TEST": return Color.red
        default: return AppTheme.Palette.primary
        }
    }

    private func formattedDate(_ ts: Double) -> String {
        let date = Date(timeIntervalSince1970: ts)
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }
}
