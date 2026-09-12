package com.rankwarz.edulabsrtm

import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.WindowManager
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.bumptech.glide.Glide
import com.bumptech.glide.request.RequestOptions

class IncomingCallActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_ROOM_NAME = "room_name"
        const val EXTRA_PEER_NAME = "peer_name"
        const val EXTRA_IS_VIDEO = "is_video"
        const val EXTRA_CALLER_IMAGE = "caller_image"
        const val EXTRA_NOTIFICATION_ID = "notification_id"

        private const val TIMEOUT_MS = 45_000L

        fun createIntent(
            context: Context,
            roomName: String,
            peerName: String,
            isVideo: Boolean,
            imageUrl: String = "",
            notificationId: Int = 0
        ): Intent {
            return Intent(context, IncomingCallActivity::class.java).apply {
                putExtra(EXTRA_ROOM_NAME, roomName)
                putExtra(EXTRA_PEER_NAME, peerName)
                putExtra(EXTRA_IS_VIDEO, isVideo)
                putExtra(EXTRA_CALLER_IMAGE, imageUrl)
                putExtra(EXTRA_NOTIFICATION_ID, notificationId)
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or
                        Intent.FLAG_ACTIVITY_CLEAR_TOP or
                        Intent.FLAG_ACTIVITY_SINGLE_TOP
            }
        }
    }

    private val handler = Handler(Looper.getMainLooper())
    private val autoDismissRunnable = Runnable {
        CallRingtoneManager.stop()
        finish()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Wake screen up and show over lock screen
        wakeUpAndShowOverLockscreen()

        setContentView(R.layout.activity_incoming_call)

        val roomName = intent.getStringExtra(EXTRA_ROOM_NAME) ?: ""
        val peerName = intent.getStringExtra(EXTRA_PEER_NAME) ?: "User"
        val isVideo = intent.getBooleanExtra(EXTRA_IS_VIDEO, true)
        val callerImage = intent.getStringExtra(EXTRA_CALLER_IMAGE) ?: ""
        val notificationId = intent.getIntExtra(EXTRA_NOTIFICATION_ID, 0)

        // Start loud looping ringtone and vibration
        CallRingtoneManager.start(this)

        val txtCallType: TextView = findViewById(R.id.txtCallType)
        val txtCallerName: TextView = findViewById(R.id.txtCallerName)
        val imgCallerAvatar: ImageView = findViewById(R.id.imgCallerAvatar)
        val btnAccept: ImageButton = findViewById(R.id.btnAccept)
        val btnDecline: ImageButton = findViewById(R.id.btnDecline)

        txtCallerName.text = peerName
        txtCallType.text = if (isVideo) "📹 Incoming Video Call" else "📞 Incoming Audio Call"

        if (callerImage.isNotBlank()) {
            val fullUrl = if (callerImage.startsWith("http")) callerImage else "https://medigyaan.xyz/Neurons/" + callerImage.trimStart('/')
            Glide.with(this)
                .load(fullUrl)
                .apply(RequestOptions.circleCropTransform())
                .placeholder(R.drawable.ic_user_placeholder)
                .error(R.drawable.ic_user_placeholder)
                .into(imgCallerAvatar)
        }

        btnAccept.setOnClickListener {
            CallRingtoneManager.stop()
            cancelNotification(notificationId)
            LiveKitCallActivity.start(this, roomName, peerName, isVideo)
            finish()
        }

        btnDecline.setOnClickListener {
            CallRingtoneManager.stop()
            cancelNotification(notificationId)
            finish()
        }

        // Auto timeout if caller hangs up or unanswered
        handler.postDelayed(autoDismissRunnable, TIMEOUT_MS)
    }

    private fun cancelNotification(notificationId: Int) {
        if (notificationId != 0) {
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager
            manager?.cancel(notificationId)
        }
    }

    private fun wakeUpAndShowOverLockscreen() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true)
            setTurnScreenOn(true)
        } else {
            @Suppress("DEPRECATION")
            window.addFlags(
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
                WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON or
                WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD or
                WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
            )
        }
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
    }

    override fun onDestroy() {
        handler.removeCallbacks(autoDismissRunnable)
        CallRingtoneManager.stop()
        super.onDestroy()
    }
}