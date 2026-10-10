import SwiftUI

/// Design tokens for the premium fitness aesthetic (§ "Design System").
/// Dark/light adaptive by using semantic dynamic colors where possible.
@Observable
final class Theme {
    // Accent used app-wide via .tint()
    let accent = Color("FitAccent")

    // Elevated surfaces
    let cardCorner: CGFloat = 20
    let cardPadding: CGFloat = 16

    // Timer numerals needs a big, readable style (§5: readable timer display)
    func timerFont(size: CGFloat) -> Font {
        .system(size: size, weight: .heavy, design: .rounded)
    }

    // Restrained motion: honor reduced-motion accessibility preference (§20)
    var prefersReducedMotion: Bool {
        UIAccessibility.isReduceMotionEnabled
    }
}

// MARK: - Card wrapper modifier

struct CardStyle: ViewModifier {
    @Environment(Theme.self) private var theme

    func body(content: Content) -> some View {
        content
            .padding(theme.cardPadding)
            .background(Color(.secondarySystemGroupedBackground))
            .clipShape(RoundedRectangle(cornerRadius: theme.cardCorner))
    }
}

extension View {
    func card() -> some View { modifier(CardStyle()) }
}
