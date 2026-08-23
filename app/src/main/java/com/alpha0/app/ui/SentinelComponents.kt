package com.alpha0.app.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.matchParentSize
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.unit.dp
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.shape.RoundedCornerShape

@Composable
fun SentinelCard(
    modifier: Modifier = Modifier,
    scanOnce: Boolean = false,
    cornerMarks: Boolean = false,
    content: @Composable BoxScope.() -> Unit,
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = SentinelSurface),
        border = androidx.compose.foundation.BorderStroke(1.dp, SentinelCardBorder),
    ) {
        Box(modifier = Modifier.fillMaxSize()) {
            content()
            if (cornerMarks || scanOnce) {
                val scanProgress = remember { Animatable(if (scanOnce) 0f else 1f) }
                if (scanOnce) {
                    LaunchedEffect(Unit) {
                        scanProgress.animateTo(1f, animationSpec = tween(380))
                    }
                }
                Canvas(modifier = Modifier.matchParentSize()) {
                    val mark = 12.dp.toPx()
                    val stroke = 1.dp.toPx()
                    val inset = 1.dp.toPx()
                    if (cornerMarks) {
                        drawLine(SentinelAmber, Offset(inset, inset), Offset(inset + mark, inset), stroke, StrokeCap.Square)
                        drawLine(SentinelAmber, Offset(inset, inset), Offset(inset, inset + mark), stroke, StrokeCap.Square)
                        drawLine(SentinelAmber, Offset(size.width - inset, inset), Offset(size.width - inset - mark, inset), stroke, StrokeCap.Square)
                        drawLine(SentinelAmber, Offset(size.width - inset, inset), Offset(size.width - inset, inset + mark), stroke, StrokeCap.Square)
                        drawLine(SentinelAmber, Offset(inset, size.height - inset), Offset(inset + mark, size.height - inset), stroke, StrokeCap.Square)
                        drawLine(SentinelAmber, Offset(inset, size.height - inset), Offset(inset, size.height - inset - mark), stroke, StrokeCap.Square)
                        drawLine(SentinelAmber, Offset(size.width - inset, size.height - inset), Offset(size.width - inset - mark, size.height - inset), stroke, StrokeCap.Square)
                        drawLine(SentinelAmber, Offset(size.width - inset, size.height - inset), Offset(size.width - inset, size.height - inset - mark), stroke, StrokeCap.Square)
                    }
                    if (scanOnce) {
                        val y = size.height * scanProgress.value
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
    }
}

@Composable
fun DataText(text: String, modifier: Modifier = Modifier) {
    androidx.compose.material3.Text(
        text = text,
        modifier = modifier,
        style = SentinelDataStyle,
        color = MaterialTheme.colorScheme.onSurface,
    )
}
