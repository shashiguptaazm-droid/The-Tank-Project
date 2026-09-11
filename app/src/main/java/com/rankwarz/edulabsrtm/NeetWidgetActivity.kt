package com.rankwarz.edulabsrtm

import android.app.AlarmManager
import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.widget.RemoteViews
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale
import java.util.concurrent.TimeUnit

class NeetWidgetActivity : AppWidgetProvider() {

    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray
    ) {
        for (appWidgetId in appWidgetIds) {
            updateWidget(context, appWidgetManager, appWidgetId)
        }
    }

    override fun onReceive(context: Context, intent: Intent) {
        super.onReceive(context, intent)

        when (intent.action) {
            ACTION_REFRESH_NEET_WIDGET,
            AppWidgetManager.ACTION_APPWIDGET_UPDATE,
            "android.appwidget.action.APPWIDGET_UPDATE" -> {
                val manager = AppWidgetManager.getInstance(context)
                val ids = manager.getAppWidgetIds(
                    ComponentName(context, NeetAppWidget::class.java)
                )
                for (appWidgetId in ids) {
                    updateWidget(context, manager, appWidgetId)
                }
            }

            ACTION_EXPIRE_CHALLENGE -> {
                clearChallengeState(context)
                forceUpdate(context)
            }
        }
    }

    private fun updateWidget(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetId: Int
    ) {
        val views = RemoteViews(context.packageName, R.layout.widget_neet_pg)
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

        val hasChallenge = prefs.getBoolean(KEY_HAS_CHALLENGE, false)
        val challengeText = prefs.getString(KEY_CHALLENGE_TEXT, null)
        val hostName = prefs.getString(KEY_CHALLENGE_HOST_NAME, "Friend")
        val challengeId = prefs.getInt(KEY_CHALLENGE_ID, 0)
        val uniqueId = prefs.getInt(KEY_UNIQUE_ID, 0)
        val quizType = prefs.getString(KEY_QUIZ_TYPE, "TEST_SERIES")
        val lobbyId = prefs.getString(KEY_LOBBY_ID, "")
        val challengeTime = prefs.getLong(KEY_CHALLENGE_TIME, 0L)

        val challengeExpired =
            hasChallenge && challengeTime > 0L && (System.currentTimeMillis() - challengeTime >= CHALLENGE_DURATION_MS)

        if (challengeExpired) {
            clearChallengeState(context)
        }

        val activeChallenge = prefs.getBoolean(KEY_HAS_CHALLENGE, false)

        if (activeChallenge) {
            views.setTextViewText(R.id.widgetTitle, "⚔️ Challenge")
            views.setTextViewText(R.id.widgetDays, "LIVE")
            views.setTextViewText(R.id.widgetSubtitle, "Tap to accept")
            views.setTextViewText(
                R.id.widgetDate,
                challengeText ?: "$hostName challenged you!"
            )
            views.setTextColor(R.id.widgetTitle, Color.WHITE)
            views.setTextColor(R.id.widgetDays, Color.WHITE)
            views.setTextColor(R.id.widgetSubtitle, Color.parseColor("#EDEDED"))
            views.setTextColor(R.id.widgetDate, Color.WHITE)

            val openIntent = Intent(context, ChallengeInvitationActivity::class.java).apply {
                putExtra("CHALLENGE_ID", challengeId)
                putExtra("lobby_id", lobbyId)
                putExtra("UNIQUE_ID", uniqueId)
                putExtra("QUIZ_TYPE", quizType)
                putExtra("host_name", hostName)
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            }

            val openPendingIntent = PendingIntent.getActivity(
                context,
                appWidgetId,
                openIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )

            views.setOnClickPendingIntent(R.id.widgetContainer, openPendingIntent)
        } else {
            val fallbackDate = "2026-06-15"
            val daysLeft = getDaysLeft(fallbackDate)
            val prettyDate = formatPrettyDate(fallbackDate)

            views.setTextViewText(R.id.widgetTitle, "NEET PG")
            views.setTextViewText(R.id.widgetDays, daysLeft)
            views.setTextViewText(R.id.widgetSubtitle, "days left")
            views.setTextViewText(R.id.widgetDate, prettyDate)
            views.setTextColor(R.id.widgetTitle, Color.WHITE)
            views.setTextColor(R.id.widgetDays, Color.WHITE)
            views.setTextColor(R.id.widgetSubtitle, Color.parseColor("#EDEDED"))
            views.setTextColor(R.id.widgetDate, Color.WHITE)

            val openIntent = Intent(context, ChallengeListActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            }

            val openPendingIntent = PendingIntent.getActivity(
                context,
                appWidgetId,
                openIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )

            views.setOnClickPendingIntent(R.id.widgetContainer, openPendingIntent)
        }

        val refreshIntent = Intent(context, NeetAppWidget::class.java).apply {
            action = ACTION_REFRESH_NEET_WIDGET
        }

        val refreshPendingIntent = PendingIntent.getBroadcast(
            context,
            appWidgetId,
            refreshIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        views.setOnClickPendingIntent(R.id.widgetDays, refreshPendingIntent)

        appWidgetManager.updateAppWidget(appWidgetId, views)
    }

    private fun getDaysLeft(dateStr: String): String {
        return try {
            val sdf = SimpleDateFormat("yyyy-MM-dd", Locale.US)
            sdf.isLenient = false
            val examDate = sdf.parse(dateStr) ?: return "--"

            val today = Calendar.getInstance()
            val examCal = Calendar.getInstance().apply { time = examDate }

            today.set(Calendar.HOUR_OF_DAY, 0)
            today.set(Calendar.MINUTE, 0)
            today.set(Calendar.SECOND, 0)
            today.set(Calendar.MILLISECOND, 0)

            examCal.set(Calendar.HOUR_OF_DAY, 0)
            examCal.set(Calendar.MINUTE, 0)
            examCal.set(Calendar.SECOND, 0)
            examCal.set(Calendar.MILLISECOND, 0)

            val diff = examCal.timeInMillis - today.timeInMillis
            val days = TimeUnit.MILLISECONDS.toDays(diff)

            when {
                days > 0 -> days.toString()
                days == 0L -> "Today"
                else -> "Passed"
            }
        } catch (_: Exception) {
            "--"
        }
    }

    private fun formatPrettyDate(dateStr: String): String {
        return try {
            val input = SimpleDateFormat("yyyy-MM-dd", Locale.US)
            val output = SimpleDateFormat("dd MMM yyyy", Locale.US)
            val date = input.parse(dateStr)
            if (date != null) output.format(date) else dateStr
        } catch (_: Exception) {
            dateStr
        }
    }

    private fun clearChallengeState(context: Context) {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit()
            .putBoolean(KEY_HAS_CHALLENGE, false)
            .remove(KEY_CHALLENGE_TEXT)
            .remove(KEY_CHALLENGE_HOST_NAME)
            .remove(KEY_CHALLENGE_ID)
            .remove(KEY_UNIQUE_ID)
            .remove(KEY_QUIZ_TYPE)
            .remove(KEY_LOBBY_ID)
            .remove(KEY_CHALLENGE_TIME)
            .apply()
    }

    companion object {
        const val ACTION_REFRESH_NEET_WIDGET = "com.rankwarz.edulabsrtm.REFRESH_NEET_WIDGET"
        const val ACTION_EXPIRE_CHALLENGE = "com.rankwarz.edulabsrtm.EXPIRE_CHALLENGE"

        private const val PREFS_NAME = "neet_widget"
        private const val KEY_HAS_CHALLENGE = "has_challenge"
        private const val KEY_CHALLENGE_TEXT = "challenge_text"
        private const val KEY_CHALLENGE_HOST_NAME = "challenge_host_name"
        private const val KEY_CHALLENGE_ID = "challenge_id"
        private const val KEY_UNIQUE_ID = "unique_id"
        private const val KEY_QUIZ_TYPE = "quiz_type"
        private const val KEY_LOBBY_ID = "lobby_id"
        private const val KEY_CHALLENGE_TIME = "challenge_time"

        private const val CHALLENGE_DURATION_MS = 60_000L

        fun forceUpdate(context: Context) {
            val intent = Intent(context, NeetAppWidget::class.java).apply {
                action = ACTION_REFRESH_NEET_WIDGET
            }
            context.sendBroadcast(intent)
        }

        fun scheduleChallengeExpiry(context: Context) {
            val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager

            val expireIntent = Intent(context, NeetAppWidget::class.java).apply {
                action = ACTION_EXPIRE_CHALLENGE
            }

            val pendingIntent = PendingIntent.getBroadcast(
                context,
                9001,
                expireIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )

            val triggerAt = System.currentTimeMillis() + CHALLENGE_DURATION_MS

            alarmManager.setExactAndAllowWhileIdle(
                AlarmManager.RTC_WAKEUP,
                triggerAt,
                pendingIntent
            )
        }
    }
}