package com.alpha0.app.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

private val SentinelDarkColorScheme = darkColorScheme(
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

private val SentinelLightColorScheme = lightColorScheme(
    primary = Color(0xFF6C20B5),
    onPrimary = Color.White,
    secondary = Color(0xFF006875),
    tertiary = Color(0xFF006875),
    background = Color(0xFFF7F7FB),
    surface = Color(0xFFFFFFFF),
    surfaceVariant = Color(0xFFECECF3),
    onBackground = Color(0xFF17131C),
    onSurface = Color(0xFF17131C),
    onSurfaceVariant = Color(0xFF5E5867),
    outline = Color(0xFF7B7483),
    error = Color(0xFFBA1A1A),
    onError = Color.White,
)

private val SentinelTypography = androidx.compose.material3.Typography(
    headlineLarge = TextStyle(fontFamily = SentinelDisplayFont, fontWeight = FontWeight.SemiBold, fontSize = 30.sp, letterSpacing = 1.5.sp),
    headlineMedium = TextStyle(fontFamily = SentinelDisplayFont, fontWeight = FontWeight.SemiBold, fontSize = 24.sp, letterSpacing = 1.2.sp),
    headlineSmall = TextStyle(fontFamily = SentinelDisplayFont, fontWeight = FontWeight.Medium, fontSize = 20.sp, letterSpacing = 0.8.sp),
    titleLarge = TextStyle(fontFamily = SentinelDisplayFont, fontWeight = FontWeight.Medium, fontSize = 20.sp),
    titleMedium = TextStyle(fontFamily = SentinelBodyFont, fontWeight = FontWeight.Medium, fontSize = 16.sp),
    bodyLarge = TextStyle(fontFamily = SentinelBodyFont, fontWeight = FontWeight.Normal, fontSize = 16.sp),
    bodyMedium = TextStyle(fontFamily = SentinelBodyFont, fontWeight = FontWeight.Normal, fontSize = 14.sp),
    bodySmall = TextStyle(fontFamily = SentinelBodyFont, fontWeight = FontWeight.Normal, fontSize = 12.sp),
    labelLarge = TextStyle(fontFamily = SentinelBodyFont, fontWeight = FontWeight.Medium, fontSize = 13.sp, letterSpacing = 0.6.sp),
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
