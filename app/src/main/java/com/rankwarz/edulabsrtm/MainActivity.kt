package com.rankwarz.edulabsrtm

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.android.volley.DefaultRetryPolicy
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import com.google.firebase.messaging.FirebaseMessaging
import com.tom_roush.pdfbox.android.PDFBoxResourceLoader

class MainActivity : AppCompatActivity() {

    private lateinit var prefs: SharedPreferences
    private val TAG = "FCM_DEBUG"

    // Launcher for Android 13+ Notification Permission
    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        Log.d(TAG, "Notification permission granted: $isGranted")
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // CRITICAL: Initialize PDFBox for Android
        PDFBoxResourceLoader.init(applicationContext)
        
        setContentView(R.layout.activity_main)

        prefs = getSharedPreferences("MY_APP", Context.MODE_PRIVATE)

        // Initial setup for Notifications
        createNotificationChannel()
        askNotificationPermission()

        val currentUid = prefs.getInt("user_id", 0)

        if (currentUid != 0) {
            // Check if we arrived here by clicking a notification (Background/Kill state)
            val fcmSenderId = intent.getStringExtra("SENDER_ID") ?: intent.getStringExtra("sender_id")

            if (!fcmSenderId.isNullOrEmpty()) {
                Log.d(TAG, "NOTIFICATION CLICK DETECTED: Opening chat with $fcmSenderId")
                // Sync token silently without blocking the transition to Chat
                updateFcmTokenToServer(currentUid, false)
                goToChat(fcmSenderId)
            } else {
                Log.d(TAG, "SESSION ACTIVE: Normal startup, syncing token...")
                updateFcmTokenToServer(currentUid, true)
            }
        } else {
            Log.d(TAG, "NO SESSION: Redirecting to Login")
            goToLogin()

        }
    }

    private fun askNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) !=
                PackageManager.PERMISSION_GRANTED
            ) {
                requestPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channelId = "chat_notifications" // Matches your Service channel ID
            val channelName = "Chat Messages"
            val importance = NotificationManager.IMPORTANCE_HIGH
            val channel = NotificationChannel(channelId, channelName, importance).apply {
                description = "Notifications for incoming messages"
            }
            val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }

    private fun updateFcmTokenToServer(userId: Int, shouldGoToDashboard: Boolean) {
        Log.d(TAG, "Starting FCM Sync for User: $userId")

        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if (!task.isSuccessful) {
                Log.e(TAG, "Fetching FCM registration token failed", task.exception)
                if (shouldGoToDashboard) goToDashboard()
                return@addOnCompleteListener
            }

            val token = task.result
            Log.d(TAG, "Fetched Token: $token")

            val url = "https://medigyaan.xyz/Neurons/api/update_fcmv2.php"

            val request = object : StringRequest(Method.POST, url,
                { response ->
                    Log.i(TAG, "SERVER RESPONSE: $response")
                    if (shouldGoToDashboard) goToDashboard()
                },
                { error ->
                    Log.e(TAG, "VOLLEY ERROR: ${error.message}")
                    // Navigate anyway so the user isn't stuck on a splash screen
                    if (shouldGoToDashboard) goToDashboard()
                }) {

                override fun getParams(): MutableMap<String, String> {
                    val params = HashMap<String, String>()
                    params["user_id"] = userId.toString()
                    params["fcm_token"] = token ?: ""
                    return params
                }
            }

            // Set timeout to 10 seconds to handle slow networks
            request.retryPolicy = DefaultRetryPolicy(10000, 1, 1.0f)
            Volley.newRequestQueue(this).add(request)
        }
    }

    private fun goToDashboard() {
        val intent = Intent(this, DashboardActivity::class.java)
        startActivity(intent)
        finish()
    }

    private fun goToChat(senderId: String) {
        val intent = Intent(this, MessengerActivity::class.java).apply {
            putExtra("SENDER_ID", senderId)
            // Ensure Messenger is the top activity
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        startActivity(intent)
        finish()
    }

    private fun goToLogin() {
        val intent = Intent(this, LoginActivity::class.java)
        startActivity(intent)
        finish()
    }
}
