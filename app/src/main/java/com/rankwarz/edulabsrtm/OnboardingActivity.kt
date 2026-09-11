package com.rankwarz.edulabsrtm

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Chat
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Message
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

class OnboardingActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
        if (prefs.getBoolean("onboarding_complete", false)) {
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
            return
        }
        setContent {
            MaterialTheme {
                OnboardingScreen()
            }
        }
    }
}

@Composable
fun OnboardingScreen() {
    val context = LocalContext.current
    var currentPage by remember { mutableStateOf(0) }
    val totalPages = 6
    val pages = remember {
        listOf(
            OnboardingPage("Welcome to Medigyaan", "Your AI-powered NEET preparation companion", Icons.Filled.AutoAwesome, Color(0xFF62E49D)),
            OnboardingPage("AI Chat", "Ask anything to our medical AI counselor 24/7", Icons.Filled.Chat, Color(0xFF38BDF8)),
            OnboardingPage("College Predictor", "Get AI predictions for NEET PG/UG admissions", Icons.Filled.Home, Color(0xFFFFD700)),
            OnboardingPage("Rank Badges", "Climb from Aspirant to Legend with every answer", Icons.Filled.Favorite, Color(0xFFFF4081)),
            OnboardingPage("Practice Tests", "Timed MCQ tests, rapid fire, and mock exams", Icons.Filled.Search, Color(0xFFB7C8FF)),
            OnboardingPage("Connect & Compete", "Challenge friends, share questions, climb leaderboard", Icons.Filled.Message, Color(0xFFF4C95D))
        )
    }

    val page = pages[currentPage]
    val progress = currentPage.toFloat() / (totalPages - 1)

    Scaffold(
        bottomBar = {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .navigationBarsPadding()
                    .padding(horizontal = 24.dp, vertical = 16.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                TextButton(onClick = {
                    val prefs = context.getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
                    prefs.edit().putBoolean("onboarding_complete", true).apply()
                    (context as ComponentActivity).startActivity(Intent(context, LoginActivity::class.java))
                    (context as ComponentActivity).finish()
                }) {
                    Text("Skip", color = Color.White.copy(alpha = 0.7f), fontWeight = FontWeight.Bold)
                }
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                    pages.forEachIndexed { index, p ->
                        Box(
                            modifier = Modifier
                                .size(if (index == currentPage) 10.dp else 8.dp)
                                .clip(CircleShape)
                                .background(if (index == currentPage) p.glowColor else Color.Gray.copy(alpha = 0.5f))
                        )
                    }
                }
                TextButton(onClick = {
                    if (currentPage < totalPages - 1) {
                        currentPage++
                    } else {
                        val prefs = context.getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
                        prefs.edit().putBoolean("onboarding_complete", true).apply()
                        (context as ComponentActivity).startActivity(Intent(context, LoginActivity::class.java))
                        (context as ComponentActivity).finish()
                    }
                }) {
                    Text(if (currentPage == totalPages - 1) "Get Started" else "Next →", color = page.glowColor, fontWeight = FontWeight.Bold)
                }
            }
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(Color(0xFF0A0F1C)),
            contentAlignment = Alignment.Center
        ) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.padding(horizontal = 32.dp)
            ) {
                val iconScale by animateFloatAsState(
                    targetValue = 1f + progress * 0.1f,
                    animationSpec = tween(500)
                )
                val iconAlpha by animateFloatAsState(
                    targetValue = 1f - progress * 0.2f,
                    animationSpec = tween(500)
                )

                Box(
                    modifier = Modifier
                        .size(180.dp)
                        .graphicsLayer(scaleX = iconScale, scaleY = iconScale)
                        .background(
                            brush = Brush.radialGradient(
                                listOf(
                                    page.glowColor.copy(alpha = 0.3f * iconAlpha),
                                    page.glowColor.copy(alpha = 0.1f),
                                    Color.Transparent
                                )
                            ),
                            shape = CircleShape
                        ),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = page.icon,
                        contentDescription = page.title,
                        modifier = Modifier.size(80.dp),
                        tint = page.glowColor
                    )
                }

                Spacer(modifier = Modifier.height(40.dp))

                Text(
                    text = page.title,
                    color = Color.White,
                    fontSize = 28.sp,
                    fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center
                )
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = page.description,
                    color = Color(0xFFB7C2D3),
                    fontSize = 16.sp,
                    textAlign = TextAlign.Center
                )
            }
        }
    }
}

data class OnboardingPage(
    val title: String,
    val description: String,
    val icon: ImageVector,
    val glowColor: Color
)