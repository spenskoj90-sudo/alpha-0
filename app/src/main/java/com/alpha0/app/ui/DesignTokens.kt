package com.alpha0.app.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.googlefonts.Font
import androidx.compose.ui.text.googlefonts.GoogleFont
import androidx.compose.ui.unit.dp
import com.alpha0.app.R

/**
 * SENTINEL Design System v2.1.
 *
 * Semantics come from Design System v2. The visual identity is the Owner-approved
 * shield/S/signal direction: deep naval surfaces, restrained cyan/teal signal,
 * no ambient HUD decoration and no color-only security state.
 */
object SentinelColors {
    val Background = Color(0xFF061018)
    val Surface = Color(0xFF0D1B29)
    val SurfaceRaised = Color(0xFF13263A)
    val SurfaceSunken = Color(0xFF091722)
    val Border = Color(0xFF29485F)
    val BorderStrong = Color(0xFF3A627D)
    val Primary = Color(0xFF2DD4FF)
    val Signal = Color(0xFF00E0C2)
    val Success = Color(0xFF22C55E)
    val Warning = Color(0xFFF59E0B)
    val Danger = Color(0xFFF43F5E)
    val TextPrimary = Color(0xFFE6F1F7)
    val TextSecondary = Color(0xFFA6B7C5)
    val TextTertiary = Color(0xFF7F95A4)
    val Disabled = Color(0xFF657783)
    val Focus = Color(0xFF91E7FF)
}

private val SentinelGoogleFontProvider = GoogleFont.Provider(
    providerAuthority = "com.google.android.gms.fonts",
    providerPackage = "com.google.android.gms",
    certificates = R.array.com_google_android_gms_fonts_certs,
)

val SentinelDisplayFont = FontFamily(
    Font(GoogleFont("Onest"), fontProvider = SentinelGoogleFontProvider, weight = FontWeight.Medium),
    Font(GoogleFont("Onest"), fontProvider = SentinelGoogleFontProvider, weight = FontWeight.SemiBold),
)
val SentinelBodyFont = FontFamily(
    Font(GoogleFont("Inter"), fontProvider = SentinelGoogleFontProvider, weight = FontWeight.Normal),
    Font(GoogleFont("Inter"), fontProvider = SentinelGoogleFontProvider, weight = FontWeight.Medium),
    Font(GoogleFont("Inter"), fontProvider = SentinelGoogleFontProvider, weight = FontWeight.SemiBold),
)
val SentinelDataFont = FontFamily(
    Font(GoogleFont("JetBrains Mono"), fontProvider = SentinelGoogleFontProvider, weight = FontWeight.Normal),
    Font(GoogleFont("JetBrains Mono"), fontProvider = SentinelGoogleFontProvider, weight = FontWeight.Medium),
)

enum class SentinelStatus {
    VERIFIED,
    ACTIVE,
    PENDING,
    WARNING,
    DENIED,
    REVOKED,
    FAILED,
    UNKNOWN,
    UNAVAILABLE,
    STOPPED,
}

enum class SentinelCardKind {
    CONTENT,
    OPERATIONAL,
    SECURITY,
    DEVICE,
    RECOMMENDATION,
}

fun statusFromRaw(value: String?): SentinelStatus {
    return when (value?.trim()?.uppercase()) {
        "VERIFIED", "OK", "HEALTHY" -> SentinelStatus.VERIFIED
        "ACTIVE", "READY", "DELIVERED", "CURRENT" -> SentinelStatus.ACTIVE
        "PENDING", "CHECKING", "DOWNLOADING", "DELIVERING" -> SentinelStatus.PENDING
        "WARNING", "DEGRADED", "PAST_DUE", "ATTENTION" -> SentinelStatus.WARNING
        "DENIED", "BLOCKED" -> SentinelStatus.DENIED
        "REVOKED", "CANCELED", "EXPIRED" -> SentinelStatus.REVOKED
        "FAILED", "ERROR", "AT_RISK" -> SentinelStatus.FAILED
        "UNAVAILABLE", "OFFLINE", "PLAY_REQUIRED" -> SentinelStatus.UNAVAILABLE
        "STOPPED", "IDLE" -> SentinelStatus.STOPPED
        else -> SentinelStatus.UNKNOWN
    }
}

private fun SentinelStatus.color(): Color = when (this) {
    SentinelStatus.VERIFIED -> SentinelColors.Success
    SentinelStatus.ACTIVE -> SentinelColors.Primary
    SentinelStatus.PENDING, SentinelStatus.WARNING -> SentinelColors.Warning
    SentinelStatus.DENIED, SentinelStatus.REVOKED, SentinelStatus.FAILED -> SentinelColors.Danger
    SentinelStatus.UNKNOWN, SentinelStatus.UNAVAILABLE, SentinelStatus.STOPPED -> SentinelColors.TextTertiary
}

private fun SentinelStatus.glyph(): String = when (this) {
    SentinelStatus.VERIFIED -> "✓"
    SentinelStatus.ACTIVE -> "●"
    SentinelStatus.PENDING -> "◷"
    SentinelStatus.WARNING -> "!"
    SentinelStatus.DENIED -> "×"
    SentinelStatus.REVOKED -> "×"
    SentinelStatus.FAILED -> "!"
    SentinelStatus.UNKNOWN -> "?"
    SentinelStatus.UNAVAILABLE -> "—"
    SentinelStatus.STOPPED -> "■"
}

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
fun StatusBadge(
    text: String,
    status: SentinelStatus,
    modifier: Modifier = Modifier,
) {
    val color = status.color()
    Surface(
        modifier = modifier,
        color = color.copy(alpha = 0.09f),
        shape = RoundedCornerShape(8.dp),
        border = BorderStroke(1.dp, color.copy(alpha = 0.48f)),
    ) {
        Row(modifier = Modifier.padding(horizontal = 9.dp, vertical = 5.dp)) {
            Text(status.glyph(), color = color, style = MaterialTheme.typography.labelLarge)
            Spacer(Modifier.width(6.dp))
            Text(text = text, color = color, style = MaterialTheme.typography.labelLarge)
        }
    }
}

@Composable
fun SentinelCard(
    modifier: Modifier = Modifier,
    kind: SentinelCardKind = SentinelCardKind.CONTENT,
    content: @Composable BoxScope.() -> Unit,
) {
    val border = when (kind) {
        SentinelCardKind.SECURITY, SentinelCardKind.DEVICE -> MaterialTheme.colorScheme.primary.copy(alpha = 0.30f)
        SentinelCardKind.OPERATIONAL -> MaterialTheme.colorScheme.outline.copy(alpha = 0.78f)
        SentinelCardKind.RECOMMENDATION -> MaterialTheme.colorScheme.secondary.copy(alpha = 0.38f)
        SentinelCardKind.CONTENT -> MaterialTheme.colorScheme.outline.copy(alpha = 0.62f)
    }
    val background = when (kind) {
        SentinelCardKind.SECURITY, SentinelCardKind.DEVICE, SentinelCardKind.RECOMMENDATION ->
            MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.42f)
        else -> MaterialTheme.colorScheme.surface
    }
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(18.dp),
        color = background,
        tonalElevation = 0.dp,
        shadowElevation = 1.dp,
        border = BorderStroke(1.dp, border),
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
        shape = RoundedCornerShape(12.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = MaterialTheme.colorScheme.primary,
            contentColor = MaterialTheme.colorScheme.onPrimary,
        ),
    ) {
        content?.invoke() ?: Text(text, style = MaterialTheme.typography.labelLarge)
    }
}

@Composable
fun SecondaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    Button(
        onClick = onClick,
        modifier = modifier.heightIn(min = 48.dp),
        enabled = enabled,
        shape = RoundedCornerShape(12.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
            contentColor = MaterialTheme.colorScheme.onSurface,
        ),
    ) {
        Text(text, style = MaterialTheme.typography.labelLarge)
    }
}

@Composable
fun GhostButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    TextButton(
        onClick = onClick,
        modifier = modifier.heightIn(min = 48.dp),
        enabled = enabled,
        shape = RoundedCornerShape(12.dp),
    ) {
        Text(text, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.secondary)
    }
}

@Composable
fun DangerButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    OutlinedButton(
        onClick = onClick,
        modifier = modifier.heightIn(min = 52.dp),
        enabled = enabled,
        shape = RoundedCornerShape(12.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.error.copy(alpha = 0.82f)),
        colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error),
    ) {
        Text(text, style = MaterialTheme.typography.labelLarge)
    }
}
