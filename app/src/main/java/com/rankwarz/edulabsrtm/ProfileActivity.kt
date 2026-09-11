package com.rankwarz.edulabsrtm

import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.os.Bundle
import android.util.Log
import android.view.View
import android.view.animation.DecelerateInterpolator
import android.widget.Button
import android.widget.ImageView
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.android.volley.Request
import com.android.volley.Response
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import com.bumptech.glide.Glide
import com.google.android.material.bottomnavigation.BottomNavigationView
import org.json.JSONObject

class ProfileActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "PROFILE_DEBUG"
        private const val PREF_NAME = "MY_APP"
        private const val KEY_USER_ID = "user_id"
        private const val KEY_FOLLOW_PREFIX = "follow_status_"
        private const val BASE_URL = "https://medigyaan.xyz/Neurons/"
        private const val PROFILE_EDIT_API = "${BASE_URL}update_profile_api.php"
    }

    private lateinit var prefs: SharedPreferences
    private lateinit var editor: SharedPreferences.Editor

    private var targetUserId = 0
    private var loggedInUserId = 0
    private var isFollowing = false
    private var profileLoaded = false

    private var tvName: TextView? = null
    private var tvBio: TextView? = null
    private var tvFollowers: TextView? = null
    private var tvFollowing: TextView? = null
    private var tvPosts: TextView? = null

    private var ivProfile: ImageView? = null
    private var ivRankBackground: ImageView? = null
    private var btnAction: Button? = null

    private var txtRankTitle: TextView? = null
    private var txtLevel: TextView? = null
    private var txtWins: TextView? = null
    private var txtStreak: TextView? = null
    private var expProgressBar: ProgressBar? = null
    private var txtLevelBadge: TextView? = null
    private var txtXpProgress: TextView? = null

    private var txtCreatedCount: TextView? = null
    private var txtSharedCount: TextView? = null
    private var txtLastAccuracy: TextView? = null
    private var txtCollegeName: TextView? = null
    private var txtStateCity: TextView? = null
    private var txtBatchYear: TextView? = null
    private var txtMobileNo: TextView? = null
    private var txtAddress: TextView? = null
    private var txtTotalAttempted: TextView? = null
    private var txtTotalCorrect: TextView? = null
    private var txtTodayStats: TextView? = null
    // AI Predicted Rank
    private var txtPredictedRank: TextView? = null
    private var txtPredictedTier: TextView? = null
    private var txtPredictedConfidence: TextView? = null
    private var predictedRankCard: View? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        log("onCreate START")

        setContentView(R.layout.activity_profile)
        log("layout loaded")

        prefs = getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        editor = prefs.edit()

        loggedInUserId = prefs.getInt(KEY_USER_ID, 0)
        targetUserId = intent.getIntExtra("TARGET_USER_ID", loggedInUserId)

        log("loggedInUserId=$loggedInUserId")
        log("targetUserId=$targetUserId")

        initViews()
        setupAppBottomNavigation(findViewById<BottomNavigationView>(R.id.bottomNavigation), R.id.nav_home)
        animateProfileEntrance()

        isFollowing = loadFollowStatus()
        updateFollowButton(btnAction)

        if (targetUserId == loggedInUserId) {
            applyLocalStatsPreview()
            UserCacheSyncer.sync(this, loggedInUserId) {
                fetchProfileDetails()
            }
        }
        fetchProfile()
    }

    override fun onResume() {
        super.onResume()
        if (profileLoaded) {
            if (targetUserId == loggedInUserId) {
                applyLocalStatsPreview()
                UserCacheSyncer.sync(this, loggedInUserId)
            }
            fetchProfile()
        }
    }

    private fun initViews() {
        log("initViews START")

        tvName = findViewById(R.id.txtProfileName)
        tvBio = findViewById(R.id.txtBio)
        tvFollowers = findViewById(R.id.txtStatFollowers)
        tvFollowing = findViewById(R.id.txtStatFollowing)
        tvPosts = findViewById(R.id.txtStatPosts)

        ivProfile = findViewById(R.id.imgProfileLarge)
        ivRankBackground = findViewById(R.id.imgRankBackground)
        btnAction = findViewById(R.id.btnProfileAction)

        txtRankTitle = findViewById(R.id.txtRankTitle)
        txtLevel = findViewById(R.id.txtLevel)
        txtWins = findViewById(R.id.txtWins)
        txtStreak = findViewById(R.id.txtStreak)
        expProgressBar = findViewById(R.id.expProgressBar)
        txtLevelBadge = findViewById(R.id.txtLevelBadge)
        txtXpProgress = findViewById(R.id.txtXpProgress)

        txtCreatedCount = findViewById(R.id.txtCreatedCount)
        txtSharedCount = findViewById(R.id.txtSharedCount)
        txtLastAccuracy = findViewById(R.id.txtLastAccuracy)
        txtCollegeName = findViewById(R.id.txtCollegeName)
        txtStateCity = findViewById(R.id.txtStateCity)
        txtBatchYear = findViewById(R.id.txtBatchYear)
        txtMobileNo = findViewById(R.id.txtMobileNo)
        txtAddress = findViewById(R.id.txtAddress)
        txtTotalAttempted = findViewById(R.id.txtTotalAttempted)
        txtTotalCorrect = findViewById(R.id.txtTotalCorrect)
        txtTodayStats = findViewById(R.id.txtTodayStats)
        // AI Predicted Rank
        txtPredictedRank = findViewById(R.id.txtPredictedRank)
        txtPredictedTier = findViewById(R.id.txtPredictedTier)
        txtPredictedConfidence = findViewById(R.id.txtPredictedConfidence)
        predictedRankCard = findViewById(R.id.predictedRankCard)

        log("initViews DONE")
    }

    private fun fetchProfile() {
        val url =
            "${BASE_URL}get_profilev1.php?user_id=$targetUserId&viewer_id=$loggedInUserId"

        log("API CALL: $url")

        val request = StringRequest(
            Request.Method.GET,
            url,
            { response ->
                log("API RESPONSE RECEIVED")
                log("RAW PROFILE RESPONSE: $response")

                try {
                    val root = JSONObject(response)
                    val json = root.optJSONObject("data") ?: root
                    log("JSON PARSED SUCCESS")
                    updateUI(json)
                    profileLoaded = true
                    fetchProfileDetails()
                    loadPredictedRankFromServer()
                } catch (e: Exception) {
                    log("JSON ERROR: ${e.message}")
                    Toast.makeText(this, "Parse error", Toast.LENGTH_SHORT).show()
                }
            },
            { error ->
                log("NETWORK ERROR: ${error.message}")
                Toast.makeText(this, "Network error", Toast.LENGTH_SHORT).show()
            }
        )

        Volley.newRequestQueue(this).add(request)
        log("Profile request queued")
    }

    private fun fetchProfileDetails() {
        val url = "$PROFILE_EDIT_API?user_id=$targetUserId&viewer_id=$loggedInUserId"
        log("DETAILS API CALL: $url")

        val request = StringRequest(
            Request.Method.GET,
            url,
            { response ->
                try {
                    val root = JSONObject(response)
                    if (root.optString("status") == "success") {
                        updateDetailsUI(root.optJSONObject("data") ?: JSONObject())
                    } else {
                        log("Details load skipped: ${root.optString("message")}")
                    }
                } catch (e: Exception) {
                    log("Details parse error: ${e.message}")
                }
            },
            { error ->
                log("Details network error: ${error.message}")
            }
        )
        Volley.newRequestQueue(this).add(request)
    }

    private fun updateDetailsUI(json: JSONObject) {
        val college = json.optString("college_name").takeUnless { it.isBlank() || it == "null" }
        val state = json.optString("state").takeUnless { it.isBlank() || it == "null" }
        val city = json.optString("city").takeUnless { it.isBlank() || it == "null" }
        val batch = json.optInt("batch_year", 0)
        val passing = json.optInt("passing_year", 0)
        val mobile = json.optString("mobile_no").takeUnless { it.isBlank() || it == "null" }
        val address = json.optString("address").takeUnless { it.isBlank() || it == "null" }

        txtCollegeName?.text = college ?: "College not added"
        txtStateCity?.text = listOfNotNull(city, state).joinToString(", ").ifBlank { "Location not added" }
        txtBatchYear?.text = when {
            batch > 0 && passing > 0 -> "$batch - $passing"
            batch > 0 -> batch.toString()
            passing > 0 -> "Passing $passing"
            else -> "-"
        }
        txtMobileNo?.text = mobile ?: "-"
        txtAddress?.apply {
            text = address.orEmpty()
            visibility = if (address.isNullOrBlank()) View.GONE else View.VISIBLE
        }

        val cache = json.optJSONObject("local_cache") ?: JSONObject()
        val attempted = cache.optInt("overall_attempted", 0)
        val correct = cache.optInt("overall_correct", 0)
        val localAccuracy = cache.optInt("overall_accuracy", 0)
        val todayAttempted = cache.optInt("today_attempted", 0)
        val todayCorrect = cache.optInt("today_correct", 0)
        val localStreak = cache.optInt("local_streak", 0)

        txtTotalAttempted?.text = attempted.toString()
        txtTotalCorrect?.text = correct.toString()
        if (attempted > 0) {
            txtLastAccuracy?.text = "$localAccuracy%"
        }
        if (localStreak > 0) {
            txtStreak?.text = localStreak.toString()
        }
        txtTodayStats?.text = "$todayCorrect/$todayAttempted today"
    }

    private fun applyLocalStatsPreview() {
        val overall = DailyStatsManager.getOverallStats(this)
        val today = DailyStatsManager.getToday(this)
        val accuracy = DailyStatsManager.calculateAccuracy(overall.first, overall.second)
        val streak = DailyStatsManager.getCurrentStreak(this)

        txtTotalAttempted?.text = overall.first.toString()
        txtTotalCorrect?.text = overall.second.toString()
        txtLastAccuracy?.text = "$accuracy%"
        txtTodayStats?.text = "${today.second}/${today.first} today"
        if (streak > 0) {
            txtStreak?.text = streak.toString()
        }
    }

    private fun updateUI(json: JSONObject) {
        log("updateUI START")

        val status = json.optString("status", "success")
        log("Profile status=$status")

        if (status.isNotBlank() && status != "success") {
            log("Profile load failed")
            Toast.makeText(this, "Failed to load profile", Toast.LENGTH_SHORT).show()
            return
        }

        val name = json.optString("name", "User")
        val bio = json.optString("bio", "")
        val photo = json.optString("photo", "")

        val followers = json.optInt("followers", 0)
        val following = json.optInt("following", 0)
        val posts = json.optInt("posts", 0)

        val localFollowState = loadFollowStatus()
        val serverFollowState = when {
            json.has("is_following") -> json.optBoolean("is_following", localFollowState)
            json.has("follow_status") -> {
                val followStatus = json.optString("follow_status", "")
                followStatus.equals("followed", ignoreCase = true) ||
                        followStatus.equals("following", ignoreCase = true) ||
                        followStatus.equals("true", ignoreCase = true)
            }
            else -> localFollowState
        }

        isFollowing = localFollowState || serverFollowState
        saveFollowStatus(isFollowing)

        val exp = json.optInt("exp", 0)
        val level = json.optInt("level", 1)
        val rank = json.optString("rank_title", "Aspirant")
        val wins = json.optInt("wins", 0)
        val streak = json.optInt("streak", 0)

        val quizzes = json.optJSONArray("quizzes")?.length() ?: 0
        val shared = json.optJSONArray("shared")?.length() ?: 0

        var accuracy = 0
        val attempts = json.optJSONArray("attempts")
        if (attempts != null && attempts.length() > 0) {
            val obj = attempts.getJSONObject(0)
            val total = obj.optInt("total_attempted", 0)
            val correct = obj.optInt("correct_attempted", 0)
            accuracy = if (total > 0) (correct * 100) / total else 0
            log("attempts parsed -> total=$total correct=$correct accuracy=$accuracy")
        } else {
            log("No attempts data found")
        }

        log("USER=$name EXP=$exp LEVEL=$level FOLLOWING=$isFollowing")

        tvName?.text = name
        tvBio?.text = bio.ifBlank { "No bio added yet." }
        tvFollowers?.text = followers.toString()
        tvFollowing?.text = following.toString()
        tvPosts?.text = posts.toString()

        txtRankTitle?.text = rank
        txtLevel?.text = "Level $level"
        txtWins?.text = wins.toString()
        txtStreak?.text = streak.toString()
        txtLevelBadge?.text = level.toString()

        txtCreatedCount?.text = quizzes.toString()
        txtSharedCount?.text = shared.toString()
        txtLastAccuracy?.text = "$accuracy%"

        val currentXp = exp % 1000
        txtXpProgress?.text = "$currentXp / 1000 XP"

        val progress = if (exp > 0) (exp % 1000) * 100 / 1000 else 0
        expProgressBar?.progress = progress
        animateProgress(expProgressBar, progress)
        log("EXP progress=$progress")

        setRankBackground(rank)
        animateRankCard()

        ivProfile?.let { imageView ->
            if (photo.isNotEmpty()) {
                val imageUrl = if (photo.startsWith("http")) {
                    photo
                } else {
                    "${BASE_URL}${photo.replace("./", "").trimStart('/')}"
                }

                log("IMAGE URL=$imageUrl")

                Glide.with(this)
                    .load(imageUrl)
                    .circleCrop()
                    .into(imageView)
            } else {
                log("No profile image found")
            }
        }

        btnAction?.let { btn ->
            if (targetUserId == loggedInUserId) {
                btn.text = "Edit Profile"
                btn.setOnClickListener {
                    log("Edit Profile clicked")
                    startActivity(Intent(this, EditProfileActivity::class.java))
                }
                log("Own profile button set")
            } else {
                updateFollowButton(btn)

                btn.setOnClickListener {
                    val newState = !isFollowing
                    log("Follow button clicked -> newState=$newState")

                    isFollowing = newState
                    updateFollowButton(btn)
                    saveFollowStatus(isFollowing)
                    sendFollowRequest(newState, btn)
                }

                log("Follow button set -> ${btn.text}")
            }
        }

        log("updateUI DONE")
    }

    private fun setRankBackground(rankTitle: String) {
        val imageView = ivRankBackground ?: findViewById(R.id.imgRankBackground)

        val drawableName = rankTitle
            .trim()
            .lowercase()
            .replace(" ", "_")

        val mappedDrawable = when {
            drawableName.contains("grandmaster") -> "grandmaster"
            drawableName.contains("scholar") -> "scholar"
            drawableName.contains("expert") -> "expert"
            drawableName.contains("legend") -> "ic_legend"
            drawableName.contains("master") -> "ic_master"
            drawableName.contains("warrior") -> "ic_warrior"
            drawableName.contains("skilled") -> "ic_skilled"
            drawableName.contains("rookie") -> "ic_rookie"
            drawableName.contains("beginner") || drawableName.contains("begginer") -> "aspirant"
            else -> drawableName.ifBlank { "aspirant" }
        }

        val resId = resources.getIdentifier(mappedDrawable, "drawable", packageName)

        if (resId != 0) {
            imageView.setImageResource(resId)
            imageView.scaleType = ImageView.ScaleType.FIT_CENTER
            imageView.setBackgroundColor(android.graphics.Color.parseColor("#101729"))
            Log.d("RANK_BG", "Loaded: $mappedDrawable")
        } else {
            imageView.setImageResource(R.drawable.aspirant)
            imageView.scaleType = ImageView.ScaleType.FIT_CENTER
            imageView.setBackgroundColor(android.graphics.Color.parseColor("#101729"))
            Log.e("RANK_BG", "Image NOT found for: $mappedDrawable")
        }
    }

    private fun animateProfileEntrance() {
        val views = listOfNotNull(
            ivProfile,
            tvName,
            tvBio,
            btnAction,
            txtRankTitle,
            expProgressBar,
            txtCreatedCount,
            txtSharedCount,
            txtLastAccuracy
        )

        views.forEachIndexed { index, view ->
            view.alpha = 0f
            view.translationY = 24f
            view.animate()
                .alpha(1f)
                .translationY(0f)
                .setInterpolator(DecelerateInterpolator())
                .setStartDelay(index * 45L)
                .setDuration(280L)
                .start()
        }

        ivProfile?.animate()
            ?.scaleX(1.06f)
            ?.scaleY(1.06f)
            ?.setStartDelay(220L)
            ?.setDuration(180L)
            ?.withEndAction {
                ivProfile?.animate()?.scaleX(1f)?.scaleY(1f)?.setDuration(180L)?.start()
            }
            ?.start()
    }

    private fun animateProgress(progressBar: ProgressBar?, progress: Int) {
        progressBar ?: return
        progressBar.progress = 0
        progressBar.animate()
            .setDuration(420L)
            .withEndAction { progressBar.progress = progress.coerceIn(0, 100) }
            .start()
    }

    private fun animateRankCard() {
        ivRankBackground?.apply {
            alpha = 0.7f
            scaleX = 1.02f
            scaleY = 1.02f
            animate()
                .alpha(1f)
                .scaleX(1f)
                .scaleY(1f)
                .setDuration(360L)
                .setInterpolator(DecelerateInterpolator())
                .start()
        }
    }

    private fun updateFollowButton(btn: Button?) {
        btn?.text = if (isFollowing) "Followed" else "Follow"
        log("BUTTON TEXT -> ${btn?.text}")
    }

    private fun sendFollowRequest(follow: Boolean, btn: Button) {
        val url = "${BASE_URL}follow_unfollow_apiv4.php"

        log("FOLLOW API URL: $url")
        log("FOLLOW ACTION: ${if (follow) "follow" else "unfollow"}")
        log("FOLLOW USER: $loggedInUserId -> TARGET: $targetUserId")

        val request = object : StringRequest(
            Request.Method.POST,
            url,
            { response ->
                log("FOLLOW RAW RESPONSE: $response")

                try {
                    val json = JSONObject(response)
                    log("FOLLOW PARSED JSON: $json")

                    val status = json.optString("status", "")
                    val action = json.optString("action", "")
                    val message = json.optString("message", "")

                    log("FOLLOW STATUS=$status | ACTION=$action | MESSAGE=$message")

                    if (status == "success") {
                        isFollowing = action.equals("followed", true) || follow
                        saveFollowStatus(isFollowing)
                        updateFollowButton(btn)
                    } else {
                        isFollowing = !follow
                        saveFollowStatus(isFollowing)
                        updateFollowButton(btn)
                        Toast.makeText(
                            this,
                            if (message.isNotBlank()) message else "Action failed",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                } catch (e: Exception) {
                    log("FOLLOW PARSE ERROR: ${e.message}")
                    isFollowing = !follow
                    saveFollowStatus(isFollowing)
                    updateFollowButton(btn)
                }
            },
            { error ->
                log("FOLLOW NETWORK ERROR: ${error.message}")
                isFollowing = !follow
                saveFollowStatus(isFollowing)
                updateFollowButton(btn)
                Toast.makeText(this, "Network error", Toast.LENGTH_SHORT).show()
            }
        ) {
            override fun getParams(): MutableMap<String, String> {
                val params = hashMapOf(
                    "user_id" to loggedInUserId.toString(),
                    "target_user_id" to targetUserId.toString(),
                    "action" to if (follow) "follow" else "unfollow"
                )
                log("FOLLOW REQUEST PARAMS: $params")
                return params
            }

            override fun getHeaders(): MutableMap<String, String> {
                val headers = hashMapOf(
                    "Content-Type" to "application/x-www-form-urlencoded"
                )
                log("FOLLOW HEADERS: $headers")
                return headers
            }
        }

        Volley.newRequestQueue(this).add(request)
        log("FOLLOW request queued")
    }

    private fun saveFollowStatus(following: Boolean) {
        val key = getFollowKey(targetUserId)
        editor.putBoolean(key, following)
        editor.apply()
        log("Saved follow status -> key=$key value=$following")
    }

    private fun loadFollowStatus(): Boolean {
        val key = getFollowKey(targetUserId)
        val saved = prefs.getBoolean(key, false)
        log("Loaded follow status -> key=$key value=$saved")
        return saved
    }

    private fun getFollowKey(userId: Int): String {
        return "$KEY_FOLLOW_PREFIX$userId"
    }

    private fun loadPredictedRankFromServer() {
        if (targetUserId == 0) return
        val url = "https://medigyaan.xyz/Neurons/api_load_predicted_rank.php?user_id=$targetUserId"
        val request = object : StringRequest(Request.Method.GET, url,
            Response.Listener<String> { response ->
                try {
                    val json = JSONObject(response)
                    if (json.optBoolean("success")) {
                        val minRank = json.optString("predicted_min_rank")
                        val maxRank = json.optString("predicted_max_rank")
                        val tier = json.optString("tier")
                        val confidence = json.optInt("confidence")
                        runOnUiThread {
                            txtPredictedRank?.text = "$minRank - $maxRank"
                            txtPredictedTier?.text = tier
                            txtPredictedConfidence?.text = "Confidence: $confidence%"
                            predictedRankCard?.visibility = View.VISIBLE
                        }
                    } else {
                        runOnUiThread { predictedRankCard?.visibility = View.GONE }
                    }
                } catch (e: Exception) {
                    runOnUiThread { predictedRankCard?.visibility = View.GONE }
                }
            },
            Response.ErrorListener { runOnUiThread { predictedRankCard?.visibility = View.GONE } }
        ) {
            override fun getHeaders() = hashMapOf(
                "X-App-Signature" to "EduLabsRTM_Secure_v1_2026",
                "Accept" to "application/json"
            )
        }
        Volley.newRequestQueue(this).add(request)
    }

    private fun log(msg: String) {
        Log.d(TAG, msg)
    }
}
