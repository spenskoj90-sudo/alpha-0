package com.alpha0.app.game

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import java.io.File

/**
 * Explicitly user-initiated, local-only APK inspection; no APK bytes leave the device.
 * Package metadata, even when matching upstream, NEVER proves projected window identity.
 */
internal object InstalledShatteredBinary {
    private fun source(context: Context): Pair<String, Boolean>? = try {
        val info = if (Build.VERSION.SDK_INT >= 33) {
            context.packageManager.getApplicationInfo(
                ShatteredGameProfile.PACKAGE,
                PackageManager.ApplicationInfoFlags.of(0L),
            )
        } else {
            @Suppress("DEPRECATION")
            context.packageManager.getApplicationInfo(ShatteredGameProfile.PACKAGE, 0)
        }
        val path = info.publicSourceDir?.takeIf { it.isNotBlank() }
        if (path == null) null else path to (info.splitSourceDirs?.isNotEmpty() == true)
    } catch (_: PackageManager.NameNotFoundException) {
        null
    } catch (_: SecurityException) {
        null
    }

    suspend fun verify(context: Context, expected: StockGameInstall): GameBinaryEvidence.Status =
        withContext(Dispatchers.IO) {
            val before = ShatteredGameProfile.installed(context)
            if (before == null || before != expected) return@withContext GameBinaryEvidence.Status.UNAVAILABLE
            val sourceBefore = source(context) ?: return@withContext GameBinaryEvidence.Status.UNAVAILABLE
            val cancellation = currentCoroutineContext()
            // Split installs cannot match whole upstream standalone APK bytes.
            val result = if (sourceBefore.second) GameBinaryEvidence.Status.OTHER_OR_SPLIT
                else GameBinaryEvidence.inspect(
                    File(sourceBefore.first), expected.versionName, expected.versionCode,
                    expected.signerSha256,
                ) { cancellation.ensureActive() }
            cancellation.ensureActive()
            if (ShatteredGameProfile.installed(context) != before || source(context) != sourceBefore)
                GameBinaryEvidence.Status.UNAVAILABLE
            else result
        }
}
