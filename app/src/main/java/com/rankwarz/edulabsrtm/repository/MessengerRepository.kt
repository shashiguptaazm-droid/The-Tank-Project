package com.rankwarz.edulabsrtm.repository

import android.content.Context
import com.android.volley.toolbox.RequestFuture
import com.android.volley.toolbox.StringRequest
import com.rankwarz.edulabsrtm.model.ChatMessage
import com.rankwarz.edulabsrtm.model.ChatUserItem
import com.rankwarz.edulabsrtm.utils.NetworkingModule
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import kotlinx.coroutines.suspendCancellableCoroutine

class MessengerRepository(private val context: Context) {
    private val baseUrl = "https://medigyaan.xyz/Neurons/messenger_api.php"

    data class MessengerConfig(
        val vpsUploadUrl: String,
        val vpsUploadToken: String,
        val maxFileSize: Int
    )

    suspend fun fetchConfig(userId: Int): MessengerConfig = withContext(Dispatchers.IO) {
        val url = "$baseUrl?get_config=1&user_id=$userId"
        val response = suspendRequest(url)
        val json = JSONObject(response)
        MessengerConfig(
            vpsUploadUrl = json.optString("vps_upload_url"),
            vpsUploadToken = json.optString("vps_upload_token"),
            maxFileSize = json.optInt("max_file_size", 100 * 1024 * 1024)
        )
    }

    suspend fun fetchMessages(userId: Int, receiverId: Int): List<ChatMessage> = withContext(Dispatchers.IO) {
        val url = "$baseUrl?fetch_messages=$receiverId&user_id=$userId"
        val response = suspendRequest(url)
        val array = JSONArray(response)
        val list = mutableListOf<ChatMessage>()
        for (i in 0 until array.length()) {
            val msg = array.getJSONObject(i)
            list.add(
                ChatMessage(
                    senderId = msg.optInt("sender_id"),
                    text = msg.optString("message"),
                    attachment = msg.optString("attachment"),
                    sentAt = msg.optString("sent_at", ""),
                    isRead = msg.optInt("is_read", 0),
                    messageUuid = msg.optString("uuid", "")
                )
            )
        }
        list
    }

    private suspend fun suspendRequest(url: String): String = suspendCancellableCoroutine { continuation ->
        val request = object : StringRequest(Method.GET, url,
            { response -> continuation.resume(response) },
            { error -> continuation.resumeWithException(error) }
        ) {
            override fun getHeaders(): MutableMap<String, String> =
                hashMapOf("X-App-Signature" to "EduLabsRTM_Secure_v1_2026")
        }
        NetworkingModule.getRequestQueue(context).add(request)
        continuation.invokeOnCancellation { request.cancel() }
    }
}
