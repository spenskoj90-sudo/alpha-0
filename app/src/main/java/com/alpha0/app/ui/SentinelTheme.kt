package com.alpha0.app.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import androidx.compose.ui.text.googlefonts.Font
import androidx.compose.ui.text.googlefonts.GoogleFont
import androidx.compose.ui.text.googlefonts.R

val SentinelBackground = Color(0xFF0B0E11)
val SentinelSurface = Color(0xFF14181D)
val SentinelCardBorder = Color(0xFF2A2F36)
val SentinelAmber = Color(0xFFE8A33D)
val SentinelSignal = Color(0xFF2FBF9F)
val SentinelDanger = Color(0xFFE5484D)
val SentinelTextPrimary = Color(0xFFF2F1EC)
val SentinelTextSecondary = Color(0xFF9AA0A6)

private val GoogleFontsProvider = GoogleFont.Provider(
    providerAuthority = "com.google.android.gms.fonts",
    providerPackage = "com.google.android.gms",
    certificates = R.array.com_google_android_gms_fonts_certs,
)

private val DisplayFont = FontFamily(
    Font(GoogleFont("Space Grotesk"), GoogleFontsProvider, FontWeight.Bold),
)

private val BodyFont = FontFamily(
    Font(GoogleFont("Inter"), GoogleFontsProvider, FontWeight.Normal),
    Font(GoogleFont("Inter"), GoogleFontsProvider, FontWeight.Medium),
)

private val DataFont = FontFamily(
    Font(GoogleFont("JetBrains Mono"), GoogleFontsProvider, FontWeight.Normal),
)

val SentinelDataStyle = TextStyle(
    fontFamily = DataFont,
    fontWeight = FontWeight.Normal,
    fontSize = 13.sp,
    letterSpacing = 0.sp,
)

private val SentinelTypography = Typography(
    displayLarge = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, letterSpacing = 1.5.sp),
    displayMedium = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, letterSpacing = 1.2.sp),
    displaySmall = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, letterSpacing = 1.0.sp),
    headlineLarge = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, letterSpacing = 1.2.sp),
    headlineMedium = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, letterSpacing = 1.0.sp),
    headlineSmall = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, letterSpacing = 0.8.sp),
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

private val SentinelColors = darkColorScheme(
    primary = SentinelAmber,
    onPrimary = SentinelBackground,
    background = SentinelBackground,
    onBackground = SentinelTextPrimary,
    surface = SentinelSurface,
    onSurface = SentinelTextPrimary,
    surfaceVariant = SentinelSurface,
    onSurfaceVariant = SentinelTextSecondary,
    error = SentinelDanger,
    onError = SentinelTextPrimary,
)

@Composable
fun SentinelTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = SentinelColors,
        typography = SentinelTypography,
        content = content,
    )
}
