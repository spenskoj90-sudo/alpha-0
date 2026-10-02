package com.alpha0.app.game

import android.content.Context
import android.content.pm.PackageManager

data class StockGameInstall(val versionName: String, val versionCode: Long)

object ShatteredGameProfile {
    const val PACKAGE = "com.shatteredpixel.shatteredpixeldungeon"
    const val GAME_ID = "shattered-pixel-dungeon"
    const val ADAPTER_ID = "android-shattered-screen-v1"

    // A package/version observation is not proof of publisher identity or capture-source identity.
    fun installed(context: Context): StockGameInstall? = try {
        val info = context.packageManager.getPackageInfo(PACKAGE, 0)
        if (info.applicationInfo?.enabled != true || context.packageManager.getLaunchIntentForPackage(PACKAGE) == null) null
        else StockGameInstall(info.versionName?.take(64) ?: "unknown", info.longVersionCode)
    } catch (_: PackageManager.NameNotFoundException) {
        null
    } catch (_: SecurityException) {
        null
    }
}
