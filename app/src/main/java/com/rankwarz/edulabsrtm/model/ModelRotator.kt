package com.rankwarz.edulabsrtm.model

import android.content.Context
import android.content.SharedPreferences
import android.util.Log
import org.json.JSONArray

data class ModelCandidate(
    val provider: String,
    val model: String
)

object ModelRotator {
    private const val PREFS_NAME = "model_rotator_prefs"
    private const val KEY_LAST_SUCCESSFUL_PROVIDER = "last_successful_provider"
    private const val KEY_LAST_SUCCESSFUL_MODEL = "last_successful_model"
    private const val KEY_LAST_REFRESH_HF = "last_refresh_hf"
    private const val KEY_LAST_REFRESH_OR = "last_refresh_or"
    private const val KEY_PROVIDER_COOLDOWN_PREFIX = "provider_cooldown_"
    private const val PROVIDER_COOLDOWN_MS = 24 * 60 * 60 * 1000L
    private const val SHORT_MODEL_COOLDOWN_MS = 60 * 60 * 1000L
    
    private var sharedPrefs: SharedPreferences? = null
    
    // In-memory model registry for dynamic updates
    private val dynamicModels = mutableMapOf<String, List<String>>()
    
    // Hardcoded fallbacks
    private val fallbackModels = mapOf(
        "groq" to listOf("openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b", "llama-3.1-8b-instant"),
        "openrouter" to listOf(
            "google/gemini-2.5-flash", 
            "meta-llama/llama-3-8b-instruct:free", 
            "mistralai/mistral-7b-instruct:free"
        ),
        "cloudflare" to listOf(
            "@cf/meta/llama-3-8b-instruct",
            "@cf/meta/llama-3.1-8b-instruct",
            "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b"
        ),
        "deepseek" to listOf("deepseek-chat"),
        "mistral" to listOf("mistral-large-latest", "open-mixtral-8x22b"),
        "cerebras" to listOf("llama3.1-70b", "llama3.1-8b"),
        "cohere" to listOf("command-r-plus", "command-r"),
        "replicate" to listOf("meta/meta-llama-3-70b-instruct"),
        "gemini" to listOf("gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp")
    )

    fun init(context: Context) {
        sharedPrefs = context.applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        loadDynamicModels()
        clearProviderCooldown("gemini")
        clearProviderCooldown("deepseek")
    }
    
    private fun loadDynamicModels() {
        val prefs = sharedPrefs ?: return
        for (provider in listOf("openrouter")) {
            val jsonStr = prefs.getString("models_$provider", null)
            if (!jsonStr.isNullOrBlank()) {
                try {
                    val arr = JSONArray(jsonStr)
                    val list = mutableListOf<String>()
                    for (i in 0 until arr.length()) {
                        list.add(arr.getString(i))
                    }
                    if (list.isNotEmpty()) {
                        dynamicModels[provider] = list
                    }
                } catch (e: Exception) {
                    Log.e("ModelRotator", "Failed to parse saved models for $provider", e)
                }
            }
        }
    }

    fun replaceProviderModels(provider: String, models: List<String>) {
        dynamicModels[provider] = models
        val prefs = sharedPrefs ?: return
        try {
            val arr = JSONArray()
            models.forEach { arr.put(it) }
            prefs.edit().putString("models_$provider", arr.toString()).apply()
            
            // Record last refresh timestamp
            val now = System.currentTimeMillis()
            if (provider == "openrouter") {
                prefs.edit().putLong(KEY_LAST_REFRESH_OR, now).apply()
            }
        } catch (e: Exception) {
            Log.e("ModelRotator", "Failed to save models for $provider", e)
        }
    }

    fun shouldRefreshHuggingFaceModels(): Boolean {
        return false
    }

    fun shouldRefreshOpenRouterFreeModels(): Boolean {
        val prefs = sharedPrefs ?: return true
        val lastRefresh = prefs.getLong(KEY_LAST_REFRESH_OR, 0L)
        // Refresh every 1 hour
        return System.currentTimeMillis() - lastRefresh > 60 * 60 * 1000L
    }

    fun buildPool(provider: String): List<ModelCandidate> {
        val cleanProvider = provider.trim().lowercase()
        val pool = mutableListOf<ModelCandidate>()
        val now = System.currentTimeMillis()

        if (cleanProvider == "auto") {
            // Priority order of providers
            val providers = listOf(
                "openrouter",
                "groq",
                "cerebras",
                "deepseek",
                "cohere",
                "mistral",
                "replicate",
                "cloudflare",
                "gemini"
            )
            
            // First place the last successful model if available
            val lastSuccessful = getLastSuccessful()
            if (lastSuccessful != null && !isProviderCoolingDown(lastSuccessful.provider, now)) {
                pool.add(lastSuccessful)
            }
            
            // Add all other models sorted by recent failure counts
            val candidates = mutableListOf<ModelCandidate>()
            for (p in providers) {
                if (isProviderCoolingDown(p, now)) continue
                val models = dynamicModels[p] ?: fallbackModels[p] ?: emptyList()
                for (model in models) {
                    val candidate = ModelCandidate(p, model)
                    if (candidate != lastSuccessful) {
                        candidates.add(candidate)
                    }
                }
            }
            
            // Sort remaining candidates: fewer failures first
            candidates.sortBy { getFailureCount(it.provider, it.model) }
            pool.addAll(candidates)
        } else {
            if (isProviderCoolingDown(cleanProvider, now)) return emptyList()
            val models = dynamicModels[cleanProvider] ?: fallbackModels[cleanProvider] ?: emptyList()
            val candidates = models.map { ModelCandidate(cleanProvider, it) }.toMutableList()
            
            // Place last successful model for this provider at the top if it matches
            val lastSuccessful = getLastSuccessful()
            if (lastSuccessful != null && lastSuccessful.provider == cleanProvider) {
                candidates.remove(lastSuccessful)
                pool.add(lastSuccessful)
            }
            
            // Sort remaining by failure count
            candidates.sortBy { getFailureCount(it.provider, it.model) }
            pool.addAll(candidates)
        }

        return pool
    }

    fun markSuccess(candidate: ModelCandidate) {
        val prefs = sharedPrefs ?: return
        prefs.edit()
            .putString(KEY_LAST_SUCCESSFUL_PROVIDER, candidate.provider)
            .putString(KEY_LAST_SUCCESSFUL_MODEL, candidate.model)
            .apply()
        clearProviderCooldown(candidate.provider)
            
        // Reset failure count for this model
        setFailureCount(candidate.provider, candidate.model, 0)
    }

    fun markFailure(provider: String, model: String, error: String) {
        Log.w("ModelRotator", "Model failed: $provider/$model: $error")
        val currentFailures = getFailureCount(provider, model)
        setFailureCount(provider, model, currentFailures + 1)
        if (isProviderWideRefusalText(error)) {
            markProviderFailure(provider, error)
        }
    }

    fun markProviderFailure(provider: String, error: String, cooldownMs: Long = providerCooldownFor(error)) {
        val prefs = sharedPrefs ?: return
        val expiry = System.currentTimeMillis() + cooldownMs
        prefs.edit().putLong(providerCooldownKey(provider), expiry).apply()
        Log.w("ModelRotator", "Provider failed; cooling down for the day: $provider until $expiry")
    }

    fun clearLastSuccessfulIfMatches(provider: String, model: String) {
        val last = getLastSuccessful()
        if (last != null && last.provider == provider && last.model == model) {
            val prefs = sharedPrefs ?: return
            prefs.edit()
                .remove(KEY_LAST_SUCCESSFUL_PROVIDER)
                .remove(KEY_LAST_SUCCESSFUL_MODEL)
                .apply()
        }
    }

    private fun isProviderCoolingDown(provider: String, nowMs: Long = System.currentTimeMillis()): Boolean {
        val prefs = sharedPrefs ?: return false
        val expiry = prefs.getLong(providerCooldownKey(provider), 0L)
        if (expiry <= 0L) return false
        if (expiry <= nowMs) {
            clearProviderCooldown(provider)
            return false
        }
        return true
    }

    private fun clearProviderCooldown(provider: String) {
        val prefs = sharedPrefs ?: return
        prefs.edit().remove(providerCooldownKey(provider)).apply()
    }

    private fun providerCooldownKey(provider: String): String = "$KEY_PROVIDER_COOLDOWN_PREFIX${provider.trim().lowercase()}"

    private fun providerCooldownFor(error: String): Long {
        val m = error.lowercase()
        return if (
            m.contains("none of its models can be used for the day") ||
            m.contains("no models can be used for the day") ||
            m.contains("no models available for the day") ||
            m.contains("models cannot be used today") ||
            m.contains("provider unavailable for today") ||
            m.contains("try again tomorrow") ||
            m.contains("come back tomorrow") ||
            m.contains("temporarily unavailable")
        ) {
            PROVIDER_COOLDOWN_MS
        } else {
            PROVIDER_COOLDOWN_MS
        }
    }

    private fun isProviderWideRefusalText(text: String): Boolean {
        val m = text.lowercase()
        return m.contains("none of its models can be used for the day") ||
            m.contains("no models can be used for the day") ||
            m.contains("no models available for the day") ||
            m.contains("models cannot be used today") ||
            m.contains("provider unavailable for today") ||
            m.contains("try again tomorrow") ||
            m.contains("come back tomorrow") ||
            m.contains("temporarily unavailable")
    }
    
    private fun getLastSuccessful(): ModelCandidate? {
        val prefs = sharedPrefs ?: return null
        val provider = prefs.getString(KEY_LAST_SUCCESSFUL_PROVIDER, null)
        val model = prefs.getString(KEY_LAST_SUCCESSFUL_MODEL, null)
        if (provider != null && model != null) {
            return ModelCandidate(provider, model)
        }
        return null
    }

    private fun getFailureCount(provider: String, model: String): Int {
        val prefs = sharedPrefs ?: return 0
        return prefs.getInt("fail_${provider}_${model}", 0)
    }

    private fun setFailureCount(provider: String, model: String, count: Int) {
        val prefs = sharedPrefs ?: return
        prefs.edit().putInt("fail_${provider}_${model}", count).apply()
    }
}
