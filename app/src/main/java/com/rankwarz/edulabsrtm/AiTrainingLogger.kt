package com.rankwarz.edulabsrtm

import android.content.Context
import android.util.Log
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/**
 * Persists AI exchanges (prompt + reply + provider/model + source screen) to the
 * server's `ai_training_log` table so the data can be used for model training.
 *
 * All calls are fire-and-forget: work is posted to a small single-thread executor
 * and network failures are swallowed silently so logging never affects UX.
 */
object AiTrainingLogger {

    private const val TAG = "AiTrainingLogger"
    private const val ENDPOINT = "https://medigyaan.xyz/Neurons/ai_training_log.php"
    private val JSON = "application/json; charset=utf-8".toMediaType()

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .writeTimeout(10, TimeUnit.SECONDS)
        .build()

    private val executor = Executors.newSingleThreadExecutor { r ->
        Thread(r, "ai-training-log").apply { isDaemon = true }
    }

    /**
     * @param source   feature: "ai_chat" | "ask_ai" | "thesis" | "poster" | "predict" | "other"
     * @param provider model provider actually used ("" when unknown)
     * @param model    model id actually used
     * @param prompt   full prompt / messages that produced the reply
     * @param response the model's reply ("" for failures)
     * @param status   "completed" or "failed"
     * @param context  optional extra JSON context (question id, mode, chapter, etc.)
     */
    fun log(
        context: Context,
        source: String,
        provider: String,
        model: String,
        prompt: String,
        response: String,
        status: String = "completed",
        contextJson: String = "",
        durationMs: Long = 0L
    ) {
        if (prompt.isBlank() && response.isBlank()) return
        executor.execute {
            try {
                val userId = context.getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
                    .getInt("user_id", 0)
                val payload = JSONObject()
                    .put("source", source)
                    .put("user_id", userId)
                    .put("provider", provider)
                    .put("model", model)
                    .put("prompt", prompt.take(450_000))
                    .put("response", response.take(450_000))
                    .put("status", status)
                    .put("context", contextJson.take(18_000))
                    .put("duration_ms", durationMs)
                val body = payload.toString().toRequestBody(JSON)
                val request = Request.Builder()
                    .url(ENDPOINT)
                    .addHeader("X-App-Signature", "EduLabsRTM_Secure_v1_2026")
                    .post(body)
                    .build()
                runCatching { client.newCall(request).execute().use { it.body?.string() } }
            } catch (e: Throwable) {
                Log.d(TAG, "training log dropped: ${e.message}")
            }
        }
    }

    /** Convenience overload that uses the application context (no Activity needed). */
    fun log(
        source: String,
        provider: String,
        model: String,
        prompt: String,
        response: String,
        status: String = "completed",
        contextJson: String = "",
        durationMs: Long = 0L
    ) {
        try {
            log(
                context = EduLabsApplication.instance.applicationContext,
                source = source,
                provider = provider,
                model = model,
                prompt = prompt,
                response = response,
                status = status,
                contextJson = contextJson,
                durationMs = durationMs
            )
        } catch (e: Throwable) {
            // Application not initialised yet — drop silently.
        }
    }
}
