package com.rankwarz.edulabsrtm

import android.content.Context
import android.util.Log
import com.android.volley.Request
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley

object UserCacheSyncer {
    private const val TAG = "USER_CACHE_SYNC"
    private const val URL = "https://medigyaan.xyz/Neurons/api/sync_user_cache.php"

    fun sync(context: Context, userId: Int, onComplete: (() -> Unit)? = null) {
        if (userId <= 0) {
            onComplete?.invoke()
            return
        }

        val overall = DailyStatsManager.getOverallStats(context)
        val today = DailyStatsManager.getToday(context)
        val streak = DailyStatsManager.getCurrentStreak(context)

        val request = object : StringRequest(
            Request.Method.POST,
            URL,
            { response ->
                Log.d(TAG, "Synced local profile cache: $response")
                onComplete?.invoke()
            },
            { error ->
                Log.e(TAG, "Local profile cache sync failed: ${error.message}", error)
                onComplete?.invoke()
            }
        ) {
            override fun getParams(): MutableMap<String, String> {
                return hashMapOf(
                    "user_id" to userId.toString(),
                    "daily_stats_json" to DailyStatsManager.exportRawJson(context),
                    "accuracy_history_json" to AccuracyHistoryManager.exportRawJson(context),
                    "overall_attempted" to overall.first.toString(),
                    "overall_correct" to overall.second.toString(),
                    "today_attempted" to today.first.toString(),
                    "today_correct" to today.second.toString(),
                    "local_streak" to streak.toString()
                )
            }
        }

        Volley.newRequestQueue(context.applicationContext).add(request)
    }
}
