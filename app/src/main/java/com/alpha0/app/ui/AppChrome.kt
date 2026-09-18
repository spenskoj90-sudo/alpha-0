package com.alpha0.app.ui

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
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue

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
        title = { Text(title) },
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
    NavigationBar {
        PrimaryDestinations.forEach { destination ->
            val icon = when (destination.route) {
                "home" -> Icons.Default.Home
                "games" -> Icons.Default.SportsEsports
                "security" -> Icons.Default.Security
                else -> Icons.Default.Timeline
            }
            NavigationBarItem(
                selected = selectedRoute == destination.route,
                onClick = { onNavigate(destination.route) },
                icon = { Icon(icon, contentDescription = null) },
                label = { Text(strings.text(destination.labelKey)) },
            )
        }
    }
}
