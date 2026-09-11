package com.rankwarz.edulabsrtm

import android.content.Context
import android.content.Intent
import android.graphics.Matrix
import android.graphics.SurfaceTexture
import android.media.MediaPlayer
import android.os.Bundle
import android.os.CountDownTimer
import android.util.Log
import android.view.Surface
import android.view.TextureView
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.android.volley.Request
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import com.google.firebase.database.*
import com.rankwarz.edulabsrtm.ui.theme.EduLabsRTMThemeFromPreferences
import org.json.JSONObject

class MatchmakingActivity : AppCompatActivity() {

    companion object {

        private const val TAG = "MatchmakingActivity"
        private const val HOST_LOCK_TTL_MS = 20_000L
        private const val BASE_URL = "https://medigyaan.xyz/Neurons/"

        fun start(
            context: Context,
            subject: String,
            topic: String? = null,
            userId: Int? = null,
            userName: String? = null
        ) {
            val intent = Intent(context, MatchmakingActivity::class.java).apply {
                putExtra("SUBJECT", subject)
                putExtra("SELECTED_SUBJECT", subject)
                putExtra("TOPIC", topic)

                if (userId != null) {
                    putExtra("USER_ID", userId)
                }

                if (userName != null) {
                    putExtra("USER_NAME", userName)
                }
            }

            context.startActivity(intent)
        }
    }

    // ─────────────────────────────────────────────
    // DATA
    // ─────────────────────────────────────────────

    private data class QueuePlayer(
        val queueKey: String,
        val userId: String,
        val userName: String
    )

    // ─────────────────────────────────────────────
    // STATE (MUTABLE FOR COMPOSE)
    // ─────────────────────────────────────────────
    private var statusMsg by mutableStateOf("Initializing...")
    private var timerMsg by mutableStateOf("")
    private var playersListState = mutableStateListOf<QueuePlayer>()

    // ─────────────────────────────────────────────
    // FIREBASE
    // ─────────────────────────────────────────────

    private lateinit var database: DatabaseReference
    private lateinit var queueRef: DatabaseReference
    private lateinit var hostLockRef: DatabaseReference
    private lateinit var challengeRef: DatabaseReference

    // ─────────────────────────────────────────────
    // STATE
    // ─────────────────────────────────────────────

    private var queueId = ""
    private var challengeId = ""

    private var userId = 0
    private var userName = ""

    private var subject = ""
    private var topic: String? = null

    private var isHost = false
    private var isBotMatch = false

    private var opponentId = ""
    private var opponentName = ""

    private var readyDialogShown = false
    private var isLaunchingGame = false
    private var matchCreationInProgress = false

    private var matchmakingTimer: CountDownTimer? = null
    private var bgMediaPlayer: MediaPlayer? = null
    private var bgMusicPlayer: MediaPlayer? = null
    private var bgTextureView: TextureView? = null
    private var isExploding = false

    private val realPlayers = mutableListOf<QueuePlayer>()

    // ─────────────────────────────────────────────
    // LISTENERS
    // ─────────────────────────────────────────────

    private var playersListener: ValueEventListener? = null
    private var matchListener: ValueEventListener? = null
    private var readyListener: ValueEventListener? = null

    // ─────────────────────────────────────────────
    // LIFECYCLE
    // ─────────────────────────────────────────────

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        startContinuousMusic()

        setContent {
            EduLabsRTMThemeFromPreferences {
                MatchmakingScreen()
            }
        }

        val prefs = getSharedPreferences("MY_APP", Context.MODE_PRIVATE)

        val intentUserId = intent.getIntExtra("USER_ID", Int.MIN_VALUE)

        userId = if (intentUserId != Int.MIN_VALUE) {
            intentUserId
        } else {
            prefs.getInt("user_id", 0)
        }

        userName = intent.getStringExtra("USER_NAME")
            ?: prefs.getString("user_name", "") ?: ""

        subject = intent.getStringExtra("SUBJECT")
            ?.takeIf { it.isNotBlank() }
            ?: intent.getStringExtra("SELECTED_SUBJECT")
                ?.takeIf { it.isNotBlank() }
            ?: prefs.getString("selected_subject_preference", "")
            ?: ""

        topic = intent.getStringExtra("TOPIC")
            ?.takeIf { it.isNotBlank() }

        if (subject.isBlank() || userId == 0) {
            Toast.makeText(this, "Invalid Session", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        database = FirebaseDatabase.getInstance().reference

        val queuePath = buildQueuePath(subject, topic)

        queueRef = database
            .child("matchmaking_queue")
            .child(queuePath)
            .child("entries")

        hostLockRef = database
            .child("matchmaking_queue")
            .child(queuePath)
            .child("hostLock")

        fetchUserDetailsFromServer()
    }

    override fun onPause() {
        super.onPause()
        try {
            if (bgMediaPlayer?.isPlaying == true) bgMediaPlayer?.pause()
            if (bgMusicPlayer?.isPlaying == true) bgMusicPlayer?.pause()
        } catch (_: Exception) {}
    }

    override fun onResume() {
        super.onResume()
        try {
            if (bgMediaPlayer != null && bgMediaPlayer?.isPlaying == false) {
                bgMediaPlayer?.start()
            }
            if (bgMusicPlayer != null && bgMusicPlayer?.isPlaying == false) {
                bgMusicPlayer?.start()
            }
        } catch (_: Exception) {}
    }

    override fun onDestroy() {
        super.onDestroy()

        try {
            bgMediaPlayer?.stop()
            bgMediaPlayer?.release()
        } catch (_: Exception) {}
        bgMediaPlayer = null
        stopContinuousMusic()

        if (!isLaunchingGame) {
            cleanup(false, true)
        }
    }

    private fun startContinuousMusic() {
        if (bgMusicPlayer == null) {
            try {
                bgMusicPlayer = MediaPlayer.create(this, R.raw.vivaldi_winter).apply {
                    isLooping = true
                    setVolume(0.85f, 0.85f)
                    start()
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error starting continuous matchmaking music", e)
            }
        } else if (bgMusicPlayer?.isPlaying == false) {
            try {
                bgMusicPlayer?.start()
            } catch (_: Exception) {}
        }
    }

    private fun stopContinuousMusic() {
        try {
            bgMusicPlayer?.let { mp ->
                if (mp.isPlaying) {
                    mp.stop()
                }
                mp.release()
            }
        } catch (_: Exception) {}
        bgMusicPlayer = null
    }

    private fun triggerVideoReloadWithExplosion(onFinished: (() -> Unit)? = null) {
        if (isFinishing || isDestroyed || isExploding) return
        isExploding = true

        ScreenExplosionHelper.triggerExplosion(
            activity = this,
            textureView = bgTextureView,
            onMidExplosion = {
                try {
                    bgMediaPlayer?.seekTo(0)
                } catch (_: Exception) {}
            },
            onComplete = {
                isExploding = false
                try {
                    bgMediaPlayer?.start()
                } catch (_: Exception) {}
                onFinished?.invoke()
            }
        )
    }

    private fun adjustTextureAspectRatio(texture: TextureView, videoWidth: Int, videoHeight: Int) {
        if (videoWidth <= 0 || videoHeight <= 0) return
        val viewWidth = texture.width.toFloat()
        val viewHeight = texture.height.toFloat()
        if (viewWidth <= 0 || viewHeight <= 0) return

        val scaleX: Float
        val scaleY: Float
        val videoRatio = videoWidth.toFloat() / videoHeight.toFloat()
        val viewRatio = viewWidth / viewHeight

        if (viewRatio > videoRatio) {
            scaleX = 1f
            scaleY = (viewWidth / videoWidth * videoHeight) / viewHeight
        } else {
            scaleX = (viewHeight / videoHeight * videoWidth) / viewWidth
            scaleY = 1f
        }

        val matrix = Matrix()
        matrix.setScale(scaleX, scaleY, viewWidth / 2f, viewHeight / 2f)
        texture.setTransform(matrix)
    }

    // ─────────────────────────────────────────────
    // COMPOSABLE UI
    // ─────────────────────────────────────────────

    @Composable
    fun MatchmakingScreen() {
        Box(
            modifier = Modifier.fillMaxSize()
        ) {
            // Layer 1: Hardware-Accelerated Video Background during matchmaking & 30s countdown
            AndroidView(
                modifier = Modifier.fillMaxSize(),
                factory = { ctx ->
                    val textureView = TextureView(ctx)
                    bgTextureView = textureView
                    textureView.surfaceTextureListener = object : TextureView.SurfaceTextureListener {
                        override fun onSurfaceTextureAvailable(st: SurfaceTexture, width: Int, height: Int) {
                            val s = Surface(st)
                            try {
                                bgMediaPlayer?.release()
                                bgMediaPlayer = MediaPlayer().apply {
                                    setSurface(s)
                                    val afd = ctx.resources.openRawResourceFd(R.raw.dont_land_the_foot_on_books_it)
                                    setDataSource(afd.fileDescriptor, afd.startOffset, afd.length)
                                    afd.close()
                                    isLooping = false
                                    setVolume(0f, 0f)
                                    setOnPreparedListener { mp ->
                                        adjustTextureAspectRatio(textureView, mp.videoWidth, mp.videoHeight)
                                        mp.start()
                                    }
                                    setOnCompletionListener {
                                        triggerVideoReloadWithExplosion()
                                    }
                                    prepareAsync()
                                }
                            } catch (e: Exception) {
                                Log.e(TAG, "Error starting matchmaking video", e)
                            }
                        }

                        override fun onSurfaceTextureSizeChanged(st: SurfaceTexture, width: Int, height: Int) {
                            bgMediaPlayer?.let { mp ->
                                adjustTextureAspectRatio(textureView, mp.videoWidth, mp.videoHeight)
                            }
                        }

                        override fun onSurfaceTextureDestroyed(st: SurfaceTexture): Boolean {
                            try {
                                bgMediaPlayer?.stop()
                                bgMediaPlayer?.release()
                            } catch (_: Exception) {}
                            bgMediaPlayer = null
                            bgTextureView = null
                            return true
                        }

                        override fun onSurfaceTextureUpdated(st: SurfaceTexture) {}
                    }
                    textureView
                }
            )

            // Layer 2: Semi-transparent dark scrim overlay for contrast & readability
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(
                        Brush.verticalGradient(
                            colors = listOf(
                                Color(0xCC050816),
                                Color(0x990A1028),
                                Color(0xE6050816)
                            )
                        )
                    )
            )

            // Layer 3: Foreground Content & Countdown UI
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                Text(
                    text = "Matchmaking",
                    fontSize = 28.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = statusMsg,
                    color = Color(0xFF00E5FF),
                    fontSize = 16.sp,
                    fontWeight = FontWeight.SemiBold
                )

                Spacer(modifier = Modifier.height(32.dp))

                if (timerMsg.isNotEmpty()) {
                    Text(
                        text = timerMsg,
                        fontSize = 24.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFFFFD54F)
                    )
                }

                Spacer(modifier = Modifier.height(32.dp))

                Text(
                    text = "Players in Lobby:",
                    color = Color.White,
                    fontWeight = FontWeight.Bold
                )
                LazyColumn(modifier = Modifier.heightIn(max = 200.dp)) {
                    items(playersListState) { player ->
                        Text(
                            text = "• ${player.userName}",
                            color = Color(0xFF00E5FF),
                            fontWeight = FontWeight.Medium,
                            modifier = Modifier.padding(vertical = 4.dp)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(48.dp))

                Button(
                    onClick = {
                        cleanup(true, true)
                        finish()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFD32F2F))
                ) {
                    Text("Cancel Search", color = Color.White, fontWeight = FontWeight.Bold)
                }
            }
        }
    }

    // ─────────────────────────────────────────────
    // PROFILE
    // ─────────────────────────────────────────────

    private fun fetchUserDetailsFromServer() {
        statusMsg = "Syncing profile..."

        val url =
            "${BASE_URL}get_profilev1.php?user_id=$userId&viewer_id=$userId"

        val request = StringRequest(
            Request.Method.GET,
            url,
            { response ->

                try {

                    val root = JSONObject(response)
                    val data = root.optJSONObject("data") ?: root

                    val fetchedName = data.optString("name", "")

                    if (fetchedName.isNotBlank()) {
                        userName = fetchedName
                    }

                } catch (e: Exception) {
                    Log.e(TAG, "Profile parse failed", e)
                }

                enterQueue()

            },
            {
                enterQueue()
            }
        )

        Volley.newRequestQueue(this).add(request)
    }

    // ─────────────────────────────────────────────
    // QUEUE
    // ─────────────────────────────────────────────

    private fun buildQueuePath(
        subject: String,
        topic: String?
    ): String {

        val cleanSubject = sanitizeKey(subject)

        return if (topic.isNullOrBlank()) {
            cleanSubject
        } else {
            "${cleanSubject}_${sanitizeKey(topic)}"
        }
    }

    private fun sanitizeKey(value: String): String {
        return value
            .trim()
            .lowercase()
            .replace(Regex("[.#$\\[\\]/]"), "_")
            .replace(Regex("\\s+"), "_")
    }

    private fun enterQueue() {
        statusMsg = "Joining Queue..."

        queueId = "${userId}_${System.currentTimeMillis()}"

        val entry = mapOf(
            "userId" to userId.toString(),
            "userName" to userName,
            "subject" to subject,
            "topic" to (topic ?: ""),
            "timestamp" to System.currentTimeMillis(),
            "status" to "waiting",
            "challengeId" to ""
        )

        queueRef.child(queueId)
            .setValue(entry)
            .addOnSuccessListener {

                queueRef.child(queueId)
                    .onDisconnect()
                    .removeValue()

                claimHostRole()
            }
            .addOnFailureListener {

                Toast.makeText(
                    this,
                    "Queue connection failed",
                    Toast.LENGTH_SHORT
                ).show()

                finish()
            }
    }

    // ─────────────────────────────────────────────
    // HOST LOCK
    // ─────────────────────────────────────────────

    private fun claimHostRole() {

        hostLockRef.runTransaction(object : Transaction.Handler {

            override fun doTransaction(
                currentData: MutableData
            ): Transaction.Result {

                val now = System.currentTimeMillis()

                val existing = currentData.value as? Map<*, *>

                val createdAt =
                    (existing?.get("createdAt") as? Number)
                        ?.toLong() ?: 0L

                return if (
                    currentData.value == null ||
                    (now - createdAt) > HOST_LOCK_TTL_MS
                ) {

                    currentData.value = mapOf(
                        "queueId" to queueId,
                        "userId" to userId.toString(),
                        "userName" to userName,
                        "createdAt" to now
                    )

                    Transaction.success(currentData)

                } else {

                    Transaction.abort()
                }
            }

            override fun onComplete(
                error: DatabaseError?,
                committed: Boolean,
                snapshot: DataSnapshot?
            ) {

                if (error != null) {
                    finish()
                    return
                }

                isHost = committed

                if (isHost) {

                    hostLockRef.onDisconnect().removeValue()
                    statusMsg = "Waiting for players..."

                    realPlayers.clear()
                    val me = QueuePlayer(queueId, userId.toString(), userName)
                    realPlayers.add(me)

                    playersListState.clear()
                    playersListState.add(me)

                    updatePlayersList()

                    startHostTimer()

                    listenForPlayers()

                } else {
                    statusMsg = "Searching for match..."

                    listenForMatch()
                }
            }
        })
    }

    // ─────────────────────────────────────────────
    // HOST FLOW
    // ─────────────────────────────────────────────

    private fun startHostTimer() {

        matchmakingTimer?.cancel()

        matchmakingTimer = object : CountDownTimer(30000, 1000) {

            override fun onTick(ms: Long) {
                timerMsg = "Starting in: ${ms / 1000}s"
            }

            override fun onFinish() {

                if (isHost && !matchCreationInProgress) {
                    createGameWithPlayers()
                }
            }

        }.start()
    }

    private fun listenForPlayers() {

        playersListener?.let {
            queueRef.removeEventListener(it)
        }

        playersListener = object : ValueEventListener {

            override fun onDataChange(snapshot: DataSnapshot) {

                if (!isHost || matchCreationInProgress) {
                    return
                }

                val updated = mutableListOf(
                    QueuePlayer(
                        queueId,
                        userId.toString(),
                        userName
                    )
                )

                for (child in snapshot.children) {

                    if (child.key == queueId) continue

                    val status = child
                        .child("status")
                        .getValue(String::class.java)

                    if (status == "waiting") {

                        val uid = child
                            .child("userId")
                            .getValue(String::class.java)
                            ?: continue

                        val name = child
                            .child("userName")
                            .getValue(String::class.java)
                            ?: "Player"

                        updated.add(
                            QueuePlayer(
                                child.key!!,
                                uid,
                                name
                            )
                        )
                    }
                }

                realPlayers.clear()
                realPlayers.addAll(updated)

                playersListState.clear()
                playersListState.addAll(updated)

                updatePlayersList()

                if (realPlayers.size >= 2) {

                    matchmakingTimer?.cancel()

                    createGameWithPlayers()
                }
            }

            override fun onCancelled(error: DatabaseError) {
            }
        }

        queueRef.addValueEventListener(playersListener!!)
    }

    private fun updatePlayersList() {
        // Note: playersListState is already updated in listenForPlayers
    }

    private fun createGameWithPlayers() {

        if (matchCreationInProgress || challengeId.isNotBlank()) {
            return
        }

        matchCreationInProgress = true

        playersListener?.let {
            queueRef.removeEventListener(it)
        }

        playersListener = null

        challengeId = "pvp_${System.currentTimeMillis()}"

        challengeRef = database
            .child("challenges")
            .child(challengeId)

        isBotMatch = realPlayers.size < 2

        val playersData = mutableMapOf<String, Any>()

        realPlayers.forEach { player ->

            playersData[player.userId] = mapOf(
                "name" to player.userName,
                "hp" to 100,
                "score" to 0,
                "isFinished" to false,
                "isBot" to false
            )
        }

        if (isBotMatch) {

            val botNames =
                ClassicGameActivity.BOT_NAME_POOL
                    .shuffled()
                    .take(2)

            botNames.forEachIndexed { index, botName ->

                playersData["BOT_$index"] = mapOf(
                    "name" to botName,
                    "hp" to 100,
                    "score" to 0,
                    "isFinished" to false,
                    "isBot" to true
                )
            }
        }

        val challengeData = mapOf(
            "status" to "creating",
            "subject" to subject,
            "topic" to (topic ?: ""),
            "hostId" to userId.toString(),
            "isBotMatch" to isBotMatch
        )

        challengeRef.setValue(challengeData)
            .addOnSuccessListener {

                challengeRef.child("players")
                    .setValue(playersData)
                    .addOnSuccessListener {

                        challengeRef.child("status")
                            .setValue("ready")
                            .addOnSuccessListener {

                                markQueuePlayersMatched()
                            }
                    }
            }
    }

    private fun markQueuePlayersMatched() {

        val updates = hashMapOf<String, Any>()

        realPlayers.forEach { player ->

            val path =
                "matchmaking_queue/${
                    buildQueuePath(subject, topic)
                }/entries/${player.queueKey}"

            updates["$path/status"] = "matched"
            updates["$path/challengeId"] = challengeId
        }

        database.updateChildren(updates)
            .addOnSuccessListener {

                resolveOpponentFromChallenge {
                    showMatchReadyDialog()
                }
            }
    }

    // ─────────────────────────────────────────────
    // GUEST FLOW
    // ─────────────────────────────────────────────

    private fun listenForMatch() {

        matchListener?.let {
            queueRef.removeEventListener(it)
        }

        matchListener = object : ValueEventListener {

            override fun onDataChange(snapshot: DataSnapshot) {

                val myEntry = snapshot.child(queueId)

                val status = myEntry
                    .child("status")
                    .getValue(String::class.java)

                val cid = myEntry
                    .child("challengeId")
                    .getValue(String::class.java)

                if (status == "matched" && !cid.isNullOrBlank()) {

                    challengeId = cid

                    queueRef.removeEventListener(this)

                    waitForChallengeReady()
                }
            }

            override fun onCancelled(error: DatabaseError) {
            }
        }

        queueRef.addValueEventListener(matchListener!!)
    }

    private fun waitForChallengeReady() {

        challengeRef = database
            .child("challenges")
            .child(challengeId)

        challengeRef.get()
            .addOnSuccessListener { snap ->

                if (
                    snap.child("status")
                        .getValue(String::class.java) == "ready"
                ) {

                    resolveOpponentFromChallenge {
                        showMatchReadyDialog()
                    }

                    return@addOnSuccessListener
                }

                readyListener?.let {
                    challengeRef.removeEventListener(it)
                }

                readyListener = object : ValueEventListener {

                    override fun onDataChange(snapshot: DataSnapshot) {

                        if (
                            snapshot.child("status")
                                .getValue(String::class.java) == "ready"
                        ) {

                            challengeRef.removeEventListener(this)

                            resolveOpponentFromChallenge {
                                showMatchReadyDialog()
                            }
                        }
                    }

                    override fun onCancelled(error: DatabaseError) {
                    }
                }

                challengeRef.addValueEventListener(readyListener!!)
            }
    }

    // ─────────────────────────────────────────────
    // READY
    // ─────────────────────────────────────────────

    private fun resolveOpponentFromChallenge(
        onDone: () -> Unit
    ) {

        database.child("challenges")
            .child(challengeId)
            .child("players")
            .get()
            .addOnSuccessListener { snap ->

                for (child in snap.children) {

                    if (child.key != userId.toString()) {

                        opponentId = child.key ?: ""

                        opponentName = child
                            .child("name")
                            .getValue(String::class.java)
                            ?: "Opponent"

                        break
                    }
                }

                onDone()
            }
            .addOnFailureListener {
                onDone()
            }
    }

    private fun showMatchReadyDialog() {

        if (
            readyDialogShown ||
            isFinishing ||
            isLaunchingGame
        ) {
            return
        }

        readyDialogShown = true

        runOnUiThread {

            AlertDialog.Builder(this)
                .setTitle("⚔ Match Ready!")
                .setMessage(
                    "Opponent Found:\n$opponentName"
                )
                .setCancelable(false)
                .setPositiveButton("Fight!") { _, _ ->
                    launchGame()
                }
                .setNegativeButton("Cancel") { _, _ ->
                    cleanup(true, true)
                    finish()
                }
                .show()
        }
    }

    // ─────────────────────────────────────────────
    // LAUNCH GAME
    // ─────────────────────────────────────────────

    private fun launchGame() {

        if (isLaunchingGame) {
            return
        }

        isLaunchingGame = true

        clearMyQueueAndLock()

        val targetIntent = if (!isBotMatch) {
            Intent(
                this,
                TopicLoadingActivity::class.java
            ).apply {
                // Multiplayer
                putExtra("REAL_MULTIPLAYER", true)
                putExtra("IS_CHALLENGE", true)

                // IMPORTANT HOST FLAGS
                putExtra("IS_HOST", isHost)
                putExtra("is_host", isHost)
                putExtra("IS_CREATOR", isHost)

                // Challenge
                putExtra("CHALLENGE_ID", challengeId)

                // Quiz
                putExtra("QUIZ_TYPE", "TOPIC")
                putExtra("MODE", "CHALLENGE")

                // Subject / Topic
                putExtra("SUBJECT", subject)
                putExtra("TOPIC", topic ?: "")

                // Players
                putExtra("USER_ID", userId)
                putExtra("USER_NAME", userName)

                putExtra("OPPONENT_ID", opponentId)
                putExtra("OPPONENT_NAME", opponentName)
            }
        } else {
            // BOT MATCH (Now also goes through Loading Screen)
            Intent(
                this,
                TopicLoadingActivity::class.java
            ).apply {
                putExtra("CHALLENGE_ID", challengeId)
                putExtra("USER_ID", userId.toString())
                putExtra("USER_NAME", userName)
                putExtra("IS_HOST", isHost)
                putExtra("IS_CHALLENGE", true)
                putExtra("REAL_MULTIPLAYER", false)
                putExtra("MODE", "CLASSIC")
                putExtra("SUBJECT", subject)
                putExtra("TOPIC", topic ?: "")
                putExtra("OPPONENT_ID", "BOT_ID")
                putExtra("OPPONENT_NAME", opponentName)
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            }
        }

        stopContinuousMusic()
        ScreenExplosionHelper.triggerExplosion(
            activity = this,
            textureView = bgTextureView
        ) {
            startActivity(targetIntent)
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
            finish()
        }
    }

    // ─────────────────────────────────────────────
    // CLEANUP
    // ─────────────────────────────────────────────

    private fun clearMyQueueAndLock() {

        if (queueId.isNotBlank()) {
            queueRef.child(queueId).removeValue()
        }

        if (isHost) {
            hostLockRef.removeValue()
        }
    }

    private fun cleanup(
        removeChallenge: Boolean,
        removeQueueEntry: Boolean
    ) {
        stopContinuousMusic()

        matchmakingTimer?.cancel()
        matchmakingTimer = null

        playersListener?.let {
            queueRef.removeEventListener(it)
        }

        matchListener?.let {
            queueRef.removeEventListener(it)
        }

        if (::challengeRef.isInitialized) {

            readyListener?.let {
                challengeRef.removeEventListener(it)
            }
        }

        if (removeQueueEntry && queueId.isNotBlank()) {
            queueRef.child(queueId).removeValue()
        }

        if (
            removeChallenge &&
            isHost &&
            challengeId.isNotBlank()
        ) {

            database.child("challenges")
                .child(challengeId)
                .removeValue()

            hostLockRef.removeValue()
        }
    }
}
