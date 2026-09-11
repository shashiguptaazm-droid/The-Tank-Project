package com.rankwarz.edulabsrtm

import android.content.Context
import android.content.Intent
import android.graphics.Matrix
import android.graphics.SurfaceTexture
import android.media.MediaPlayer
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.Surface
import android.view.TextureView
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import com.android.volley.DefaultRetryPolicy
import com.android.volley.Request
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import com.google.firebase.messaging.FirebaseMessaging
import com.tom_roush.pdfbox.android.PDFBoxResourceLoader

class SplashActivity : AppCompatActivity() {

    private val TAG = "SPLASH_VIDEO"
    private var tokenSyncCompleted = false
    private var videoFinishedOrSkipped = false
    private var hasNavigated = false
    private val handler = Handler(Looper.getMainLooper())
    private var splashTextureView: TextureView? = null
    private var mediaPlayer: MediaPlayer? = null
    private var activeSurface: Surface? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // CRITICAL: Initialize PDFBox resources at the very first entry point
        PDFBoxResourceLoader.init(applicationContext)

        // Set themed layout
        setContentView(R.layout.activity_splash)

        Log.i(TAG, "==== SPLASH STARTED ====")

        // Find views and set initial animation states
        val splashLogo = findViewById<View>(R.id.splashLogo)
        val splashTitle = findViewById<View>(R.id.splashTitle)
        val splashSubtitle = findViewById<View>(R.id.splashSubtitle)

        splashLogo?.alpha = 0f
        splashLogo?.scaleX = 0.8f
        splashLogo?.scaleY = 0.8f
        splashTitle?.alpha = 0f
        splashSubtitle?.alpha = 0f

        // Start premium entrance animation
        splashLogo?.animate()?.alpha(1f)?.scaleX(1f)?.scaleY(1f)?.setDuration(800)?.start()
        splashTitle?.animate()?.alpha(1f)?.setDuration(800)?.setStartDelay(200)?.start()
        splashSubtitle?.animate()?.alpha(0.85f)?.setDuration(800)?.setStartDelay(400)?.start()

        // Setup background intro video playback before reaching dashboard
        splashTextureView = findViewById(R.id.splashTextureView)
        val btnSkipVideo = findViewById<View>(R.id.btnSkipVideo)

        btnSkipVideo?.setOnClickListener {
            Log.i(TAG, "User clicked Skip button")
            onVideoEnd()
        }

        splashTextureView?.surfaceTextureListener = object : TextureView.SurfaceTextureListener {
            override fun onSurfaceTextureAvailable(st: SurfaceTexture, width: Int, height: Int) {
                Log.i(TAG, "SurfaceTexture available: $width x $height")
                activeSurface = Surface(st)
                startBackgroundVideo(activeSurface!!)
            }

            override fun onSurfaceTextureSizeChanged(st: SurfaceTexture, width: Int, height: Int) {
                mediaPlayer?.let { adjustAspectRatio(it.videoWidth, it.videoHeight) }
            }

            override fun onSurfaceTextureDestroyed(st: SurfaceTexture): Boolean {
                Log.i(TAG, "SurfaceTexture destroyed")
                activeSurface?.release()
                activeSurface = null
                stopVideoPlayback()
                return true
            }

            override fun onSurfaceTextureUpdated(st: SurfaceTexture) {}
        }

        if (splashTextureView?.isAvailable == true) {
            splashTextureView?.surfaceTexture?.let {
                activeSurface = Surface(it)
                startBackgroundVideo(activeSurface!!)
            }
        }

        val prefs = getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
        val userId = prefs.getInt("user_id", 0)

        // Safety timeout for FCM token sync (3.5s) to avoid stalling
        handler.postDelayed({
            if (!tokenSyncCompleted) {
                Log.w(TAG, "FCM token sync timed out, marking completed...")
                completeTokenSync()
            }
        }, 3500)

        // Sync state and run token sync
        if (userId != 0) {
            Log.d(TAG, "User session found (ID: $userId). Syncing FCM Token...")
            updateFcmTokenToServer(userId)
        } else {
            Log.d(TAG, "No session. Redirecting when video completes...")
            tokenSyncCompleted = true // No sync needed, proceed when video ends or skipped
        }
    }

    private fun startBackgroundVideo(surface: Surface) {
        try {
            stopVideoPlayback()
            mediaPlayer = MediaPlayer().apply {
                setSurface(surface)
                val afd = resources.openRawResourceFd(R.raw.dont_land_the_foot_on_books_it)
                setDataSource(afd.fileDescriptor, afd.startOffset, afd.length)
                afd.close()

                isLooping = false

                setOnPreparedListener { mp ->
                    Log.i(TAG, "MediaPlayer prepared (${mp.videoWidth}x${mp.videoHeight}, ${mp.duration}ms). Starting playback!")
                    adjustAspectRatio(mp.videoWidth, mp.videoHeight)
                    mp.start()
                }

                setOnCompletionListener {
                    Log.i(TAG, "Background video completed successfully")
                    onVideoEnd()
                }

                setOnErrorListener { _, what, extra ->
                    Log.e(TAG, "MediaPlayer error: what=$what, extra=$extra")
                    onVideoEnd()
                    true
                }

                prepareAsync()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error starting background video", e)
            onVideoEnd()
        }
    }

    private fun adjustAspectRatio(videoWidth: Int, videoHeight: Int) {
        val texture = splashTextureView ?: return
        if (videoWidth <= 0 || videoHeight <= 0) return

        val viewWidth = texture.width.toFloat()
        val viewHeight = texture.height.toFloat()
        if (viewWidth <= 0 || viewHeight <= 0) return

        val scaleX: Float
        val scaleY: Float
        val videoRatio = videoWidth.toFloat() / videoHeight.toFloat()
        val viewRatio = viewWidth / viewHeight

        // Center-crop to fill screen perfectly without black bars or distortion
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

    private fun stopVideoPlayback() {
        try {
            mediaPlayer?.let {
                if (it.isPlaying) it.stop()
                it.reset()
                it.release()
            }
        } catch (_: Exception) {}
        mediaPlayer = null
    }

    private fun updateFcmTokenToServer(userId: Int) {
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if (!task.isSuccessful) {
                Log.e(TAG, "Firebase Token Fetch Failed", task.exception)
                completeTokenSync()
                return@addOnCompleteListener
            }

            val token = task.result
            Log.d(TAG, "Token Retrieved: ${token?.take(10)}...")

            val url = "https://medigyaan.xyz/Neurons/api/update_fcmv2.php"

            val request = object : StringRequest(Request.Method.POST, url,
                { response ->
                    Log.i(TAG, "SERVER SYNC SUCCESS: $response")
                    completeTokenSync()
                },
                { error ->
                    Log.e(TAG, "SERVER SYNC ERROR: ${error.message}")
                    completeTokenSync()
                }) {

                override fun getParams(): MutableMap<String, String> {
                    val params = HashMap<String, String>()
                    params["user_id"] = userId.toString()
                    params["fcm_token"] = token ?: ""
                    return params
                }
            }

            request.retryPolicy = DefaultRetryPolicy(10000, 1, 1.0f)
            Volley.newRequestQueue(this).add(request)
        }
    }

    private fun completeTokenSync() {
        tokenSyncCompleted = true
        checkNavigationState()
    }

    private fun onVideoEnd() {
        if (videoFinishedOrSkipped) return
        videoFinishedOrSkipped = true
        ScreenExplosionHelper.triggerExplosion(
            activity = this,
            textureView = splashTextureView,
            hudTitle = "[ ENTERING THE MATRIX ]",
            hudSubtitle = "> SYSTEM OVERRIDE: NEURAL LINK ACTIVE",
            hudFootnote = "DECRYPTING CONSTRUCT CORE"
        ) {
            stopVideoPlayback()
            checkNavigationState()
        }
    }

    private fun checkNavigationState() {
        if (hasNavigated) return
        // Navigate only when video has finished/skipped AND token sync completed
        if (videoFinishedOrSkipped && tokenSyncCompleted) {
            hasNavigated = true
            val prefs = getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
            val userId = prefs.getInt("user_id", 0)

            if (!prefs.getBoolean("onboarding_complete", false)) {
                goToOnboarding()
                return
            }

            if (userId != 0) {
                val fcmSenderId = intent.getStringExtra("SENDER_ID") ?: intent.getStringExtra("sender_id")
                if (!fcmSenderId.isNullOrEmpty()) {
                    Log.w(TAG, "Notification click: routing to chat with $fcmSenderId")
                    goToChat(fcmSenderId)
                } else {
                    goToDashboard()
                }
            } else {
                goToLogin()
            }
        }
    }

    private fun goToOnboarding() {
        startActivity(Intent(this, OnboardingActivity::class.java))
        overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
        finish()
    }

    private fun goToDashboard() {
        startActivity(Intent(this, DashboardActivity::class.java))
        overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
        finish()
    }

    private fun goToChat(senderId: String) {
        val intent = Intent(this, MessengerActivity::class.java).apply {
            putExtra("SENDER_ID", senderId)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        startActivity(intent)
        overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
        finish()
    }

    private fun goToLogin() {
        startActivity(Intent(this, LoginActivity::class.java))
        overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
        finish()
    }

    override fun onPause() {
        super.onPause()
        try {
            if (mediaPlayer?.isPlaying == true) mediaPlayer?.pause()
        } catch (_: Exception) {}
    }

    override fun onResume() {
        super.onResume()
        try {
            if (!videoFinishedOrSkipped && mediaPlayer != null && mediaPlayer?.isPlaying == false) {
                mediaPlayer?.start()
            }
        } catch (_: Exception) {}
    }

    override fun onDestroy() {
        super.onDestroy()
        handler.removeCallbacksAndMessages(null)
        stopVideoPlayback()
        activeSurface?.release()
        activeSurface = null
    }
}



