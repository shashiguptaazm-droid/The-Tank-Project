package com.rankwarz.edulabsrtm

import android.util.Base64
import android.util.Log
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore

object FirebaseOnlineCache {
    private const val TAG = "FirebaseOnlineCache"
    private const val COLLECTION = "online_cache"
    private const val MAX_FIRESTORE_RESPONSE_CHARS = 450_000

    private fun uid(): String? = FirebaseAuth.getInstance().currentUser?.uid

    private fun documentId(key: String): String {
        return Base64.encodeToString(key.toByteArray(Charsets.UTF_8), Base64.URL_SAFE or Base64.NO_WRAP)
            .take(900)
    }

    fun getString(
        key: String,
        maxAgeMs: Long,
        allowStale: Boolean = true,
        onResult: (String?) -> Unit
    ) {
        val userId = uid()
        if (userId.isNullOrBlank()) {
            onResult(null)
            return
        }

        FirebaseFirestore.getInstance()
            .collection("users")
            .document(userId)
            .collection(COLLECTION)
            .document(documentId(key))
            .get()
            .addOnSuccessListener { snapshot ->
                val response = snapshot.getString("response")
                val updatedAt = snapshot.getLong("updatedAt") ?: 0L
                val isFresh = System.currentTimeMillis() - updatedAt <= maxAgeMs
                onResult(response?.takeIf { isFresh || allowStale })
            }
            .addOnFailureListener {
                Log.e(TAG, "Cache read failed for $key", it)
                onResult(null)
            }
    }

    fun putString(key: String, response: String) {
        val userId = uid() ?: return
        if (response.isBlank()) return
        if (response.length > MAX_FIRESTORE_RESPONSE_CHARS) {
            Log.w(TAG, "Skipping oversized Firestore cache write for $key (${response.length} chars)")
            return
        }

        FirebaseFirestore.getInstance()
            .collection("users")
            .document(userId)
            .collection(COLLECTION)
            .document(documentId(key))
            .set(
                mapOf(
                    "key" to key.take(500),
                    "response" to response,
                    "updatedAt" to System.currentTimeMillis()
                )
            )
            .addOnFailureListener {
                Log.e(TAG, "Cache write failed for $key", it)
            }
    }
}
