package com.rankwarz.edulabsrtm

import android.app.Activity
import android.content.Context
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.text.Html
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.core.content.ContextCompat
import androidx.appcompat.app.AlertDialog as AppCompatAlertDialog
import androidx.recyclerview.widget.RecyclerView
import com.android.volley.DefaultRetryPolicy
import com.android.volley.Request
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import com.bumptech.glide.Glide
import org.json.JSONArray
import org.json.JSONObject

class ReviewAdapter(
    rawReviewArray: JSONArray
) : RecyclerView.Adapter<ReviewAdapter.ViewHolder>() {

    companion object {
        private const val IMAGE_BASE_URL = "https://medigyaan.xyz/Neurons/"
        private const val TAG = "REVIEW_DEBUG"
    }

    private val reviewArray = JSONArray()

    init {
        val uniqueMap = LinkedHashMap<String, JSONObject>()

        for (i in 0 until rawReviewArray.length()) {
            val item = rawReviewArray.optJSONObject(i) ?: continue

            val questionId = item.optInt("question_id", -1)
            val questionText = item.optString(
                "question",
                item.optString("question_text", "")
            )

            val key = if (questionId > 0) "ID_$questionId" else questionText.trim()

            val existing = uniqueMap[key]
            if (existing == null) {
                uniqueMap[key] = item
            } else {
                val existingScore = calculateCompleteness(existing)
                val newScore = calculateCompleteness(item)
                if (newScore >= existingScore) {
                    uniqueMap[key] = item
                }
            }
        }

        uniqueMap.values.forEach { reviewArray.put(it) }

        Log.d(TAG, "Final filtered review count = ${reviewArray.length()}")
    }

    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val qText: TextView = view.findViewById(R.id.itemQuestion)
        val uAns: TextView = view.findViewById(R.id.itemUserAnswer)
        val cAns: TextView = view.findViewById(R.id.itemCorrectAnswer)
        val explanation: TextView = view.findViewById(R.id.itemExplanation)

        val optionA: TextView = view.findViewById(R.id.optionA)
        val optionB: TextView = view.findViewById(R.id.optionB)
        val optionC: TextView = view.findViewById(R.id.optionC)
        val optionD: TextView = view.findViewById(R.id.optionD)

        val questionImage: ImageView = view.findViewById(R.id.questionImage)
        val askAiBtn: Button = view.findViewById(R.id.askAiBtn)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_review_row, parent, false)
        return ViewHolder(view)
    }

    override fun getItemCount(): Int = reviewArray.length()

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val item = reviewArray.optJSONObject(position) ?: return
        val context = holder.itemView.context

        val question = item.optString(
            "question",
            item.optString("question_text", "Question not available")
        )

        val optionA = item.optString("option_a", "")
        val optionB = item.optString("option_b", "")
        val optionC = item.optString("option_c", "")
        val optionD = item.optString("option_d", "")

        val image = item.optString(
            "image_url",
            item.optString("question_image", "")
        )

        val userAnswerRaw = item.optString(
            "selected_option",
            item.optString(
                "user_answer",
                item.optString("your_answer", "")
            )
        )

        val correctAnswerRaw = item.optString(
            "correct_option",
            item.optString("correct_answer", "N/A")
        )

        val explanation = item.optString("explanation", "")

        val userAnswer = normalizeAnswer(userAnswerRaw)
        val correctAnswer = normalizeAnswer(correctAnswerRaw)

        val userAnswerText = answerToText(userAnswer, optionA, optionB, optionC, optionD)
        val correctAnswerText = answerToText(correctAnswer, optionA, optionB, optionC, optionD)

        holder.qText.text = "Q${position + 1}: $question"
        holder.optionA.text = "A. $optionA"
        holder.optionB.text = "B. $optionB"
        holder.optionC.text = "C. $optionC"
        holder.optionD.text = "D. $optionD"

        holder.uAns.text = if (userAnswer.isBlank()) {
            "Your Answer: Not Answered"
        } else {
            "Your Answer: $userAnswer → $userAnswerText"
        }

        holder.cAns.text = "Correct Answer: $correctAnswer → $correctAnswerText"

        if (image.isNotEmpty() && image != "null") {
            holder.questionImage.visibility = View.VISIBLE
            val imgUrl = if (image.startsWith("http")) image else IMAGE_BASE_URL + image
            Glide.with(context)
                .load(imgUrl.replace(" ", "%20"))
                .into(holder.questionImage)
        } else {
            holder.questionImage.visibility = View.GONE
        }

        if (explanation.isNotEmpty() && explanation != "null") {
            holder.explanation.visibility = View.VISIBLE
            holder.explanation.text = aiMarkdownSpannable("Explanation:\n$explanation")
        } else {
            holder.explanation.visibility = View.GONE
        }

        val isCorrect = when {
            item.has("is_correct") -> readBoolean(item, "is_correct")
            else -> userAnswer.isNotBlank() && userAnswer.equals(correctAnswer, true)
        }

        holder.uAns.setTextColor(
            if (isCorrect) Color.parseColor("#2E7D32") else Color.RED
        )
        holder.cAns.setTextColor(Color.parseColor("#1565C0"))

        resetOptionColors(holder)
        highlightCorrect(holder, correctAnswer)

        if (!isCorrect && userAnswer.isNotBlank()) {
            highlightWrong(holder, userAnswer)
        }

        holder.askAiBtn.setOnClickListener {
            val qId = item.optInt("question_id", 0)
            val optionA = item.optString("option_a", "")
            val optionB = item.optString("option_b", "")
            val optionC = item.optString("option_c", "")
            val optionD = item.optString("option_d", "")
            val options = listOfNotNull(
                if (optionA.isNotBlank()) "A. $optionA" else null,
                if (optionB.isNotBlank()) "B. $optionB" else null,
                if (optionC.isNotBlank()) "C. $optionC" else null,
                if (optionD.isNotBlank()) "D. $optionD" else null
            )
            val act = context as? Activity
            if (act != null) {
                AiChatDialogHelper.openAskAiDialog(
                    activity = act,
                    questionId = qId,
                    question = question,
                    options = options,
                    correctAnswer = correctAnswer,
                    explanation = explanation
                )
            }
        }
    }

    private fun normalizeAnswer(value: String): String {
        val v = value.trim()
        return when {
            v.equals("A", true) -> "A"
            v.equals("B", true) -> "B"
            v.equals("C", true) -> "C"
            v.equals("D", true) -> "D"
            else -> ""
        }
    }

    private fun answerToText(
        answer: String,
        optionA: String,
        optionB: String,
        optionC: String,
        optionD: String
    ): String {
        return when (answer.uppercase()) {
            "A" -> optionA
            "B" -> optionB
            "C" -> optionC
            "D" -> optionD
            else -> ""
        }
    }

    private fun readBoolean(item: JSONObject, key: String): Boolean {
        return when (val value = item.opt(key)) {
            is Boolean -> value
            is Int -> value == 1
            is Long -> value == 1L
            is String -> value.equals("true", true) || value == "1"
            else -> false
        }
    }

    private fun createOptionDrawable(bgColor: Int): GradientDrawable {
        return GradientDrawable().apply {
            shape = GradientDrawable.RECTANGLE
            cornerRadius = 14f
            setColor(bgColor)
        }
    }

    private fun resetOptionColors(holder: ViewHolder) {
        val context = holder.itemView.context
        val defaultBg = ContextCompat.getColor(context, R.color.option_card_bg_default)
        val defaultText = ContextCompat.getColor(context, R.color.colorOnSurface)
        val options = listOf(holder.optionA, holder.optionB, holder.optionC, holder.optionD)
        options.forEach { opt ->
            opt.background = createOptionDrawable(defaultBg)
            opt.setTextColor(defaultText)
        }
    }

    private fun highlightCorrect(holder: ViewHolder, correctAnswer: String) {
        val target = when (correctAnswer.uppercase()) {
            "A" -> holder.optionA
            "B" -> holder.optionB
            "C" -> holder.optionC
            "D" -> holder.optionD
            else -> null
        }
        target?.apply {
            background = createOptionDrawable(Color.parseColor("#2E7D32"))
            setTextColor(Color.WHITE)
        }
    }

    private fun highlightWrong(holder: ViewHolder, userAnswer: String) {
        val target = when (userAnswer.uppercase()) {
            "A" -> holder.optionA
            "B" -> holder.optionB
            "C" -> holder.optionC
            "D" -> holder.optionD
            else -> null
        }
        target?.apply {
            background = createOptionDrawable(Color.parseColor("#C62828"))
            setTextColor(Color.WHITE)
        }
    }

    private fun calculateCompleteness(item: JSONObject): Int {
        var score = 0
        val fields = listOf(
            "question",
            "question_text",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "selected_option",
            "user_answer",
            "correct_option",
            "correct_answer",
            "explanation",
            "image_url",
            "question_image",
            "bot_answers"
        )

        for (key in fields) {
            val value = item.optString(key, "")
            if (value.isNotBlank() && value != "null") score++
        }
        return score
    }
}