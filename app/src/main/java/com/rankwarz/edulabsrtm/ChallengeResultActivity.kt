package com.rankwarz.edulabsrtm

import android.graphics.Color
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.android.volley.DefaultRetryPolicy
import com.android.volley.Response
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.firebase.database.DataSnapshot
import com.google.firebase.database.DatabaseError
import com.google.firebase.database.DatabaseReference
import com.google.firebase.database.FirebaseDatabase
import com.google.firebase.database.ValueEventListener
import org.json.JSONArray
import org.json.JSONObject

class ChallengeResultActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "RESULT_DEBUG"
    }

    private lateinit var recyclerView: RecyclerView
    private lateinit var scoreText: TextView
    private lateinit var statusText: TextView
    private lateinit var expGainText: TextView
    private lateinit var homeBtn: Button

    private lateinit var database: DatabaseReference

    private var currentUserId = 0
    private var currentChallengeId = ""
    private var gameMode = ""

    private var isBotMatch = false
    private var botName = "Opponent"

    private val requestQueue by lazy {
        Volley.newRequestQueue(this)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_challenge_result)

        try {
            initViews()

            recyclerView.layoutManager = LinearLayoutManager(this)
            database = FirebaseDatabase.getInstance().reference

            currentChallengeId = intent.getStringExtra("CHALLENGE_ID") ?: ""
            currentUserId = getSafeIntExtra("USER_ID")
            gameMode = intent.getStringExtra("GAME_MODE") ?: ""

            isBotMatch = intent.getBooleanExtra("IS_BOT_MATCH", false) ||
                gameMode.equals("CLASSIC_BOT", ignoreCase = true) ||
                currentChallengeId.startsWith("BOT_MATCH_", ignoreCase = true) || currentChallengeId.startsWith("ARENA_PVP_", ignoreCase = true)
            botName = intent.getStringExtra("BOT_NAME") ?: "Opponent"

            loadReviewData()

            statusText.text = "Loading results..."
            expGainText.visibility = View.GONE

            Log.d(TAG, "ChallengeId=$currentChallengeId UserId=$currentUserId")
            Log.d(TAG, "isBotMatch=$isBotMatch botName=$botName")

            if (currentChallengeId.isBlank() || currentUserId == 0) {
                showFallbackResult()
                return
            }

            fetchBattleResultsFromFirebase(currentChallengeId, currentUserId)

        } catch (e: Exception) {
            Log.e(TAG, "Setup Crash", e)
            statusText.text = "Failed to load results"
        }

        homeBtn.setOnClickListener { finish() }
    }

    private fun initViews() {
        statusText = findViewById(R.id.resultStatus)
        scoreText = findViewById(R.id.scoreText)
        expGainText = findViewById(R.id.expGainText)
        recyclerView = findViewById(R.id.reviewRecyclerView)
        homeBtn = findViewById(R.id.homeBtn)
        setupAppBottomNavigation(findViewById<BottomNavigationView>(R.id.bottomNavigation), R.id.nav_home)
    }

    private fun getSafeIntExtra(key: String): Int {
        return try {
            val value = intent?.extras?.get(key)
            when (value) {
                is Int -> value
                is Long -> value.toInt()
                is Double -> value.toInt()
                is Float -> value.toInt()
                is String -> value.trim().toIntOrNull() ?: 0
                else -> 0
            }
        } catch (e: Exception) {
            Log.e(TAG, "Extra Parse Error: $key", e)
            0
        }
    }

    private fun loadReviewData() {
        val jsonStr = intent.getStringExtra("REVIEW_JSON_STR")
        Log.d(TAG, "loadReviewData: jsonStr=$jsonStr")
        if (jsonStr.isNullOrEmpty()) {
            // Fallback: try to load review JSON from Firebase history records
            val historyRef = database.child("history").child(currentUserId.toString())
            historyRef.orderByChild("challengeId").equalTo(currentChallengeId)
                .addListenerForSingleValueEvent(object : com.google.firebase.database.ValueEventListener {
                    override fun onDataChange(snapshot: com.google.firebase.database.DataSnapshot) {
                        var found = false
                        for (child in snapshot.children) {
                            val review = child.child("reviewJson").getValue(String::class.java)
                            if (!review.isNullOrEmpty()) {
                                found = true
                                Log.d(TAG, "Fetched reviewJson from history: length=${review.length}")
                                try {
                                    val reviewArray = org.json.JSONArray(review)
                                    if (reviewArray.length() == 0) {
                                        statusText?.text = "No questions answered"
                                        recyclerView.visibility = View.GONE
                                    } else {
                                        recyclerView.adapter = ReviewAdapter(reviewArray)
                                        recyclerView.visibility = View.VISIBLE
                                        statusText?.text = ""
                                    }
                                } catch (e: Exception) {
                                    Log.e(TAG, "Error parsing reviewJson from Firebase", e)
                                    statusText?.text = "Error loading review"
                                    recyclerView.visibility = View.GONE
                                }
                                break
                            }
                        }
                        if (!found) {
                            statusText?.text = "No review data available"
                            recyclerView.visibility = View.GONE
                        }
                    }
                    override fun onCancelled(error: com.google.firebase.database.DatabaseError) {
                        Log.e(TAG, "Firebase cancel while fetching review", error.toException())
                        statusText?.text = "Error loading review"
                        recyclerView.visibility = View.GONE
                    }
                })
            // Return now; UI will be updated asynchronously
            return
        }
        try {
            val reviewArray = JSONArray(jsonStr)
            Log.d(TAG, "loadReviewData: review count=${reviewArray.length()}")
            if (reviewArray.length() == 0) {
                statusText?.text = "No questions answered"
                recyclerView.visibility = View.GONE
                return
            }
            recyclerView.adapter = ReviewAdapter(reviewArray)
        } catch (e: Exception) {
            Log.e(TAG, "Review JSON Error", e)
            statusText?.text = "Error loading review"
        }
    }

    private fun showFallbackResult() {
        statusText.text = "Result unavailable"
        statusText.setTextColor(Color.RED)

        scoreText.visibility = View.VISIBLE
        scoreText.text = "Challenge data missing or expired"

        expGainText.visibility = View.GONE
    }

    private fun fetchBattleResultsFromFirebase(challengeId: String, userId: Int) {
        statusText.text = "Fetching battle results..."

        val battleRef = database
            .child("challenges")
            .child(challengeId)
            .child("players")

        battleRef.addListenerForSingleValueEvent(object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                if (isFinishing || isDestroyed) return

                try {
                    if (!snapshot.exists()) {
                        Log.e(TAG, "No Firebase battle data for challengeId=$challengeId")
                        statusText.text = "Battle data missing"
                        scoreText.text = "Results unavailable"
                        expGainText.visibility = View.GONE
                        return
                    }

                    var myHp = 0
                    var myScore = 0
                    var enemyFound = false
                    var topEnemyHp = 0
                    var topEnemyScore = 0
                    var topEnemyName = botName

                    for (playerSnap in snapshot.children) {
                        val pId = playerSnap.key ?: continue
                        val hp = playerSnap.child("hp").getValue(Int::class.java) ?: 0
                        val score = playerSnap.child("score").getValue(Int::class.java) ?: 0
                        val name = playerSnap.child("name").getValue(String::class.java) ?: "Player"

                        Log.d(TAG, "Player=$pId Name=$name Score=$score HP=$hp")

                        if (pId == userId.toString()) {
                            myHp = hp
                            myScore = score
                        } else {
                            enemyFound = true
                            val enemyPower = (score * 100) + hp
                            val currentBest = (topEnemyScore * 100) + topEnemyHp

                            if (enemyPower > currentBest) {
                                topEnemyHp = hp
                                topEnemyScore = score
                                topEnemyName = name
                            }
                        }
                    }

                    Log.d(TAG, "MY SCORE=$myScore HP=$myHp")
                    Log.d(TAG, "ENEMY FOUND=$enemyFound")

                    if (!enemyFound && isBotMatch) {
                        enemyFound = true
                        topEnemyName = botName
                        topEnemyHp = 0
                        topEnemyScore = 0
                    }

                    if (!enemyFound) {
                        statusText.text = "CHALLENGE COMPLETE! 🏆"
                        statusText.setTextColor(Color.parseColor("#2E7D32"))
                        scoreText.text = "Final Score: $myScore ($myHp HP)"

                        syncStatsWithBackend(
                            userId = userId,
                            score = myScore,
                            hp = myHp,
                            isWin = true,
                            cId = challengeId
                        )
                        return
                    }

                    processAndDisplay(
                        myHp = myHp,
                        enHp = topEnemyHp,
                        myS = myScore,
                        enS = topEnemyScore,
                        enName = topEnemyName
                    )

                } catch (e: Exception) {
                    Log.e(TAG, "Result Parse Error", e)
                    statusText.text = "Failed to parse result"
                }
            }

            override fun onCancelled(error: DatabaseError) {
                Log.e(TAG, "Firebase Cancelled", error.toException())
                statusText.text = "Result loading failed"
            }
        })
    }

    private fun processAndDisplay(
        myHp: Int,
        enHp: Int,
        myS: Int,
        enS: Int,
        enName: String
    ) {
        val myPower = (myS * 100) + myHp
        val enPower = (enS * 100) + enHp
        val isWin = myPower >= enPower

        when {
            myPower > enPower -> {
                statusText.text = "VICTORY! 🏆"
                statusText.setTextColor(Color.parseColor("#2E7D32"))
            }
            myPower < enPower -> {
                statusText.text = "DEFEAT! 💀"
                statusText.setTextColor(Color.RED)
            }
            else -> {
                statusText.text = "DRAW! 🤝"
                statusText.setTextColor(Color.GRAY)
            }
        }

        scoreText.text = "You: $myS (${myHp}HP)\n$enName: $enS (${enHp}HP)"

        syncStatsWithBackend(
            userId = currentUserId,
            score = myS,
            hp = myHp,
            isWin = isWin,
            cId = currentChallengeId
        )
    }

    private fun syncStatsWithBackend(
        userId: Int,
        score: Int,
        hp: Int,
        isWin: Boolean,
        cId: String
    ) {
        val fallbackExp = calculateLocalReward(score, isWin)
        val url = "https://medigyaan.xyz/Neurons/api/sync_game_stats.php"

        expGainText.visibility = View.VISIBLE
        expGainText.text = "Syncing rewards..."

        if (isBotMatch || cId.startsWith("BOT_MATCH_", ignoreCase = true) || cId.startsWith("ARENA_PVP_", ignoreCase = true) || cId.isBlank()) {
            expGainText.text = "+$fallbackExp EXP"
            Log.d(TAG, "Skipping server reward sync for bot/synthetic match -> cId=$cId")
            return
        }

        val request = object : StringRequest(
            Method.POST,
            url,
            Response.Listener { response ->
                try {
                    Log.d(TAG, "SYNC RESPONSE: $response")
                    val json = JSONObject(response)

                    val status = json.optString("status")
                    if (status.equals("success", true) || status.equals("ok", true) || status == "1") {
                        val earnedObj = json.optJSONObject("earned")
                        val exp = earnedObj?.optInt("total_exp", fallbackExp) ?: fallbackExp
                        val mult = earnedObj?.optDouble("multiplier", 1.0) ?: 1.0

                        expGainText.text = "+$exp EXP x$mult Bonus"
                    } else {
                        expGainText.text = "+$fallbackExp EXP"
                        Log.w(TAG, "Reward sync returned non-success status: $status")
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Sync JSON Error", e)
                    expGainText.text = "+$fallbackExp EXP"
                }
            },
            Response.ErrorListener { error ->
                Log.e(TAG, "Volley Error", error)
                expGainText.text = "+$fallbackExp EXP"
            }
        ) {
            override fun getParams(): MutableMap<String, String> {
                return hashMapOf(
                    "user_id" to userId.toString(),
                    "score" to score.toString(),
                    "hp" to hp.toString(),
                    "is_win" to if (isWin) "1" else "0",
                    "challenge_id" to cId,
                    "total_questions" to "10"
                )
            }
        }

        request.retryPolicy = DefaultRetryPolicy(
            10000,
            1,
            1f
        )

        request.setShouldCache(false)
        request.tag = "sync_result"
        requestQueue.add(request)
    }

    private fun calculateLocalReward(score: Int, isWin: Boolean): Int {
        return when {
            isWin -> 120 + score
            score >= 40 -> 100 + (score / 2)
            else -> 60 + (score / 3)
        }.coerceAtLeast(0)
    }

    override fun onDestroy() {
        super.onDestroy()
        requestQueue.cancelAll("sync_result")
    }
}
