package com.rankwarz.edulabsrtm

import android.content.Context
import android.util.Log
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.database.FirebaseDatabase

object HistoryManager {

    private const val TAG = "HISTORY_MANAGER"

    fun saveHistory(
        context: Context,
        mode: String,
        title: String,
        topic: String,
        score: Int,
        totalQuestions: Int,
        correctAnswers: Int,
        wrongAnswers: Int,
        challengeId: String = "",
        reviewJson: String = "",
        onComplete: (Boolean) -> Unit = {}
    ) {
        // Ensure user is authenticated to Firebase to avoid "Permission Denied"
        val auth = FirebaseAuth.getInstance()
        if (auth.currentUser == null) {
            Log.d(TAG, "No Firebase user, signing in anonymously before saving history")
            auth.signInAnonymously().addOnCompleteListener { task ->
                if (task.isSuccessful) {
                    performSave(context, mode, title, topic, score, totalQuestions, correctAnswers, wrongAnswers, challengeId, reviewJson, onComplete)
                } else {
                    Log.e(TAG, "Anonymous sign-in failed", task.exception)
                    onComplete(false)
                }
            }
        } else {
            performSave(context, mode, title, topic, score, totalQuestions, correctAnswers, wrongAnswers, challengeId, reviewJson, onComplete)
        }
    }

    private fun performSave(
        context: Context,
        mode: String,
        title: String,
        topic: String,
        score: Int,
        totalQuestions: Int,
        correctAnswers: Int,
        wrongAnswers: Int,
        challengeId: String = "",
        reviewJson: String = "",
        onComplete: (Boolean) -> Unit = {}
    ) {
        try {
            val prefs = context.getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
            val userId = prefs.getInt("user_id", 0)

            if (userId == 0) {
                Log.e(TAG, "Invalid user_id in SharedPreferences")
                onComplete(false)
                return
            }

            val attempted = correctAnswers + wrongAnswers
            val percentage = if (attempted > 0)
                (correctAnswers * 100f) / attempted
            else
                0f

            val database = FirebaseDatabase
                .getInstance()
                .getReference("history")
                .child(userId.toString())

            val key = database.push().key ?: return

            val history = HistoryModel(
                historyId = key,
                userId = userId,
                mode = mode,
                title = title,
                topic = topic,
                score = score,
                totalQuestions = totalQuestions,
                correctAnswers = correctAnswers,
                wrongAnswers = wrongAnswers,
                percentage = percentage,
                challengeId = challengeId,
                reviewJson = reviewJson,
                timestamp = System.currentTimeMillis()
            )

            database.child(key)
                .setValue(history)
                .addOnSuccessListener {
                    Log.d(TAG, "History saved successfully to history/$userId/$key")
                    onComplete(true)
                }
                .addOnFailureListener {
                    Log.e(TAG, "History save failed for path history/$userId/$key", it)
                    onComplete(false)
                }

        } catch (e: Exception) {
            Log.e(TAG, "saveHistory error", e)
            onComplete(false)
        }
    }
}