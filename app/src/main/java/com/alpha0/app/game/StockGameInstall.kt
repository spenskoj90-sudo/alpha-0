package com.alpha0.app.game

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build

data class StockGameInstall(val versionName: String, val versionCode: Long, val signerSha256: String? = null)

/** Exact metadata equality across consent, callback and service start; NOT source attestation. */
internal object GameInstallFence {
    fun matches(
        versionName: String?, versionCode: Long?, signerSha256: String?,
        current: StockGameInstall?, signerSupplied: Boolean = true,
    ): Boolean =
        signerSupplied && versionName != null && versionCode != null && current != null &&
            current.versionName == versionName &&
            current.versionCode == versionCode &&
            current.signerSha256 == signerSha256
}

object ShatteredGameProfile {
    const val PACKAGE = "com.shatteredpixel.shatteredpixeldungeon"
    const val GAME_ID = "shattered-pixel-dungeon"
    const val ADAPTER_ID = "android-shattered-screen-v1"

    // A package/version observation is not proof of publisher identity or capture-source identity.
    fun installed(context: Context): StockGameInstall? = try {
        // Certificate fingerprint describes the installed package, not the captured app.
        val info = if (Build.VERSION.SDK_INT >= 33) {
            context.packageManager.getPackageInfo(
                PACKAGE, PackageManager.PackageInfoFlags.of(PackageManager.GET_SIGNING_CERTIFICATES.toLong()),
            )
        } else {
            @Suppress("DEPRECATION")
            context.packageManager.getPackageInfo(PACKAGE, PackageManager.GET_SIGNING_CERTIFICATES)
        }
        if (info.applicationInfo?.enabled != true || context.packageManager.getLaunchIntentForPackage(PACKAGE) == null) null
        else {
            val signatures = if (Build.VERSION.SDK_INT >= 28) {
                info.signingInfo?.apkContentsSigners?.map { it.toByteArray() }.orEmpty()
            } else emptyList()
            StockGameInstall(
                info.versionName?.take(64) ?: "unknown", info.longVersionCode,
                StockGameCertificate.digest(signatures),
            )
        }
    } catch (_: PackageManager.NameNotFoundException) {
        null
    } catch (_: SecurityException) {
        null
    }
}
