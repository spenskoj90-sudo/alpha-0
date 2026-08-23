package com.alpha0.app.ui

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.unit.dp

@Composable
fun SentinelCard(
    modifier: Modifier = Modifier,
    cornerMarks: Boolean = false,
    scanOnce: Boolean = false,
    content: @Composable BoxScope.() -> Unit,
) {
    val progress = remember { Animatable(0f) }

    if (scanOnce) {
        LaunchedEffect(Unit) {
            progress.snapTo(0f)
            progress.animateTo(1f, animationSpec = tween(durationMillis = 380))
        }
    }

    Box(
        modifier = modifier
            .clip(RoundedCornerShape(8.dp))
            .background(SentinelSurface)
            .border(1.dp, SentinelBorder, RoundedCornerShape(8.dp)),
        content = content,
    ) {
        if (cornerMarks) {
            CornerMarks()
        }
        if (scanOnce) {
            Canvas(modifier = Modifier.matchParentSize()) {
                val y = size.height * progress.value
                drawLine(
                    color = SentinelAmber.copy(alpha = 0.6f),
                    start = Offset(0f, y),
                    end = Offset(size.width, y),
                    strokeWidth = 2.dp.toPx(),
                    cap = StrokeCap.Square,
                )
            }
        }
    }
}

@Composable
private fun BoxScope.CornerMarks() {
    Canvas(modifier = Modifier.matchParentSize()) {
        val length = 12.dp.toPx()
        val stroke = 1.dp.toPx()
        val w = size.width
        val h = size.height
        val c = SentinelAmber

        drawLine(c, Offset(0f, length), Offset(0f, 0f), strokeWidth = stroke)
        drawLine(c, Offset(0f, 0f), Offset(length, 0f), strokeWidth = stroke)
        drawLine(c, Offset(w - length, 0f), Offset(w, 0f), strokeWidth = stroke)
        drawLine(c, Offset(w, 0f), Offset(w, length), strokeWidth = stroke)
        drawLine(c, Offset(0f, h - length), Offset(0f, h), strokeWidth = stroke)
        drawLine(c, Offset(0f, h), Offset(length, h), strokeWidth = stroke)
        drawLine(c, Offset(w - length, h), Offset(w, h), strokeWidth = stroke)
        drawLine(c, Offset(w, h - length), Offset(w, h), strokeWidth = stroke)
    }
}
