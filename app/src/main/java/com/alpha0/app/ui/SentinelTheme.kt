package com.alpha0.app.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val SentinelColors = darkColorScheme(
    primary = Color(0xFF9ACB52),
    secondary = Color(0xFF4CA3FF),
    background = Color(0xFF070A0D),
    surface = Color(0xFF0D1217),
    surfaceVariant = Color(0xFF111820),
    onBackground = Color(0xFFE7EDF2),
    onSurface = Color(0xFFE7EDF2),
)

@Composable
fun SentinelTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = SentinelColors, content = content)
}
