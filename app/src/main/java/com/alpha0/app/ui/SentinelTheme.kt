package com.alpha0.app.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

private val SentinelDarkColorScheme = darkColorScheme(
    primary = SentinelColors.Primary,
    onPrimary = Color(0xFF04131E),
    secondary = SentinelColors.Signal,
    onSecondary = Color(0xFF031814),
    tertiary = SentinelColors.Success,
    onTertiary = Color(0xFF041812),
    background = SentinelColors.Background,
    surface = SentinelColors.Surface,
    surfaceVariant = SentinelColors.SurfaceRaised,
    onBackground = SentinelColors.TextPrimary,
    onSurface = SentinelColors.TextPrimary,
    onSurfaceVariant = SentinelColors.TextSecondary,
    outline = SentinelColors.Border,
    error = SentinelColors.Danger,
    onError = Color(0xFF24040A),
)

private val SentinelLightColorScheme = lightColorScheme(
    primary = Color(0xFF006A86),
    onPrimary = Color.White,
    secondary = Color(0xFF006B60),
    onSecondary = Color.White,
    tertiary = Color(0xFF196B4F),
    onTertiary = Color.White,
    background = Color(0xFFF5FAFD),
    surface = Color(0xFFFFFFFF),
    surfaceVariant = Color(0xFFE7F0F5),
    onBackground = Color(0xFF0F1B24),
    onSurface = Color(0xFF0F1B24),
    onSurfaceVariant = Color(0xFF506270),
    outline = Color(0xFF78909F),
    error = Color(0xFFBA1A1A),
    onError = Color.White,
)

private val SentinelTypography = androidx.compose.material3.Typography(
    headlineLarge = TextStyle(fontFamily = SentinelDisplayFont, fontWeight = FontWeight.SemiBold, fontSize = 30.sp, lineHeight = 36.sp),
    headlineMedium = TextStyle(fontFamily = SentinelDisplayFont, fontWeight = FontWeight.SemiBold, fontSize = 24.sp, lineHeight = 30.sp),
    headlineSmall = TextStyle(fontFamily = SentinelDisplayFont, fontWeight = FontWeight.Medium, fontSize = 20.sp, lineHeight = 26.sp),
    titleLarge = TextStyle(fontFamily = SentinelDisplayFont, fontWeight = FontWeight.SemiBold, fontSize = 20.sp),
    titleMedium = TextStyle(fontFamily = SentinelBodyFont, fontWeight = FontWeight.SemiBold, fontSize = 16.sp),
    bodyLarge = TextStyle(fontFamily = SentinelBodyFont, fontWeight = FontWeight.Normal, fontSize = 16.sp, lineHeight = 24.sp),
    bodyMedium = TextStyle(fontFamily = SentinelBodyFont, fontWeight = FontWeight.Normal, fontSize = 14.sp, lineHeight = 21.sp),
    bodySmall = TextStyle(fontFamily = SentinelBodyFont, fontWeight = FontWeight.Normal, fontSize = 12.sp, lineHeight = 18.sp),
    labelLarge = TextStyle(fontFamily = SentinelBodyFont, fontWeight = FontWeight.SemiBold, fontSize = 13.sp, letterSpacing = 0.2.sp),
)

@Composable
fun SentinelTheme(mode: AppThemeMode = AppThemeMode.SYSTEM, content: @Composable () -> Unit) {
    val dark = when (mode) {
        AppThemeMode.SYSTEM -> isSystemInDarkTheme()
        AppThemeMode.LIGHT -> false
        AppThemeMode.DARK -> true
    }
    MaterialTheme(
        colorScheme = if (dark) SentinelDarkColorScheme else SentinelLightColorScheme,
        typography = SentinelTypography,
        content = content,
    )
}
