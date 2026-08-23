package com.alpha0.app.dashboard

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.alpha0.app.ui.SentinelCard
import com.alpha0.app.ui.SentinelDataStyle
import com.alpha0.app.ui.SentinelDanger
import com.alpha0.app.ui.SentinelSignal
import com.alpha0.app.ui.SentinelTextSecondary
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

@Composable
fun GameDetailsScreen(accessToken: String, entitlementId: String, api: DashboardApi) {
    var game by remember { mutableStateOf<DashboardApi.GameDetails?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var loading by remember { mutableStateOf(true) }

    LaunchedEffect(entitlementId, accessToken) {
        when (val result = withContext(Dispatchers.IO) { api.getEntitlement(accessToken, entitlementId) }) {
            is DashboardApi.Result.Success -> game = result.value
            is DashboardApi.Result.Failure -> error = result.message
        }
        loading = false
    }

    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(modifier = Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Text("GAME DETAILS", style = MaterialTheme.typography.displaySmall)
            when {
                loading -> CircularProgressIndicator()
                error != null -> Text("Load failed: $error", color = SentinelDanger)
                game != null -> {
                    val current = game!!
                    SentinelCard(modifier = Modifier.fillMaxWidth()) {
                        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(current.gameName, style = MaterialTheme.typography.titleLarge)
                            Text(
                                "Access: ${current.status}",
                                color = if (current.status == "ACTIVE" || current.status == "OK") SentinelSignal else SentinelDanger,
                            )
                            Text("Platform: ${current.platform}")
                            Text("Family: ${current.family}")
                            Text("Versioning: ${current.versioning}")
                            Text("Source: ${current.source}")
                            Text("Valid from: ${current.validFrom}", style = SentinelDataStyle)
                            Text("Valid until: ${current.validUntil}", style = SentinelDataStyle)
                            Text("Launcher supported: ${current.launcherSupported}")
                            Text("Interaction mode: ${current.interactionMode}")
                        }
                    }
                }
                else -> Text("Game entitlement not found.", color = SentinelTextSecondary)
            }
        }
    }
}
