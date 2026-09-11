package com.rankwarz.edulabsrtm.data.remote

import retrofit2.http.*
import com.google.gson.annotations.SerializedName
import com.rankwarz.edulabsrtm.model.GeminiContent
import com.rankwarz.edulabsrtm.model.GeminiGenerationConfig

interface AiService {
    @POST
    suspend fun chatCompletion(
        @Url url: String,
        @Header("Authorization") auth: String?,
        @Body request: ChatRequest
    ): ChatResponse
}

data class ChatRequest(
    val model: String,
    val messages: List<Message>,
    val temperature: Double = 0.2,
    @SerializedName("max_tokens")
    val maxTokens: Int = 2048,

    @SerializedName("response_format")
    val responseFormat: ResponseFormat? = null
)

data class Message(val role: String, val content: String)
data class ResponseFormat(val type: String)
data class GeminiRequest(
    val contents: List<GeminiContent>,
    val generationConfig: GeminiGenerationConfig
)

data class Content(
    val parts: List<Part>
)

data class Part(
    val text: String
)

data class GenerationConfig(
    val temperature: Double,
    val maxOutputTokens: Int
)
data class ChatResponse(
    val choices: List<Choice>
) {
    data class Choice(val message: MessageContent)
    data class MessageContent(val content: String)
}