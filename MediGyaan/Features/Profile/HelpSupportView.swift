import SwiftUI

/// Contact & Technical Support screen.
///
/// 1:1 port of Android `HelpActivity.kt`.
struct HelpSupportView: View {

    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.lg) {
                // Crest
                VStack(spacing: AppTheme.Spacing.sm) {
                    ZStack {
                        Circle()
                            .fill(AppTheme.Palette.primary.opacity(0.15))
                            .frame(width: 80, height: 80)

                        Image(systemName: "headphones.circle.fill")
                            .font(.system(size: 48))
                            .foregroundStyle(AppTheme.Palette.primary)
                    }

                    Text("MediGyaan Support")
                        .font(AppTheme.Font.title)
                        .foregroundStyle(AppTheme.Palette.textPrimary)

                    Text("We're here to help you conquer medical exams and arena battles.")
                        .font(AppTheme.Font.subheadline)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                        .multilineTextAlignment(.center)
                }
                .padding(.top, AppTheme.Spacing.md)

                // Channels Card
                CardContainer {
                    VStack(spacing: AppTheme.Spacing.md) {
                        // Email support
                        Link(destination: URL(string: "mailto:runescape007@ymail.com?subject=Query%20regarding%20EduLabs%20MediGyaan")!) {
                            HStack(spacing: AppTheme.Spacing.md) {
                                Image(systemName: "envelope.fill")
                                    .font(.title2)
                                    .foregroundStyle(AppTheme.Palette.primary)
                                    .frame(width: 32)

                                VStack(alignment: .leading, spacing: 2) {
                                    Text("Official Email Support")
                                        .font(AppTheme.Font.headline)
                                        .foregroundStyle(AppTheme.Palette.textPrimary)

                                    Text("runescape007@ymail.com")
                                        .font(AppTheme.Font.caption)
                                        .foregroundStyle(AppTheme.Palette.textSecondary)
                                }

                                Spacer()

                                Image(systemName: "arrow.up.right.square")
                                    .foregroundStyle(AppTheme.Palette.textMuted)
                            }
                        }

                        Divider().background(AppTheme.Palette.divider)

                        // Phone / WhatsApp support
                        Link(destination: URL(string: "tel:7860245819")!) {
                            HStack(spacing: AppTheme.Spacing.md) {
                                Image(systemName: "phone.fill")
                                    .font(.title2)
                                    .foregroundStyle(Color.green)
                                    .frame(width: 32)

                                VStack(alignment: .leading, spacing: 2) {
                                    Text("Direct Helpline")
                                        .font(AppTheme.Font.headline)
                                        .foregroundStyle(AppTheme.Palette.textPrimary)

                                    Text("+91 7860245819")
                                        .font(AppTheme.Font.caption)
                                        .foregroundStyle(AppTheme.Palette.textSecondary)
                                }

                                Spacer()

                                Image(systemName: "phone.arrow.up.right")
                                    .foregroundStyle(AppTheme.Palette.textMuted)
                            }
                        }
                    }
                    .padding(.vertical, AppTheme.Spacing.xs)
                }

                // FAQs / Tips
                CardContainer {
                    VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                        Label("Fast Troubleshooting", systemImage: "sparkles")
                            .font(AppTheme.Font.headline)
                            .foregroundStyle(AppTheme.Palette.warning)

                        Text("• Audio / Call Connection Issues: Verify microphone permission in iOS Settings > MediGyaan.")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.textSecondary)

                        Text("• Missing Arena Credits: Open Treasury & Store and tap your Daily Mystery Chest to sync online.")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.textSecondary)

                        Text("• Thesis Exporter Issues: Ensure chapter drafts have at least 100 words before compiling.")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                    }
                }
            }
            .padding(AppTheme.Spacing.md)
        }
        .screenBackground()
        .navigationTitle("Help & Support")
        .navigationBarTitleDisplayMode(.inline)
    }
}
