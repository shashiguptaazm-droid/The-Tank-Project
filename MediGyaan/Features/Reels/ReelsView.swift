import SwiftUI
import AVKit

/// Full-screen vertical medical reels player, porting `ReelsActivity` and backed by `api/getReels.php`.
struct ReelsView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api

    @State private var reels: [Reel] = []
    @State private var currentIndex: Int = 0
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var isMuted = false

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            if reels.isEmpty {
                if isLoading {
                    ProgressView("Loading Medical Reels...")
                        .tint(.white)
                        .foregroundStyle(.white)
                } else {
                    VStack(spacing: AppTheme.Spacing.md) {
                        Image(systemName: "film.stack")
                            .font(.system(size: 48))
                            .foregroundStyle(.white.opacity(0.6))
                        Text("No Reels Available")
                            .font(AppTheme.Font.title3)
                            .foregroundStyle(.white)
                        Button("Refresh") {
                            Task { await loadReels() }
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(AppTheme.Palette.primary)
                    }
                }
            } else {
                TabView(selection: $currentIndex) {
                    ForEach(Array(reels.enumerated()), id: \.element.id) { index, reel in
                        ReelCardView(
                            reel: reel,
                            isActive: index == currentIndex,
                            isMuted: isMuted,
                            onToggleMute: { isMuted.toggle() },
                            onToggleLike: { toggleLike(at: index) }
                        )
                        .tag(index)
                        .rotationEffect(.degrees(-90))
                        .frame(width: UIScreen.main.bounds.width, height: UIScreen.main.bounds.height)
                    }
                }
                .rotationEffect(.degrees(90))
                .frame(width: UIScreen.main.bounds.height, height: UIScreen.main.bounds.width)
                .tabViewStyle(.page(indexDisplayMode: .never))
            }
        }
        .navigationTitle("Reels")
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(.hidden, for: .navigationBar)
        .toolbarColorScheme(.dark, for: .navigationBar)
        .task {
            if reels.isEmpty {
                await loadReels()
            }
        }
    }

    @MainActor
    private func loadReels() async {
        isLoading = true
        defer { isLoading = false }
        do {
            reels = try await api.social.reels()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func toggleLike(at index: Int) {
        guard reels.indices.contains(index) else { return }
        reels[index].isLiked.toggle()
        reels[index].likes += reels[index].isLiked ? 1 : -1
    }
}

/// An individual video card within the vertical Reels stream.
struct ReelCardView: View {
    let reel: Reel
    let isActive: Bool
    let isMuted: Bool
    let onToggleMute: () -> Void
    let onToggleLike: () -> Void

    @State private var player: AVPlayer?
    @State private var isPlaying = true
    @State private var showHeartAnimation = false
    @State private var isSharing = false

    var body: some View {
        ZStack {
            Color.black

            // Video layer
            if let player {
                VideoPlayerControllerRepresentable(player: player)
                    .ignoresSafeArea()
                    .onTapGesture {
                        if isPlaying {
                            player.pause()
                            isPlaying = false
                        } else {
                            player.play()
                            isPlaying = true
                        }
                    }
            } else {
                ProgressView().tint(.white)
            }

            // Big popping heart on double-tap
            if showHeartAnimation {
                Image(systemName: "heart.fill")
                    .font(.system(size: 90))
                    .foregroundStyle(.pink)
                    .shadow(radius: 10)
                    .transition(.scale.combined(with: .opacity))
            }

            // Overlay controls & metadata
            VStack {
                Spacer()

                HStack(alignment: .bottom, spacing: AppTheme.Spacing.md) {
                    // Left info: author & caption
                    VStack(alignment: .leading, spacing: 8) {
                        HStack(spacing: AppTheme.Spacing.sm) {
                            if let photoURL = reel.authorPhotoURL {
                                AsyncImage(url: photoURL) { image in
                                    image.resizable().scaledToFill()
                                } placeholder: {
                                    Circle().fill(Color.gray.opacity(0.4))
                                }
                                .frame(width: 38, height: 38)
                                .clipShape(Circle())
                                .overlay(Circle().stroke(Color.white, lineWidth: 1.5))
                            } else {
                                Image(systemName: "person.circle.fill")
                                    .font(.system(size: 38))
                                    .foregroundStyle(.white.opacity(0.8))
                            }

                            Text(reel.authorName.isEmpty ? "MediGyaan Scholar" : reel.authorName)
                                .font(AppTheme.Font.headline)
                                .foregroundStyle(.white)
                                .shadow(radius: 4)

                            Image(systemName: "checkmark.seal.fill")
                                .font(.system(size: 14))
                                .foregroundStyle(AppTheme.Palette.primary)
                        }

                        if !reel.caption.isEmpty {
                            Text(reel.caption)
                                .font(AppTheme.Font.subheadline)
                                .foregroundStyle(.white.opacity(0.95))
                                .lineLimit(3)
                                .shadow(radius: 4)
                        }
                    }

                    Spacer()

                    // Right action column
                    VStack(spacing: 20) {
                        Button {
                            onToggleLike()
                            if reel.isLiked {
                                triggerHeartAnimation()
                            }
                        } label: {
                            VStack(spacing: 4) {
                                Image(systemName: reel.isLiked ? "heart.fill" : "heart")
                                    .font(.system(size: 28))
                                    .foregroundStyle(reel.isLiked ? .pink : .white)
                                Text("\(reel.likes)")
                                    .font(.system(size: 12, weight: .semibold))
                                    .foregroundStyle(.white)
                            }
                        }

                        Button {
                            isSharing = true
                        } label: {
                            VStack(spacing: 4) {
                                Image(systemName: "arrowshape.turn.up.right.fill")
                                    .font(.system(size: 26))
                                    .foregroundStyle(.white)
                                Text("Share")
                                    .font(.system(size: 12, weight: .semibold))
                                    .foregroundStyle(.white)
                            }
                        }

                        Button {
                            onToggleMute()
                        } label: {
                            Image(systemName: isMuted ? "speaker.slash.fill" : "speaker.wave.2.fill")
                                .font(.system(size: 22))
                                .foregroundStyle(.white)
                                .padding(10)
                                .background(Circle().fill(Color.black.opacity(0.4)))
                        }
                    }
                    .shadow(radius: 4)
                }
                .padding(.horizontal, AppTheme.Spacing.lg)
                .padding(.bottom, 36)
            }
        }
        .contentShape(Rectangle())
        .onTapGesture(count: 2) {
            if !reel.isLiked {
                onToggleLike()
            }
            triggerHeartAnimation()
        }
        .sheet(isPresented: $isSharing) {
            if let url = reel.videoURL {
                ShareActivitySheet(activityItems: [url, reel.caption])
            }
        }
        .onAppear {
            setupPlayer()
        }
        .onDisappear {
            teardownPlayer()
        }
        .onChange(of: isActive) { active in
            if active {
                player?.play()
                isPlaying = true
            } else {
                player?.pause()
                isPlaying = false
            }
        }
        .onChange(of: isMuted) { muted in
            player?.isMuted = muted
        }
    }

    private func setupPlayer() {
        guard let url = reel.videoURL else { return }
        let playerItem = AVPlayerItem(url: url)
        let newPlayer = AVPlayer(playerItem: playerItem)
        newPlayer.isMuted = isMuted
        newPlayer.actionAtItemEnd = .none

        NotificationCenter.default.addObserver(
            forName: .AVPlayerItemDidPlayToEndTime,
            object: playerItem,
            queue: .main
        ) { _ in
            newPlayer.seek(to: .zero)
            newPlayer.play()
        }

        self.player = newPlayer
        if isActive {
            newPlayer.play()
            isPlaying = true
        }
    }

    private func teardownPlayer() {
        player?.pause()
        player = nil
    }

    private func triggerHeartAnimation() {
        withAnimation(.spring(response: 0.3, dampingFraction: 0.6)) {
            showHeartAnimation = true
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
            withAnimation(.easeOut(duration: 0.2)) {
                showHeartAnimation = false
            }
        }
    }
}

/// Bridge to `AVPlayerViewController` with playback controls hidden for full-bleed reel display.
struct VideoPlayerControllerRepresentable: UIViewControllerRepresentable {
    let player: AVPlayer

    func makeUIViewController(context: Context) -> AVPlayerViewController {
        let controller = AVPlayerViewController()
        controller.player = player
        controller.showsPlaybackControls = false
        controller.videoGravity = .resizeAspectFill
        return controller
    }

    func updateUIViewController(_ uiViewController: AVPlayerViewController, context: Context) {
        uiViewController.player = player
    }
}

/// Reusable UIActivityViewController representation for SwiftUI.
struct ShareActivitySheet: UIViewControllerRepresentable {
    let activityItems: [Any]
    let applicationActivities: [UIActivity]? = nil

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: activityItems, applicationActivities: applicationActivities)
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}
