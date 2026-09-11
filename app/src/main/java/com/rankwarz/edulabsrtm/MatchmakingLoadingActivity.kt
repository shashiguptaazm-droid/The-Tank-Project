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
import com.google.firebase.database.*
import org.json.JSONObject

class MatchmakingLoadingActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "MATCH_LOADING_DEBUG"
        private const val BASE_URL = "https://medigyaan.xyz/Neurons/"
        private const val IMAGE_BASE_URL = "https://medigyaan.xyz/Neurons/"
    }

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

    private lateinit var database: DatabaseReference

    private var challengeId = ""
    private var userId = ""
    private var opponentId = ""

    private var userName = "You"
    private var opponentName = "Opponent"

    private var loadedCount = 0
    private var hasNavigated = false
    private var playersListener: ValueEventListener? = null

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

        database = FirebaseDatabase.getInstance().reference

        challengeId = intent.getStringExtra("CHALLENGE_ID").orEmpty()
        userId = intent.getStringExtra("USER_ID").orEmpty()

        txtStatus.text = "Connecting players..."
        progressBar.isIndeterminate = true

        setupGameLoadingBackdrop(battleVideoBg, battlePosterBg, intent.getStringExtra("SUBJECT"), intent.getStringExtra("TOPIC"))
        setupSinglePlayerUI()
        startIntroAnimation()
        waitForPlayers()
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

    private fun setupMultiplayerUI() {
        findViewById<View>(R.id.rightContainer).visibility = View.VISIBLE
        findViewById<View>(R.id.bgOpp).visibility = View.VISIBLE
        findViewById<View>(R.id.txtVS).visibility = View.VISIBLE
        findViewById<View>(R.id.guidelineCenter).visibility = View.VISIBLE

        // Reset leftContainer constraints to original (left half)
        val leftContainer = findViewById<View>(R.id.leftContainer)
        val lp = leftContainer.layoutParams as ConstraintLayout.LayoutParams
        lp.endToEnd = R.id.guidelineCenter
        leftContainer.layoutParams = lp

        // Reset bgMe constraints to left half
        val bgMeParams = bgMe.layoutParams as ConstraintLayout.LayoutParams
        bgMeParams.endToEnd = R.id.guidelineCenter
        bgMe.layoutParams = bgMeParams

        // Ensure intro animation for opponent side
        imgOpp.scaleX = 0f
        imgOpp.scaleY = 0f
        imgOpp.animate().scaleX(1f).scaleY(1f).setDuration(500).start()
    }

    private fun waitForPlayers() {
        if (challengeId.isBlank() || userId.isBlank()) {
            Log.e(TAG, "Missing challengeId or userId")
            txtStatus.text = "Missing match data"
            return
        }

        val playersRef = database.child("challenges").child(challengeId).child("players")

        playersListener = object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                if (!snapshot.exists()) return
                if (snapshot.childrenCount < 2) {
                    Log.d(TAG, "Waiting for players... count=${snapshot.childrenCount}")
                    return
                }

                var foundOpponentId = ""
                for (child in snapshot.children) {
                    val pid = child.key ?: continue
                    if (pid != userId) {
                        foundOpponentId = pid
                        break
                    }
                }

                if (foundOpponentId.isNotEmpty() && !hasNavigated) {
                    opponentId = foundOpponentId
                    Log.d(TAG, "Opponent found: $opponentId")
                    playersRef.removeEventListener(this)
                    setupMultiplayerUI()
                    loadProfiles()
                }
            }

            override fun onCancelled(error: DatabaseError) {
                Log.e(TAG, "Firebase error: ${error.message}")
                txtStatus.text = "Match error"
            }
        }

        playersRef.addValueEventListener(playersListener!!)
    }

    private fun loadProfiles() {
        txtStatus.text = "Loading players..."
        fetchPlayer(userId, isMe = true)
        fetchPlayer(opponentId, isMe = false)
    }

    private fun fetchPlayer(id: String, isMe: Boolean) {
        if (id.isBlank()) {
            onImageLoaded()
            return
        }

        val url = "${BASE_URL}get_profilev1.php?user_id=$id&viewer_id=$id"

        val request = StringRequest(
            Request.Method.GET,
            url,
            { response ->
                try {
                    Log.d(TAG, "Profile response for $id: $response")

                    val root = JSONObject(response)
                    val json = root.optJSONObject("data") ?: root

                    val name = json.optString("name", if (isMe) "You" else "Opponent")
                    val rank = json.optString("rank_title", "Aspirant")
                    var image = json.optString("photo", "").trim()

                    image = image.replace("./", "").replace("\\", "").trim()

                    val finalUrl = when {
                        image.isEmpty() || image == "null" -> null
                        image.startsWith("http") -> image
                        else -> IMAGE_BASE_URL.trimEnd('/') + "/" + image.trimStart('/')
                    }

                    val profile = PlayerProfileInfo(
                        photoUrl = finalUrl.orEmpty(),
                        rankTitle = rank,
                        name = name
                    )

                    if (isMe) {
                        userName = name
                        txtMe.text = name
                        applyProfileSide(bgMe, imgMe, imgMeBadge, txtMeRank, profile, isMe = true)
                    } else {
                        opponentName = name
                        txtOpp.text = name
                        applyProfileSide(bgOpp, imgOpp, imgOppBadge, txtOppRank, profile, isMe = false)
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Parse error for $id", e)
                    val fallback = PlayerProfileInfo(rankTitle = "Aspirant", name = if (isMe) "You" else "Opponent")
                    if (isMe) {
                        txtMe.text = fallback.name
                        applyProfileSide(bgMe, imgMe, imgMeBadge, txtMeRank, fallback, isMe = true)
                    } else {
                        txtOpp.text = fallback.name
                        applyProfileSide(bgOpp, imgOpp, imgOppBadge, txtOppRank, fallback, isMe = false)
                    }
                }
            },
            { error ->
                Log.e(TAG, "Network error for $id: ${error.message}")
                val fallback = PlayerProfileInfo(rankTitle = "Aspirant", name = if (isMe) "You" else "Opponent")
                if (isMe) {
                    txtMe.text = fallback.name
                    applyProfileSide(bgMe, imgMe, imgMeBadge, txtMeRank, fallback, isMe = true)
                } else {
                    txtOpp.text = fallback.name
                    applyProfileSide(bgOpp, imgOpp, imgOppBadge, txtOppRank, fallback, isMe = false)
                }
            }
        )

        Volley.newRequestQueue(this).add(request)
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
                override fun onLoadFailed(
                    e: GlideException?,
                    model: Any?,
                    target: Target<Drawable>,
                    isFirstResource: Boolean
                ): Boolean {
                    onImageLoaded()
                    return false
                }

                override fun onResourceReady(
                    resource: Drawable,
                    model: Any,
                    target: Target<Drawable>?,
                    dataSource: DataSource,
                    isFirstResource: Boolean
                ): Boolean {
                    onImageLoaded()
                    return false
                }
            })
            .into(view)
    }

    private fun onImageLoaded() {
        loadedCount++

        if (loadedCount >= 2 && !hasNavigated) {
            hasNavigated = true
            txtStatus.text = "Match Found!"
            animateVS()

            Handler(Looper.getMainLooper()).postDelayed({
                openGame()
            }, 2000)
        }
    }

    private fun startIntroAnimation() {
        imgMe.scaleX = 0f
        imgMe.scaleY = 0f

        imgMe.animate().scaleX(1f).scaleY(1f).setDuration(500).start()

        if (opponentId.isNotBlank()) {
            imgOpp.scaleX = 0f
            imgOpp.scaleY = 0f
            imgOpp.animate().scaleX(1f).scaleY(1f).setDuration(500).setStartDelay(200).start()
        }
    }

    private fun animateVS() {
        val vs = findViewById<TextView>(R.id.txtVS)
        vs.animate()
            .scaleX(1.2f)
            .scaleY(1.2f)
            .setDuration(300)
            .withEndAction {
                vs.animate().scaleX(1f).scaleY(1f).setDuration(200).start()
            }
            .start()
    }

    private fun openGame() {
        Log.d(TAG, "Opening Classic Game")

        val intent = Intent(this, ClassicGameActivity::class.java).apply {
            putExtra("CHALLENGE_ID", challengeId)
            putExtra("USER_ID", userId)
            putExtra("OPPONENT_ID", opponentId)
            putExtra("USER_NAME", userName)
            putExtra("OPPONENT_NAME", opponentName)
            putExtra("MODE", "CLASSIC")
            putExtra("REAL_MULTIPLAYER", true)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }

        startActivity(intent)
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
        super.onDestroy()
        if (::database.isInitialized && playersListener != null && challengeId.isNotBlank()) {
            database.child("challenges").child(challengeId).child("players")
                .removeEventListener(playersListener!!)
        }
        if (::battleVideoBg.isInitialized) {
            battleVideoBg.stopPlayback()
        }
    }
}
