package com.alpha0.app.dashboard

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
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
import com.alpha0.app.ui.PrimaryButton
import com.alpha0.app.ui.SentinelCard
import com.alpha0.app.ui.StatusBadge
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

@Composable
fun GamesScreen(accessToken: String, api: DashboardApi, onGameClick: (String) -> Unit) {
    val strings = LocalAppStrings.current
    var games by remember { mutableStateOf<List<DashboardApi.Entitlement>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }
    var generation by remember { mutableStateOf(0) }
    LaunchedEffect(accessToken, generation) {
        loading = true
        error = null
        when (val result = withContext(Dispatchers.IO) { api.getEntitlements(accessToken) }) {
            is DashboardApi.Result.Success -> games = result.value
            is DashboardApi.Result.Failure -> error = result.message
        }
        loading = false
    }
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            Text(strings.text("games_title"), style = MaterialTheme.typography.headlineMedium)
            Text(strings.text("games_description"), color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        if (loading) item { CircularProgressIndicator() }
        error?.let { message ->
            item {
                Text(strings.text("load_failed", message), color = MaterialTheme.colorScheme.error)
                PrimaryButton(strings.text("retry"), { generation += 1 })
            }
        }
        if (!loading && error == null && games.isEmpty()) item { Text(strings.text("no_entitlements")) }
        items(games, key = { it.id }) { game ->
            SentinelCard(modifier = Modifier.clickable { onGameClick(game.id) }) {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(game.gameName, style = MaterialTheme.typography.titleMedium)
                    StatusBadge(game.status, game.status.equals("ACTIVE", true))
                    Text(game.platform, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    DataText(strings.text("valid_until", game.validUntil))
                }
            }
        }
    }
}

@Composable
fun ActivityScreen(deviceId: String?) {
    val strings = LocalAppStrings.current
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            Text(strings.text("activity_title"), style = MaterialTheme.typography.headlineMedium)
            Text(strings.text("activity_description"), color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        listOf(
            strings.text("activity_session") to true,
            strings.text("activity_device") to !deviceId.isNullOrBlank(),
            strings.text("activity_logs") to true,
        ).forEach { (message, active) ->
            item {
                SentinelCard {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        StatusBadge(if (active) "OK" else strings.text("not_available"), active)
                        Text(message)
                    }
                }
            }
        }
    }
}
