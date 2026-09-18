package com.alpha0.app.help

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.alpha0.app.BuildConfig
import com.alpha0.app.ui.DataText
import com.alpha0.app.ui.LocalAppStrings
import com.alpha0.app.ui.SentinelCard

@Composable
fun HelpScreen() {
    val strings = LocalAppStrings.current
    val sections = listOf(
        "help_getting_started" to "help_getting_started_body",
        "help_security" to "help_security_body",
        "help_updates" to "help_updates_body",
        "help_support" to "help_support_body",
    )
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item { Text(strings.text("help_title"), style = MaterialTheme.typography.headlineMedium) }
        sections.forEach { (title, body) ->
            item {
                SentinelCard {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(strings.text(title), style = MaterialTheme.typography.titleMedium)
                        Text(strings.text(body), color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }
    }
}

@Composable
fun AboutScreen() {
    val strings = LocalAppStrings.current
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        item { Text(strings.text("about_title"), style = MaterialTheme.typography.headlineMedium) }
        item { Text(strings.text("about_body"), style = MaterialTheme.typography.bodyLarge) }
        item {
            SentinelCard {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("${strings.text("current_version")}: ${BuildConfig.VERSION_NAME}")
                    Text("${strings.text("build_channel")}: ${BuildConfig.SENTINEL_RUNTIME_ENVIRONMENT}")
                    DataText("${strings.text("source_revision")}: ${BuildConfig.SENTINEL_SOURCE_SHA}")
                    if (BuildConfig.SENTINEL_DIAGNOSTICS_MODE == "FORENSIC_TEST") {
                        Text(strings.text("diagnostic_build"), color = MaterialTheme.colorScheme.error)
                    }
                }
            }
        }
    }
}
