package com.alpha0.app.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.googlefonts.Font
import androidx.compose.ui.text.googlefonts.GoogleFont
import androidx.compose.ui.unit.sp

val SentinelBackground = Color(0xFF0B0E11)
val SentinelSurface = Color(0xFF14181D)
val SentinelBorder = Color(0xFF2A2F36)
val SentinelAmber = Color(0xFFE8A33D)
val SentinelSignal = Color(0xFF2FBF9F)
val SentinelDanger = Color(0xFFE5484D)
val SentinelTextPrimary = Color(0xFFF2F1EC)
val SentinelTextSecondary = Color(0xFF9AA0A6)

private val SentinelColors = darkColorScheme(
    primary = SentinelAmber,
    onPrimary = SentinelBackground,
    secondary = SentinelSignal,
    onSecondary = SentinelBackground,
    error = SentinelDanger,
    onError = SentinelTextPrimary,
    background = SentinelBackground,
    surface = SentinelSurface,
    surfaceVariant = SentinelSurface,
    outline = SentinelBorder,
    onBackground = SentinelTextPrimary,
    onSurface = SentinelTextPrimary,
    onSurfaceVariant = SentinelTextSecondary,
)

private val DisplayFont = FontFamily(
    Font(googleFont = GoogleFont("Space Grotesk"), weight = FontWeight.Bold)
)
private val BodyFont = FontFamily(
    Font(googleFont = GoogleFont("Inter"), weight = FontWeight.Normal),
    Font(googleFont = GoogleFont("Inter"), weight = FontWeight.Medium),
)
val SentinelMonoFont = FontFamily(
    Font(googleFont = GoogleFont("JetBrains Mono"), weight = FontWeight.Normal)
)

private val SentinelTypography = Typography(
    displayLarge = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, letterSpacing = 1.4.sp),
    displayMedium = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, letterSpacing = 1.1.sp),
    displaySmall = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, letterSpacing = 0.9.sp),
    headlineLarge = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, letterSpacing = 1.0.sp),
    headlineMedium = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, letterSpacing = 0.8.sp),
    headlineSmall = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, letterSpacing = 0.6.sp),
    titleLarge = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Medium),
    titleMedium = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Medium),
    titleSmall = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Medium),
    bodyLarge = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Normal),
    bodyMedium = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Normal),
    bodySmall = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Normal),
    labelLarge = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Medium),
    labelMedium = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Medium),
    labelSmall = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Medium),
)

val SentinelDataStyle = TextStyle(
    fontFamily = SentinelMonoFont,
    fontWeight = FontWeight.Normal,
    color = SentinelTextSecondary,
)

@Composable
fun SentinelTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = SentinelColors,
        typography = SentinelTypography,
        content = content,
    )
}
