package com.alpha0.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.SportsEsports
import androidx.compose.material.icons.filled.Timeline
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

data class AppDestination(val route: String, val labelKey: String)

val PrimaryDestinations = listOf(
    AppDestination("home", "home"),
    AppDestination("games", "games"),
    AppDestination("security", "security"),
    AppDestination("activity", "activity"),
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SentinelTopBar(
    title: String,
    canGoBack: Boolean,
    onBack: () -> Unit,
    onNavigate: (String) -> Unit,
) {
    val strings = LocalAppStrings.current
    var expanded by remember { mutableStateOf(false) }
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
                listOf(
                    "settings" to "settings",
                    "updates" to "updates",
                    "help" to "help",
                    "about" to "about",
                ).forEach { (route, label) ->
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

@Composable
fun SentinelBottomBar(selectedRoute: String?, onNavigate: (String) -> Unit) {
    val strings = LocalAppStrings.current
    NavigationBar(
        containerColor = MaterialTheme.colorScheme.surface,
        contentColor = MaterialTheme.colorScheme.onSurface,
        tonalElevation = 0.dp,
    ) {
        PrimaryDestinations.forEach { destination ->
            val icon = when (destination.route) {
                "home" -> Icons.Default.Home
                "games" -> Icons.Default.SportsEsports
                "security" -> Icons.Default.Security
                else -> Icons.Default.Timeline
            }
            val selected = selectedRoute == destination.route
            NavigationBarItem(
                selected = selected,
                onClick = { onNavigate(destination.route) },
                icon = {
                    Column {
                        Box(
                            Modifier
                                .fillMaxWidth()
                                .height(3.dp)
                                .background(if (selected) MaterialTheme.colorScheme.primary else Color.Transparent)
                        )
                        Icon(icon, contentDescription = null, modifier = Modifier.padding(top = 5.dp))
                    }
                },
                label = { Text(strings.text(destination.labelKey)) },
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = MaterialTheme.colorScheme.primary,
                    selectedTextColor = MaterialTheme.colorScheme.primary,
                    indicatorColor = Color.Transparent,
                    unselectedIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
                    unselectedTextColor = MaterialTheme.colorScheme.onSurfaceVariant,
                ),
            )
        }
    }
}
