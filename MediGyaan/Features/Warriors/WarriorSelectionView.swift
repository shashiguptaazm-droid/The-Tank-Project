import SwiftUI

/// Avatar Warrior Selection Screen, porting `AvatarSelectionActivity` and strictly representing
/// all 27 animal warriors from `character_spec/avatar_3d_generation_guide.md`.
struct WarriorSelectionView: View {

    @AppStorage("selected_avatar_id") private var selectedAvatarId: Int = 1
    @AppStorage("selected_avatar_name") private var selectedAvatarName: String = "Mantis • Zerek"
    @AppStorage("selected_avatar_title") private var selectedAvatarTitle: String = "The Mantis • Zerek (ER Trauma)"

    @State private var selectedFilter: Warrior.Archetype? = nil
    @State private var inspectingWarrior: Warrior? = nil
    @Environment(\.dismiss) private var dismiss

    private var filteredWarriors: [Warrior] {
        if let filter = selectedFilter {
            return Warrior.allWarriors.filter { $0.archetype == filter }
        }
        return Warrior.allWarriors
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.lg) {
                activeWarriorHeader

                NavigationLink {
                    GuardianShowcaseView(initialWarriorId: selectedAvatarId)
                } label: {
                    HStack(spacing: 12) {
                        ZStack {
                            Circle()
                                .fill(AppTheme.Ink.gold.opacity(0.2))
                                .frame(width: 44, height: 44)
                            Image(systemName: "cube.transparent.fill")
                                .font(.system(size: 20, weight: .bold))
                                .foregroundStyle(AppTheme.Ink.gold)
                        }

                        VStack(alignment: .leading, spacing: 2) {
                            HStack {
                                Text("3D GUARDIAN SHOWCASE")
                                    .font(.system(size: 13, weight: .heavy))
                                    .foregroundStyle(Color.white)
                                Spacer()
                                Text("INSPECT")
                                    .font(.system(size: 10, weight: .black))
                                    .foregroundStyle(AppTheme.Ink.teal)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 3)
                                    .background(Capsule().fill(AppTheme.Ink.teal.opacity(0.15)))
                            }

                            Text("Explore 4-Slot Tactical Arsenals, Live Scans & Origin Lore")
                                .font(.system(size: 11))
                                .foregroundStyle(AppTheme.Palette.textSecondary)
                        }
                    }
                    .padding(14)
                    .background(
                        RoundedRectangle(cornerRadius: 16, style: .continuous)
                            .fill(Color(hex: "#0A172C"))
                            .overlay(
                                RoundedRectangle(cornerRadius: 16, style: .continuous)
                                    .stroke(AppTheme.Ink.teal.opacity(0.5), lineWidth: 1.5)
                            )
                    )
                }
                .buttonStyle(.plain)

                archetypeFilterBar

                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: AppTheme.Spacing.md) {
                    ForEach(filteredWarriors) { warrior in
                        WarriorCard(
                            warrior: warrior,
                            isSelected: warrior.id == selectedAvatarId,
                            onSelect: {
                                selectWarrior(warrior)
                            },
                            onInspect: {
                                inspectingWarrior = warrior
                            }
                        )
                    }
                }
            }
            .padding(AppTheme.Spacing.lg)
        }
        .background(AppTheme.Palette.surface.ignoresSafeArea())
        .navigationTitle("Animal Avatar Warriors")
        .navigationBarTitleDisplayMode(.inline)
        .sheet(item: $inspectingWarrior) { warrior in
            WarriorDetailSheet(warrior: warrior, isSelected: warrior.id == selectedAvatarId) {
                selectWarrior(warrior)
                inspectingWarrior = nil
            }
        }
    }

    private var activeWarriorHeader: some View {
        let current = Warrior.allWarriors.first(where: { $0.id == selectedAvatarId }) ?? Warrior.allWarriors[0]

        return CardContainer {
            HStack(spacing: AppTheme.Spacing.md) {
                ZStack {
                    Circle()
                        .fill(current.glowColor.opacity(0.18))
                        .frame(width: 60, height: 60)

                    Circle()
                        .stroke(current.glowColor, lineWidth: 2)
                        .frame(width: 60, height: 60)

                    Image(current.avatarImageName)
                        .resizable()
                        .scaledToFit()
                        .frame(width: 48, height: 48)
                        .clipShape(Circle())
                }

                VStack(alignment: .leading, spacing: 3) {
                    Text("ACTIVE WARRIOR COMPANION")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundStyle(current.glowColor)

                    Text(current.displayName)
                        .font(AppTheme.Font.title3)
                        .foregroundStyle(AppTheme.Palette.textPrimary)

                    Text(current.specialty)
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }

                Spacer()
            }
        }
    }

    private var archetypeFilterBar: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: AppTheme.Spacing.sm) {
                FilterChip(
                    title: "All (27)",
                    isSelected: selectedFilter == nil,
                    tint: AppTheme.Palette.primary
                ) {
                    selectedFilter = nil
                }

                ForEach(Warrior.Archetype.allCases, id: \.self) { archetype in
                    FilterChip(
                        title: archetype.rawValue,
                        isSelected: selectedFilter == archetype,
                        tint: archetype.color
                    ) {
                        selectedFilter = archetype
                    }
                }
            }
            .padding(.vertical, 2)
        }
    }

    private func selectWarrior(_ warrior: Warrior) {
        selectedAvatarId = warrior.id
        selectedAvatarName = warrior.displayName
        selectedAvatarTitle = warrior.title
    }
}

/// Grid card for each animal avatar warrior.
struct WarriorCard: View {
    let warrior: Warrior
    let isSelected: Bool
    let onSelect: () -> Void
    let onInspect: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            HStack {
                Text(warrior.animal)
                    .font(AppTheme.Font.captionBold)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(Capsule().fill(warrior.archetype.color.opacity(0.18)))
                    .foregroundStyle(warrior.archetype.color)

                Spacer()

                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(AppTheme.Palette.primary)
                }
            }

            HStack(spacing: AppTheme.Spacing.sm) {
                ZStack {
                    Circle()
                        .fill(warrior.glowColor.opacity(0.18))
                        .frame(width: 44, height: 44)

                    Circle()
                        .stroke(warrior.glowColor, lineWidth: 1.5)
                        .frame(width: 44, height: 44)

                    Image(warrior.avatarImageName)
                        .resizable()
                        .scaledToFit()
                        .frame(width: 36, height: 36)
                        .clipShape(Circle())
                }

                VStack(alignment: .leading, spacing: 2) {
                    Text(warrior.name)
                        .font(AppTheme.Font.headline)
                        .foregroundStyle(AppTheme.Palette.textPrimary)

                    Text(warrior.specialty)
                        .font(.system(size: 12))
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }
            }

            Text("\"\(warrior.catchphrase)\"")
                .font(.system(size: 11, weight: .regular, design: .serif))
                .italic()
                .foregroundStyle(AppTheme.Palette.textSecondary)
                .lineLimit(2)
                .frame(minHeight: 30, alignment: .topLeading)

            // Stat bars mini preview
            VStack(spacing: 3) {
                StatMiniBar(label: "VIT", value: warrior.vitality, color: Color(hex: "#00E676"))
                StatMiniBar(label: "ATK", value: warrior.assault, color: Color(hex: "#FF5252"))
                StatMiniBar(label: "DEF", value: warrior.defense, color: Color(hex: "#00E5FF"))
            }

            HStack(spacing: 6) {
                Button("Info") {
                    onInspect()
                }
                .buttonStyle(.bordered)
                .font(.system(size: 12))
                .tint(AppTheme.Palette.textSecondary)

                Button(isSelected ? "Active" : "Equip") {
                    onSelect()
                }
                .buttonStyle(.borderedProminent)
                .font(.system(size: 12, weight: .semibold))
                .tint(isSelected ? AppTheme.Palette.primary : warrior.archetype.color)
            }
            .padding(.top, 4)
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                .fill(AppTheme.Palette.cardBackground)
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                        .stroke(isSelected ? AppTheme.Palette.primary : warrior.glowColor.opacity(0.25), lineWidth: isSelected ? 2 : 1)
                )
        )
    }
}

/// Mini stat gauge.
struct StatMiniBar: View {
    let label: String
    let value: Int
    let color: Color

    var body: some View {
        HStack(spacing: 4) {
            Text(label)
                .font(.system(size: 9, weight: .bold))
                .foregroundStyle(AppTheme.Palette.textSecondary)
                .frame(width: 22, alignment: .leading)

            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.gray.opacity(0.2))
                    Capsule().fill(color)
                        .frame(width: geo.size.width * CGFloat(value) / 10.0)
                }
            }
            .frame(height: 4)

            Text("\(value)")
                .font(.system(size: 9, weight: .bold))
                .foregroundStyle(AppTheme.Palette.textSecondary)
                .frame(width: 14, alignment: .trailing)
        }
    }
}

/// Detailed warrior profile and quest lore sheet.
struct WarriorDetailSheet: View {
    let warrior: Warrior
    let isSelected: Bool
    let onEquip: () -> Void

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: AppTheme.Spacing.lg) {
                    // Header card
                    CardContainer {
                        VStack(spacing: AppTheme.Spacing.sm) {
                            ZStack {
                                Circle()
                                    .fill(warrior.glowColor.opacity(0.2))
                                    .frame(width: 90, height: 90)

                                Circle()
                                    .stroke(warrior.glowColor, lineWidth: 3)
                                    .frame(width: 90, height: 90)

                                Image(warrior.avatarImageName)
                                    .resizable()
                                    .scaledToFit()
                                    .frame(width: 74, height: 74)
                                    .clipShape(Circle())
                            }

                            if let glb = warrior.glbModelName {
                                Label("3D Model Ready (\(glb))", systemImage: "cube.fill")
                                    .font(.system(size: 11, weight: .semibold))
                                    .foregroundStyle(warrior.glowColor)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 3)
                                    .background(Capsule().fill(warrior.glowColor.opacity(0.15)))
                            }

                            Text(warrior.displayName)
                                .font(AppTheme.Font.title2)
                                .foregroundStyle(AppTheme.Palette.textPrimary)

                            Text(warrior.specialty)
                                .font(AppTheme.Font.subheadline)
                                .foregroundStyle(warrior.archetype.color)

                            Text("\"\(warrior.catchphrase)\"")
                                .font(AppTheme.Font.callout)
                                .italic()
                                .multilineTextAlignment(.center)
                                .foregroundStyle(AppTheme.Palette.textSecondary)
                                .padding(.top, 4)
                        }
                        .frame(maxWidth: .infinity)
                    }

                    // Stats Breakdown
                    CardContainer {
                        VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                            Text("COMBAT ATTRIBUTES")
                                .font(AppTheme.Font.captionBold)
                                .foregroundStyle(AppTheme.Palette.textSecondary)

                            StatDetailRow(label: "Vitality (HP)", value: warrior.vitality, max: 10, color: Color(hex: "#00E676"))
                            StatDetailRow(label: "Assault (Damage)", value: warrior.assault, max: 10, color: Color(hex: "#FF5252"))
                            StatDetailRow(label: "Defense (Shield)", value: warrior.defense, max: 10, color: Color(hex: "#00E5FF"))
                            StatDetailRow(label: "Control (Disruption)", value: warrior.control, max: 10, color: Color(hex: "#E040FB"))
                            StatDetailRow(label: "Speed (Response)", value: warrior.speed, max: 10, color: Color(hex: "#FFD700"))
                        }
                    }

                    // Hero Quest & Plotline
                    CardContainer {
                        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                            Text("HERO QUEST & LORE")
                                .font(AppTheme.Font.captionBold)
                                .foregroundStyle(AppTheme.Palette.textSecondary)

                            Text(warrior.questTitle)
                                .font(AppTheme.Font.headline)
                                .foregroundStyle(warrior.glowColor)

                            Text(warrior.heroPlotline)
                                .font(AppTheme.Font.body)
                                .foregroundStyle(AppTheme.Palette.textPrimary)
                        }
                    }

                    NavigationLink {
                        GuardianShowcaseView(initialWarriorId: warrior.id)
                    } label: {
                        HStack {
                            Image(systemName: "cube.fill")
                            Text("Open in 3D Showcase")
                        }
                        .font(.system(size: 14, weight: .bold))
                        .foregroundStyle(Color.white)
                        .frame(maxWidth: .infinity)
                        .frame(height: 48)
                        .background(
                            RoundedRectangle(cornerRadius: 12, style: .continuous)
                                .fill(Color(hex: "#0A172C"))
                                .overlay(
                                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                                        .stroke(warrior.glowColor, lineWidth: 1.5)
                                )
                        )
                    }
                    .buttonStyle(.plain)

                    Button(isSelected ? "Equipped" : "Equip This Warrior") {
                        onEquip()
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(warrior.archetype.color)
                    .frame(maxWidth: .infinity)
                    .controlSize(.large)
                    .disabled(isSelected)
                }
                .padding(AppTheme.Spacing.lg)
            }
            .background(AppTheme.Palette.surface.ignoresSafeArea())
            .navigationTitle("Warrior Dossier")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

struct StatDetailRow: View {
    let label: String
    let value: Int
    let max: Int
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(label)
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                Spacer()
                Text("\(value) / \(max)")
                    .font(AppTheme.Font.captionBold)
                    .foregroundStyle(color)
            }

            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.gray.opacity(0.18))
                    Capsule().fill(color)
                        .frame(width: geo.size.width * CGFloat(value) / CGFloat(max))
                }
            }
            .frame(height: 8)
        }
    }
}

struct FilterChip: View {
    let title: String
    let isSelected: Bool
    let tint: Color
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 13, weight: isSelected ? .bold : .medium))
                .padding(.horizontal, 14)
                .padding(.vertical, 7)
                .background(
                    Capsule()
                        .fill(isSelected ? tint : AppTheme.Palette.cardBackground)
                )
                .foregroundStyle(isSelected ? Color.white : AppTheme.Palette.textPrimary)
                .overlay(
                    Capsule().stroke(isSelected ? tint : Color.gray.opacity(0.3), lineWidth: 1)
                )
        }
    }
}
