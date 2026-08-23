package com.alpha0.app.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

private val SentinelColorScheme = darkColorScheme(
    primary = SentinelColors.Primary,
    onPrimary = SentinelColors.TextPrimary,
    secondary = SentinelColors.Signal,
    background = SentinelColors.Background,
    surface = SentinelColors.Surface,
    surfaceVariant = SentinelColors.Surface,
    onBackground = SentinelColors.TextPrimary,
    onSurface = SentinelColors.TextPrimary,
    outline = SentinelColors.Border,
    error = SentinelColors.Danger,
    onError = SentinelColors.TextPrimary,
)

private val SentinelTypography = androidx.compose.material3.Typography(
    headlineLarge = TextStyle(fontFamily = SentinelDisplayFont, fontWeight = FontWeight.SemiBold, fontSize = 30.sp, letterSpacing = 1.5.sp),
    headlineMedium = TextStyle(fontFamily = SentinelDisplayFont, fontWeight = FontWeight.SemiBold, fontSize = 24.sp, letterSpacing = 1.2.sp),
    headlineSmall = TextStyle(fontFamily = SentinelDisplayFont, fontWeight = FontWeight.Medium, fontSize = 20.sp, letterSpacing = 0.8.sp),
    titleLarge = TextStyle(fontFamily = SentinelDisplayFont, fontWeight = FontWeight.Medium, fontSize = 20.sp),
    titleMedium = TextStyle(fontFamily = SentinelBodyFont, fontWeight = FontWeight.Medium, fontSize = 16.sp),
    bodyLarge = TextStyle(fontFamily = SentinelBodyFont, fontWeight = FontWeight.Normal, fontSize = 16.sp, color = SentinelColors.TextPrimary),
    bodyMedium = TextStyle(fontFamily = SentinelBodyFont, fontWeight = FontWeight.Normal, fontSize = 14.sp, color = SentinelColors.TextPrimary),
    bodySmall = TextStyle(fontFamily = SentinelBodyFont, fontWeight = FontWeight.Normal, fontSize = 12.sp, color = SentinelColors.TextSecondary),
    labelLarge = TextStyle(fontFamily = SentinelBodyFont, fontWeight = FontWeight.Medium, fontSize = 13.sp, letterSpacing = 0.6.sp),
)

@Composable
fun SentinelTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = SentinelColorScheme, typography = SentinelTypography, content = content)
}
