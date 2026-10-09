import Foundation
import UIKit

/// Sends real-time application logs, unhandled exceptions, and diagnostics
/// directly to the VPS server (`/Neurons/api/client_log.php`).
public enum RemoteLogger {

    private static let endpoint = URL(string: "https://medigyaan.com/Neurons/api/client_log.php")!
    private static let queue = DispatchQueue(label: "com.corp.medigyaan.remotelogger", qos: .utility)

    public static func initializeCrashReporting() {
        // Log application startup
        log(tag: "AppLifecycle", message: "Application launched - iOS \(UIDevice.current.systemVersion) - \(UIDevice.current.model)")

        // Catch NSExceptions (e.g. fatal Objective-C / UIKit exceptions)
        NSSetUncaughtExceptionHandler { exception in
            let symbols = exception.callStackSymbols.joined(separator: "\n")
            let details: [String: Any] = [
                "tag": "CRASH_NSException",
                "name": exception.name.rawValue,
                "reason": exception.reason ?? "Unknown reason",
                "userInfo": "\(exception.userInfo ?? [:])",
                "stack": symbols
            ]
            syncSend(payload: details)
        }

        // Catch POSIX Signals (SIGSEGV, SIGABRT, SIGBUS, SIGILL, SIGFPE)
        for sig in [SIGABRT, SIGSEGV, SIGBUS, SIGILL, SIGFPE] {
            signal(sig) { signum in
                let symbols = Thread.callStackSymbols.joined(separator: "\n")
                let details: [String: Any] = [
                    "tag": "CRASH_Signal",
                    "signal": signum,
                    "signal_name": signalName(signum),
                    "stack": symbols
                ]
                syncSend(payload: details)
                // Re-raise default signal handler to terminate
                signal(signum, SIG_DFL)
                raise(signum)
            }
        }
    }

    public static func log(tag: String, message: String, metadata: [String: Any] = [:]) {
        queue.async {
            var payload = metadata
            payload["tag"] = tag
            payload["message"] = message
            payload["timestamp"] = ISO8601DateFormatter().string(from: Date())
            send(payload: payload)
        }
    }

    private static func send(payload: [String: Any]) {
        guard let data = try? JSONSerialization.data(withJSONObject: payload) else { return }
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(APIConfig.appSignature, forHTTPHeaderField: "X-App-Signature")
        request.setValue(APIConfig.userAgent, forHTTPHeaderField: "User-Agent")
        request.httpBody = data
        request.timeoutInterval = 10

        URLSession.shared.dataTask(with: request).resume()
    }

    private static func syncSend(payload: [String: Any]) {
        guard let data = try? JSONSerialization.data(withJSONObject: payload) else { return }
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(APIConfig.appSignature, forHTTPHeaderField: "X-App-Signature")
        request.setValue(APIConfig.userAgent, forHTTPHeaderField: "User-Agent")
        request.httpBody = data
        request.timeoutInterval = 5

        let semaphore = DispatchSemaphore(value: 0)
        let session = URLSession(configuration: .ephemeral)
        let task = session.dataTask(with: request) { _, _, _ in
            semaphore.signal()
        }
        task.resume()
        _ = semaphore.wait(timeout: .now() + 3.0)
    }

    private static func signalName(_ sig: Int32) -> String {
        switch sig {
        case SIGABRT: return "SIGABRT"
        case SIGSEGV: return "SIGSEGV"
        case SIGBUS: return "SIGBUS"
        case SIGILL: return "SIGILL"
        case SIGFPE: return "SIGFPE"
        default: return "SIGNAL_\(sig)"
        }
    }
}
