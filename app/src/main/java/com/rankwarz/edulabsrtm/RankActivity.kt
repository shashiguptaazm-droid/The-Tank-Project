package com.rankwarz.edulabsrtm

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.ui.res.painterResource
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.BottomNavigation
import androidx.compose.material.BottomNavigationItem
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Chat
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Message
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rankwarz.edulabsrtm.ui.theme.EduLabsRTMThemeFromPreferences

// --- Data Models ---
data class RankTier(
    val name: String,
    val minExp: Int,
    val iconRes: Int,
    val accentColor: Color,
    val description: String
)

object RankManager {
    val tiers = listOf(
        RankTier("ASPIRANT", 0, R.drawable.ic_beginner, Color(0xFFB0BEC5), "The first step of many."),
        RankTier("ROOKIE", 500, R.drawable.ic_rookie, Color(0xFFCD7F32), "Learning the ropes."),
        RankTier("SKILLED", 1500, R.drawable.ic_skilled, Color(0xFFC0C0C0), "A rising talent."),
        RankTier("WARRIOR", 3500, R.drawable.ic_warrior, Color(0xFFFFD700), "Battle-hardened student."),
        RankTier("EXPERT", 7500, R.drawable.ic_warrior, Color(0xFFE5E4E2), "Deep mastery of concepts."),
        RankTier("SCHOLAR", 15000, R.drawable.ic_skilled, Color(0xFFB9F2FF), "A true academic force."),
        RankTier("MASTER", 30000, R.drawable.ic_master, Color(0xFFFF4081), "Leading by example."),
        RankTier("GRANDMASTER", 60000, R.drawable.ic_master, Color(0xFF7B1FFF), "Virtuoso of knowledge."),
        RankTier("LEGEND", 100000, R.drawable.ic_legend, Color(0xFF00E5FF), "The ultimate pinnacle.")
    )

    fun getCurrentTier(exp: Int): RankTier = tiers.last { exp >= it.minExp }

    fun getNextTier(exp: Int): RankTier? = tiers.firstOrNull { it.minExp > exp }
}

// --- Activity Implementation ---
class RankActivity : ComponentActivity() {
    // Held in Compose state so the badge recomposes the moment EXP changes.
    private var userExpState by mutableStateOf(0)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val prefs = getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
        userExpState = prefs.getInt("user_exp", 0)

        setContent {
            EduLabsRTMThemeFromPreferences {
                var selectedTab by remember { mutableStateOf(0) }
                Scaffold(
                    bottomBar = {
                        // Pad above the system navigation bar so this bar matches the
                        // Dashboard/XML bottom bar and never overlaps the Android nav icons.
                        BottomNavigation(modifier = Modifier.navigationBarsPadding()) {
                            BottomNavigationItem(
                                selected = selectedTab == 0,
                                onClick = {
                                    selectedTab = 0
                                    startActivity(Intent(this@RankActivity, DashboardActivity::class.java))
                                    finish()
                                },
                                icon = { Icon(painterResource(R.drawable.ic_home), contentDescription = "Home") },
                                label = { Text("Home") }
                            )
                            BottomNavigationItem(
                                selected = selectedTab == 1,
                                onClick = { selectedTab = 1 },
                                icon = { Icon(painterResource(R.drawable.ic_comment), contentDescription = "AI Chat") },
                                label = { Text("AI Chat") }
                            )
                            BottomNavigationItem(
                                selected = selectedTab == 2,
                                onClick = {
                                    selectedTab = 2
                                    startActivity(Intent(this@RankActivity, GlobalSearchActivity::class.java))
                                    finish()
                                },
                                icon = { Icon(painterResource(R.drawable.ic_search), contentDescription = "Search") },
                                label = { Text("Search") }
                            )
                            BottomNavigationItem(
                                selected = selectedTab == 3,
                                onClick = {
                                    selectedTab = 3
                                    startActivity(Intent(this@RankActivity, ChallengeListActivity::class.java))
                                    finish()
                                },
                                icon = { Icon(painterResource(R.drawable.ic_feed), contentDescription = "History") },
                                label = { Text("History") }
                            )
                            BottomNavigationItem(
                                selected = selectedTab == 4,
                                onClick = {
                                    selectedTab = 4
                                    startActivity(Intent(this@RankActivity, MessengerActivity::class.java))
                                    finish()
                                },
                                icon = { Icon(painterResource(R.drawable.ic_message), contentDescription = "Messages") },
                                label = { Text("Messages") }
                            )
                        }
                    }
                ) { innerPadding ->
                    RankScreen(
                        userExpState,
                        onBack = { finish() },
                        modifier = Modifier.padding(innerPadding)
                    )
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        // Re-read EXP every time the screen is shown so the rank badge is never stale
        // (e.g. after earning XP in a quiz, then tapping back into this screen).
        userExpState = getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
            .getInt("user_exp", userExpState)
    }
}

@Composable
fun RankScreen(userExp: Int, onBack: () -> Unit, modifier: Modifier = Modifier) {
    // Keyed on userExp so the badge/progress recompose whenever EXP is re-read on resume.
    val currentTier = remember(userExp) { RankManager.getCurrentTier(userExp) }
    val nextTier = remember(userExp) { RankManager.getNextTier(userExp) }
    val progress = remember(userExp, currentTier, nextTier) {
        if (nextTier != null) {
            val totalInTier = nextTier.minExp - currentTier.minExp
            val earnedInTier = userExp - currentTier.minExp
            (earnedInTier.toFloat() / totalInTier.toFloat()).coerceIn(0f, 1f)
        } else 1f
    }

    Surface(
        modifier = modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Header
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(onClick = onBack) {
                    Icon(
                        Icons.Default.ArrowBack,
                        contentDescription = "Back",
                        tint = MaterialTheme.colorScheme.onBackground
                    )
                }
                Text(
                    "RANK PROGRESSION",
                    color = MaterialTheme.colorScheme.onBackground,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Black,
                    modifier = Modifier.weight(1f),
                    textAlign = TextAlign.Center
                )
                Spacer(modifier = Modifier.width(48.dp)) // To balance the back button
            }

            Spacer(modifier = Modifier.height(30.dp))

            // Current Rank Badge with Premium Sweep Arc Ring
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(220.dp)
                    .drawBehind {
                        // Background track
                        drawCircle(
                            color = currentTier.accentColor.copy(alpha = 0.15f),
                            radius = size.minDimension / 2,
                            style = Stroke(width = 6.dp.toPx())
                        )
                        // Dynamic progress arc
                        drawArc(
                            color = currentTier.accentColor,
                            startAngle = -90f,
                            sweepAngle = 360f * progress,
                            useCenter = false,
                            style = Stroke(width = 6.dp.toPx(), cap = androidx.compose.ui.graphics.StrokeCap.Round)
                        )
                    }
            ) {
                Image(
                    painter = painterResource(id = currentTier.iconRes),
                    contentDescription = currentTier.name,
                    modifier = Modifier.size(140.dp)
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            Text(
                text = currentTier.name,
                color = currentTier.accentColor,
                fontSize = 32.sp,
                fontWeight = FontWeight.ExtraBold,
                textAlign = TextAlign.Center
            )

            Text(
                text = currentTier.description,
                color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.7f),
                fontSize = 14.sp,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(horizontal = 32.dp)
            )

            Spacer(modifier = Modifier.height(40.dp))

            // Progression Card
            ProgressionCard(userExp, currentTier, nextTier)

            Spacer(modifier = Modifier.height(32.dp))

            // All Badges Section
            Text(
                "ALL RANK BADGES",
                color = MaterialTheme.colorScheme.onBackground,
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.fillMaxWidth(),
                textAlign = TextAlign.Start
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Simplified Grid for small badges
            RankBadgesGrid(userExp)

            Spacer(modifier = Modifier.height(50.dp))
        }
    }
}

@Composable
fun ProgressionCard(userExp: Int, current: RankTier, next: RankTier?) {
    val progress = remember {
        if (next != null) {
            val totalInTier = next.minExp - current.minExp
            val earnedInTier = userExp - current.minExp
            (earnedInTier.toFloat() / totalInTier.toFloat()).coerceIn(0f, 1f)
        } else 1f
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.2f))
    ) {
        Column(modifier = Modifier.padding(24.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    "${userExp} XP",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    fontWeight = FontWeight.Bold
                )
                if (next != null) {
                    Text(
                        "Goal: ${next.minExp} XP",
                        color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f),
                        fontSize = 12.sp
                    )
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Progress Bar
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(12.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.outline.copy(alpha = 0.2f))
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth(progress)
                        .fillMaxHeight()
                        .clip(CircleShape)
                        .background(
                            Brush.horizontalGradient(
                                listOf(
                                    MaterialTheme.colorScheme.primary,
                                    MaterialTheme.colorScheme.secondary
                                )
                            )
                        )
                )
            }

            if (next != null) {
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = "${next.minExp - userExp} XP needed for ${next.name}",
                    color = MaterialTheme.colorScheme.primary,
                    fontSize = 12.sp,
                    modifier = Modifier.fillMaxWidth(),
                    textAlign = TextAlign.Center
                )
            }
        }
    }
}

@Composable
fun RankBadgesGrid(userExp: Int) {
    // We use a simple Column + Row approach since LazyVerticalGrid
    // doesn't work well inside a vertical scroll state directly without fixed height
    val chunks = RankManager.tiers.chunked(3)

    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        chunks.forEach { rowTiers ->
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                rowTiers.forEach { tier ->
                    BadgeSmallItem(tier, isUnlocked = userExp >= tier.minExp, modifier = Modifier.weight(1f))
                }
                // Fill empty slots if row isn't full
                if (rowTiers.size < 3) {
                    repeat(3 - rowTiers.size) { Spacer(modifier = Modifier.weight(1f)) }
                }
            }
        }
    }
}

@Composable
fun BadgeSmallItem(tier: RankTier, isUnlocked: Boolean, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(16.dp))
            .background(
                if (isUnlocked) MaterialTheme.colorScheme.surfaceVariant
                else MaterialTheme.colorScheme.surface.copy(alpha = 0.5f)
            )
            .padding(12.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Image(
            painter = painterResource(id = tier.iconRes),
            contentDescription = null,
            modifier = Modifier
                .size(50.dp)
                .then(if (!isUnlocked) Modifier.drawBehind { drawRect(Color.Black.copy(alpha = 0.6f)) } else Modifier),
            alpha = if (isUnlocked) 1f else 0.3f
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = tier.name,
            color = if (isUnlocked) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.4f),
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
            maxLines = 1
        )
        Text(
            text = "${tier.minExp} XP",
            color = if (isUnlocked) tier.accentColor else MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.2f),
            fontSize = 9.sp
        )
    }
}


