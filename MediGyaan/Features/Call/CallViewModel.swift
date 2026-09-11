import AVFoundation
import LiveKit
import SwiftUI

/// Drives a LiveKit call: connects the `Room`, tracks the local media state, and
/// exposes the in-call controls.
///
/// `Room` is itself an `ObservableObject`, so views observe it directly for
/// participant and track changes while this object owns the connection
/// lifecycle. That keeps the participant list live without mirroring the SDK's
/// state into a second source of truth.
@MainActor
final class CallViewModel: ObservableObject {

    /// Lifecycle of the call, as the UI needs to render it.
    enum Phase: Equatable {
        case connecting
        case connected
        /// The call finished. `reason` is set when it ended because of a failure.
        case ended(reason: String?)

        var isConnected: Bool { self == .connected }
    }

    /// The underlying LiveKit room. Observed by `CallView` for participants.
    let room = Room()

    @Published private(set) var phase: Phase = .connecting
    @Published private(set) var microphoneEnabled = true
    @Published private(set) var cameraEnabled = true
    @Published var errorMessage: String?

    /// Room to join, already resolved by the caller.
    let roomName: String
    /// Audio-only calls never publish a camera track.
    let kind: CallKind
    /// Who the user is talking to, for the call header.
    let peerName: String

    private let api: MediGyaanAPI
    private let session: SessionStore
    private var cameraPosition: AVCaptureDevice.Position = .front
    private var hasStarted = false
    private var didPublishMedia = false

    init(
        roomName: String,
        kind: CallKind,
        peerName: String,
        api: MediGyaanAPI,
        session: SessionStore
    ) {
        self.roomName = roomName
        self.kind = kind
        self.peerName = peerName
        self.api = api
        self.session = session
    }

    // MARK: - Lifecycle

    /// Fetches a token and joins the room. Safe to call repeatedly; only the
    /// first call does any work, so a `task` modifier cannot double-connect.
    func start() async {
        guard !hasStarted else { return }
        hasStarted = true

        let userId = session.userId
        guard userId > 0 else {
            phase = .ended(reason: "Please sign in again to start a call.")
            return
        }

        do {
            let token = try await api.liveKit.token(
                room: roomName,
                userId: userId,
                displayName: displayName
            )

            try await room.connect(url: token.url, token: token.token)
            phase = .connected

            // Media is published after connecting so the token's grants are
            // already in effect.
            await publishInitialMedia()
        } catch {
            let message = (error as? APIError)?.errorDescription ?? error.localizedDescription
            errorMessage = message
            phase = .ended(reason: message)
        }
    }

    /// Publishes microphone (always) and camera (video calls only).
    private func publishInitialMedia() async {
        guard !didPublishMedia else { return }
        didPublishMedia = true

        do {
            try await room.localParticipant.setMicrophone(enabled: true)
            microphoneEnabled = true

            if kind == .video {
                try await room.localParticipant.setCamera(
                    enabled: true,
                    captureOptions: CameraCaptureOptions(position: cameraPosition)
                )
                cameraEnabled = true
            } else {
                cameraEnabled = false
            }
        } catch {
            // A camera failure must not kill an audio call.
            errorMessage = "Camera or microphone unavailable: \(error.localizedDescription)"
            cameraEnabled = false
        }
    }

    /// Leaves the room. Idempotent, so it is safe from both the hang-up button
    /// and `onDisappear`.
    func end() async {
        if room.connectionState != .disconnected {
            await room.disconnect()
        }
        phase = .ended(reason: nil)
    }

    // MARK: - Controls

    func toggleMicrophone() async {
        let target = !microphoneEnabled
        do {
            try await room.localParticipant.setMicrophone(enabled: target)
            microphoneEnabled = target
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func toggleCamera() async {
        let target = !cameraEnabled
        do {
            try await room.localParticipant.setCamera(
                enabled: target,
                captureOptions: CameraCaptureOptions(position: cameraPosition)
            )
            cameraEnabled = target
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    /// Switches between the front and rear camera, iOS's equivalent of the
    /// Android front/back toggle. Only meaningful on a face-to-face call.
    func flipCamera() async {
        cameraPosition = cameraPosition == .front ? .back : .front
        guard cameraEnabled else { return }
        do {
            try await room.localParticipant.setCamera(
                enabled: true,
                captureOptions: CameraCaptureOptions(position: cameraPosition)
            )
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    // MARK: - Derived state

    /// Display name other participants see, falling back to something readable.
    private var displayName: String {
        let name = session.currentUser?.name ?? ""
        return name.isEmpty ? "MediGyaan user \(session.userId)" : name
    }

    /// Remote participants, stable-ordered so the grid does not reshuffle.
    var remoteParticipants: [RemoteParticipant] {
        room.remoteParticipants.values.sorted {
            ($0.identity?.stringValue ?? "") < ($1.identity?.stringValue ?? "")
        }
    }

    /// True once someone else has actually joined, so the UI can tell "waiting
    /// for them to answer" apart from "connected".
    var hasRemoteParticipant: Bool {
        !remoteParticipants.isEmpty
    }

    /// Live camera track for the local picture-in-picture preview.
    var localCameraTrack: VideoTrack? {
        room.localParticipant.firstCameraVideoTrack
    }

    /// True while the SDK is still working on the connection, so the UI can show
    /// a spinner rather than an empty room.
    var isConnecting: Bool {
        switch room.connectionState {
        case .connecting, .reconnecting: return true
        case .disconnected, .connected, .disconnecting: return false
        @unknown default: return false
        }
    }
}
