import AudioToolbox
import AVFoundation
import LiveKit
import SwiftUI
import UIKit

/// Manages dialing tones and ringing for outgoing calls.
/// Mirrors Android's `LiveKitCallActivity.kt` ringtone.
@MainActor
final class CallRingtoneHelper {
    static let shared = CallRingtoneHelper()
    private var timer: Timer?
    private var isRinging = false

    func start() {
        guard !isRinging else { return }
        isRinging = true
        tick()
        timer = Timer.scheduledTimer(withTimeInterval: 3.5, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.tick()
            }
        }
    }

    private func tick() {
        guard isRinging else { return }
        // Standard telephony call signaling tone in iOS
        AudioServicesPlaySystemSound(1005)
        UIImpactFeedbackGenerator(style: .medium).impactOccurred()
    }

    func stop() {
        isRinging = false
        timer?.invalidate()
        timer = nil
    }
}

/// Concurrency-safe helper that receives LiveKit RoomDelegate callbacks
/// and dispatches state updates back to `CallViewModel` on the `@MainActor`.
private final class CallRoomDelegate: RoomDelegate {
    weak var viewModel: CallViewModel?

    init(viewModel: CallViewModel) {
        self.viewModel = viewModel
    }

    func room(_ room: Room, participantDidConnect participant: RemoteParticipant) {
        Task { @MainActor [weak self] in
            self?.viewModel?.onParticipantConnected(participant)
        }
    }

    func room(_ room: Room, participantDidDisconnect participant: RemoteParticipant) {
        Task { @MainActor [weak self] in
            self?.viewModel?.onParticipantDisconnected(participant)
        }
    }

    func room(_ room: Room, didDisconnectWithError error: LiveKitError?) {
        Task { @MainActor [weak self] in
            self?.viewModel?.onDisconnected(error: error)
        }
    }
}

/// Drives a LiveKit call: connects the `Room`, tracks local media state,
/// handles peer joins/disconnects, speakerphone toggling, 45-second call timeout,
/// and updates call records in `CallLogManager`.
@MainActor
final class CallViewModel: ObservableObject {

    /// Lifecycle of the call, as the UI needs to render it.
    enum Phase: Equatable {
        case connecting
        case connected
        /// The call finished. `reason` is set when it ended because of a failure or peer hangup.
        case ended(reason: String?)

        var isConnected: Bool { self == .connected }
    }

    /// The underlying LiveKit room. Observed by `CallView` for participants and tracks.
    let room = Room()

    @Published private(set) var phase: Phase = .connecting
    @Published private(set) var microphoneEnabled = true
    @Published private(set) var cameraEnabled = true
    @Published private(set) var isSpeakerOn: Bool
    @Published var errorMessage: String?

    /// Room to join, already resolved by the caller.
    let roomName: String
    /// Audio-only calls or video calls.
    let kind: CallKind
    /// Who the user is talking to, for the call header.
    let peerName: String

    private let api: MediGyaanAPI
    private let session: SessionStore
    private var cameraPosition: AVCaptureDevice.Position = .front
    private var hasStarted = false
    private var didPublishMedia = false
    private var roomDelegate: CallRoomDelegate?
    private var timeoutTask: Task<Void, Never>?
    private(set) var callStartTime: Date?

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
        // Video calls default to loud speaker; Audio calls default to earpiece (like Android)
        self.isSpeakerOn = (kind == .video)
    }

    // MARK: - Lifecycle

    /// Fetches a token, attaches delegate, and connects to SFU. Safe to call repeatedly.
    func start() async {
        guard !hasStarted else { return }
        hasStarted = true

        let userId = session.userId
        guard userId > 0 else {
            phase = .ended(reason: "Please sign in again to start a call.")
            return
        }

        // Configure audio session routing
        configureAudioSession()

        // Attach delegate
        let delegate = CallRoomDelegate(viewModel: self)
        self.roomDelegate = delegate
        room.add(delegate: delegate)

        do {
            let token = try await api.liveKit.token(
                room: roomName,
                userId: userId,
                displayName: displayName
            )

            // Start dialing ringtone while waiting for peer
            CallRingtoneHelper.shared.start()

            try await room.connect(url: token.url, token: token.token)

            // Publish media tracks once token grants are active
            await publishInitialMedia()

            // Check if remote peer is already in room
            if !room.remoteParticipants.isEmpty {
                CallRingtoneHelper.shared.stop()
                phase = .connected
                callStartTime = Date()
            } else {
                // We are calling peer; start 45s ringing timeout (Android parity)
                startCallTimeout()
            }
        } catch {
            CallRingtoneHelper.shared.stop()
            let message = (error as? APIError)?.errorDescription ?? error.localizedDescription
            errorMessage = message
            phase = .ended(reason: message)
        }
    }

    private func configureAudioSession() {
        do {
            let audioSession = AVAudioSession.sharedInstance()
            try audioSession.setCategory(.playAndRecord, mode: .voiceChat, options: [.allowBluetooth, .defaultToSpeaker])
            try audioSession.overrideOutputAudioPort(isSpeakerOn ? .speaker : .none)
            try audioSession.setActive(true)
        } catch {
            RemoteLogger.log(tag: "Call_AudioSession_Error", message: error.localizedDescription)
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
            errorMessage = "Camera or microphone unavailable: \(error.localizedDescription)"
            cameraEnabled = false
        }
    }

    /// 45-second timeout waiting for remote peer to answer (Android CALL_TIMEOUT_MS parity).
    private func startCallTimeout() {
        timeoutTask?.cancel()
        timeoutTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 45_000_000_000)
            guard let self = self, !Task.isCancelled else { return }
            if self.remoteParticipants.isEmpty && self.phase == .connecting {
                CallRingtoneHelper.shared.stop()
                CallLogManager.shared.updateCallCompletion(roomName: self.roomName, durationSeconds: 0, status: .noAnswer)
                self.phase = .ended(reason: "No answer")
            }
        }
    }

    // MARK: - Delegate Callbacks

    func onParticipantConnected(_ participant: RemoteParticipant) {
        CallRingtoneHelper.shared.stop()
        timeoutTask?.cancel()
        timeoutTask = nil
        if phase != .connected {
            phase = .connected
            callStartTime = Date()
        }
        RemoteLogger.log(tag: "LiveKit_Peer_Connected", message: "Peer joined call: \(participant.identity?.stringValue ?? "")")
    }

    func onParticipantDisconnected(_ participant: RemoteParticipant) {
        CallRingtoneHelper.shared.stop()
        timeoutTask?.cancel()
        timeoutTask = nil
        let duration = callStartTime.map { Int(Date().timeIntervalSince($0)) } ?? 0
        CallLogManager.shared.updateCallCompletion(roomName: roomName, durationSeconds: duration, status: .connected)
        phase = .ended(reason: "Call ended")
        RemoteLogger.log(tag: "LiveKit_Peer_Disconnected", message: "Peer hung up, duration: \(duration)s")
    }

    func onDisconnected(error: LiveKitError?) {
        CallRingtoneHelper.shared.stop()
        timeoutTask?.cancel()
        timeoutTask = nil
        if case .ended = phase { return }
        let duration = callStartTime.map { Int(Date().timeIntervalSince($0)) } ?? 0
        CallLogManager.shared.updateCallCompletion(roomName: roomName, durationSeconds: duration, status: duration > 0 ? .connected : .noAnswer)
        phase = .ended(reason: error?.localizedDescription ?? "Call disconnected")
    }

    /// Leaves the room and logs completion. Safe from both user hang-up button and dismiss.
    func end() async {
        CallRingtoneHelper.shared.stop()
        timeoutTask?.cancel()
        timeoutTask = nil
        let duration = callStartTime.map { Int(Date().timeIntervalSince($0)) } ?? 0
        CallLogManager.shared.updateCallCompletion(roomName: roomName, durationSeconds: duration, status: duration > 0 ? .connected : .noAnswer)

        if room.connectionState != .disconnected {
            await room.disconnect()
        }
        try? AVAudioSession.sharedInstance().overrideOutputAudioPort(.none)
        try? AVAudioSession.sharedInstance().setActive(false)
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

    /// Switches between front and back camera.
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

    /// Toggles speakerphone on or earpiece (matching Android toggleSpeaker).
    func toggleSpeaker() {
        isSpeakerOn.toggle()
        do {
            try AVAudioSession.sharedInstance().overrideOutputAudioPort(isSpeakerOn ? .speaker : .none)
        } catch {
            RemoteLogger.log(tag: "Call_Speaker_Toggle_Error", message: error.localizedDescription)
        }
    }

    /// Dynamically upgrades an audio call to video during the call.
    func upgradeToVideo() async {
        guard !cameraEnabled else { return }
        do {
            try await room.localParticipant.setCamera(
                enabled: true,
                captureOptions: CameraCaptureOptions(position: cameraPosition)
            )
            cameraEnabled = true
            isSpeakerOn = true
            try? AVAudioSession.sharedInstance().overrideOutputAudioPort(.speaker)
            RemoteLogger.log(tag: "Call_Upgrade_Video", message: "Audio call dynamically upgraded to video")
        } catch {
            errorMessage = "Could not activate camera: \(error.localizedDescription)"
        }
    }

    // MARK: - Derived state

    private var displayName: String {
        let name = session.currentUser?.name ?? ""
        return name.isEmpty ? "MediGyaan user \(session.userId)" : name
    }

    var remoteParticipants: [RemoteParticipant] {
        room.remoteParticipants.values.sorted {
            ($0.identity?.stringValue ?? "") < ($1.identity?.stringValue ?? "")
        }
    }

    var hasRemoteParticipant: Bool {
        !remoteParticipants.isEmpty
    }

    var localCameraTrack: VideoTrack? {
        room.localParticipant.firstCameraVideoTrack
    }

    var isConnecting: Bool {
        switch room.connectionState {
        case .connecting, .reconnecting: return true
        case .disconnected, .connected, .disconnecting: return false
        @unknown default: return false
        }
    }
}
