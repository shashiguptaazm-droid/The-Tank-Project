package com.rankwarz.edulabsrtm

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.media.AudioManager
import android.media.ToneGenerator
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
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.FormBody
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.util.Locale
import java.util.concurrent.TimeUnit

/**
 * LiveKit WebRTC 1-to-1 Call Activity (WhatsApp / FaceTime style).
 * Interoperable with VPS SFU server (wss://medigyaan.com/rtc).
 * Supports strictly 1-on-1 audio & video calls with ringing, timer on connect,
 * and auto-hangup when peer disconnects.
 */
class LiveKitCallActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "LiveKitCallActivity"
        private const val PREF_NAME = "MY_APP"
        private const val TOKEN_URL = "https://medigyaan.com/Neurons/livekit_token.php"
        private const val WS_URL = "wss://medigyaan.com/rtc"
        private const val PERMISSION_REQUEST_CODE = 2001
        private const val CALL_TIMEOUT_MS = 45_000L

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
    private var isCallConnected = false
    private var timerJob: Job? = null
    private var callTimeoutJob: Job? = null
    private var toneGenerator: ToneGenerator? = null
    private lateinit var audioManager: AudioManager
    private var targetPeerName: String = "User"
    private var isCallEnding = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_livekit_call)

        // Make sure incoming call ringtone is stopped when call connects/opens
        CallRingtoneManager.stop()
        (getSystemService(Context.NOTIFICATION_SERVICE) as? android.app.NotificationManager)?.cancelAll()

        audioManager = getSystemService(Context.AUDIO_SERVICE) as AudioManager

        val roomName = intent.getStringExtra(EXTRA_ROOM_NAME) ?: run {
            Toast.makeText(this, "Room name missing", Toast.LENGTH_SHORT).show()
            finish()
            return
        }
        targetPeerName = intent.getStringExtra(EXTRA_PEER_NAME)?.takeIf { it.isNotBlank() } ?: "User"
        isVideoCall = intent.getBooleanExtra(EXTRA_IS_VIDEO, true)

        initViews(targetPeerName)
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
            audioPlaceholder.visibility = View.GONE
            localVideoContainer.visibility = View.VISIBLE
            setLocalPipFullScreen(true) // Start local camera in full-screen (WhatsApp style)
            isSpeakerOn = true
        }
        updateSpeakerUI()
        updateStatus("Connecting...")
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

        updateStatus("Connecting...")

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
                val newRoom = LiveKit.create(applicationContext)
                room = newRoom

                // Initialize video renderers
                newRoom.initVideoRenderer(localVideoView)
                newRoom.initVideoRenderer(remoteVideoView)

                localVideoView.setEnableHardwareScaler(true)
                localVideoView.setMirror(true)
                remoteVideoView.setEnableHardwareScaler(true)

                // Setup audio routing
                configureAudioRouting()

                // 3. Immediately start local camera preview (WhatsApp style)
                if (isVideoCall) {
                    audioPlaceholder.visibility = View.GONE
                    setLocalPipFullScreen(true)
                    newRoom.localParticipant.setCameraEnabled(true)
                    attachLocalVideoTrack()
                }

                // 4. Connect to WebSocket
                newRoom.connect(WS_URL, token)

                // 5. Publish local microphone
                newRoom.localParticipant.setMicrophoneEnabled(true)

                // 6. Collect room events
                observeRoomEvents(newRoom)

                // Check if remote peer is already in the room
                if (newRoom.remoteParticipants.isNotEmpty()) {
                    onCallAnswered()
                } else {
                    // We are caller, waiting for peer to answer
                    updateStatus("Calling $targetPeerName...")
                    startRinging()
                    startCallTimeout()
                }

            } catch (e: Exception) {
                Log.e(TAG, "Connection error: ${e.message}", e)
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@LiveKitCallActivity, "Call failed: ${e.localizedMessage}", Toast.LENGTH_LONG).show()
                    finish()
                }
            }
        }
    }

    private fun onCallAnswered() {
        if (isCallConnected || isCallEnding) return
        isCallConnected = true
        stopRinging()
        callTimeoutJob?.cancel()
        updateStatus("Connected (00:00)")
        startCallTimer()
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
                            if (isVideoCall) {
                                setLocalPipFullScreen(false) // Shrink local camera to top-right PiP!
                            }
                        }
                    }
                    is RoomEvent.TrackUnsubscribed -> {
                        val track = event.track
                        if (track is VideoTrack) {
                            track.removeRenderer(remoteVideoView)
                            remoteVideoView.visibility = View.GONE
                            if (isVideoCall) {
                                setLocalPipFullScreen(true) // Expand local camera back to full-screen
                            } else {
                                audioPlaceholder.visibility = View.VISIBLE
                            }
                        }
                    }
                    is RoomEvent.TrackPublished -> {
                        if (event.publication.track is VideoTrack) {
                            attachLocalVideoTrack()
                        }
                    }
                    is RoomEvent.ParticipantConnected -> {
                        // Strictly 1-to-1: if this is our peer joining, mark answered
                        if (!isCallConnected) {
                            onCallAnswered()
                        }
                    }
                    is RoomEvent.ParticipantDisconnected -> {
                        // In 1-to-1 call, when remote peer leaves, call ends immediately
                        onPeerDisconnected()
                    }
                    is RoomEvent.FailedToConnect -> {
                        stopRinging()
                        updateStatus("Failed to connect")
                        Toast.makeText(this@LiveKitCallActivity, "Failed to connect to call", Toast.LENGTH_SHORT).show()
                        finish()
                    }
                    is RoomEvent.Disconnected -> {
                        if (!isCallEnding) {
                            onPeerDisconnected()
                        }
                    }
                    else -> {}
                }
            }
        }
    }

    private fun onPeerDisconnected() {
        if (isCallEnding) return
        isCallEnding = true
        stopRinging()
        timerJob?.cancel()
        callTimeoutJob?.cancel()
        updateStatus("Call ended")
        Toast.makeText(this@LiveKitCallActivity, "Call ended", Toast.LENGTH_SHORT).show()

        scope.launch {
            delay(1200)
            endCall()
        }
    }

    private var ringbackJob: Job? = null

    private fun startRinging() {
        stopRinging()
        ringbackJob = scope.launch {
            try {
                val tg = ToneGenerator(AudioManager.STREAM_VOICE_CALL, 80)
                toneGenerator = tg
                while (isActive) {
                    tg.startTone(ToneGenerator.TONE_SUP_RINGTONE, 2000)
                    delay(4500)
                }
            } catch (e: Exception) {
                Log.w(TAG, "Failed to start ringtone: ${e.message}")
            }
        }
    }

    private fun stopRinging() {
        ringbackJob?.cancel()
        ringbackJob = null
        try {
            toneGenerator?.stopTone()
            toneGenerator?.release()
            toneGenerator = null
        } catch (e: Exception) {
            Log.w(TAG, "Failed to stop ringtone: ${e.message}")
        }
    }

    private fun startCallTimeout() {
        callTimeoutJob?.cancel()
        callTimeoutJob = scope.launch {
            delay(CALL_TIMEOUT_MS)
            if (!isCallConnected && !isCallEnding) {
                isCallEnding = true
                stopRinging()
                updateStatus("No answer")
                try {
                    val busyTone = ToneGenerator(AudioManager.STREAM_VOICE_CALL, 70)
                    busyTone.startTone(ToneGenerator.TONE_SUP_BUSY, 1500)
                } catch (_: Exception) {}
                delay(2000)
                endCall()
            }
        }
    }

    private fun attachLocalVideoTrack() {
        scope.launch {
            for (i in 0 until 15) {
                val camPub = room?.localParticipant?.getTrackPublication(Track.Source.CAMERA)
                val track = camPub?.track as? VideoTrack
                if (track != null) {
                    track.addRenderer(localVideoView)
                    localVideoContainer.visibility = if (isCameraOff) View.GONE else View.VISIBLE
                    break
                }
                delay(120)
            }
        }
    }

    private fun setLocalPipFullScreen(isFull: Boolean) {
        runOnUiThread {
            val params = localVideoContainer.layoutParams as? FrameLayout.LayoutParams ?: return@runOnUiThread
            if (isFull) {
                params.width = FrameLayout.LayoutParams.MATCH_PARENT
                params.height = FrameLayout.LayoutParams.MATCH_PARENT
                params.setMargins(0, 0, 0, 0)
                localVideoContainer.background = null
                localVideoContainer.elevation = 0f
                localVideoView.setZOrderMediaOverlay(false)
            } else {
                val density = resources.displayMetrics.density
                params.width = (120 * density).toInt()
                params.height = (160 * density).toInt()
                params.setMargins(0, (50 * density).toInt(), (16 * density).toInt(), 0)
                params.gravity = android.view.Gravity.TOP or android.view.Gravity.END
                localVideoContainer.setBackgroundResource(R.drawable.bg_pip_border)
                localVideoContainer.elevation = 6f * density
                localVideoView.setZOrderMediaOverlay(true)
            }
            localVideoContainer.layoutParams = params
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
                delay(1000)
                callDurationSeconds++
                val min = callDurationSeconds / 60
                val sec = callDurationSeconds % 60
                val formatted = String.format(Locale.US, "%02d:%02d", min, sec)
                updateStatus("Connected ($formatted)")
            }
        }
    }

    private fun endCall() {
        isCallEnding = true
        CallRingtoneManager.stop()
        stopRinging()
        timerJob?.cancel()
        callTimeoutJob?.cancel()
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
        isCallEnding = true
        CallRingtoneManager.stop()
        stopRinging()
        timerJob?.cancel()
        callTimeoutJob?.cancel()
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
