package com.alpha0.app.update

/** Build-selected update route, never an APK trust or install permission decision. */
internal object UpdateChannelPolicy {
    fun allowsSignedFeed(channel: String): Boolean =
        channel == "diagnostic" || channel == "signed_feed"

    /** Signed-feed channels must not initialize or register Google Play update listeners. */
    fun usesPlayManager(channel: String): Boolean = !allowsSignedFeed(channel)

    fun allowsLocalApkSelection(channel: String): Boolean =
        channel == "diagnostic"

    /** Share verified APK install/permission controls without exposing the manual picker. */
    fun showsStagedInstall(channel: String): Boolean =
        allowsSignedFeed(channel)
}
