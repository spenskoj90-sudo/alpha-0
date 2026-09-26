package com.alpha0.app.ui

import androidx.annotation.DrawableRes
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.alpha0.app.R

data class AppDestination(
    val route: String,
    val labelKey: String,
    @DrawableRes val iconRes: Int,
)

val PrimaryDestinations = listOf(
    AppDestination("home", "home", R.drawable.ic_domain_home),
    AppDestination("games", "games", R.drawable.ic_domain_games),
    AppDestination("security", "security", R.drawable.ic_domain_security),
    AppDestination("activity", "activity", R.drawable.ic_domain_activity),
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SentinelTopBar(
    title: String,
    canGoBack: Boolean,
    onBack: () -> Unit,
    onNavigate: (String) -> Unit,
    compact: Boolean = false,
    compactContext: String? = null,
    compactActionLabel: String? = null,
    onCompactAction: (() -> Unit)? = null,
) {
    val strings = LocalAppStrings.current
    var expanded by remember { mutableStateOf(false) }
    val menuEntries = listOf(
        "settings" to "settings",
        "updates" to "updates",
        "help" to "help",
        "about" to "about",
    )

    if (compact) {
        Surface(
            color = MaterialTheme.colorScheme.background,
            contentColor = MaterialTheme.colorScheme.onBackground,
            tonalElevation = 0.dp,
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 48.dp)
                    .padding(horizontal = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                if (canGoBack) {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = strings.text("back"))
                    }
                }
                Text(
                    text = title,
                    modifier = Modifier.padding(start = if (canGoBack) 0.dp else 12.dp),
                    style = MaterialTheme.typography.titleMedium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                if (!compactContext.isNullOrBlank()) {
                    Text(
                        text = compactContext,
                        modifier = Modifier
                            .weight(1f)
                            .padding(start = 12.dp),
                        style = MaterialTheme.typography.bodySmall.copy(fontFamily = SentinelDataFont),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                } else {
                    Box(modifier = Modifier.weight(1f))
                }
                if (!compactActionLabel.isNullOrBlank() && onCompactAction != null) {
                    TextButton(
                        onClick = onCompactAction,
                        modifier = Modifier.heightIn(min = 48.dp),
                    ) {
                        Text(
                            compactActionLabel,
                            style = MaterialTheme.typography.labelMedium,
                            maxLines = 1,
                        )
                    }
                }
                Box {
                    IconButton(onClick = { expanded = true }) {
                        Icon(Icons.Default.MoreVert, contentDescription = strings.text("menu"))
                    }
                    DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                        menuEntries.forEach { (route, label) ->
                            DropdownMenuItem(
                                text = { Text(strings.text(label)) },
                                onClick = {
                                    expanded = false
                                    onNavigate(route)
                                },
                            )
                        }
                    }
                }
            }
        }
    } else {
        TopAppBar(
            title = { Text(title, style = MaterialTheme.typography.titleLarge) },
            colors = TopAppBarDefaults.topAppBarColors(
                containerColor = MaterialTheme.colorScheme.background,
                titleContentColor = MaterialTheme.colorScheme.onBackground,
                navigationIconContentColor = MaterialTheme.colorScheme.onBackground,
                actionIconContentColor = MaterialTheme.colorScheme.onSurfaceVariant,
            ),
            navigationIcon = {
                if (canGoBack) {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = strings.text("back"))
                    }
                }
            },
            actions = {
                IconButton(onClick = { expanded = true }) {
                    Icon(Icons.Default.MoreVert, contentDescription = strings.text("menu"))
                }
                DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                    menuEntries.forEach { (route, label) ->
                        DropdownMenuItem(
                            text = { Text(strings.text(label)) },
                            onClick = {
                                expanded = false
                                onNavigate(route)
                            },
                        )
                    }
                }
            },
        )
    }
}

@Composable
fun SentinelSideRail(selectedRoute: String?, onNavigate: (String) -> Unit) {
    val strings = LocalAppStrings.current
    Surface(
        color = MaterialTheme.colorScheme.surface,
        contentColor = MaterialTheme.colorScheme.onSurface,
        tonalElevation = 0.dp,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.72f)),
    ) {
        Column(
            modifier = Modifier
                .fillMaxHeight()
                .width(72.dp)
                .navigationBarsPadding()
                .padding(vertical = 4.dp)
                .selectableGroup(),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.SpaceEvenly,
        ) {
            PrimaryDestinations.forEach { destination ->
                val selected = selectedRoute == destination.route
                Column(
                    modifier = Modifier
                        .width(68.dp)
                        .heightIn(min = 48.dp)
                        .selectable(
                            selected = selected,
                            role = Role.Tab,
                            onClick = { onNavigate(destination.route) },
                        )
                        .padding(horizontal = 3.dp, vertical = 2.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center,
                ) {
                    Box(
                        Modifier
                            .width(if (selected) 24.dp else 12.dp)
                            .height(2.dp)
                            .background(
                                if (selected) MaterialTheme.colorScheme.primary
                                else Color.Transparent,
                            ),
                    )
                    Icon(
                        painter = painterResource(destination.iconRes),
                        contentDescription = null,
                        modifier = Modifier
                            .padding(top = 3.dp)
                            .size(20.dp),
                        tint = if (selected) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(
                        text = strings.text(destination.labelKey),
                        modifier = Modifier.padding(top = 2.dp),
                        style = MaterialTheme.typography.labelSmall,
                        color = if (selected) MaterialTheme.colorScheme.onSurface
                        else MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }
    }
}

@Composable
fun SentinelBottomBar(selectedRoute: String?, onNavigate: (String) -> Unit) {
    val strings = LocalAppStrings.current
    Surface(
        color = MaterialTheme.colorScheme.surface,
        contentColor = MaterialTheme.colorScheme.onSurface,
        tonalElevation = 0.dp,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.72f)),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .navigationBarsPadding()
                .heightIn(min = 68.dp)
                .selectableGroup(),
            horizontalArrangement = Arrangement.SpaceEvenly,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            PrimaryDestinations.forEach { destination ->
                val selected = selectedRoute == destination.route
                Column(
                    modifier = Modifier
                        .weight(1f)
                        .heightIn(min = 60.dp)
                        .selectable(
                            selected = selected,
                            role = Role.Tab,
                            onClick = { onNavigate(destination.route) },
                        )
                        .padding(horizontal = 4.dp, vertical = 6.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center,
                ) {
                    Box(
                        Modifier
                            .width(if (selected) 24.dp else 12.dp)
                            .height(2.dp)
                            .background(
                                if (selected) MaterialTheme.colorScheme.primary
                                else Color.Transparent,
                            ),
                    )
                    Icon(
                        painter = painterResource(destination.iconRes),
                        contentDescription = null,
                        modifier = Modifier
                            .padding(top = 6.dp)
                            .size(22.dp),
                        tint = if (selected) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(
                        text = strings.text(destination.labelKey),
                        modifier = Modifier.padding(top = 3.dp),
                        style = MaterialTheme.typography.labelLarge,
                        color = if (selected) MaterialTheme.colorScheme.onSurface
                        else MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
    }
}

@Composable
fun PhysicalTestIdentityStrip(
    version: String,
    sourceSha: String,
    environment: String,
    exportLabel: String,
    onExport: () -> Unit,
    compact: Boolean = false,
) {
    val metadata = listOf(
        version,
        sourceSha.take(12).ifBlank { "sha-unavailable" },
        environment.ifBlank { "staging" }.uppercase(),
    ).joinToString(" · ")

    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = MaterialTheme.colorScheme.surfaceVariant,
        contentColor = MaterialTheme.colorScheme.onSurface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.secondary.copy(alpha = 0.42f)),
        tonalElevation = 0.dp,
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 48.dp)
                .padding(
                    start = if (compact) 10.dp else 14.dp,
                    end = 6.dp,
                    top = if (compact) 0.dp else 4.dp,
                    bottom = if (compact) 0.dp else 4.dp,
                ),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(if (compact) 8.dp else 10.dp),
        ) {
            Box(
                Modifier
                    .size(8.dp)
                    .background(MaterialTheme.colorScheme.secondary),
            )
            if (compact) {
                Text(
                    text = "PHYSICAL TEST · $metadata",
                    modifier = Modifier.weight(1f),
                    style = MaterialTheme.typography.bodySmall.copy(fontFamily = SentinelDataFont),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            } else {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        "PHYSICAL TEST",
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text(
                        metadata,
                        style = MaterialTheme.typography.bodySmall.copy(fontFamily = SentinelDataFont),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            TextButton(
                onClick = onExport,
                modifier = Modifier.heightIn(min = 48.dp),
            ) {
                Text(
                    exportLabel,
                    style = if (compact) MaterialTheme.typography.labelMedium
                    else MaterialTheme.typography.labelLarge,
                    maxLines = 1,
                )
            }
        }
    }
}
