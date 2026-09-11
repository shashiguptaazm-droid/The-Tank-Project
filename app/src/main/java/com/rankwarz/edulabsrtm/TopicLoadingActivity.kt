package com.rankwarz.edulabsrtm

import android.content.Intent
import android.graphics.drawable.Drawable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.View
import android.widget.ImageView
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.VideoView
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout
import com.android.volley.Request
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import com.bumptech.glide.Glide
import com.bumptech.glide.load.DataSource
import com.bumptech.glide.load.engine.GlideException
import com.bumptech.glide.request.RequestListener
import com.bumptech.glide.request.target.Target
import org.json.JSONObject

// FIXED: Renamed class to match the filename and Lobby call
class TopicLoadingActivity : AppCompatActivity() {

    // FIXED: Changed TAG so you can see "TOPIC_LOADING_DEBUG" in Logcat
    private val TAG = "TOPIC_LOADING_DEBUG"

    private lateinit var imgMe: ImageView
    private lateinit var imgOpp: ImageView
    private lateinit var bgMe: ImageView
    private lateinit var bgOpp: ImageView
    private lateinit var imgMeBadge: ImageView
    private lateinit var imgOppBadge: ImageView
    private lateinit var txtMe: TextView
    private lateinit var txtOpp: TextView
    private lateinit var txtMeRank: TextView
    private lateinit var txtOppRank: TextView
    private lateinit var txtStatus: TextView
    private lateinit var progressBar: ProgressBar
    private lateinit var battleVideoBg: VideoView
    private lateinit var battlePosterBg: ImageView

    private var challengeId = ""
    private var userId = ""
    private var opponentId = ""

    private var uniqueId = 0
    private var quizType = ""
    private var isCreator = false

    private var subject = ""
    private var topic = ""

    private val playerProfileCache = HashMap<String, PlayerProfileInfo>()

    private val BASE_URL = "https://medigyaan.xyz/Neurons/"
    private val IMAGE_BASE_URL = "https://medigyaan.xyz/Neurons/"

    private var loadedCount = 0
    private var hasNavigated = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_loading)

        Log.d(TAG, "TopicLoadingActivity STARTED")

        bgMe = findViewById(R.id.bgMe)
        bgOpp = findViewById(R.id.bgOpp)
        imgMe = findViewById(R.id.imgMe)
        imgOpp = findViewById(R.id.imgOpp)
        imgMeBadge = findViewById(R.id.imgMeBadge)
        imgOppBadge = findViewById(R.id.imgOppBadge)
        txtMe = findViewById(R.id.txtMe)
        txtOpp = findViewById(R.id.txtOpponent)
        txtMeRank = findViewById(R.id.txtMeRank)
        txtOppRank = findViewById(R.id.txtOpponentRank)
        txtStatus = findViewById(R.id.txtStatus)
        progressBar = findViewById(R.id.progressBar)
        battleVideoBg = findViewById(R.id.battleVideoBg)
        battlePosterBg = findViewById(R.id.battlePosterBg)

        challengeId = intent.getStringExtra("CHALLENGE_ID") ?: ""
        val rawUserId = intent.extras?.get("USER_ID")
        userId = rawUserId?.toString() ?: ""
        opponentId = intent.getStringExtra("OPPONENT_ID") ?: ""

        uniqueId = intent.getIntExtra("UNIQUE_ID", 0)
        quizType = intent.getStringExtra("QUIZ_TYPE") ?: "TOPIC"
        isCreator = intent.getBooleanExtra("IS_CREATOR", false)

        subject = intent.getStringExtra("SUBJECT") ?: ""
        topic = intent.getStringExtra("TOPIC") ?: ""

        Log.d(TAG, "Data Received -> challengeId=$challengeId | subject=$subject | topic=$topic")

        setupGameLoadingBackdrop(battleVideoBg, battlePosterBg, subject, topic)
        txtMe.text = "YOU"
        txtOpp.text = "Opponent"
        txtStatus.text = "Initializing Battle..."

        if (opponentId.isBlank()) {
            setupSinglePlayerUI()
        }

        startIntroAnimation()

        // Load profiles
        fetchPlayerProfile(userId, "YOU") { profile ->
            txtMe.text = profile.name.ifBlank { "YOU" }
            applyProfileSide(bgMe, imgMe, imgMeBadge, txtMeRank, profile, isMe = true)
        }

        if (opponentId.isNotBlank()) {
            fetchPlayerProfile(opponentId, "Opponent") { profile ->
                txtOpp.text = profile.name.ifBlank { "Opponent" }
                applyProfileSide(bgOpp, imgOpp, imgOppBadge, txtOppRank, profile, isMe = false)
            }
        }
    }

    private fun setupSinglePlayerUI() {
        findViewById<View>(R.id.rightContainer).visibility = View.GONE
        findViewById<View>(R.id.bgOpp).visibility = View.GONE
        findViewById<View>(R.id.txtVS).visibility = View.GONE
        findViewById<View>(R.id.guidelineCenter).visibility = View.GONE

        // Re-center leftContainer
        val leftContainer = findViewById<View>(R.id.leftContainer)
        val lp = leftContainer.layoutParams as ConstraintLayout.LayoutParams
        lp.endToEnd = ConstraintLayout.LayoutParams.PARENT_ID
        leftContainer.layoutParams = lp

        // Expand bgMe to full screen
        val bgMeParams = bgMe.layoutParams as ConstraintLayout.LayoutParams
        bgMeParams.endToEnd = ConstraintLayout.LayoutParams.PARENT_ID
        bgMe.layoutParams = bgMeParams
    }

    private fun fetchPlayerProfile(userId: String, fallbackName: String, callback: (PlayerProfileInfo) -> Unit) {
        if (userId.isEmpty()) {
            callback(PlayerProfileInfo(rankTitle = "Aspirant", name = fallbackName))
            return
        }

        val cached = playerProfileCache[userId]
        if (cached != null) {
            callback(cached)
        } else {
            val url = "${BASE_URL}get_profilev1.php?user_id=$userId&viewer_id=$userId"
            val request = StringRequest(
                Request.Method.GET,
                url,
                { response ->
                    try {
                        val root = JSONObject(response)
                        val json = root.optJSONObject("data") ?: root
                        val name = json.optString("name", fallbackName).ifBlank { fallbackName }
                        val rank = json.optString("rank_title", "Aspirant").ifBlank { "Aspirant" }
                        var image = json.optString("photo", "").trim()
                        image = image.replace("./", "").replace("\\", "")

                        val finalUrl = when {
                            image.isEmpty() || image == "null" -> ""
                            image.startsWith("http") -> image
                            else -> IMAGE_BASE_URL.trimEnd('/') + "/" + image.trimStart('/')
                        }
                        val profile = PlayerProfileInfo(photoUrl = finalUrl, rankTitle = rank, name = name)
                        playerProfileCache[userId] = profile
                        callback(profile)
                    } catch (e: Exception) {
                        callback(PlayerProfileInfo(rankTitle = "Aspirant", name = fallbackName))
                    }
                },
                {
                    callback(PlayerProfileInfo(rankTitle = "Aspirant", name = fallbackName))
                }
            )
            Volley.newRequestQueue(this).add(request)
        }
    }

    private fun applyProfileSide(
        bgView: ImageView,
        photoView: ImageView,
        badgeView: ImageView,
        rankTextView: TextView,
        profile: PlayerProfileInfo,
        isMe: Boolean = false
    ) {
        val rankInfo = getRankInfo(profile.rankTitle.ifBlank { "Aspirant" })
        bgView.setImageResource(rankInfo.drawable)
        bgView.alpha = 0.35f
        badgeView.setImageResource(rankInfo.drawable)
        rankTextView.text = rankInfo.title
        if (isMe) {
            AvatarManager.loadAvatar(this, photoView, isMe = true)
            onImageLoaded()
        } else {
            loadImage(photoView, profile.photoUrl.takeIf { it.isNotBlank() }, profile.name)
        }
    }

    private fun loadImage(view: ImageView, url: String?, fallbackName: String? = null) {
        val fallbackRes = AvatarManager.getAvatarForIdentifier(fallbackName)
        Glide.with(this)
            .load(url)
            .circleCrop()
            .placeholder(fallbackRes)
            .error(fallbackRes)
            .listener(object : RequestListener<android.graphics.drawable.Drawable> {
                override fun onLoadFailed(e: GlideException?, model: Any?, target: Target<Drawable>, isFirstResource: Boolean): Boolean {
                    onImageLoaded()
                    return false
                }
                override fun onResourceReady(resource: Drawable, model: Any, target: Target<Drawable>?, dataSource: DataSource, isFirstResource: Boolean): Boolean {
                    onImageLoaded()
                    return false
                }
            })
            .into(view)
    }

    private fun onImageLoaded() {
        loadedCount++
        val targetCount = if (opponentId.isBlank()) 1 else 2
        if (loadedCount >= targetCount && !hasNavigated) {
            hasNavigated = true
            txtStatus.text = if (opponentId.isBlank()) "Entering Topic Challenge..." else "Ready to Battle!"
            if (opponentId.isNotBlank()) {
                animateVS()
            }

            Handler(Looper.getMainLooper()).postDelayed({
                openGame()
            }, if (opponentId.isBlank()) 1500 else 2500)
        }
    }

    private fun startIntroAnimation() {
        imgMe.scaleX = 0f; imgMe.scaleY = 0f
        imgMe.animate().scaleX(1f).scaleY(1f).setDuration(500).start()

        if (opponentId.isNotBlank()) {
            imgOpp.scaleX = 0f; imgOpp.scaleY = 0f
            imgOpp.animate().scaleX(1f).scaleY(1f).setDuration(500).setStartDelay(200).start()
        }
    }

    private fun animateVS() {
        val vs = findViewById<TextView>(R.id.txtVS)
        vs.animate().scaleX(1.2f).scaleY(1.2f).setDuration(300).withEndAction {
            vs.animate().scaleX(1f).scaleY(1f).setDuration(200).start()
        }.start()
    }

    private fun openGame() {
        val type = quizType.trim().uppercase()
        val mode = intent.getStringExtra("MODE") ?: "CHALLENGE"
        val isRealMultiplayer = intent.getBooleanExtra("REAL_MULTIPLAYER", true)

        // Determine the correct activity based on mode and multiplayer status
        val target = when {
            mode == "PRACTICE" -> SinglePlayerTestModeActivity::class.java
            mode == "CLASSIC" || !isRealMultiplayer -> ClassicGameActivity::class.java
            type == "TOPIC" || subject.isNotBlank() -> SubjectTestActivity::class.java
            else -> TestActivity::class.java
        }

        Log.d(TAG, "Navigating to Game -> ${target.simpleName}")

        val i = Intent(this, target).apply {
            putExtra("CHALLENGE_ID", challengeId)
            putExtra("USER_ID", userId.toIntOrNull() ?: 0)
            putExtra("UNIQUE_ID", uniqueId)
            putExtra("QUIZ_TYPE", quizType)
            putExtra("IS_CREATOR", isCreator)
            putExtra("SUBJECT", subject)
            putExtra("TOPIC", topic)
            putExtra("IS_CHALLENGE", mode != "PRACTICE")
            putExtra("REAL_MULTIPLAYER", isRealMultiplayer)
            putExtra("OPPONENT_ID", opponentId)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        startActivity(i)
        finish()
    }

    override fun onResume() {
        super.onResume()
        if (::battleVideoBg.isInitialized && !battleVideoBg.isPlaying) {
            battleVideoBg.start()
        }
    }

    override fun onPause() {
        if (::battleVideoBg.isInitialized) {
            battleVideoBg.pause()
        }
        super.onPause()
    }

    override fun onDestroy() {
        if (::battleVideoBg.isInitialized) {
            battleVideoBg.stopPlayback()
        }
        super.onDestroy()
    }
}
