package com.alpha0.app.update

import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import android.content.Intent
import android.net.Uri
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.alpha0.app.BuildConfig
import com.alpha0.app.ui.DataText
import com.alpha0.app.ui.LocalAppStrings
import com.alpha0.app.ui.PrimaryButton
import com.alpha0.app.ui.SentinelCard
import com.google.android.play.core.appupdate.AppUpdateManagerFactory
import com.google.android.play.core.appupdate.AppUpdateOptions
import com.google.android.play.core.install.InstallStateUpdatedListener
import com.google.android.play.core.install.model.InstallStatus
import com.google.android.play.core.install.model.AppUpdateType
import com.google.android.play.core.install.model.UpdateAvailability

private enum class UpdateState { IDLE, CHECKING, CURRENT, AVAILABLE, DOWNLOADING, READY_TO_INSTALL, PLAY_REQUIRED, FAILED }

@Composable
fun UpdateScreen() {
    val strings = LocalAppStrings.current
    val context = LocalContext.current
    val activity = context.findActivity()
    val manager = remember(context) { AppUpdateManagerFactory.create(context) }
    var state by remember { mutableStateOf(UpdateState.IDLE) }
    val channelLabel = when (BuildConfig.SENTINEL_DISTRIBUTION_CHANNEL) {
        "play" -> strings.text("channel_play")
        "diagnostic" -> strings.text("channel_diagnostic")
        "development" -> strings.text("channel_development")
        else -> BuildConfig.SENTINEL_DISTRIBUTION_CHANNEL
    }
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.StartIntentSenderForResult()) {
        state = if (it.resultCode == Activity.RESULT_OK) UpdateState.DOWNLOADING else UpdateState.FAILED
    }
    val installListener = remember {
        InstallStateUpdatedListener { installState ->
            state = when (installState.installStatus()) {
                InstallStatus.DOWNLOADED -> UpdateState.READY_TO_INSTALL
                InstallStatus.DOWNLOADING, InstallStatus.INSTALLING, InstallStatus.PENDING -> UpdateState.DOWNLOADING
                InstallStatus.FAILED, InstallStatus.CANCELED -> UpdateState.FAILED
                InstallStatus.INSTALLED -> UpdateState.CURRENT
                else -> state
            }
        }
    }
    DisposableEffect(manager, installListener) {
        manager.registerListener(installListener)
        onDispose { manager.unregisterListener(installListener) }
    }

    fun check() {
        state = UpdateState.CHECKING
        manager.appUpdateInfo
            .addOnSuccessListener { info ->
                if (info.installStatus() == InstallStatus.DOWNLOADED) {
                    state = UpdateState.READY_TO_INSTALL
                } else if (info.updateAvailability() == UpdateAvailability.UPDATE_AVAILABLE &&
                    info.isUpdateTypeAllowed(AppUpdateType.FLEXIBLE)
                ) {
                    state = UpdateState.AVAILABLE
                    if (activity != null) {
                        manager.startUpdateFlowForResult(
                            info,
                            launcher,
                            AppUpdateOptions.newBuilder(AppUpdateType.FLEXIBLE).build(),
                        )
                    }
                } else {
                    state = if (context.installedFromPlay()) UpdateState.CURRENT else UpdateState.PLAY_REQUIRED
                }
            }
            .addOnFailureListener {
                state = if (context.installedFromPlay()) UpdateState.FAILED else UpdateState.PLAY_REQUIRED
            }
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        item { Text(strings.text("updates_title"), style = MaterialTheme.typography.headlineMedium) }
        item {
            SentinelCard {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("${strings.text("current_version")}: ${BuildConfig.VERSION_NAME}")
                    Text("${strings.text("build_channel")}: $channelLabel")
                    DataText("${strings.text("source_revision")}: ${BuildConfig.SENTINEL_SOURCE_SHA.take(12)}")
                }
            }
        }
        item {
            val readyToInstall = state == UpdateState.READY_TO_INSTALL
            PrimaryButton(
                text = strings.text(if (readyToInstall) "install_update" else "check_updates"),
                onClick = { if (readyToInstall) manager.completeUpdate() else check() },
                enabled = state != UpdateState.CHECKING,
                modifier = Modifier.fillMaxWidth(),
            ) {
                if (state == UpdateState.CHECKING) {
                    CircularProgressIndicator()
                } else {
                    Text(strings.text(if (readyToInstall) "install_update" else "check_updates"))
                }
            }
        }
        item {
            val message = when (state) {
                UpdateState.IDLE -> if (BuildConfig.SENTINEL_DISTRIBUTION_CHANNEL == "diagnostic") "update_sideload_notice" else "up_to_date"
                UpdateState.CHECKING -> "checking_updates"
                UpdateState.CURRENT -> "up_to_date"
                UpdateState.AVAILABLE -> "update_available"
                UpdateState.DOWNLOADING -> "update_downloading"
                UpdateState.READY_TO_INSTALL -> "update_ready"
                UpdateState.PLAY_REQUIRED -> "update_play_required"
                UpdateState.FAILED -> "server_unreachable"
            }
            Text(strings.text(message), color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        item {
            PrimaryButton(
                text = strings.text("open_play_store"),
                onClick = {
                    val market = Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=${context.packageName}"))
                    runCatching { context.startActivity(market) }.onFailure {
                        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://play.google.com/store/apps/details?id=${context.packageName}")))
                    }
                },
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

private tailrec fun Context.findActivity(): Activity? = when (this) {
    is Activity -> this
    is ContextWrapper -> baseContext.findActivity()
    else -> null
}

private fun Context.installedFromPlay(): Boolean = runCatching {
    val installer = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
        packageManager.getInstallSourceInfo(packageName).installingPackageName
    } else {
        @Suppress("DEPRECATION")
        packageManager.getInstallerPackageName(packageName)
    }
    installer == "com.android.vending"
}.getOrDefault(false)
