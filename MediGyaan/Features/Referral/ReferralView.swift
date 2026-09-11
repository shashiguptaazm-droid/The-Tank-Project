import SwiftUI
import UIKit

/// Refer & earn. Ports `ReferralActivity`.
struct ReferralView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api

    @State private var state: LoadState<ReferralInfo> = .idle
    @State private var didCopy = false

    var body: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.lg) {
                switch state {
                case .idle, .loading:
                    LoadingStateView(message: "Loading your referral code…")
                        .frame(height: 200)

                case let .failed(message):
                    ErrorStateView(message: message) { Task { await load() } }

                case let .loaded(info):
                    codeCard(info)
                    statsRow(info)
                    shareActions(info)
                    howItWorks
                }
            }
            .padding(AppTheme.Spacing.md)
        }
        .screenBackground()
        .navigationTitle("Refer & earn")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
        .refreshable { await load() }
    }

    // MARK: - Sections

    private func codeCard(_ info: ReferralInfo) -> some View {
        CardContainer {
            VStack(spacing: AppTheme.Spacing.sm) {
                Image(systemName: "gift.fill")
                    .font(.system(size: 34))
                    .foregroundStyle(AppTheme.Palette.accent)

                Text("Your referral code")
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Palette.textSecondary)

                Text(info.code.isEmpty ? "—" : info.code)
                    .font(.system(size: 28, weight: .bold, design: .monospaced))
                    .foregroundStyle(AppTheme.Palette.primary)
                    .textSelection(.enabled)

                Button {
                    UIPasteboard.general.string = info.code
                    didCopy = true
                    Task {
                        try? await Task.sleep(nanoseconds: 1_800_000_000)
                        didCopy = false
                    }
                } label: {
                    Label(didCopy ? "Copied!" : "Copy code", systemImage: didCopy ? "checkmark" : "doc.on.doc")
                        .font(AppTheme.Font.caption.weight(.semibold))
                }
                .disabled(info.code.isEmpty)
            }
            .frame(maxWidth: .infinity)
        }
    }

    private func statsRow(_ info: ReferralInfo) -> some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            StatTile(
                value: "\(info.totalReferrals)",
                label: "Invited",
                systemImage: "person.2.fill",
                tint: AppTheme.Palette.info
            )
            StatTile(
                value: "\(info.successfulReferrals)",
                label: "Joined",
                systemImage: "checkmark.seal.fill",
                tint: AppTheme.Palette.success
            )
            StatTile(
                value: "\(info.pointsEarned)",
                label: "Points",
                systemImage: "star.fill",
                tint: AppTheme.Palette.warning
            )
        }
    }

    private func shareActions(_ info: ReferralInfo) -> some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            if let url = info.shareURL ?? shareURL(for: info) {
                ShareLink(
                    item: url,
                    subject: Text("Join me on MediGyaan"),
                    message: Text("Use my referral code \(info.code) to get started on MediGyaan.")
                ) {
                    Label("Share invite", systemImage: "square.and.arrow.up")
                        .font(AppTheme.Font.headline)
                        .frame(maxWidth: .infinity)
                        .frame(height: 50)
                        .background(
                            RoundedRectangle(cornerRadius: AppTheme.Radius.md)
                                .fill(AppTheme.Palette.primary)
                        )
                        .foregroundStyle(.white)
                }
            }
        }
    }

    private func shareURL(for info: ReferralInfo) -> URL? {
        guard !info.code.isEmpty else { return nil }
        return URL(string: "https://medigyaan.xyz/Neurons/referral.php?code=\(info.code)")
    }

    private var howItWorks: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            SectionHeader(title: "How it works")

            CardContainer(padding: 0) {
                VStack(alignment: .leading, spacing: 0) {
                    ForEach(Array(steps.enumerated()), id: \.offset) { index, step in
                        HStack(alignment: .top, spacing: AppTheme.Spacing.md) {
                            Text("\(index + 1)")
                                .font(.system(size: 13, weight: .bold))
                                .frame(width: 24, height: 24)
                                .background(Circle().fill(AppTheme.Palette.primary.opacity(0.15)))
                                .foregroundStyle(AppTheme.Palette.primary)

                            Text(step)
                                .font(AppTheme.Font.callout)
                                .foregroundStyle(AppTheme.Palette.textPrimary)
                                .fixedSize(horizontal: false, vertical: true)

                            Spacer()
                        }
                        .padding(AppTheme.Spacing.md)

                        if index < steps.count - 1 {
                            Divider().padding(.leading, 52)
                        }
                    }
                }
            }
        }
    }

    private var steps: [String] {
        [
            "Share your referral code with a friend.",
            "They sign up on MediGyaan using your code.",
            "You earn points as soon as they complete their first test.",
        ]
    }

    // MARK: - Networking

    @MainActor
    private func load() async {
        let userId = session.userId
        guard userId > 0 else { return }
        state = await LoadState.result { [api] in
            try await api.referral.summary(userId: userId)
        }
    }
}

#Preview {
    NavigationStack {
        ReferralView()
            .environmentObject(SessionStore())
            .environment(\.api, .live)
    }
}
