package com.rankwarz.edulabsrtm

import QuestionModel
import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.spring
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.material.icons.filled.List
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.snapshots.SnapshotStateList
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.material.icons.filled.Warning
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.android.volley.DefaultRetryPolicy
import com.android.volley.Request
import com.android.volley.toolbox.JsonObjectRequest
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import com.rankwarz.edulabsrtm.ui.theme.EduLabsRTMThemeFromPreferences
import kotlinx.coroutines.delay
import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.roundToInt

class SinglePlayerTestModeActivity : ComponentActivity() {

    private val requestQueue by lazy { Volley.newRequestQueue(this) }

    private var uniqueId: Int = 0
    private var subject: String = ""
    private var quizType: String = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        uniqueId = intent.getIntExtra("UNIQUE_ID", 0)
        subject = intent.getStringExtra("SUBJECT") ?: intent.getStringExtra("SELECTED_SUBJECT") ?: ""
        quizType = intent.getStringExtra("QUIZ_TYPE") ?: ""

        setContent {
            EduLabsRTMThemeFromPreferences {
                SinglePlayerTestModeScreen(
                    uniqueId = uniqueId,
                    subject = subject,
                    quizType = quizType,
                    imageBaseUrl = IMAGE_BASE_URL,
                    onFinishExit = { finish() },
                    fetchQuestionIds = { callback ->
                        fetchQuestionIdsLegacyByUniqueId(uniqueId, subject, quizType, callback)
                    },
                    loadQuestion = ::loadQuestion
                )
            }
        }
    }

    private fun normalizeUniqueId(id: Int): Int {
        // If ID is in a special subject range (e.g. 701), don't normalize it down to 1-50
        if (id > 100) return id
        
        val safe = ((id % 50) + 50) % 50
        return if (safe == 0) 1 else safe
    }

    private fun fetchQuestionIdsLegacyByUniqueId(
        id: Int,
        subj: String,
        qType: String,
        callback: (ArrayList<Int>) -> Unit
    ) {
        val safeId = normalizeUniqueId(id)
        val url = "${BASE_URL}api/get_test_structure.php?unique_id=$safeId&subject=${Uri.encode(subj)}&quiz_type=${Uri.encode(qType)}"
        
        Log.d("SINGLE_PLAYER", "Fetching test structure: $url")
        
        val req = StringRequest(Request.Method.GET, url, { response ->
            try {
                val arr = JSONObject(response).optJSONArray("question_ids")
                val ids = ArrayList<Int>()
                if (arr != null) {
                    for (i in 0 until arr.length()) {
                        val q = arr.optInt(i, -1)
                        if (q > 0) ids.add(q)
                    }
                }
                callback(ids)
            } catch (_: Exception) {
                callback(ArrayList())
                Toast.makeText(this, "Question list parse error", Toast.LENGTH_SHORT).show()
            }
        }, { _ ->
            callback(ArrayList())
            Toast.makeText(this, "Question list failed", Toast.LENGTH_SHORT).show()
        })

        req.retryPolicy = DefaultRetryPolicy(
            10000,
            2,
            DefaultRetryPolicy.DEFAULT_BACKOFF_MULT
        )
        requestQueue.add(req)
    }

    private fun loadQuestion(
        qId: Int,
        callback: (QuestionModel?) -> Unit
    ) {
        val url = "${BASE_URL}api/get_single_question.php?question_id=$qId"
        val req = JsonObjectRequest(Request.Method.GET, url, null, { res ->
            try {
                val data = res.getJSONObject("data")
                val q = QuestionModel(
                    qId,
                    data.getString("question"),
                    data.getString("option_a"),
                    data.getString("option_b"),
                    data.getString("option_c"),
                    data.getString("option_d"),
                    data.getString("correct_option"),
                    data.getString("explanation"),
                    data.getString("question_image")
                )
                callback(q)
            } catch (_: Exception) {
                callback(null)
                Toast.makeText(this, "Question parse error", Toast.LENGTH_SHORT).show()
            }
        }, { _ ->
            callback(null)
            Toast.makeText(this, "Question load failed", Toast.LENGTH_SHORT).show()
        })

        requestQueue.add(req)
    }

    fun syncExpToServer(userId: Int, xpGain: Int) {
        val url = "${BASE_URL}sync_game_stats.php"
        val request = object : StringRequest(Method.POST, url, { _ ->
            // Optionally handle success
        }, { _ ->
            // Optionally handle failure
        }) {
            override fun getParams(): MutableMap<String, String> {
                return hashMapOf(
                    "user_id" to userId.toString(),
                    "score" to xpGain.toString(),
                    "total_questions" to "1",
                    "hp" to "0",
                    "is_win" to "false",
                    "challenge_id" to "0"
                )
            }
        }
        requestQueue.add(request)
    }

    fun saveLocalExp(currentExp: Int) {
        val prefs = getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
        prefs.edit().putInt("user_exp", currentExp).apply()
    }

    fun getLocalExp(): Int {
        val prefs = getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
        return prefs.getInt("user_exp", 0)
    }

    companion object {
        private const val BASE_URL = "https://medigyaan.xyz/Neurons/"
        private const val IMAGE_BASE_URL = "https://medigyaan.xyz/Neurons/"
    }
}

@SuppressLint("ContextCastToActivity")
@Composable
private fun SinglePlayerTestModeScreen(
    uniqueId: Int,
    subject: String,
    quizType: String,
    imageBaseUrl: String,
    onFinishExit: () -> Unit,
    userIdProvider: () -> Int = { 0 }, // Assuming a way to get user ID
    fetchQuestionIds: ((ArrayList<Int>) -> Unit) -> Unit,
    loadQuestion: (Int, (QuestionModel?) -> Unit) -> Unit
) {
    val context = LocalContext.current as SinglePlayerTestModeActivity

    val xpPerCorrect = 10
    val totalQuestions = 200
    val maxScore = 800
    val correctPoints = 4
    val wrongPoints = -1

    var questionIds by remember { mutableStateOf<List<Int>>(emptyList()) }
    var loadingIds by rememberSaveable { mutableStateOf(true) }
    var loadingQuestion by rememberSaveable { mutableStateOf(false) }
    var currentIndex by rememberSaveable { mutableIntStateOf(0) }
    var currentQuestion by remember { mutableStateOf<QuestionModel?>(null) }

    var selectedOption by rememberSaveable { mutableStateOf("") }
    var answerLocked by rememberSaveable { mutableStateOf(false) }
    var isQuestionPenalized by rememberSaveable { mutableStateOf(false) }

    var score by rememberSaveable { mutableIntStateOf(0) }
    var correctCount by rememberSaveable { mutableIntStateOf(0) }
    var wrongCount by rememberSaveable { mutableIntStateOf(0) }
    var attemptedCount by rememberSaveable { mutableIntStateOf(0) }

    var currentExp by rememberSaveable { mutableIntStateOf(context.getLocalExp()) }

    var showFeedback by rememberSaveable { mutableStateOf(false) }
    var feedbackCorrect by rememberSaveable { mutableStateOf(false) }
    var feedbackText by rememberSaveable { mutableStateOf("") }
    var feedbackTitle by rememberSaveable { mutableStateOf("") }

    var finished by rememberSaveable { mutableStateOf(false) }
    var finishEarly by rememberSaveable { mutableStateOf(false) }

    var showBattleSummary by rememberSaveable { mutableStateOf(false) }

    val reviewQuestions = remember { mutableStateListOf<JSONObject>() }

    fun appendReviewJson(
        q: QuestionModel,
        selected: String,
        isCorrect: Boolean
    ) {
        try {
            val optionsArray = JSONArray().apply {
                put(q.a) // Index 0 -> A
                put(q.b) // Index 1 -> B
                put(q.c) // Index 2 -> C
                put(q.d) // Index 3 -> D
            }

            val obj = JSONObject().apply {
                put("question_id", q.id)
                put("question", q.question)
                put("options", optionsArray)
                put("option_a", q.a)
                put("option_b", q.b)
                put("option_c", q.c)
                put("option_d", q.d)
                put("a", q.a)
                put("b", q.b)
                put("c", q.c)
                put("d", q.d)

                put("selected_option", selected)
                put("correct_option", q.correctAnswer)
                put("is_correct", if (isCorrect) 1 else 0)

                put(
                    "selected_answer_text",
                    when (selected.uppercase()) {
                        "A" -> q.a
                        "B" -> q.b
                        "C" -> q.c
                        "D" -> q.d
                        else -> ""
                    }
                )

                put(
                    "correct_answer_text",
                    when (q.correctAnswer.uppercase()) {
                        "A" -> q.a
                        "B" -> q.b
                        "C" -> q.c
                        "D" -> q.d
                        else -> ""
                    }
                )

                put("score_change", if (isCorrect) correctPoints else wrongPoints)
                put("explanation", q.explanation)
                put("image_url", q.imageUrl)
                put("answered_at", System.currentTimeMillis())
            }
            reviewQuestions.add(obj)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    fun loadQuestionByIndex(index: Int) {
        if (index !in questionIds.indices) return
        val qId = questionIds[index]

        // Check if this question was already answered (exists in reviewQuestions)
        val existingReview = reviewQuestions.find { it.optInt("question_id") == qId }

        loadingQuestion = true
        loadQuestion(qId) { q ->
            loadingQuestion = false
            if (q == null) {
                Toast.makeText(context, "Unable to load question", Toast.LENGTH_SHORT).show()
                return@loadQuestion
            }
            currentQuestion = q

            if (existingReview != null) {
                // Restore state for already answered question
                selectedOption = existingReview.optString("selected_option", "")
                answerLocked = true
            } else {
                // Reset state for new question
                selectedOption = ""
                answerLocked = false
                isQuestionPenalized = false
            }
        }
    }

    val lifecycleOwner = androidx.lifecycle.compose.LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner, currentIndex) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                // If they come back to the app and haven't answered yet, and haven't been penalized yet
                if (!answerLocked && !isQuestionPenalized && !loadingQuestion && currentQuestion != null) {
                    score -= 1
                    isQuestionPenalized = true
                }
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)

        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
        }
    }

    fun goToNextQuestionOrFinish() {
        if (finishEarly) {
            finished = true
            return
        }

        val nextIndex = currentIndex + 1
        if (nextIndex < questionIds.size && nextIndex < totalQuestions) {
            currentIndex = nextIndex
            loadQuestionByIndex(currentIndex)
        } else {
            finished = true
        }
    }

    fun submitAnswer() {
        val q = currentQuestion ?: return
        if (selectedOption.isBlank() || answerLocked) return

        val correctAnswer = q.correctAnswer
        val isCorrect = selectedOption.equals(correctAnswer, ignoreCase = true)

        answerLocked = true

        // Save to Daily Stats
        DailyStatsManager.recordAnswer(
            context = context,
            topic = "Mock Test $uniqueId",
            isCorrect = isCorrect
        )

        attemptedCount += 1
        if (isCorrect) {
            correctCount += 1
            score += correctPoints
            feedbackTitle = "Correct"

            // Update EXP
            currentExp += xpPerCorrect
            context.saveLocalExp(currentExp)
            context.syncExpToServer(0, xpPerCorrect) // Replace 0 with real userId if available
            feedbackText = q.explanation.takeIf { it.isNotBlank() } ?: "Great answer."
        } else {
            wrongCount += 1
            score += wrongPoints
            feedbackTitle = "Incorrect"
            feedbackText = buildString {
                append("Correct answer: ")
                append(correctAnswer.ifBlank { "N/A" })
                val exp = q.explanation.trim()
                if (exp.isNotBlank()) {
                    append("\n\n")
                    append(exp)
                }
            }
        }

        feedbackCorrect = isCorrect
        showFeedback = true
        appendReviewJson(q, selectedOption, isCorrect)
    }

    LaunchedEffect(uniqueId) {
        loadingIds = true
        fetchQuestionIds { ids ->
            val finalIds = ids.take(totalQuestions)
            questionIds = finalIds
            loadingIds = false

            if (finalIds.isNotEmpty()) {
                currentIndex = 0
                loadQuestionByIndex(0)
            } else {
                finished = true
            }
        }
    }

    LaunchedEffect(showFeedback) {
        if (showFeedback) {
            delay(1100)
            showFeedback = false
            goToNextQuestionOrFinish()
        }
    }

    val scoreRatio = (score.toFloat() / maxScore.toFloat()).coerceIn(0f, 1f)
    val progressText = if (!finished) {
        "Q ${minOf(currentIndex + 1, totalQuestions)} / $totalQuestions"
    } else {
        "Finished"
    }

    val bgBrush = Brush.verticalGradient(
        listOf(
            Color(0xFF0F172A),
            Color(0xFF111827),
            Color(0xFF1E293B)
        )
    )

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = Color.Transparent
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(bgBrush)
        ) {
            if (finished) {
                // Save to history before showing result screen
                LaunchedEffect(Unit) {
                    HistoryManager.saveHistory(
                        context = context,
                        mode = "FINAL_TEST",
                        title = "Final Mock Test",
                        topic = "Mock Test $uniqueId",
                        score = score,
                        totalQuestions = totalQuestions,
                        correctAnswers = correctCount,
                        wrongAnswers = wrongCount
                    )
                }

                ResultScreen(
                    uniqueId = uniqueId,
                    score = score,
                    maxScore = maxScore,
                    correctCount = correctCount,
                    wrongCount = wrongCount,
                    attemptedCount = attemptedCount,
                    totalLoaded = questionIds.size,
                    reviewCount = reviewQuestions.size,
                    reviewQuestions = reviewQuestions.toList(),
                    imageBaseUrl = imageBaseUrl,
                    onExit = onFinishExit,
                    onRestart = {
                        Toast.makeText(context, "Restart by reopening this test", Toast.LENGTH_SHORT).show()
                    }
                )
            } else {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .verticalScroll(rememberScrollState())
                        .padding(16.dp)
                ) {
                    TopHeader(
                        progressText = progressText,
                        score = score,
                        maxScore = maxScore,
                        currentExp = currentExp,
                        scoreRatio = scoreRatio,
                        uniqueId = uniqueId,
                        onEarlyFinish = {
                            finishEarly = true
                            finished = true
                        }
                    )

                    Spacer(modifier = Modifier.height(16.dp))

                    BattleSummaryCard(
                        questionLoaded = questionIds.size,
                        attempted = attemptedCount,
                        correct = correctCount,
                        wrong = wrongCount,
                        remaining = (totalQuestions - attemptedCount).coerceAtLeast(0),
                        expanded = showBattleSummary,
                        onToggle = { showBattleSummary = !showBattleSummary }
                    )

                    Spacer(modifier = Modifier.height(16.dp))

                    AnimatedVisibility(visible = isQuestionPenalized && !answerLocked) {
                        PenaltyNotice()
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    if (loadingIds) {
                        LoadingCard("Loading your test series...", "Fetching question order using unique id.")
                    } else if (loadingQuestion || currentQuestion == null) {
                        LoadingCard("Loading question...", "Please wait while the next item appears.")
                    } else {
                        QuestionCard(
                            question = currentQuestion!!,
                            questionNumber = currentIndex + 1,
                            totalQuestions = totalQuestions,
                            selectedOption = selectedOption,
                            answerLocked = answerLocked,
                            onSelect = { selectedOption = it },
                            imageBaseUrl = imageBaseUrl
                        )

                        Spacer(modifier = Modifier.height(16.dp))

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            OutlinedButton(
                                onClick = {
                                    if (currentIndex > 0 && !answerLocked) {
                                        currentIndex -= 1
                                        loadQuestionByIndex(currentIndex)
                                    }
                                },
                                modifier = Modifier.weight(1f),
                                enabled = currentIndex > 0 && !answerLocked
                            ) {
                                Text("Previous")
                            }

                            if (answerLocked && currentIndex < attemptedCount) {
                                Button(
                                    onClick = {
                                        currentIndex += 1
                                        loadQuestionByIndex(currentIndex)
                                    },
                                    modifier = Modifier.weight(1.2f)
                                ) {
                                    Text("Next")
                                }
                            } else {
                                Button(
                                    onClick = { submitAnswer() },
                                    modifier = Modifier.weight(1.2f),
                                    enabled = !answerLocked && selectedOption.isNotBlank()
                                ) {
                                    Text(if (answerLocked) "Submitted" else "Submit")
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(10.dp))

                        TextButton(
                            onClick = {
                                finishEarly = true
                                finished = true
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Finish Early")
                        }
                    }

                    AnimatedVisibility(visible = showFeedback) {
                        FeedbackCard(
                            isCorrect = feedbackCorrect,
                            title = feedbackTitle,
                            text = feedbackText
                        )
                    }

                    Spacer(modifier = Modifier.height(18.dp))

                    Text(
                        text = "Max score: $maxScore • +$correctPoints correct • $wrongPoints wrong",
                        color = Color(0xFFCBD5E1),
                        fontSize = 12.sp,
                        modifier = Modifier.fillMaxWidth(),
                        textAlign = androidx.compose.ui.text.style.TextAlign.Center
                    )

                    Spacer(modifier = Modifier.height(30.dp))
                }
            }

            StaticBottomNavigation()
        }
    }
}

@Composable
private fun PenaltyNotice() {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF7F1D1D).copy(alpha = 0.2f)),
        border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFEF4444))
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = Icons.Default.Warning,
                contentDescription = "Penalty",
                tint = Color(0xFFF87171),
                modifier = Modifier.size(24.dp)
            )
            Spacer(modifier = Modifier.width(12.dp))
            Column {
                Text(
                    text = "Background Penalty: -1 Point",
                    color = Color(0xFFF87171),
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "Leaving the app during an active question results in a point deduction.",
                    color = Color(0xFFFCA5A5),
                    fontSize = 11.sp
                )
            }
        }
    }
}

@Composable
private fun TopHeader(
    progressText: String,
    score: Int,
    maxScore: Int,
    currentExp: Int,
    scoreRatio: Float,
    uniqueId: Int,
    onEarlyFinish: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF111827)),
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "Single Player Test Mode",
                        color = Color.White,
                        fontSize = 23.sp,
                        fontWeight = FontWeight.ExtraBold
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Unique ID: $uniqueId • Same series for every user",
                        color = Color(0xFF94A3B8),
                        fontSize = 12.sp
                    )
                }

                IconButton(
                    onClick = onEarlyFinish,
                    modifier = Modifier
                        .clip(CircleShape)
                        .background(Color(0xFF1E293B))
                ) {
                    Icon(
                        imageVector = Icons.Default.Close,
                        contentDescription = "Finish Early",
                        tint = Color.White
                    )
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                MetricChip(
                    title = "Progress",
                    value = progressText,
                    modifier = Modifier.weight(1f)
                )
                MetricChip(
                    title = "Score",
                    value = "$score / $maxScore",
                    modifier = Modifier.weight(1f)
                )
                MetricChip(
                    title = "Total EXP",
                    value = "⭐ $currentExp",
                    modifier = Modifier.weight(1f)
                )
            }

            Spacer(modifier = Modifier.height(14.dp))

            Card(
                shape = RoundedCornerShape(18.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF0F172A))
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(
                            text = "Score Meter",
                            color = Color(0xFFCBD5E1),
                            fontSize = 12.sp
                        )
                        Text(
                            text = "${(scoreRatio * 100).roundToInt()}%",
                            color = Color(0xFF38BDF8),
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    Spacer(modifier = Modifier.height(10.dp))
                    LinearProgressIndicator(
                        progress = { scoreRatio },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(10.dp)
                            .clip(RoundedCornerShape(50)),
                        color = Color(0xFF06B6D4),
                        trackColor = Color(0xFF334155)
                    )
                }
            }
        }
    }
}

@Composable
private fun MetricChip(
    title: String,
    value: String,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1E293B))
    ) {
        Column(
            modifier = Modifier.padding(vertical = 12.dp, horizontal = 10.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = title,
                color = Color(0xFF94A3B8),
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(modifier = Modifier.height(5.dp))
            Text(
                text = value,
                color = Color.White,
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }
    }
}

@Composable
private fun BattleSummaryCard(
    questionLoaded: Int,
    attempted: Int,
    correct: Int,
    wrong: Int,
    remaining: Int,
    expanded: Boolean,
    onToggle: () -> Unit
) {
    // This card is designed to be hidden/collapsed by default.
    // The 'expanded' state is passed from the parent's 'showBattleSummary'
    // which is initialized to false.
    // Content inside AnimatedVisibility only shows when 'expanded' is true.

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onToggle() },
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF0B1220)),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Battle Summary",
                    color = Color.White,
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold
                )
                Icon(
                    imageVector = if (expanded) Icons.Default.KeyboardArrowUp else Icons.Default.KeyboardArrowDown,
                    contentDescription = null,
                    tint = Color.White
                )
            }

            AnimatedVisibility(visible = expanded) {
                Column {
                    Spacer(modifier = Modifier.height(12.dp))

                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        SummaryPill("Loaded", questionLoaded.toString(), Color(0xFFE0F2FE), Color(0xFF075985))
                        SummaryPill("Attempted", attempted.toString(), Color(0xFFF1F5F9), Color(0xFF334155))
                        SummaryPill("Correct", correct.toString(), Color(0xFFF0FDF4), Color(0xFF166534))
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        SummaryPill("Wrong", wrong.toString(), Color(0xFFFFF1F2), Color(0xFFB91C1C))
                        SummaryPill("Remaining", remaining.toString(), Color(0xFFFAFAFA), Color(0xFF0F172A))
                    }
                }
            }
        }
    }
}

@Composable
private fun SummaryPill(
    title: String,
    value: String,
    bg: Color,
    fg: Color
) {
    Card(
        shape = RoundedCornerShape(999.dp),
        colors = CardDefaults.cardColors(containerColor = bg)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "$title: ",
                color = fg,
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold
            )
            Text(
                text = value,
                color = fg,
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold
            )
        }
    }
}

@Composable
private fun LoadingCard(
    title: String,
    subtitle: String
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier.padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            CircularProgressIndicator(color = Color(0xFF06B6D4))
            Spacer(modifier = Modifier.height(14.dp))
            Text(
                text = title,
                color = Color(0xFF0F172A),
                fontWeight = FontWeight.Bold,
                fontSize = 16.sp
            )
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = subtitle,
                color = Color(0xFF64748B),
                fontSize = 13.sp
            )
        }
    }
}

@Composable
private fun QuestionCard(
    question: QuestionModel,
    questionNumber: Int,
    totalQuestions: Int,
    selectedOption: String,
    answerLocked: Boolean,
    onSelect: (String) -> Unit,
    imageBaseUrl: String
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF111827)),
        elevation = CardDefaults.cardElevation(defaultElevation = 6.dp)
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "QUESTION $questionNumber",
                    color = Color(0xFF22D3EE),
                    fontWeight = FontWeight.Bold,
                    fontSize = 12.sp
                )
                Text(
                    text = "$questionNumber / $totalQuestions",
                    color = Color(0xFF94A3B8),
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 12.sp
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = question.question,
                color = Color.White,
                fontSize = 19.sp,
                lineHeight = 27.sp,
                fontWeight = FontWeight.SemiBold
            )

            Spacer(modifier = Modifier.height(16.dp))

            val image = question.imageUrl
            if (image.isNotBlank() && image != "null") {
                val imgUrl = if (image.startsWith("http")) image else imageBaseUrl + image
                AsyncImage(
                    model = imgUrl,
                    contentDescription = null,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(220.dp)
                        .clip(RoundedCornerShape(20.dp)),
                    contentScale = ContentScale.Crop
                )
                Spacer(modifier = Modifier.height(16.dp))
            }

            QuizOption(
                text = "A. ${question.a}",
                selected = selectedOption == "A",
                answerLocked = answerLocked,
                isCorrect = question.correctAnswer == "A",
                onClick = { onSelect("A") }
            )
            QuizOption(
                text = "B. ${question.b}",
                selected = selectedOption == "B",
                answerLocked = answerLocked,
                isCorrect = question.correctAnswer == "B",
                onClick = { onSelect("B") }
            )
            QuizOption(
                text = "C. ${question.c}",
                selected = selectedOption == "C",
                answerLocked = answerLocked,
                isCorrect = question.correctAnswer == "C",
                onClick = { onSelect("C") }
            )
            QuizOption(
                text = "D. ${question.d}",
                selected = selectedOption == "D",
                answerLocked = answerLocked,
                isCorrect = question.correctAnswer == "D",
                onClick = { onSelect("D") }
            )
        }
    }
}

@Composable
private fun QuizOption(
    text: String,
    selected: Boolean,
    answerLocked: Boolean,
    isCorrect: Boolean,
    onClick: () -> Unit
) {
    val bg by animateColorAsState(
        targetValue = when {
            answerLocked && isCorrect -> Color(0xFF166534) // Green if correct
            answerLocked && selected && !isCorrect -> Color(0xFF991B1B) // Red if selected and wrong
            selected -> Color(0xFF06B6D4) // Blue if selected but not locked
            else -> Color(0xFF1E293B) // Default
        },
        animationSpec = spring(dampingRatio = Spring.DampingRatioMediumBouncy),
        label = ""
    )

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 7.dp)
            .clickable(enabled = !answerLocked) { onClick() },
        colors = CardDefaults.cardColors(containerColor = bg),
        shape = RoundedCornerShape(18.dp)
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(26.dp)
                    .clip(CircleShape)
                    .background(if (selected) Color.White else Color(0xFF334155)),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = if (selected) "✓" else "",
                    color = Color(0xFF0F172A),
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold
                )
            }

            Spacer(modifier = Modifier.width(12.dp))

            Text(
                text = text,
                color = Color.White,
                fontSize = 15.sp,
                fontWeight = FontWeight.Medium,
                lineHeight = 22.sp
            )
        }
    }
}

@Composable
private fun FeedbackCard(
    isCorrect: Boolean,
    title: String,
    text: String
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 16.dp),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (isCorrect) Color(0xFF064E3B) else Color(0xFF7F1D1D)
        )
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Text(
                text = if (isCorrect) "✅ $title" else "❌ $title",
                color = Color.White,
                fontWeight = FontWeight.Bold,
                fontSize = 19.sp
            )
            Spacer(modifier = Modifier.height(10.dp))
            Text(
                text = text,
                color = Color.White.copy(alpha = 0.95f),
                fontSize = 14.sp,
                lineHeight = 22.sp
            )
        }
    }
}

@Composable
private fun ResultScreen(
    uniqueId: Int,
    score: Int,
    maxScore: Int,
    correctCount: Int,
    wrongCount: Int,
    attemptedCount: Int,
    totalLoaded: Int,
    reviewCount: Int,
    reviewQuestions: List<JSONObject>,
    imageBaseUrl: String,
    onExit: () -> Unit,
    onRestart: () -> Unit
) {
    val percentage = if (maxScore > 0) {
        ((score.toFloat() / maxScore.toFloat()) * 100f).coerceIn(0f, 100f)
    } else 0f

    val positiveScore = score.coerceAtLeast(0)
    val color = when {
        percentage >= 75f -> Color(0xFF22C55E)
        percentage >= 50f -> Color(0xFFF59E0B)
        else -> Color(0xFFEF4444)
    }

    var showReview by rememberSaveable { mutableStateOf(false) }
    val scroll = rememberScrollState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(scroll)
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(30.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFF111827)),
            elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
        ) {
            Column(
                modifier = Modifier.padding(22.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = "Test Completed",
                    color = Color.White,
                    fontSize = 22.sp,
                    fontWeight = FontWeight.ExtraBold
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Unique ID: $uniqueId",
                    color = Color(0xFF94A3B8),
                    fontSize = 12.sp
                )

                Spacer(modifier = Modifier.height(18.dp))

                Box(
                    modifier = Modifier
                        .size(120.dp)
                        .clip(CircleShape)
                        .background(Color(0xFF0F172A))
                        .border(4.dp, color, CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "${percentage.roundToInt()}%",
                        color = color,
                        fontSize = 28.sp,
                        fontWeight = FontWeight.ExtraBold
                    )
                }

                Spacer(modifier = Modifier.height(18.dp))

                Text(
                    text = "Score $positiveScore / $maxScore",
                    color = Color.White,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold
                )

                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = "Max score is 800 • +4 right • -1 wrong",
                    color = Color(0xFF94A3B8),
                    fontSize = 12.sp
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(24.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White),
            elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "Performance",
                    color = Color(0xFF0F172A),
                    fontWeight = FontWeight.Bold,
                    fontSize = 18.sp
                )

                Spacer(modifier = Modifier.height(12.dp))

                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    ResultMetric(
                        "Attempted",
                        attemptedCount.toString(),
                        Color(0xFFF1F5F9),
                        Color(0xFF334155),
                        modifier = Modifier.weight(1f)
                    )
                    ResultMetric(
                        "Correct",
                        correctCount.toString(),
                        Color(0xFFF0FDF4),
                        Color(0xFF166534),
                        modifier = Modifier.weight(1f)
                    )
                }

                Spacer(modifier = Modifier.height(10.dp))

                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    ResultMetric(
                        "Wrong",
                        wrongCount.toString(),
                        Color(0xFFFFF1F2),
                        Color(0xFFB91C1C),
                        modifier = Modifier.weight(1f)
                    )
                    ResultMetric(
                        "Loaded",
                        totalLoaded.toString(),
                        Color(0xFFE0F2FE),
                        Color(0xFF075985),
                        modifier = Modifier.weight(1f)
                    )
                }

                Spacer(modifier = Modifier.height(10.dp))
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { showReview = !showReview },
                    shape = RoundedCornerShape(18.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFF5F3FF))
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = if (showReview) "Hide Review Questions" else "Show Review Questions",
                            color = Color(0xFF6D28D9),
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "$reviewCount Questions Attempted",
                            color = Color(0xFF7C3AED),
                            fontSize = 13.sp
                        )
                    }
                }

                // Carousel Review Section
                AnimatedVisibility(visible = showReview) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = 12.dp)
                    ) {
                        if (reviewQuestions.isEmpty()) {
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                colors = CardDefaults.cardColors(
                                    containerColor = Color(0xFF1E293B)
                                ),
                                shape = RoundedCornerShape(18.dp)
                            ) {
                                Text(
                                    text = "Review data not available",
                                    color = Color.White,
                                    modifier = Modifier.padding(16.dp)
                                )
                            }
                        } else {
                            val pagerState = rememberPagerState(pageCount = { reviewQuestions.size })

                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                HorizontalPager(
                                    state = pagerState,
                                    modifier = Modifier.fillMaxWidth(),
                                    contentPadding = PaddingValues(horizontal = 4.dp),
                                    pageSpacing = 12.dp,
                                    verticalAlignment = Alignment.Top
                                ) { page ->
                                    ReviewQuestionCard(
                                        reviewQuestions[page],
                                        page + 1,
                                        imageBaseUrl
                                    )
                                }

                                Spacer(modifier = Modifier.height(12.dp))

                                // Simple Page Indicator
                                Row(
                                    Modifier
                                        .height(20.dp)
                                        .fillMaxWidth(),
                                    horizontalArrangement = Arrangement.Center
                                ) {
                                    repeat(reviewQuestions.size) { iteration ->
                                        val color = if (pagerState.currentPage == iteration) Color(0xFF6D28D9) else Color.LightGray
                                        Box(
                                            modifier = Modifier
                                                .padding(2.dp)
                                                .clip(CircleShape)
                                                .background(color)
                                                .size(8.dp)
                                        )
                                    }
                                }
                                Text("Swipe Left/Right to see more", fontSize = 11.sp, color = Color.Gray)
                            }
                        }
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(24.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFF0B1220))
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "Result Notes",
                    color = Color.White,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Your answers were stored in review JSON for later analysis. The same unique test series can be reused for all players.",
                    color = Color(0xFFCBD5E1),
                    fontSize = 13.sp,
                    lineHeight = 20.sp
                )
            }
        }

        Spacer(modifier = Modifier.height(18.dp))

        Button(
            onClick = onExit,
            modifier = Modifier
                .fillMaxWidth()
                .height(54.dp),
            shape = RoundedCornerShape(18.dp)
        ) {
            Text("Exit")
        }

        Spacer(modifier = Modifier.height(10.dp))

        OutlinedButton(
            onClick = onRestart,
            modifier = Modifier
                .fillMaxWidth()
                .height(54.dp),
            shape = RoundedCornerShape(18.dp)
        ) {
            Text("Open Again")
        }

        Spacer(modifier = Modifier.height(24.dp))
    }

}

@Composable
private fun StaticBottomNavigation() {
    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.BottomCenter
    ) {
        Card(
            modifier = Modifier
                .padding(bottom = 36.dp)
                .padding(horizontal = 16.dp)
                .fillMaxWidth(0.9f),
            shape = RoundedCornerShape(24.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFF1E293B)),
            elevation = CardDefaults.cardElevation(defaultElevation = 10.dp)
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                horizontalArrangement = Arrangement.SpaceEvenly,
                verticalAlignment = Alignment.CenterVertically
            ) {
                val context = LocalContext.current

                BottomIcon(Icons.Default.Home, "Home") {
                    (context as? android.app.Activity)?.finish()
                }
                BottomIcon(Icons.Default.PlayArrow, "Reels") { /* Navigate to Reels */ }
                BottomIcon(Icons.Default.Search, "Search") {
                    context.startActivity(Intent(context, GlobalSearchActivity::class.java))
                }
                BottomIcon(Icons.Default.List, "History") { /* Navigate to History */ }
                BottomIcon(Icons.Default.PlayArrow, "Messages") { /* Navigate to Messages */ }
            }
        }
    }
}

@Composable
private fun BottomIcon(
    imageVector: androidx.compose.ui.graphics.vector.ImageVector,
    contentDescription: String,
    onClick: () -> Unit
) {
    IconButton(onClick = onClick) {
        Icon(
            imageVector = imageVector,
            contentDescription = contentDescription,
            tint = Color.White
        )
    }
}

@Composable
private fun ResultMetric(
    title: String,
    value: String,
    bg: Color,
    fg: Color,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = bg)
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = title,
                color = fg,
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = value,
                color = fg,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold
            )
        }
    }
}

@Composable
private fun ReviewQuestionCard(
    obj: JSONObject,
    index: Int,
    imageBaseUrl: String
) {
    var expanded by remember {
        mutableStateOf(false)
    }

    val isCorrect = obj.optInt("is_correct", 0) == 1
    val question = obj.optString("question", "Question")
    val selected = obj.optString("selected_option", "")
    val correct = obj.optString("correct_option", "")
    val selectedAnswerText =
        obj.optString("selected_answer_text", "")
    val correctAnswerText =
        obj.optString("correct_answer_text", "")
    val explanation =
        obj.optString("explanation", "")
    val scoreChange =
        obj.optInt("score_change", 0)
    val imageUrl =
        obj.optString("image_url", "")

    // Ensure we extract all 4 options correctly
    val options = mutableListOf<String>()
    val optsArray = obj.optJSONArray("options")
    if (optsArray != null && optsArray.length() >= 4) {
        for (i in 0 until 4) options.add(optsArray.optString(i))
    } else {
        // Fallback to individual keys if array is missing
        listOf("option_a", "option_b", "option_c", "option_d").forEach { key ->
            options.add(obj.optString(key, ""))
        }
    }

    val bgColor =
        if (isCorrect)
            Color(0xFF052E16)
        else
            Color(0xFF450A0A)

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = bgColor)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            /* --------------------------------
               HEADER
            -------------------------------- */
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Box(
                        modifier = Modifier
                            .size(38.dp)
                            .clip(RoundedCornerShape(12.dp))
                            .background(
                                if (isCorrect)
                                    Color(0xFF16A34A)
                                else
                                    Color(0xFFDC2626)
                            ),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "$index",
                            color = Color.White,
                            fontWeight = FontWeight.Bold
                        )
                    }

                }

                Spacer(modifier = Modifier.width(12.dp))

                Column(
                    modifier = Modifier.weight(1f)
                ) {
                    Text(
                        text = if (isCorrect) "Correct Answer" else "Wrong Answer",
                        color = Color.White,
                        fontWeight = FontWeight.Bold,
                        fontSize = 16.sp
                    )

                    Spacer(modifier = Modifier.height(2.dp))

                    Text(
                        text = "Score: ${if (scoreChange >= 0) "+$scoreChange" else scoreChange.toString()}",
                        color = Color(0xFFCBD5E1),
                        fontSize = 12.sp
                    )
                }

                TextButton(
                    onClick = { expanded = !expanded }
                ) {
                    Text(
                        text = if (expanded) "Hide" else "View",
                        color = Color.White
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            /* --------------------------------
               QUESTION
            -------------------------------- */
            Text(
                text = question,
                color = Color.White,
                fontWeight = FontWeight.Bold,
                fontSize = 16.sp,
                lineHeight = 24.sp
            )

            /* --------------------------------
               IMAGE
            -------------------------------- */
            if (imageUrl.isNotBlank() && imageUrl != "null") {
                Spacer(modifier = Modifier.height(14.dp))
                val finalImage = if (imageUrl.startsWith("http")) imageUrl else imageBaseUrl + imageUrl
                AsyncImage(
                    model = finalImage,
                    contentDescription = null,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(220.dp)
                        .clip(RoundedCornerShape(18.dp)),
                    contentScale = ContentScale.Crop
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            /* --------------------------------
               ANSWERS
            -------------------------------- */
            ReviewAnswerItem(
                title = "Your Answer",
                answer = if (selected.isBlank()) "Not Attempted" else "$selected. $selectedAnswerText",
                bg = if (isCorrect) Color(0xFF166534) else Color(0xFF7F1D1D)
            )

            Spacer(modifier = Modifier.height(12.dp))

            ReviewAnswerItem(
                title = "Correct Answer",
                answer = "$correct. $correctAnswerText",
                bg = Color(0xFF14532D)
            )

            /* --------------------------------
               EXPANDABLE SECTION
            -------------------------------- */
            AnimatedVisibility(visible = expanded) {
                Column {
                    Spacer(modifier = Modifier.height(18.dp))
                    Text(
                        text = "All Options",
                        color = Color.White,
                        fontWeight = FontWeight.Bold,
                        fontSize = 16.sp
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    options.forEachIndexed { optionIndex, option ->
                        val optionLetter = ('A' + optionIndex).toString()
                        val optionBg = when {
                            optionLetter == correct -> Color(0xFF14532D)
                            optionLetter == selected && selected != correct -> Color(0xFF7F1D1D)
                            else -> Color(0xFF1E293B)
                        }
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 5.dp)
                                .clip(RoundedCornerShape(16.dp))
                                .background(optionBg)
                                .padding(14.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(28.dp)
                                    .clip(CircleShape)
                                    .background(Color.White.copy(alpha = 0.15f)),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = optionLetter,
                                    color = Color.White,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                            Spacer(modifier = Modifier.width(12.dp))
                            Text(
                                text = option,
                                color = Color.White,
                                fontSize = 14.sp,
                                lineHeight = 20.sp
                            )
                        }
                    }

                    if (explanation.isNotBlank()) {
                        Spacer(modifier = Modifier.height(18.dp))
                        Text(
                            text = "Explanation",
                            color = Color.White,
                            fontWeight = FontWeight.Bold,
                            fontSize = 16.sp
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = explanation,
                            color = Color(0xFFCBD5E1),
                            fontSize = 14.sp,
                            lineHeight = 22.sp
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ReviewAnswerItem(
    title: String,
    answer: String,
    bg: Color
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(bg)
            .padding(14.dp)
    ) {
        Text(
            text = title,
            color = Color.White.copy(alpha = 0.7f),
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(bottom = 4.dp)
        )
        Text(
            text = answer,
            color = Color.White,
            fontSize = 14.sp,
            fontWeight = FontWeight.SemiBold,
            lineHeight = 20.sp
        )
    }
}
