package com.rankwarz.edulabsrtm.data.remote

import com.google.gson.JsonObject
import retrofit2.Response
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Query

interface ModelDiscoveryService {

    // =====================================================
    // GROQ
    // GET https://api.groq.com/openai/v1/models
    // =====================================================
    @GET("openai/v1/models")
    suspend fun getGroqModels(
        @Header("Authorization") authorization: String
    ): Response<JsonObject>

    // =====================================================
    // GEMINI
    // GET https://generativelanguage.googleapis.com/v1beta/models
    // =====================================================
    @GET("v1beta/models")
    suspend fun getGeminiModels(
        @Query("key") apiKey: String
    ): Response<JsonObject>

    // =====================================================
    // OPENROUTER
    // GET https://openrouter.ai/api/v1/models
    // =====================================================
    @GET("api/v1/models")
    suspend fun getOpenRouterModels(
        @Header("Authorization") authorization: String
    ): Response<JsonObject>

    // =====================================================
    // MISTRAL
    // GET https://api.mistral.ai/v1/models
    // =====================================================
    @GET("v1/models")
    suspend fun getMistralModels(
        @Header("Authorization") authorization: String
    ): Response<JsonObject>

    // =====================================================
    // CEREBRAS
    // GET https://api.cerebras.ai/v1/models
    // =====================================================
    @GET("v1/models")
    suspend fun getCerebrasModels(
        @Header("Authorization") authorization: String
    ): Response<JsonObject>

    // =====================================================
    // CLOUDFLARE AI
    // GET
    // https://api.cloudflare.com/client/v4/accounts/{accountId}/ai/models/search
    // =====================================================
    @GET
    suspend fun getCloudflareModels(
        @retrofit2.http.Url url: String,
        @Header("Authorization") authorization: String
    ): Response<JsonObject>

    // =====================================================
    // COHERE
    // GET https://api.cohere.ai/v1/models
    // =====================================================
    @GET("v1/models")
    suspend fun getCohereModels(
        @Header("Authorization") authorization: String
    ): Response<JsonObject>

    // =====================================================
    // REPLICATE
    // GET https://api.replicate.com/v1/models
    // =====================================================
    @GET("v1/models")
    suspend fun getReplicateModels(
        @Header("Authorization") authorization: String
    ): Response<JsonObject>

}