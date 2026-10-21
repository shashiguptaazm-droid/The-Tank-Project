import Foundation
import Speech
import AVFoundation

/// Live speech-to-text recognizer for voice dictation in the AI chat composer.
/// Ports Android's voice dictation flow in `AiChatDialogHelper.kt`.
@MainActor
final class AiSpeechRecognizer: ObservableObject {

    @Published var isRecording = false
    @Published var transcribedText = ""
    @Published var permissionError: String?

    private var speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private let audioEngine = AVAudioEngine()

    init() {}

    /// Toggles live voice recording. Calls `onTextChange` with real-time transcribed words.
    func toggleRecording(onTextChange: @escaping (String) -> Void) {
        if isRecording {
            stopRecording()
        } else {
            startRecording(onTextChange: onTextChange)
        }
    }

    func startRecording(onTextChange: @escaping (String) -> Void) {
        permissionError = nil

        SFSpeechRecognizer.requestAuthorization { [weak self] authStatus in
            Task { @MainActor in
                guard let self = self else { return }
                switch authStatus {
                case .authorized:
                    self.beginAudioSession(onTextChange: onTextChange)
                case .denied:
                    self.permissionError = "Speech recognition permission was denied. Please enable it in Settings."
                case .restricted:
                    self.permissionError = "Speech recognition is restricted on this device."
                case .notDetermined:
                    self.permissionError = "Speech recognition not authorized."
                @unknown default:
                    self.permissionError = "Unknown speech recognition error."
                }
            }
        }
    }

    private func beginAudioSession(onTextChange: @escaping (String) -> Void) {
        // Cancel any active task
        stopRecording()

        let audioSession = AVAudioSession.sharedInstance()
        do {
            try audioSession.setCategory(.record, mode: .measurement, options: .duckOthers)
            try audioSession.setActive(true, options: .notifyOthersOnDeactivation)
        } catch {
            permissionError = "Audio session failed: \(error.localizedDescription)"
            return
        }

        let request = SFSpeechAudioBufferRecognitionRequest()
        request.shouldReportPartialResults = true
        self.recognitionRequest = request

        let inputNode = audioEngine.inputNode

        recognitionTask = speechRecognizer?.recognitionTask(with: request) { [weak self] result, error in
            Task { @MainActor in
                guard let self = self else { return }
                if let result = result {
                    let best = result.bestTranscription.formattedString
                    self.transcribedText = best
                    onTextChange(best)
                }

                if error != nil || (result?.isFinal ?? false) {
                    self.stopRecording()
                }
            }
        }

        let recordingFormat = inputNode.outputFormat(forBus: 0)
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { buffer, _ in
            request.append(buffer)
        }

        audioEngine.prepare()
        do {
            try audioEngine.start()
            isRecording = true
        } catch {
            permissionError = "Could not start audio engine: \(error.localizedDescription)"
            stopRecording()
        }
    }

    func stopRecording() {
        if audioEngine.isRunning {
            audioEngine.stop()
            audioEngine.inputNode.removeTap(onBus: 0)
        }
        recognitionRequest?.endAudio()
        recognitionTask?.cancel()
        recognitionRequest = nil
        recognitionTask = nil
        isRecording = false

        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }

    deinit {
        if audioEngine.isRunning {
            audioEngine.stop()
            audioEngine.inputNode.removeTap(onBus: 0)
        }
        recognitionTask?.cancel()
    }
}
