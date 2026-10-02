import SwiftUI

/// Full 3D Guardian Showcase replicating Android's `GuardianShowcaseActivity.kt`.
/// Features:
/// - Horizontal Hero Selection Carousel / Reel
/// - Interactive Pedestal View with Archetype Glow & 3D Model GLB badge
/// - 4-Slot Tactical Power System (Intel, Strike, Defense, Surge) with Cyan/Crimson/Green/Gold tabs
/// - Tactical Dynamics Detail Card with Cooldowns, Charges, and Live Scan Insights
/// - Full Story / Origin Lore Sheet with Clinical Philosophy & High-Yield Mnemonics
/// - Equip & Unlock Status persistence across UserDefaults
struct GuardianShowcaseView: View {

    @Environment(\.dismiss) private var dismiss
    @AppStorage("selected_avatar_id") private var selectedAvatarId: Int = 1
    @AppStorage("selected_avatar_name") private var selectedAvatarName: String = "Mantis • Zerek"
    @AppStorage("selected_avatar_title") private var selectedAvatarTitle: String = "The Mantis • Zerek (ER Trauma)"

    var initialWarriorId: Int? = nil

    @State private var currentWarriorIndex: Int = 0
    @State private var selectedPowerSlot: Int = 2 // 0: Intel, 1: Strike, 2: Defense, 3: Surge
    @State private var showingStorySheet: Bool = false
    @State private var showEquippedToast: Bool = false

    private var allWarriors: [Warrior] {
        Warrior.allWarriors
    }

    private var currentWarrior: Warrior {
        if currentWarriorIndex >= 0 && currentWarriorIndex < allWarriors.count {
            return allWarriors[currentWarriorIndex]
        }
        return allWarriors[0]
    }

    private var currentHeroKit: GuardianHeroKit? {
        let avatarIdx = GuardianRegistry.avatarIndex(for: currentWarrior.id)
        return GuardianRegistry.getHeroKit(for: avatarIdx)
    }

    private var selectedPower: GuardianPower? {
        guard let kit = currentHeroKit else { return nil }
        switch selectedPowerSlot {
        case 0: return kit.intelPower
        case 1: return kit.strikePower
        case 2: return kit.defensePower
        case 3: return kit.surgePower
        default: return kit.defensePower
        }
    }

    var body: some View {
        ZStack {
            // Dark Atmospheric Canvas
            AppTheme.Palette.surface.ignoresSafeArea()

            VStack(spacing: 0) {
                // Top Custom Navigation Bar
                headerBar

                ScrollView(showsIndicators: false) {
                    VStack(spacing: AppTheme.Spacing.md) {
                        // Character Title & Faction Banner
                        characterHeaderSection

                        // Central Hero Showcase Card (Pedestal + Avatar Art + 3D Badge)
                        heroPedestalCard

                        // 4-Slot Tactical Power Bar
                        tacticalPowerSelector

                        // Tactical Dynamics Detail Card
                        tacticalDetailCard

                        // Lore & Mastery Story Button
                        loreStoryBanner

                        // Bottom Reel Carousel of All 27 Warriors
                        guardianReelSection
                    }
                    .padding(.horizontal, AppTheme.Spacing.md)
                    .padding(.bottom, 90)
                }

                // Sticky Bottom Action Bar (Equip / Active)
                bottomActionBar
            }

            // Equipped Toast Overlay
            if showEquippedToast {
                VStack {
                    Spacer()
                    HStack(spacing: 8) {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundStyle(Color(hex: "#00E676"))
                        Text("Equipped \(currentWarrior.name) as Companion")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundStyle(Color.white)
                    }
                    .padding(.horizontal, 20)
                    .padding(.vertical, 12)
                    .background(
                        Capsule()
                            .fill(Color(hex: "#0C2036"))
                            .overlay(Capsule().stroke(Color(hex: "#00E5FF"), lineWidth: 1.5))
                    )
                    .padding(.bottom, 100)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
                }
            }
        }
        .navigationBarHidden(true)
        .onAppear {
            if let initialId = initialWarriorId,
               let idx = allWarriors.firstIndex(where: { $0.id == initialId }) {
                currentWarriorIndex = idx
            } else if let idx = allWarriors.firstIndex(where: { $0.id == selectedAvatarId }) {
                currentWarriorIndex = idx
            }
        }
        .sheet(isPresented: $showingStorySheet) {
            if let story = currentHeroKit?.story {
                GuardianStorySheet(warrior: currentWarrior, story: story)
            }
        }
    }

    // MARK: - Header Bar

    private var headerBar: some View {
        HStack {
            Button {
                dismiss()
            } label: {
                Image(systemName: "chevron.left")
                    .font(.system(size: 18, weight: .bold))
                    .foregroundStyle(AppTheme.Ink.teal)
                    .frame(width: 44, height: 44)
                    .background(Circle().fill(Color(hex: "#101D33")))
            }

            Spacer()

            VStack(spacing: 2) {
                Text("GUARDIAN SHOWCASE")
                    .font(.system(size: 13, weight: .black))
                    .tracking(2.0)
                    .foregroundStyle(AppTheme.Ink.gold)

                Text("TACTICAL ARSENAL & DYNAMICS")
                    .font(.system(size: 9, weight: .heavy))
                    .tracking(1.2)
                    .foregroundStyle(AppTheme.Ink.teal)
            }

            Spacer()

            // Quick Cycle Arrow buttons
            HStack(spacing: 4) {
                Button {
                    cycleHero(step: -1)
                } label: {
                    Image(systemName: "arrow.left")
                        .font(.system(size: 13, weight: .bold))
                        .foregroundStyle(Color.white)
                        .frame(width: 32, height: 32)
                        .background(Circle().fill(Color(hex: "#101D33")))
                }

                Button {
                    cycleHero(step: 1)
                } label: {
                    Image(systemName: "arrow.right")
                        .font(.system(size: 13, weight: .bold))
                        .foregroundStyle(Color.white)
                        .frame(width: 32, height: 32)
                        .background(Circle().fill(Color(hex: "#101D33")))
                }
            }
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.top, 8)
        .padding(.bottom, 6)
    }

    // MARK: - Character Header Section

    private var characterHeaderSection: some View {
        VStack(spacing: 4) {
            HStack(spacing: 8) {
                Text("\(currentWarrior.name.uppercased()) • THE \(currentWarrior.animal.uppercased())")
                    .font(.system(size: 18, weight: .black))
                    .foregroundStyle(Color.white)

                if let faction = currentHeroKit?.faction {
                    Text("\(faction.iconEmoji) \(faction.displayName)")
                        .font(.system(size: 10, weight: .heavy))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(Capsule().fill(faction.badgeColor.opacity(0.2)))
                        .overlay(Capsule().stroke(faction.badgeColor, lineWidth: 1))
                        .foregroundStyle(faction.badgeColor)
                }
            }

            Text("\(currentWarrior.title) • \(currentWarrior.archetype.rawValue.uppercased())")
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(currentWarrior.glowColor)

            Text("\"\(currentWarrior.catchphrase)\"")
                .font(.system(size: 11, weight: .medium, design: .serif))
                .italic()
                .foregroundStyle(AppTheme.Palette.textSecondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 16)
                .padding(.top, 2)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 6)
    }

    // MARK: - Central Hero Showcase Card

    private var heroPedestalCard: some View {
        ZStack {
            // Glow Pedestal Ring
            RoundedRectangle(cornerRadius: 22, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [Color(hex: "#0A1324"), Color(hex: "#050914")],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 22, style: .continuous)
                        .stroke(
                            LinearGradient(
                                colors: [currentWarrior.glowColor, currentWarrior.glowColor.opacity(0.15)],
                                startPoint: .top,
                                endPoint: .bottom
                            ),
                            lineWidth: 1.5
                        )
                )

            VStack(spacing: 8) {
                // Top status row inside card
                HStack {
                    if let glb = currentWarrior.glbModelName {
                        HStack(spacing: 5) {
                            Image(systemName: "cube.fill")
                                .font(.system(size: 10))
                            Text("3D GLB (\(glb))")
                                .font(.system(size: 10, weight: .bold))
                        }
                        .foregroundStyle(currentWarrior.glowColor)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 4)
                        .background(Capsule().fill(currentWarrior.glowColor.opacity(0.16)))
                    } else {
                        HStack(spacing: 5) {
                            Image(systemName: "sparkles")
                                .font(.system(size: 10))
                            Text("APEX WARRIOR")
                                .font(.system(size: 10, weight: .bold))
                        }
                        .foregroundStyle(AppTheme.Ink.gold)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 4)
                        .background(Capsule().fill(AppTheme.Ink.gold.opacity(0.16)))
                    }

                    Spacer()

                    if currentWarrior.id == selectedAvatarId {
                        HStack(spacing: 4) {
                            Circle().fill(Color(hex: "#00E676")).frame(width: 7, height: 7)
                            Text("EQUIPPED")
                                .font(.system(size: 10, weight: .heavy))
                                .foregroundStyle(Color(hex: "#00E676"))
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 4)
                        .background(Capsule().fill(Color(hex: "#00E676").opacity(0.14)))
                    }
                }
                .padding(.horizontal, 16)
                .padding(.top, 14)

                // Avatar Graphic with Pedestal Glow
                ZStack {
                    Circle()
                        .fill(
                            RadialGradient(
                                gradient: Gradient(colors: [currentWarrior.glowColor.opacity(0.35), Color.clear]),
                                center: .center,
                                startRadius: 10,
                                endRadius: 110
                            )
                        )
                        .frame(width: 190, height: 190)

                    Circle()
                        .stroke(currentWarrior.glowColor.opacity(0.6), lineWidth: 2.5)
                        .frame(width: 140, height: 140)

                    Image(currentWarrior.avatarImageName)
                        .resizable()
                        .scaledToFit()
                        .frame(width: 124, height: 124)
                        .clipShape(Circle())
                        .shadow(color: currentWarrior.glowColor.opacity(0.8), radius: 14)
                }
                .padding(.vertical, 4)

                // Combat Attributes Gauges
                HStack(spacing: 12) {
                    attributeBadge(label: "VIT", value: currentWarrior.vitality, color: Color(hex: "#00E676"))
                    attributeBadge(label: "ATK", value: currentWarrior.assault, color: Color(hex: "#FF5252"))
                    attributeBadge(label: "DEF", value: currentWarrior.defense, color: Color(hex: "#00E5FF"))
                    attributeBadge(label: "CTRL", value: currentWarrior.control, color: Color(hex: "#E040FB"))
                    attributeBadge(label: "SPD", value: currentWarrior.speed, color: Color(hex: "#FFD700"))
                }
                .padding(.horizontal, 16)
                .padding(.bottom, 14)
            }
        }
        .frame(height: 270)
    }

    private func attributeBadge(label: String, value: Int, color: Color) -> some View {
        VStack(spacing: 2) {
            Text(label)
                .font(.system(size: 9, weight: .heavy))
                .foregroundStyle(AppTheme.Palette.textSecondary)
            Text("\(value)")
                .font(.system(size: 13, weight: .black))
                .foregroundStyle(color)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 4)
        .background(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .fill(Color(hex: "#0E182A"))
        )
    }

    // MARK: - 4-Slot Tactical Power Bar

    private var tacticalPowerSelector: some View {
        guard let kit = currentHeroKit else { return AnyView(EmptyView()) }

        let slots: [(index: Int, name: String, colorHex: String, power: GuardianPower, defaultTitle: String)] = [
            (0, kit.intelPower.shortLabel, "#00E5FF", kit.intelPower, "INTEL"),
            (1, kit.strikePower.shortLabel, "#FF3D5A", kit.strikePower, "STRIKE"),
            (2, kit.defensePower.shortLabel, "#00E676", kit.defensePower, "DEFENSE"),
            (3, kit.surgePower.shortLabel, "#FFD700", kit.surgePower, "SURGE")
        ]

        return AnyView(
            VStack(alignment: .leading, spacing: 6) {
                Text("TACTICAL ARSENAL (4 SLOTS)")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(AppTheme.Palette.textSecondary)

                HStack(spacing: 8) {
                    ForEach(slots, id: \.index) { item in
                        let isSelected = selectedPowerSlot == item.index
                        let themeColor = Color(hex: item.colorHex)

                        Button {
                            selectedPowerSlot = item.index
                        } label: {
                            VStack(spacing: 4) {
                                Image(systemName: item.power.systemIconName)
                                    .font(.system(size: 16, weight: .bold))
                                    .foregroundStyle(isSelected ? Color(hex: "#050816") : themeColor)

                                Text(item.name.uppercased())
                                    .font(.system(size: 11, weight: .heavy))
                                    .foregroundStyle(isSelected ? Color(hex: "#050816") : Color.white)
                                    .lineLimit(1)

                                Text(item.defaultTitle)
                                    .font(.system(size: 8, weight: .bold))
                                    .foregroundStyle(isSelected ? Color(hex: "#050816").opacity(0.8) : themeColor)
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 8)
                            .background(
                                RoundedRectangle(cornerRadius: 12, style: .continuous)
                                    .fill(isSelected ? themeColor : Color(hex: "#0E182A"))
                            )
                            .overlay(
                                RoundedRectangle(cornerRadius: 12, style: .continuous)
                                    .stroke(isSelected ? themeColor : themeColor.opacity(0.35), lineWidth: 1.5)
                            )
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        )
    }

    // MARK: - Tactical Dynamics Detail Card

    private var tacticalDetailCard: some View {
        guard let power = selectedPower else { return AnyView(EmptyView()) }
        let dynamicsText = GuardianRegistry.tacticalDynamicsText(for: power)

        return AnyView(
            VStack(alignment: .leading, spacing: 10) {
                // Header row of power details
                HStack(alignment: .top, spacing: 12) {
                    ZStack {
                        RoundedRectangle(cornerRadius: 12, style: .continuous)
                            .fill(power.powerCategory.color.opacity(0.18))
                            .frame(width: 44, height: 44)

                        Image(systemName: power.systemIconName)
                            .font(.system(size: 20, weight: .bold))
                            .foregroundStyle(power.powerCategory.color)
                    }

                    VStack(alignment: .leading, spacing: 3) {
                        HStack {
                            Text(power.powerName)
                                .font(.system(size: 15, weight: .bold))
                                .foregroundStyle(Color.white)

                            Spacer()

                            Text(power.powerCategory.displayName.uppercased())
                                .font(.system(size: 10, weight: .heavy))
                                .foregroundStyle(power.powerCategory.color)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 3)
                                .background(Capsule().fill(power.powerCategory.color.opacity(0.15)))
                        }

                        HStack(spacing: 12) {
                            Label(
                                power.chargesPerQuiz >= 99 ? "Passive" : "\(power.chargesPerQuiz) charges",
                                systemImage: "bolt.fill"
                            )
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundStyle(AppTheme.Ink.gold)

                            Label(
                                power.cooldownRounds == 0 ? "No cooldown" : "\(power.cooldownRounds) round CD",
                                systemImage: "clock.fill"
                            )
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                        }
                    }
                }

                // Power Description
                Text(power.description)
                    .font(.system(size: 12))
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                    .lineSpacing(2)

                Divider()
                    .background(Color.white.opacity(0.1))

                // Tactical Dynamics Scan Analysis Box
                HStack(alignment: .top, spacing: 8) {
                    Text(dynamicsText)
                        .font(.system(size: 11.5, weight: .medium))
                        .foregroundStyle(Color(hex: "#81D4FA"))
                        .lineSpacing(3)
                }
                .padding(10)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .fill(Color(hex: "#051329"))
                        .overlay(
                            RoundedRectangle(cornerRadius: 8, style: .continuous)
                                .stroke(Color(hex: "#00E5FF").opacity(0.3), lineWidth: 1)
                        )
                )
            }
            .padding(AppTheme.Spacing.md)
            .background(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .fill(Color(hex: "#0A1324"))
                    .overlay(
                        RoundedRectangle(cornerRadius: 16, style: .continuous)
                            .stroke(Color.white.opacity(0.1), lineWidth: 1)
                    )
            )
        )
    }

    // MARK: - Lore & Mastery Story Banner

    private var loreStoryBanner: some View {
        Button {
            showingStorySheet = true
        } label: {
            HStack(spacing: 12) {
                ZStack {
                    Circle()
                        .fill(AppTheme.Ink.gold.opacity(0.18))
                        .frame(width: 40, height: 40)
                    Image(systemName: "book.pages.fill")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundStyle(AppTheme.Ink.gold)
                }

                VStack(alignment: .leading, spacing: 2) {
                    Text("MASTER ORIGIN & LORE")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(Color.white)

                    Text("Chapter chronicles, clinical philosophy & mnemonics")
                        .font(.system(size: 10))
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(AppTheme.Ink.gold)
            }
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(Color(hex: "#0C1B2E"))
                    .overlay(
                        RoundedRectangle(cornerRadius: 14, style: .continuous)
                            .stroke(AppTheme.Ink.gold.opacity(0.4), lineWidth: 1)
                    )
            )
        }
        .buttonStyle(.plain)
    }

    // MARK: - Bottom Reel Carousel of All 27 Warriors

    private var guardianReelSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("GUARDIAN REEL (27 ANIMAL WARRIORS)")
                .font(.system(size: 11, weight: .bold))
                .foregroundStyle(AppTheme.Palette.textSecondary)

            ScrollViewReader { proxy in
                ScrollView(.horizontal, showsIndicators: false) {
                    LazyHStack(spacing: 12) {
                        ForEach(Array(allWarriors.enumerated()), id: \.element.id) { index, warrior in
                            let isSelected = index == currentWarriorIndex
                            let isEquipped = warrior.id == selectedAvatarId

                            Button {
                                withAnimation(.easeInOut(duration: 0.2)) {
                                    currentWarriorIndex = index
                                }
                            } label: {
                                VStack(spacing: 5) {
                                    ZStack {
                                        Circle()
                                            .fill(isSelected ? warrior.glowColor.opacity(0.3) : Color(hex: "#0E182A"))
                                            .frame(width: 58, height: 58)

                                        Circle()
                                            .stroke(
                                                isSelected ? warrior.glowColor : Color.white.opacity(0.15),
                                                lineWidth: isSelected ? 2.5 : 1
                                            )
                                            .frame(width: 58, height: 58)

                                        Image(warrior.avatarImageName)
                                            .resizable()
                                            .scaledToFit()
                                            .frame(width: 46, height: 46)
                                            .clipShape(Circle())

                                        if isEquipped {
                                            VStack {
                                                Spacer()
                                                HStack {
                                                    Spacer()
                                                    Circle()
                                                        .fill(Color(hex: "#00E676"))
                                                        .frame(width: 14, height: 14)
                                                        .overlay(
                                                            Image(systemName: "checkmark")
                                                                .font(.system(size: 8, weight: .heavy))
                                                                .foregroundStyle(Color.black)
                                                        )
                                                }
                                            }
                                            .frame(width: 58, height: 58)
                                        }
                                    }

                                    Text(warrior.name)
                                        .font(.system(size: 10, weight: isSelected ? .bold : .medium))
                                        .foregroundStyle(isSelected ? warrior.glowColor : Color.white)
                                        .lineLimit(1)
                                        .frame(width: 64)
                                }
                            }
                            .buttonStyle(.plain)
                            .id(index)
                        }
                    }
                    .padding(.horizontal, 4)
                    .padding(.vertical, 6)
                }
                .onChange(of: currentWarriorIndex) { newIdx in
                    withAnimation {
                        proxy.scrollTo(newIdx, anchor: .center)
                    }
                }
            }
        }
    }

    // MARK: - Sticky Bottom Action Bar

    private var bottomActionBar: some View {
        let isEquipped = currentWarrior.id == selectedAvatarId

        return VStack(spacing: 0) {
            Divider().background(Color.white.opacity(0.1))

            HStack(spacing: 12) {
                Button {
                    equipCurrentWarrior()
                } label: {
                    HStack(spacing: 8) {
                        Image(systemName: isEquipped ? "checkmark.circle.fill" : "shield.fill")
                            .font(.system(size: 15, weight: .bold))

                        Text(isEquipped ? "CURRENTLY EQUIPPED" : "EQUIP \(currentWarrior.name.uppercased())")
                            .font(.system(size: 14, weight: .black))
                            .tracking(1.0)
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 50)
                    .background(
                        RoundedRectangle(cornerRadius: 14, style: .continuous)
                            .fill(isEquipped ? Color(hex: "#10233D") : Color(hex: "#00E5FF"))
                    )
                    .foregroundStyle(isEquipped ? Color(hex: "#00E5FF") : Color(hex: "#050816"))
                    .overlay(
                        RoundedRectangle(cornerRadius: 14, style: .continuous)
                            .stroke(Color(hex: "#00E5FF"), lineWidth: isEquipped ? 1.5 : 0)
                    )
                }
                .disabled(isEquipped)
            }
            .padding(.horizontal, AppTheme.Spacing.md)
            .padding(.top, 10)
            .padding(.bottom, 24)
            .background(Color(hex: "#050914").ignoresSafeArea())
        }
    }

    // MARK: - Actions

    private func cycleHero(step: Int) {
        let total = allWarriors.count
        guard total > 0 else { return }
        withAnimation(.easeInOut(duration: 0.2)) {
            currentWarriorIndex = (currentWarriorIndex + step + total) % total
        }
    }

    private func equipCurrentWarrior() {
        selectedAvatarId = currentWarrior.id
        selectedAvatarName = currentWarrior.displayName
        selectedAvatarTitle = currentWarrior.title

        withAnimation {
            showEquippedToast = true
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
            withAnimation {
                showEquippedToast = false
            }
        }
    }
}

// MARK: - Guardian Story & Origin Lore Sheet

struct GuardianStorySheet: View {
    let warrior: Warrior
    let story: MasteryStory
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: AppTheme.Spacing.lg) {
                    // Header Card
                    VStack(alignment: .leading, spacing: 6) {
                        Text(story.chapterName.uppercased())
                            .font(.system(size: 11, weight: .black))
                            .tracking(1.5)
                            .foregroundStyle(warrior.glowColor)

                        Text(story.subjectTitle)
                            .font(.system(size: 20, weight: .bold))
                            .foregroundStyle(Color.white)

                        Text(warrior.displayName)
                            .font(.system(size: 13, weight: .semibold))
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                    }
                    .padding()
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(
                        RoundedRectangle(cornerRadius: 16, style: .continuous)
                            .fill(Color(hex: "#0C1B2E"))
                            .overlay(
                                RoundedRectangle(cornerRadius: 16, style: .continuous)
                                    .stroke(warrior.glowColor.opacity(0.35), lineWidth: 1)
                            )
                    )

                    // Narrative Section
                    VStack(alignment: .leading, spacing: 8) {
                        Text("ORIGIN CHRONICLE")
                            .font(.system(size: 11, weight: .heavy))
                            .foregroundStyle(AppTheme.Palette.textSecondary)

                        Text(story.narrative)
                            .font(.system(size: 14))
                            .foregroundStyle(AppTheme.Palette.textPrimary)
                            .lineSpacing(4)
                    }

                    // Clinical Philosophy Callout
                    VStack(alignment: .leading, spacing: 6) {
                        Label("CLINICAL PHILOSOPHY", systemImage: "cross.case.fill")
                            .font(.system(size: 11, weight: .heavy))
                            .foregroundStyle(Color(hex: "#00E676"))

                        Text("\"\(story.clinicalPhilosophy)\"")
                            .font(.system(size: 13, weight: .medium, design: .serif))
                            .italic()
                            .foregroundStyle(Color.white)
                            .lineSpacing(3)
                    }
                    .padding()
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(
                        RoundedRectangle(cornerRadius: 12, style: .continuous)
                            .fill(Color(hex: "#072016"))
                            .overlay(
                                RoundedRectangle(cornerRadius: 12, style: .continuous)
                                    .stroke(Color(hex: "#00E676").opacity(0.4), lineWidth: 1)
                            )
                    )

                    // High-Yield Mnemonic Callout
                    VStack(alignment: .leading, spacing: 6) {
                        Label("HIGH-YIELD MNEMONIC PEARL", systemImage: "sparkles")
                            .font(.system(size: 11, weight: .heavy))
                            .foregroundStyle(AppTheme.Ink.gold)

                        Text(story.highYieldMnemonic)
                            .font(.system(size: 13, weight: .semibold))
                            .foregroundStyle(Color.white)
                            .lineSpacing(3)
                    }
                    .padding()
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(
                        RoundedRectangle(cornerRadius: 12, style: .continuous)
                            .fill(Color(hex: "#261E08"))
                            .overlay(
                                RoundedRectangle(cornerRadius: 12, style: .continuous)
                                    .stroke(AppTheme.Ink.gold.opacity(0.5), lineWidth: 1)
                            )
                    )
                }
                .padding(AppTheme.Spacing.lg)
            }
            .background(AppTheme.Palette.surface.ignoresSafeArea())
            .navigationTitle("Master Origin Lore")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") {
                        dismiss()
                    }
                    .foregroundStyle(AppTheme.Ink.teal)
                }
            }
        }
    }
}
