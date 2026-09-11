package com.rankwarz.edulabsrtm

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.app.ServiceCompat

class ThesisBackgroundService : Service() {
    private var foregroundStarted = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        ensureChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val message = intent?.getStringExtra(EXTRA_MESSAGE) ?: "Thesis processing is running"
        startAsForeground(message)
        return START_STICKY
    }

    private fun startAsForeground(message: String) {
        if (foregroundStarted) {
            NotificationManagerCompat.from(this).notify(NOTIFICATION_ID, buildNotification(message))
            return
        }

        val primaryNotification = buildNotification(message)
        val started = runCatching {
            startForegroundCompat(primaryNotification)
            true
        }.getOrElse { primaryError ->
            runCatching {
                startForegroundCompat(buildFallbackNotification(message))
                true
            }.getOrElse { fallbackError ->
                logForegroundFailure(primaryError, fallbackError)
                false
            }
        }

        if (started) {
            foregroundStarted = true
        } else {
            stopSelf()
        }
    }

    private fun startForegroundCompat(notification: Notification) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ServiceCompat.startForeground(
                this,
                NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            )
        } else {
            ServiceCompat.startForeground(this, NOTIFICATION_ID, notification, 0)
        }
    }

    private fun ensureChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = getSystemService(NotificationManager::class.java)
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Thesis background work",
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "Keeps thesis export, generation, and figure downloads running in the background"
        }
        manager.createNotificationChannel(channel)
    }

    private fun buildNotification(message: String): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle("EduLabs thesis processing")
            .setContentText(message)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    private fun buildFallbackNotification(message: String): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle("EduLabs thesis processing")
            .setContentText(message)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    private fun logForegroundFailure(primaryError: Throwable, fallbackError: Throwable) {
        android.util.Log.e(
            "ThesisBackgroundService",
            "Failed to start foreground service with primary and fallback notifications",
            primaryError
        )
        android.util.Log.e(
            "ThesisBackgroundService",
            "Fallback notification also failed",
            fallbackError
        )
    }

    companion object {
        private const val CHANNEL_ID = "thesis_background_work"
        private const val NOTIFICATION_ID = 8104
        private const val EXTRA_MESSAGE = "extra_message"

        fun start(context: Context, message: String) {
            val appContext = context.applicationContext
            val intent = Intent(appContext, ThesisBackgroundService::class.java)
                .putExtra(EXTRA_MESSAGE, message)
            runCatching {
                appContext.startService(intent)
            }.onFailure {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    runCatching {
                        appContext.startForegroundService(intent)
                    }
                }
            }
        }

        fun stop(context: Context) {
            val appContext = context.applicationContext
            runCatching {
                appContext.stopService(Intent(appContext, ThesisBackgroundService::class.java))
            }
        }
    }
}
