import SwiftUI
import AVKit

/// Full-screen clinical video player with navigation bar, title, progress, and controls.
/// Ports Android's `VideoPlayerActivity.kt`.
struct VideoPlayerView: View {
    let title: String
    let videoURL: URL?

    @Environment(\.dismiss) private var dismiss
    @State private var player: AVPlayer?
    @State private var isPlaying = true
    @State private var isLoading = true

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            if let player {
                VideoPlayer(player: player)
                    .ignoresSafeArea()
            } else {
                VStack(spacing: AppTheme.Spacing.md) {
                    ProgressView()
                        .tint(.white)
                    Text("Loading Clinical Video...")
                        .font(AppTheme.Font.subheadline)
                        .foregroundStyle(.white.opacity(0.8))
                }
            }
        }
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbarColorScheme(.dark, for: .navigationBar)
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Button {
                    dismiss()
                } label: {
                    Image(systemName: "chevron.left")
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(.white)
                }
            }
        }
        .onAppear {
            RemoteLogger.log(tag: "VideoPlayer_Open", message: "Clinical Video Player opened")
            setupPlayer()
        }
        .onDisappear {
            player?.pause()
            player = nil
        }
    }

    private func setupPlayer() {
        guard let url = videoURL else { return }
        let playerItem = AVPlayerItem(url: url)
        let newPlayer = AVPlayer(playerItem: playerItem)
        self.player = newPlayer
        newPlayer.play()
    }
}
