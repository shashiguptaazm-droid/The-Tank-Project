package com.rankwarz.edulabsrtm

import android.app.AlarmManager
import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.graphics.BitmapFactory
import android.graphics.Color
import android.os.Bundle
import android.widget.RemoteViews
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale
import java.util.concurrent.TimeUnit

class NeetAppWidget : AppWidgetProvider() {

    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray
    ) {
        for (appWidgetId in appWidgetIds) {
            updateWidget(context, appWidgetManager, appWidgetId)
        }
    }

    override fun onAppWidgetOptionsChanged(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetId: Int,
        newOptions: Bundle
    ) {
        updateWidget(context, appWidgetManager, appWidgetId)
    }

    override fun onReceive(context: Context, intent: Intent) {
        super.onReceive(context, intent)

        if (intent.action == ACTION_REFRESH_NEET_WIDGET) {
            val manager = AppWidgetManager.getInstance(context)
            val ids = manager.getAppWidgetIds(
                ComponentName(context, NeetAppWidget::class.java)
            )
            for (id in ids) {
                updateWidget(context, manager, id)
            }
        }
    }

    private fun getTodayDate(): String {
        return try {
            SimpleDateFormat("dd MMM yyyy", Locale.getDefault()).format(Date())
        } catch (_: Exception) {
            "--"
        }
    }

    private fun chooseLayout(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetId: Int
    ): Int {
        val options = appWidgetManager.getAppWidgetOptions(appWidgetId)
        val minWidthDp = options.getInt(AppWidgetManager.OPTION_APPWIDGET_MIN_WIDTH)

        return when {
            minWidthDp < 180 -> R.layout.widget_small
            minWidthDp < 260 -> R.layout.widget_medium
            else -> R.layout.widget_large
        }
    }

    private fun updateWidget(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetId: Int
    ) {
        val prefs = context.getSharedPreferences("neet_widget", Context.MODE_PRIVATE)

        var hasChallenge = prefs.getBoolean("has_challenge", false)
        val challengeStart = prefs.getLong("challenge_time", 0L)

        if (hasChallenge && challengeStart > 0L) {
            val elapsed = System.currentTimeMillis() - challengeStart
            if (elapsed >= 60_000) {
                prefs.edit()
                    .putBoolean("has_challenge", false)
                    .remove("challenge_host_name")
                    .remove("challenge_id")
                    .remove("lobby_id")
                    .remove("unique_id")
                    .remove("quiz_type")
                    .remove("mode")
                    .remove("subject")
                    .remove("topic")
                    .remove("challenge_time")
                    .apply()

                hasChallenge = false
            }
        }

        val layoutRes = chooseLayout(context, appWidgetManager, appWidgetId)
        val views = RemoteViews(context.packageName, layoutRes)

        val hostName = prefs.getString("challenge_host_name", "Friend") ?: "Friend"

        val rankTitle = prefs.getString("user_rank_title", "Expert")
            ?.trim()
            ?.lowercase(Locale.US)

        val fallbackBackgroundRes = when (rankTitle) {
            "expert" -> R.drawable.expert_widget
            "grandmaster" -> R.drawable.grandmaster_widget
            "aspirant" -> R.drawable.aspirant
            "scholar" -> R.drawable.scholar
            else -> R.drawable.expert_widget
        }

        val localBackgroundPath = prefs.getString("local_background_path", null)
        if (!localBackgroundPath.isNullOrBlank()) {
            try {
                val options = BitmapFactory.Options().apply {
                    inSampleSize = 2
                    inPreferredConfig = android.graphics.Bitmap.Config.RGB_565
                }
                val bgBitmap = BitmapFactory.decodeFile(localBackgroundPath, options)
                if (bgBitmap != null) {
                    views.setImageViewBitmap(R.id.widgetBg, bgBitmap)
                } else {
                    views.setImageViewResource(R.id.widgetBg, fallbackBackgroundRes)
                }
            } catch (_: Exception) {
                views.setImageViewResource(R.id.widgetBg, fallbackBackgroundRes)
            }
        } else {
            views.setImageViewResource(R.id.widgetBg, fallbackBackgroundRes)
        }

        views.setImageViewResource(R.id.widgetProfileIcon, R.drawable.ic_settings)

        if (hasChallenge) {
            views.setTextViewText(R.id.widgetTitle, "⚔️ Challenge")
            views.setTextViewText(R.id.widgetDays, "LIVE")
            views.setTextViewText(R.id.widgetSubtitle, "Tap to accept")
            views.setTextViewText(R.id.widgetDate, "$hostName challenged you!")
            views.setTextColor(R.id.widgetDays, Color.RED)
            views.setTextViewText(R.id.widgetStats, "")

            val openIntent = Intent(context, ChallengeInvitationActivity::class.java).apply {
                putExtra("CHALLENGE_ID", prefs.getInt("challenge_id", 0))
                putExtra("lobby_id", prefs.getString("lobby_id", "") ?: "")
                putExtra("UNIQUE_ID", prefs.getInt("unique_id", 0))
                putExtra("QUIZ_TYPE", prefs.getString("quiz_type", "TEST_SERIES") ?: "TEST_SERIES")
                putExtra("MODE", prefs.getString("mode", "") ?: "")
                putExtra("SUBJECT", prefs.getString("subject", "") ?: "")
                putExtra("TOPIC", prefs.getString("topic", "") ?: "")
                putExtra("host_name", hostName)
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            }

            val pendingIntent = PendingIntent.getActivity(
                context,
                appWidgetId,
                openIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            views.setOnClickPendingIntent(R.id.widgetContainer, pendingIntent)

            scheduleChallengeExpiry(context)

        } else {
            val examName = prefs.getString("selected_exam_name", "NEET PG") ?: "NEET PG"
            val examDate = prefs.getString("selected_exam_date", "2026-06-15") ?: "2026-06-15"
            val daysLeft = getDaysLeft(examDate)

            views.setTextViewText(R.id.widgetTitle, examName)
            views.setTextViewText(R.id.widgetDays, daysLeft)
            views.setTextViewText(R.id.widgetSubtitle, "days left")
            views.setTextViewText(R.id.widgetDate, getTodayDate())
            views.setTextColor(R.id.widgetDays, Color.parseColor("#FF1744"))

            val (attempted, correctCount) = DailyStatsManager.getToday(context)
            val accuracy = DailyStatsManager.calculateAccuracy(attempted, correctCount)

            val statsText = if (attempted == 0) {
                "Start practicing today 🚀"
            } else {
                "$correctCount/$attempted MCQs done today • $accuracy% accuracy"
            }
            views.setTextViewText(R.id.widgetStats, statsText)

            val openIntent = Intent(context, ChallengeListActivity::class.java)
            val pendingIntent = PendingIntent.getActivity(
                context,
                appWidgetId,
                openIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            views.setOnClickPendingIntent(R.id.widgetContainer, pendingIntent)

            scheduleMidnightUpdate(context)
        }

        val settingsIntent = Intent(context, WidgetSettingsActivity::class.java)
        val settingsPendingIntent = PendingIntent.getActivity(
            context,
            2001,
            settingsIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        views.setOnClickPendingIntent(R.id.widgetProfileIcon, settingsPendingIntent)

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
            val examCal = parseToCalendar(dateStr) ?: return "--"
            val today = Calendar.getInstance()

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

    private fun parseToCalendar(dateStr: String): Calendar? {
        return try {
            val formats = listOf(
                SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US),
                SimpleDateFormat("yyyy-MM-dd", Locale.US)
            )

            val date = formats.firstNotNullOfOrNull { format ->
                try {
                    format.parse(dateStr)
                } catch (_: Exception) {
                    null
                }
            } ?: return null

            Calendar.getInstance().apply { time = date }
        } catch (_: Exception) {
            null
        }
    }

    private fun scheduleMidnightUpdate(context: Context) {
        val intent = Intent(context, NeetAppWidget::class.java).apply {
            action = ACTION_REFRESH_NEET_WIDGET
        }

        val pendingIntent = PendingIntent.getBroadcast(
            context,
            MIDNIGHT_REQUEST_CODE,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager

        val calendar = Calendar.getInstance().apply {
            add(Calendar.DAY_OF_YEAR, 1)
            set(Calendar.HOUR_OF_DAY, 0)
            set(Calendar.MINUTE, 0)
            set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
        }

        alarmManager.set(
            AlarmManager.RTC,
            calendar.timeInMillis,
            pendingIntent
        )
    }

    private fun scheduleChallengeExpiry(context: Context) {
        val intent = Intent(context, NeetAppWidget::class.java).apply {
            action = ACTION_REFRESH_NEET_WIDGET
        }

        val pendingIntent = PendingIntent.getBroadcast(
            context,
            CHALLENGE_EXPIRE_REQUEST_CODE,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager

        alarmManager.setExact(
            AlarmManager.RTC_WAKEUP,
            System.currentTimeMillis() + 60_000,
            pendingIntent
        )
    }

    companion object {
        private const val MIDNIGHT_REQUEST_CODE = 1001
        private const val CHALLENGE_EXPIRE_REQUEST_CODE = 1002
        const val ACTION_REFRESH_NEET_WIDGET = "com.rankwarz.edulabsrtm.REFRESH_NEET_WIDGET"

        fun forceUpdate(context: Context) {
            val intent = Intent(context, NeetAppWidget::class.java).apply {
                action = ACTION_REFRESH_NEET_WIDGET
            }
            context.sendBroadcast(intent)
        }
    }
}