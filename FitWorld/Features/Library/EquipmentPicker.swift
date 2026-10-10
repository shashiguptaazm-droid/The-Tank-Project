import SwiftUI

/// A wrap-style multi-select list of equipment.
struct EquipmentPicker: View {
    @Binding var selection: [Equipment]

    private var ordered: [Equipment] {
        // .none/.bodyweight first so they're the obvious defaults.
        [Equipment.bodyweight] + Equipment.allCases.filter { $0 != .bodyweight }
    }

    var body: some View {
        FlowLayoutCompat(items: ordered) { equipment in
            let isOn = selection.contains(equipment)
            Button {
                if isOn {
                    selection.removeAll { $0 == equipment }
                } else {
                    selection.append(equipment)
                }
            } label: {
                Text(equipment.displayName)
                    .font(.subheadline)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(isOn ? Color.accentColor.opacity(0.2) : Color(.tertiarySystemFill))
                    .clipShape(Capsule())
            }
            .buttonStyle(.plain)
        }
    }
}

// MARK: - Minimal flow layout (works on iOS 16+ patterns; fine on 17.4 baseline)

struct FlowLayoutCompat<Item: Hashable, Content: View>: View {
    let items: [Item]
    let content: (Item) -> Content

    var body: some View {
        // Phase 1 keeps it simple: vertical list of capsule rows is readable,
        // avoids custom Layout math; polish arrives with the design pass.
        LazyVGrid(columns: [GridItem(.adaptive(minimum: 120), spacing: 8)], spacing: 8) {
            ForEach(items, id: \.self) { item in
                content(item)
            }
        }
    }
}
