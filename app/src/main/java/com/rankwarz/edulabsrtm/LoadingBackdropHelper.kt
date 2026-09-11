package com.rankwarz.edulabsrtm

import android.net.Uri
import android.view.View
import android.widget.ImageView
import android.widget.VideoView
import androidx.appcompat.app.AppCompatActivity

fun resolveLobbyVideoRes(subject: String?, topic: String? = null): Int {
    val combined = "${subject.orEmpty()} ${topic.orEmpty()}".lowercase()
    return when {
        combined.contains("biochem") -> R.raw.loading_screen_elephant_biochemistry
        combined.contains("physio") || combined.contains("physilo") -> R.raw.loading_screen_eagle_physiology
        else -> R.raw.loading_screen_friends_lion
    }
}

fun resolveGameLoadingVideoRes(subject: String?, topic: String? = null): Int {
    val combined = "${subject.orEmpty()} ${topic.orEmpty()}".lowercase()
    return when {
        combined.contains("biochem") -> R.raw.loading_screen_elephant_biochemistry
        combined.contains("physio") || combined.contains("physilo") -> R.raw.loading_screen_eagle_physiology
        else -> R.raw.dont_land_the_foot_on_books_it
    }
}

fun AppCompatActivity.setupGameLoadingBackdrop(
    videoView: VideoView,
    posterView: ImageView,
    subject: String? = null,
    topic: String? = null
) {
    posterView.visibility = View.VISIBLE
    try {
        val rawResId = resolveGameLoadingVideoRes(subject, topic)
        val rawUri = Uri.parse("android.resource://${packageName}/${rawResId}")
        videoView.setVideoURI(rawUri)
        videoView.setOnPreparedListener { mediaPlayer ->
            mediaPlayer.isLooping = false
            mediaPlayer.setVolume(0f, 0f)
            videoView.start()
            videoView.alpha = 1f
        }
        videoView.setOnCompletionListener {
            ScreenExplosionHelper.triggerExplosion(
                activity = this,
                textureView = null,
                onMidExplosion = {
                    try {
                        videoView.seekTo(0)
                    } catch (_: Exception) {}
                },
                onComplete = {
                    try {
                        videoView.start()
                    } catch (_: Exception) {}
                }
            )
        }
        videoView.setOnErrorListener { _, _, _ ->
            posterView.visibility = View.VISIBLE
            true
        }
    } catch (_: Exception) {
        posterView.visibility = View.VISIBLE
    }
}

