package com.rankwarz.edulabsrtm

import android.content.Intent
import android.graphics.drawable.Drawable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.View
import android.view.animation.DecelerateInterpolator
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

data class PlayerProfileInfo(
    val photoUrl: String = "",
    val rankTitle: String = "",
    val level: Int = 0,
    val name: String = ""
)

class LoadingActivity : AppCompatActivity() {

    private val TAG = "LOADING_DEBUG"

    private lateinit var bgMe: ImageView
    private lateinit var bgOpp: ImageView
    private lateinit var imgMe: ImageView
    private lateinit var imgOpp: ImageView
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

    private val IMAGE_BASE_URL = "https://medigyaan.xyz/Neurons/"
    private val BASE_URL = "https://medigyaan.xyz/Neurons/"

    private val requestQueue by lazy { Volley.newRequestQueue(this) }
    private val playerProfileCache = HashMap<String, PlayerProfileInfo>()

    private var loadedCount = 0
    private var hasNavigated = false
    private val dynamicMessages = listOf(
        "Preparing battle...",
        "Loading player data...",
        "Fetching opponents...",
        "Connecting to server...",
        "Analyzing skills...",
        "Almost ready...",
        "Loading maps...",
        "Calibrating match..."
    )
    private var messageIndex = 0
    private val handler = Handler(Looper.getMainLooper())
    private val messageRunnable = object : Runnable {
        override fun run() {
            messageIndex = (messageIndex + 1) % dynamicMessages.size
            txtStatus.text = dynamicMessages[messageIndex]
            handler.postDelayed(this, 2000)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_loading)

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

        handler.post(messageRunnable)

        challengeId = intent.getStringExtra("CHALLENGE_ID") ?: ""
        userId = intent.getStringExtra("USER_ID") ?: ""
        opponentId = intent.getStringExtra("OPPONENT_ID") ?: ""

        uniqueId = intent.getIntExtra("UNIQUE_ID", 0)
        quizType = intent.getStringExtra("QUIZ_TYPE") ?: "NEET_PG"
        isCreator = intent.getBooleanExtra("IS_CREATOR", false)

        Log.d(TAG, "onCreate -> challengeId=$challengeId userId=$userId opponentId=$opponentId uniqueId=$uniqueId quizType=$quizType isCreator=$isCreator")

        setupGameLoadingBackdrop(battleVideoBg, battlePosterBg, intent.getStringExtra("SUBJECT"), intent.getStringExtra("TOPIC"))
        txtMe.text = "YOU"
        txtOpp.text = "Opponent"

        if (opponentId.isBlank()) {
            setupSinglePlayerUI()
        }

        startIntroAnimation()

        fetchPlayerProfile(userId, "YOU") { profile ->
            Log.d(TAG, "LEFT profile callback -> name=${profile.name}, rank=${profile.rankTitle}, photo=${profile.photoUrl}")
            txtMe.text = profile.name.ifBlank { "YOU" }
            applyRankBadge(imgMeBadge, txtMeRank, profile.rankTitle)
            loadProfileSide("LEFT", bgMe, imgMe, profile)
        }

        if (opponentId.isNotBlank()) {
            fetchPlayerProfile(opponentId, "Opponent") { profile ->
                Log.d(TAG, "RIGHT profile callback -> name=${profile.name}, rank=${profile.rankTitle}, photo=${profile.photoUrl}")
                txtOpp.text = profile.name.ifBlank { "Opponent" }
                applyRankBadge(imgOppBadge, txtOppRank, profile.rankTitle)
                loadProfileSide("RIGHT", bgOpp, imgOpp, profile)
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

    private fun fetchPlayerProfile(
        targetUserId: String,
        fallbackName: String,
        callback: (PlayerProfileInfo) -> Unit
    ) {
        playerProfileCache[targetUserId]?.let {
            Log.d(TAG, "fetchPlayerProfile cache hit -> targetUserId=$targetUserId name=${it.name} rank=${it.rankTitle} photo=${it.photoUrl}")
            callback(it)
            return
        }

        val url = "${BASE_URL}get_profilev1.php?user_id=$targetUserId&viewer_id=$userId"
        Log.d(TAG, "fetchPlayerProfile request -> targetUserId=$targetUserId url=$url")

        val request = StringRequest(
            Request.Method.GET,
            url,
            { response ->
                try {
                    Log.d(TAG, "fetchPlayerProfile response -> targetUserId=$targetUserId raw=$response")

                    val root = JSONObject(response)
                    val data = root.optJSONObject("data") ?: root

                    val rawPhoto = data.optString("photo", "")
                    val rawRank = data.optString("rank_title", "")
                    val rawLevel = data.optInt("level", 0)
                    val rawName = data.optString("name", fallbackName).ifBlank { fallbackName }

                    val profile = PlayerProfileInfo(
                        photoUrl = buildPhotoUrl(rawPhoto),
                        rankTitle = rawRank.trim(),
                        level = rawLevel,
                        name = rawName
                    )

                    Log.d(
                        TAG,
                        "fetchPlayerProfile parsed -> targetUserId=$targetUserId name=${profile.name} rank='${profile.rankTitle}' level=${profile.level} photo='${profile.photoUrl}'"
                    )

                    playerProfileCache[targetUserId] = profile
                    callback(profile)
                } catch (e: Exception) {
                    Log.e(TAG, "fetchPlayerProfile parse error -> targetUserId=$targetUserId", e)
                    callback(
                        PlayerProfileInfo(
                            photoUrl = "",
                            rankTitle = "",
                            level = 0,
                            name = fallbackName
                        )
                    )
                }
            },
            { error ->
                Log.e(TAG, "fetchPlayerProfile API error -> targetUserId=$targetUserId message=${error.message}", error)
                callback(
                    PlayerProfileInfo(
                        photoUrl = "",
                        rankTitle = "",
                        level = 0,
                        name = fallbackName
                    )
                )
            }
        )

        requestQueue.add(request)
    }

    private fun buildPhotoUrl(raw: String?): String {
        val cleaned = raw.orEmpty()
            .replace("./", "")
            .replace("\\", "/")
            .trim()

        val finalUrl = when {
            cleaned.isBlank() || cleaned.equals("null", ignoreCase = true) -> ""
            cleaned.startsWith("http://") || cleaned.startsWith("https://") -> cleaned
            else -> IMAGE_BASE_URL.trimEnd('/') + "/" + cleaned.trimStart('/')
        }

        Log.d(TAG, "buildPhotoUrl -> raw='$raw' cleaned='$cleaned' final='$finalUrl'")
        return finalUrl
    }

    private fun getRankAvatarRes(rank: String): Int {
        val normalized = rank.trim()
        val resId = when {
            normalized.contains("expert", ignoreCase = true) -> R.drawable.expert
            normalized.contains("scholar", ignoreCase = true) -> R.drawable.scholar
            normalized.contains("aspirant", ignoreCase = true) -> R.drawable.aspirant
            normalized.contains("grandmaster", ignoreCase = true) -> R.drawable.grandmaster



            else -> R.drawable.medigyaan_logo
        }

        Log.d(TAG, "getRankAvatarRes -> rank='$rank' resId=$resId")
        return resId
    }

    private fun applyRankBadge(badgeView: ImageView, rankTextView: TextView, rankTitle: String) {
        val rankInfo = getRankInfo(rankTitle.ifBlank { "Aspirant" })
        badgeView.setImageResource(rankInfo.drawable)
        rankTextView.text = rankInfo.title
    }

    private fun loadProfileSide(
        side: String,
        bgView: ImageView,
        photoView: ImageView,
        profile: PlayerProfileInfo
    ) {
        val bgRes = getRankAvatarRes(profile.rankTitle)
        Log.d(
            TAG,
            "loadProfileSide($side) -> applying background res=$bgRes rank='${profile.rankTitle}' name='${profile.name}'"
        )

        bgView.setImageResource(bgRes)
        bgView.alpha = 0.35f
        bgView.scaleType = ImageView.ScaleType.CENTER_CROP

        if (side == "LEFT") {
            AvatarManager.loadAvatar(this, photoView, isMe = true)
            onProfileLoaded()
            return
        }

        val photoUrl = profile.photoUrl
        if (photoUrl.isBlank()) {
            val fallbackRes = AvatarManager.getAvatarForIdentifier(profile.name)
            photoView.setImageResource(fallbackRes)
            onProfileLoaded()
            return
        }

        Log.d(TAG, "loadProfileSide($side) -> loading photoUrl=$photoUrl")

        Glide.with(this)
            .load(photoUrl)
            .circleCrop()
            .placeholder(R.drawable.medigyaan_logo)
            .error(R.drawable.medigyaan_logo)
            .listener(object : RequestListener<Drawable> {
                override fun onLoadFailed(
                    e: GlideException?,
                    model: Any?,
                    target: Target<Drawable>,
                    isFirstResource: Boolean
                ): Boolean {
                    Log.e(TAG, "loadProfileSide($side) -> photo load failed url=$photoUrl error=${e?.message}")
                    photoView.setImageResource(R.drawable.medigyaan_logo)
                    onProfileLoaded()
                    return false
                }

                override fun onResourceReady(
                    resource: Drawable,
                    model: Any,
                    target: Target<Drawable>?,
                    dataSource: DataSource,
                    isFirstResource: Boolean
                ): Boolean {
                    Log.d(TAG, "loadProfileSide($side) -> photo load success url=$photoUrl dataSource=$dataSource")
                    onProfileLoaded()
                    return false
                }
            })
            .into(photoView)
    }

    private fun onProfileLoaded() {
        loadedCount++
        Log.d(TAG, "onProfileLoaded -> loadedCount=$loadedCount hasNavigated=$hasNavigated")

        val targetCount = if (opponentId.isBlank()) 1 else 2
        if (loadedCount >= targetCount && !hasNavigated) {
            hasNavigated = true
            txtStatus.text = if (opponentId.isBlank()) "Entering Practice..." else "Match Found!"
            Log.d(TAG, "onProfileLoaded -> loading complete, starting transition")

            if (opponentId.isNotBlank()) {
                animateVS()
            }

            Handler(Looper.getMainLooper()).postDelayed({
                Log.d(TAG, "onProfileLoaded -> opening game after delay")
                openGame()
            }, if (opponentId.isBlank()) 1500 else 5000)
        }
    }

    private fun startIntroAnimation() {
        Log.d(TAG, "startIntroAnimation -> starting")

        bgMe.scaleX = 0f
        bgMe.scaleY = 0f
        bgOpp.scaleX = 0f
        bgOpp.scaleY = 0f
        imgMe.scaleX = 0f
        imgMe.scaleY = 0f
        imgOpp.scaleX = 0f
        imgOpp.scaleY = 0f

        bgMe.animate()
            .scaleX(1f)
            .scaleY(1f)
            .setDuration(500)
            .setInterpolator(DecelerateInterpolator())
            .start()

        imgMe.animate()
            .scaleX(1f)
            .scaleY(1f)
            .setDuration(500)
            .setInterpolator(DecelerateInterpolator())
            .start()

        if (opponentId.isNotBlank()) {
            bgOpp.animate()
                .scaleX(1f)
                .scaleY(1f)
                .setDuration(500)
                .setStartDelay(200)
                .setInterpolator(DecelerateInterpolator())
                .start()

            imgOpp.animate()
                .scaleX(1f)
                .scaleY(1f)
                .setDuration(500)
                .setStartDelay(200)
                .setInterpolator(DecelerateInterpolator())
                .start()
        }
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
        handler.removeCallbacks(messageRunnable)
        super.onDestroy()
    }

    private fun animateVS() {
        val vs = findViewById<TextView>(R.id.txtVS)
        Log.d(TAG, "animateVS -> starting")

        vs.scaleX = 0f
        vs.scaleY = 0f

        vs.animate()
            .scaleX(1.5f)
            .scaleY(1.5f)
            .setDuration(400)
            .withEndAction {
                Log.d(TAG, "animateVS -> bounce back")
                vs.animate().scaleX(1f).scaleY(1f).setDuration(200).start()
            }
            .start()
    }

    private fun openGame() {
        Log.d(
            TAG,
            "openGame -> challengeId=$challengeId userId=$userId uniqueId=$uniqueId quizType=$quizType isCreator=$isCreator"
        )

        val i = Intent(this, TestActivity::class.java)

        i.putExtra("CHALLENGE_ID", challengeId)
        i.putExtra("USER_ID", userId)
        i.putExtra("UNIQUE_ID", uniqueId)
        i.putExtra("QUIZ_TYPE", quizType)
        i.putExtra("IS_CREATOR", isCreator)

        i.putExtra("IS_CHALLENGE", true)
        i.putExtra("MODE", "CHALLENGE")
        i.putExtra("IS_SINGLE_PLAYER", false)

        startActivity(i)
        finish()
    }
}
