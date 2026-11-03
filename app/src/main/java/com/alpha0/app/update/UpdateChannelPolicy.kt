package com.alpha0.app.update

/** Build-selected update route, never an APK trust or install permission decision. */
internal object UpdateChannelPolicy {
    fun allowsSignedFeed(channel: String): Boolean =
        channel == "diagnostic" || channel == "signed_feed"

    fun allowsLocalApkSelection(channel: String): Boolean =
        channel == "diagnostic"
}
