package com.rankwarz.edulabsrtm

import android.content.Context
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity

class VideoCallActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val room = intent.getStringExtra(LiveKitCallActivity.EXTRA_ROOM_NAME)
        val peer = intent.getStringExtra(LiveKitCallActivity.EXTRA_PEER_NAME) ?: "User"
        val isVideo = intent.getBooleanExtra(LiveKitCallActivity.EXTRA_IS_VIDEO, true)

        if (!room.isNullOrBlank()) {
            LiveKitCallActivity.start(
                context = this,
                roomName = room,
                peerName = peer,
                isVideo = isVideo
            )
        } else {
            // If no room is specified, route to Messenger to pick a user to call
            val intent = android.content.Intent(this, MessengerActivity::class.java)
            startActivity(intent)
        }

        finish()
    }
}
