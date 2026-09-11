package com.rankwarz.edulabsrtm

import android.content.Intent
import android.content.Context
import android.os.Bundle
import android.text.format.DateFormat
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.android.material.navigation.NavigationView
import androidx.core.content.ContextCompat
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.database.DataSnapshot
import com.google.firebase.database.DatabaseError
import com.google.firebase.database.FirebaseDatabase
import com.google.firebase.database.ValueEventListener

data class RecentChallengeModel(
    val challengeId: String = "",
    val score: Int = 0,
    val mode: String = "",
    val result: String = "",
    val time: Long = 0,
    val totalQuestions: Int = 0,
    val correctAnswers: Int = 0,
    val xpGained: Int = 0,
    val isBotMatch: Boolean = false
)

class RecentChallengesActivity : AppCompatActivity() {

    private lateinit var listView: ListView
    private lateinit var bottomNav: BottomNavigationView
    private lateinit var navigationView: NavigationView
    private lateinit var filterTabLayout: LinearLayout

    private val allChallenges = ArrayList<RecentChallengeModel>()
    private val displayChallenges = ArrayList<RecentChallengeModel>()
    private var currentFilter = "ALL"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_recent_challenges)

        listView = findViewById(R.id.historyList)
        bottomNav = findViewById(R.id.bottomNavigation)
        navigationView = findViewById(R.id.navigationView)
        filterTabLayout = findViewById(R.id.filterTabLayout)

        setupBottomNavigation()
        setupDrawerNavigation()
        setupFilterTabs()
        loadHistory()
    }

    private fun setupFilterTabs() {
        filterTabLayout.removeAllViews()
        val tabs = listOf(
            "All" to "ALL",
            "Ranked Quiz Challenge" to "RANKED_QUIZ",
            "Other Challenges" to "OTHERS"
        )

        for ((label, filter) in tabs) {
            val btn = Button(this).apply {
                text = label
                setBackgroundResource(R.drawable.bg_filter_tab)
                layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
                setTextColor(ContextCompat.getColor(this@RecentChallengesActivity, if (filter == currentFilter) android.R.color.white else R.color.text_secondary))
                setOnClickListener {
                    currentFilter = filter
                    applyFilter()
                    updateTabHighlight()
                }
            }
            filterTabLayout.addView(btn)
        }
    }

    private fun updateTabHighlight() {
        for (i in 0 until filterTabLayout.childCount) {
            val btn = filterTabLayout.getChildAt(i) as Button
            val isSelected = when (currentFilter) {
                "ALL" -> btn.text == "All"
                "RANKED_QUIZ" -> btn.text == "Ranked Quiz Challenge"
                "OTHERS" -> btn.text == "Other Challenges"
                else -> false
            }
            btn.setTextColor(ContextCompat.getColor(this@RecentChallengesActivity, if (isSelected) android.R.color.white else R.color.text_secondary))
            btn.setBackgroundResource(if (isSelected) R.drawable.bg_filter_tab_selected else R.drawable.bg_filter_tab)
        }
    }

    private fun applyFilter() {
        displayChallenges.clear()
        when (currentFilter) {
            "ALL" -> displayChallenges.addAll(allChallenges)
            "RANKED_QUIZ" -> displayChallenges.addAll(allChallenges.filter { it.isBotMatch })
            "OTHERS" -> displayChallenges.addAll(allChallenges.filter { !it.isBotMatch })
        }
        updateListView()
    }

    private fun loadHistory() {
        val userId = getSharedPreferences("MY_APP", MODE_PRIVATE)
            .getInt("user_id", 0)
            .toString()

        val ref = FirebaseDatabase.getInstance()
            .getReference("user_challenges")
            .child(userId)

        ref.addListenerForSingleValueEvent(object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                allChallenges.clear()

                for (child in snapshot.children) {
                    val challengeId = child.key ?: ""

                    val score = when (val v = child.child("score").value) {
                        is Long -> v.toInt()
                        is Int -> v
                        is String -> v.toIntOrNull() ?: 0
                        else -> 0
                    }

                    val mode = child.child("mode").getValue(String::class.java) ?: "Unknown"
                    val result = child.child("result").getValue(String::class.java) ?: "completed"

                    val time = when (val v = child.child("time").value) {
                        is Long -> v
                        is Int -> v.toLong()
                        is String -> v.toLongOrNull() ?: 0L
                        else -> 0L
                    }

                    val totalQuestions = child.child("total_questions").getValue(Int::class.java) ?: 0
                    val correctAnswers = child.child("correct_answers").getValue(Int::class.java) ?: 0
                    val xpGained = child.child("xp_gained").getValue(Int::class.java) ?: 0
                    val isBotMatch = mode.equals("CLASSIC_BOT", ignoreCase = true) ||
                        mode.equals("BOT_MATCH", ignoreCase = true) ||
                        mode.equals("ARENA_PVP", ignoreCase = true)

                    val model = RecentChallengeModel(
                        challengeId = challengeId,
                        score = score,
                        mode = mode,
                        result = result,
                        time = time,
                        totalQuestions = totalQuestions,
                        correctAnswers = correctAnswers,
                        xpGained = xpGained,
                        isBotMatch = isBotMatch
                    )

                    allChallenges.add(model)
                }

                applyFilter()
            }

            override fun onCancelled(error: DatabaseError) {
                Toast.makeText(
                    this@RecentChallengesActivity,
                    "Failed to load history",
                    Toast.LENGTH_SHORT
                ).show()
            }
        })
    }

    private fun updateListView() {
        if (displayChallenges.isEmpty()) {
            listView.adapter = ArrayAdapter(
                this,
                android.R.layout.simple_list_item_1,
                listOf("No challenges found for this filter.")
            )
            return
        }

        listView.adapter = ChallengeListAdapter(this, displayChallenges) { model ->
            openChallengeReview(model)
        }
    }

    private fun openChallengeReview(model: RecentChallengeModel) {
        val intent = Intent(this, ChallengeResultActivity::class.java).apply {
            putExtra("CHALLENGE_ID", model.challengeId)
            putExtra("USER_ID", getSharedPreferences("MY_APP", MODE_PRIVATE).getInt("user_id", 0))
            putExtra("GAME_MODE", model.mode)
            putExtra("IS_BOT_MATCH", model.isBotMatch)
            putExtra("BOT_NAME", "Bot Opponent")
        }
        startActivity(intent)
    }

    private fun setupBottomNavigation() {
        setupAppBottomNavigation(bottomNav, R.id.nav_feed)
    }

    private fun setupDrawerNavigation() {
        navigationView.setNavigationItemSelectedListener { item ->
            when (item.itemId) {
                R.id.side_profile -> {
                    startActivity(Intent(this, ProfileActivity::class.java))
                    true
                }

                R.id.nav_logout -> {
                    FirebaseAuth.getInstance().signOut()
                    getSharedPreferences("MY_APP", MODE_PRIVATE)
                        .edit()
                        .clear()
                        .apply()

                    startActivity(
                        Intent(this, LoginActivity::class.java).apply {
                            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                        }
                    )
                    true
                }

                else -> false
            }
        }
    }
}

class ChallengeListAdapter(
    private val context: Context,
    private val challenges: List<RecentChallengeModel>,
    private val onClick: (RecentChallengeModel) -> Unit
) : BaseAdapter() {

    override fun getCount() = challenges.size

    override fun getItem(position: Int) = challenges[position]

    override fun getItemId(position: Int) = position.toLong()

    override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
        val view = convertView ?: LayoutInflater.from(context).inflate(R.layout.item_challenge_card, parent, false)
        val model = challenges[position]

        view.findViewById<TextView>(R.id.txtChallengeTitle).text = getChallengeTitle(model)
        view.findViewById<TextView>(R.id.txtChallengeMeta).text = "📅 ${DateFormat.format("dd MMM yyyy", model.time)}  |  ⏱ ${model.totalQuestions} Qs"
        view.findViewById<TextView>(R.id.txtScore).text = "Score: ${model.score}"
        view.findViewById<TextView>(R.id.txtXP).text = "⚡ +${model.xpGained} XP"
        view.findViewById<TextView>(R.id.txtCorrect).text = "✅ ${model.correctAnswers}/${model.totalQuestions}"

        val badge = view.findViewById<TextView>(R.id.txtBadge)
        if (model.isBotMatch) {
            badge.text = "🤖 Ranked Quiz"
            badge.setBackgroundResource(R.drawable.bg_ranked_quiz_badge)
        } else {
            badge.text = "⚔️ ${model.mode}"
            badge.setBackgroundResource(R.drawable.bg_challenge_badge)
        }

        view.setOnClickListener { onClick(model) }

        return view
    }

    private fun getChallengeTitle(model: RecentChallengeModel): String {
        return when {
            model.isBotMatch -> "Ranked Quiz Challenge"
            model.mode == "FRIENDS" -> "Friend Challenge"
            model.mode == "MATCHMAKING" -> "Matchmaking Battle"
            else -> "Challenge: ${model.mode}"
        }
    }
}