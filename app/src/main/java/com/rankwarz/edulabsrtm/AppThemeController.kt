package com.rankwarz.edulabsrtm

import android.content.Context
import androidx.appcompat.app.AppCompatDelegate

const val APP_PREFS_NAME = "MY_APP"
const val KEY_DARK_MODE = "dark_mode_enabled"

fun isAppDarkModeEnabled(context: Context): Boolean {
    return context.getSharedPreferences(APP_PREFS_NAME, Context.MODE_PRIVATE)
        .getBoolean(KEY_DARK_MODE, false)
}

fun applySavedAppTheme(context: Context) {
    AppCompatDelegate.setDefaultNightMode(
        if (isAppDarkModeEnabled(context)) AppCompatDelegate.MODE_NIGHT_YES
        else AppCompatDelegate.MODE_NIGHT_NO
    )
}

fun setAppDarkMode(context: Context, enabled: Boolean) {
    context.getSharedPreferences(APP_PREFS_NAME, Context.MODE_PRIVATE)
        .edit()
        .putBoolean(KEY_DARK_MODE, enabled)
        .apply()

    AppCompatDelegate.setDefaultNightMode(
        if (enabled) AppCompatDelegate.MODE_NIGHT_YES
        else AppCompatDelegate.MODE_NIGHT_NO
    )
}
