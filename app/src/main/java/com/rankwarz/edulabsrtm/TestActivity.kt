package com.rankwarz.edulabsrtm

import QuestionModel
import android.animation.ObjectAnimator
import android.content.Context
import android.content.Intent
import android.content.res.ColorStateList
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.os.CountDownTimer
import android.os.Handler
import android.os.Looper
import android.os.VibrationEffect
import android.os.Vibrator
import android.util.Log
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.animation.Animation
import android.view.animation.AnimationUtils
import android.view.animation.TranslateAnimation
import android.widget.*
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.android.volley.DefaultRetryPolicy
import com.android.volley.Request
import com.android.volley.toolbox.JsonObjectRequest
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import com.bumptech.glide.Glide
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.firebase.database.*
import org.json.JSONArray
import org.json.JSONObject
import java.util.ArrayList
import java.util.HashMap
import java.util.Random

class TestActivity : AppCompatActivity() {

    private val TAG = "CHALLENGE_DEBUG"

    private lateinit var challengeRootRef: DatabaseReference
    private lateinit var challengePlayersRef: DatabaseReference
    private lateinit var questionOrderRef: DatabaseReference

    private var healthListener: ValueEventListener? = null
    private var sharedQuestionListener: ValueEventListener? = null

    private var isGameOverHandled = false
    private var currentHp: Int = 100

    private lateinit var rootLayout: ViewGroup
    private lateinit var questionText: TextView
    private lateinit var timerText: TextView
    private lateinit var radioGroup: RadioGroup
    private lateinit var optionA: RadioButton
    private lateinit var optionB: RadioButton
    private lateinit var optionC: RadioButton
    private lateinit var optionD: RadioButton
    private lateinit var submitBtn: Button
    private lateinit var statusText: TextView
    private lateinit var questionImageView: ImageView
    private lateinit var finalSubmitBtn: Button
    private lateinit var explanationLayout: View
    private lateinit var explanationText: TextView
    private lateinit var challengeBattleHeader: LinearLayout

    private lateinit var btnAdrenaline: ImageButton
    private lateinit var btnShield: ImageButton
    private lateinit var btnShock: ImageButton
    private lateinit var btnConfuse: ImageButton
    private lateinit var tvAdrenalineCooldown: TextView
    private lateinit var tvShieldCooldown: TextView
    private lateinit var tvShockCooldown: TextView
    private lateinit var tvConfuseCooldown: TextView

    private val playerBars = HashMap<String, ProgressBar>()
    private val playerScoreLabels = HashMap<String, TextView>()
    private val playerRankLabels = HashMap<String, TextView>()
    private val playerNameLabels = HashMap<String, TextView>()
    private val playerAvatarViews = HashMap<String, ImageView>()
    private val playerImageCache = HashMap<String, String>()
    private val playerProfileCache = HashMap<String, PlayerProfileInfo>()
    private val playerScores = HashMap<String, Int>()

    private var userId = 0
    private var currentQuestion: QuestionModel? = null
    private var uniqueId = 0
    private var challengeId = 0
    private var isChallenge = false
    private var isHost = false
    private var myCurrentScore = 0

    private var canHeal = true
    private var canShield = true
    private var canShock = true
    private var canConfuse = true
    private var shieldRoundsActive = 0
    private var isShockCharged = false

    private var allQuestionIds = ArrayList<Int>()
    private var currentIndex = 0
    private var testTimer: CountDownTimer? = null

    private val IMAGE_BASE_URL = "https://medigyaan.xyz/Neurons/"
    private val BASE_URL = "https://medigyaan.xyz/Neurons/"
    private val requestQueue by lazy { Volley.newRequestQueue(this) }

    private val uiHandler = Handler(Looper.getMainLooper())
    private val reviewJson = JSONArray()

    private var iAmWaiting = false
    private var sharedQuestionLoaded = false
    private var isQuestionGenerationInProgress = false

    private data class PlayerProfileInfo(
        val photoUrl: String,
        val rankTitle: String,
        val level: Int,
        val name: String
    )

    private fun logStep(message: String) {
        Log.d(TAG, message)
    }

    private fun logError(message: String, tr: Throwable? = null) {
        if (tr != null) Log.e(TAG, message, tr) else Log.e(TAG, message)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        logStep("onCreate() started")
        setContentView(R.layout.activity_test_mode)
        logStep("Layout set: activity_test_mode")
        setupAppBottomNavigation(findViewById<BottomNavigationView>(R.id.bottomNavigation), R.id.nav_home)

        val prefs = getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
        userId = prefs.getInt("user_id", 0)

        uniqueId = intent.getIntExtra("UNIQUE_ID", 0)

        val challengeIdString = intent.getStringExtra("CHALLENGE_ID")
        val challengeIdInt = intent.getIntExtra("CHALLENGE_ID", 0)
        challengeId = when {
            !challengeIdString.isNullOrBlank() -> {
                challengeIdString.replace("lobby_", "").toIntOrNull() ?: challengeIdInt
            }
            challengeIdInt != 0 -> challengeIdInt
            else -> intent.getIntExtra("challenge_id", 0)
        }

        isChallenge = intent.getBooleanExtra("IS_CHALLENGE", false) ||
                intent.getBooleanExtra("is_host", false) ||
                intent.getBooleanExtra("IS_CREATOR", false) ||
                challengeId > 0

        isHost = intent.getBooleanExtra("IS_CREATOR", false) ||
                intent.getBooleanExtra("is_host", false)

        logStep(
            "Intent values -> userId=$userId, uniqueId=$uniqueId, challengeId=$challengeId, " +
                    "isChallenge=$isChallenge, isHost=$isHost"
        )

        bindViews()
        setupPowerButtons()
        setupButtons()

        if (isChallenge && challengeId > 0) {
            logStep("Challenge mode enabled. Setting up multiplayer Firebase.")
            setupMultiplayerFirebase()
            startTimer(15 * 60 * 1000)
            fetchOrCreateSharedQuestionList()
        } else {
            logStep("Non-challenge fallback enabled.")
            challengeBattleHeader.visibility = View.GONE
            findViewById<View>(R.id.powersContainer)?.visibility = View.GONE
            startTimer(30 * 60 * 1000)
            fetchQuestionListSinglePlayer()
        }
    }

    private fun bindViews() {
        logStep("Binding views...")
        rootLayout = findViewById(android.R.id.content)
        questionText = findViewById(R.id.questionText)
        timerText = findViewById(R.id.timerText)
        radioGroup = findViewById(R.id.radioGroup)
        optionA = findViewById(R.id.optionA)
        optionB = findViewById(R.id.optionB)
        optionC = findViewById(R.id.optionC)
        optionD = findViewById(R.id.optionD)
        submitBtn = findViewById(R.id.submitBtn)
        statusText = findViewById(R.id.statusText)
        questionImageView = findViewById(R.id.questionImageView)
        explanationLayout = findViewById(R.id.explanationLayout)
        explanationText = findViewById(R.id.explanationText)
        challengeBattleHeader = findViewById(R.id.challengeBattleHeader)
        finalSubmitBtn = findViewById(R.id.finalSubmitBtn)

        btnAdrenaline = findViewById(R.id.btnAdrenaline)
        btnShield = findViewById(R.id.btnShield)
        btnShock = findViewById(R.id.btnShock)
        btnConfuse = findViewById(R.id.btnConfuse)
        tvAdrenalineCooldown = findViewById(R.id.tvAdrenalineCooldown)
        tvShieldCooldown = findViewById(R.id.tvShieldCooldown)
        tvShockCooldown = findViewById(R.id.tvShockCooldown)
        tvConfuseCooldown = findViewById(R.id.tvConfuseCooldown)

        logStep("Views bound successfully")
    }

    private fun setupPowerButtons() {
        logStep("Setting up power buttons...")

        btnAdrenaline.setOnClickListener {
            logStep("Adrenaline clicked by userId=$userId")

            if (!canHeal) {
                logStep("Adrenaline blocked: already used")
                return@setOnClickListener
            }

            if (!::challengePlayersRef.isInitialized) {
                logStep("Adrenaline blocked: challengePlayersRef not initialized")
                return@setOnClickListener
            }

            val newHp = (currentHp + 15).coerceAtMost(100)
            logStep("Updating HP via adrenaline: $currentHp -> $newHp")
            challengePlayersRef.child(userId.toString()).child("hp").setValue(newHp)
                .addOnSuccessListener { logStep("Adrenaline HP write success") }
                .addOnFailureListener { e -> logError("Adrenaline HP write failed", e) }

            canHeal = false
            playPowerPop(btnAdrenaline)
            btnAdrenaline.alpha = 0.3f
            tvAdrenalineCooldown.visibility = View.VISIBLE
            tvAdrenalineCooldown.text = "USED"
            showFloatingText("+15 HP", Color.GREEN)
        }

        btnShield.setOnClickListener {
            logStep("Shield clicked by userId=$userId")

            if (!canShield) {
                logStep("Shield blocked: already used")
                return@setOnClickListener
            }

            shieldRoundsActive = 2
            canShield = false
            playPowerPop(btnShield)
            btnShield.alpha = 0.3f
            tvShieldCooldown.visibility = View.VISIBLE
            tvShieldCooldown.text = "ACTIVE: 2"
            showFloatingText("SHIELD UP", Color.CYAN)
            logStep("Shield activated for 2 rounds")
        }

        btnShock.setOnClickListener {
            logStep("Shock clicked by userId=$userId")

            if (!canShock) {
                logStep("Shock blocked: already used")
                return@setOnClickListener
            }

            isShockCharged = true
            canShock = false
            playPowerPop(btnShock)
            btnShock.alpha = 0.3f
            tvShockCooldown.visibility = View.VISIBLE
            tvShockCooldown.text = "CHARGED"
            showFloatingText("SHOCK CHARGED", Color.YELLOW)
            logStep("Shock charged")
        }

        btnConfuse.setOnClickListener {
            logStep("Confuse clicked by userId=$userId")

            if (!canConfuse) {
                logStep("Confuse blocked: already used")
                return@setOnClickListener
            }

            if (!::challengePlayersRef.isInitialized) {
                logStep("Confuse blocked: challengePlayersRef not initialized")
                return@setOnClickListener
            }

            val myUid = userId.toString()
            val targetId = playerBars.keys.filter { it != myUid }.randomOrNull()
            canConfuse = false
            playPowerPop(btnConfuse)
            btnConfuse.alpha = 0.3f
            tvConfuseCooldown.visibility = View.VISIBLE
            tvConfuseCooldown.text = "USED"

            if (targetId == null) {
                showFloatingText("No target", Color.GRAY)
                logStep("Confuse skipped: no opponent")
                return@setOnClickListener
            }

            damagePlayer(targetId, 4)
            showFloatingText("CONFUSE HIT", Color.MAGENTA)
            logStep("Confuse applied to opponent=$targetId")
        }
    }

    private fun setupMultiplayerFirebase() {
        logStep("Initializing Firebase challenge references...")

        val challengeRef = FirebaseDatabase.getInstance()
            .getReference("challenges")
            .child(challengeId.toString())

        challengeRootRef = challengeRef
        challengePlayersRef = challengeRef.child("players")
        questionOrderRef = challengeRef.child("question_ids")

        logStep("Firebase refs ready -> root=${challengeRef.path}, players=${challengePlayersRef.path}, question_ids=${questionOrderRef.path}")

        healthListener = object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                logStep("players snapshot received. children=${snapshot.childrenCount}")

                var survivors = 0
                var lastManId = ""

                for (playerSnap in snapshot.children) {
                    val pId = playerSnap.key ?: continue
                    val hp = playerSnap.child("hp").getValue(Int::class.java) ?: 100
                    val score = playerSnap.child("score").getValue(Int::class.java) ?: 0
                    val name = playerSnap.child("name").getValue(String::class.java) ?: "Player $pId"

                    playerScores[pId] = score
                    if (hp > 0) {
                        survivors++
                        lastManId = pId
                    }

                    if (pId == userId.toString() && hp <= 0 && !isGameOverHandled) {
                        logStep("Local player hp <= 0, triggering defeat")
                        showResult(false)
                    }

                    fetchPlayerProfile(pId, name) { profile ->
                        updatePlayerHealthUI(pId, hp, score, profile)
                    }
                }

                logStep("Survivors count=$survivors, lastManId=$lastManId")

                if (survivors == 1 && playerBars.size > 1 && !isGameOverHandled) {
                    logStep("Only one survivor left. Determining winner...")
                    showResult(lastManId == userId.toString())
                }
            }

            override fun onCancelled(error: DatabaseError) {
                logError("players listener cancelled: ${error.message}")
            }
        }

        challengePlayersRef.addValueEventListener(healthListener!!)
        logStep("players listener attached")
    }

    private fun fetchPlayerProfile(userId: String, fallbackName: String, callback: (PlayerProfileInfo) -> Unit) {
        logStep("fetchPlayerProfile called for userId=$userId")

        playerProfileCache[userId]?.let {
            logStep("Profile cache hit for userId=$userId")
            callback(it)
            return
        }

        val url = "${BASE_URL}get_profilev1.php?user_id=$userId&viewer_id=${this.userId}"
        logStep("Fetching player profile from API: $url")

        val request = StringRequest(
            Request.Method.GET,
            url,
            { response ->
                try {
                    logStep("Player profile API response received for userId=$userId")

                    val root = JSONObject(response)
                    val data = root.optJSONObject("data") ?: root

                    val rawPhoto = data.optString("photo", "").trim()
                    val rankTitle = data.optString("rank_title", "").trim()
                    val level = data.optInt("level", 0)
                    val apiName = data.optString("name", fallbackName).ifBlank { fallbackName }

                    val finalPhotoUrl = buildPhotoUrl(rawPhoto)

                    val profile = PlayerProfileInfo(
                        photoUrl = finalPhotoUrl,
                        rankTitle = if (rankTitle.isBlank()) "Unranked" else rankTitle,
                        level = level,
                        name = apiName
                    )

                    playerProfileCache[userId] = profile
                    logStep("Profile resolved for userId=$userId -> photo=${profile.photoUrl}, rank=${profile.rankTitle}, level=${profile.level}")
                    callback(profile)
                } catch (e: Exception) {
                    logError("Player profile parse error for userId=$userId", e)
                    val fallback = PlayerProfileInfo(
                        photoUrl = "",
                        rankTitle = "Unranked",
                        level = 0,
                        name = fallbackName
                    )
                    callback(fallback)
                }
            },
            { error ->
                logError("Player profile API error for userId=$userId: ${error.message}")
                val fallback = PlayerProfileInfo(
                    photoUrl = "",
                    rankTitle = "Unranked",
                    level = 0,
                    name = fallbackName
                )
                callback(fallback)
            }
        )

        requestQueue.add(request)
    }

    private fun buildPhotoUrl(rawPhoto: String): String {
        val cleaned = rawPhoto
            .replace("./", "")
            .replace("\\", "/")
            .replace("//", "/")
            .trim()

        if (cleaned.isBlank() || cleaned.equals("null", ignoreCase = true)) {
            return ""
        }

        return if (cleaned.startsWith("http://") || cleaned.startsWith("https://")) {
            cleaned
        } else {
            IMAGE_BASE_URL.trimEnd('/') + "/" + cleaned.trimStart('/')
        }
    }

    private fun updatePlayerHealthUI(pId: String, hp: Int, score: Int, profile: PlayerProfileInfo) {
        val isMe = pId == userId.toString()
        if (isMe) currentHp = hp

        logStep(
            "updatePlayerHealthUI -> pid=$pId, isMe=$isMe, hp=$hp, score=$score, " +
                    "rank=${profile.rankTitle}, level=${profile.level}, photo=${profile.photoUrl}"
        )

        if (!playerBars.containsKey(pId)) {
            logStep("Creating UI row for player=$pId")

            val row = LinearLayout(this).apply {
                tag = pId
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                layoutParams = LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT
                ).apply { setMargins(0, 15, 0, 15) }
            }

            val sizeInPx = (45 * resources.displayMetrics.density).toInt()

            val avatar = ImageView(this).apply {
                id = View.generateViewId()
                layoutParams = LinearLayout.LayoutParams(sizeInPx, sizeInPx)
                scaleType = ImageView.ScaleType.CENTER_CROP
            }

            val infoLayout = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.2f)
                setPadding(30, 0, 10, 0)
            }

            val nameLabel = TextView(this).apply {
                text = if (isMe) "YOU" else profile.name
                textSize = 14f
                setTextColor(Color.BLACK)
                setTypeface(null, android.graphics.Typeface.BOLD)
            }

            val rankLabel = TextView(this).apply {
                text = "Rank: ${profile.rankTitle} • Lv ${profile.level}"
                textSize = 12f
                setTextColor(Color.DKGRAY)
            }

            val scoreLabel = TextView(this).apply {
                text = "Score: $score"
                textSize = 12f
                setTextColor(Color.DKGRAY)
            }

            infoLayout.addView(nameLabel)
            infoLayout.addView(rankLabel)
            infoLayout.addView(scoreLabel)

            val bar = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
                layoutParams = LinearLayout.LayoutParams(0, 35, 2.5f)
                max = 100
                progress = hp
                progressTintList = ColorStateList.valueOf(
                    if (isMe) Color.parseColor("#4CAF50") else Color.parseColor("#F44336")
                )
            }

            row.addView(avatar)
            row.addView(infoLayout)
            row.addView(bar)

            challengeBattleHeader.addView(row)
            playerBars[pId] = bar
            playerScoreLabels[pId] = scoreLabel
            playerRankLabels[pId] = rankLabel
            playerNameLabels[pId] = nameLabel
            playerAvatarViews[pId] = avatar

            loadPlayerAvatar(avatar, profile, pId, profile.name)
        } else {
            logStep("Updating existing UI row for player=$pId")

            val bar = playerBars[pId] ?: return
            playerScoreLabels[pId]?.text = "Score: $score"
            playerRankLabels[pId]?.text = "Rank: ${profile.rankTitle} • Lv ${profile.level}"
            playerNameLabels[pId]?.text = if (isMe) "YOU" else profile.name

            if (hp < bar.progress) {
                logStep("Damage detected for player=$pId (${bar.progress} -> $hp)")
                triggerDamageVisuals(bar, isMe)
            }

            ObjectAnimator.ofInt(bar, "progress", bar.progress, hp)
                .setDuration(400)
                .start()

            playerAvatarViews[pId]?.let { avatar ->
                loadPlayerAvatar(avatar, profile, pId, profile.name)
            }
        }
    }

    private fun loadPlayerAvatar(imageView: ImageView, profile: PlayerProfileInfo, userId: String, fallbackName: String) {
        val finalUrl = if (profile.photoUrl.isNotBlank()) {
            profile.photoUrl
        } else {
            "https://api.dicebear.com/7.x/pixel-art/png?seed=${fallbackName.replace(" ", "_")}"
        }

        logStep("Loading avatar for player=$userId -> $finalUrl")

        Glide.with(this)
            .load(finalUrl)
            .placeholder(android.R.drawable.ic_menu_gallery)
            .error(android.R.drawable.ic_menu_report_image)
            .circleCrop()
            .into(imageView)
    }

    private fun handleScoringAndDamage(isCorrect: Boolean) {
        logStep("handleScoringAndDamage -> isCorrect=$isCorrect, isChallenge=$isChallenge")

        if (!isChallenge) return
        val myUid = userId.toString()

        if (isCorrect) {
            logStep("Correct answer: incrementing score for user=$myUid")

            challengePlayersRef.child(myUid).child("score").runTransaction(object : Transaction.Handler {
                override fun doTransaction(data: MutableData): Transaction.Result {
                    val current = data.getValue(Int::class.java) ?: 0
                    val updated = current + 4
                    data.value = updated
                    logStep("Score transaction -> $current -> $updated")
                    return Transaction.success(data)
                }

                override fun onComplete(e: DatabaseError?, b: Boolean, s: DataSnapshot?) {
                    if (e != null) logError("Score transaction failed: ${e.message}")
                    else logStep("Score transaction complete for user=$myUid")
                }
            })

            val dmg = if (isShockCharged) {
                logStep("Shock effect active: using 10 damage")
                isShockCharged = false
                tvShockCooldown.text = "USED"
                10
            } else {
                5
            }

            for (pid in playerBars.keys) {
                if (pid != myUid) {
                    logStep("Dealing $dmg damage to opponent=$pid")
                    damagePlayer(pid, dmg)
                }
            }
        } else {
            logStep("Incorrect answer: damaging self by 3")
            damagePlayer(myUid, 3)
        }
    }

    private fun damagePlayer(pid: String, dmg: Int) {
        logStep("damagePlayer -> pid=$pid, dmg=$dmg, shieldRoundsActive=$shieldRoundsActive")

        if (pid == userId.toString() && shieldRoundsActive > 0) {
            shieldRoundsActive--
            logStep("Shield absorbed damage for self. Remaining shield rounds=$shieldRoundsActive")
            tvShieldCooldown.text = if (shieldRoundsActive > 0) "ACTIVE: $shieldRoundsActive" else "USED"
            return
        }

        challengePlayersRef.child(pid).child("hp").runTransaction(object : Transaction.Handler {
            override fun doTransaction(data: MutableData): Transaction.Result {
                val hp = data.getValue(Int::class.java) ?: 100
                val updated = (hp - dmg).coerceAtLeast(0)
                data.value = updated
                logStep("HP transaction -> pid=$pid, $hp -> $updated")
                return Transaction.success(data)
            }

            override fun onComplete(e: DatabaseError?, b: Boolean, s: DataSnapshot?) {
                if (e != null) logError("HP transaction failed for pid=$pid: ${e.message}")
                else logStep("HP transaction complete for pid=$pid")
            }
        })
    }

    private fun displayQuestion(q: QuestionModel) {
        logStep("displayQuestion -> qId=${q.id}")

        val fullText = q.question.trim()

        val splitRegex = Regex("""(?i)\s*[\(\[]?a[\)\].]""")
        val cleanQuestion = fullText.split(splitRegex)[0].trim()
        questionText.text = cleanQuestion
        logStep("Question text displayed: $cleanQuestion")

        if (q.a.isNullOrBlank() || q.a == "null") {
            logStep("Options missing in model fields. Attempting parse from question text.")

            val extractRegex = Regex(
                """(?is)a[\)\].]\s*(.*?)\s*b[\)\].]\s*(.*?)\s*c[\)\].]\s*(.*?)\s*d[\)\].]\s*(.*)"""
            )
            val match = extractRegex.find(fullText)

            if (match != null) {
                optionA.text = match.groupValues[1].trim()
                optionB.text = match.groupValues[2].trim()
                optionC.text = match.groupValues[3].trim()
                optionD.text = match.groupValues[4].trim()
                logStep("Parsed options from question text successfully")
            } else {
                optionA.text = q.a ?: ""
                optionB.text = q.b ?: ""
                optionC.text = q.c ?: ""
                optionD.text = q.d ?: ""
                logStep("Fallback option values used from model")
            }
        } else {
            optionA.text = q.a
            optionB.text = q.b
            optionC.text = q.c
            optionD.text = q.d
            logStep("Options loaded directly from model")
        }

        val imagePath = q.imageUrl?.trim()
        if (!imagePath.isNullOrEmpty() && imagePath != "null") {
            val imgUrl = if (imagePath.startsWith("http")) imagePath else IMAGE_BASE_URL + imagePath
            questionImageView.visibility = View.VISIBLE
            Glide.with(this).load(imgUrl.replace(" ", "%20")).into(questionImageView)
            logStep("Question image loaded -> $imgUrl")
        } else {
            questionImageView.visibility = View.GONE
            logStep("No question image found")
        }

        radioGroup.clearCheck()
        explanationLayout.visibility = View.GONE
        submitBtn.isEnabled = true
        submitBtn.text = "Submit"
        logStep("Question ready for answer")
    }

    private fun setupButtons() {

        logStep("Setting up submit button...")

        submitBtn.setOnClickListener {

            logStep("Submit clicked")

            val selectedId = radioGroup.checkedRadioButtonId

            if (selectedId == -1) {

                logStep("Submit blocked: no option selected")

                Toast.makeText(
                    this,
                    "Please select an answer",
                    Toast.LENGTH_SHORT
                ).show()

                return@setOnClickListener
            }

            val ans = when (selectedId) {

                R.id.optionA -> "A"
                R.id.optionB -> "B"
                R.id.optionC -> "C"

                else -> "D"
            }

            val question = currentQuestion

            if (question == null) {

                logError("Current question is null")

                Toast.makeText(
                    this,
                    "Question not loaded",
                    Toast.LENGTH_SHORT
                ).show()

                return@setOnClickListener
            }

            val correct = question.correctAnswer ?: ""
            val isCorrect = ans.equals(correct, true)

            logStep(
                "Answer selected -> " +
                        "ans=$ans, " +
                        "correct=$correct, " +
                        "isCorrect=$isCorrect"
            )

            try {

                val qObj = JSONObject().apply {

                    // IDs
                    put(
                        "question_id",
                        question.id
                    )

                    // Question
                    put(
                        "question",
                        question.question ?: ""
                    )

                    put(
                        "question_text",
                        question.question ?: ""
                    )

                    // Options
                    put(
                        "option_a",
                        question.a ?: ""
                    )

                    put(
                        "option_b",
                        question.b ?: ""
                    )

                    put(
                        "option_c",
                        question.c ?: ""
                    )

                    put(
                        "option_d",
                        question.d ?: ""
                    )

                    // Image
                    put(
                        "question_image",
                        question.imageUrl ?: ""
                    )

                    put(
                        "image_url",
                        question.imageUrl ?: ""
                    )

                    // User answer
                    put(
                        "selected_option",
                        ans
                    )

                    put(
                        "user_answer",
                        ans
                    )

                    put(
                        "your_answer",
                        ans
                    )

                    // Correct answer
                    put(
                        "correct_option",
                        correct
                    )

                    put(
                        "correct_answer",
                        correct
                    )

                    // Explanation
                    put(
                        "explanation",
                        question.explanation ?: ""
                    )

                    // Result
                    put(
                        "is_correct",
                        if (isCorrect) 1 else 0
                    )
                }

                reviewJson.put(qObj)

                logStep(
                    "Review JSON appended successfully. " +
                            "Total=${reviewJson.length()}"
                )

                logStep("Review Object -> $qObj")

            } catch (e: Exception) {

                logError(
                    "Error building review JSON",
                    e
                )
            }

            showInstantFeedback(
                isCorrect,
                question.explanation ?: "No explanation available."
            )

            submitBtn.isEnabled = false

            logStep("Submit disabled to prevent double taps")

            handleScoringAndDamage(isCorrect)

            syncWithServer(ans)
        }
    }

    private fun showInstantFeedback(isCorrect: Boolean, explanation: String) {
        logStep("showInstantFeedback -> isCorrect=$isCorrect")

        explanationLayout.visibility = View.VISIBLE
        explanationText.text = aiMarkdownSpannable(if (isCorrect) "CORRECT!\n$explanation" else "INCORRECT!\n$explanation")
        explanationText.setTextColor(if (isCorrect) Color.GREEN else Color.RED)

        uiHandler.postDelayed({
            logStep("Feedback delay finished, moving next question")
            moveNext()
        }, 2500)
    }

    private fun moveNext() {
        currentIndex++
        logStep("moveNext -> currentIndex=$currentIndex, total=${allQuestionIds.size}")

        if (currentIndex < allQuestionIds.size) {
            val nextId = allQuestionIds[currentIndex]
            logStep("Loading next questionId=$nextId")
            loadQuestion(nextId)
        } else {
            logStep("All questions completed locally")

            iAmWaiting = true

            if (::challengePlayersRef.isInitialized) {
                challengePlayersRef.child(userId.toString()).child("isFinished")
                    .setValue(true)
                    .addOnSuccessListener { logStep("Marked self as finished in Firebase") }
                    .addOnFailureListener { e -> logError("Failed to mark self as finished", e) }

                submitBtn.isEnabled = false
                submitBtn.text = "Waiting for others..."
                questionText.text = "Battle finished! Waiting for other doctors to complete their rounds..."
                radioGroup.visibility = View.GONE
                explanationLayout.visibility = View.GONE
                questionImageView.visibility = View.GONE

                logStep("Entering waiting state")
                checkIfEveryoneIsDone()
            } else {
                logStep("challengePlayersRef not initialized, finalizing immediately")
                finalizeChallenge()
            }
        }
    }

    private fun checkIfEveryoneIsDone() {
        if (!iAmWaiting) {
            logStep("checkIfEveryoneIsDone aborted: not waiting")
            return
        }

        logStep("Checking whether all competitors are done...")

        challengePlayersRef.addListenerForSingleValueEvent(object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                var allCompetitorsFinished = true

                for (playerSnap in snapshot.children) {
                    val hp = playerSnap.child("hp").getValue(Int::class.java) ?: 100
                    val finished = playerSnap.child("isFinished").getValue(Boolean::class.java) ?: false
                    val pid = playerSnap.key ?: "unknown"

                    logStep("Waiting check -> pid=$pid, hp=$hp, finished=$finished")

                    if (hp > 0 && !finished) {
                        allCompetitorsFinished = false
                        break
                    }
                }

                if (allCompetitorsFinished) {
                    logStep("All competitors finished. Determining winner...")
                    determineWinnerByPoints()
                } else {
                    logStep("Not all competitors finished yet. Rechecking in 2 seconds.")
                    uiHandler.postDelayed({ checkIfEveryoneIsDone() }, 2000)
                }
            }

            override fun onCancelled(error: DatabaseError) {
                logError("checkIfEveryoneIsDone cancelled: ${error.message}")
            }
        })
    }

    private fun determineWinnerByPoints() {
        if (isGameOverHandled) {
            logStep("determineWinnerByPoints ignored: game already handled")
            return
        }

        val myUid = userId.toString()
        var winnerId = ""
        var bestPower = -1

        logStep("Calculating winner by (score * 10) + hp")

        for (pid in playerBars.keys) {
            val hp = playerBars[pid]?.progress ?: 0
            val score = playerScores[pid] ?: 0
            val power = (score * 10) + hp

            logStep("Power calc -> pid=$pid, score=$score, hp=$hp, power=$power")

            if (power > bestPower) {
                bestPower = power
                winnerId = pid
            }
        }

        logStep("Winner calculation complete -> winnerId=$winnerId, bestPower=$bestPower, myUid=$myUid")

        if (winnerId.isBlank()) {
            logStep("Winner blank, showing fallback defeat")
            showResult(false)
        } else {
            showResult(winnerId == myUid)
        }
    }

    private fun fetchOrCreateSharedQuestionList() {
        logStep("fetchOrCreateSharedQuestionList started")

        questionOrderRef.addListenerForSingleValueEvent(object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                logStep("question_ids snapshot received. children=${snapshot.childrenCount}")

                val existingIds = ArrayList<Int>()

                for (child in snapshot.children) {
                    val id = when (val v = child.value) {
                        is Long -> v.toInt()
                        is Int -> v
                        is String -> v.toIntOrNull() ?: -1
                        else -> -1
                    }

                    logStep("question_ids child -> key=${child.key}, value=${child.value}, parsed=$id")

                    if (id > 0) existingIds.add(id)
                }

                if (existingIds.isNotEmpty()) {
                    logStep("Existing shared question list found. Count=${existingIds.size}")
                    allQuestionIds.clear()
                    allQuestionIds.addAll(existingIds)
                    currentIndex = 0
                    sharedQuestionLoaded = true

                    logStep("Shared question order loaded -> $allQuestionIds")

                    if (allQuestionIds.isNotEmpty()) {
                        loadQuestion(allQuestionIds[currentIndex])
                    } else {
                        Toast.makeText(this@TestActivity, "No questions available", Toast.LENGTH_SHORT).show()
                        logStep("No questions available after loading shared list")
                    }
                } else {
                    logStep("No shared question list found. Creating new list...")
                    createSharedQuestionListInFirebase()
                }
            }

            override fun onCancelled(error: DatabaseError) {
                logError("question_ids read cancelled: ${error.message}")
            }
        })
    }

    private fun createSharedQuestionListInFirebase() {
        if (isQuestionGenerationInProgress) {
            logStep("Question generation already in progress, skipping")
            return
        }

        if (!isHost) {
            logStep("Not host → waiting for shared question list in Firebase")
            listenToSharedQuestionList()
            return
        }

        isQuestionGenerationInProgress = true

        val safeUniqueId = normalizeUniqueId(uniqueId)
        val url = "${BASE_URL}api/get_test_structure.php?unique_id=$safeUniqueId"
        logStep("Creating shared question list from API: $url (raw=$uniqueId safe=$safeUniqueId)")

        val req = StringRequest(
            Request.Method.GET,
            url,
            { response ->
                try {
                    logStep("Test structure response received")
                    logStep("RAW STRUCTURE RESPONSE -> $response")

                    val json = JSONObject(response)
                    val arr = json.optJSONArray("question_ids")

                    if (arr == null || arr.length() == 0) {
                        logStep("API returned empty question_ids")
                        Toast.makeText(this, "No questions found", Toast.LENGTH_SHORT).show()
                        isQuestionGenerationInProgress = false
                        return@StringRequest
                    }

                    val tempIds = ArrayList<Int>()
                    for (i in 0 until arr.length()) {
                        val q = arr.optInt(i, -1)
                        if (q != -1) tempIds.add(q)
                    }

                    if (tempIds.isEmpty()) {
                        logStep("No valid question IDs parsed")
                        Toast.makeText(this, "Invalid question data", Toast.LENGTH_SHORT).show()
                        isQuestionGenerationInProgress = false
                        return@StringRequest
                    }

                    logStep("Fetched question_ids -> $tempIds")

                    tempIds.shuffle(Random(challengeId.toLong()))
                    val finalIds = tempIds.take(15)

                    logStep("Final shared question_ids -> $finalIds")
                    logStep("Writing shared question_ids to Firebase...")

                    questionOrderRef.setValue(finalIds)
                        .addOnSuccessListener {
                            logStep("Shared question_ids saved successfully to Firebase")
                            isQuestionGenerationInProgress = false
                            sharedQuestionLoaded = true

                            allQuestionIds.clear()
                            allQuestionIds.addAll(finalIds)
                            currentIndex = 0

                            if (allQuestionIds.isNotEmpty()) {
                                loadQuestion(allQuestionIds[0])
                            } else {
                                Toast.makeText(this, "No questions available", Toast.LENGTH_SHORT).show()
                            }
                        }
                        .addOnFailureListener { e ->
                            isQuestionGenerationInProgress = false
                            logError("Firebase write failed", e)
                            Toast.makeText(this, "Sync failed", Toast.LENGTH_SHORT).show()
                        }
                } catch (e: Exception) {
                    isQuestionGenerationInProgress = false
                    logError("Parsing error", e)
                    Toast.makeText(this, "Data error", Toast.LENGTH_SHORT).show()
                }
            },
            { error ->
                isQuestionGenerationInProgress = false
                logError("Network error: ${error.message}", error)
                Toast.makeText(this, "Network error", Toast.LENGTH_SHORT).show()
            }
        )

        req.retryPolicy = DefaultRetryPolicy(10000, 1, 1f)
        requestQueue.add(req)

        logStep("Shared question list request queued")
    }

    private fun listenToSharedQuestionList() {
        if (sharedQuestionListener != null) return

        logStep("Listening for shared question list from host...")

        sharedQuestionListener = object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                val list = ArrayList<Int>()

                for (child in snapshot.children) {
                    val id = when (val v = child.value) {
                        is Long -> v.toInt()
                        is Int -> v
                        is String -> v.toIntOrNull() ?: -1
                        else -> -1
                    }
                    if (id > 0) list.add(id)
                }

                logStep("listenToSharedQuestionList -> received=$list")

                if (list.isNotEmpty() && !sharedQuestionLoaded) {
                    sharedQuestionLoaded = true
                    allQuestionIds.clear()
                    allQuestionIds.addAll(list)
                    currentIndex = 0
                    logStep("Shared questions loaded from Firebase -> $allQuestionIds")
                    loadQuestion(allQuestionIds[0])

                    questionOrderRef.removeEventListener(sharedQuestionListener!!)
                    sharedQuestionListener = null
                }
            }

            override fun onCancelled(error: DatabaseError) {
                logError("listenToSharedQuestionList cancelled: ${error.message}")
            }
        }

        questionOrderRef.addValueEventListener(sharedQuestionListener!!)
    }

    private fun normalizeUniqueId(id: Int): Int {
        val safe = ((id % 50) + 50) % 50
        return if (safe == 0) 1 else safe
    }

    private fun fetchQuestionListSinglePlayer() {
        val safeUniqueId = normalizeUniqueId(uniqueId)
        val url = "${BASE_URL}api/get_test_structure.php?unique_id=$safeUniqueId"
        logStep("Fetching single-player question list: $url")

        val req = StringRequest(Request.Method.GET, url, { response ->
            try {
                logStep("Single-player raw response -> $response")

                val arr = JSONObject(response).optJSONArray("question_ids")
                if (arr != null) {
                    val tempIds = ArrayList<Int>()
                    for (i in 0 until arr.length()) {
                        tempIds.add(arr.getInt(i))
                    }

                    allQuestionIds.clear()
                    allQuestionIds.addAll(tempIds.take(15))

                    logStep("Single-player question_ids loaded -> $allQuestionIds")

                    if (allQuestionIds.isNotEmpty()) {
                        loadQuestion(allQuestionIds[currentIndex])
                    } else {
                        Toast.makeText(this, "No questions available", Toast.LENGTH_SHORT).show()
                        logStep("No single-player questions available")
                    }
                } else {
                    logStep("Single-player API response missing question_ids")
                }
            } catch (e: Exception) {
                logError("fetchQuestionListSinglePlayer parse error", e)
            }
        }, { error ->
            logError("fetchQuestionListSinglePlayer network error: ${error.message}", error)
        })

        req.retryPolicy = DefaultRetryPolicy(10000, 0, 1f)
        requestQueue.add(req)
        logStep("Single-player question list request queued")
    }

    private fun loadQuestion(qId: Int) {
        val url = "${BASE_URL}api/get_single_question.php?question_id=$qId"
        logStep("Loading questionId=$qId from: $url")

        val req = JsonObjectRequest(Request.Method.GET, url, null, { res ->
            try {
                val data = res.getJSONObject("data")
                currentQuestion = QuestionModel(
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

                logStep("Question loaded successfully -> id=$qId")
                currentQuestion?.let { displayQuestion(it) }
            } catch (e: Exception) {
                logError("loadQuestion parse error for qId=$qId", e)
            }
        }, { error ->
            logError("loadQuestion network error for qId=$qId: ${error.message}", error)
        })

        requestQueue.add(req)
        logStep("Question request queued for qId=$qId")
    }

    private fun syncWithServer(ans: String) {
        if (currentIndex !in allQuestionIds.indices) {
            logStep("syncWithServer aborted: currentIndex out of bounds -> $currentIndex")
            return
        }

        val qId = allQuestionIds[currentIndex]
        val url = "${BASE_URL}sync_challenge_v16_authenticated.php"

        logStep("Syncing answer -> challengeId=$challengeId, userId=$userId, questionId=$qId, answer=$ans")

        val req = object : StringRequest(Request.Method.POST, url, { response ->
            logStep("Server synced successfully for questionId=$qId -> $response")
        }, { error ->
            logError("syncWithServer error for questionId=$qId: ${error.message}", error)
        }) {
            override fun getParams(): MutableMap<String, String> {
                return hashMapOf(
                    "challenge_id" to challengeId.toString(),
                    "user_id" to userId.toString(),
                    "question_id" to qId.toString(),
                    "answer" to ans
                )
            }
        }

        req.retryPolicy = DefaultRetryPolicy(8000, 0, 1f)
        requestQueue.add(req)
        logStep("Sync request queued for questionId=$qId")
    }

    private fun startTimer(ms: Long) {
        logStep("startTimer -> ${ms}ms")

        testTimer?.cancel()
        testTimer = object : CountDownTimer(ms, 1000) {
            override fun onTick(millisUntilFinished: Long) {
                val mins = millisUntilFinished / 60000
                val secs = (millisUntilFinished / 1000) % 60
                timerText.text = String.format("%02d:%02d", mins, secs)

                if (millisUntilFinished < 30000) {
                    timerText.setTextColor(Color.RED)
                }

                if (millisUntilFinished % 10000L == 0L) {
                    logStep("Timer tick -> ${String.format("%02d:%02d", mins, secs)} remaining")
                }
            }

            override fun onFinish() {
                timerText.text = "00:00"
                logStep("Timer finished")
                finalizeChallenge()
            }
        }.start()
    }

    /** press_pop + wiggle combo for battle power-up buttons. */
    private fun playPowerPop(button: ImageButton) {
        button.clearAnimation()
        button.startAnimation(AnimationUtils.loadAnimation(this, R.anim.power_pop))
    }

    private fun showFloatingText(text: String, color: Int) {
        logStep("showFloatingText -> $text")

        val tv = TextView(this).apply {
            this.text = text
            setTextColor(color)
            textSize = 22f
            setTypeface(null, android.graphics.Typeface.BOLD)
            setShadowLayer(8f, 0f, 0f, Color.BLACK)
        }

        val params = FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.WRAP_CONTENT,
            FrameLayout.LayoutParams.WRAP_CONTENT
        ).apply { gravity = Gravity.CENTER }

        rootLayout.addView(tv, params)

        tv.animate()
            .translationY(-300f)
            .alpha(0f)
            .setDuration(1200)
            .withEndAction {
                rootLayout.removeView(tv)
                logStep("Floating text removed -> $text")
            }
            .start()
    }

    private var lastVibrationTime = 0L

    private fun triggerDamageVisuals(bar: ProgressBar, isMe: Boolean) {
        logStep("triggerDamageVisuals -> isMe=$isMe, barProgress=${bar.progress}")

        // Prevent animation stacking
        bar.clearAnimation()

        val shake = TranslateAnimation(-12f, 12f, 0f, 0f).apply {
            duration = 40
            repeatCount = 4
            repeatMode = Animation.REVERSE
        }
        bar.startAnimation(shake)

        if (isMe) {

            // 🔊 VIBRATION (throttled)
            val now = System.currentTimeMillis()
            if (now - lastVibrationTime > 150) {
                val v = getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
                v?.let {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        it.vibrate(
                            VibrationEffect.createOneShot(80, VibrationEffect.DEFAULT_AMPLITUDE)
                        )
                    } else {
                        @Suppress("DEPRECATION")
                        it.vibrate(80)
                    }
                }
                lastVibrationTime = now
            }

            // 🔴 BACKGROUND FLASH
            rootLayout.setBackgroundColor(Color.argb(80, 255, 0, 0))
            uiHandler.postDelayed({
                rootLayout.setBackgroundColor(Color.TRANSPARENT)
            }, 120)

            // 🎬 GIF OVERLAY
            val gifView = findViewById<ImageView>(R.id.damageGif)

            gifView.clearAnimation()
            gifView.visibility = View.VISIBLE

            // Load GIF
            Glide.with(this)
                .asGif()
                .load(R.drawable.damage_effect) // your gif
                .into(gifView)

            // Reset state
            gifView.alpha = 0f
            gifView.translationY = 150f
            gifView.scaleX = 0.85f
            gifView.scaleY = 0.85f

            // Animate entry
            gifView.animate()
                .alpha(1f)
                .translationY(0f)
                .scaleX(1f)
                .scaleY(1f)
                .setDuration(250)
                .withEndAction {

                    // Exit animation
                    gifView.postDelayed({
                        gifView.animate()
                            .alpha(0f)
                            .translationY(80f)
                            .setDuration(600)
                            .withEndAction {
                                gifView.visibility = View.GONE
                            }
                            .start()
                    }, 400)

                }
                .start()

            logStep("Self damage visual + GIF shown")
        }
    }

    private fun showResult(win: Boolean) {
        if (isGameOverHandled) {
            logStep("showResult ignored: already handled")
            return
        }

        isGameOverHandled = true
        testTimer?.cancel()

        logStep("showResult -> win=$win")

        if (::challengePlayersRef.isInitialized) {
            val myUid = userId.toString()
            challengePlayersRef.child(myUid).child("hp")
                .setValue(if (win) currentHp else 0)
                .addOnSuccessListener { logStep("Final HP write complete for user=$myUid") }
                .addOnFailureListener { e -> logError("Final HP write failed", e) }
        }

        AlertDialog.Builder(this)
            .setTitle(if (win) "VICTORY! 🏆" else "DEFEAT! 💀")
            .setMessage(if (win) "You are the last doctor standing!" else "You have been eliminated from the battle.")
            .setCancelable(false)
            .setPositiveButton("View Leaderboard") { _, _ ->
                logStep("Leaderboard button clicked from result dialog")
                finalizeChallenge()
            }
            .show()
    }

    private fun finalizeChallenge() {

        logStep("finalizeChallenge called")

        if (::challengePlayersRef.isInitialized && healthListener != null) {

            challengePlayersRef.removeEventListener(healthListener!!)

            logStep("Firebase listener removed")
        }

        if (sharedQuestionListener != null) {

            questionOrderRef.removeEventListener(sharedQuestionListener!!)

            sharedQuestionListener = null

            logStep("Shared question listener removed")
        }

        val finalChallengeId = when {

            challengeId > 0 -> {
                "lobby_$challengeId"
            }

            !intent.getStringExtra("CHALLENGE_ID").isNullOrBlank() -> {
                intent.getStringExtra("CHALLENGE_ID")!!
            }

            !intent.getStringExtra("challenge_id").isNullOrBlank() -> {
                intent.getStringExtra("challenge_id")!!
            }

            else -> {
                ""
            }
        }

        logStep(
            "Preparing final result launch -> " +
                    "challengeId=$challengeId, " +
                    "finalChallengeId=$finalChallengeId, " +
                    "reviewCount=${reviewJson.length()}"
        )

        val openResultScreen = {

            try {

                logStep(
                    "Opening ChallengeResultActivity with review JSON -> " +
                            reviewJson.toString()
                )

                val intent = Intent(
                    this,
                    ChallengeResultActivity::class.java
                ).apply {

                    // Challenge ID
                    putExtra(
                        "CHALLENGE_ID",
                        finalChallengeId
                    )

                    putExtra(
                        "challenge_id",
                        finalChallengeId
                    )

                    // User
                    putExtra(
                        "USER_ID",
                        userId
                    )

                    putExtra(
                        "user_id",
                        userId
                    )

                    // Review JSON
                    putExtra(
                        "REVIEW_JSON_STR",
                        reviewJson.toString()
                    )

                    putExtra(
                        "review_json",
                        reviewJson.toString()
                    )

                    // Extra info
                    putExtra(
                        "review_count",
                        reviewJson.length()
                    )

                    putExtra(
                        "is_challenge",
                        true
                    )
                }

                startActivity(intent)

                finish()

            } catch (e: Exception) {

                logError(
                    "Failed opening ChallengeResultActivity",
                    e
                )

                Toast.makeText(
                    this,
                    "Failed to open results",
                    Toast.LENGTH_LONG
                ).show()
            }
        }

        val url = "${BASE_URL}sync_challenge_v16_authenticated.php"

        logStep("Final sync URL -> $url")

        val req = object : StringRequest(

            Request.Method.POST,
            url,

            { response ->

                logStep(
                    "Final sync success -> $response"
                )

                openResultScreen()
            },

            { error ->

                logError(
                    "Final sync failed -> ${error.message}",
                    error
                )

                // STILL OPEN RESULT SCREEN
                openResultScreen()
            }

        ) {

            override fun getParams(): MutableMap<String, String> {

                val params = hashMapOf(

                    "challenge_id" to challengeId.toString(),

                    "user_id" to userId.toString(),

                    "finish_test" to "true"
                )

                logStep("Final sync params -> $params")

                return params
            }
        }

        req.retryPolicy = DefaultRetryPolicy(
            10000,
            0,
            1f
        )

        requestQueue.add(req)

        logStep("Final sync request queued")
    }



    override fun onDestroy() {
        super.onDestroy()
        logStep("onDestroy() called")

        testTimer?.cancel()
        uiHandler.removeCallbacksAndMessages(null)

        if (::challengePlayersRef.isInitialized && healthListener != null) {
            challengePlayersRef.removeEventListener(healthListener!!)
            logStep("Firebase listener detached in onDestroy")
        }

        if (sharedQuestionListener != null) {
            questionOrderRef.removeEventListener(sharedQuestionListener!!)
            logStep("Shared question listener detached in onDestroy")
        }
    }
}
