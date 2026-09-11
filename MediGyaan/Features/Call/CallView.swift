import LiveKit
import SwiftUI

/// An outgoing call the user asked for. Drives `fullScreenCover(item:)`.
struct PendingCall: Identifiable, Hashable {
    let id = UUID()
    /// LiveKit room name.
    let room: String
    let kind: CallKind
    /// Who is being called, shown in the call header.
    let peerName: String

    /// 1-on-1 room for two users, using Android's naming scheme so both
    /// platforms resolve to the same room.
    static func oneToOne(
        myId: Int,
        peerId: Int,
        peerName: String,
        kind: CallKind
    ) -> PendingCall {
        PendingCall(room: CallRoom.oneToOne(myId, peerId), kind: kind, peerName: peerName)
    }
}

/// Full-screen call, backed by the LiveKit SFU.
///
/// Replaces the Android app's Jitsi Meet SDK screen. Android handed the whole
/// call UI to `JitsiMeetActivity`; here the UI is ours, which is why the palette
/// and controls follow the app's own design tokens instead of a third-party
/// look.
struct CallView: View {

    @StateObject private var model: CallViewModel

    init(model: CallViewModel) {
        _model = StateObject(wrappedValue: model)
    }

    var body: some View {
        CallRoomContent(model: model, room: model.room)
            .task { await model.start() }
    }
}

/// Split out so `Room` can be observed with `@ObservedObject` — the SDK is the
/// source of truth for participants and tracks, and mirroring it would let the
/// two drift.
private struct CallRoomContent: View {

    @ObservedObject var model: CallViewModel
    @ObservedObject var room: Room

    @Environment(\.dismiss) private var dismiss
    @State private var connectedAt = Date()

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            switch model.phase {
            case .connecting:
                connectingView
            case .connected:
                connectedView
            case let .ended(reason):
                endedView(reason: reason)
            }
        }
        .preferredColorScheme(.dark)
        .onChange(of: model.phase) { phase in
            switch phase {
            case .connected:
                connectedAt = Date()
            case .ended where model.errorMessage != nil:
                // A failure has nothing left to show; surface it briefly, then
                // close so the user is not stranded on a dead screen.
                DispatchQueue.main.asyncAfter(deadline: .now() + 3) { dismiss() }
            case .connecting, .ended:
                break
            }
        }
    }

    // MARK: - States

    private var connectingView: some View {
        VStack(spacing: AppTheme.Spacing.lg) {
            ProgressView()
                .controlSize(.large)
                .tint(.white)
            Text("Connecting…")
                .font(AppTheme.Font.headline)
                .foregroundStyle(.white)
            Text(model.peerName)
                .font(AppTheme.Font.callout)
                .foregroundStyle(.white.opacity(0.7))
        }
    }

    /// Terminal state. `reason` is non-nil only when the call ended in failure.
    private func endedView(reason: String?) -> some View {
        VStack(spacing: AppTheme.Spacing.md) {
            Image(systemName: "phone.down.fill")
                .font(.system(size: 44))
                .foregroundStyle(AppTheme.Palette.error)
            Text(reason == nil ? "Call ended" : "Call failed")
                .font(AppTheme.Font.headline)
                .foregroundStyle(.white)
            if let reason {
                Text(reason)
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(.white.opacity(0.7))
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, AppTheme.Spacing.xxl)
            }
            TextActionButton(title: "Close") { dismiss() }
        }
    }

    private var connectedView: some View {
        ZStack {
            remoteArea

            VStack(spacing: 0) {
                header
                    .padding(.horizontal, AppTheme.Spacing.lg)
                    .padding(.top, AppTheme.Spacing.sm)

                Spacer()

                HStack(alignment: .bottom) {
                    Spacer()
                    localPreview
                }
                .padding(.horizontal, AppTheme.Spacing.lg)
                .padding(.bottom, AppTheme.Spacing.md)

                controls
                    .padding(.bottom, AppTheme.Spacing.xxl)
            }
        }
    }

    // MARK: - Remote video

    @ViewBuilder
    private var remoteArea: some View {
        let participants = model.remoteParticipants

        if participants.isEmpty {
            waitingView
        } else if participants.count == 1, let track = participants[0].firstCameraVideoTrack {
            SwiftUIVideoView(track, layoutMode: .fill)
                .ignoresSafeArea()
        } else {
            // Audio-only call, camera off, or more than one remote participant.
            VStack(spacing: AppTheme.Spacing.lg) {
                ForEach(participants) { participant in
                    participantTile(participant)
                }
            }
            .padding(AppTheme.Spacing.lg)
        }
    }

    private func participantTile(_ participant: RemoteParticipant) -> some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            if let track = participant.firstCameraVideoTrack {
                SwiftUIVideoView(track, layoutMode: .fill)
                    .aspectRatio(3.0 / 4.0, contentMode: .fit)
                    .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous))
            } else {
                AvatarView(
                    url: nil,
                    name: participant.name ?? "Participant",
                    size: 96,
                    strokeColor: participant.isSpeaking
                        ? AppTheme.Ink.teal
                        : AppTheme.Palette.outline,
                    strokeWidth: participant.isSpeaking ? 3 : 1
                )
                .frame(height: 200)
            }

            Label(
                participant.name ?? participant.identity?.stringValue ?? "Participant",
                systemImage: participant.isMicrophoneEnabled() ? "mic.fill" : "mic.slash.fill"
            )
            .font(AppTheme.Font.cardTitle)
            .foregroundStyle(.white.opacity(0.9))
        }
    }

    private var waitingView: some View {
        VStack(spacing: AppTheme.Spacing.md) {
            AvatarView(
                url: nil,
                name: model.peerName,
                size: 110,
                strokeColor: AppTheme.Ink.teal,
                strokeWidth: 2
            )
            Text("Waiting for \(model.peerName) to join…")
                .font(AppTheme.Font.callout)
                .foregroundStyle(.white.opacity(0.85))
                .multilineTextAlignment(.center)
        }
        .padding(AppTheme.Spacing.xxl)
    }

    // MARK: - Local preview

    @ViewBuilder
    private var localPreview: some View {
        if model.cameraEnabled, let track = model.localCameraTrack {
            // `.auto` mirrors the front camera, matching every other video app.
            SwiftUIVideoView(track, layoutMode: .fill, mirrorMode: .auto)
                .frame(width: 104, height: 148)
                .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.card, style: .continuous)
                        .stroke(.white.opacity(0.25), lineWidth: 1)
                )
                .shadow(color: .black.opacity(0.4), radius: 8, y: 3)
        }
    }

    // MARK: - Header

    private var header: some View {
        VStack(spacing: 2) {
            Text(model.peerName)
                .font(AppTheme.Font.headline)
                .foregroundStyle(.white)
                .lineLimit(1)

            HStack(spacing: AppTheme.Spacing.xs) {
                TimelineView(.periodic(from: connectedAt, by: 1)) { context in
                    Text(durationString(from: connectedAt, to: context.date))
                }
                if model.remoteParticipants.count > 1 {
                    Text("·")
                    Text("\(model.remoteParticipants.count + 1) on the call")
                }
            }
            .font(AppTheme.Font.caption)
            .foregroundStyle(.white.opacity(0.7))
        }
        .padding(.vertical, AppTheme.Spacing.sm)
        .padding(.horizontal, AppTheme.Spacing.lg)
        .background(
            Capsule().fill(.black.opacity(0.35))
        )
    }

    private func durationString(from start: Date, to now: Date) -> String {
        let total = max(0, Int(now.timeIntervalSince(start)))
        let minutes = total / 60
        let seconds = total % 60
        return String(format: "%02d:%02d", minutes, seconds)
    }

    // MARK: - Controls

    private var controls: some View {
        HStack(spacing: AppTheme.Spacing.lg) {
            controlButton(
                systemImage: model.microphoneEnabled ? "mic.fill" : "mic.slash.fill",
                label: model.microphoneEnabled ? "Mute" : "Unmute",
                isActive: !model.microphoneEnabled
            ) {
                Task { await model.toggleMicrophone() }
            }

            if model.kind == .video {
                controlButton(
                    systemImage: model.cameraEnabled ? "video.fill" : "video.slash.fill",
                    label: model.cameraEnabled ? "Camera off" : "Camera on",
                    isActive: !model.cameraEnabled
                ) {
                    Task { await model.toggleCamera() }
                }

                controlButton(
                    systemImage: "arrow.triangle.2.circlepath.camera.fill",
                    label: "Flip",
                    isActive: false
                ) {
                    Task { await model.flipCamera() }
                }
            }

            Button {
                Task {
                    await model.end()
                    dismiss()
                }
            } label: {
                Image(systemName: "phone.down.fill")
                    .font(.system(size: 22, weight: .semibold))
                    .foregroundStyle(.white)
                    .frame(width: 64, height: 64)
                    .background(Circle().fill(AppTheme.Palette.error))
            }
            .accessibilityLabel("End call")
        }
    }

    private func controlButton(
        systemImage: String,
        label: String,
        isActive: Bool,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            Image(systemName: systemImage)
                .font(.system(size: 20, weight: .semibold))
                .foregroundStyle(isActive ? .black : .white)
                .frame(width: 54, height: 54)
                .background(
                    Circle().fill(isActive ? Color.white : Color.white.opacity(0.18))
                )
        }
        .accessibilityLabel(label)
    }
}
