package com.rankwarz.edulabsrtm

import android.content.Context
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

object DailyStatsManager {

    private const val PREF_NAME = "MCQ_STATS_HISTORY"
    private const val KEY_DATA = "daily_data"

    private fun getPrefs(context: Context) =
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)

    private fun getTodayKey(): String {
        return SimpleDateFormat("yyyyMMdd", Locale.getDefault()).format(Date())
    }
    fun getOverallStats(context: Context): Pair<Int, Int> {
        val data = load(context)

        var attempted = 0
        var correct = 0

        val keys = data.keys()

        while (keys.hasNext()) {
            val key = keys.next()
            val obj = data.optJSONObject(key)

            attempted += obj?.optInt("attempted", 0) ?: 0
            correct += obj?.optInt("correct", 0) ?: 0
        }

        return Pair(attempted, correct)
    }

    fun getOverallAccuracy(context: Context): Int {
        val stats = getOverallStats(context)
        return calculateAccuracy(stats.first, stats.second)
    }

    fun getCurrentStreak(context: Context): Int {
        val data = load(context)

        var streak = 0
        val cal = Calendar.getInstance()

        while (true) {
            val key = SimpleDateFormat(
                "yyyyMMdd",
                Locale.getDefault()
            ).format(cal.time)

            val obj = data.optJSONObject(key)

            val attempted = obj?.optInt("attempted", 0) ?: 0

            if (attempted > 0) {
                streak++
            } else {
                break
            }

            cal.add(Calendar.DAY_OF_YEAR, -1)
        }

        return streak
    }

    fun getTotalBattles(context: Context): Int {
        val overall = getOverallStats(context)
        return overall.first
    }

    fun getTotalWins(context: Context): Int {
        val overall = getOverallStats(context)
        return overall.second
    }

    fun getRankBadge(context: Context): String {
        val accuracy = getOverallAccuracy(context)

        return when {
            accuracy >= 90 -> "🏆 Legend"
            accuracy >= 80 -> "🔥 Master"
            accuracy >= 70 -> "⚔️ Warrior"
            accuracy >= 60 -> "🎯 Skilled"
            accuracy >= 50 -> "📘 Rookie"
            else -> "🌱 Beginner"
        }
    }
    private fun load(context: Context): JSONObject {
        val raw = getPrefs(context).getString(KEY_DATA, "{}") ?: "{}"
        return try {
            JSONObject(raw)
        } catch (_: Exception) {
            JSONObject()
        }
    }

    fun exportRawJson(context: Context): String {
        return load(context).toString()
    }

    private fun save(context: Context, json: JSONObject) {
        getPrefs(context).edit().putString(KEY_DATA, json.toString()).apply()
    }

    fun recordAnswer(context: Context, topic: String, isCorrect: Boolean) {
        val cleanTopic = topic.trim().ifEmpty { "General" }

        val data = load(context)
        val today = getTodayKey()

        val todayObj = data.optJSONObject(today) ?: JSONObject().apply {
            put("attempted", 0)
            put("correct", 0)
            put("topics", JSONObject())
        }

        val attempted = todayObj.optInt("attempted", 0) + 1
        val correct = todayObj.optInt("correct", 0) + if (isCorrect) 1 else 0

        todayObj.put("attempted", attempted)
        todayObj.put("correct", correct)

        val topicsObj = todayObj.optJSONObject("topics") ?: JSONObject()

        val topicObj = topicsObj.optJSONObject(cleanTopic) ?: JSONObject().apply {
            put("attempted", 0)
            put("correct", 0)
        }

        val topicAttempted = topicObj.optInt("attempted", 0) + 1
        val topicCorrect = topicObj.optInt("correct", 0) + if (isCorrect) 1 else 0

        topicObj.put("attempted", topicAttempted)
        topicObj.put("correct", topicCorrect)

        topicsObj.put(cleanTopic, topicObj)
        todayObj.put("topics", topicsObj)

        data.put(today, todayObj)
        save(context, data)
    }

    fun getToday(context: Context): Pair<Int, Int> {
        val data = load(context)
        val today = getTodayKey()
        val obj = data.optJSONObject(today)

        val attempted = obj?.optInt("attempted", 0) ?: 0
        val correct = obj?.optInt("correct", 0) ?: 0

        return Pair(attempted, correct)
    }

    fun getTodayTopicWise(context: Context): Map<String, Pair<Int, Int>> {
        val result = mutableMapOf<String, Pair<Int, Int>>()
        val data = load(context)
        val today = getTodayKey()

        val todayObj = data.optJSONObject(today) ?: return result
        val topicsObj = todayObj.optJSONObject("topics") ?: return result

        val keys = topicsObj.keys()
        while (keys.hasNext()) {
            val topic = keys.next()
            val obj = topicsObj.optJSONObject(topic)

            val attempted = obj?.optInt("attempted", 0) ?: 0
            val correct = obj?.optInt("correct", 0) ?: 0

            result[topic] = Pair(attempted, correct)
        }

        return result
    }

    fun getLastNDays(context: Context, days: Int): Pair<Int, Int> {
        val data = load(context)

        var totalAttempted = 0
        var totalCorrect = 0

        val cal = Calendar.getInstance()

        repeat(days) {
            val key = SimpleDateFormat("yyyyMMdd", Locale.getDefault()).format(cal.time)
            val obj = data.optJSONObject(key)

            totalAttempted += obj?.optInt("attempted", 0) ?: 0
            totalCorrect += obj?.optInt("correct", 0) ?: 0

            cal.add(Calendar.DAY_OF_YEAR, -1)
        }

        return Pair(totalAttempted, totalCorrect)
    }

    fun getGraphData(context: Context, days: Int): List<Pair<String, Int>> {
        val data = load(context)
        val list = mutableListOf<Pair<String, Int>>()

        val cal = Calendar.getInstance()
        val labelFormat = SimpleDateFormat("dd MMM", Locale.getDefault())

        repeat(days) {
            val key = SimpleDateFormat("yyyyMMdd", Locale.getDefault()).format(cal.time)
            val label = labelFormat.format(cal.time)
            val obj = data.optJSONObject(key)

            val attempted = obj?.optInt("attempted", 0) ?: 0
            val correct = obj?.optInt("correct", 0) ?: 0
            val accuracy = calculateAccuracy(attempted, correct)

            list.add(Pair(label, accuracy))
            cal.add(Calendar.DAY_OF_YEAR, -1)
        }

        return list.reversed()
    }

    fun getTopicAccuracyList(context: Context): List<Triple<String, Int, Int>> {
        val topicMap = getTodayTopicWise(context)

        return topicMap.map { entry ->
            val topic = entry.key
            val attempted = entry.value.first
            val correct = entry.value.second
            val acc = calculateAccuracy(attempted, correct)
            Triple(topic, attempted, acc)
        }.sortedByDescending { it.third }
    }

    fun calculateAccuracy(attempted: Int, correct: Int): Int {
        return if (attempted > 0) (correct * 100) / attempted else 0
    }
}
