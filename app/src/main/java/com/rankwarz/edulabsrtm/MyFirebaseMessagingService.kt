package com.rankwarz.edulabsrtm

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import com.bumptech.glide.Glide
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * Service to handle FCM notifications for RankWarz EduLabs.
 * Handles Chat, Challenge Invites, and General notifications with image support.
 */
class MyFirebaseMessagingService : FirebaseMessagingService() {

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        Log.d(TAG, "--- New Message Received ---")

        if (remoteMessage.data.isNotEmpty()) {
            Log.d(TAG, "Payload Data: ${remoteMessage.data}")
        }

        val data = remoteMessage.data
        if (data.isEmpty() && remoteMessage.notification == null) return

        val type = data["type"] ?: ""
        val title = data["title"] ?: remoteMessage.notification?.title ?: "EduLabs"
        val body = data["body"] ?: remoteMessage.notification?.body ?: "New notification"
        val image = data["image"] ?: data["profile_pic"] ?: ""

        val isVideoCall = type == "video_call" || body.contains("VIDEO_CALL_INVITE:")
        val isAudioCall = type == "audio_call" || body.contains("AUDIO_CALL_INVITE:")

        when {
            isVideoCall -> sendCallNotification(data, title, body, image, isVideo = true)
            isAudioCall -> sendCallNotification(data, title, body, image, isVideo = false)
            type == "chat" -> sendChatMessage(data, title, body, image)
            type == "CHALLENGE_INVITE" -> sendChallengeInvite(data, title, body, image)
            else -> sendGeneral(title, body, image)
        }
    }

    private fun sendCallNotification(
        data: Map<String, String>,
        title: String,
        body: String,
        img: String,
        isVideo: Boolean
    ) {
        val senderId = data["sender_id"] ?: "0"
        val roomName = data["room_name"]
            ?: (if (isVideo) body.substringAfter("VIDEO_CALL_INVITE:") else body.substringAfter("AUDIO_CALL_INVITE:")).trim()
        val callerName = title.ifBlank { "Incoming Call" }

        val callIntent = Intent(this, LiveKitCallActivity::class.java).apply {
            putExtra(LiveKitCallActivity.EXTRA_ROOM_NAME, roomName)
            putExtra(LiveKitCallActivity.EXTRA_PEER_NAME, callerName)
            putExtra(LiveKitCallActivity.EXTRA_IS_VIDEO, isVideo)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }

        val displayBody = if (isVideo) "📹 Incoming Video Call (Tap to answer)" else "📞 Incoming Audio Call (Tap to answer)"
        val notificationId = (senderId.toIntOrNull() ?: 1000) + 5000

        showNotification(callerName, displayBody, callIntent, notificationId, CHANNEL_CALL, img)
    }

    private fun sendChatMessage(data: Map<String, String>, title: String, body: String, img: String) {
        val senderId = data["sender_id"] ?: "0"
        val intent = Intent(this, MessengerActivity::class.java).apply {
            putExtra("SENDER_ID", senderId)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }

        val notificationId = senderId.toIntOrNull() ?: 1001
        showNotification(title, body, intent, notificationId, CHANNEL_CHAT, img)
    }

    private fun sendChallengeInvite(data: Map<String, String>, title: String, body: String, img: String) {
        val challengeId = data["challenge_id"]?.toIntOrNull() ?: 0
        val uniqueId = data["unique_id"]?.toIntOrNull() ?: 0
        val quizType = data["quiz_type"] ?: "TEST_SERIES"
        val hostName = data["host_name"] ?: "Friend"
        val lobbyId = data["lobby_id"] ?: "lobby_$challengeId"
        val challengeText = "You have been challenged! Do you want to accept?"

        // Persist challenge data for the Widget
        val prefs = getSharedPreferences("neet_widget", Context.MODE_PRIVATE)
        prefs.edit().apply {
            putBoolean("has_challenge", true)
            putString("challenge_text", challengeText)
            putString("challenge_host_name", hostName)
            putInt("challenge_id", challengeId)
            putInt("unique_id", uniqueId)
            putString("quiz_type", quizType)
            putString("lobby_id", lobbyId)
            putLong("challenge_time", System.currentTimeMillis())
            apply()
        }

        // Update UI Components
        NeetAppWidget.forceUpdate(this)

        val intent = Intent(this, ChallengeInvitationActivity::class.java).apply {
            putExtra("CHALLENGE_ID", challengeId)
            putExtra("lobby_id", lobbyId)
            putExtra("UNIQUE_ID", uniqueId)
            putExtra("QUIZ_TYPE", quizType)
            putExtra("host_name", hostName)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }

        showNotification(
            title = title.ifBlank { "Challenge Invite" },
            body = challengeText,
            intent = intent,
            id = if (challengeId != 0) challengeId else 2001,
            channelId = CHANNEL_CHALLENGE,
            img = img
        )
    }

    private fun sendGeneral(title: String, body: String, img: String) {
        val intent = Intent(this, DashboardActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        showNotification(title, body, intent, 1001, CHANNEL_GENERAL, img)
    }

    private fun showNotification(
        title: String,
        body: String,
        intent: Intent,
        id: Int,
        channelId: String,
        img: String
    ) {
        // Android 12+ requires FLAG_IMMUTABLE
        val pendingIntent = PendingIntent.getActivity(
            this, id, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val builder = NotificationCompat.Builder(this, channelId)
            .setSmallIcon(R.drawable.ic_notification) // Ensure this exists in res/drawable
            .setContentTitle(title)
            .setContentText(body)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setContentIntent(pendingIntent)

        if (img.isNotEmpty()) {
            val url = if (img.startsWith("http")) img else IMAGE_BASE_URL + img

            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val bmp: Bitmap = Glide.with(applicationContext)
                        .asBitmap()
                        .load(url)
                        .submit()
                        .get()

                    builder.setLargeIcon(bmp)

                    if (img.contains("uploads/") || img.contains("challenge")) {
                        builder.setStyle(
                            NotificationCompat.BigPictureStyle()
                                .bigPicture(bmp)
                                .bigLargeIcon(null as Bitmap?)
                        )
                    }

                    withContext(Dispatchers.Main) {
                        dispatchNotification(id, channelId, builder)
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Image loading failed: ${e.message}")
                    withContext(Dispatchers.Main) {
                        dispatchNotification(id, channelId, builder)
                    }
                }
            }
        } else {
            dispatchNotification(id, channelId, builder)
        }
    }

    private fun dispatchNotification(id: Int, channelId: String, builder: NotificationCompat.Builder) {
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val name = when (channelId) {
                CHANNEL_CALL -> "Incoming Calls"
                CHANNEL_CHAT -> "Direct Messages"
                CHANNEL_CHALLENGE -> "Game Challenges"
                else -> "General Updates"
            }
            val channel = NotificationChannel(channelId, name, NotificationManager.IMPORTANCE_HIGH).apply {
                description = "Notifications for $name"
                enableVibration(true)
            }
            manager.createNotificationChannel(channel)
        }

        manager.notify(id, builder.build())
        Log.d(TAG, "Notification Dispatched | ID: $id | Channel: $channelId")
    }

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Log.d(TAG, "New Token Generated: $token")
        // TODO: Send token to your server
    }

    // THIS IS THE COMPANION OBJECT.
    // It must be INSIDE the class curly braces.
    companion object {
        private const val TAG = "FCM_DEBUG_LOG"
        private const val IMAGE_BASE_URL = "https://medigyaan.xyz/Neurons/"

        private const val CHANNEL_CALL = "call_channel"
        private const val CHANNEL_CHAT = "chat_channel"
        private const val CHANNEL_CHALLENGE = "challenge_channel"
        private const val CHANNEL_GENERAL = "general_channel"
    }
}