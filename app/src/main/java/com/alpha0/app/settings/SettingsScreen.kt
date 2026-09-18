package com.alpha0.app.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.alpha0.app.ui.AppLanguage
import com.alpha0.app.ui.AppThemeMode
import com.alpha0.app.ui.LocalAppStrings
import com.alpha0.app.ui.SentinelCard

@Composable
fun SettingsScreen(
    language: AppLanguage,
    theme: AppThemeMode,
    onLanguage: (AppLanguage) -> Unit,
    onTheme: (AppThemeMode) -> Unit,
) {
    val strings = LocalAppStrings.current
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        item { Text(strings.text("settings_title"), style = MaterialTheme.typography.headlineMedium) }
        item {
            SentinelCard {
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(strings.text("language"), style = MaterialTheme.typography.titleLarge)
                    ChoiceRow(strings.text("language_system"), language == AppLanguage.SYSTEM) { onLanguage(AppLanguage.SYSTEM) }
                    ChoiceRow(strings.text("language_ru"), language == AppLanguage.RUSSIAN) { onLanguage(AppLanguage.RUSSIAN) }
                    ChoiceRow(strings.text("language_en"), language == AppLanguage.ENGLISH) { onLanguage(AppLanguage.ENGLISH) }
                }
            }
        }
        item {
            SentinelCard {
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(strings.text("appearance"), style = MaterialTheme.typography.titleLarge)
                    ChoiceRow(strings.text("theme_system"), theme == AppThemeMode.SYSTEM) { onTheme(AppThemeMode.SYSTEM) }
                    ChoiceRow(strings.text("theme_light"), theme == AppThemeMode.LIGHT) { onTheme(AppThemeMode.LIGHT) }
                    ChoiceRow(strings.text("theme_dark"), theme == AppThemeMode.DARK) { onTheme(AppThemeMode.DARK) }
                }
            }
        }
        item { Text(strings.text("settings_applied"), color = MaterialTheme.colorScheme.onSurfaceVariant) }
    }
}

@Composable
private fun ChoiceRow(label: String, selected: Boolean, onClick: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        RadioButton(selected = selected, onClick = onClick)
        Text(label, modifier = Modifier.weight(1f), style = MaterialTheme.typography.bodyLarge)
    }
}
