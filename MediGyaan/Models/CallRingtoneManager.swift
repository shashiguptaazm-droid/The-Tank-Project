import SwiftUI
import AudioToolbox
import AVFoundation

/// Ringtone and haptics manager for incoming audio/video calls in iOS.
///
/// 1:1 port of Android `CallRingtoneManager.kt`.
/// Plays system ringtones, loops custom chimes, triggers rhythmic haptics,
/// and auto-times out after 45 seconds of unanswered ringing.
public final class CallRingtoneManager: ObservableObject {

    public static let shared = CallRingtoneManager()
    private var audioPlayer: AVAudioPlayer?
    private var isRinging = false
    private var ringTimer: Timer?

    private init() {}

    public func startRinging() {
        guard !isRinging else { return }
        isRinging = true

        // 1. Play System Haptic Ring pattern
        AudioServicesPlaySystemSound(SystemSoundID(1005)) // SMS/Call alert vibration

        // 2. Play Looping Ringtone sound
        if let soundURL = Bundle.main.url(forResource: "ringtone", withExtension: "mp3") {
            try? AVAudioSession.sharedInstance().setCategory(.playback, mode: .voiceChat, options: [.duckOthers])
            try? AVAudioSession.sharedInstance().setActive(true)
            audioPlayer = try? AVAudioPlayer(contentsOf: soundURL)
            audioPlayer?.numberOfLoops = -1
            audioPlayer?.play()
        } else {
            // Default iOS ring tone system sound fallback
            AudioServicesPlaySystemSound(1000)
        }

        // 3. Auto-stop after 45 seconds timeout
        ringTimer?.invalidate()
        ringTimer = Timer.scheduledTimer(withTimeInterval: 45.0, repeats: false) { [weak self] _ in
            self?.stopRinging()
        }
    }

    public func stopRinging() {
        guard isRinging else { return }
        isRinging = false
        ringTimer?.invalidate()
        ringTimer = nil

        audioPlayer?.stop()
        audioPlayer = nil
        try? AVAudioSession.sharedInstance().setActive(false)
    }
}
