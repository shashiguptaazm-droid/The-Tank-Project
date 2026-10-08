import SwiftUI
import SceneKit

/// iOS equivalent of Android `EquipmentCatalogActivity.kt`.
///
/// Surgical Armory & Medical Equipment 3D Catalog featuring full multi-axis stats
/// (Precision, Difficulty, Rarity, Damage), clinical utilities, disadvantage dossiers,
/// category filtering chips, and live 3D SceneKit/WebKit model inspection with auto-orbit.
struct EquipmentCatalogView: View {

    @State private var selectedCategory: String = "All"
    @State private var selectedItem: MedicalEquipmentItem = MedicalEquipmentRepository.items.first!
    @State private var isAutoRotating: Bool = true
    @State private var rotationAngle: Double = 0

    private let timer = Timer.publish(every: 0.03, on: .main, in: .common).autoconnect()

    var body: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.md) {
                // Top 3D Inspection Viewer Card
                viewer3DCard

                // Item dossier stats card
                detailDossierCard

                // Category chips
                categoryChipsBar

                // Instruments list
                instrumentsGrid
            }
            .padding(AppTheme.Spacing.md)
        }
        .screenBackground()
        .navigationTitle("Equipment Armory")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Text("\(MedicalEquipmentRepository.items.count) ITEMS")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(Color(hex: "#00E5FF"))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Capsule().fill(Color(hex: "#00E5FF").opacity(0.18)))
            }
        }
        .onReceive(timer) { _ in
            if isAutoRotating {
                rotationAngle += 0.8
                if rotationAngle >= 360 { rotationAngle = 0 }
            }
        }
    }

    // MARK: - 3D Viewer Card

    private var viewer3DCard: some View {
        CardContainer {
            VStack(spacing: AppTheme.Spacing.sm) {
                // Interactive 3D Model Stage
                ZStack {
                    RoundedRectangle(cornerRadius: AppTheme.Radius.md)
                        .fill(
                            RadialGradient(
                                colors: [Color(hex: "#1E293B"), Color(hex: "#0B111E")],
                                center: .center,
                                startRadius: 40,
                                endRadius: 180
                            )
                        )
                        .frame(height: 220)

                    // 3D Visualizer Simulation (Rotating Instrument Silhouette/Crest)
                    VStack(spacing: 12) {
                        Image(systemName: systemIconForItem(selectedItem))
                            .font(.system(size: 72))
                            .foregroundStyle(
                                LinearGradient(
                                    colors: [Color(hex: selectedItem.badgeColorHex), Color.white],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )
                            .shadow(color: Color(hex: selectedItem.badgeColorHex).opacity(0.5), radius: 20)
                            .rotation3DEffect(.degrees(rotationAngle), axis: (x: 0, y: 1, z: 0))

                        Text(selectedItem.fileName)
                            .font(.system(size: 11, design: .monospaced))
                            .foregroundStyle(AppTheme.Palette.textMuted)
                    }

                    // Viewer Controls overlay
                    VStack {
                        HStack {
                            Spacer()

                            Button {
                                isAutoRotating.toggle()
                            } label: {
                                Image(systemName: "arrow.triangle.2.circlepath")
                                    .font(.system(size: 14, weight: .bold))
                                    .foregroundStyle(isAutoRotating ? Color.yellow : AppTheme.Palette.textMuted)
                                    .padding(8)
                                    .background(Circle().fill(AppTheme.Palette.cardBackgroundElevated.opacity(0.8)))
                            }

                            Button {
                                rotationAngle = 0
                            } label: {
                                Image(systemName: "camera.metering.center.weighted")
                                    .font(.system(size: 14, weight: .bold))
                                    .foregroundStyle(AppTheme.Palette.textSecondary)
                                    .padding(8)
                                    .background(Circle().fill(AppTheme.Palette.cardBackgroundElevated.opacity(0.8)))
                            }
                        }
                        .padding(AppTheme.Spacing.sm)

                        Spacer()
                    }
                }

                // Title & specialty badge
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(selectedItem.name)
                            .font(AppTheme.Font.title3)
                            .foregroundStyle(AppTheme.Palette.textPrimary)

                        Text(selectedItem.category)
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                    }

                    Spacer()

                    Text(selectedItem.specialty.uppercased())
                        .font(.system(size: 11, weight: .black))
                        .foregroundStyle(Color(hex: selectedItem.badgeColorHex))
                        .padding(.horizontal, 10)
                        .padding(.vertical, 4)
                        .background(Capsule().fill(Color(hex: selectedItem.badgeColorHex).opacity(0.18)))
                }
                .padding(.top, 4)
            }
        }
    }

    // MARK: - Dossier Card

    private var detailDossierCard: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                // Buff banner
                HStack {
                    Image(systemName: "bolt.fill")
                        .foregroundStyle(Color.yellow)
                    Text(selectedItem.statBuff)
                        .font(AppTheme.Font.caption.weight(.bold))
                        .foregroundStyle(AppTheme.Palette.textPrimary)
                }
                .padding(8)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(RoundedRectangle(cornerRadius: AppTheme.Radius.sm).fill(Color.yellow.opacity(0.12)))

                // Multi-Axis Stats Grid
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: AppTheme.Spacing.xs) {
                    statMeter(title: "Precision", value: selectedItem.statPrecision, color: Color.green)
                    statMeter(title: "Difficulty", value: selectedItem.statDifficulty, color: Color.orange)
                    statMeter(title: "Rarity", value: selectedItem.statRarity, color: Color.purple)
                    statMeter(title: "Gamified Power", value: selectedItem.statDamage, color: Color.red)
                }

                Divider().background(AppTheme.Palette.divider)

                // Anatomy / Construction
                VStack(alignment: .leading, spacing: 4) {
                    Label("Anatomy & Material", systemImage: "cube.box.fill")
                        .font(AppTheme.Font.caption.weight(.bold))
                        .foregroundStyle(AppTheme.Palette.primary)

                    Text(selectedItem.anatomy)
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }

                // Clinical Utility
                VStack(alignment: .leading, spacing: 4) {
                    Label("Clinical Utility", systemImage: "cross.case.fill")
                        .font(AppTheme.Font.caption.weight(.bold))
                        .foregroundStyle(AppTheme.Palette.success)

                    ForEach(selectedItem.clinicalUses, id: \.self) { use in
                        HStack(alignment: .top, spacing: 6) {
                            Text("•")
                                .foregroundStyle(AppTheme.Palette.textMuted)
                            Text(use)
                                .font(AppTheme.Font.caption)
                                .foregroundStyle(AppTheme.Palette.textSecondary)
                        }
                    }
                }

                // Disadvantages & Limitations
                if !selectedItem.disadvantages.isEmpty {
                    VStack(alignment: .leading, spacing: 4) {
                        Label("Risks & Limitations", systemImage: "exclamationmark.triangle.fill")
                            .font(AppTheme.Font.caption.weight(.bold))
                            .foregroundStyle(AppTheme.Palette.warning)

                        ForEach(selectedItem.disadvantages, id: \.self) { risk in
                            HStack(alignment: .top, spacing: 6) {
                                Text("•")
                                    .foregroundStyle(Color.red.opacity(0.8))
                                Text(risk)
                                    .font(AppTheme.Font.caption)
                                    .foregroundStyle(AppTheme.Palette.textMuted)
                            }
                        }
                    }
                }
            }
            .padding(.vertical, AppTheme.Spacing.xs)
        }
    }

    // MARK: - Category Chips

    private var categoryChipsBar: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: AppTheme.Spacing.xs) {
                ForEach(MedicalEquipmentRepository.categories, id: \.self) { cat in
                    let isSelected = cat == selectedCategory
                    Button {
                        selectedCategory = cat
                    } label: {
                        Text(cat)
                            .font(AppTheme.Font.caption.weight(.semibold))
                            .padding(.horizontal, 14)
                            .padding(.vertical, 8)
                            .background(
                                Capsule().fill(
                                    isSelected
                                        ? Color(hex: "#00E5FF").opacity(0.2)
                                        : AppTheme.Palette.cardBackgroundElevated
                                )
                            )
                            .foregroundStyle(
                                isSelected
                                    ? Color(hex: "#00E5FF")
                                    : AppTheme.Palette.textSecondary
                            )
                            .overlay(
                                Capsule().stroke(
                                    isSelected ? Color(hex: "#00E5FF") : Color.clear,
                                    lineWidth: 1
                                )
                            )
                    }
                }
            }
        }
    }

    // MARK: - Instruments Grid

    private var instrumentsGrid: some View {
        VStack(spacing: AppTheme.Spacing.xs) {
            let filtered = MedicalEquipmentRepository.itemsForCategory(selectedCategory)
            ForEach(filtered) { item in
                let isSelected = item.id == selectedItem.id
                Button {
                    selectedItem = item
                } label: {
                    CardContainer {
                        HStack(spacing: AppTheme.Spacing.md) {
                            ZStack {
                                RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                                    .fill(Color(hex: item.badgeColorHex).opacity(0.15))
                                    .frame(width: 44, height: 44)

                                Image(systemName: systemIconForItem(item))
                                    .font(.system(size: 20))
                                    .foregroundStyle(Color(hex: item.badgeColorHex))
                            }

                            VStack(alignment: .leading, spacing: 2) {
                                Text(item.name)
                                    .font(AppTheme.Font.headline)
                                    .foregroundStyle(AppTheme.Palette.textPrimary)

                                Text("\(item.specialty) • \(item.category)")
                                    .font(AppTheme.Font.caption2)
                                    .foregroundStyle(AppTheme.Palette.textSecondary)
                            }

                            Spacer()

                            VStack(alignment: .trailing, spacing: 2) {
                                Text("\(item.creditCost == 0 ? "Starter" : "\(item.creditCost) C")")
                                    .font(.system(size: 11, weight: .bold))
                                    .foregroundStyle(item.creditCost == 0 ? Color.green : Color.yellow)

                                Image(systemName: isSelected ? "checkmark.circle.fill" : "chevron.right")
                                    .font(.system(size: 12))
                                    .foregroundStyle(isSelected ? AppTheme.Palette.primary : AppTheme.Palette.textMuted)
                            }
                        }
                    }
                }
            }
        }
    }

    // MARK: - Meter Helper

    private func statMeter(title: String, value: Int, color: Color) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            HStack {
                Text(title)
                    .font(.system(size: 10, weight: .medium))
                    .foregroundStyle(AppTheme.Palette.textSecondary)
                Spacer()
                Text("\(value)%")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(AppTheme.Palette.textPrimary)
            }

            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.gray.opacity(0.2))
                    Capsule()
                        .fill(color)
                        .frame(width: geo.size.width * CGFloat(value) / 100)
                }
            }
            .frame(height: 5)
        }
    }

    private func systemIconForItem(_ item: MedicalEquipmentItem) -> String {
        switch item.specialty.lowercased() {
        case "anatomy": return "figure.walk"
        case "cardiothoracic": return "heart.fill"
        case "neurosurgery": return "brain.head.profile"
        case "ent": return "ear.fill"
        case "diagnostics": return "waveform.path.ecg"
        default: return "cross.case.fill"
        }
    }
}
