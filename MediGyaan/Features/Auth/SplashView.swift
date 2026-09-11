import SwiftUI

/// Branding splash. Ports the Android `SplashActivity` visuals.
struct SplashView: View {

    @State private var isAnimating = false

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [AppTheme.Palette.primary, AppTheme.Palette.primaryDark],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            VStack(spacing: AppTheme.Spacing.md) {
                // `drawable/medigyaan_logo.png` is a gold emblem on black, so it
                // is presented as a rounded tile rather than a bare glyph.
                BrandLogo(size: 104)
                    .clipShape(RoundedRectangle(cornerRadius: 26, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 26, style: .continuous)
                            .stroke(.white.opacity(0.18), lineWidth: 1)
                    )
                    .shadow(color: .black.opacity(0.25), radius: 18, y: 8)
                    .scaleEffect(isAnimating ? 1.0 : 0.86)

                VStack(spacing: AppTheme.Spacing.xxs) {
                    Text("MediGyaan")
                        .font(.system(size: 34, weight: .bold, design: .rounded))
                        .foregroundStyle(.white)
                    Text("Learn. Practise. Excel.")
                        .font(AppTheme.Font.callout)
                        .foregroundStyle(.white.opacity(0.85))
                }

                ProgressView()
                    .tint(.white)
                    .padding(.top, AppTheme.Spacing.md)
            }
        }
        .onAppear {
            withAnimation(.easeOut(duration: 0.7)) { isAnimating = true }
        }
    }
}

#Preview {
    SplashView()
}
