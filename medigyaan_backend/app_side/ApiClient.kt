package com.rankwarz.edulabsrtm.data.remote

import com.google.gson.JsonObject
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Query

object ApiClient {
    private val client = OkHttpClient.Builder()
        .connectTimeout(120, java.util.concurrent.TimeUnit.SECONDS)
        .readTimeout(120, java.util.concurrent.TimeUnit.SECONDS)
        .writeTimeout(120, java.util.concurrent.TimeUnit.SECONDS)
        .addInterceptor(HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        })
        .build()

    // Groq
    val groqApi: AiService by lazy {
        Retrofit.Builder()
            .baseUrl("https://api.groq.com/")
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(AiService::class.java)
    }

    // Gemini
    val geminiApi: AiService by lazy {
        Retrofit.Builder()
            .baseUrl("https://generativelanguage.googleapis.com/")
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(AiService::class.java)
    }

    // OpenRouter
    val openRouterApi: AiService by lazy {
        Retrofit.Builder()
            .baseUrl("https://openrouter.ai/")
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(AiService::class.java)
    }

    // DeepSeek direct API
    val deepSeekApi: AiService by lazy {
        Retrofit.Builder()
            .baseUrl("https://api.deepseek.com/")
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(AiService::class.java)
    }

    // Mistral
    val mistralApi: AiService by lazy {
        Retrofit.Builder()
            .baseUrl("https://api.mistral.ai/")
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(AiService::class.java)
    }

    // Cloudflare
    val cloudflareApi: AiService by lazy {
        Retrofit.Builder()
            .baseUrl("https://api.cloudflare.com/")
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(AiService::class.java)
    }

    // Cerebras
    val cerebrasApi: AiService by lazy {
        Retrofit.Builder()
            .baseUrl("https://api.cerebras.ai/")
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(AiService::class.java)
    }

    // Cohere
    val cohereApi: AiService by lazy {
        Retrofit.Builder()
            .baseUrl("https://api.cohere.ai/")
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(AiService::class.java)
    }

    // Replicate
    val replicateApi: AiService by lazy {
        Retrofit.Builder()
            .baseUrl("https://api.replicate.com/")
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(AiService::class.java)
    }

    // OpenAI-compatible fallback endpoint
    val openAiApi: AiService by lazy {
        Retrofit.Builder()
            .baseUrl("https://api.openai.com/")
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(AiService::class.java)
    }
}
