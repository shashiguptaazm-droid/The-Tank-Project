import SwiftUI

// MARK: - Buttons

/// Ports `AppMaterialButton`: 24dp corner radius, primary tint, no caps.
struct PrimaryButton: View {
    let title: String
    var isLoading: Bool = false
    var isEnabled: Bool = true
    /// `SubmitButtonStyle` uses a 26dp radius and bold text.
    var isSubmit: Bool = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            ZStack {
                Text(title)
                    .font(isSubmit
                        ? .system(size: 15, weight: .bold)
                        : AppTheme.Font.body.weight(.medium))
                    .opacity(isLoading ? 0 : 1)
                if isLoading {
                    ProgressView().tint(AppTheme.Palette.onPrimary)
                }
            }
            .frame(maxWidth: .infinity)
            .frame(height: 48)
            .background(
                RoundedRectangle(
                    cornerRadius: isSubmit ? AppTheme.Radius.submitButton : AppTheme.Radius.button,
                    style: .continuous
                )
                .fill(isEnabled && !isLoading
                    ? AppTheme.Palette.primary
                    : AppTheme.Palette.primary.opacity(0.4))
            )
            .foregroundStyle(AppTheme.Palette.onPrimary)
        }
        .disabled(!isEnabled || isLoading)
        .accessibilityLabel(title)
    }
}

/// Outlined secondary action, matching the "Continue with Google" button.
struct SecondaryButton: View {
    let title: String
    var systemImage: String?
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: AppTheme.Spacing.sm) {
                if let systemImage { Image(systemName: systemImage) }
                Text(title).font(AppTheme.Font.body)
            }
            .frame(maxWidth: .infinity)
            .frame(height: 46)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.button, style: .continuous)
                    .stroke(AppTheme.Palette.outline, lineWidth: 1)
            )
            .foregroundStyle(AppTheme.Palette.primary)
        }
    }
}

/// Text-only button, matching `Widget.MaterialComponents.Button.TextButton`.
struct TextActionButton: View {
    let title: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Palette.primary)
        }
    }
}

// MARK: - Containers

/// Ports `AppMaterialCardView`: 18dp radius, 1dp `colorOutline` stroke,
/// surface fill, 2dp elevation.
struct CardContainer<Content: View>: View {
    var padding: CGFloat = AppTheme.Spacing.lg
    /// `DashboardCardStyle` uses a 20dp radius and 3dp elevation.
    var isDashboardCard: Bool = false
    @ViewBuilder var content: Content

    var body: some View {
        content
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(
                    cornerRadius: isDashboardCard
                        ? AppTheme.Radius.dashboardCard
                        : AppTheme.Radius.materialCard,
                    style: .continuous
                )
                .fill(AppTheme.Palette.cardBackground)
            )
            .overlay(
                RoundedRectangle(
                    cornerRadius: isDashboardCard
                        ? AppTheme.Radius.dashboardCard
                        : AppTheme.Radius.materialCard,
                    style: .continuous
                )
                .stroke(AppTheme.Palette.outline, lineWidth: 1)
            )
            .shadow(
                color: .black.opacity(0.06),
                radius: isDashboardCard ? AppTheme.Elevation.dashboardCard : AppTheme.Elevation.card,
                y: 1
            )
    }
}

/// A card painted with the dashboard's fixed dark "ink" palette.
struct InkCard<Content: View>: View {
    var fill: Color = AppTheme.Ink.surface
    var stroke: Color?
    var radius: CGFloat = AppTheme.Radius.materialCard
    var padding: CGFloat = AppTheme.Spacing.lg
    @ViewBuilder var content: Content

    var body: some View {
        content
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: radius, style: .continuous).fill(fill)
            )
            .overlay {
                if let stroke {
                    RoundedRectangle(cornerRadius: radius, style: .continuous)
                        .stroke(stroke, lineWidth: 1)
                }
            }
    }
}

/// Section heading. The Android dashboard writes these as
/// "Battle Modes ⚔️" at 18sp bold with a 12sp subtitle beneath.
struct SectionHeader: View {
    let title: String
    var subtitle: String?
    var actionTitle: String?
    var action: (() -> Void)?

    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(AppTheme.Font.section)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                if let subtitle {
                    Text(subtitle)
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }
            }
            Spacer()
            if let actionTitle, let action {
                Button(actionTitle, action: action)
                    .font(AppTheme.Font.captionBold)
            }
        }
    }
}

// MARK: - MCQ options

/// Ports `PrepLadderOptionStyle` + `option_selector_rounded`:
/// 12dp radius, 16dp padding, 16sp text, 12dp bottom margin.
///
/// * default — `?attr/colorSurface` fill with a 1dp `@color/divider` stroke
/// * checked — `@color/primary_variant` fill with a 2dp `@color/primary` stroke
struct OptionRow: View {
    let text: String
    let index: Int
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(alignment: .top, spacing: AppTheme.Spacing.sm) {
                Text(optionLetter)
                    .font(AppTheme.Font.body.weight(.bold))
                    .foregroundStyle(isSelected
                        ? AppTheme.Palette.onPrimary
                        : AppTheme.Palette.textSecondary)
                    .frame(width: 22, alignment: .leading)

                Text(text)
                    .font(AppTheme.Font.body)
                    .foregroundStyle(isSelected
                        ? AppTheme.Palette.onPrimary
                        : AppTheme.Palette.textPrimary)
                    .multilineTextAlignment(.leading)
                    .fixedSize(horizontal: false, vertical: true)

                Spacer(minLength: 0)
            }
            .padding(AppTheme.Spacing.lg)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.option, style: .continuous)
                    .fill(isSelected
                        ? AppTheme.Palette.primaryVariant
                        : AppTheme.Palette.optionBackground)
            )
            .overlay(
                RoundedRectangle(cornerRadius: AppTheme.Radius.option, style: .continuous)
                    .stroke(
                        isSelected ? AppTheme.Palette.primary : AppTheme.Palette.optionStroke,
                        lineWidth: isSelected ? 2 : 1
                    )
            )
        }
        .buttonStyle(.plain)
        .padding(.bottom, AppTheme.Spacing.optionGap)
    }

    /// A / B / C / D like the Android radiogroup.
    private var optionLetter: String {
        guard index >= 0, index < 26 else { return "•" }
        let scalar = UnicodeScalar(UInt8(65 + index))
        return String(Character(scalar))
    }
}

// MARK: - Statistics

/// Dashboard stat tile: 22sp rounded value above an 11sp label, painted on the
/// ink surface.
struct InkStatTile: View {
    let value: String
    let label: String

    var body: some View {
        VStack(spacing: 2) {
            Text(value)
                .font(AppTheme.Font.statValue)
                .foregroundStyle(AppTheme.Ink.textPrimary)
                .minimumScaleFactor(0.6)
                .lineLimit(1)
            Text(label)
                .font(AppTheme.Font.micro)
                .foregroundStyle(AppTheme.Ink.textSecondary)
                .lineLimit(1)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, AppTheme.Spacing.sm)
    }
}

/// Legacy coloured stat tile used on the Material-themed screens.
struct StatTile: View {
    let value: String
    let label: String
    var systemImage: String?
    var tint: Color = AppTheme.Palette.primary

    var body: some View {
        VStack(spacing: AppTheme.Spacing.xxs) {
            if let systemImage {
                Image(systemName: systemImage)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(tint)
            }
            Text(value)
                .font(AppTheme.Font.statValue)
                .foregroundStyle(AppTheme.Palette.textPrimary)
                .minimumScaleFactor(0.6)
                .lineLimit(1)
            Text(label)
                .font(AppTheme.Font.micro)
                .foregroundStyle(AppTheme.Palette.textSecondary)
                .multilineTextAlignment(.center)
                .lineLimit(2)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, AppTheme.Spacing.sm)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(tint.opacity(0.10))
        )
    }
}

/// Progress bar with caption (dashboard XP / accuracy rows).
struct ProgressRow: View {
    let title: String
    let value: Double
    var tint: Color = AppTheme.Palette.primary
    var caption: String?
    var track: Color = AppTheme.Palette.primary.opacity(0.15)

    var body: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
            HStack {
                Text(title)
                    .font(AppTheme.Font.callout)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                Spacer()
                Text(caption ?? String(format: "%.0f%%", min(max(value, 0), 1) * 100))
                    .font(AppTheme.Font.captionBold)
                    .foregroundStyle(AppTheme.Palette.textSecondary)
            }
            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    Capsule().fill(track)
                    Capsule()
                        .fill(tint)
                        .frame(width: max(0, min(1, value)) * geometry.size.width)
                }
            }
            .frame(height: 8)
        }
    }
}

// MARK: - Avatars

/// Circular avatar. Dashboard uses 76dp with a 2dp `#F4C95D` stroke.
struct AvatarView: View {
    let url: URL?
    let name: String
    var size: CGFloat = 44
    var strokeColor: Color = AppTheme.Palette.outline
    var strokeWidth: CGFloat = 1
    var backdrop: Color = AppTheme.Palette.primary.opacity(0.15)

    private var initials: String {
        let parts = name.split(separator: " ").prefix(2)
        return parts.compactMap { $0.first }.map(String.init).joined().uppercased()
    }

    var body: some View {
        Group {
            if let url {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case let .success(image):
                        image.resizable().scaledToFill()
                    default:
                        initialsView
                    }
                }
            } else {
                initialsView
            }
        }
        .frame(width: size, height: size)
        .clipShape(Circle())
        .overlay(Circle().stroke(strokeColor, lineWidth: strokeWidth))
    }

    private var initialsView: some View {
        ZStack {
            backdrop
            Text(initials.isEmpty ? "?" : initials)
                .font(.system(size: size * 0.38, weight: .semibold))
                .foregroundStyle(.white)
        }
    }
}

// MARK: - State placeholders

struct LoadingStateView: View {
    var message: String = "Loading…"

    var body: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            ProgressView()
            Text(message)
                .font(AppTheme.Font.caption)
                .foregroundStyle(AppTheme.Palette.textSecondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct ErrorStateView: View {
    let message: String
    var retry: (() -> Void)?

    var body: some View {
        VStack(spacing: AppTheme.Spacing.md) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 34))
                .foregroundStyle(AppTheme.Palette.warning)
            Text(message)
                .font(AppTheme.Font.callout)
                .foregroundStyle(AppTheme.Palette.textSecondary)
                .multilineTextAlignment(.center)
            if let retry {
                TextActionButton(title: "Try Again", action: retry)
            }
        }
        .padding(AppTheme.Spacing.xxl)
        .frame(maxWidth: .infinity)
    }
}

struct EmptyStateView: View {
    let title: String
    var message: String?
    var systemImage: String = "tray"
    var actionTitle: String?
    var action: (() -> Void)?

    var body: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            Image(systemName: systemImage)
                .font(.system(size: 38))
                .foregroundStyle(AppTheme.Palette.primary.opacity(0.5))
            Text(title).font(AppTheme.Font.cardTitle)
            if let message {
                Text(message)
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Palette.textSecondary)
                    .multilineTextAlignment(.center)
            }
            if let actionTitle, let action {
                TextActionButton(title: actionTitle, action: action)
                    .padding(.top, AppTheme.Spacing.xxs)
            }
        }
        .padding(AppTheme.Spacing.xxl)
        .frame(maxWidth: .infinity)
    }
}

/// Square quick-action tile used by the challenges hub and thesis tools.
struct QuickActionTile: View {
    let title: String
    let systemImage: String
    var tint: Color = AppTheme.Palette.primary

    var body: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            Image(systemName: systemImage)
                .font(.system(size: 22, weight: .semibold))
                .foregroundStyle(tint)

            Text(title)
                .font(AppTheme.Font.callout.weight(.semibold))
                .foregroundStyle(AppTheme.Palette.textPrimary)
                .multilineTextAlignment(.leading)
                .lineLimit(2)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .frame(height: 96)
        .padding(AppTheme.Spacing.lg)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.materialCard, style: .continuous)
                .fill(tint.opacity(0.10))
        )
    }
}

// MARK: - Badges

/// Small capsule badge (mode tags such as "RANKED", "FRIENDS").
struct TagBadge: View {
    let text: String
    var tint: Color = AppTheme.Palette.primary

    var body: some View {
        Text(text)
            .font(.system(size: 11, weight: .bold))
            .padding(.horizontal, AppTheme.Spacing.sm)
            .padding(.vertical, 3)
            .background(Capsule().fill(tint.opacity(0.18)))
            .foregroundStyle(tint)
    }
}

// MARK: - View modifiers

extension View {
    func screenBackground() -> some View {
        background(AppTheme.Palette.background.ignoresSafeArea())
    }

    /// Fixed dark backdrop for the ink-palette screens (dashboard et al).
    func inkBackground() -> some View {
        background(AppTheme.Ink.background.ignoresSafeArea())
    }

    func errorAlert(message: Binding<String?>) -> some View {
        alert(
            "Something went wrong",
            isPresented: Binding(
                get: { message.wrappedValue != nil },
                set: { if !$0 { message.wrappedValue = nil } }
            ),
            actions: {
                Button("OK", role: .cancel) { message.wrappedValue = nil }
            },
            message: {
                Text(message.wrappedValue ?? "")
            }
        )
    }
}

extension AppTheme.Spacing {
    /// 12dp — `PrepLadderOptionStyle` `layout_marginBottom`.
    static let optionGap: CGFloat = 12
}
