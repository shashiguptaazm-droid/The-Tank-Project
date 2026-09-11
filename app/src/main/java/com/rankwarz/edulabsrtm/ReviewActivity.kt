package com.rankwarz.edulabsrtm

import android.app.Activity
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.spring
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import coil.request.ImageRequest
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.rankwarz.edulabsrtm.ui.theme.EduLabsRTMThemeFromPreferences

class ReviewActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val reviewJson = intent.getStringExtra("REVIEW_JSON") ?: "[]"

        val reviewList: List<ReviewQuestionModel> = try {
            val type = object : TypeToken<List<ReviewQuestionModel>>() {}.type
            Gson().fromJson(reviewJson, type)
        } catch (e: Exception) {
            e.printStackTrace()
            emptyList()
        }

        setContent {
            EduLabsRTMThemeFromPreferences {

                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = Color.Transparent
                ) {

                    ReviewScreen(
                        reviewList = reviewList,
                        onBack = { finish() }
                    )
                }
            }
        }
    }
}

/* ---------------------------------------------------
   DATA MODEL
--------------------------------------------------- */

data class ReviewQuestionModel(
    val question_id: Int = 0,
    val question: String = "",

    val option_a: String = "",
    val option_b: String = "",
    val option_c: String = "",
    val option_d: String = "",
    val option_e: String = "",

    val selected_option: String = "",
    val correct_option: String = "",

    val selected_answer_text: String = "",
    val correct_answer_text: String = "",

    val score_change: Int = 0,

    val explanation: String = "",
    val image_url: String = "",

    val is_correct: Int = 0
)

/* ---------------------------------------------------
   MAIN SCREEN
--------------------------------------------------- */

@Composable
fun ReviewScreen(
    reviewList: List<ReviewQuestionModel>,
    onBack: () -> Unit
) {

    val totalQuestions = reviewList.size

    val correctAnswers = reviewList.count {
        it.is_correct == 1
    }

    val wrongAnswers = totalQuestions - correctAnswers

    val accuracy =
        if (totalQuestions > 0)
            ((correctAnswers.toFloat() / totalQuestions.toFloat()) * 100).toInt()
        else
            0

    val bgBrush = Brush.verticalGradient(
        listOf(
            Color(0xFF0F172A),
            Color(0xFF111827),
            Color(0xFF1E293B)
        )
    )

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(bgBrush)
    ) {

        Column(
            modifier = Modifier.fillMaxSize()
        ) {

            /* ---------------------------------------------------
               TOP HEADER
            --------------------------------------------------- */

            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                shape = RoundedCornerShape(30.dp),
                colors = CardDefaults.cardColors(
                    containerColor = Color(0xFF111827)
                )
            ) {

                Column(
                    modifier = Modifier.padding(20.dp)
                ) {

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {

                        Column(
                            modifier = Modifier.weight(1f)
                        ) {

                            Text(
                                text = "Review Answers",
                                color = Color.White,
                                fontWeight = FontWeight.ExtraBold,
                                fontSize = 28.sp
                            )

                            Spacer(modifier = Modifier.height(4.dp))

                            Text(
                                text = "Detailed performance analysis",
                                color = Color(0xFF94A3B8),
                                fontSize = 13.sp
                            )
                        }

                        IconButton(
                            onClick = onBack,
                            modifier = Modifier
                                .clip(CircleShape)
                                .background(Color(0xFF1E293B))
                        ) {

                            Icon(
                                imageVector = Icons.Default.Close,
                                contentDescription = null,
                                tint = Color.White
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(20.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {

                        SummaryMetricCard(
                            title = "Correct",
                            value = correctAnswers.toString(),
                            bg = Color(0xFF14532D),
                            modifier = Modifier.weight(1f)
                        )

                        SummaryMetricCard(
                            title = "Wrong",
                            value = wrongAnswers.toString(),
                            bg = Color(0xFF7F1D1D),
                            modifier = Modifier.weight(1f)
                        )

                        SummaryMetricCard(
                            title = "Total",
                            value = totalQuestions.toString(),
                            bg = Color(0xFF1E3A8A),
                            modifier = Modifier.weight(1f)
                        )
                    }

                    Spacer(modifier = Modifier.height(18.dp))

                    Card(
                        shape = RoundedCornerShape(18.dp),
                        colors = CardDefaults.cardColors(
                            containerColor = Color(0xFF0F172A)
                        )
                    ) {

                        Column(
                            modifier = Modifier.padding(14.dp)
                        ) {

                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {

                                Text(
                                    text = "Accuracy",
                                    color = Color(0xFFCBD5E1),
                                    fontSize = 12.sp
                                )

                                Text(
                                    text = "$accuracy%",
                                    color = Color(0xFF22D3EE),
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 12.sp
                                )
                            }

                            Spacer(modifier = Modifier.height(10.dp))

                            LinearProgressIndicator(
                                progress = { accuracy / 100f },
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

            /* ---------------------------------------------------
               REVIEW LIST
            --------------------------------------------------- */

            if (reviewList.isEmpty()) {

                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {

                    Card(
                        shape = RoundedCornerShape(24.dp),
                        colors = CardDefaults.cardColors(
                            containerColor = Color(0xFF111827)
                        )
                    ) {

                        Column(
                            modifier = Modifier.padding(30.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {

                            Text(
                                text = "No Review Data Found",
                                color = Color.White,
                                fontSize = 18.sp,
                                fontWeight = FontWeight.Bold
                            )

                            Spacer(modifier = Modifier.height(8.dp))

                            Text(
                                text = "Questions you attempt will appear here.",
                                color = Color(0xFF94A3B8),
                                fontSize = 13.sp
                            )
                        }
                    }
                }

            } else {

                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(
                        start = 16.dp,
                        end = 16.dp,
                        bottom = 24.dp
                    ),
                    verticalArrangement = Arrangement.spacedBy(14.dp)
                ) {

                    itemsIndexed(reviewList) { index, item ->

                        ReviewQuestionCard(
                            index = index + 1,
                            model = item
                        )
                    }
                }
            }
        }
    }
}

/* ---------------------------------------------------
   SUMMARY CARD
--------------------------------------------------- */

@Composable
fun SummaryMetricCard(
    title: String,
    value: String,
    bg: Color,
    modifier: Modifier = Modifier
) {

    Card(
        modifier = modifier,
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(
            containerColor = bg
        )
    ) {

        Column(
            modifier = Modifier.padding(vertical = 16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {

            Text(
                text = value,
                color = Color.White,
                fontWeight = FontWeight.ExtraBold,
                fontSize = 24.sp
            )

            Spacer(modifier = Modifier.height(4.dp))

            Text(
                text = title,
                color = Color.White.copy(alpha = 0.9f),
                fontSize = 13.sp
            )
        }
    }
}

/* ---------------------------------------------------
   QUESTION CARD
--------------------------------------------------- */

@Composable
fun ReviewQuestionCard(
    index: Int,
    model: ReviewQuestionModel
) {

    var expanded by remember {
        mutableStateOf(false)
    }

    val isCorrect = model.is_correct == 1

    val cardColor =
        if (isCorrect)
            Color(0xFF052E16)
        else
            Color(0xFF450A0A)

    val optionsList = listOf(
        "A" to model.option_a,
        "B" to model.option_b,
        "C" to model.option_c,
        "D" to model.option_d,
        "E" to model.option_e
    )

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(26.dp),
        colors = CardDefaults.cardColors(
            containerColor = cardColor
        )
    ) {

        Column(
            modifier = Modifier.padding(18.dp)
        ) {

            /* ---------------------------------------------------
               HEADER
            --------------------------------------------------- */

            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {

                Box(
                    modifier = Modifier
                        .size(42.dp)
                        .clip(RoundedCornerShape(14.dp))
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

                Spacer(modifier = Modifier.width(12.dp))

                Column(
                    modifier = Modifier.weight(1f)
                ) {

                    Text(
                        text =
                            if (isCorrect)
                                "Correct Answer"
                            else
                                "Wrong Answer",

                        color = Color.White,
                        fontWeight = FontWeight.Bold,
                        fontSize = 16.sp
                    )

                    Spacer(modifier = Modifier.height(2.dp))

                    Text(
                        text = "Score: ${
                            if (model.score_change >= 0)
                                "+${model.score_change}"
                            else
                                model.score_change.toString()
                        }",

                        color = Color(0xFFCBD5E1),
                        fontSize = 12.sp
                    )
                }

                FilledIconButton(
                    onClick = {
                        expanded = !expanded
                    },
                    colors = IconButtonDefaults.filledIconButtonColors(
                        containerColor = Color(0xFF1E293B)
                    )
                ) {

                    Icon(
                        imageVector =
                            if (expanded)
                                Icons.Default.KeyboardArrowUp
                            else
                                Icons.Default.KeyboardArrowDown,

                        contentDescription = null,
                        tint = Color.White
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            /* ---------------------------------------------------
               QUESTION
            --------------------------------------------------- */

            Text(
                text = model.question,
                color = Color.White,
                fontWeight = FontWeight.Bold,
                fontSize = 17.sp,
                lineHeight = 25.sp
            )

            /* ---------------------------------------------------
               IMAGE
            --------------------------------------------------- */

            if (
                model.image_url.isNotEmpty() &&
                model.image_url != "null"
            ) {

                Spacer(modifier = Modifier.height(16.dp))

                val finalUrl =
                    if (model.image_url.startsWith("http"))
                        model.image_url
                    else
                        "https://medigyaan.xyz/Neurons/${model.image_url}"

                AsyncImage(
                    model = ImageRequest.Builder(LocalContext.current)
                        .data(finalUrl)
                        .crossfade(true)
                        .build(),

                    contentDescription = null,

                    modifier = Modifier
                        .fillMaxWidth()
                        .height(230.dp)
                        .clip(RoundedCornerShape(20.dp)),

                    contentScale = ContentScale.Crop
                )
            }

            Spacer(modifier = Modifier.height(18.dp))

            /* ---------------------------------------------------
               ANSWER BOXES
            --------------------------------------------------- */

            ReviewAnswerBox(
                title = "Your Answer",
                answer =
                    if (model.selected_option.isEmpty())
                        "Not Attempted"
                    else
                        "${model.selected_option}. ${model.selected_answer_text}",

                bg =
                    if (isCorrect)
                        Color(0xFF166534)
                    else
                        Color(0xFF7F1D1D)
            )

            Spacer(modifier = Modifier.height(12.dp))

            ReviewAnswerBox(
                title = "Correct Answer",
                answer = "${model.correct_option}. ${model.correct_answer_text}",
                bg = Color(0xFF14532D)
            )

            /* ---------------------------------------------------
               EXPANDABLE SECTION
            --------------------------------------------------- */

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

                    optionsList.forEach { pair ->

                        val optionKey = pair.first
                        val optionText = pair.second

                        if (optionText.isNotBlank()) {

                            val bgColor = when {

                                optionKey.equals(
                                    model.correct_option,
                                    true
                                ) -> {
                                    Color(0xFF14532D)
                                }

                                optionKey.equals(
                                    model.selected_option,
                                    true
                                ) &&
                                        !model.selected_option.equals(
                                            model.correct_option,
                                            true
                                        ) -> {
                                    Color(0xFF7F1D1D)
                                }

                                else -> {
                                    Color(0xFF1E293B)
                                }
                            }

                            val animatedBg by animateColorAsState(
                                targetValue = bgColor,
                                animationSpec = spring(
                                    dampingRatio = Spring.DampingRatioMediumBouncy
                                ),
                                label = ""
                            )

                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 5.dp)
                                    .clip(RoundedCornerShape(16.dp))
                                    .background(animatedBg)
                                    .padding(14.dp),

                                verticalAlignment = Alignment.CenterVertically
                            ) {

                                Box(
                                    modifier = Modifier
                                        .size(30.dp)
                                        .clip(CircleShape)
                                        .background(
                                            Color.White.copy(alpha = 0.12f)
                                        ),
                                    contentAlignment = Alignment.Center
                                ) {

                                    Text(
                                        text = optionKey,
                                        color = Color.White,
                                        fontWeight = FontWeight.Bold
                                    )
                                }

                                Spacer(modifier = Modifier.width(12.dp))

                                Column(
                                    modifier = Modifier.weight(1f)
                                ) {

                                    Text(
                                        text = optionText,
                                        color = Color.White,
                                        fontSize = 15.sp,
                                        lineHeight = 22.sp
                                    )
                                }

                                Spacer(modifier = Modifier.width(10.dp))

                                when {

                                    optionKey.equals(
                                        model.correct_option,
                                        true
                                    ) -> {

                                        Icon(
                                            imageVector = Icons.Default.CheckCircle,
                                            contentDescription = null,
                                            tint = Color(0xFF4ADE80)
                                        )
                                    }

                                    optionKey.equals(
                                        model.selected_option,
                                        true
                                    ) &&
                                            !model.selected_option.equals(
                                                model.correct_option,
                                                true
                                            ) -> {

                                        Icon(
                                            imageVector = Icons.Default.Warning,
                                            contentDescription = null,
                                            tint = Color(0xFFF87171)
                                        )
                                    }
                                }
                            }
                        }
                    }

                    /* ---------------------------------------------------
                       EXPLANATION
                    --------------------------------------------------- */

                    if (model.explanation.isNotBlank()) {

                        Spacer(modifier = Modifier.height(18.dp))

                        Card(
                            shape = RoundedCornerShape(18.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = Color(0xFF111827)
                            )
                        ) {

                            Column(
                                modifier = Modifier.padding(16.dp)
                            ) {

                                Text(
                                    text = "Explanation",
                                    color = Color.White,
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 16.sp
                                )

                                Spacer(modifier = Modifier.height(10.dp))

                                Text(
                                    text = model.explanation,
                                    color = Color(0xFFCBD5E1),
                                    fontSize = 14.sp,
                                    lineHeight = 23.sp
                                )
                            }
                        }
                    }

                    /* ---------------------------------------------------
                       ASK AI BUTTON
                    --------------------------------------------------- */
                    val context = LocalContext.current
                    Spacer(modifier = Modifier.height(16.dp))

                    Button(
                        onClick = {
                            val act = context as? Activity ?: return@Button
                            val options = listOfNotNull(
                                if (model.option_a.isNotBlank()) "A. ${model.option_a}" else null,
                                if (model.option_b.isNotBlank()) "B. ${model.option_b}" else null,
                                if (model.option_c.isNotBlank()) "C. ${model.option_c}" else null,
                                if (model.option_d.isNotBlank()) "D. ${model.option_d}" else null
                            )
                            val correctAnsText = when (model.correct_option.uppercase()) {
                                "A" -> "${model.correct_option}. ${model.option_a}"
                                "B" -> "${model.correct_option}. ${model.option_b}"
                                "C" -> "${model.correct_option}. ${model.option_c}"
                                "D" -> "${model.correct_option}. ${model.option_d}"
                                else -> "${model.correct_option}. ${model.correct_answer_text}"
                            }
                            AiChatDialogHelper.openAskAiDialog(
                                activity = act,
                                questionId = model.question_id,
                                question = model.question,
                                options = options,
                                correctAnswer = correctAnsText,
                                explanation = model.explanation
                            )
                        },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.primary
                        ),
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            text = "\uD83D\uDCAC Ask AI Medical Tutor",
                            fontWeight = FontWeight.Bold,
                            fontSize = 15.sp
                        )
                    }
                }
            }
        }
    }
}

/* ---------------------------------------------------
   ANSWER BOX
--------------------------------------------------- */

@Composable
fun ReviewAnswerBox(
    title: String,
    answer: String,
    bg: Color
) {

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(18.dp))
            .background(bg)
            .padding(14.dp)
    ) {

        Text(
            text = title,
            color = Color.White.copy(alpha = 0.7f),
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold
        )

        Spacer(modifier = Modifier.height(6.dp))

        Text(
            text = answer,
            color = Color.White,
            fontWeight = FontWeight.SemiBold,
            fontSize = 15.sp,
            lineHeight = 22.sp,
            overflow = TextOverflow.Visible
        )
    }
}
