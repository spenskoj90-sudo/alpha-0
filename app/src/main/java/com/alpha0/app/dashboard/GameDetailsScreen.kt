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
import com.alpha0.app.ui.DataText
import com.alpha0.app.ui.LocalAppStrings
import com.alpha0.app.ui.SentinelCard
import com.alpha0.app.ui.SentinelColors
import com.alpha0.app.ui.StatusBadge
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

@Composable
fun GameDetailsScreen(accessToken: String, entitlementId: String, api: DashboardApi) {
    val strings = LocalAppStrings.current
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
            Text(strings.text("game_details"), style = MaterialTheme.typography.headlineMedium)
            when {
                loading -> CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                error != null -> Text(strings.text("load_failed", error), color = MaterialTheme.colorScheme.error)
                game != null -> {
                    val current = game!!
                    SentinelCard {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(current.gameName, style = MaterialTheme.typography.titleLarge)
                            StatusBadge(current.status, active = current.status.equals("ACTIVE", ignoreCase = true))
                            Text(strings.text("platform", current.platform), style = MaterialTheme.typography.bodyMedium)
                            Text(strings.text("family", current.family), style = MaterialTheme.typography.bodyMedium)
                            Text(strings.text("versioning", current.versioning), style = MaterialTheme.typography.bodyMedium)
                            DataText(strings.text("source", current.source))
                            DataText(strings.text("valid_from", current.validFrom))
                            DataText(strings.text("valid_until", current.validUntil))
                            Text(strings.text("launcher_supported", strings.text(if (current.launcherSupported) "yes" else "no")), style = MaterialTheme.typography.bodyMedium)
                            Text(strings.text("interaction_mode", current.interactionMode), style = MaterialTheme.typography.bodyMedium)
                        }
                    }
                }
            }
        }
    }
}
