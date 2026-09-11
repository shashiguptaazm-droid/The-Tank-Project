package com.rankwarz.edulabsrtm

import android.content.Context
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale

data class AccuracyPeriodStats(
    val label: String,
    val attempted: Int,
    val correct: Int
) {
    val accuracy: Int
        get() = if (attempted > 0) (correct * 100) / attempted else 0
}

object AccuracyHistoryManager {

    private const val PREF_NAME = "ACCURACY_HISTORY_PREF"
    private const val KEY_HISTORY = "daily_history"

    private fun getPrefs(context: Context) =
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)

    private fun todayKey(): String {
        return SimpleDateFormat("yyyyMMdd", Locale.getDefault()).format(Calendar.getInstance().time)
    }

    private fun loadHistory(context: Context): JSONObject {
        val raw = getPrefs(context).getString(KEY_HISTORY, "{}") ?: "{}"
        return try {
            JSONObject(raw)
        } catch (_: Exception) {
            JSONObject()
        }
    }

    fun exportRawJson(context: Context): String {
        return loadHistory(context).toString()
    }

    private fun saveHistory(context: Context, json: JSONObject) {
        getPrefs(context).edit().putString(KEY_HISTORY, json.toString()).apply()
    }

    fun recordAnswer(context: Context, isCorrect: Boolean) {
        val history = loadHistory(context)
        val key = todayKey()

        val dayObj = history.optJSONObject(key) ?: JSONObject().apply {
            put("attempted", 0)
            put("correct", 0)
        }

        val attempted = dayObj.optInt("attempted", 0) + 1
        val correct = dayObj.optInt("correct", 0) + if (isCorrect) 1 else 0

        dayObj.put("attempted", attempted)
        dayObj.put("correct", correct)
        history.put(key, dayObj)

        saveHistory(context, history)
    }

    fun getTodayStats(context: Context): AccuracyPeriodStats {
        val key = todayKey()
        val history = loadHistory(context)
        val dayObj = history.optJSONObject(key)

        val attempted = dayObj?.optInt("attempted", 0) ?: 0
        val correct = dayObj?.optInt("correct", 0) ?: 0

        return AccuracyPeriodStats("Today", attempted, correct)
    }

    fun getLastNDays(context: Context, days: Int): List<AccuracyPeriodStats> {
        val history = loadHistory(context)
        val sdfKey = SimpleDateFormat("yyyyMMdd", Locale.getDefault())
        val sdfLabel = SimpleDateFormat("dd MMM", Locale.getDefault())

        val cal = Calendar.getInstance()
        val result = ArrayList<AccuracyPeriodStats>()

        for (i in days - 1 downTo 0) {
            val c = cal.clone() as Calendar
            c.add(Calendar.DAY_OF_YEAR, -i)

            val key = sdfKey.format(c.time)
            val label = sdfLabel.format(c.time)

            val dayObj = history.optJSONObject(key)
            val attempted = dayObj?.optInt("attempted", 0) ?: 0
            val correct = dayObj?.optInt("correct", 0) ?: 0

            result.add(AccuracyPeriodStats(label, attempted, correct))
        }

        return result
    }

    fun getLastNWeeks(context: Context, weeks: Int): List<AccuracyPeriodStats> {
        val history = loadHistory(context)
        val cal = Calendar.getInstance()

        val result = ArrayList<AccuracyPeriodStats>()

        for (w in weeks - 1 downTo 0) {
            val end = cal.clone() as Calendar
            end.add(Calendar.WEEK_OF_YEAR, -w)

            val start = end.clone() as Calendar
            start.set(Calendar.DAY_OF_WEEK, start.firstDayOfWeek)
            start.set(Calendar.HOUR_OF_DAY, 0)
            start.set(Calendar.MINUTE, 0)
            start.set(Calendar.SECOND, 0)
            start.set(Calendar.MILLISECOND, 0)

            val weekEnd = start.clone() as Calendar
            weekEnd.add(Calendar.DAY_OF_YEAR, 6)
            weekEnd.set(Calendar.HOUR_OF_DAY, 23)
            weekEnd.set(Calendar.MINUTE, 59)
            weekEnd.set(Calendar.SECOND, 59)
            weekEnd.set(Calendar.MILLISECOND, 999)

            var attempted = 0
            var correct = 0

            val walk = start.clone() as Calendar
            val sdfKey = SimpleDateFormat("yyyyMMdd", Locale.getDefault())

            while (!walk.after(weekEnd)) {
                val key = sdfKey.format(walk.time)
                val dayObj = history.optJSONObject(key)
                attempted += dayObj?.optInt("attempted", 0) ?: 0
                correct += dayObj?.optInt("correct", 0) ?: 0
                walk.add(Calendar.DAY_OF_YEAR, 1)
            }

            val label = "W${weeks - w}"
            result.add(AccuracyPeriodStats(label, attempted, correct))
        }

        return result
    }

    fun getLastNMonths(context: Context, months: Int): List<AccuracyPeriodStats> {
        val history = loadHistory(context)
        val cal = Calendar.getInstance()
        val result = ArrayList<AccuracyPeriodStats>()

        val sdfKey = SimpleDateFormat("yyyyMMdd", Locale.getDefault())
        val sdfLabel = SimpleDateFormat("MMM yy", Locale.getDefault())

        for (m in months - 1 downTo 0) {
            val monthCal = cal.clone() as Calendar
            monthCal.add(Calendar.MONTH, -m)

            val start = monthCal.clone() as Calendar
            start.set(Calendar.DAY_OF_MONTH, 1)
            start.set(Calendar.HOUR_OF_DAY, 0)
            start.set(Calendar.MINUTE, 0)
            start.set(Calendar.SECOND, 0)
            start.set(Calendar.MILLISECOND, 0)

            val end = monthCal.clone() as Calendar
            end.set(Calendar.DAY_OF_MONTH, end.getActualMaximum(Calendar.DAY_OF_MONTH))
            end.set(Calendar.HOUR_OF_DAY, 23)
            end.set(Calendar.MINUTE, 59)
            end.set(Calendar.SECOND, 59)
            end.set(Calendar.MILLISECOND, 999)

            var attempted = 0
            var correct = 0

            val walk = start.clone() as Calendar
            while (!walk.after(end)) {
                val key = sdfKey.format(walk.time)
                val dayObj = history.optJSONObject(key)
                attempted += dayObj?.optInt("attempted", 0) ?: 0
                correct += dayObj?.optInt("correct", 0) ?: 0
                walk.add(Calendar.DAY_OF_YEAR, 1)
            }

            val label = sdfLabel.format(monthCal.time)
            result.add(AccuracyPeriodStats(label, attempted, correct))
        }

        return result
    }
}
