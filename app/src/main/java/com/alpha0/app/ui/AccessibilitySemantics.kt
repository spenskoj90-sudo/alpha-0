package com.alpha0.app.ui

import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics

/** Accessibility semantics shared by SENTINEL Compose surfaces. */
fun Modifier.politeStatusSemantics(): Modifier = semantics {
    liveRegion = LiveRegionMode.Polite
}

fun Modifier.assertiveStatusSemantics(): Modifier = semantics {
    liveRegion = LiveRegionMode.Assertive
}

fun Modifier.progressStatusSemantics(label: String): Modifier = semantics {
    contentDescription = label
    liveRegion = LiveRegionMode.Polite
}

fun Modifier.buttonCardSemantics(label: String): Modifier = semantics {
    role = Role.Button
    contentDescription = label
}
