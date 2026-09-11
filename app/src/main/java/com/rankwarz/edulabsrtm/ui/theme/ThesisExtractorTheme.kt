package com.rankwarz.edulabsrtm.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

@Composable
fun ThesisExtractorTheme(
    darkTheme: Boolean,
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) {
        darkColorScheme(
            primary = Color(0xFF8DB7FF),
            onPrimary = Color(0xFF00325B),
            primaryContainer = Color(0xFF174A79),
            onPrimaryContainer = Color(0xFFD4E3FF),
            secondary = Color(0xFF93D5C2),
            onSecondary = Color(0xFF00382D),
            secondaryContainer = Color(0xFF1D5145),
            onSecondaryContainer = Color(0xFFAFEEDC),
            tertiary = Color(0xFFE7B6CC),
            onTertiary = Color(0xFF492435),
            background = Color(0xFF101417),
            onBackground = Color(0xFFE0E3E7),
            surface = Color(0xFF181C20),
            onSurface = Color(0xFFE0E3E7),
            surfaceVariant = Color(0xFF40484F),
            onSurfaceVariant = Color(0xFFC0C7CE),
            outline = Color(0xFF8A9299),
            outlineVariant = Color(0xFF40484F),
            error = Color(0xFFFFB4AB),
            onError = Color(0xFF690005)
        )
    } else {
        lightColorScheme(
            primary = Color(0xFF0F5B92),
            onPrimary = Color.White,
            primaryContainer = Color(0xFFD0E4FF),
            onPrimaryContainer = Color(0xFF001D33),
            secondary = Color(0xFF2F6B5C),
            onSecondary = Color.White,
            secondaryContainer = Color(0xFFB3E7D5),
            onSecondaryContainer = Color(0xFF002018),
            tertiary = Color(0xFF8B4A63),
            onTertiary = Color.White,
            background = Color(0xFFF7F9FC),
            onBackground = Color(0xFF181C20),
            surface = Color(0xFFFFFFFF),
            onSurface = Color(0xFF181C20),
            surfaceVariant = Color(0xFFE0E7EF),
            onSurfaceVariant = Color(0xFF40484F),
            outline = Color(0xFF70787F),
            outlineVariant = Color(0xFFC0C7CE),
            error = Color(0xFFBA1A1A),
            onError = Color.White
        )
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}
