package com.alpha0.app.ui

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.googlefonts.Font
import androidx.compose.ui.text.googlefonts.GoogleFont
import androidx.compose.ui.text.googlefonts.GoogleFont.Provider
import androidx.compose.ui.unit.dp
import androidx.compose.ui.text.googlefonts.R as GoogleFontsR

object SentinelColors {
    val Background = Color(0xFF0D1117)
    val Surface = Color(0xFF161B22)
    val Border = Color(0xFF30363D)
    val Primary = Color(0xFFB356FF)
    val Signal = Color(0xFF00E5FF)
    val Danger = Color(0xFFFF3366)
    val TextPrimary = Color(0xFFF0F6FC)
    val TextSecondary = Color(0xFF8B949E)
}

private val GoogleFontsProvider = Provider(
    providerAuthority = "com.google.android.gms.fonts",
    providerPackage = "com.google.android.gms",
    certificates = GoogleFontsR.array.com_google_android_gms_fonts_certs,
)

val SentinelDisplayFont = FontFamily(
    Font(GoogleFont("Outfit"), GoogleFontsProvider, weight = FontWeight.Medium),
    Font(GoogleFont("Outfit"), GoogleFontsProvider, weight = FontWeight.SemiBold),
)
val SentinelBodyFont = FontFamily(
    Font(GoogleFont("Inter"), GoogleFontsProvider, weight = FontWeight.Normal),
    Font(GoogleFont("Inter"), GoogleFontsProvider, weight = FontWeight.Medium),
)
val SentinelDataFont = FontFamily(
    Font(GoogleFont("JetBrains Mono"), GoogleFontsProvider, weight = FontWeight.Normal),
)

@Composable
fun DataText(text: String, modifier: Modifier = Modifier) {
    Text(text, modifier = modifier, style = MaterialTheme.typography.bodySmall.copy(fontFamily = SentinelDataFont), color = SentinelColors.TextSecondary)
}

@Composable
fun StatusBadge(text: String, active: Boolean = true, modifier: Modifier = Modifier) {
    val color = if (active) SentinelColors.Signal else SentinelColors.Danger
    Surface(modifier = modifier, color = color.copy(alpha = 0.15f), shape = RoundedCornerShape(50)) {
        Text(
            text = text.uppercase(),
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
            color = color,
            style = MaterialTheme.typography.labelLarge,
        )
    }
}

@Composable
fun SentinelCard(
    modifier: Modifier = Modifier,
    scan: Boolean = false,
    content: @Composable BoxScope.() -> Unit,
) {
    val shape = RoundedCornerShape(4.dp)
    Box(
        modifier = modifier
            .fillMaxWidth()
            .clip(shape)
            .background(SentinelColors.Surface)
            .border(BorderStroke(1.dp, SentinelColors.Border), shape)
            .padding(start = 2.dp),
    ) {
        Box(modifier = Modifier.padding(16.dp), content = content)
        if (scan) {
            var heightPx by remember { mutableStateOf(0) }
            var started by remember { mutableStateOf(false) }
            val progress = remember { Animatable(0f) }
            LaunchedEffect(heightPx) {
                if (heightPx > 0 && !started) {
                    started = true
                    progress.snapTo(0f)
                    progress.animateTo(1f, animationSpec = tween(1000))
                }
            }
            Canvas(
                modifier = Modifier
                    .fillMaxSize()
                    .onSizeChanged { heightPx = it.height },
            ) {
                drawLine(
                    color = SentinelColors.Primary,
                    start = Offset(0f, size.height * progress.value),
                    end = Offset(size.width, size.height * progress.value),
                    strokeWidth = 1.dp.toPx(),
                    alpha = 0.9f,
                )
            }
        }
    }
}

@Composable
fun PrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    content: @Composable (() -> Unit)? = null,
) {
    androidx.compose.material3.Button(
        onClick = onClick,
        modifier = modifier,
        enabled = enabled,
        shape = RoundedCornerShape(14.dp),
        colors = ButtonDefaults.buttonColors(containerColor = SentinelColors.Primary, contentColor = SentinelColors.TextPrimary),
    ) {
        content?.invoke() ?: Text(text)
    }
}

@Composable
fun DangerButton(text: String, onClick: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true) {
    OutlinedButton(
        onClick = onClick,
        modifier = modifier,
        enabled = enabled,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, SentinelColors.Danger),
        colors = ButtonDefaults.outlinedButtonColors(contentColor = SentinelColors.Danger),
    ) { Text(text) }
}
