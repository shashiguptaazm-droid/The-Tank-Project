package com.rankwarz.edulabsrtm

import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.graphics.Color
import android.os.Bundle
import android.widget.Toast
import androidx.activity.compose.setContent
import androidx.appcompat.app.AppCompatActivity
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.ExperimentalMaterialApi
import androidx.compose.material.TopAppBar
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color as ComposeColor
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.android.volley.Request
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.rankwarz.edulabsrtm.ui.theme.EduLabsRTMThemeFromPreferences
import org.json.JSONObject

data class LeaderboardUser(
    val id: String,
    val name: String,
    val photo: String,
    val exp: Int,
    val level: Int,
    val rankTitle: String = "Aspirant"
)

class LeaderboardActivity : AppCompatActivity() {

    companion object {
        private const val BASE_URL = "https://medigyaan.xyz/Neurons/"
        private const val PREF_NAME = "MY_APP"
        private const val KEY_USER_ID = "user_id"
    }

    private lateinit var prefs: SharedPreferences
    private var userId: Int = 0

    private val _userList = mutableStateListOf<LeaderboardUser>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        prefs = getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        userId = prefs.getInt(KEY_USER_ID, 0)

        setContent {
            EduLabsRTMThemeFromPreferences {
                LeaderboardScreen(_userList) { clickedUser ->
                    val intent = Intent(this, ProfileActivity::class.java)
                    intent.putExtra("TARGET_USER_ID", clickedUser.id.toIntOrNull() ?: 0)
                    startActivity(intent)
                }
            }
        }

        loadLeaderboard()
    }

    @OptIn(ExperimentalMaterial3Api::class)
    @Composable
    fun LeaderboardScreen(users: List<LeaderboardUser>, onUserClick: (LeaderboardUser) -> Unit) {
        val top3 = users.take(3)
        val others = users.drop(3)

        Scaffold(
            topBar = {
                TopAppBar(
                    title = {
                        Text(
                            "Leaderboard",
                            fontWeight = FontWeight.Bold,
                            color = androidx.compose.material3.MaterialTheme.colorScheme.onSurface
                        )
                    },
                    backgroundColor = androidx.compose.material3.MaterialTheme.colorScheme.surface,
                    elevation = 0.dp
                )
            },
            bottomBar = {
                AndroidView(
                    modifier = Modifier.fillMaxWidth(),
                    factory = { context ->
                        BottomNavigationView(context).apply {
                            inflateMenu(R.menu.bottom_nav_menu)
                            this@LeaderboardActivity.setupAppBottomNavigation(this, R.id.nav_home)
                        }
                    }
                )
            }
        ) { padding ->
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .background(androidx.compose.material3.MaterialTheme.colorScheme.background)
            ) {
                if (top3.isNotEmpty()) {
                    PodiumSection(top3)
                }

                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    itemsIndexed(others) { index, user ->
                        LeaderboardItem(user, index + 4, onUserClick)
                    }
                }
            }
        }
    }

    @Composable
    fun PodiumSection(topUsers: List<LeaderboardUser>) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(24.dp),
            horizontalArrangement = Arrangement.SpaceEvenly,
            verticalAlignment = Alignment.Bottom
        ) {
            // Second Place
            topUsers.getOrNull(1)?.let { PodiumPlace(it, 2, 80.dp, ComposeColor(0xFFC0C0C0)) }

            // First Place
            topUsers.getOrNull(0)?.let { PodiumPlace(it, 1, 110.dp, ComposeColor(0xFFFFD700)) }

            // Third Place
            topUsers.getOrNull(2)?.let { PodiumPlace(it, 3, 70.dp, ComposeColor(0xFFCD7F32)) }
        }
    }

    @Composable
    fun PodiumPlace(user: LeaderboardUser, rank: Int, size: androidx.compose.ui.unit.Dp, color: ComposeColor) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Box(contentAlignment = Alignment.BottomEnd) {
                AsyncImage(
                    model = getImageUrl(user.photo),
                    contentDescription = null,
                    modifier = Modifier
                        .size(size)
                        .clip(CircleShape)
                        .background(ComposeColor.LightGray),
                    contentScale = ContentScale.Crop
                )
                Surface(
                    shape = CircleShape,
                    color = color,
                    shadowElevation = 4.dp,
                    modifier = Modifier.size(24.dp)
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Text(rank.toString(), fontSize = 12.sp, fontWeight = FontWeight.Bold, color = ComposeColor.White)
                    }
                }
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text(user.name, fontWeight = FontWeight.Bold, fontSize = 14.sp)
            Text("${user.exp} XP", fontSize = 12.sp, color = ComposeColor.Gray)
        }
    }

    @OptIn(ExperimentalMaterialApi::class)
    @Composable
    fun LeaderboardItem(user: LeaderboardUser, rank: Int, onClick: (LeaderboardUser) -> Unit) {
        Card(
            shape = RoundedCornerShape(16.dp),
            modifier = Modifier.fillMaxWidth(),
            onClick = { onClick(user) },
            elevation = androidx.compose.material3.CardDefaults.cardElevation(defaultElevation = 2.dp)
        ) {
            Row(
                modifier = Modifier
                    .padding(16.dp)
                    .fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "#$rank",
                    modifier = Modifier.width(40.dp),
                    fontWeight = FontWeight.Bold,
                    color = ComposeColor.Gray
                )

                AsyncImage(
                    model = getImageUrl(user.photo),
                    contentDescription = null,
                    modifier = Modifier
                        .size(50.dp)
                        .clip(CircleShape),
                    contentScale = ContentScale.Crop
                )

                Spacer(modifier = Modifier.width(16.dp))

                Column(modifier = Modifier.weight(1f)) {
                    Text(user.name, fontWeight = FontWeight.SemiBold, fontSize = 16.sp)
                    Text("Level ${user.level} • ${user.rankTitle}", fontSize = 12.sp, color = ComposeColor.Gray)
                }

                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        "${user.exp} XP",
                        fontWeight = FontWeight.Bold,
                        color = ComposeColor(0xFF4CAF50)
                    )
                }
            }
        }
    }

    private fun getImageUrl(photo: String): String {
        return if (photo.startsWith("http")) {
            photo
        } else {
            BASE_URL + photo.replace("./", "").trimStart('/')
        }
    }


    private fun loadLeaderboard() {
        val url = "${BASE_URL}leaderboard1.php?user_id=$userId"

        val request = StringRequest(
            Request.Method.GET,
            url,
            { response ->
                try {
                    val root = JSONObject(response)

                    if (root.optString("status") == "success") {
                        val arr = when {
                            root.has("users") -> root.getJSONArray("users")
                            root.has("data") -> root.getJSONArray("data")
                            else -> null
                        }

                        if (arr == null) {
                            Toast.makeText(this, "No leaderboard data", Toast.LENGTH_SHORT).show()
                            return@StringRequest
                        }

                        _userList.clear()

                        for (i in 0 until arr.length()) {
                            val obj = arr.getJSONObject(i)

                            val id = obj.optString("id", obj.optString("user_id", "0"))
                            val name = obj.optString("name", "User")
                            val photo = obj.optString("photo", "Default.jpg")
                            val exp = obj.optInt("exp", 0)
                            val level = obj.optInt("level", 1)
                            val rankTitle = obj.optString("rank_title", "Aspirant")

                            _userList.add(
                                LeaderboardUser(
                                    id = id,
                                    name = name,
                                    photo = photo,
                                    exp = exp,
                                    level = level,
                                    rankTitle = rankTitle
                                )
                            )
                        }
                    } else {
                        Toast.makeText(
                            this,
                            root.optString("message", "Server error"),
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                } catch (e: Exception) {
                    e.printStackTrace()
                    Toast.makeText(this, "Parse error", Toast.LENGTH_SHORT).show()
                }
            },
            { error ->
                error.printStackTrace()
                Toast.makeText(this, "Network error", Toast.LENGTH_SHORT).show()
            }
        )

        Volley.newRequestQueue(this).add(request)
    }
}
