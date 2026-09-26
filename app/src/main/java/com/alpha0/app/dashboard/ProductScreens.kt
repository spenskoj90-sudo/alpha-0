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
import com.alpha0.app.ui.SentinelCardKind
import com.alpha0.app.ui.SentinelStatus
import com.alpha0.app.ui.StatusBadge
import com.alpha0.app.ui.statusFromRaw
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
            Text(strings.text("games_title"), style = MaterialTheme.typography.headlineLarge)
            Text(strings.text("games_description"), color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        if (loading) item { CircularProgressIndicator() }
        error?.let { message ->
            item {
                SentinelCard(kind = SentinelCardKind.OPERATIONAL) {
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        StatusBadge(strings.text("attention_required"), SentinelStatus.WARNING)
                        Text(strings.text("load_failed", message), color = MaterialTheme.colorScheme.error)
                        PrimaryButton(strings.text("retry"), { generation += 1 })
                    }
                }
            }
        }
        if (!loading && error == null && games.isEmpty()) {
            item {
                SentinelCard(kind = SentinelCardKind.CONTENT) {
                    Text(strings.text("no_entitlements"), color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
        items(games, key = { it.id }) { game ->
            SentinelCard(
                modifier = Modifier.clickable { onGameClick(game.id) },
                kind = SentinelCardKind.CONTENT,
            ) {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(game.gameName, style = MaterialTheme.typography.titleLarge)
                    StatusBadge(game.status, statusFromRaw(game.status))
                    Text(game.platform, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    DataText(strings.text("valid_until", game.validUntil))
                }
            }
        }
    }
}

@Composable
fun ActivityScreen(accessToken: String, api: DashboardApi) {
    val strings = LocalAppStrings.current
    var events by remember { mutableStateOf<List<DashboardApi.AuditEvent>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }
    var generation by remember { mutableStateOf(0) }

    LaunchedEffect(accessToken, generation) {
        loading = true
        error = null
        when (val result = withContext(Dispatchers.IO) { api.getAudit(accessToken) }) {
            is DashboardApi.Result.Success -> events = result.value
            is DashboardApi.Result.Failure -> error = result.message
        }
        loading = false
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            Text(strings.text("activity_title"), style = MaterialTheme.typography.headlineLarge)
            Text(strings.text("activity_description"), color = MaterialTheme.colorScheme.onSurfaceVariant)
        }

        if (loading) {
            item { CircularProgressIndicator(color = MaterialTheme.colorScheme.primary) }
        }

        error?.let { message ->
            item {
                SentinelCard(kind = SentinelCardKind.OPERATIONAL) {
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        StatusBadge(strings.text("status_unavailable"), SentinelStatus.UNAVAILABLE)
                        Text(strings.text("load_failed", message), color = MaterialTheme.colorScheme.error)
                        PrimaryButton(strings.text("retry"), { generation += 1 })
                    }
                }
            }
        }

        if (!loading && error == null && events.isEmpty()) {
            item {
                SentinelCard(kind = SentinelCardKind.CONTENT) {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        StatusBadge(strings.text("status_active"), SentinelStatus.ACTIVE)
                        Text(strings.text("activity_empty_title"), style = MaterialTheme.typography.titleLarge)
                        Text(
                            strings.text("activity_empty_body"),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }

        items(events) { event ->
            val status = when (event.decision.uppercase()) {
                "ALLOW" -> SentinelStatus.ACTIVE
                "DENY" -> SentinelStatus.DENIED
                else -> SentinelStatus.UNKNOWN
            }
            SentinelCard(kind = SentinelCardKind.CONTENT) {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    StatusBadge(
                        strings.text(
                            when (status) {
                                SentinelStatus.ACTIVE -> "activity_event_allowed"
                                SentinelStatus.DENIED -> "activity_event_denied"
                                else -> "status_unknown"
                            }
                        ),
                        status,
                    )
                    Text(
                        event.action.replace(':', ' · ').replace('-', ' '),
                        style = MaterialTheme.typography.titleMedium,
                    )
                    DataText(strings.text("activity_event_resource", event.resource))
                    Text(
                        strings.text("activity_event_reason", event.reasonCode),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    event.createdAt?.let {
                        Text(
                            strings.text("activity_event_time", it),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }
    }
}
