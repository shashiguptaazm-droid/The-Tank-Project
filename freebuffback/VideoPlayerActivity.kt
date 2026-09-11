package com.rankwarz.edulabsrtm

import android.annotation.SuppressLint
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.android.exoplayer2.ExoPlayer
import com.google.android.exoplayer2.MediaItem
import com.google.android.exoplayer2.ui.PlayerView

class VideoPlayerActivity : AppCompatActivity() {

    private var exoPlayer: ExoPlayer? = null

    @SuppressLint("SetTextI18n")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_video_player)

        val videoUrl = intent.getStringExtra("VIDEO_URL") ?: ""
        val videoTitle = intent.getStringExtra("VIDEO_TITLE") ?: "Video"

        val titleText = findViewById<TextView>(R.id.txtVideoTitle)
        titleText.text = videoTitle

        val backBtn = findViewById<ImageButton>(R.id.btnBack)
        backBtn.setOnClickListener { onBackPressed() }

        val progressBar = findViewById<ProgressBar>(R.id.videoProgressBar)
        val playerView = findViewById<PlayerView>(R.id.playerView)

        exoPlayer = ExoPlayer.Builder(this).build()
        playerView.player = exoPlayer

        if (videoUrl.isNotEmpty()) {
            val mediaItem = MediaItem.fromUri(videoUrl)
            exoPlayer?.setMediaItem(mediaItem)
            exoPlayer?.prepare()
            exoPlayer?.playWhenReady = true

            exoPlayer?.addListener(object : com.google.android.exoplayer2.Player.Listener {
                override fun onIsPlayingChanged(isPlaying: Boolean) {
                    progressBar.visibility = if (isPlaying) View.GONE else View.VISIBLE
                }
                override fun onPlayerError(error: com.google.android.exoplayer2.PlaybackException) {
                    progressBar.visibility = View.GONE
                    Toast.makeText(this@VideoPlayerActivity, "Video playback error", Toast.LENGTH_SHORT).show()
                }
            })
        } else {
            progressBar.visibility = View.GONE
            Toast.makeText(this, "No video URL available", Toast.LENGTH_SHORT).show()
        }

        val shareBtn = findViewById<ImageButton>(R.id.btnShare)
        shareBtn.setOnClickListener {
            val shareIntent = Intent(Intent.ACTION_SEND).apply {
                type = "text/plain"
                putExtra(Intent.EXTRA_TEXT, "Watch: $videoTitle - $videoUrl")
            }
            startActivity(Intent.createChooser(shareIntent, "Share video"))
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        exoPlayer?.release()
        exoPlayer = null
    }

    override fun onBackPressed() {
        exoPlayer?.pause()
        super.onBackPressed()
    }
}