import Foundation

/// Persists AI exchanges (prompt + reply + provider/model + source screen) to the
/// server's `ai_training_log.php` table so the data can be used for model training.
/// Strictly ports Android's `AiTrainingLogger.kt`.
///
/// All calls are fire-and-forget: background URLSession task where network failures
/// are swallowed silently so logging never blocks UX.
enum AiTrainingLogger {

    private static let endpoint = URL(string: "https://medigyaan.com/Neurons/ai_training_log.php")!

    /// Asynchronous fire-and-forget logging.
    static func log(
        userId: Int,
        source: String,
        provider: String = "gemini",
        model: String = "gemini-2.5-flash",
        prompt: String,
        response: String,
        status: String = "completed",
        contextJson: String = "",
        durationMs: Int = 0
    ) {
        guard !prompt.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ||
              !response.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return
        }

        let payload: [String: Any] = [
            "source": source,
            "user_id": userId,
            "provider": provider,
            "model": model,
            "prompt": String(prompt.prefix(450_000)),
            "response": String(response.prefix(450_000)),
            "status": status,
            "context": String(contextJson.prefix(18_000)),
            "duration_ms": durationMs
        ]

        guard let body = try? JSONSerialization.data(withJSONObject: payload) else { return }

        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.setValue("application/json; charset=utf-8", forHTTPHeaderField: "Content-Type")
        request.setValue("EduLabsRTM_Secure_v1_2026", forHTTPHeaderField: "X-App-Signature")
        request.httpBody = body
        request.timeoutInterval = 10

        let task = URLSession.shared.dataTask(with: request) { _, _, _ in
            // Fire and forget; errors dropped silently
        }
        task.resume()
    }
}
