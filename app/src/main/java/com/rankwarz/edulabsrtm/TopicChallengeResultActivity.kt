package com.rankwarz.edulabsrtm

import android.content.Intent
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.Html
import android.util.Log
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.*
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.ComposeView
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.graphics.Color as ComposeColor
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AlertDialog
import androidx.compose.ui.res.vectorResource
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.android.volley.Request
import com.android.volley.toolbox.JsonObjectRequest
import com.android.volley.toolbox.Volley
import com.bumptech.glide.Glide
import com.google.firebase.database.DataSnapshot
import com.google.firebase.database.DatabaseError
import com.google.firebase.database.DatabaseReference
import com.google.firebase.database.FirebaseDatabase
import com.google.firebase.database.ValueEventListener
import com.rankwarz.edulabsrtm.ui.theme.EduLabsRTMThemeFromPreferences
import org.json.JSONArray
import org.json.JSONObject
import com.android.volley.toolbox.StringRequest
import com.google.android.material.bottomnavigation.BottomNavigationView
import kotlinx.coroutines.launch

class TopicChallengeResultActivity : AppCompatActivity() {

    private val TAG = "RESULT_DEBUG"

    private lateinit var recyclerView: RecyclerView
    private lateinit var statusText: TextView
    private lateinit var scoreText: TextView
    private lateinit var expGainText: TextView
    private lateinit var streakText: TextView
    private lateinit var levelProgress: ProgressBar
    private lateinit var homeBtn: Button

    private lateinit var database: DatabaseReference
    private val requestQueue by lazy { Volley.newRequestQueue(applicationContext) }

    private var currentUserId: Int = 0
    private var isSyncTriggered = false

    private val reviewItems = mutableListOf<ReviewModel>()
    private lateinit var reviewAdapter: ReviewAdapter

    private val chatHistory = StringBuilder()

    private val mergedPlayers = linkedMapOf<String, PlayerRow>()
    private val mergedQuestionIds = linkedSetOf<Int>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        logStep("onCreate() started")

        setContentView(R.layout.activity_challenge_result)

        initViews()

        // =========================
        // SAFE INTENT PARSING
        // Supports BOTH old + new activities
        // =========================

        val challengeId = when {
            intent.hasExtra("CHALLENGE_ID") -> {

                when (val raw = intent.extras?.getString("CHALLENGE_ID")
                    ?: intent.extras?.getInt("CHALLENGE_ID")?.takeIf { it != 0 }
                    ?: intent.extras?.getLong("CHALLENGE_ID")?.takeIf { it != 0L }) {
                    is String -> raw
                    is Int -> raw.toString()
                    is Long -> raw.toString()
                    else -> ""
                }
            }

            else -> ""
        }

        currentUserId = when (val raw = intent.extras?.getString("USER_ID")
            ?: intent.extras?.getInt("USER_ID")?.takeIf { it != 0 }
            ?: intent.extras?.getLong("USER_ID")?.takeIf { it != 0L }) {
            is Int -> raw
            is String -> raw.toIntOrNull() ?: 0
            is Long -> raw.toInt()
            else -> {
                getSharedPreferences("MY_APP", MODE_PRIVATE)
                    .getInt("user_id", 0)
            }
        }

        logStep(
            "Intent loaded -> CHALLENGE_ID=$challengeId, USER_ID=$currentUserId"
        )

        // =========================
        // REVIEW JSON
        // =========================

        val jsonStr = intent.getStringExtra("REVIEW_JSON_STR")

        if (!jsonStr.isNullOrBlank()) {

            logStep("Local review JSON received -> length=${jsonStr.length}")

            val localReviews = parseReviewJson(jsonStr)

            logStep("Local review parsed -> count=${localReviews.size}")

            mergeReviewList(localReviews)

            reviewAdapter.notifyDataSetChanged()

        } else {

            logStep("No local REVIEW_JSON_STR found")
        }

        // =========================
        // FIREBASE FETCH
        // =========================

        if (challengeId.isNotBlank() && challengeId != "0") {

            logStep("Fetching challenge data from Firebase")

            fetchChallengeData(challengeId)

        } else {

            logStep("Skipping Firebase fetch because challengeId is blank/0")
        }

        // =========================
        // BUTTONS
        // =========================

        homeBtn.setOnClickListener {

            logStep("Home button clicked")

            finish()
        }
    }
    private fun initViews() {
        logStep("Binding views")

        statusText = findViewById(R.id.resultStatus)
        scoreText = findViewById(R.id.scoreText)
        expGainText = findViewById(R.id.expGainText)
        streakText = findViewById(R.id.streakText)
        levelProgress = findViewById(R.id.levelProgress)
        recyclerView = findViewById(R.id.reviewRecyclerView)
        homeBtn = findViewById(R.id.homeBtn)
        setupAppBottomNavigation(findViewById<BottomNavigationView>(R.id.bottomNavigation), R.id.nav_home)

        recyclerView.layoutManager = LinearLayoutManager(this)
        reviewAdapter = ReviewAdapter(reviewItems)
        recyclerView.adapter = reviewAdapter

        database = FirebaseDatabase.getInstance().reference

        levelProgress.max = 100
        expGainText.visibility = View.INVISIBLE
        streakText.visibility = View.GONE

        logStep("Views bound successfully")
    }

    private fun parseReviewJson(json: String): List<ReviewModel> {
        val list = mutableListOf<ReviewModel>()

        try {
            val arr = JSONArray(json)
            logStep("parseReviewJson() -> arrayLength=${arr.length()}")

            for (i in 0 until arr.length()) {
                val o = arr.getJSONObject(i)

                val model = ReviewModel(
                    questionId = o.optInt("question_id", o.optInt("qid", 0)),
                    question = cleanText(o.optString("question", o.optString("question_text", "N/A"))),
                    optA = cleanText(o.optString("option_a", o.optString("optA", ""))),
                    optB = cleanText(o.optString("option_b", o.optString("optB", ""))),
                    optC = cleanText(o.optString("option_c", o.optString("optC", ""))),
                    optD = cleanText(o.optString("option_d", o.optString("optD", ""))),
                    userAns = cleanText(
                        o.optString(
                            "user_answer",
                            o.optString("your_answer", o.optString("selected_option", ""))
                        )
                    ),
                    correctAns = cleanText(
                        o.optString(
                            "correct_option",
                            o.optString("correct_answer", "")
                        )
                    ),
                    isCorrect = o.optBoolean("is_correct", o.optInt("is_correct", 0) == 1),
                    explanation = cleanText(o.optString("explanation", "")),
                    imageUrl = cleanImageUrl(
                        o.optString("image_url", o.optString("question_image", ""))
                    )
                )

                logStep(
                    "Parsed item[$i] -> qid=${model.questionId}, " +
                            "userAns=${model.userAns}, correctAns=${model.correctAns}, " +
                            "image=${if (model.imageUrl.isBlank()) "EMPTY" else model.imageUrl}"
                )
                list.add(model)
            }
        } catch (e: Exception) {
            logError("JSON Parsing error", e)
        }

        return list
    }

    private fun fetchChallengeData(challengeId: String) {
        // Try fetching from both paths: "challenges/lobby_ID" and "challenges/ID"
        val cleanId = challengeId.replace("lobby_", "")
        val lobbyPath = "challenges/lobby_$cleanId"
        val directPath = "challenges/$cleanId"

        logStep("fetchChallengeData() -> checking paths: $lobbyPath and $directPath")

        val listener = object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                if (!snapshot.exists()) {
                    // If we checked lobbyPath and failed, try directPath
                    if (snapshot.ref.path.toString().contains("lobby_")) {
                        logStep("Lobby path empty, trying direct path: $directPath")
                        database.child(directPath).addListenerForSingleValueEvent(this)
                    } else {
                        logStep("Both Firebase paths missing for ID: $cleanId")
                    }
                    return
                }

                logStep("Firebase snapshot found at ${snapshot.ref.path}")

                snapshot.child("question_ids").children.forEachIndexed { index, qSnap ->
                    val qid = qSnap.getValue(Int::class.java)
                    if (qid != null) {
                        mergedQuestionIds.add(qid)
                    }
                }

                snapshot.child("players").children.forEachIndexed { index, pSnap ->
                    val pId = pSnap.key ?: return@forEachIndexed

                    // Support both Long and Int types from Firebase
                    val score = when (val s = pSnap.child("score").value) {
                        is Long -> s.toInt()
                        is Int -> s
                        else -> 0
                    }
                    val hp = when (val h = pSnap.child("hp").value) {
                        is Long -> h.toInt()
                        is Int -> h
                        else -> 0
                    }
                    val name = pSnap.child("name").getValue(String::class.java) ?: "Player"

                    mergedPlayers[pId] = PlayerRow(id = pId, name = name,
                        hp = hp,
                        score = score
                    )

                    logStep("Player[$index] -> id=$pId, name=$name, score=$score, hp=$hp")
                }

                updateLeaderboardUI()
                fetchBackendQuestionDetails()
            }

            override fun onCancelled(error: DatabaseError) {
                logError("Firebase fetch cancelled", error.toException())
            }
        }

        // Start search with lobby prefix first
        database.child(lobbyPath).addListenerForSingleValueEvent(listener)
    }

    private fun updateLeaderboardUI() {
        logStep("updateLeaderboardUI() started")

        val myPlayer = mergedPlayers[currentUserId.toString()]
        if (myPlayer == null) {
            logStep("Current user not found in leaderboard -> userId=$currentUserId")
            scoreText.text = "Your player data was not found."
            return
        }

        val sorted = mergedPlayers.values.sortedByDescending { (it.score * 1000) + it.hp }
        val isWin = sorted.firstOrNull()?.id == currentUserId.toString()
        val rank = sorted.indexOfFirst { it.id == currentUserId.toString() } + 1

        statusText.text = if (isWin) "VICTORY! 🏆" else "DEFEAT! 💀"
        statusText.setTextColor(if (isWin) Color.parseColor("#2E7D32") else Color.RED)

        scoreText.text = "Rank #$rank / ${mergedPlayers.size}\nScore: ${myPlayer.score} | HP: ${myPlayer.hp}"

        logStep(
            "Leaderboard -> isWin=$isWin, rank=$rank, total=${mergedPlayers.size}, " +
                    "score=${myPlayer.score}, hp=${myPlayer.hp}"
        )

        if (!isSyncTriggered) {
            syncStats(myPlayer.score, myPlayer.hp, isWin)
            isSyncTriggered = true
        } else {
            logStep("syncStats already triggered once; skipping")
        }
    }

    private fun fetchBackendQuestionDetails() {
        if (mergedQuestionIds.isEmpty()) {
            logStep("No question ids available for backend fetch")
            return
        }

        logStep("fetchBackendQuestionDetails() -> count=${mergedQuestionIds.size}")

        mergedQuestionIds.forEach { qid ->
            val url = "https://medigyaan.xyz/Neurons/api/get_single_question.php?question_id=$qid"
            logStep("Requesting backend question -> qid=$qid, url=$url")

            requestQueue.add(
                JsonObjectRequest(Request.Method.GET, url, null, { res ->
                    try {
                        logStep("Backend response received for qid=$qid")

                        val data = res.optJSONObject("data") ?: res
                        val question = cleanText(data.optString("question"))
                        val optA = cleanText(data.optString("option_a"))
                        val optB = cleanText(data.optString("option_b"))
                        val optC = cleanText(data.optString("option_c"))
                        val optD = cleanText(data.optString("option_d"))
                        val correct = cleanText(data.optString("correct_option"))
                        val explanation = cleanText(data.optString("explanation"))
                        val imageUrl = cleanImageUrl(data.optString("question_image", ""))

                        val item = ReviewModel(
                            questionId = qid,
                            question = question,
                            optA = optA,
                            optB = optB,
                            optC = optC,
                            optD = optD,
                            correctAns = correct,
                            explanation = explanation,
                            imageUrl = imageUrl
                        )

                        logStep(
                            "Backend parsed -> qid=$qid, " +
                                    "imageUrl=${if (imageUrl.isBlank()) "EMPTY" else imageUrl}"
                        )

                        mergeSingleReview(item)
                        reviewAdapter.notifyDataSetChanged()
                    } catch (e: Exception) {
                        logError("Backend parse error for qid=$qid", e)
                    }
                }, { error ->
                    logError("Backend request failed for qid=$qid", error)
                })
            )
        }
    }

    private fun mergeReviewList(incoming: List<ReviewModel>) {
        logStep("mergeReviewList() -> incoming=${incoming.size}")
        incoming.forEach { mergeSingleReview(it) }
    }

    private fun mergeSingleReview(item: ReviewModel) {
        val index = reviewItems.indexOfFirst {
            it.questionId == item.questionId || it.question == item.question
        }

        if (index >= 0) {
            val existing = reviewItems[index]
            logStep("Merging into existing item -> qid=${item.questionId}, index=$index")

            if (existing.question.isBlank()) existing.question = item.question
            if (existing.optA.isBlank()) existing.optA = item.optA
            if (existing.optB.isBlank()) existing.optB = item.optB
            if (existing.optC.isBlank()) existing.optC = item.optC
            if (existing.optD.isBlank()) existing.optD = item.optD
            if (existing.userAns.isBlank() || existing.userAns == "N/A") existing.userAns = item.userAns
            if (existing.correctAns.isBlank() || existing.correctAns == "N/A") existing.correctAns = item.correctAns
            if (existing.explanation.isBlank()) existing.explanation = item.explanation
            if (existing.imageUrl.isBlank()) existing.imageUrl = item.imageUrl

            existing.isCorrect = existing.isCorrect || item.isCorrect
            reviewItems[index] = existing

            logStep(
                "Merge complete -> qid=${existing.questionId}, " +
                        "imageUrl=${if (existing.imageUrl.isBlank()) "EMPTY" else existing.imageUrl}"
            )
        } else {
            reviewItems.add(item)
            logStep(
                "Added new review item -> qid=${item.questionId}, " +
                        "question=${item.question.take(30)}"
            )
        }
    }

    private fun syncStats(score: Int, hp: Int, isWin: Boolean) {
        logStep("syncStats() called -> score=$score, hp=$hp, isWin=$isWin")

        val expGain = when {
            isWin -> 120 + score
            score >= 40 -> 100 + (score / 2)
            else -> 60 + (score / 3)
        }.coerceAtLeast(0)

        val progress = hp.coerceIn(0, 100)

        expGainText.text = "+$expGain EXP"
        expGainText.visibility = View.VISIBLE

        streakText.text = if (isWin) "Winning Streak 🔥" else "Battle Completed"
        streakText.visibility = View.VISIBLE
        streakText.setTextColor(if (isWin) Color.parseColor("#F44336") else Color.parseColor("#616161"))

        levelProgress.max = 100
        levelProgress.progress = progress

        logStep("Stats updated -> expGain=$expGain, progress=$progress")

        expGainText.animate().alpha(1f).setDuration(200).start()
    }

    private fun cleanText(value: String?): String {
        val v = value?.trim().orEmpty()
        return if (
            v.isBlank() ||
            v.equals("null", ignoreCase = true) ||
            v.equals("undefined", ignoreCase = true)
        ) {
            ""
        } else {
            v
        }
    }

    private fun cleanImageUrl(raw: String?): String {
        var cleaned = raw?.trim().orEmpty()

        if (
            cleaned.isBlank() ||
            cleaned.equals("null", ignoreCase = true) ||
            cleaned.equals("undefined", ignoreCase = true)
        ) {
            return ""
        }

        cleaned = cleaned
            .replace("\\", "/")
            .replace("./", "")
            .replace("//", "/")
            .trim()

        if (cleaned.startsWith("http://", ignoreCase = true) ||
            cleaned.startsWith("https://", ignoreCase = true)
        ) {
            return cleaned
        }

        cleaned = cleaned
            .replace("https:/medigyaan.xyz/Neurons/", "")
            .replace("http:/medigyaan.xyz/Neurons/", "")
            .replace("https://medigyaan.xyz/Neurons/", "")
            .replace("http://medigyaan.xyz/Neurons/", "")
            .trimStart('/')

        if (cleaned.startsWith("http://", ignoreCase = true) ||
            cleaned.startsWith("https://", ignoreCase = true)
        ) {
            return cleaned
        }

        return "https://medigyaan.xyz/Neurons/$cleaned"
    }

    private fun safeLoadImage(imageView: ImageView, rawUrl: String?) {
        val safeUrl = cleanImageUrl(rawUrl)

        if (safeUrl.isBlank()) {
            logStep("safeLoadImage() -> no valid URL, hiding ImageView")
            imageView.setImageDrawable(null)
            imageView.visibility = View.GONE
            Glide.with(imageView.context).clear(imageView)
            return
        }

        imageView.visibility = View.VISIBLE
        logStep("safeLoadImage() -> loading $safeUrl")

        Glide.with(imageView.context)
            .load(safeUrl)
            .placeholder(android.R.drawable.ic_menu_gallery)
            .error(android.R.drawable.ic_menu_report_image)
            .into(imageView)
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

    private fun logStep(message: String) {
        Log.d(TAG, message)
    }

    private fun logError(message: String, tr: Throwable? = null) {
        if (tr != null) {
            Log.e(TAG, message, tr)
        } else {
            Log.e(TAG, message)
        }
    }

    data class ChatMessage(val text: String, val isUser: Boolean)

    data class PlayerRow(
        val id: String,
        val name: String,
        val hp: Int,
        val score: Int
    )

    data class ReviewModel(
        var questionId: Int = 0,
        var question: String = "",
        var optA: String = "",
        var optB: String = "",
        var optC: String = "",
        var optD: String = "",
        var userAns: String = "N/A",
        var correctAns: String = "N/A",
        var isCorrect: Boolean = false,
        var explanation: String = "",
        var imageUrl: String = ""
    )

    private inner class ReviewAdapter(
        private val items: List<ReviewModel>
    ) : RecyclerView.Adapter<ReviewAdapter.VH>() {

        inner class VH(v: View) : RecyclerView.ViewHolder(v) {
            val q: TextView = v.findViewById(R.id.itemQuestion)
            val u: TextView = v.findViewById(R.id.itemUserAnswer)
            val c: TextView = v.findViewById(R.id.itemCorrectAnswer)
            val img: ImageView = v.findViewById(R.id.questionImage)
            val e: TextView = v.findViewById(R.id.itemExplanation)

            val optionA: TextView = v.findViewById(R.id.optionA)
            val optionB: TextView = v.findViewById(R.id.optionB)
            val optionC: TextView = v.findViewById(R.id.optionC)
            val optionD: TextView = v.findViewById(R.id.optionD)
            val btnAskAI: Button = v.findViewById(R.id.askAiBtn)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
            logStep("onCreateViewHolder()")
            return VH(
                LayoutInflater.from(parent.context)
                    .inflate(R.layout.item_review_row, parent, false)
            )
        }

        override fun onBindViewHolder(holder: VH, position: Int) {
            val m = items[position]

            val userAnswer = normalizeAnswer(m.userAns)
            val correctAnswer = normalizeAnswer(m.correctAns)

            val userAnswerText = answerToText(userAnswer, m.optA, m.optB, m.optC, m.optD)
            val correctAnswerText = answerToText(correctAnswer, m.optA, m.optB, m.optC, m.optD)

            logStep(
                "onBindViewHolder() -> pos=$position, qid=${m.questionId}, " +
                        "userAnswer=$userAnswer, correctAnswer=$correctAnswer, " +
                        "image=${if (m.imageUrl.isBlank()) "EMPTY" else m.imageUrl}"
            )

            holder.q.text = "Q${position + 1}: ${m.question}"

            holder.optionA.text = "A. ${m.optA}"
            holder.optionB.text = "B. ${m.optB}"
            holder.optionC.text = "C. ${m.optC}"
            holder.optionD.text = "D. ${m.optD}"

            holder.u.text = if (userAnswer.isBlank()) {
                "Your Answer: Not Answered"
            } else {
                "Your Answer: $userAnswer → $userAnswerText"
            }

            holder.c.text = if (correctAnswer.isBlank()) {
                "Correct Answer: N/A"
            } else {
                "Correct Answer: $correctAnswer → $correctAnswerText"
            }

            holder.u.setTextColor(if (m.isCorrect) Color.parseColor("#2E7D32") else Color.RED)
            holder.c.setTextColor(Color.parseColor("#1565C0"))

            holder.e.text = aiMarkdownSpannable(m.explanation)
            holder.e.visibility = if (m.explanation.isBlank()) View.GONE else View.VISIBLE

            resetOptionStyles(holder)
            highlightCorrect(holder, correctAnswer)
            if (!m.isCorrect && userAnswer.isNotBlank()) {
                highlightWrong(holder, userAnswer)
            }

            safeLoadImage(holder.img, m.imageUrl)

            holder.btnAskAI.setOnClickListener {
                AiChatDialogHelper.openAskAiDialog(
                    activity = this@TopicChallengeResultActivity,
                    questionId = m.questionId,
                    question = m.question,
                    options = listOfNotNull(
                        if (m.optA.isNotBlank()) "A. ${m.optA}" else null,
                        if (m.optB.isNotBlank()) "B. ${m.optB}" else null,
                        if (m.optC.isNotBlank()) "C. ${m.optC}" else null,
                        if (m.optD.isNotBlank()) "D. ${m.optD}" else null
                    ),
                    correctAnswer = m.correctAns,
                    explanation = m.explanation
                )
            }
        }

        override fun getItemCount(): Int = items.size

        private fun createOptionDrawable(bgColor: Int): GradientDrawable {
            return GradientDrawable().apply {
                shape = GradientDrawable.RECTANGLE
                cornerRadius = 14f
                setColor(bgColor)
            }
        }

        private fun resetOptionStyles(holder: VH) {
            val defaultBg = ContextCompat.getColor(this@TopicChallengeResultActivity, R.color.option_card_bg_default)
            val defaultText = ContextCompat.getColor(this@TopicChallengeResultActivity, R.color.colorOnSurface)

            val options = listOf(holder.optionA, holder.optionB, holder.optionC, holder.optionD)
            options.forEach { opt ->
                opt.background = createOptionDrawable(defaultBg)
                opt.setTextColor(defaultText)
            }
        }

        private fun highlightCorrect(holder: VH, correctAnswer: String) {
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

        private fun highlightWrong(holder: VH, userAnswer: String) {
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
    }
}
