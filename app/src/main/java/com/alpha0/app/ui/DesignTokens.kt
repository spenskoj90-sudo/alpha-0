package com.alpha0.app.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.googlefonts.Font
import androidx.compose.ui.text.googlefonts.GoogleFont
import androidx.compose.ui.unit.dp
import com.alpha0.app.R

object SentinelColors {
    val Background = Color(0xFF07121F)
    val Surface = Color(0xFF0D1B2A)
    val SurfaceRaised = Color(0xFF13263A)
    val Border = Color(0xFF27445D)
    val Primary = Color(0xFF70DBFF)
    val Signal = Color(0xFF5BE3D0)
    val Success = Color(0xFF61D6A7)
    val Danger = Color(0xFFFF6F82)
    val TextPrimary = Color(0xFFF1F8FC)
    val TextSecondary = Color(0xFF9EB4C5)
}

private val SentinelGoogleFontProvider = GoogleFont.Provider(
    providerAuthority = "com.google.android.gms.fonts",
    providerPackage = "com.google.android.gms",
    certificates = R.array.com_google_android_gms_fonts_certs,
)

val SentinelDisplayFont = FontFamily(
    Font(GoogleFont("Outfit"), fontProvider = SentinelGoogleFontProvider, weight = FontWeight.Medium),
    Font(GoogleFont("Outfit"), fontProvider = SentinelGoogleFontProvider, weight = FontWeight.SemiBold),
)
val SentinelBodyFont = FontFamily(
    Font(GoogleFont("Inter"), fontProvider = SentinelGoogleFontProvider, weight = FontWeight.Normal),
    Font(GoogleFont("Inter"), fontProvider = SentinelGoogleFontProvider, weight = FontWeight.Medium),
    Font(GoogleFont("Inter"), fontProvider = SentinelGoogleFontProvider, weight = FontWeight.SemiBold),
)
val SentinelDataFont = FontFamily(
    Font(GoogleFont("JetBrains Mono"), fontProvider = SentinelGoogleFontProvider, weight = FontWeight.Normal),
)

@Composable
fun DataText(text: String, modifier: Modifier = Modifier) {
    Text(
        text,
        modifier = modifier,
        style = MaterialTheme.typography.bodySmall.copy(fontFamily = SentinelDataFont),
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
}

@Composable
fun StatusBadge(text: String, active: Boolean = true, modifier: Modifier = Modifier) {
    val color = if (active) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.error
    Surface(
        modifier = modifier,
        color = color.copy(alpha = 0.12f),
        shape = RoundedCornerShape(10.dp),
        border = BorderStroke(1.dp, color.copy(alpha = 0.24f)),
    ) {
        Text(
            text = text,
            modifier = Modifier.padding(horizontal = 9.dp, vertical = 5.dp),
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
    val borderColor = if (scan) {
        MaterialTheme.colorScheme.secondary.copy(alpha = 0.42f)
    } else {
        MaterialTheme.colorScheme.outline.copy(alpha = 0.72f)
    }
    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        color = MaterialTheme.colorScheme.surface,
        tonalElevation = 1.dp,
        border = BorderStroke(1.dp, borderColor),
    ) {
        Box(modifier = Modifier.padding(20.dp), content = content)
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
    Button(
        onClick = onClick,
        modifier = modifier.heightIn(min = 52.dp),
        enabled = enabled,
        shape = RoundedCornerShape(16.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = MaterialTheme.colorScheme.primary,
            contentColor = MaterialTheme.colorScheme.onPrimary,
        ),
    ) {
        content?.invoke() ?: Text(text, style = MaterialTheme.typography.labelLarge)
    }
}

@Composable
fun DangerButton(text: String, onClick: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true) {
    OutlinedButton(
        onClick = onClick,
        modifier = modifier.heightIn(min = 52.dp),
        enabled = enabled,
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.error.copy(alpha = 0.72f)),
        colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error),
    ) {
        Text(text, style = MaterialTheme.typography.labelLarge)
    }
}
