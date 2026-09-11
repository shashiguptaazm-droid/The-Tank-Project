package com.rankwarz.edulabsrtm

import QuestionModel
import android.animation.Animator
import android.animation.AnimatorListenerAdapter
import android.animation.ObjectAnimator
import android.content.Context
import android.content.Intent
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.CountDownTimer
import android.os.Handler
import android.os.Looper
import android.os.VibrationEffect
import android.os.Vibrator
import android.speech.tts.TextToSpeech
import android.util.Log
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.animation.Animation
import android.view.animation.AnimationUtils
import android.view.animation.TranslateAnimation
import android.widget.Button
import android.widget.FrameLayout
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.RadioButton
import android.widget.RadioGroup
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.android.volley.DefaultRetryPolicy
import com.android.volley.Request
import com.android.volley.toolbox.JsonObjectRequest
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import com.bumptech.glide.Glide
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.firebase.database.DataSnapshot
import com.google.firebase.database.DatabaseError
import com.google.firebase.database.DatabaseReference
import com.google.firebase.database.FirebaseDatabase
import com.google.firebase.database.MutableData
import com.google.firebase.database.Transaction
import com.google.firebase.database.ValueEventListener
import org.json.JSONArray
import org.json.JSONObject
import java.util.Collections
import java.util.Locale

class SubjectTestActivity : AppCompatActivity(), TextToSpeech.OnInitListener {

    private val TAG = "CHALLENGE_DEBUG"
    private val VOLLEY_TAG = "SUBJECT_TEST_REQUESTS"
    private val PLAYER_AVATAR_TAG = "PLAYER_AVATAR_TAG"
    private val FINAL_SYNC_TAG = "FINAL_SYNC"
    private val ACTION_TAG = "ACTION_TAG"

    private val IMAGE_BASE_URL = "https://medigyaan.xyz/Neurons/"
    private val BASE_URL = "https://medigyaan.xyz/Neurons/"

    private val requestQueue by lazy(LazyThreadSafetyMode.NONE) {
        Volley.newRequestQueue(applicationContext)
    }

    private lateinit var challengeRootRef: DatabaseReference
    private lateinit var challengePlayersRef: DatabaseReference
    private lateinit var questionOrderRef: DatabaseReference
    private lateinit var challengeActionRef: DatabaseReference

    private var healthListener: ValueEventListener? = null
    private var sharedQuestionListener: ValueEventListener? = null
    private var actionListener: ValueEventListener? = null

    private var isGameOverHandled = false
    private var currentHp: Int = 100

    private lateinit var questionText: TextView
    private lateinit var tvQuestionProgress: TextView
    private lateinit var statusText: TextView
    private lateinit var tvStreak: TextView
    private lateinit var timerText: TextView
    private lateinit var radioGroup: RadioGroup
    private lateinit var optionA: RadioButton
    private lateinit var optionB: RadioButton
    private lateinit var optionC: RadioButton
    private lateinit var optionD: RadioButton
    private var optionE: RadioButton? = null
    private var optionEId: Int = View.NO_ID
    private var lastFloatingText: String? = null
    private var lastShownTime = 0L
    private lateinit var submitBtn: Button
    private lateinit var questionImageView: ImageView
    private var btnFinishTest: Button? = null
    private var btnPrev: Button? = null
    private lateinit var explanationLayout: LinearLayout
    private lateinit var explanationText: TextView
    private lateinit var battleCard: View
    private lateinit var challengeBattleHeader: LinearLayout
    private lateinit var tvBattleStatusTitle: TextView
    private lateinit var btnBattleToggle: ImageButton
    private lateinit var rootLayout: ViewGroup
    private val playerImageCache = HashMap<String, String>()
    private val pendingImageCallbacks = HashMap<String, MutableList<(String) -> Unit>>()
    private val pendingImageRequests = HashSet<String>()
    private lateinit var btnAdrenaline: ImageButton
    private lateinit var btnShield: ImageButton
    private lateinit var btnShock: ImageButton
    private lateinit var btnConfuse: ImageButton
    private var btnSpeakExplanation: ImageButton? = null
    private var tts: TextToSpeech? = null

    private lateinit var tvAdrenalineCooldown: TextView
    private lateinit var tvShieldCooldown: TextView
    private lateinit var tvShockCooldown: TextView
    private lateinit var tvConfuseCooldown: TextView

    private val playerBars = mutableMapOf<String, ProgressBar>()
    private val playerScoreLabels = mutableMapOf<String, TextView>()

    private val playerScores = mutableMapOf<String, Int>()
    private val playerNames = mutableMapOf<String, String>()


    private var userId = 0
    private var currentUserName: String = "Doctor"
    private var currentQuestion: QuestionModel? = null
    private var uniqueId = 0
    private var challengeId: String = ""

    private var isChallenge = false
    private var isHost = false
    private var battleStatusExpanded = true

    private var currentSubject: String = ""
    private var currentTopic: String? = null

    private var canHeal = true
    private var canShield = true
    private var canShock = true
    private var canConfuse = true
    private var shieldRoundsActive = 0
    private var isShockCharged = false

    private val allQuestionIds = ArrayList<Int>()
    private val answeredIndices = mutableSetOf<Int>()
    private var currentIndex = 0
    private var testTimer: CountDownTimer? = null
    private var endWaitTimer: CountDownTimer? = null

    private var sharedQuestionLoaded = false
    private var myCurrentScore = 0

    private val reviewJson = JSONArray()
    private val uiHandler = Handler(Looper.getMainLooper())

    private var lastHandledActionId: String = ""

    private data class ParsedQuestionContent(
        val question: String,
        val optionA: String,
        val optionB: String,
        val optionC: String,
        val optionD: String,
        val optionE: String?
    )

    override fun onCreate(savedInstanceState: Bundle?) {

        // ✅ INIT PREFS FIRST
        val prefs = getSharedPreferences("MY_APP", Context.MODE_PRIVATE)

        super.onCreate(savedInstanceState)

        logStep("onCreate() started")

        setContentView(R.layout.activity_test_mode)
        setupAppBottomNavigation(findViewById<BottomNavigationView>(R.id.bottomNavigation), R.id.nav_home)

        // =========================
        // SAFE USER LOAD
        // =========================
        userId = prefs.getInt("user_id", 0)

        currentUserName = prefs
            .getString("name", null)
            ?.takeIf { it.isNotBlank() }
            ?: "Doctor"

        logStep("Loaded from prefs -> userId=$userId name=$currentUserName")

        // =========================
        // VALIDATE SESSION
        // =========================
        if (userId == 0) {

            logStep("Invalid user session -> finish()")

            Toast.makeText(
                this,
                "Session expired. Please login again.",
                Toast.LENGTH_LONG
            ).show()

            finish()
            return
        }

        // =========================
        // INTENT DATA
        // =========================
        uniqueId = intent.getIntExtra("UNIQUE_ID", 0)

        currentSubject = intent.getStringExtra("SUBJECT")
            ?: intent.getStringExtra("SELECTED_SUBJECT")
            ?: prefs.getString("selected_subject_preference", "")
            ?: ""

        currentTopic = intent.getStringExtra("TOPIC") ?: ""

        // ✅ SUPPORT BOTH STRING + INT
        val challengeIdString =
            intent.getStringExtra("CHALLENGE_ID")
                ?: intent.getStringExtra("challenge_id")

        val challengeIdInt = intent.getIntExtra(
            "CHALLENGE_ID_INT",
            intent.getIntExtra("challenge_id_int", 0)
        )

        challengeId = when {

            !challengeIdString.isNullOrBlank() &&
                    challengeIdString != "0" -> {
                challengeIdString
            }

            challengeIdInt != 0 -> {
                challengeIdInt.toString()
            }

            else -> {
                ""
            }
        }

        // =========================
        // FLAGS
        // =========================
        isChallenge =
            intent.getBooleanExtra("IS_CHALLENGE", false) ||
                    intent.getBooleanExtra("IS_CREATOR", false) ||
                    intent.getBooleanExtra("is_challenge", false) ||
                    challengeId.isNotBlank()

        isHost =
            intent.getBooleanExtra("IS_HOST", false) ||
                    intent.getBooleanExtra("IS_CREATOR", false) ||
                    intent.getBooleanExtra("is_host", false)

        logStep(
            "Intent -> " +
                    "userId=$userId, " +
                    "uniqueId=$uniqueId, " +
                    "challengeId=$challengeId, " +
                    "isChallenge=$isChallenge, " +
                    "isHost=$isHost"
        )

        logStep(
            "Subject=$currentSubject, " +
                    "Topic=$currentTopic, " +
                    "userName=$currentUserName"
        )

        // =========================
        // UI INIT
        // =========================
        bindViews()
        applyBattleStatusVisibility()

        setupPowerButtons()

        setupButtons()

        // =========================
        // MODE HANDLING
        // =========================
        val incomingIds =
            intent.getIntegerArrayListExtra("QUESTION_ID_LIST")

        if (incomingIds != null && incomingIds.isNotEmpty()) {

            // =========================================
            // FIXED TEST MODE
            // =========================================
            logStep(
                "Fixed test mode -> questions=${incomingIds.size}"
            )

            allQuestionIds.clear()
            allQuestionIds.addAll(incomingIds)

            currentIndex = 0

            findViewById<View>(R.id.topicLayout)?.visibility =
                View.GONE

            setBattleStatusVisible(false)

            findViewById<View>(R.id.powersContainer)?.visibility =
                View.GONE

            startTimer(30 * 60 * 1000L)

            loadQuestion(allQuestionIds[currentIndex])

        } else if (
            isChallenge &&
            challengeId.isNotBlank()
        ) {

            // =========================================
            // MULTIPLAYER MODE
            // =========================================
            logStep(
                "Multiplayer mode -> Firebase init, " +
                        "challengeId=$challengeId"
            )

            setupMultiplayerFirebase()

            registerPlayerInChallenge(currentUserName)

            fetchOrCreateSharedQuestionList()

            startTimer(15 * 60 * 1000L)

        } else {

            // =========================================
            // SINGLE PLAYER MODE
            // =========================================
            logStep(
                "Single player mode -> backend fetch"
            )

            setBattleStatusVisible(false)

            findViewById<View>(R.id.powersContainer)?.visibility =
                View.GONE

            startTimer(30 * 60 * 1000L)

            fetchQuestionListSinglePlayer()
        }

        // Initialize TTS
        tts = TextToSpeech(this, this)
    }

    private fun bindViews() {
        logStep("Binding all views")
        questionText = findViewById(R.id.questionText)
        tvQuestionProgress = findViewById(R.id.tvQuestionProgress)
        statusText = findViewById(R.id.statusText)
        tvStreak = findViewById(R.id.tvStreak)

        timerText = findViewById(R.id.timerText)
        radioGroup = findViewById(R.id.radioGroup)
        optionA = findViewById(R.id.optionA)
        optionB = findViewById(R.id.optionB)
        optionC = findViewById(R.id.optionC)
        optionD = findViewById(R.id.optionD)

        optionEId = resources.getIdentifier("optionE", "id", packageName)
        optionE = if (optionEId != 0) findViewById(optionEId) else null
        optionE?.visibility = View.GONE

        submitBtn = findViewById(R.id.submitBtn)
        questionImageView = findViewById(R.id.questionImageView)
        explanationLayout = findViewById(R.id.explanationLayout)

        btnFinishTest = findViewById(R.id.finalSubmitBtn)
        btnPrev = findViewById(R.id.prevBtn)

        explanationText = findViewById(R.id.explanationText)
        battleCard = findViewById(R.id.battleCard)
        challengeBattleHeader = findViewById(R.id.challengeBattleHeader)
        tvBattleStatusTitle = findViewById(R.id.tvBattleStatusTitle)
        btnBattleToggle = findViewById(R.id.btnBattleToggle)

        // Power Ups
        btnAdrenaline = findViewById(R.id.btnAdrenaline)
        btnShield = findViewById(R.id.btnShield)
        btnShock = findViewById(R.id.btnShock)
        btnConfuse = findViewById(R.id.btnConfuse)

        tvAdrenalineCooldown = findViewById(R.id.tvAdrenalineCooldown)
        tvShieldCooldown = findViewById(R.id.tvShieldCooldown)
        tvShockCooldown = findViewById(R.id.tvShockCooldown)
        tvConfuseCooldown = findViewById(R.id.tvConfuseCooldown)

        rootLayout = findViewById(android.R.id.content)

        val speakBtnId = resources.getIdentifier("btnSpeakExplanation", "id", packageName)
        btnSpeakExplanation = if (speakBtnId != 0) findViewById(speakBtnId) else null

        btnBattleToggle.setOnClickListener { toggleBattleStatus() }

        logStep("Views bound successfully")
    }

    private fun setupPowerButtons() {
        logStep("Setting up power buttons")

        btnAdrenaline.setOnClickListener {
            logStep("Adrenaline clicked")

            if (!canHeal) {
                Toast.makeText(this, "Adrenaline already used", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            if (challengeId.isBlank()) {
                Toast.makeText(this, "Available only in challenge mode", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            val healedHp = (currentHp + 20).coerceAtMost(100)
            val healAmount = healedHp - currentHp
            currentHp = healedHp
            canHeal = false
            btnAdrenaline.alpha = 0.45f
            tvAdrenalineCooldown.visibility = View.VISIBLE
            tvAdrenalineCooldown.text = "USED"

            if (isChallenge) {
                healPlayer(userId.toString(), healAmount)
                broadcastAction("ADRENALINE", targetId = userId.toString(), amount = healAmount)
            }

            showFloatingText("+20 HP", Color.GREEN)
            animateLocalPowerButton(btnAdrenaline)
            logStep("Adrenaline applied. currentHp=$currentHp")
        }

        btnShield.setOnClickListener {
            logStep("Shield clicked")

            if (!canShield) {
                Toast.makeText(this, "Shield already used", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            if (challengeId.isBlank()) {
                Toast.makeText(this, "Available only in challenge mode", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            shieldRoundsActive = 2
            canShield = false
            btnShield.alpha = 0.45f
            tvShieldCooldown.visibility = View.VISIBLE
            tvShieldCooldown.text = "ACTIVE: 2"
            showFloatingText("SHIELD ACTIVE", Color.CYAN)
            animateLocalPowerButton(btnShield)
            broadcastAction("SHIELD", targetId = userId.toString(), amount = shieldRoundsActive)
            logStep("Shield activated for $shieldRoundsActive rounds")
        }

        btnShock.setOnClickListener {
            logStep("Shock clicked")

            if (!canShock) {
                Toast.makeText(this, "Shock already used", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            if (challengeId.isBlank()) {
                Toast.makeText(this, "Available only in challenge mode", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            isShockCharged = true
            canShock = false
            btnShock.alpha = 0.45f
            tvShockCooldown.visibility = View.VISIBLE
            tvShockCooldown.text = "CHARGED"
            showFloatingText("SHOCK CHARGED", Color.YELLOW)
            animateLocalPowerButton(btnShock)
            broadcastAction("SHOCK", targetId = userId.toString(), amount = 1)
            logStep("Shock charged for next correct answer")
        }

        btnConfuse.setOnClickListener {
            logStep("Confuse clicked")

            if (!canConfuse) {
                Toast.makeText(this, "Confuse already used", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            if (challengeId.isBlank()) {
                Toast.makeText(this, "Available only in challenge mode", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            val myUid = userId.toString()
            val targetId = playerBars.keys.filter { it != myUid }.randomOrNull()
            canConfuse = false
            btnConfuse.alpha = 0.45f
            tvConfuseCooldown.visibility = View.VISIBLE
            tvConfuseCooldown.text = "USED"
            animateLocalPowerButton(btnConfuse)

            if (targetId == null) {
                showFloatingText("No target", Color.GRAY)
                logStep("Confuse skipped: no opponent target")
                return@setOnClickListener
            }

            val confuseDamage = 4
            broadcastAction("CONFUSE", targetId = targetId, amount = confuseDamage)
            damagePlayer(targetId, confuseDamage)
            showFloatingText("CONFUSE HIT", Color.MAGENTA)
            animatePlayerPulse(targetId, Color.MAGENTA, "CONFUSED")
            logStep("Confuse applied to $targetId for $confuseDamage damage")
        }
    }

    private fun setupMultiplayerFirebase() {
        logStep("Setting up multiplayer Firebase references")

        val db = FirebaseDatabase.getInstance().getReference("challenges").child(challengeId)
        challengeRootRef = db
        challengePlayersRef = db.child("players")
        questionOrderRef = db.child("question_ids")
        challengeActionRef = db.child("last_action")

        logStep(
            "Firebase refs ready -> root=${challengeRootRef.path}, " +
                    "players=${challengePlayersRef.path}, question_ids=${questionOrderRef.path}"
        )

        healthListener = object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                logStep("players snapshot received. children=${snapshot.childrenCount}")

                var survivors = 0
                var lastManId = ""

                for (pSnap in snapshot.children) {
                    val pId = pSnap.key ?: continue
                    val hp = pSnap.child("hp").getValue(Int::class.java) ?: 100
                    val score = pSnap.child("score").getValue(Int::class.java) ?: 0
                    val name = pSnap.child("name").getValue(String::class.java) ?: "Opponent"

                    playerNames[pId] = name
                    playerScores[pId] = score

                    logStep("Player data -> id=$pId, name=$name, hp=$hp, score=$score")

                    if (hp > 0) {
                        survivors++
                        lastManId = pId
                    }

                    updatePlayerHealthUI(pId, name, hp, score)

                    if (pId == userId.toString() && hp <= 0 && !isGameOverHandled) {
                        logStep("Local player HP reached zero")
                        showResult(false)
                    }
                }

                logStep("Survivors=$survivors, lastManId=$lastManId")

                if (survivors == 1 && playerBars.size > 1 && !isGameOverHandled) {
                    logStep("Only one survivor remains")
                    showResult(lastManId == userId.toString())
                }
            }

            override fun onCancelled(error: DatabaseError) {
                logError("healthListener cancelled", error.toException())
            }
        }

        challengePlayersRef.addValueEventListener(healthListener!!)
        logStep("Health listener attached")

        actionListener = object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                if (!snapshot.exists()) return

                val actionId = snapshot.child("action_id").getValue(String::class.java) ?: return
                if (actionId == lastHandledActionId) return
                lastHandledActionId = actionId

                val type = snapshot.child("type").getValue(String::class.java) ?: ""
                val actorId = snapshot.child("actor_id").getValue(String::class.java) ?: ""
                val targetId = snapshot.child("target_id").getValue(String::class.java) ?: ""
                val amount = snapshot.child("amount").getValue(Int::class.java) ?: 0
                val actorName = snapshot.child("actor_name").getValue(String::class.java)
                    ?: playerNames[actorId]
                    ?: "Player"

                runOnUiThread {
                    playRemoteActionAnimation(type, actorId, targetId, amount, actorName)
                }
            }

            override fun onCancelled(error: DatabaseError) {
                logError("actionListener cancelled", error.toException())
            }
        }

        challengeActionRef.addValueEventListener(actionListener!!)
        logStep("Action listener attached")
    }

    private fun registerPlayerInChallenge(name: String) {
        if (challengeId.isBlank()) {
            logStep("registerPlayerInChallenge aborted: challengeId blank")
            return
        }

        logStep("Registering player in challenge -> userId=$userId, name=$name")
        playerNames[userId.toString()] = name

        val data = hashMapOf(
            "name" to name,
            "hp" to 100,
            "score" to 0,
            "isFinished" to false
        )

        challengePlayersRef.child(userId.toString()).setValue(data)
            .addOnSuccessListener { logStep("Player registration success") }
            .addOnFailureListener { e -> logError("Player registration failed", e) }
    }

    private fun fetchOrCreateSharedQuestionList() {
        logStep("fetchOrCreateSharedQuestionList started")

        sharedQuestionListener = object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                logStep("question_ids snapshot received. exists=${snapshot.exists()}, children=${snapshot.childrenCount}")

                if (snapshot.exists()) {
                    // DATA EXISTS: Someone (likely the host) has already set the question list
                    val list = ArrayList<Int>()
                    snapshot.children.forEach { child ->
                        val value = child.getValue(Int::class.java)
                        if (value != null) list.add(value)
                    }

                    logStep("Shared question IDs read -> count=${list.size}")

                    if (list.isNotEmpty() && !sharedQuestionLoaded) {
                        sharedQuestionLoaded = true
                        allQuestionIds.clear()
                        allQuestionIds.addAll(list)
                        currentIndex = 0
                        logStep("Shared question list loaded into memory. Starting first question.")
                        loadQuestion(allQuestionIds[currentIndex])
                    }
                } else if (isHost) {
                    // NO DATA & HOST: We are responsible for picking the 15 questions
                    logStep("No shared list found and user is host. Generating list from backend")

                    fetchQuestionIdsFromBackend { ids ->
                        if (ids.isNotEmpty()) {
                            // 1. Shuffle the entire pool fetched from backend
                            val shuffledPool = ids.shuffled()

                            // 2. IMPORTANT: Take only the first 15 to keep the game focused
                            val battleList = if (shuffledPool.size > 15) {
                                shuffledPool.take(15)
                            } else {
                                shuffledPool
                            }

                            // 3. Save only the 15 selected IDs to Firebase for everyone to use
                            questionOrderRef.setValue(battleList)
                                .addOnSuccessListener {
                                    logStep("Shared list of ${battleList.size} questions saved to Firebase")
                                }
                                .addOnFailureListener { e ->
                                    logError("Failed to save shared question list", e)
                                }

                            // 4. Load local memory
                            allQuestionIds.clear()
                            allQuestionIds.addAll(battleList)
                            currentIndex = 0
                            loadQuestion(allQuestionIds[0])
                            sharedQuestionLoaded = true
                        } else {
                            Toast.makeText(
                                this@SubjectTestActivity,
                                "No questions found for this topic",
                                Toast.LENGTH_SHORT
                            ).show()
                        }
                    }
                } else {
                    // NO DATA & CLIENT: Just wait for the host to finish their work
                    logStep("Client waiting for host to create shared question list...")
                }
            }

            override fun onCancelled(error: DatabaseError) {
                logError("question order listener cancelled", error.toException())
            }
        }

        // Attach the listener
        questionOrderRef.addValueEventListener(sharedQuestionListener!!)
        logStep("Shared question listener attached to path: ${questionOrderRef.path}")
    }

    private fun fetchQuestionIdsFromBackend(callback: (ArrayList<Int>) -> Unit) {
        val urlBuilder = StringBuilder("${BASE_URL}api/getQuestions.php?")
            .append("subject=${Uri.encode(currentSubject)}")
            .append("&user_id=$userId")

        if (!currentTopic.isNullOrEmpty()) {
            urlBuilder.append("&topic=${Uri.encode(currentTopic)}")
        }

        val url = urlBuilder.toString()
        logStep("STEP 1: Fetching question IDs from backend -> $url")

        val req = StringRequest(Request.Method.GET, url, { response ->
            try {
                logStep("STEP 2: API RAW RESPONSE -> $response")

                val json = JSONObject(response)

                if (!json.optBoolean("success", false)) {
                    logError("STEP 3: Backend returned failure -> ${json.optString("error")}")
                    callback(ArrayList())
                    return@StringRequest
                }

                val ids = ArrayList<Int>()
                val arr = json.optJSONArray("all_question_ids")

                if (arr != null) {
                    for (i in 0 until arr.length()) {
                        ids.add(arr.optInt(i))
                    }
                } else {
                    logError("STEP 4: 'all_question_ids' missing")
                }

                logStep("STEP 5: Parsed question IDs -> $ids")

                json.optJSONObject("data")?.let { data ->
                    logStep("STEP 6: First question preview -> ${data.optString("question")}")
                }

                callback(ids)

            } catch (e: Exception) {
                logError("STEP ERROR: Question IDs parse error", e)
                callback(ArrayList())
            }

        }, { error ->
            logError("STEP ERROR: Question ID request failed -> ${error.message}", error)
            callback(ArrayList())
        })

        req.retryPolicy = DefaultRetryPolicy(
            10000,
            2,
            DefaultRetryPolicy.DEFAULT_BACKOFF_MULT
        )

        req.tag = VOLLEY_TAG
        requestQueue.add(req)
        logStep("STEP 7: Question ID request queued")
    }

    private fun shuffleQuestionIds(ids: ArrayList<Int>) {
        Collections.shuffle(ids)
        logStep("Question IDs shuffled -> $ids")
    }

    private fun fetchQuestionListSinglePlayer() {
        logStep("fetchQuestionListSinglePlayer started")
        fetchQuestionIdsFromBackend { ids ->
            allQuestionIds.clear()
            allQuestionIds.addAll(ids)
            logStep("Single-player raw question list loaded -> size=${allQuestionIds.size}, ids=$allQuestionIds")

            if (allQuestionIds.isEmpty()) {
                Toast.makeText(this, "No questions available", Toast.LENGTH_SHORT).show()
                return@fetchQuestionIdsFromBackend
            }

            shuffleQuestionIds(allQuestionIds)
            currentIndex = 0
            logStep("Single-player shuffled question list -> $allQuestionIds")
            loadQuestion(allQuestionIds[currentIndex])
        }
    }
    private fun buildPhotoUrl(rawPhoto: String): String {
        val cleaned = rawPhoto
            .replace("\\", "/")
            .replace("./", "")
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
    private fun loadQuestion(qId: Int) {
        val url = "${BASE_URL}api/get_single_question.php?question_id=$qId"
        logStep("Loading question -> id=$qId, url=$url")

        val req = JsonObjectRequest(Request.Method.GET, url, null, { res ->
            try {
                val data = if (res.has("data")) res.getJSONObject("data") else res

                currentQuestion = QuestionModel(
                    id = data.optInt("question_id", qId),
                    question = data.optString("question", ""),
                    a = data.optString("option_a", ""),
                    b = data.optString("option_b", ""),
                    c = data.optString("option_c", ""),
                    d = data.optString("option_d", ""),
                    correctAnswer = data.optString("correct_option", "").trim().uppercase(Locale.US),
                    explanation = data.optString("explanation", ""),
                    imageUrl = data.optString("question_image", "")
                )

                logStep("Question parsed successfully -> id=${currentQuestion?.id}")
                currentQuestion?.let { displayQuestion(it) }
            } catch (e: Exception) {
                logError("Load question parse error", e)
                moveNext()
            }
        }, { error ->
            logError("Load question failed", error)
            moveNext()
        })

        req.tag = VOLLEY_TAG
        requestQueue.add(req)
        logStep("Question request queued")
    }

    private fun displayQuestion(q: QuestionModel) {
        logStep("displayQuestion -> qId=${q.id}")

        updateQuestionCounter()

        val fullText = q.question.trim()

        // Remove options from question text
        val splitRegex = Regex("""(?i)\s*[\(\[]?a[\)\].]""")
        val cleanQuestion = fullText.split(splitRegex)[0].trim()
        questionText.text = cleanQuestion
        logStep("Question text displayed: $cleanQuestion")

        // Load options
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

        // Image
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

        // Handle Locked State for already answered questions
        if (answeredIndices.contains(currentIndex)) {
            logStep("Question already answered -> locking state")
            setAnswerControlsEnabled(false)
            submitBtn.text = "Answered"
            explanationLayout.visibility = View.VISIBLE
            explanationText.text = aiMarkdownSpannable(q.explanation)
            explanationText.setTextColor(Color.GRAY)
        } else {
            // 🔥 RESET STATE FOR NEW QUESTION
            radioGroup.clearCheck()
            explanationLayout.visibility = View.GONE
            stopSpeaking()

            setAnswerControlsEnabled(true)
            submitBtn.text = "Submit"
            submitBtn.isEnabled = true
            submitBtn.alpha = 1f
            logStep("Question ready for answer")
        }

        btnPrev?.visibility = if (currentIndex > 0) View.VISIBLE else View.INVISIBLE
    }

    private fun updateQuestionCounter() {
        val displayIndex = currentIndex + 1
        val total = allQuestionIds.size
        tvQuestionProgress.text = "Q $displayIndex / $total"
        statusText.text = "Round $displayIndex of $total"
    }

    private fun setupButtons() {
        logStep("Setting up submit button...")

        btnPrev?.setOnClickListener {
            if (currentIndex > 0) {
                uiHandler.removeCallbacksAndMessages(null) // Stop auto-advance if moving back
                currentIndex--
                logStep("Prev clicked -> currentIndex=$currentIndex")
                loadQuestion(allQuestionIds[currentIndex])
            }
        }

        submitBtn.setOnClickListener {
            logStep("Submit clicked")

            val selectedId = radioGroup.checkedRadioButtonId
            if (selectedId == -1) {
                Toast.makeText(this, "Please select an answer", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            val ans = when (selectedId) {
                R.id.optionA -> "A"
                R.id.optionB -> "B"
                R.id.optionC -> "C"
                R.id.optionD -> "D"
                optionEId -> "E"
                else -> ""
            }

            if (ans.isBlank()) {
                Toast.makeText(this, "Please select a valid answer", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            val correct = currentQuestion?.correctAnswer?.trim()?.uppercase(Locale.US)
            val isCorrect = ans.trim().uppercase(Locale.US) == correct

            logStep("Answer selected -> ans=$ans, correct=$correct, isCorrect=$isCorrect")

            addReviewEntry(
                questionId = currentQuestion?.id ?: 0,
                questionText = currentQuestion?.question ?: "",
                yourAnswer = ans,
                correctAnswer = currentQuestion?.correctAnswer ?: "",
                explanation = currentQuestion?.explanation ?: "",
                isCorrect = isCorrect,
                questionImage = currentQuestion?.imageUrl ?: ""
            )

            answeredIndices.add(currentIndex)
            setAnswerControlsEnabled(false)

            handleScoringAndDamage(isCorrect)
            syncWithServer(ans)
            showInstantFeedback(isCorrect)
        }

        btnSpeakExplanation?.setOnClickListener {
            speakExplanation()
        }

        btnFinishTest?.setOnClickListener {
            logStep("Finish Test manually clicked")
            AlertDialog.Builder(this)
                .setTitle("Finish Test?")
                .setMessage("Are you sure you want to end the test now? Your current score will be saved.")
                .setPositiveButton("Finish") { _, _ ->
                    showResult(win = !isChallenge || currentHp > 0)
                }
                .setNegativeButton("Continue", null)
                .show()
        }
    }

    private fun showInstantFeedback(isCorrect: Boolean) {
        logStep("showFeedback called -> isCorrect=$isCorrect")

        explanationLayout.visibility = View.VISIBLE
        explanationText.text = aiMarkdownSpannable(if (isCorrect) {
            "Correct!\n\n${currentQuestion?.explanation?.takeIf { it.isNotBlank() } ?: "No explanation available."}"
        } else {
            "Wrong answer.\n\n${currentQuestion?.explanation?.takeIf { it.isNotBlank() } ?: "No explanation available."}"
        })
        explanationText.setTextColor(if (isCorrect) Color.GREEN else Color.RED)

        explanationLayout.alpha = 0f
        explanationLayout.animate().alpha(1f).setDuration(200).start()

        // If player is dead, don't wait for delay, move to result immediately
        if (isChallenge && currentHp <= 0) {
            moveNext()
            return
        }

        uiHandler.removeCallbacksAndMessages(null)
        uiHandler.postDelayed({
            logStep("Feedback delay finished -> moving next")
            moveNext()
        }, 1800) // Reduced delay for smoother multiplayer flow
    }

    private fun speakExplanation() {
        val text = explanationText.text.toString()
        if (text.isNotBlank()) {
            logStep("TTS: Speaking explanation")
            tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "ExplanationID")
        }
    }

    private fun stopSpeaking() {
        if (tts?.isSpeaking == true) {
            tts?.stop()
        }
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            val result = tts?.setLanguage(Locale.US)
            if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                logError("TTS: Language not supported")
            } else {
                logStep("TTS: Initialization successful")
            }
        } else {
            logError("TTS: Initialization failed")
        }
    }


    private fun moveNext() {
        if (allQuestionIds.isEmpty()) {
            logError("moveNext called but allQuestionIds is empty")
            showResult(false)
            return
        }

        stopSpeaking()

        currentIndex++
        logStep("moveNext called -> currentIndex=$currentIndex, total=${allQuestionIds.size}")

        // Continue if there are more questions AND the player is still alive
        if (currentIndex < allQuestionIds.size && (!isChallenge || currentHp > 0)) {
            val nextQid = allQuestionIds[currentIndex]
            logStep("Loading next question -> index=$currentIndex, qid=$nextQid")

            radioGroup.clearCheck()
            setAnswerControlsEnabled(false)
            submitBtn.isEnabled = false
            submitBtn.alpha = 0.65f
            explanationLayout.visibility = View.GONE

            loadQuestion(nextQid)
        } else { 
            logStep("All questions completed")

            if (isChallenge && challengeId.isNotBlank()) {
                challengePlayersRef.child(userId.toString())
                    .child("isFinished")
                    .setValue(true)
                    .addOnSuccessListener { logStep("Marked user as finished in Firebase") }
                    .addOnFailureListener { e -> logError("Failed to mark finished", e) }

                submitBtn.isEnabled = false
                submitBtn.alpha = 0.5f
                
                radioGroup.visibility = View.GONE
                explanationLayout.visibility = View.GONE
                questionImageView.visibility = View.GONE

                startEndWaitTimer()
                checkEndGame()
            } else {
                showResult(true)
            }
        }
    }

    private fun handleScoringAndDamage(isCorrect: Boolean) {
        logStep("handleScoringAndDamage -> isCorrect=$isCorrect, isChallenge=$isChallenge")

        if (!isChallenge) return

        val myUid = userId.toString()

        if (isCorrect) {
            myCurrentScore += 4
            logStep("Local score increased -> myCurrentScore=$myCurrentScore")

            challengePlayersRef.child(myUid).child("score")
                .runTransaction(object : Transaction.Handler {
                    override fun doTransaction(d: MutableData): Transaction.Result {
                        val current = d.getValue(Int::class.java) ?: 0
                        val updated = current + 4
                        d.value = updated
                        logStep("Score transaction -> $current -> $updated")
                        return Transaction.success(d)
                    }

                    override fun onComplete(
                        error: DatabaseError?,
                        committed: Boolean,
                        currentData: DataSnapshot?
                    ) {
                        if (error != null) {
                            logError("Score transaction failed", error.toException())
                        } else {
                            logStep("Score transaction complete")
                        }
                    }
                })

            val dmg = if (isShockCharged) 15 else 8
            logStep("Damage to opponents = $dmg")

            broadcastAction("ATTACK", targetId = "", amount = dmg)

            if (isShockCharged) {
                isShockCharged = false
                tvShockCooldown.text = "USED"
            }

            for (pid in playerBars.keys) {
                if (pid != myUid) {
                    logStep("Damaging opponent -> $pid by $dmg")
                    damagePlayer(pid, dmg)
                }
            }
        } else {
            logStep("Wrong answer -> self damage 5")
            broadcastAction("SELF_HIT", targetId = myUid, amount = 5)
            damagePlayer(myUid, 5)
        }
    }
    private val tauntCache = mutableMapOf<String, String>()
    private val pendingTaunts = mutableMapOf<String, MutableList<(String) -> Unit>>()

    private fun fetchTaunt(
        type: String,
        actorName: String?,
        amount: Int,
        callback: (String) -> Unit
    ) {
        val safeName = actorName?.takeIf { it.isNotBlank() } ?: "Opponent"

        val key = "$type|$safeName|$amount"

        // ✅ CACHE HIT
        tauntCache[key]?.let {
            logStep("Taunt cache hit -> $it")
            callback(it)
            return
        }

        // ✅ REQUEST ALREADY RUNNING
        if (pendingTaunts.containsKey(key)) {
            logStep("Taunt request in-flight, queueing callback")
            pendingTaunts[key]?.add(callback)
            return
        }

        pendingTaunts[key] = mutableListOf(callback)

        val url = "https://medigyaan.xyz/Neurons/taunt_ai.php"

        val request = object : StringRequest(
            Method.POST,
            url,
            { response ->
                val callbacks = pendingTaunts.remove(key) ?: mutableListOf()

                try {
                    val obj = JSONObject(response)
                    val taunt = obj.optString("taunt", "").trim()

                    val finalTaunt = if (taunt.isNotEmpty()) {
                        taunt
                    } else {
                        localFallback(type, safeName, amount)
                    }

                    tauntCache[key] = finalTaunt

                    logStep("Taunt success -> $finalTaunt")

                    callbacks.forEach { it(finalTaunt) }

                } catch (e: Exception) {
                    logError("Taunt parse error", e)

                    val fallback = localFallback(type, safeName, amount)
                    callbacks.forEach { it(fallback) }
                }
            },
            { error ->
                val callbacks = pendingTaunts.remove(key) ?: mutableListOf()

                logError("Taunt API error: ${error.message}")

                val fallback = localFallback(type, safeName, amount)
                callbacks.forEach { it(fallback) }
            }
        ) {
            override fun getParams(): MutableMap<String, String> {
                return hashMapOf(
                    "type" to type,
                    "actor" to safeName,
                    "amount" to amount.toString()
                )
            }
        }

        request.tag = "TAUNT_API"

        // ⚠️ IMPORTANT: Use SINGLE queue (not newRequestQueue)
        requestQueue.add(request)
    }
    private fun localFallback(type: String, actorName: String, amount: Int): String {
        return when (type) {
            "ATTACK" -> "$actorName strikes hard!"
            "SHIELD" -> "$actorName blocks the attack!"
            "ADRENALINE" -> "$actorName heals +$amount!"
            "SHOCK" -> "$actorName charges energy!"
            "CONFUSE" -> "$actorName disrupts an opponent!"
            "SELF_HIT" -> "$actorName messed up!"
            "BLOCKED" -> "Attack blocked!"
            else -> "$actorName makes a move!"
        }
    }
    private fun damagePlayer(pid: String, dmg: Int) {
        logStep("damagePlayer -> pid=$pid, dmg=$dmg, shieldRoundsActive=$shieldRoundsActive")

        if (pid == userId.toString() && shieldRoundsActive > 0 && dmg > 0) {
            shieldRoundsActive--
            logStep("Shield blocked damage. Remaining shield rounds=$shieldRoundsActive")
            tvShieldCooldown.text = if (shieldRoundsActive > 0) "ACTIVE: $shieldRoundsActive" else "USED"
            showFloatingText("BLOCKED", Color.CYAN)
            animatePlayerPulse(pid, Color.CYAN, "BLOCKED")
            broadcastAction("BLOCKED", targetId = pid, amount = dmg)
            return
        }

        if (pid == userId.toString()) {
            currentHp = (currentHp - dmg).coerceIn(0, 100)
            logStep("Local hp updated -> currentHp=$currentHp")
        }

        if (isChallenge && challengeId.isNotBlank()) {
            challengePlayersRef.child(pid).child("hp")
                .runTransaction(object : Transaction.Handler {
                    override fun doTransaction(d: MutableData): Transaction.Result {
                        val current = d.getValue(Int::class.java) ?: 100
                        val updated = (current - dmg).coerceIn(0, 100)
                        d.value = updated
                        logStep("HP transaction -> pid=$pid, $current -> $updated")
                        return Transaction.success(d)
                    }

                    override fun onComplete(
                        error: DatabaseError?,
                        committed: Boolean,
                        currentData: DataSnapshot?
                    ) {
                        if (error != null) {
                            logError("HP transaction failed for pid=$pid", error.toException())
                        } else {
                            logStep("HP transaction complete for pid=$pid")
                        }
                    }
                })
        }

        if (pid == userId.toString()) {
            playerBars[pid]?.let { triggerDamageVisuals(it, true) }
        }
    }

    private fun healPlayer(pid: String, amount: Int) {
        if (amount <= 0) return

        logStep("healPlayer -> pid=$pid, amount=$amount")

        if (pid == userId.toString()) {
            currentHp = (currentHp + amount).coerceIn(0, 100)
            logStep("Local hp healed -> currentHp=$currentHp")
        }

        if (isChallenge && challengeId.isNotBlank()) {
            challengePlayersRef.child(pid).child("hp")
                .runTransaction(object : Transaction.Handler {
                    override fun doTransaction(d: MutableData): Transaction.Result {
                        val current = d.getValue(Int::class.java) ?: 100
                        val updated = (current + amount).coerceIn(0, 100)
                        d.value = updated
                        logStep("HP heal transaction -> pid=$pid, $current -> $updated")
                        return Transaction.success(d)
                    }

                    override fun onComplete(
                        error: DatabaseError?,
                        committed: Boolean,
                        currentData: DataSnapshot?
                    ) {
                        if (error != null) {
                            logError("HP heal transaction failed for pid=$pid", error.toException())
                        } else {
                            logStep("HP heal transaction complete for pid=$pid")
                        }
                    }
                })
        }

        if (pid == userId.toString()) {
            playerBars[pid]?.let { bar ->
                bar.progressTintList = ColorStateList.valueOf(hpColor(currentHp))
                ObjectAnimator.ofInt(bar, "progress", bar.progress, currentHp).apply {
                    duration = 250
                    start()
                }
            }
        }
    }

    private fun broadcastAction(type: String, targetId: String = "", amount: Int = 0) {
        if (!isChallenge || challengeId.isBlank()) return
        if (!this::challengeActionRef.isInitialized) return

        val actionId = "${System.currentTimeMillis()}_$userId"
        val map = hashMapOf<String, Any>(
            "action_id" to actionId,
            "type" to type,
            "actor_id" to userId.toString(),
            "actor_name" to currentUserName,
            "target_id" to targetId,
            "amount" to amount,
            "ts" to System.currentTimeMillis()
        )

        challengeActionRef.setValue(map)
            .addOnSuccessListener { logStep("Action broadcast -> $type ($actionId)") }
            .addOnFailureListener { e -> logError("Action broadcast failed -> $type", e) }
    }

    private fun playRemoteActionAnimation(
        type: String,
        actorId: String,
        targetId: String,
        amount: Int,
        actorName: String
    ) {

        val color = when (type) {
            "ADRENALINE" -> Color.GREEN
            "SHIELD" -> Color.CYAN
            "SHOCK" -> Color.YELLOW
            "CONFUSE" -> Color.MAGENTA
            "ATTACK" -> Color.RED
            "SELF_HIT" -> Color.RED
            "BLOCKED" -> Color.CYAN
            else -> Color.WHITE
        }

        val pulseTarget = if (type == "SELF_HIT" || type == "BLOCKED") targetId else actorId

        // ✅ Only animation first (NO TEXT YET)
        animatePlayerPulse(pulseTarget, color, "")

        // ✅ Fetch taunt (AI OR fallback handled inside)
        fetchTaunt(type, actorName, amount) { finalText ->

            runOnUiThread {
                showFloatingText(finalText, color)
                logStep("Final Taunt -> $finalText")
            }
        }

        if (amount > 0) {
            logStep("Remote action -> $type | $actorName | $amount")
        }
    }

    private fun animatePlayerPulse(pid: String, color: Int, label: String) {
        runOnUiThread {
            val row = challengeBattleHeader.findViewWithTag<LinearLayout>(pid)
            val bar = playerBars[pid]

            row?.animate()?.scaleX(1.04f)?.scaleY(1.04f)?.setDuration(140)?.withEndAction {
                row.animate().scaleX(1f).scaleY(1f).setDuration(140).start()
            }?.start()

            bar?.let {
                it.progressTintList = ColorStateList.valueOf(color)
                ObjectAnimator.ofInt(it, "progress", it.progress, it.progress).apply {
                    duration = 150
                    start()
                }
            }

            if (label.isNotBlank()) {
                showFloatingText(label, color)
            }
        }
    }



    private fun fetchPlayerImage(
        targetUserId: String,
        callback: (String) -> Unit
    ) {
        logStep("fetchPlayerImage called for userId=$targetUserId")

        // ✅ 1. Cache hit
        playerImageCache[targetUserId]?.let {
            logStep("Image cache hit for userId=$targetUserId")
            callback(it)
            return
        }

        // ✅ 2. Already fetching → queue callback
        pendingImageCallbacks[targetUserId]?.let { list ->
            logStep("Request already in flight → queue callback for userId=$targetUserId")
            list.add(callback)
            return
        }

        // ✅ 3. Start new request
        pendingImageRequests.add(targetUserId)
        pendingImageCallbacks[targetUserId] = mutableListOf(callback)

        val url = "${BASE_URL}get_profilev1.php?user_id=$targetUserId&viewer_id=$userId"
        logStep("Fetching image from API: $url")

        val request = StringRequest(
            Request.Method.GET,
            url,
            { response ->

                pendingImageRequests.remove(targetUserId)
                val callbacks = pendingImageCallbacks.remove(targetUserId).orEmpty()

                try {
                    logStep("Image API response for $targetUserId -> $response")

                    val root = JSONObject(response)
                    val data = root.optJSONObject("data") ?: root

                    val rawPhoto = data.optString("photo", "").trim()

                    val finalUrl = buildPhotoUrl(rawPhoto)

                    // ✅ Save cache
                    playerImageCache[targetUserId] = finalUrl

                    logStep("Final image URL for $targetUserId -> $finalUrl")

                    callbacks.forEach { it(finalUrl) }

                } catch (e: Exception) {
                    logError("Image parse error for userId=$targetUserId", e)

                    callbacks.forEach { it("") }
                }
            },
            { error ->
                pendingImageRequests.remove(targetUserId)
                val callbacks = pendingImageCallbacks.remove(targetUserId).orEmpty()

                logError("Image API error for userId=$targetUserId: ${error.message}", error)

                callbacks.forEach { it("") }
            }
        )

        request.tag = PLAYER_AVATAR_TAG
        requestQueue.add(request)
    }

    private fun updatePlayerHealthUI(
        pId: String,
        name: String,
        hp: Int,
        score: Int
    ) {
        val isMe = pId == userId.toString()
        if (isMe) currentHp = hp

        logStep("updatePlayerHealthUI -> pid=$pId, hp=$hp, score=$score")

        if (!playerBars.containsKey(pId)) {
            logStep("Creating new UI row for player=$pId")

            val row = LinearLayout(this).apply {
                tag = pId
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                layoutParams = LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT
                ).apply { setMargins(0, 15, 0, 15) }
            }

            val size = (45 * resources.displayMetrics.density).toInt()
            val avatar = ImageView(this).apply {
                layoutParams = LinearLayout.LayoutParams(size, size)
                scaleType = ImageView.ScaleType.CENTER_CROP
                setImageResource(android.R.drawable.ic_menu_gallery)
            }

            val infoLayout = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.2f)
                setPadding(30, 0, 10, 0)
            }

            val nameLabel = TextView(this).apply {
                text = if (isMe) "YOU" else name
                textSize = 14f
                setTextColor(ContextCompat.getColor(this@SubjectTestActivity, R.color.text_primary))
                setTypeface(null, Typeface.BOLD)
            }

            val scoreLabel = TextView(this).apply {
                text = "Score: $score"
                textSize = 12f
                setTextColor(ContextCompat.getColor(this@SubjectTestActivity, R.color.text_secondary))
            }

            infoLayout.addView(nameLabel)
            infoLayout.addView(scoreLabel)

            val bar = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
                layoutParams = LinearLayout.LayoutParams(0, 35, 2.5f)
                max = 100
                progress = hp
                progressTintList = ColorStateList.valueOf(hpColor(hp))
            }

            row.addView(avatar)
            row.addView(infoLayout)
            row.addView(bar)

            challengeBattleHeader.addView(row)
            playerBars[pId] = bar
            playerScoreLabels[pId] = scoreLabel
            playerNames[pId] = name

            loadAvatar(pId, name, avatar)
            applyBattleStatusVisibility()
        } else {
            val bar = playerBars[pId] ?: return
            playerScoreLabels[pId]?.text = "Score: $score"
            playerScores[pId] = score
            playerNames[pId] = name

            if (hp < bar.progress) {
                triggerDamageVisuals(bar, isMe)
            }

            bar.progressTintList = ColorStateList.valueOf(hpColor(hp))

            ObjectAnimator.ofInt(bar, "progress", bar.progress, hp).apply {
                duration = 350
                start()
            }

            val row = challengeBattleHeader.findViewWithTag<LinearLayout>(pId)
            val avatar = row?.getChildAt(0) as? ImageView
            if (avatar != null && !playerImageCache.containsKey(pId)) {
                loadAvatar(pId, name, avatar)
            }
        }
    }

    private fun toggleBattleStatus() {
        battleStatusExpanded = !battleStatusExpanded
        applyBattleStatusVisibility()
    }

    private fun setBattleStatusVisible(visible: Boolean) {
        if (::battleCard.isInitialized) {
            battleCard.visibility = if (visible) View.VISIBLE else View.GONE
        }
    }

    private fun applyBattleStatusVisibility() {
        if (!::challengeBattleHeader.isInitialized || !::btnBattleToggle.isInitialized || !::tvBattleStatusTitle.isInitialized) return

        if (!battleStatusExpanded) {
            tvBattleStatusTitle.text = "YOUR SCORE: $myCurrentScore"
            for (index in 0 until challengeBattleHeader.childCount) {
                challengeBattleHeader.getChildAt(index).visibility = View.GONE
            }
        } else {
            tvBattleStatusTitle.text = "BATTLE STATUS"
            for (index in 0 until challengeBattleHeader.childCount) {
                challengeBattleHeader.getChildAt(index).visibility = View.VISIBLE
            }
        }

        btnBattleToggle.setImageResource(
            if (battleStatusExpanded) android.R.drawable.arrow_up_float
            else android.R.drawable.arrow_down_float
        )
        btnBattleToggle.contentDescription =
            if (battleStatusExpanded) "Collapse battle status" else "Expand battle status"
    }

    private fun loadAvatar(
        pId: String,
        name: String,
        imageView: ImageView
    ) {
        playerImageCache[pId]?.let { cachedUrl ->
            logStep("Avatar cache hit -> $pId -> $cachedUrl")
            if (cachedUrl.isNotBlank()) {
                Glide.with(this)
                    .load(cachedUrl)
                    .placeholder(android.R.drawable.ic_menu_gallery)
                    .error(android.R.drawable.ic_menu_report_image)
                    .circleCrop()
                    .into(imageView)
                return
            }
        }

        fetchPlayerImage(pId) { fetchedUrl ->
            val finalUrl = if (fetchedUrl.isNotBlank()) {
                fetchedUrl
            } else {
                "https://api.dicebear.com/7.x/pixel-art/png?seed=${Uri.encode(name.replace(" ", "_"))}"
            }

            logStep("Loading avatar for player=$pId -> $finalUrl")

            runOnUiThread {
                if (!isFinishing && !isDestroyed) {
                    Glide.with(this)
                        .load(finalUrl)
                        .placeholder(android.R.drawable.ic_menu_gallery)
                        .error(android.R.drawable.ic_menu_report_image)
                        .circleCrop()
                        .into(imageView)
                }
            }
        }
    }

    private fun checkEndGame() {
        if (challengeId.isBlank()) {
            logStep("checkEndGame skipped: challengeId blank")
            return
        }

        logStep("checkEndGame started")

        challengePlayersRef.addListenerForSingleValueEvent(object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                var allDone = true

                snapshot.children.forEach { child ->
                    val hp = child.child("hp").getValue(Int::class.java) ?: 0
                    val finished = child.child("isFinished").getValue(Boolean::class.java) ?: false
                    val pid = child.key ?: "unknown"

                    logStep("End check -> pid=$pid, hp=$hp, finished=$finished")

                    if (hp > 0 && !finished) {
                        allDone = false
                    }
                }

                if (allDone) {
                    logStep("All players done -> calculating winner")
                    calculateFinalWinner(snapshot)
                } else {
                    logStep("Not everyone finished yet")
                }
            }

            override fun onCancelled(error: DatabaseError) {
                logError("checkEndGame cancelled", error.toException())
            }
        })
    }

    private fun calculateFinalWinner(snapshot: DataSnapshot) {
        logStep("calculateFinalWinner started")

        var topPower = -1
        var winnerId = ""

        snapshot.children.forEach { child ->
            val score = child.child("score").getValue(Int::class.java) ?: 0
            val hp = child.child("hp").getValue(Int::class.java) ?: 0
            val pid = child.key ?: "unknown"
            val power = (score * 10) + hp

            logStep("Winner calc -> pid=$pid, score=$score, hp=$hp, power=$power")

            if (power > topPower) {
                topPower = power
                winnerId = pid
            }
        }

        logStep("Winner calculated -> winnerId=$winnerId, topPower=$topPower")
        showResult(winnerId == userId.toString())
    }

    private fun showResult(win: Boolean) {
        if (isGameOverHandled) {
            logStep("showResult ignored: already handled")
            return
        }

        isGameOverHandled = true
        testTimer?.cancel()

        logStep("showResult -> win=$win")

        if (this::challengePlayersRef.isInitialized && challengeId.isNotBlank()) {
            val myUid = userId.toString()
            challengePlayersRef.child(myUid).child("hp")
                .setValue(if (win) currentHp else 0)
                .addOnSuccessListener { logStep("Final HP write complete for user=$myUid") }
                .addOnFailureListener { e -> logError("Final HP write failed", e) }
        }

        AlertDialog.Builder(this)
            .setTitle(if (win) "VICTORY! 🏆" else "DEFEAT! 💀")
            .setMessage(
                if (win) "You are the last doctor standing!"
                else "You have been eliminated from the battle."
            )
            .setCancelable(false)
            .setPositiveButton("View Leaderboard") { _, _ ->
                logStep("Result dialog positive button clicked")
                finalizeChallenge(win)
            }
            .show()
    }

    private fun finalizeChallenge(won: Boolean) {
        logStep("finalizeChallenge called -> won=$won")

        if (this::challengePlayersRef.isInitialized) {
            healthListener?.let {
                challengePlayersRef.removeEventListener(it)
                logStep("Removed health listener")
            }
            healthListener = null
        }

        if (this::questionOrderRef.isInitialized) {
            sharedQuestionListener?.let {
                questionOrderRef.removeEventListener(it)
                logStep("Removed shared question listener")
            }
            sharedQuestionListener = null
        }

        if (this::challengeActionRef.isInitialized) {
            actionListener?.let {
                challengeActionRef.removeEventListener(it)
                logStep("Removed action listener")
            }
            actionListener = null
        }

        val url = "${BASE_URL}sync_challenge_v16_authenticated.php"
        logStep("Final sync URL -> $url")

        val req = object : StringRequest(
            Request.Method.POST,
            url,
            { response ->
                logStep("Final sync success -> $response")
                launchResultScreen(won)
            },
            { error ->
                logStep("Final sync failed -> ${error.message}")
                launchResultScreen(won)
            }
        ) {
            override fun getParams(): MutableMap<String, String> {
                return hashMapOf(
                    "challenge_id" to challengeId.toString(),
                    "user_id" to userId.toString(),
                    "finish_test" to "true",
                    "score" to myCurrentScore.toString()
                )
            }
        }

        req.retryPolicy = DefaultRetryPolicy(
            10000,
            DefaultRetryPolicy.DEFAULT_MAX_RETRIES,
            DefaultRetryPolicy.DEFAULT_BACKOFF_MULT
        )

        req.tag = FINAL_SYNC_TAG
        requestQueue.add(req)
    }

    private fun launchResultScreen(won: Boolean) {
        logStep("Launching ChallengeResultActivity")

        // Save to local history before leaving
        try {
            HistoryManager.saveHistory(
                context = this,
                mode = "CHALLENGE",
                title = "Challenge Match",
                topic = currentTopic ?: currentSubject,
                score = myCurrentScore,
                totalQuestions = allQuestionIds.size,
                correctAnswers = reviewJson.let {
                    var count = 0; for(i in 0 until it.length()) { if(it.getJSONObject(i).optInt("is_correct") == 1) count++ }; count
                },
                wrongAnswers = reviewJson.let {
                    var count = 0; for(i in 0 until it.length()) { if(it.getJSONObject(i).optInt("is_correct") == 0) count++ }; count
                },
                challengeId = challengeId
            )
        } catch (e: Exception) {
            logError("Failed to save local history", e)
        }

        val parsedChallengeId = parseChallengeIdToInt(challengeId)

        val intent = Intent(this, TopicChallengeResultActivity::class.java).apply {

            // RESULT DATA
            putExtra("WON", won)
            putExtra("USER_ID", userId)
            putExtra("FINAL_SCORE", myCurrentScore)
            putExtra("REVIEW_JSON_STR", reviewJson.toString())

            // SEND BOTH STRING + INT
            putExtra("CHALLENGE_ID", challengeId) // STRING
            putExtra("CHALLENGE_ID_INT", parsedChallengeId) // OPTIONAL SAFE INT

            // LEGACY SUPPORT
            putExtra("challenge_id", challengeId)
            putExtra("challenge_id_int", parsedChallengeId)
        }

        logStep(
            "Result Intent -> challengeId=$challengeId, " +
                    "parsed=$parsedChallengeId, userId=$userId"
        )

        startActivity(intent)
        finish()
    }

    private fun syncWithServer(userAns: String) {
        if (!isChallenge || challengeId.isBlank()) {
            logStep("syncWithServer skipped: not in challenge mode")
            return
        }

        val qId = currentQuestion?.id ?: 0
        val url = "${BASE_URL}sync_challenge_v16_authenticated.php"

        val params = hashMapOf(
            "user_id" to userId.toString(),
            "challenge_id" to challengeId,
            "question_id" to qId.toString(),
            "answer" to userAns,
            "is_correct" to if (userAns == currentQuestion?.correctAnswer) "1" else "0"
        )

        logStep("syncWithServer -> url=$url, params=$params")

        val req = object : StringRequest(
            Request.Method.POST,
            url,
            { response ->
                logStep("Server sync response -> $response")
            },
            { error ->
                logError("Server sync failed", error)
            }
        ) {
            override fun getParams(): MutableMap<String, String> = params
        }

        req.tag = VOLLEY_TAG
        requestQueue.add(req)
        logStep("Sync request queued")
    }

    private fun startTimer(millis: Long) {
        logStep("startTimer called -> millis=$millis")

        testTimer?.cancel()
        testTimer = object : CountDownTimer(millis, 1000) {
            override fun onTick(ms: Long) {
                val sec = ms / 1000
                val min = sec / 60
                val rem = sec % 60
                timerText.text = String.format(Locale.US, "%02d:%02d", min, rem)

                if (ms <= 30_000L) {
                    timerText.setTextColor(Color.parseColor("#FF1744"))
                    timerText.scaleX = 1.08f
                    timerText.scaleY = 1.08f
                } else {
                    timerText.setTextColor(Color.parseColor("#E53935"))
                    timerText.scaleX = 1.0f
                    timerText.scaleY = 1.0f
                }

                if (ms % 10000L == 0L) {
                    logStep("Timer tick -> ${timerText.text}")
                }
            }

            override fun onFinish() {
                logStep("Timer expired")
                timerText.text = "00:00"
                showResult(false)
            }
        }.start()
    }

    private fun startEndWaitTimer() {
        endWaitTimer?.cancel()
        val duration = 60_000L // 1 minute
        
        endWaitTimer = object : CountDownTimer(duration, 1000) {
            override fun onTick(millisUntilFinished: Long) {
                val seconds = millisUntilFinished / 1000
                val statusPrefix = if (currentHp <= 0) "Eliminated! 💀" else "Battle finished!"
                
                questionText.text = "$statusPrefix\n\nEnding in ${seconds}s..."
                submitBtn.text = "Waiting... (${seconds}s)"
            }

            override fun onFinish() {
                logStep("End wait timer finished forcing result")
                if (!isGameOverHandled) {
                    // If timer runs out, we force check the state one last time
                    // or just show result based on current survival
                    showResult(currentHp > 0)
                }
            }
        }.start()
    }

    private fun triggerDamageVisuals(bar: ProgressBar, isMe: Boolean) {
        logStep("triggerDamageVisuals called -> isMe=$isMe, current=${bar.progress}")

        val shake = TranslateAnimation(0f, 15f, 0f, 0f).apply {
            duration = 50
            repeatCount = 5
            repeatMode = Animation.REVERSE
        }
        bar.startAnimation(shake)

        if (isMe) {
            val vibrator = getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator.vibrate(VibrationEffect.createOneShot(120, VibrationEffect.DEFAULT_AMPLITUDE))
            } else {
                @Suppress("DEPRECATION")
                vibrator.vibrate(120)
            }

            rootLayout.setBackgroundColor(Color.argb(50, 255, 0, 0))
            Handler(Looper.getMainLooper()).postDelayed({
                rootLayout.setBackgroundColor(Color.TRANSPARENT)
            }, 120)
        }
    }

    private fun showFloatingText(text: String, color: Int) {

        val now = System.currentTimeMillis()

        // 🚫 PREVENT SAME TEXT SPAM (within 500ms)
        if (text == lastFloatingText && (now - lastShownTime) < 500) {
            logStep("Skipped duplicate floating text -> $text")
            return
        }

        lastFloatingText = text
        lastShownTime = now

        logStep("showFloatingText -> $text")

        runOnUiThread {

            val tv = TextView(this).apply {
                this.text = text
                setTextColor(color)
                textSize = 20f
                setTypeface(null, Typeface.BOLD)
                alpha = 0f   // start hidden for smooth fade
            }

            val params = FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply {
                gravity = Gravity.CENTER
            }

            rootLayout.addView(tv, params)

            // 🔥 COMBINED ANIMATION (SMOOTHER)
            val move = ObjectAnimator.ofFloat(tv, "translationY", 0f, -250f)
            val fadeIn = ObjectAnimator.ofFloat(tv, "alpha", 0f, 1f)
            val fadeOut = ObjectAnimator.ofFloat(tv, "alpha", 1f, 0f)

            fadeOut.startDelay = 700

            val set = android.animation.AnimatorSet().apply {
                playTogether(move, fadeIn, fadeOut)
                duration = 1000
            }

            set.addListener(object : AnimatorListenerAdapter() {
                override fun onAnimationEnd(animation: Animator) {
                    rootLayout.removeView(tv)
                    logStep("Floating text removed")
                }
            })

            set.start()
        }
    }

    private fun animateQuestionEntry(view: View) {
        view.alpha = 0f
        view.translationY = 24f
        view.animate()
            .alpha(1f)
            .translationY(0f)
            .setDuration(250)
            .start()
    }

    private fun animateLocalPowerButton(button: ImageButton) {
        // press_pop + wiggle combo
        button.clearAnimation()
        button.startAnimation(AnimationUtils.loadAnimation(this, R.anim.power_pop))
    }

    private fun setAnswerControlsEnabled(enabled: Boolean) {
        radioGroup.isEnabled = enabled
        optionA.isEnabled = enabled
        optionB.isEnabled = enabled
        optionC.isEnabled = enabled
        optionD.isEnabled = enabled
        optionE?.isEnabled = enabled
        submitBtn.isEnabled = enabled
        submitBtn.alpha = if (enabled) 1f else 0.65f
    }

    private fun hpColor(hp: Int): Int {
        return when {
            hp > 60 -> Color.parseColor("#4CAF50")
            hp > 30 -> Color.parseColor("#FF9800")
            else -> Color.parseColor("#F44336")
        }
    }

    private fun parseQuestionContent(text: String): ParsedQuestionContent? {
        val regex = Regex(
            """(?is)^(.*?)\bA[\)\.\:]?\s*(.*?)\s*\bB[\)\.\:]?\s*(.*?)\s*\bC[\)\.\:]?\s*(.*?)\s*\bD[\)\.\:]?\s*(.*?)(?:\s*\bE[\)\.\:]?\s*(.*?))?$"""
        )

        val match = regex.find(text) ?: return null

        val question = match.groupValues[1].trim()
        val a = match.groupValues[2].trim()
        val b = match.groupValues[3].trim()
        val c = match.groupValues[4].trim()
        val d = match.groupValues[5].trim()
        val e = match.groupValues.getOrNull(6)?.trim().orEmpty()

        return ParsedQuestionContent(
            question = question,
            optionA = a,
            optionB = b,
            optionC = c,
            optionD = d,
            optionE = e
        )
    }

    private fun addReviewEntry(
        questionId: Int,
        questionText: String,
        yourAnswer: String,
        correctAnswer: String,
        explanation: String,
        isCorrect: Boolean,
        questionImage: String
    ) {
        try {
            val obj = JSONObject().apply {
                put("question_id", questionId)
                put("question", questionText) // Adapter priority 1

                // Options (Critical for the answerToText function in the adapter)
                put("option_a", currentQuestion?.a ?: "")
                put("option_b", currentQuestion?.b ?: "")
                put("option_c", currentQuestion?.c ?: "")
                put("option_d", currentQuestion?.d ?: "")

                // Answer Logic (Adapter priority 1)
                put("selected_option", yourAnswer)
                put("correct_option", correctAnswer)

                // Boolean Logic (Handled by adapter's readBoolean)
                put("is_correct", if (isCorrect) 1 else 0)

                put("explanation", explanation)

                // Image Logic
                // The adapter prepends IMAGE_BASE_URL if it doesn't start with http
                put("image_url", questionImage)

                put("CHALLENGE_ID", challengeId)
            }
            reviewJson.put(obj)
        } catch (e: Exception) {
            logError("addReviewEntry failed", e)
        }
    }

    private fun parseChallengeIdToInt(raw: String): Int {
        return raw.toIntOrNull()
            ?: raw.removePrefix("lobby_").toIntOrNull()
            ?: 0
    }

    private fun logStep(msg: String) {
        Log.d(TAG, msg)
    }

    private fun logError(msg: String, error: Throwable? = null) {
        if (error != null) Log.e(TAG, msg, error) else Log.e(TAG, msg)
    }

    override fun onDestroy() {
        super.onDestroy()
        logStep("onDestroy called")

        testTimer?.cancel()
        endWaitTimer?.cancel()
        uiHandler.removeCallbacksAndMessages(null)

        tts?.apply {
            stop()
            shutdown()
        }

        if (this::challengePlayersRef.isInitialized) {
            healthListener?.let {
                challengePlayersRef.removeEventListener(it)
                logStep("Health listener removed in onDestroy")
            }
        }

        if (this::questionOrderRef.isInitialized) {
            sharedQuestionListener?.let {
                questionOrderRef.removeEventListener(it)
                logStep("Shared question listener removed in onDestroy")
            }
        }

        if (this::challengeActionRef.isInitialized) {
            actionListener?.let {
                challengeActionRef.removeEventListener(it)
                logStep("Action listener removed in onDestroy")
            }
        }

        requestQueue.cancelAll(VOLLEY_TAG)
        requestQueue.cancelAll(PLAYER_AVATAR_TAG)
        requestQueue.cancelAll(FINAL_SYNC_TAG)
        requestQueue.cancelAll(ACTION_TAG)
        logStep("Volley requests cancelled")
    }
}
