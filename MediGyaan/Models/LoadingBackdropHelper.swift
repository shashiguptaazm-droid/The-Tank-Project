import SwiftUI

/// Loading backdrop and thematic matrix shatter effects.
///
/// 1:1 port of Android `LoadingBackdropHelper.kt` and `ScreenExplosionHelper.kt`.
/// Provides dynamic subject video selection, rank backdrop wallpapers,
/// and cinematic matrix cyberspace / particle shatter transitions.
public enum LoadingBackdropHelper {

    public static func resolveLobbyVideoName(subject: String?, topic: String? = nil) -> String {
        let combined = "\(subject ?? "") \(topic ?? "")".lowercased()
        if combined.contains("biochem") {
            return "loading_screen_elephant_biochemistry"
        } else if combined.contains("physio") || combined.contains("physilo") {
            return "loading_screen_eagle_physiology"
        } else {
            return "loading_screen_friends_lion"
        }
    }

    public static func resolveRankBackdrop(rankTitle: String) -> String {
        let norm = rankTitle.lowercased().trimmingCharacters(in: .whitespacesAndNewlines)
        if norm.contains("legend") || norm.contains("grandmaster") || norm.contains("master") {
            return "grandmaster"
        } else if norm.contains("scholar") {
            return "scholar"
        } else if norm.contains("expert") || norm.contains("warrior") || norm.contains("skilled") {
            return "expert"
        } else if norm.contains("rookie") || norm.contains("aspirant") || norm.contains("beginner") {
            return "aspirant"
        } else {
            return "bg_battle"
        }
    }
}

/// Matrix cyberspace digital rain and shatter particle view for transitions.
public struct ScreenExplosionTransitionView: View {

    @State private var phase: Double = 0.0
    var onComplete: (() -> Void)?

    private let matrixGlyphs = ["0", "1", "Ω", "Ψ", "X", "Z", "A", "B", "C", "D", "7", "9", "⚡", "⚔️"]

    public var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            // Digital green rain columns
            HStack(spacing: 12) {
                ForEach(0..<18, id: \.self) { col in
                    VStack(spacing: 6) {
                        ForEach(0..<25, id: \.self) { row in
                            Text(matrixGlyphs[(col * 7 + row) % matrixGlyphs.count])
                                .font(.system(size: 11, weight: .bold, design: .monospaced))
                                .foregroundStyle(
                                    row == 0 ? Color(hex: "#E0FFE8") : Color(hex: "#00FF41").opacity(Double(25 - row) / 25.0)
                                )
                        }
                    }
                    .offset(y: CGFloat((col * 35) % 120))
                }
            }
            .opacity(1.0 - phase)

            // Central Telemetry HUD
            VStack(spacing: 12) {
                Text("ENTERING THE ARENA MATRIX")
                    .font(.system(size: 18, weight: .black, design: .monospaced))
                    .foregroundStyle(Color(hex: "#00FF41"))
                    .shadow(color: Color(hex: "#00FF41"), radius: 10)

                Text("[ SYNCHRONIZING CLINICAL TELEMETRY ]")
                    .font(.system(size: 11, weight: .semibold, design: .monospaced))
                    .foregroundStyle(Color.white.opacity(0.8))
            }
            .scaleEffect(1.0 + phase * 0.4)
        }
        .onAppear {
            withAnimation(.easeInOut(duration: 1.5)) {
                phase = 1.0
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                onComplete?()
            }
        }
    }
}
