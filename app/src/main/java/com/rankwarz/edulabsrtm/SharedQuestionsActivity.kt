package com.rankwarz.edulabsrtm

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.expandVertically
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowForward
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.android.volley.Request
import com.android.volley.toolbox.JsonObjectRequest
import com.android.volley.toolbox.Volley
import com.rankwarz.edulabsrtm.ui.theme.EduLabsRTMThemeFromPreferences
import org.json.JSONObject
import kotlin.math.roundToInt

data class SharedQuestionModel(
    val question_id: Int,
    val question: String,
    val total_attempts: Int,
    val total_correct: Int,
    val accuracy: Double
)

data class AttemptModel(
    val temporary_user_id: String,
    val user_answer: String,
    val is_correct: Int,
    val name: String,
    val created_at: String
)

class SharedQuestionsActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            EduLabsTheme {
                SharedQuestionsScreen(
                    onOpenAttempts = { questionId ->
                        startActivity(
                            Intent(this, QuestionAttemptsActivity::class.java)
                                .putExtra("question_id", questionId)
                        )
                    }
                )
            }
        }
    }
}

@Composable
private fun SharedQuestionsScreen(
    onOpenAttempts: (Int) -> Unit
) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val prefs = context.getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
    val userId = prefs.getInt("user_id", 0)

    var isLoading by rememberSaveable { mutableStateOf(true) }
    var errorMessage by rememberSaveable { mutableStateOf<String?>(null) }
    var searchText by rememberSaveable { mutableStateOf("") }
    var questions by remember { mutableStateOf<List<SharedQuestionModel>>(emptyList()) }

    val filteredQuestions = remember(questions, searchText) {
        if (searchText.isBlank()) questions
        else questions.filter {
            it.question.contains(searchText, ignoreCase = true) ||
                    it.question_id.toString().contains(searchText)
        }
    }

    val totalAttempts = remember(questions) { questions.sumOf { it.total_attempts } }
    val totalCorrect = remember(questions) { questions.sumOf { it.total_correct } }
    val averageAccuracy = remember(questions) {
        if (questions.isEmpty()) 0.0 else questions.map { it.accuracy }.average()
    }

    fun loadSharedQuestions() {
        if (userId == 0) {
            errorMessage = "User not found"
            isLoading = false
            return
        }

        isLoading = true
        errorMessage = null

        val url = "https://medigyaan.xyz/Neurons/shared_api.php?user_id=$userId"
        val request = JsonObjectRequest(
            Request.Method.GET,
            url,
            null,
            { response ->
                try {
                    val arr = response.getJSONArray("questions")
                    val newList = ArrayList<SharedQuestionModel>()

                    for (i in 0 until arr.length()) {
                        val obj = arr.getJSONObject(i)
                        newList.add(
                            SharedQuestionModel(
                                question_id = obj.optInt("question_id"),
                                question = obj.optString("question"),
                                total_attempts = obj.optInt("total_attempts"),
                                total_correct = obj.optInt("total_correct"),
                                accuracy = obj.optDouble("accuracy")
                            )
                        )
                    }

                    questions = newList
                    isLoading = false
                } catch (e: Exception) {
                    errorMessage = "Invalid response"
                    isLoading = false
                }
            },
            {
                errorMessage = "Error loading questions"
                isLoading = false
                Toast.makeText(context, "Error loading questions", Toast.LENGTH_SHORT).show()
            }
        )

        Volley.newRequestQueue(context).add(request)
    }

    LaunchedEffect(Unit) {
        loadSharedQuestions()
    }

    val bgBrush = Brush.verticalGradient(
        listOf(
            MaterialTheme.colorScheme.background,
            MaterialTheme.colorScheme.surface,
            MaterialTheme.colorScheme.surfaceVariant
        )
    )

    Surface(
        modifier = Modifier
            .fillMaxSize()
            .background(bgBrush),
        color = Color.Transparent
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp)
        ) {
            TopHeroCard(
                totalQuestions = questions.size,
                totalAttempts = totalAttempts,
                totalCorrect = totalCorrect,
                averageAccuracy = averageAccuracy,
                onRefresh = { loadSharedQuestions() }
            )

            Spacer(modifier = Modifier.height(14.dp))

            SearchBarCard(
                value = searchText,
                onValueChange = { searchText = it }
            )

            Spacer(modifier = Modifier.height(14.dp))

            AnimatedVisibility(
                visible = isLoading,
                enter = fadeIn(),
                exit = fadeOut()
            ) {
                LoadingStateCard()
            }

            AnimatedVisibility(
                visible = !isLoading && errorMessage != null,
                enter = fadeIn(),
                exit = fadeOut()
            ) {
                ErrorStateCard(
                    message = errorMessage ?: "Something went wrong",
                    onRetry = { loadSharedQuestions() }
                )
            }

            AnimatedVisibility(
                visible = !isLoading && errorMessage == null,
                enter = fadeIn(),
                exit = fadeOut()
            ) {
                if (filteredQuestions.isEmpty()) {
                    EmptyStateCard()
                } else {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(bottom = 20.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        items(filteredQuestions, key = { it.question_id }) { question ->
                            SharedQuestionCard(
                                question = question,
                                onClick = { onOpenAttempts(question.question_id) }
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun TopHeroCard(
    totalQuestions: Int,
    totalAttempts: Int,
    totalCorrect: Int,
    averageAccuracy: Double,
    onRefresh: () -> Unit
) {
    val accuracyInt = averageAccuracy.roundToInt()

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF0F172A)),
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "Shared Questions",
                        color = Color.White,
                        fontSize = 24.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Tap any question to see all attempts",
                        color = Color(0xFFCBD5E1),
                        fontSize = 13.sp
                    )
                }

                IconButton(
                    onClick = onRefresh,
                    modifier = Modifier
                        .clip(CircleShape)
                        .background(Color(0xFF1E293B))
                ) {
                    Icon(
                        imageVector = Icons.Default.Refresh,
                        contentDescription = "Refresh",
                        tint = Color.White
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                StatChip(
                    title = "Questions",
                    value = totalQuestions.toString(),
                    modifier = Modifier.weight(1f)
                )
                StatChip(
                    title = "Attempts",
                    value = totalAttempts.toString(),
                    modifier = Modifier.weight(1f)
                )
                StatChip(
                    title = "Correct",
                    value = totalCorrect.toString(),
                    modifier = Modifier.weight(1f)
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF111827))
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(14.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Average Accuracy",
                            color = Color(0xFF94A3B8),
                            fontSize = 12.sp
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "$accuracyInt%",
                            color = Color(0xFF38BDF8),
                            fontSize = 26.sp,
                            fontWeight = FontWeight.ExtraBold
                        )
                    }

                    AccuracyRing(percent = accuracyInt)
                }
            }
        }
    }
}

@Composable
private fun StatChip(
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
                color = Color(0xFFCBD5E1),
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = value,
                color = Color.White,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold
            )
        }
    }
}

@Composable
private fun AccuracyRing(percent: Int) {
    val clamped = percent.coerceIn(0, 100)
    val color = when {
        clamped >= 80 -> Color(0xFF22C55E)
        clamped >= 50 -> Color(0xFFF59E0B)
        else -> Color(0xFFEF4444)
    }

    Box(
        modifier = Modifier
            .size(72.dp)
            .clip(CircleShape)
            .background(Color(0xFF0F172A)),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = "$clamped%",
            color = color,
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold
        )
    }
}

@Composable
private fun SearchBarCard(
    value: String,
    onValueChange: (String) -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(22.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Text(
                text = "Search Questions",
                color = MaterialTheme.colorScheme.onSurface,
                fontWeight = FontWeight.SemiBold,
                fontSize = 14.sp
            )
            Spacer(modifier = Modifier.height(10.dp))

            OutlinedTextField(
                value = value,
                onValueChange = onValueChange,
                modifier = Modifier.fillMaxWidth(),
                placeholder = { Text("Search by question text or ID") },
                singleLine = true,
                shape = RoundedCornerShape(16.dp),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Color(0xFF2563EB),
                    unfocusedBorderColor = Color(0xFFCBD5E1),
                    focusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                    unfocusedContainerColor = MaterialTheme.colorScheme.surfaceVariant
                )
            )
        }
    }
}

@Composable
private fun SharedQuestionCard(
    question: SharedQuestionModel,
    onClick: () -> Unit
) {
    val accuracyColor = when {
        question.accuracy >= 80 -> Color(0xFF16A34A)
        question.accuracy >= 50 -> Color(0xFFF59E0B)
        else -> Color(0xFFDC2626)
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 6.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                verticalAlignment = Alignment.Top,
                modifier = Modifier.fillMaxWidth()
            ) {
                Box(
                    modifier = Modifier
                        .size(48.dp)
                        .clip(CircleShape)
                        .background(Color(0xFFE0F2FE)),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = question.question_id.toString(),
                        color = Color(0xFF0369A1),
                        fontWeight = FontWeight.Bold,
                        fontSize = 14.sp
                    )
                }

                Spacer(modifier = Modifier.width(12.dp))

                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = question.question,
                        color = MaterialTheme.colorScheme.onSurface,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 3,
                        overflow = TextOverflow.Ellipsis
                    )

                    Spacer(modifier = Modifier.height(10.dp))

                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        SmallLabel(
                            text = "${question.total_attempts} attempts",
                            bg = Color(0xFFF1F5F9),
                            fg = Color(0xFF334155)
                        )
                        SmallLabel(
                            text = "${question.total_correct} correct",
                            bg = Color(0xFFF0FDF4),
                            fg = Color(0xFF166534)
                        )
                    }
                }

                Icon(
                    imageVector = Icons.Default.ArrowForward,
                    contentDescription = null,
                    tint = Color(0xFF94A3B8)
                )
            }

            Spacer(modifier = Modifier.height(14.dp))

            Card(
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFFAFAFA))
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 14.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Accuracy",
                        color = Color(0xFF475569),
                        fontSize = 13.sp,
                        modifier = Modifier.weight(1f)
                    )
                    Text(
                        text = "${question.accuracy.roundToInt()}%",
                        color = accuracyColor,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }
    }
}

@Composable
private fun SmallLabel(
    text: String,
    bg: Color,
    fg: Color
) {
    Text(
        text = text,
        color = fg,
        fontSize = 11.sp,
        fontWeight = FontWeight.SemiBold,
        modifier = Modifier
            .clip(RoundedCornerShape(999.dp))
            .background(bg)
            .padding(horizontal = 10.dp, vertical = 6.dp)
    )
}

@Composable
private fun LoadingStateCard() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier.padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            CircularProgressIndicator(color = Color(0xFF2563EB))
            Spacer(modifier = Modifier.height(12.dp))
            Text(
                text = "Loading shared questions...",
                color = MaterialTheme.colorScheme.onSurface,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "Please wait while we fetch the latest list.",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                fontSize = 13.sp
            )
        }
    }
}

@Composable
private fun ErrorStateCard(
    message: String,
    onRetry: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF1F2)),
        elevation = CardDefaults.cardElevation(defaultElevation = 3.dp)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Text(
                text = "Something went wrong",
                color = Color(0xFFB91C1C),
                fontWeight = FontWeight.Bold,
                fontSize = 16.sp
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = message,
                color = Color(0xFF7F1D1D),
                fontSize = 14.sp
            )
            Spacer(modifier = Modifier.height(14.dp))
            Button(onClick = onRetry) {
                Text("Retry")
            }
        }
    }
}

@Composable
private fun EmptyStateCard() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(28.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "📭",
                fontSize = 36.sp
            )
            Spacer(modifier = Modifier.height(10.dp))
            Text(
                text = "No questions found",
                color = MaterialTheme.colorScheme.onSurface,
                fontWeight = FontWeight.Bold,
                fontSize = 16.sp
            )
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = "Try a different search term or refresh the list.",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                fontSize = 13.sp
            )
        }
    }
}

@Composable
private fun EduLabsTheme(content: @Composable () -> Unit) {
    EduLabsRTMThemeFromPreferences(content = content)
}
