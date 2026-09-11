package com.rankwarz.edulabsrtm

import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Handler
import android.os.Looper
import android.text.Html
import android.util.Log
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import androidx.core.content.ContextCompat
import com.android.volley.DefaultRetryPolicy
import com.android.volley.Request
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import com.google.android.material.card.MaterialCardView
import org.json.JSONObject
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import java.util.Locale

/**
 * Reusable interactive AI Chat Box helper.
 * Provides the same full-screen chat experience as MCQActivity (with follow-ups,
 * WhatsApp-styled speech bubbles, typing effect, Markdown formatting, and training logs)
 * to result activities and review screens.
 */
object AiChatDialogHelper {

    private const val TAG = "AiChatDialogHelper"
    private const val AI_URL = "https://medigyaan.xyz/Neurons/ask_ai2.php"

    fun startVoiceInput(activity: Activity, onResult: (String) -> Unit) {
        if (activity.isFinishing || activity.isDestroyed) return
        try {
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault())
                putExtra(RecognizerIntent.EXTRA_PROMPT, "Speak to MediGyaan AI…")
            }
            if (SpeechRecognizer.isRecognitionAvailable(activity)) {
                val recognizer = SpeechRecognizer.createSpeechRecognizer(activity)
                recognizer.setRecognitionListener(object : RecognitionListener {
                    override fun onReadyForSpeech(params: Bundle?) {
                        Toast.makeText(activity, "Listening… Speak now", Toast.LENGTH_SHORT).show()
                    }
                    override fun onBeginningOfSpeech() {}
                    override fun onRmsChanged(rmsdB: Float) {}
                    override fun onBufferReceived(buffer: ByteArray?) {}
                    override fun onEndOfSpeech() {}
                    override fun onError(error: Int) {
                        try {
                            activity.startActivityForResult(intent, 9091)
                        } catch (_: Exception) {
                            Toast.makeText(activity, "Speech recognition unavailable", Toast.LENGTH_SHORT).show()
                        }
                    }
                    override fun onResults(results: Bundle?) {
                        val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                        val text = matches?.firstOrNull()
                        if (!text.isNullOrBlank()) {
                            onResult(text)
                        }
                        recognizer.destroy()
                    }
                    override fun onPartialResults(partialResults: Bundle?) {}
                    override fun onEvent(eventType: Int, params: Bundle?) {}
                })
                recognizer.startListening(intent)
            } else {
                activity.startActivityForResult(intent, 9091)
            }
        } catch (e: Exception) {
            Toast.makeText(activity, "Voice input unavailable on this device", Toast.LENGTH_SHORT).show()
        }
    }

    fun openAskAiDialog(
        activity: Activity,
        questionId: Int,
        question: String,
        options: List<String> = emptyList(),
        correctAnswer: String = "",
        explanation: String = ""
    ) {
        if (activity.isFinishing || activity.isDestroyed) return

        val cleanQuestion = question.trim()
        if (cleanQuestion.isEmpty()) {
            Toast.makeText(activity, "No question available", Toast.LENGTH_SHORT).show()
            return
        }

        val inputContainer = LinearLayout(activity).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(30, 20, 30, 20)
        }

        val input = EditText(activity).apply {
            hint = "Ask something like: explain this question"
            setText("Explain this question in simple exam-focused language.")
            setPadding(20, 20, 20, 20)
            setTextColor(ContextCompat.getColor(activity, R.color.text_primary))
            setHintTextColor(ContextCompat.getColor(activity, R.color.text_secondary))
            layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        }

        val voiceBtn = ImageButton(activity).apply {
            setImageResource(android.R.drawable.ic_btn_speak_now)
            background = GradientDrawable().apply {
                shape = GradientDrawable.OVAL
                setColor(ContextCompat.getColor(activity, R.color.primary))
            }
            setColorFilter(Color.WHITE)
            setPadding(16, 16, 16, 16)
            layoutParams = LinearLayout.LayoutParams(100, 100).apply { marginStart = 12 }
            setOnClickListener {
                startVoiceInput(activity) { spoken ->
                    val cur = input.text.toString().trim()
                    input.setText(if (cur.isBlank()) spoken else "$cur $spoken")
                    input.setSelection(input.text.length)
                }
            }
        }

        inputContainer.addView(input)
        inputContainer.addView(voiceBtn)

        val previewMessage = buildString {
            append("Question:\n\n")
            append(Html.fromHtml(cleanQuestion, Html.FROM_HTML_MODE_LEGACY))
            if (options.isNotEmpty()) {
                append("\n\nOptions:\n")
                options.forEach { opt ->
                    append(opt).append("\n")
                }
            }
            if (correctAnswer.isNotBlank()) {
                append("\nCorrect Answer: ").append(correctAnswer)
            }
            if (explanation.isNotBlank() && explanation != "null") {
                append("\n\nExplanation:\n").append(explanation.trim())
            }
        }

        AlertDialog.Builder(activity)
            .setTitle("Ask AI")
            .setMessage(previewMessage)
            .setView(inputContainer)
            .setPositiveButton("Ask") { _, _ ->
                val userQuery = input.text.toString().trim().ifEmpty {
                    "Explain this question clearly"
                }
                fetchInitialAiAnswer(
                    activity = activity,
                    questionId = questionId,
                    question = cleanQuestion,
                    userQuery = userQuery,
                    baseExplanation = explanation,
                    correctAnswer = correctAnswer
                )
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun fetchInitialAiAnswer(
        activity: Activity,
        questionId: Int,
        question: String,
        userQuery: String,
        baseExplanation: String,
        correctAnswer: String
    ) {
        if (activity.isFinishing || activity.isDestroyed) return

        val loadingDialog = AlertDialog.Builder(activity)
            .setTitle("AI Tutor")
            .setMessage("Analyzing question...")
            .setCancelable(false)
            .show()

        val requestQueue = Volley.newRequestQueue(activity.applicationContext)

        val request = object : StringRequest(
            Request.Method.POST,
            AI_URL,
            { response ->
                try {
                    if (!activity.isFinishing && !activity.isDestroyed) {
                        loadingDialog.dismiss()
                    }
                    val json = JSONObject(response)
                    var aiText = when {
                        json.optBoolean("success", false) -> {
                            json.optString("answer", "")
                                .ifEmpty { json.optString("content", "") }
                                .ifEmpty { json.optString("message", "") }
                        }
                        json.has("choices") -> {
                            json.getJSONArray("choices")
                                .getJSONObject(0)
                                .getJSONObject("message")
                                .getString("content")
                        }
                        else -> json.optString("answer", response)
                    }

                    if (aiText.isBlank()) {
                        aiText = "No AI response received. Please try again."
                    }

                    AiTrainingLogger.log(
                        context = activity,
                        source = "result_ask_ai",
                        provider = "openai",
                        model = "ask_ai2",
                        prompt = "[$questionId] $question\nUser: $userQuery",
                        response = aiText,
                        status = "completed"
                    )

                    showChatBox(
                        activity = activity,
                        questionId = questionId,
                        question = question,
                        correctAnswer = correctAnswer,
                        baseExplanation = baseExplanation,
                        initialQuery = userQuery,
                        initialAiText = aiText
                    )
                } catch (e: Exception) {
                    Log.e(TAG, "AI parse error: ${e.message}", e)
                    if (!activity.isFinishing && !activity.isDestroyed) {
                        loadingDialog.dismiss()
                        Toast.makeText(activity, "AI parse error", Toast.LENGTH_SHORT).show()
                    }
                }
            },
            { error ->
                Log.e(TAG, "AI request error: ${error.message}", error)
                if (!activity.isFinishing && !activity.isDestroyed) {
                    loadingDialog.dismiss()
                    Toast.makeText(activity, "AI request failed", Toast.LENGTH_SHORT).show()
                }
            }
        ) {
            override fun getParams(): MutableMap<String, String> {
                val prefs = activity.getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
                val userId = prefs.getInt("user_id", 0)
                return hashMapOf(
                    "question_id" to questionId.toString(),
                    "question" to question,
                    "query" to userQuery,
                    "explanation" to baseExplanation,
                    "correct_answer" to correctAnswer,
                    "user_id" to userId.toString(),
                    "timestamp" to System.currentTimeMillis().toString(),
                    "random" to (100000..999999).random().toString()
                )
            }

            override fun getHeaders(): MutableMap<String, String> {
                return hashMapOf(
                    "Cache-Control" to "no-cache",
                    "Pragma" to "no-cache"
                )
            }
        }

        request.retryPolicy = DefaultRetryPolicy(45000, 0, 1f)
        request.setShouldCache(false)
        requestQueue.add(request)
    }

    fun showChatBox(
        activity: Activity,
        questionId: Int,
        question: String,
        correctAnswer: String,
        baseExplanation: String,
        initialQuery: String,
        initialAiText: String
    ) {
        if (activity.isFinishing || activity.isDestroyed) return

        val chatHistory = StringBuilder()
        chatHistory.append("System: You are a helpful medical exam tutor. Base your answers on the provided question and explanation.\n")
        if (initialQuery.isNotBlank()) {
            chatHistory.append("User: $initialQuery\n")
        }
        chatHistory.append("Assistant: $initialAiText\n")

        val container = LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
            setBackgroundResource(R.drawable.bg_chat_wallpaper)
        }

        val scroll = ScrollView(activity).apply {
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                0,
                1f
            )
            isFillViewport = true
        }

        val chatLayout = LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(20, 20, 20, 20)
        }
        scroll.addView(chatLayout)

        val inputCard = MaterialCardView(activity).apply {
            radius = 0f
            cardElevation = 20f
            setCardBackgroundColor(ContextCompat.getColor(activity, R.color.colorSurface))
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
        }

        val inputRow = LinearLayout(activity).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(20, 12, 20, 12)
            gravity = Gravity.CENTER_VERTICAL
        }
        inputCard.addView(inputRow)

        val inputBox = EditText(activity).apply {
            hint = "Ask a follow-up question..."
            background = null
            maxLines = 4
            setTextColor(ContextCompat.getColor(activity, R.color.text_primary))
            setHintTextColor(ContextCompat.getColor(activity, R.color.text_secondary))
            layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        }

        val sendBtn = ImageButton(activity).apply {
            setImageResource(android.R.drawable.ic_menu_send)
            background = GradientDrawable().apply {
                shape = GradientDrawable.OVAL
                setColor(ContextCompat.getColor(activity, R.color.primary))
            }
            setColorFilter(Color.WHITE)
            setPadding(20, 20, 20, 20)
            layoutParams = LinearLayout.LayoutParams(110, 110).apply { marginStart = 10 }
        }

        val voiceBtn = ImageButton(activity).apply {
            setImageResource(android.R.drawable.ic_btn_speak_now)
            background = GradientDrawable().apply {
                shape = GradientDrawable.OVAL
                setColor(ContextCompat.getColor(activity, R.color.primary))
            }
            setColorFilter(Color.WHITE)
            setPadding(20, 20, 20, 20)
            layoutParams = LinearLayout.LayoutParams(110, 110).apply { marginStart = 10 }
            setOnClickListener {
                startVoiceInput(activity) { spoken ->
                    val cur = inputBox.text.toString().trim()
                    inputBox.setText(if (cur.isBlank()) spoken else "$cur $spoken")
                    inputBox.setSelection(inputBox.text.length)
                }
            }
        }

        inputRow.addView(inputBox)
        inputRow.addView(voiceBtn)
        inputRow.addView(sendBtn)

        container.addView(scroll)
        container.addView(inputCard)

        val dialog = AlertDialog.Builder(activity, android.R.style.Theme_NoTitleBar_Fullscreen)
            .setView(container)
            .create()

        val header = LinearLayout(activity).apply {
            orientation = LinearLayout.HORIZONTAL
            setBackgroundColor(ContextCompat.getColor(activity, R.color.primary))
            setPadding(36, 36, 36, 36)
            gravity = Gravity.CENTER_VERTICAL

            val title = TextView(context).apply {
                text = "🤖 AI Medical Tutor"
                setTextColor(Color.WHITE)
                textSize = 18f
                setTypeface(null, Typeface.BOLD)
                layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
            }
            val close = ImageButton(context).apply {
                setImageResource(android.R.drawable.ic_menu_close_clear_cancel)
                setBackgroundColor(Color.TRANSPARENT)
                setColorFilter(Color.WHITE)
                setPadding(10, 10, 10, 10)
                setOnClickListener { dialog.dismiss() }
            }
            addView(title)
            addView(close)
        }
        container.addView(header, 0)

        dialog.show()

        if (initialQuery.isNotBlank()) {
            addMessage(activity, chatLayout, initialQuery, isUser = true)
        }
        if (baseExplanation.isNotBlank() && baseExplanation != "null") {
            addMessage(activity, chatLayout, "📖 Book Explanation:\n$baseExplanation", isUser = false)
        }
        streamMessage(activity, chatLayout, initialAiText)

        sendBtn.setOnClickListener {
            val userText = inputBox.text.toString().trim()
            if (userText.isEmpty()) return@setOnClickListener

            addMessage(activity, chatLayout, userText, isUser = true)
            chatHistory.append("User: $userText\n")
            inputBox.setText("")

            fetchFollowUp(
                activity = activity,
                questionId = questionId,
                question = question,
                baseExplanation = baseExplanation,
                userQuery = userText,
                chatHistory = chatHistory,
                chatLayout = chatLayout
            )
        }
    }

    private fun addMessage(context: Context, parent: LinearLayout, text: String, isUser: Boolean) {
        val card = MaterialCardView(context).apply {
            radius = 32f
            cardElevation = 2f
            setCardBackgroundColor(
                if (isUser) ContextCompat.getColor(context, R.color.whatsapp_bubble_sent)
                else ContextCompat.getColor(context, R.color.whatsapp_bubble_received)
            )
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply {
                gravity = if (isUser) Gravity.END else Gravity.START
                setMargins(
                    if (isUser) 100 else 20,
                    12,
                    if (isUser) 20 else 100,
                    12
                )
            }
        }

        val tv = TextView(context).apply {
            this.text = if (isUser) text else aiMarkdownSpannable(text)
            textSize = 15f
            setTextColor(
                if (isUser) ContextCompat.getColor(context, R.color.whatsapp_bubble_sent_text)
                else ContextCompat.getColor(context, R.color.whatsapp_bubble_received_text)
            )
            setPadding(35, 20, 35, 20)
        }
        card.addView(tv)
        parent.addView(card)

        (card.parent.parent as? ScrollView)?.post {
            (card.parent.parent as? ScrollView)?.fullScroll(View.FOCUS_DOWN)
        }
    }

    private fun streamMessage(context: Context, parent: LinearLayout, fullText: String) {
        val card = MaterialCardView(context).apply {
            radius = 32f
            cardElevation = 2f
            setCardBackgroundColor(ContextCompat.getColor(context, R.color.whatsapp_bubble_received))
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply {
                gravity = Gravity.START
                setMargins(20, 12, 100, 12)
            }
        }

        val tv = TextView(context).apply {
            textSize = 15f
            setTextColor(ContextCompat.getColor(context, R.color.whatsapp_bubble_received_text))
            setPadding(35, 20, 35, 20)
        }
        card.addView(tv)
        parent.addView(card)

        val handler = Handler(Looper.getMainLooper())
        var index = 0
        val chunkSize = 6

        val runnable = object : Runnable {
            override fun run() {
                index += chunkSize
                val displayed = if (index >= fullText.length) fullText else fullText.substring(0, index)
                tv.text = if (index >= fullText.length) aiMarkdownSpannable(fullText) else displayed
                (card.parent.parent as? ScrollView)?.post {
                    (card.parent.parent as? ScrollView)?.fullScroll(View.FOCUS_DOWN)
                }
                if (index < fullText.length) {
                    handler.postDelayed(this, 18)
                }
            }
        }
        handler.post(runnable)
    }

    private fun fetchFollowUp(
        activity: Activity,
        questionId: Int,
        question: String,
        baseExplanation: String,
        userQuery: String,
        chatHistory: StringBuilder,
        chatLayout: LinearLayout
    ) {
        val requestQueue = Volley.newRequestQueue(activity.applicationContext)

        val request = object : StringRequest(
            Request.Method.POST,
            AI_URL,
            { response ->
                try {
                    val json = JSONObject(response)
                    val reply = json.optString("answer", json.optString("content", "No response"))
                    chatHistory.append("Assistant: $reply\n")

                    AiTrainingLogger.log(
                        context = activity,
                        source = "result_ask_ai",
                        provider = "openai",
                        model = "ask_ai2",
                        prompt = userQuery,
                        response = reply,
                        status = "completed"
                    )

                    streamMessage(activity, chatLayout, reply)
                } catch (e: Exception) {
                    addMessage(activity, chatLayout, "⚠️ Parse error", isUser = false)
                }
            },
            {
                addMessage(activity, chatLayout, "⚠️ Network error", isUser = false)
            }
        ) {
            override fun getParams(): MutableMap<String, String> {
                val prefs = activity.getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
                val userId = prefs.getInt("user_id", 0)
                return hashMapOf(
                    "question_id" to questionId.toString(),
                    "question" to question,
                    "explanation" to baseExplanation,
                    "query" to userQuery,
                    "chat_history" to chatHistory.toString(),
                    "mode" to "chat",
                    "user_id" to userId.toString(),
                    "timestamp" to System.currentTimeMillis().toString(),
                    "random" to (0..999999).random().toString()
                )
            }

            override fun getHeaders(): MutableMap<String, String> {
                return hashMapOf(
                    "Cache-Control" to "no-cache",
                    "Pragma" to "no-cache"
                )
            }
        }

        request.setShouldCache(false)
        requestQueue.add(request)
    }
}