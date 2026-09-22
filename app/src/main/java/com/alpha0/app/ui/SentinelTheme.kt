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
    onPrimary = Color(0xFF06151F),
    secondary = SentinelColors.Signal,
    onSecondary = Color(0xFF001A17),
    tertiary = SentinelColors.Success,
    onTertiary = Color(0xFF041812),
    background = SentinelColors.Background,
    surface = SentinelColors.Surface,
    surfaceVariant = SentinelColors.SurfaceRaised,
    onBackground = SentinelColors.TextPrimary,
    onSurface = SentinelColors.TextPrimary,
    onSurfaceVariant = SentinelColors.TextSecondary,
    outline = SentinelColors.Border,
    outlineVariant = SentinelColors.BorderStrong,
    error = SentinelColors.Danger,
    onError = Color(0xFF24040A),
)

private val SentinelLightColorScheme = lightColorScheme(
    primary = Color(0xFF006C88),
    onPrimary = Color.White,
    secondary = Color(0xFF0B6F67),
    onSecondary = Color.White,
    tertiary = Color(0xFF147251),
    onTertiary = Color.White,
    background = Color(0xFFF4F8FB),
    surface = Color.White,
    surfaceVariant = Color(0xFFEAF1F6),
    onBackground = Color(0xFF10202B),
    onSurface = Color(0xFF10202B),
    onSurfaceVariant = Color(0xFF506875),
    outline = Color(0xFFB8C8D3),
    outlineVariant = Color(0xFF8299A8),
    error = Color(0xFFB4233A),
    onError = Color.White,
)

private val SentinelTypography = androidx.compose.material3.Typography(
    displayLarge = TextStyle(fontFamily = SentinelDisplayFont, fontWeight = FontWeight.SemiBold, fontSize = 32.sp, lineHeight = 40.sp),
    headlineLarge = TextStyle(fontFamily = SentinelDisplayFont, fontWeight = FontWeight.SemiBold, fontSize = 28.sp, lineHeight = 36.sp),
    headlineMedium = TextStyle(fontFamily = SentinelDisplayFont, fontWeight = FontWeight.SemiBold, fontSize = 22.sp, lineHeight = 30.sp),
    headlineSmall = TextStyle(fontFamily = SentinelDisplayFont, fontWeight = FontWeight.SemiBold, fontSize = 18.sp, lineHeight = 26.sp),
    titleLarge = TextStyle(fontFamily = SentinelBodyFont, fontWeight = FontWeight.SemiBold, fontSize = 16.sp, lineHeight = 24.sp),
    titleMedium = TextStyle(fontFamily = SentinelBodyFont, fontWeight = FontWeight.SemiBold, fontSize = 16.sp, lineHeight = 24.sp),
    bodyLarge = TextStyle(fontFamily = SentinelBodyFont, fontWeight = FontWeight.Normal, fontSize = 16.sp, lineHeight = 24.sp),
    bodyMedium = TextStyle(fontFamily = SentinelBodyFont, fontWeight = FontWeight.Normal, fontSize = 14.sp, lineHeight = 21.sp),
    bodySmall = TextStyle(fontFamily = SentinelBodyFont, fontWeight = FontWeight.Normal, fontSize = 12.sp, lineHeight = 18.sp),
    labelLarge = TextStyle(fontFamily = SentinelBodyFont, fontWeight = FontWeight.SemiBold, fontSize = 13.sp, lineHeight = 18.sp),
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
