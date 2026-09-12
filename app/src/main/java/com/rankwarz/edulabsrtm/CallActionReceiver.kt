package com.rankwarz.edulabsrtm

import android.app.NotificationManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class CallActionReceiver : BroadcastReceiver() {

    companion object {
        const val ACTION_DECLINE = "com.rankwarz.edulabsrtm.ACTION_DECLINE_CALL"
        const val EXTRA_NOTIFICATION_ID = "notification_id"
    }

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == ACTION_DECLINE) {
            CallRingtoneManager.stop()
            val notifId = intent.getIntExtra(EXTRA_NOTIFICATION_ID, 0)
            if (notifId != 0) {
                val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager
                notificationManager?.cancel(notifId)
            }
        }
    }
}