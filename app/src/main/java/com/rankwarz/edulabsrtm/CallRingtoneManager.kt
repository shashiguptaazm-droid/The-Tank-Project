package com.rankwarz.edulabsrtm

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.MediaPlayer
import android.media.RingtoneManager
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.util.Log

/**
 * Manages the looping phone ringtone and vibration for incoming audio/video calls.
 * Behaves like WhatsApp/FaceTime/cellular phone ringers.
 */
object CallRingtoneManager {

    private const val TAG = "CallRingtoneManager"
    private const val CALL_RING_TIMEOUT_MS = 45_000L

    private var mediaPlayer: MediaPlayer? = null
    private var vibrator: Vibrator? = null
    private val handler = Handler(Looper.getMainLooper())
    private var isRinging = false

    private val timeoutRunnable = Runnable {
        stop()
    }

    @Synchronized
    fun start(context: Context) {
        if (isRinging) return
        isRinging = true

        val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        val ringerMode = audioManager.ringerMode

        // 1. Setup Vibrator (if not silent)
        if (ringerMode != AudioManager.RINGER_MODE_SILENT) {
            startVibration(context)
        }

        // 2. Setup Ringtone Sound (if normal ringer mode)
        if (ringerMode == AudioManager.RINGER_MODE_NORMAL) {
            startRingtonePlayer(context)
        }

        // 3. Auto-stop after 45 seconds if nobody answers or declines
        handler.removeCallbacks(timeoutRunnable)
        handler.postDelayed(timeoutRunnable, CALL_RING_TIMEOUT_MS)
    }

    @Synchronized
    fun stop() {
        if (!isRinging && mediaPlayer == null && vibrator == null) return
        isRinging = false
        handler.removeCallbacks(timeoutRunnable)

        // Stop media player
        try {
            mediaPlayer?.let { player ->
                if (player.isPlaying) {
                    player.stop()
                }
                player.reset()
                player.release()
            }
        } catch (e: Exception) {
            Log.w(TAG, "Error stopping ringtone player: ${e.message}")
        } finally {
            mediaPlayer = null
        }

        // Stop vibration
        try {
            vibrator?.cancel()
        } catch (e: Exception) {
            Log.w(TAG, "Error stopping vibrator: ${e.message}")
        } finally {
            vibrator = null
        }
    }

    fun isRinging(): Boolean = isRinging

    private fun startRingtonePlayer(context: Context) {
        try {
            var ringtoneUri: Uri? = RingtoneManager.getActualDefaultRingtoneUri(context, RingtoneManager.TYPE_RINGTONE)
            if (ringtoneUri == null) {
                ringtoneUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE)
            }
            if (ringtoneUri == null) {
                ringtoneUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION)
            }

            if (ringtoneUri == null) {
                Log.w(TAG, "No valid ringtone URI found on device")
                return
            }

            val player = MediaPlayer().apply {
                setDataSource(context, ringtoneUri)
                setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_NOTIFICATION_RINGTONE)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                        .setLegacyStreamType(AudioManager.STREAM_RING)
                        .build()
                )
                isLooping = true
                prepare()
                start()
            }
            mediaPlayer = player
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start ringtone player: ${e.message}", e)
        }
    }

    private fun startVibration(context: Context) {
        try {
            val vib = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val vibratorManager = context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
                vibratorManager.defaultVibrator
            } else {
                @Suppress("DEPRECATION")
                context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
            }

            vibrator = vib
            val pattern = longArrayOf(0, 1000, 1000, 1000, 1000)

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vib.vibrate(VibrationEffect.createWaveform(pattern, 1))
            } else {
                @Suppress("DEPRECATION")
                vib.vibrate(pattern, 1)
            }
        } catch (e: Exception) {
            Log.w(TAG, "Failed to start vibration: ${e.message}")
        }
    }
}