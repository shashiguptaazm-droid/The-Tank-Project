package com.rankwarz.edulabsrtm

import android.content.Context
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity

class VideoCallActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val prefs = getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
        val userId = prefs.getInt("user_id", 0)
        val userName = prefs.getString("user_name", "User $userId") ?: "User $userId"
        val room = "EDULABS_${System.currentTimeMillis()}"

        LiveKitCallActivity.start(
            context = this,
            roomName = room,
            peerName = "EduLabs Meeting",
            isVideo = true
        )

        finish()
    }
}
