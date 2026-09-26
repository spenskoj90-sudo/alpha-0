package com.alpha0.app.dashboard

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.alpha0.app.ui.DataText
import com.alpha0.app.ui.LocalAppStrings
import com.alpha0.app.ui.PrimaryButton
import com.alpha0.app.ui.SentinelCard
import com.alpha0.app.ui.SentinelCardKind

@Composable
fun MfaRecoveryCodesScreen(
    codes: List<String>,
    onContinueToSignIn: () -> Unit,
) {
    val strings = LocalAppStrings.current
    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text(strings.text("mfa_recovery_title"), style = MaterialTheme.typography.headlineMedium)
            SentinelCard(kind = SentinelCardKind.CONTENT) {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(strings.text("mfa_enabled_relogin"), style = MaterialTheme.typography.bodyMedium)
                    Text(strings.text("mfa_recovery_warning"), style = MaterialTheme.typography.bodyMedium)
                    codes.forEach { DataText(it) }
                    PrimaryButton(
                        text = strings.text("continue_sign_in"),
                        onClick = onContinueToSignIn,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }
        }
    }
}
