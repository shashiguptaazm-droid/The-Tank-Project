package com.rankwarz.edulabsrtm

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.media.AudioManager
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.FrameLayout
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import io.livekit.android.LiveKit
import io.livekit.android.events.RoomEvent
import io.livekit.android.renderer.SurfaceViewRenderer
import io.livekit.android.room.Room
import io.livekit.android.room.track.LocalVideoTrack
import io.livekit.android.room.track.Track
import io.livekit.android.room.track.VideoTrack
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.FormBody
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.util.Locale
import java.util.concurrent.TimeUnit

/**
 * LiveKit WebRTC Call Activity.
 * Interoperable with iOS and VPS SFU server (wss://medigyaan.com/rtc).
 * Supports 1-on-1 audio/video calls and ad-hoc conference rooms.
 */
class LiveKitCallActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "LiveKitCallActivity"
        private const val PREF_NAME = "MY_APP"
        private const val TOKEN_URL = "https://medigyaan.com/Neurons/livekit_token.php"
        private const val WS_URL = "wss://medigyaan.com/rtc"
        private const val PERMISSION_REQUEST_CODE = 2001

        const val EXTRA_ROOM_NAME = "room_name"
        const val EXTRA_PEER_NAME = "peer_name"
        const val EXTRA_IS_VIDEO = "is_video"

        fun start(context: Context, roomName: String, peerName: String, isVideo: Boolean = true) {
            val intent = Intent(context, LiveKitCallActivity::class.java).apply {
                putExtra(EXTRA_ROOM_NAME, roomName)
                putExtra(EXTRA_PEER_NAME, peerName)
                putExtra(EXTRA_IS_VIDEO, isVideo)
            }
            context.startActivity(intent)
        }
    }

    private var room: Room? = null
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    // UI elements
    private lateinit var remoteVideoView: SurfaceViewRenderer
    private lateinit var localVideoView: SurfaceViewRenderer
    private lateinit var localVideoContainer: FrameLayout
    private lateinit var audioPlaceholder: LinearLayout
    private lateinit var peerNameText: TextView
    private lateinit var callStatusText: TextView
    private lateinit var audioPeerName: TextView
    private lateinit var audioCallStatus: TextView
    private lateinit var muteButton: ImageButton
    private lateinit var cameraButton: ImageButton
    private lateinit var flipCameraButton: ImageButton
    private lateinit var speakerButton: ImageButton
    private lateinit var endCallButton: ImageButton

    // State
    private var isVideoCall = true
    private var isMicMuted = false
    private var isCameraOff = false
    private var isSpeakerOn = true
    private var callDurationSeconds = 0
    private var timerJob: Job? = null
    private lateinit var audioManager: AudioManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_livekit_call)

        audioManager = getSystemService(Context.AUDIO_SERVICE) as AudioManager

        val roomName = intent.getStringExtra(EXTRA_ROOM_NAME) ?: run {
            Toast.makeText(this, "Room name missing", Toast.LENGTH_SHORT).show()
            finish()
            return
        }
        val peerName = intent.getStringExtra(EXTRA_PEER_NAME) ?: "User"
        isVideoCall = intent.getBooleanExtra(EXTRA_IS_VIDEO, true)

        initViews(peerName)
        setupControls()

        if (checkPermissions()) {
            connectToCall(roomName)
        } else {
            requestPermissions()
        }
    }

    private fun initViews(peerName: String) {
        remoteVideoView = findViewById(R.id.remoteVideo)
        localVideoView = findViewById(R.id.localVideo)
        localVideoContainer = findViewById(R.id.localVideoContainer)
        audioPlaceholder = findViewById(R.id.audioCallPlaceholder)
        peerNameText = findViewById(R.id.peerNameText)
        callStatusText = findViewById(R.id.callStatusText)
        audioPeerName = findViewById(R.id.audioPeerName)
        audioCallStatus = findViewById(R.id.audioCallStatus)

        muteButton = findViewById(R.id.muteButton)
        cameraButton = findViewById(R.id.cameraButton)
        flipCameraButton = findViewById(R.id.flipCameraButton)
        speakerButton = findViewById(R.id.speakerButton)
        endCallButton = findViewById(R.id.endCallButton)

        peerNameText.text = peerName
        audioPeerName.text = peerName

        if (!isVideoCall) {
            cameraButton.visibility = View.GONE
            flipCameraButton.visibility = View.GONE
            localVideoContainer.visibility = View.GONE
            remoteVideoView.visibility = View.GONE
            audioPlaceholder.visibility = View.VISIBLE
            isSpeakerOn = false
        } else {
            cameraButton.visibility = View.VISIBLE
            flipCameraButton.visibility = View.VISIBLE
            localVideoContainer.visibility = View.VISIBLE
            isSpeakerOn = true
        }
        updateSpeakerUI()
    }

    private fun setupControls() {
        muteButton.setOnClickListener {
            toggleMicrophone()
        }

        cameraButton.setOnClickListener {
            if (isVideoCall) {
                toggleCamera()
            }
        }

        flipCameraButton.setOnClickListener {
            if (isVideoCall) {
                flipCamera()
            }
        }

        speakerButton.setOnClickListener {
            toggleSpeaker()
        }

        endCallButton.setOnClickListener {
            endCall()
        }
    }

    private fun checkPermissions(): Boolean {
        val audioGranted = ContextCompat.checkSelfPermission(
            this, Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED

        val cameraGranted = if (isVideoCall) {
            ContextCompat.checkSelfPermission(
                this, Manifest.permission.CAMERA
            ) == PackageManager.PERMISSION_GRANTED
        } else true

        return audioGranted && cameraGranted
    }

    private fun requestPermissions() {
        val perms = if (isVideoCall) {
            arrayOf(Manifest.permission.RECORD_AUDIO, Manifest.permission.CAMERA)
        } else {
            arrayOf(Manifest.permission.RECORD_AUDIO)
        }
        ActivityCompat.requestPermissions(this, perms, PERMISSION_REQUEST_CODE)
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == PERMISSION_REQUEST_CODE) {
            if (grantResults.isNotEmpty() && grantResults.all { it == PackageManager.PERMISSION_GRANTED }) {
                val roomName = intent.getStringExtra(EXTRA_ROOM_NAME) ?: return
                connectToCall(roomName)
            } else {
                Toast.makeText(this, "Permissions required for call", Toast.LENGTH_SHORT).show()
                finish()
            }
        }
    }

    private fun connectToCall(roomName: String) {
        val prefs = getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        val userId = prefs.getInt("user_id", 0)
        val userName = prefs.getString("user_name", "User $userId") ?: "User $userId"

        updateStatus("Connecting to server...")

        scope.launch {
            try {
                // 1. Fetch token from medigyaan.com
                val token = withContext(Dispatchers.IO) {
                    fetchLiveKitToken(roomName, userId, userName)
                }

                if (token == null) {
                    withContext(Dispatchers.Main) {
                        Toast.makeText(this@LiveKitCallActivity, "Failed to get call token", Toast.LENGTH_SHORT).show()
                        finish()
                    }
                    return@launch
                }

                // 2. Initialize LiveKit Room
                updateStatus("Joining room...")
                val newRoom = LiveKit.create(applicationContext)
                room = newRoom

                // Initialize video renderers
                newRoom.initVideoRenderer(localVideoView)
                newRoom.initVideoRenderer(remoteVideoView)

                // Setup audio routing
                configureAudioRouting()

                // 3. Connect to WebSocket
                newRoom.connect(WS_URL, token)

                // 4. Publish local media tracks
                newRoom.localParticipant.setMicrophoneEnabled(true)
                if (isVideoCall) {
                    newRoom.localParticipant.setCameraEnabled(true)
                    attachLocalVideoTrack()
                }

                updateStatus("Connected")
                startCallTimer()

                // 5. Collect room events
                observeRoomEvents(newRoom)

            } catch (e: Exception) {
                Log.e(TAG, "Connection error: ${e.message}", e)
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@LiveKitCallActivity, "Call failed: ${e.localizedMessage}", Toast.LENGTH_LONG).show()
                    finish()
                }
            }
        }
    }

    private fun observeRoomEvents(r: Room) {
        scope.launch {
            r.events.events.collectLatest { event: RoomEvent ->
                when (event) {
                    is RoomEvent.TrackSubscribed -> {
                        val track = event.track
                        if (track is VideoTrack) {
                            track.addRenderer(remoteVideoView)
                            remoteVideoView.visibility = View.VISIBLE
                            audioPlaceholder.visibility = View.GONE
                        }
                    }
                    is RoomEvent.TrackUnsubscribed -> {
                        val track = event.track
                        if (track is VideoTrack) {
                            track.removeRenderer(remoteVideoView)
                            remoteVideoView.visibility = View.GONE
                            if (!isVideoCall) {
                                audioPlaceholder.visibility = View.VISIBLE
                            }
                        }
                    }
                    is RoomEvent.ParticipantConnected -> {
                        updateStatus("Peer joined")
                    }
                    is RoomEvent.ParticipantDisconnected -> {
                        updateStatus("Peer left")
                        if (r.remoteParticipants.isEmpty()) {
                            Toast.makeText(this@LiveKitCallActivity, "Call ended", Toast.LENGTH_SHORT).show()
                            endCall()
                        }
                    }
                    is RoomEvent.FailedToConnect -> {
                        updateStatus("Failed to connect")
                        Toast.makeText(this@LiveKitCallActivity, "Failed to connect to room", Toast.LENGTH_SHORT).show()
                        finish()
                    }
                    is RoomEvent.Disconnected -> {
                        updateStatus("Call ended")
                        finish()
                    }
                    else -> {}
                }
            }
        }
    }

    private fun attachLocalVideoTrack() {
        val camPub = room?.localParticipant?.getTrackPublication(Track.Source.CAMERA)
        val track = camPub?.track as? VideoTrack
        if (track != null) {
            track.addRenderer(localVideoView)
            localVideoContainer.visibility = View.VISIBLE
        }
    }

    private fun toggleMicrophone() {
        scope.launch {
            val lp = room?.localParticipant ?: return@launch
            isMicMuted = !isMicMuted
            lp.setMicrophoneEnabled(!isMicMuted)
            muteButton.setImageResource(if (isMicMuted) R.drawable.ic_mic_off else R.drawable.ic_mic)
            muteButton.setBackgroundResource(if (isMicMuted) R.drawable.bg_circle_red else R.drawable.bg_circle_gray)
        }
    }

    private fun toggleCamera() {
        scope.launch {
            val lp = room?.localParticipant ?: return@launch
            isCameraOff = !isCameraOff
            lp.setCameraEnabled(!isCameraOff)
            localVideoContainer.visibility = if (isCameraOff) View.GONE else View.VISIBLE
            cameraButton.setBackgroundResource(if (isCameraOff) R.drawable.bg_circle_red else R.drawable.bg_circle_gray)
        }
    }

    private fun flipCamera() {
        scope.launch {
            val lp = room?.localParticipant ?: return@launch
            val track = lp.getTrackPublication(Track.Source.CAMERA)?.track as? LocalVideoTrack
            track?.switchCamera()
        }
    }

    private fun toggleSpeaker() {
        isSpeakerOn = !isSpeakerOn
        audioManager.isSpeakerphoneOn = isSpeakerOn
        updateSpeakerUI()
    }

    private fun updateSpeakerUI() {
        speakerButton.setBackgroundResource(if (isSpeakerOn) R.drawable.bg_circle_green else R.drawable.bg_circle_gray)
    }

    private fun configureAudioRouting() {
        try {
            audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
            audioManager.isSpeakerphoneOn = isSpeakerOn
        } catch (e: Exception) {
            Log.w(TAG, "Failed to set audio mode: ${e.message}")
        }
    }

    private fun restoreAudioRouting() {
        try {
            audioManager.mode = AudioManager.MODE_NORMAL
            audioManager.isSpeakerphoneOn = false
        } catch (e: Exception) {
            Log.w(TAG, "Failed to restore audio mode: ${e.message}")
        }
    }

    private fun fetchLiveKitToken(room: String, userId: Int, displayName: String): String? {
        val formBody = FormBody.Builder()
            .add("room", room)
            .add("user_id", userId.toString())
            .add("display_name", displayName)
            .build()

        val request = Request.Builder()
            .url(TOKEN_URL)
            .post(formBody)
            .build()

        return try {
            val response = httpClient.newCall(request).execute()
            val raw = response.body?.string() ?: return null
            Log.d(TAG, "Token response: $raw")
            val json = JSONObject(raw)
            if (json.optBoolean("success", false)) {
                json.optString("token")
            } else {
                json.optString("token").ifEmpty { null }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Token request error: ${e.message}", e)
            null
        }
    }

    private fun updateStatus(text: String) {
        runOnUiThread {
            callStatusText.text = text
            audioCallStatus.text = text
        }
    }

    private fun startCallTimer() {
        timerJob?.cancel()
        timerJob = scope.launch {
            while (true) {
                kotlinx.coroutines.delay(1000)
                callDurationSeconds++
                val min = callDurationSeconds / 60
                val sec = callDurationSeconds % 60
                val formatted = String.format(Locale.US, "%02d:%02d", min, sec)
                updateStatus("Connected ($formatted)")
            }
        }
    }

    private fun endCall() {
        timerJob?.cancel()
        scope.launch {
            try {
                room?.disconnect()
            } catch (e: Exception) {
                Log.w(TAG, "Error disconnecting: ${e.message}")
            }
            restoreAudioRouting()
            finish()
        }
    }

    override fun onDestroy() {
        timerJob?.cancel()
        restoreAudioRouting()
        scope.launch {
            try {
                localVideoView.release()
                remoteVideoView.release()
                room?.disconnect()
                room?.release()
            } catch (e: Exception) {
                Log.w(TAG, "Error in onDestroy cleanup: ${e.message}")
            }
        }
        scope.cancel()
        super.onDestroy()
    }
}
