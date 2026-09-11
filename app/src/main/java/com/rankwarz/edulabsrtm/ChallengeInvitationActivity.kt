package com.rankwarz.edulabsrtm

import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class ChallengeInvitationActivity : AppCompatActivity() {

    private val TAG = "INVITE_DEBUG"

    private lateinit var prefs: SharedPreferences
    private var userId: Int = 0

    private var challengeId: Int = 0
    private var lobbyId: String = ""
    private var uniqueId: Int = 0
    private var quizType: String = ""
    private var mode: String = ""
    private var subject: String = ""
    private var topic: String = ""
    private var hostName: String = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_challenge_invitation)

        Log.d(TAG, "Invitation Activity OPENED")

        prefs = getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
        userId = prefs.getInt("user_id", -1)

        val sessionValid = userId != -1 && userId != 0
        if (!sessionValid) {
            Log.e(TAG, "SESSION MISSING -> Redirecting to Login")

            Toast.makeText(this, "Session expired. Please login again", Toast.LENGTH_LONG).show()

            startActivity(
                Intent(this, LoginActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                }
            )
            finish()
            return
        }

        challengeId = readIntExtraCompat("CHALLENGE_ID", "challenge_id", 0)
        lobbyId = intent.getStringExtra("lobby_id")
            ?: intent.getStringExtra("LOBBY_ID")
                    ?: ""
        uniqueId = readIntExtraCompat("UNIQUE_ID", "unique_id", 0)

        quizType = intent.getStringExtra("QUIZ_TYPE")
            ?: intent.getStringExtra("quiz_type")
                    ?: "TEST_SERIES"

        mode = intent.getStringExtra("MODE")
            ?: intent.getStringExtra("mode")
                    ?: ""

        subject = intent.getStringExtra("SUBJECT")
            ?: intent.getStringExtra("subject")
                    ?: ""

        topic = intent.getStringExtra("TOPIC")
            ?: intent.getStringExtra("topic")
                    ?: ""

        hostName = intent.getStringExtra("host_name")
            ?: intent.getStringExtra("sender_name")
                    ?: "Friend"

        Log.d(
            TAG,
            "Data -> lobby=$lobbyId challenge=$challengeId user=$userId uniqueId=$uniqueId quizType=$quizType mode=$mode subject=$subject topic=$topic hostName=$hostName"
        )

        val txt = findViewById<TextView>(R.id.inviteText)
        val yes = findViewById<Button>(R.id.btnYes)
        val no = findViewById<Button>(R.id.btnNo)

        txt.text = "⚔️ $hostName invited you to a battle!"

        yes.setOnClickListener {
            joinLobby()
        }

        no.setOnClickListener {
            Log.d(TAG, "Invite rejected")
            finish()
        }
    }

    private fun joinLobby() {
        Log.d(TAG, "JOIN CLICKED")

        if (lobbyId.isBlank() && challengeId == 0) {
            Log.e(TAG, "Invalid lobby id / challenge id")
            Toast.makeText(this, "Invalid lobby", Toast.LENGTH_SHORT).show()
            return
        }

        val normalizedMode = mode.trim().uppercase()
        val normalizedQuizType = quizType.trim().uppercase()
        val hasSubjectTopic = subject.isNotBlank() && topic.isNotBlank()

        Log.d(
            TAG,
            "Routing decision -> hasSubjectTopic=$hasSubjectTopic rawMode='$mode' normalizedMode='$normalizedMode' rawQuizType='$quizType' normalizedQuizType='$normalizedQuizType'"
        )

        val targetActivity = when {
            hasSubjectTopic -> {
                Log.d(TAG, "Subject + Topic present -> Choosing TopicLobbyActivity")
                TopicLobbyActivity::class.java
            }

            normalizedMode == "TOPIC" || normalizedMode.contains("TOPIC") -> {
                Log.d(TAG, "MODE indicates TOPIC -> Choosing TopicLobbyActivity")
                TopicLobbyActivity::class.java
            }

            normalizedQuizType == "TOPIC" || normalizedQuizType.contains("TOPIC") -> {
                Log.d(TAG, "QUIZ_TYPE indicates TOPIC -> Choosing TopicLobbyActivity")
                TopicLobbyActivity::class.java
            }

            normalizedMode == "TEST" || normalizedMode.contains("TEST") -> {
                Log.d(TAG, "MODE indicates TEST -> Choosing LobbyActivity")
                LobbyActivity::class.java
            }

            normalizedQuizType == "TEST_SERIES" || normalizedQuizType.contains("TEST") -> {
                Log.d(TAG, "QUIZ_TYPE indicates TEST -> Choosing LobbyActivity")
                LobbyActivity::class.java
            }

            else -> {
                Log.d(TAG, "No subject/topic found -> Choosing LobbyActivity")
                LobbyActivity::class.java
            }
        }

        val launchIntent = Intent(this, targetActivity).apply {
            putExtra("lobby_id", lobbyId)
            putExtra("CHALLENGE_ID", challengeId)
            putExtra("UNIQUE_ID", uniqueId)
            putExtra("QUIZ_TYPE", quizType)
            putExtra("MODE", mode)
            putExtra("SUBJECT", subject)
            putExtra("TOPIC", topic)
            putExtra("user_id", userId.toString())
            putExtra("user_name", prefs.getString("name", "Player"))
            putExtra("IS_CHALLENGE", true)
            putExtra("IS_CREATOR", false)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }

        Log.d(TAG, "Launching ${targetActivity.simpleName} for lobby=$lobbyId challenge=$challengeId")
        startActivity(launchIntent)
        finish()
    }

    private fun readIntExtraCompat(primaryKey: String, fallbackKey: String, defaultValue: Int): Int {
        val primaryValue = intent.getIntExtra(primaryKey, Int.MIN_VALUE)
        if (primaryValue != Int.MIN_VALUE) return primaryValue

        val fallbackString = intent.getStringExtra(fallbackKey)
        return fallbackString?.replace("lobby_", "")?.toIntOrNull() ?: defaultValue
    }
}