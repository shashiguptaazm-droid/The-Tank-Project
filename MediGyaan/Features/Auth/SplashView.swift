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
                Image(systemName: "cross.case.fill")
                    .font(.system(size: 62, weight: .semibold))
                    .foregroundStyle(.white)
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
