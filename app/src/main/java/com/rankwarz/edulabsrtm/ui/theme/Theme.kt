package com.rankwarz.edulabsrtm.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import com.rankwarz.edulabsrtm.isAppDarkModeEnabled

private val DarkColorScheme = darkColorScheme(
    primary = DarkPrimary,
    onPrimary = Color(0xFF0F1115),
    primaryContainer = Color(0xFF2A325F),
    onPrimaryContainer = Color(0xFFE8EAF6),
    secondary = AmberSecondary,
    onSecondary = Color(0xFF0F1115),
    background = DarkBackground,
    onBackground = Color(0xFFF5F5F5),
    surface = DarkSurface,
    onSurface = Color.White,
    outline = DarkOutline,
    error = ErrorRedDark,
    onError = Color.White
)

private val LightColorScheme = lightColorScheme(
    primary = IndigoPrimary,
    onPrimary = Color.White,
    primaryContainer = IndigoLight,
    onPrimaryContainer = Color(0xFF1A237E),
    secondary = AmberSecondary,
    onSecondary = Color(0xFF212121),
    background = LightBackground,
    onBackground = LightTextPrimary,
    surface = LightSurface,
    onSurface = LightTextPrimary,
    outline = LightOutline,
    error = ErrorRed,
    onError = Color.White
)

@Composable
fun EduLabsRTMTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = false, // Keep it false to enforce our customized brand guidelines consistently
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}

@Composable
fun EduLabsRTMThemeFromPreferences(
    dynamicColor: Boolean = false, // Enforce brand identity consistently
    content: @Composable () -> Unit
) {
    val context = LocalContext.current
    EduLabsRTMTheme(
        darkTheme = isAppDarkModeEnabled(context),
        dynamicColor = dynamicColor,
        content = content
    )
}
