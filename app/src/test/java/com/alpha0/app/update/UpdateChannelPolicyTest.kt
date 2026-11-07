package com.alpha0.app.update

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class UpdateChannelPolicyTest {
    @Test fun nonPlayReleaseUsesSignedFeedWithoutDiagnosticPicker() {
        assertTrue(UpdateChannelPolicy.allowsSignedFeed("signed_feed"))
        assertTrue(UpdateChannelPolicy.showsStagedInstall("signed_feed"))
        assertFalse(UpdateChannelPolicy.allowsLocalApkSelection("signed_feed"))
        assertFalse(UpdateChannelPolicy.usesPlayManager("signed_feed"))
    }

    @Test fun diagnosticUsesBothButPlayAndUnknownNeverAcquireFeedAuthority() {
        assertTrue(UpdateChannelPolicy.allowsSignedFeed("diagnostic"))
        assertTrue(UpdateChannelPolicy.showsStagedInstall("diagnostic"))
        assertTrue(UpdateChannelPolicy.allowsLocalApkSelection("diagnostic"))
        assertFalse(UpdateChannelPolicy.usesPlayManager("diagnostic"))
        for (channel in listOf("play", "development", "", "signedfeed", "SIGNED_FEED")) {
            assertFalse("Unexpected signed-feed authority: $channel", UpdateChannelPolicy.allowsSignedFeed(channel))
            assertFalse("Unexpected staged install controls: $channel", UpdateChannelPolicy.showsStagedInstall(channel))
            assertFalse("Unexpected manual APK picker: $channel", UpdateChannelPolicy.allowsLocalApkSelection(channel))
            assertTrue("Existing Play fallback changed: $channel", UpdateChannelPolicy.usesPlayManager(channel))
        }
    }
}
