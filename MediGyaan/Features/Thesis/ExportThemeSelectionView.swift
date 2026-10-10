import SwiftUI

/// iOS equivalent of Android `ExportThemeSelectionActivity.kt`.
///
/// Complete thesis and report export layout selector featuring real-time preview of cover pages,
/// academic border styling, table grid specifications, font schemes, and family filter chips.
struct ExportThemeSelectionView: View {

    @State private var selectedLayout: ExportThemeLayout = ExportThemeRepository.standardLayouts.first!
    @State private var selectedFamily: String = "All"
    @State private var previewMode: PreviewMode = .cover

    var onSelectTheme: ((ExportThemeLayout) -> Void)?
    @Environment(\.dismiss) private var dismiss

    enum PreviewMode: String, CaseIterable, Identifiable {
        case cover = "Cover Page"
        case page = "Chapter Page"
        case table = "Table & Grid"
        case chart = "Analytics Chart"

        var id: String { rawValue }
    }

    var body: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.md) {
                // Interactive Manuscript Preview
                manuscriptPreviewCard

                // Preview Mode Picker
                previewModePicker

                // Layout dossier card
                layoutDossierCard

                // Family Filter Chips
                familyFilterBar

                // Themes Grid
                themesList
            }
            .padding(AppTheme.Spacing.md)
        .onAppear {
            RemoteLogger.log(tag: "ExportTheme_Appear", message: "Thesis Export Theme selection opened")
        }
        }
        .screenBackground()
        .navigationTitle("Thesis Export Themes")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .confirmationAction) {
                Button("Apply") {
                    onSelectTheme?(selectedLayout)
                    dismiss()
                }
                .fontWeight(.bold)
            }
        }
    }

    // MARK: - Live Preview Card

    private var manuscriptPreviewCard: some View {
        CardContainer {
            VStack(spacing: AppTheme.Spacing.sm) {
                // Simulating physical A4 paper page
                ZStack {
                    RoundedRectangle(cornerRadius: 6)
                        .fill(Color(hex: selectedLayout.softHex))
                        .aspectRatio(1 / 1.35, contentMode: .fit)
                        .shadow(color: Color.black.opacity(0.15), radius: 8, y: 4)

                    // Page borders according to layout
                    RoundedRectangle(cornerRadius: 4)
                        .stroke(Color(hex: selectedLayout.accentHex).opacity(0.7), lineWidth: 2)
                        .padding(12)

                    VStack(spacing: 8) {
                        switch previewMode {
                        case .cover:
                            VStack(spacing: 6) {
                                Image(systemName: "building.columns.fill")
                                    .font(.system(size: 24))
                                    .foregroundStyle(Color(hex: selectedLayout.accentHex))

                                Text("NATIONAL BOARD OF EXAMINATIONS")
                                    .font(.system(size: 8, weight: .bold, design: .serif))
                                    .foregroundStyle(AppTheme.Palette.textMuted)

                                Spacer().frame(height: 10)

                                Text("CLINICAL EVALUATION OF MULTI-DRUG RESISTANT BACTERIAL ISOLATES")
                                    .font(.system(size: 11, weight: .black, design: .serif))
                                    .foregroundStyle(Color(hex: selectedLayout.accentHex))
                                    .multilineTextAlignment(.center)
                                    .padding(.horizontal, 24)

                                Text("THESIS DISSERTATION IN MD PATHOLOGY")
                                    .font(.system(size: 7, weight: .semibold, design: .monospaced))
                                    .foregroundStyle(AppTheme.Palette.textSecondary)

                                Spacer().frame(height: 20)

                                Text("CANDIDATE: DR. ARJUN MEHTA, MBBS")
                                    .font(.system(size: 8, weight: .bold))
                                    .foregroundStyle(AppTheme.Palette.textPrimary)
                            }

                        case .page:
                            VStack(alignment: .leading, spacing: 6) {
                                HStack {
                                    Text("CHAPTER 1: INTRODUCTION")
                                        .font(.system(size: 8, weight: .bold))
                                        .foregroundStyle(Color(hex: selectedLayout.accentHex))
                                    Spacer()
                                    Text("PAGE 14")
                                        .font(.system(size: 8, weight: .medium))
                                        .foregroundStyle(AppTheme.Palette.textMuted)
                                }
                                Divider().background(Color(hex: selectedLayout.accentHex))

                                Text("1.1 Background & Clinical Epidemiology")
                                    .font(.system(size: 10, weight: .bold))
                                    .foregroundStyle(AppTheme.Palette.textPrimary)

                                Text("Antimicrobial resistance represents one of the major therapeutic challenges in intensive care medicine globally. Patients admitted to tertiary healthcare centers exhibit increased morbidity when confronted with hospital-acquired resistant strains...")
                                    .font(.system(size: 8))
                                    .foregroundStyle(AppTheme.Palette.textSecondary)
                                    .lineSpacing(3)
                            }
                            .padding(.horizontal, 20)

                        case .table:
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Table 1.4: Antibiotic Susceptibility Profile")
                                    .font(.system(size: 8, weight: .bold))
                                    .foregroundStyle(Color(hex: selectedLayout.accentHex))

                                VStack(spacing: 2) {
                                    HStack {
                                        Text("Antimicrobial Agent").font(.system(size: 7, weight: .bold)).frame(maxWidth: .infinity, alignment: .leading)
                                        Text("MIC50").font(.system(size: 7, weight: .bold)).frame(width: 40)
                                        Text("Sensitive %").font(.system(size: 7, weight: .bold)).frame(width: 50)
                                    }
                                    .padding(4)
                                    .background(Color(hex: selectedLayout.accentHex).opacity(0.15))

                                    ForEach(["Meropenem", "Colistin", "Tigecycline", "Amikacin"], id: \.self) { drug in
                                        HStack {
                                            Text(drug).font(.system(size: 6)).frame(maxWidth: .infinity, alignment: .leading)
                                            Text("≤ 0.5").font(.system(size: 6)).frame(width: 40)
                                            Text("94.2%").font(.system(size: 6, weight: .bold)).foregroundStyle(Color.green).frame(width: 50)
                                        }
                                        .padding(.horizontal, 4)
                                        .padding(.vertical, 2)
                                        Divider()
                                    }
                                }
                            }
                            .padding(.horizontal, 20)

                        case .chart:
                            VStack(alignment: .leading, spacing: 6) {
                                Text("Figure 2.1: Resistance Trends (2022–2026)")
                                    .font(.system(size: 8, weight: .bold))
                                    .foregroundStyle(Color(hex: selectedLayout.accentHex))

                                HStack(alignment: .bottom, spacing: 12) {
                                    barSample(label: "2022", height: 35)
                                    barSample(label: "2023", height: 50)
                                    barSample(label: "2024", height: 65)
                                    barSample(label: "2025", height: 80)
                                    barSample(label: "2026", height: 95)
                                }
                                .frame(height: 90)
                                .frame(maxWidth: .infinity)
                            }
                            .padding(.horizontal, 20)
                        }
                    }
                    .padding(24)
                }
                .frame(maxHeight: 260)
            }
        }
    }

    private func barSample(label: String, height: CGFloat) -> some View {
        VStack(spacing: 2) {
            RoundedRectangle(cornerRadius: 2)
                .fill(Color(hex: selectedLayout.accentHex))
                .frame(width: 14, height: height)

            Text(label)
                .font(.system(size: 6))
                .foregroundStyle(AppTheme.Palette.textMuted)
        }
    }

    // MARK: - Mode Picker

    private var previewModePicker: some View {
        Picker("Preview Mode", selection: $previewMode) {
            ForEach(PreviewMode.allCases) { mode in
                Text(mode.rawValue).tag(mode)
            }
        }
        .pickerStyle(.segmented)
    }

    // MARK: - Dossier Card

    private var layoutDossierCard: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(selectedLayout.label)
                            .font(AppTheme.Font.headline)
                            .foregroundStyle(AppTheme.Palette.textPrimary)

                        Text("Typography: \(selectedLayout.fontScheme)")
                            .font(AppTheme.Font.caption)
                            .foregroundStyle(AppTheme.Palette.textSecondary)
                    }

                    Spacer()

                    Text(selectedLayout.family.uppercased())
                        .font(.system(size: 10, weight: .bold))
                        .foregroundStyle(Color(hex: selectedLayout.accentHex))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Capsule().fill(Color(hex: selectedLayout.accentHex).opacity(0.18)))
                }

                Divider().background(AppTheme.Palette.divider)

                HStack(spacing: AppTheme.Spacing.md) {
                    specBullet(icon: "doc.fill", title: "Cover", desc: selectedLayout.cover)
                    specBullet(icon: "rectangle.inset.filled", title: "Borders", desc: selectedLayout.page)
                }

                HStack(spacing: AppTheme.Spacing.md) {
                    specBullet(icon: "tablecells", title: "Tables", desc: selectedLayout.table)
                    specBullet(icon: "chart.bar.fill", title: "Visuals", desc: selectedLayout.chart)
                }
            }
        }
    }

    private func specBullet(icon: String, title: String, desc: String) -> some View {
        HStack(alignment: .top, spacing: 6) {
            Image(systemName: icon)
                .font(.system(size: 11))
                .foregroundStyle(Color(hex: selectedLayout.accentHex))
                .frame(width: 16)

            VStack(alignment: .leading, spacing: 1) {
                Text(title)
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(AppTheme.Palette.textSecondary)
                Text(desc)
                    .font(.system(size: 9))
                    .foregroundStyle(AppTheme.Palette.textMuted)
                    .lineLimit(1)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    // MARK: - Family Filter Bar

    private var familyFilterBar: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: AppTheme.Spacing.xs) {
                ForEach(ExportThemeRepository.families, id: \.self) { family in
                    let isSelected = family == selectedFamily
                    Button {
                        selectedFamily = family
                    } label: {
                        Text(family)
                            .font(AppTheme.Font.caption.weight(.semibold))
                            .padding(.horizontal, 14)
                            .padding(.vertical, 8)
                            .background(
                                Capsule().fill(
                                    isSelected
                                        ? AppTheme.Palette.primary
                                        : AppTheme.Palette.cardBackgroundElevated
                                )
                            )
                            .foregroundStyle(
                                isSelected ? Color.white : AppTheme.Palette.textSecondary
                            )
                    }
                }
            }
        }
    }

    // MARK: - Themes List

    private var themesList: some View {
        VStack(spacing: AppTheme.Spacing.xs) {
            let filtered = ExportThemeRepository.layoutsForFamily(selectedFamily)
            ForEach(filtered) { layout in
                let isSelected = layout.id == selectedLayout.id
                Button {
                    selectedLayout = layout
                } label: {
                    CardContainer {
                        HStack(spacing: AppTheme.Spacing.md) {
                            Circle()
                                .fill(Color(hex: layout.accentHex))
                                .frame(width: 24, height: 24)

                            VStack(alignment: .leading, spacing: 2) {
                                Text(layout.label)
                                    .font(AppTheme.Font.headline)
                                    .foregroundStyle(AppTheme.Palette.textPrimary)

                                Text("\(layout.family) • \(layout.fontScheme)")
                                    .font(AppTheme.Font.caption2)
                                    .foregroundStyle(AppTheme.Palette.textSecondary)
                            }

                            Spacer()

                            Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                                .foregroundStyle(isSelected ? AppTheme.Palette.primary : AppTheme.Palette.textMuted)
                        }
                    }
                }
            }
        }
    }
}