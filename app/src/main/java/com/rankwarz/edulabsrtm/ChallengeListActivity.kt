package com.rankwarz.edulabsrtm

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.database.*

class ChallengeListActivity : AppCompatActivity() {

    private lateinit var recyclerView: RecyclerView
    private lateinit var loader: ProgressBar
    private lateinit var btnChallenges: TextView
    private lateinit var btnHistory: TextView
    private lateinit var emptyView: TextView
    private lateinit var bottomNav: BottomNavigationView

    private lateinit var challengeDatabase: DatabaseReference
    private lateinit var historyDatabase: DatabaseReference

    private val challengeList = mutableListOf<ChallengeModel>()
    private val historyList = mutableListOf<HistoryModel>()

    private var challengeAdapter: ChallengeAdapter? = null
    private var historyAdapter: HistoryAdapter? = null

    private var currentUserId: Int = 0
    private var currentMode: String = MODE_CHALLENGES

    private var challengeListener: ValueEventListener? = null
    private var historyListener: ValueEventListener? = null

    companion object {
        private const val TAG = "CHALLENGE_LIST"
        private const val MODE_CHALLENGES = "CHALLENGES"
        private const val MODE_HISTORY = "HISTORY"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Log.d(TAG, "onCreate started")
        setContentView(R.layout.activity_challenge_list)

        recyclerView = findViewById(R.id.challengeRecyclerView)
        loader = findViewById(R.id.loader)
        emptyView = findViewById(R.id.emptyView)
        btnChallenges = findViewById(R.id.btnChallengesTab)
        btnHistory = findViewById(R.id.btnHistoryTab)
        bottomNav = findViewById(R.id.bottomNavigation)

        recyclerView.layoutManager = LinearLayoutManager(this)

        val prefs = getSharedPreferences("MY_APP", MODE_PRIVATE)
        currentUserId = prefs.getInt("user_id", 0)

        Log.d(TAG, "Loaded user_id = $currentUserId")

        if (currentUserId == 0) {
            Log.e(TAG, "User not logged in, finishing activity")
            Toast.makeText(this, "User not logged in", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        challengeDatabase = FirebaseDatabase.getInstance().getReference("lobbies")
        historyDatabase = FirebaseDatabase.getInstance()
            .getReference("history")
            .child(currentUserId.toString())

        Log.d(TAG, "Firebase references initialized")

        setupAdapters()
        setupBottomNavigation()
        setupTabButtons()

        currentMode = intent.getStringExtra("MODE") ?: MODE_CHALLENGES
        Log.d(TAG, "Initial mode = $currentMode")

        ensureFirebaseAuth {
            Log.d(TAG, "Firebase auth ready, attaching listener for mode = $currentMode")
            if (currentMode == MODE_HISTORY) {
                attachHistoryListener()
            } else {
                attachRealtimeListener()
            }
        }
    }

    private fun setupAdapters() {
        Log.d(TAG, "Setting up adapters")

        challengeAdapter = ChallengeAdapter(challengeList) { selected ->
            Log.d(TAG, "Challenge clicked: id=${selected.id}")

            val intent = Intent(this, TopicChallengeResultActivity::class.java)
            intent.putExtra("CHALLENGE_ID", selected.id)
            intent.putExtra("USER_ID", currentUserId)
            startActivity(intent)
        }

        historyAdapter = HistoryAdapter(historyList) { selected ->
            Log.d(TAG, "History item clicked: title=${selected.title}")

            if (!selected.reviewJson.isNullOrEmpty()) {
                val intent = Intent(this, ReviewActivity::class.java)
                intent.putExtra("REVIEW_JSON", selected.reviewJson)
                startActivity(intent)
            } else {
                Toast.makeText(this, "Review data not available for this session", Toast.LENGTH_SHORT).show()
            }
        }

        Log.d(TAG, "Adapters ready")
    }

    private fun ensureFirebaseAuth(onReady: () -> Unit) {
        val current = FirebaseAuth.getInstance().currentUser
        if (current != null) {
            Log.d(TAG, "Auth OK: ${current.uid}")
            onReady()
        } else {
            Log.d(TAG, "No Firebase auth user, signing in anonymously")
            FirebaseAuth.getInstance().signInAnonymously()
                .addOnSuccessListener { result ->
                    Log.d(TAG, "Anonymous auth success: ${result.user?.uid}")
                    onReady()
                }
                .addOnFailureListener { e ->
                    Log.e(TAG, "Auth failed", e)
                    Toast.makeText(this, "Auth failed", Toast.LENGTH_SHORT).show()
                }
        }
    }

    private fun attachRealtimeListener() {
        Log.d(TAG, "attachRealtimeListener called")

        removeHistoryListener()
        removeChallengeListener()

        updateTabUI()
        loader.visibility = View.VISIBLE
        Log.d(TAG, "Loading challenges...")

        challengeListener = object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                Log.d(TAG, "Challenge snapshot received, total lobbies=${snapshot.childrenCount}")

                challengeList.clear()
                var matchedCount = 0

                for (child in snapshot.children) {
                    try {
                        val lobbyId = child.key
                        if (lobbyId == null) {
                            Log.d(TAG, "Skipping lobby with null key")
                            continue
                        }

                        val playersNode = child.child("players")
                        if (!playersNode.exists()) {
                            Log.d(TAG, "Skipping $lobbyId (no players node)")
                            continue
                        }

                        val isUserInside = playersNode.hasChild(currentUserId.toString())
                        Log.d(TAG, "Lobby $lobbyId players check, userInside=$isUserInside")

                        if (!isUserInside) continue

                        val model = child.getValue(ChallengeModel::class.java) ?: ChallengeModel()
                        model.id = lobbyId
                        challengeList.add(model)
                        matchedCount++

                        Log.d(TAG, "Added challenge lobby: $lobbyId")
                    } catch (e: Exception) {
                        Log.e(TAG, "Parse error for lobby=${child.key}", e)
                    }
                }

                challengeList.sortByDescending {
                    it.id.replace("lobby_", "").toLongOrNull() ?: 0L
                }

                Log.d(TAG, "Challenges matched=$matchedCount, final list size=${challengeList.size}")
                updateChallengeUI()
            }

            override fun onCancelled(error: DatabaseError) {
                loader.visibility = View.GONE
                Log.e(TAG, "Challenge listener cancelled: ${error.message}", error.toException())
                Toast.makeText(this@ChallengeListActivity, "Permission denied", Toast.LENGTH_SHORT).show()
            }
        }

        challengeDatabase.addValueEventListener(challengeListener as ValueEventListener)
        Log.d(TAG, "Challenge listener attached")
    }

    private fun attachHistoryListener() {
        Log.d(TAG, "attachHistoryListener called")

        removeChallengeListener()
        removeHistoryListener()

        updateTabUI()
        loader.visibility = View.VISIBLE
        Log.d(TAG, "Loading history for user=$currentUserId")

        historyListener = object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                Log.d(TAG, "History snapshot received, total records=${snapshot.childrenCount}")

                historyList.clear()
                var count = 0

                for (child in snapshot.children) {
                    try {
                        val item = child.getValue(HistoryModel::class.java)
                        if (item == null) {
                            Log.d(TAG, "Skipping null history item at key=${child.key}")
                            continue
                        }

                        historyList.add(item)
                        count++

                        Log.d(
                            TAG,
                            "History item added: mode=${item.mode}, title=${item.title}, topic=${item.topic}, score=${item.score}, time=${item.timestamp}"
                        )
                    } catch (e: Exception) {
                        Log.e(TAG, "History parse error at key=${child.key}", e)
                    }
                }

                historyList.sortByDescending { it.timestamp }

                Log.d(TAG, "History loaded count=$count, final size=${historyList.size}")
                updateHistoryUI()
            }

            override fun onCancelled(error: DatabaseError) {
                loader.visibility = View.GONE
                Log.e(TAG, "History listener cancelled: ${error.message}", error.toException())
                Toast.makeText(this@ChallengeListActivity, "Failed to load history", Toast.LENGTH_SHORT).show()
            }
        }

        historyDatabase.orderByChild("timestamp")
            .addValueEventListener(historyListener as ValueEventListener)

        Log.d(TAG, "History listener attached")
    }

    private fun updateChallengeUI() {
        Log.d(TAG, "updateChallengeUI called, items=${challengeList.size}")
        loader.visibility = View.GONE

        if (challengeList.isEmpty()) {
            Log.d(TAG, "No challenges found")
            showEmpty("No challenges yet")
            return
        }

        recyclerView.adapter = challengeAdapter
        recyclerView.visibility = View.VISIBLE
        emptyView.visibility = View.GONE

        Log.d(TAG, "Challenge UI updated successfully")
    }

    private fun updateHistoryUI() {
        Log.d(TAG, "updateHistoryUI called, items=${historyList.size}")
        loader.visibility = View.GONE

        if (historyList.isEmpty()) {
            Log.d(TAG, "No history found")
            showEmpty("No history yet")
            return
        }

        recyclerView.adapter = historyAdapter
        recyclerView.visibility = View.VISIBLE
        emptyView.visibility = View.GONE

        Log.d(TAG, "History UI updated successfully")
    }

    private fun showEmpty(msg: String) {
        Log.d(TAG, "showEmpty: $msg")
        recyclerView.visibility = View.GONE
        emptyView.visibility = View.VISIBLE
        emptyView.text = msg
    }

    fun showChallenges() {
        Log.d(TAG, "showChallenges requested")
        currentMode = MODE_CHALLENGES
        attachRealtimeListener()
    }

    fun showHistory() {
        Log.d(TAG, "showHistory requested")
        currentMode = MODE_HISTORY
        attachHistoryListener()
    }

    private fun setupTabButtons() {
        btnChallenges.setOnClickListener {
            if (currentMode != MODE_CHALLENGES) {
                showChallenges()
            }
        }
        btnHistory.setOnClickListener {
            if (currentMode != MODE_HISTORY) {
                showHistory()
            }
        }
    }

    private fun updateTabUI() {
        if (currentMode == MODE_CHALLENGES) {
            btnChallenges.setTextColor(ContextCompat.getColor(this, R.color.white))
            btnChallenges.setBackgroundResource(R.drawable.tab_selected_bg)

            btnHistory.setTextColor(ContextCompat.getColor(this, R.color.gray))
            btnHistory.setBackgroundResource(0)
        } else {
            btnHistory.setTextColor(ContextCompat.getColor(this, R.color.white))
            btnHistory.setBackgroundResource(R.drawable.tab_selected_bg)

            btnChallenges.setTextColor(ContextCompat.getColor(this, R.color.gray))
            btnChallenges.setBackgroundResource(0)
        }
    }

    private fun setupBottomNavigation() {
        Log.d(TAG, "Setting up bottom navigation")
        setupAppBottomNavigation(bottomNav, R.id.nav_feed)
    }

    private fun removeChallengeListener() {
        if (::challengeDatabase.isInitialized && challengeListener != null) {
            Log.d(TAG, "Removing old challenge listener")
            challengeDatabase.removeEventListener(challengeListener!!)
            challengeListener = null
        }
    }

    private fun removeHistoryListener() {
        if (::historyDatabase.isInitialized && historyListener != null) {
            Log.d(TAG, "Removing old history listener")
            historyDatabase.removeEventListener(historyListener!!)
            historyListener = null
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        Log.d(TAG, "onDestroy called, cleaning listeners")
        removeChallengeListener()
        removeHistoryListener()
    }
}
