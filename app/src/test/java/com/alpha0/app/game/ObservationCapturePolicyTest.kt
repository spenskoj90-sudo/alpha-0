package com.alpha0.app.game

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Source-availability only, not real Android capture/source acceptance. */
class ObservationCapturePolicyTest {
    @Test fun exhaustiveSdkAndChannelMatrixIsFailClosed() {
        for (api in listOf(29, 30, 33, 34, 35, 36, 37)) {
            for (channel in listOf("development", "diagnostic", "signed_feed", "play", "", "unknown")) {
                for (debug in listOf(true, false)) {
                    val expected = api >= 34 && when (channel) {
                        "development", "diagnostic" -> debug
                        "signed_feed" -> !debug
                        else -> false
                    }
                    assertEquals("api=$api channel=$channel debug=$debug", expected,
                        ObservationCapturePolicy.supports(debug, channel, api))
                }
            }
        }
    }


    @Test fun captureChooserRequiresFreshDisplayedGameIdentityAndAcknowledgement() {
        val shown = StockGameInstall("4.0.2", 922L, "a".repeat(64))
        assertTrue(ObservationCapturePolicy.canRequestConsent(true, true, shown, shown))
        assertFalse(ObservationCapturePolicy.canRequestConsent(false, true, shown, shown))
        assertFalse(ObservationCapturePolicy.canRequestConsent(true, false, shown, shown))
        assertFalse(ObservationCapturePolicy.canRequestConsent(true, true, null, shown))
        assertFalse(ObservationCapturePolicy.canRequestConsent(true, true, shown, null))
        assertFalse(ObservationCapturePolicy.canRequestConsent(true, true, shown, shown.copy(versionCode = 923L)))
        assertFalse(ObservationCapturePolicy.canRequestConsent(true, true, shown, shown.copy(versionName = "4.0.3")))
        assertFalse(ObservationCapturePolicy.canRequestConsent(true, true, shown, shown.copy(signerSha256 = "b".repeat(64))))
    }

    @Test fun unknownSignerRemainsDiagnosticOnlyAndNeverClaimsSourceAttestation() {
        val observedWithoutSigner = StockGameInstall("4.0.2", 922L, null)
        assertTrue(ObservationCapturePolicy.canRequestConsent(true, true, observedWithoutSigner, observedWithoutSigner))
        assertFalse(ObservationCapturePolicy.canRequestConsent(true, true, observedWithoutSigner,
            observedWithoutSigner.copy(signerSha256 = "b".repeat(64))))
    }
    @Test fun nonDebuggableSignedFeedObservesButPlayDoesNot() {
        assertTrue(ObservationCapturePolicy.supports(false, "signed_feed", 34))
        assertTrue(ObservationCapturePolicy.supports(false, "signed_feed", 37))
        assertFalse(ObservationCapturePolicy.supports(true, "signed_feed", 37))
        assertFalse(ObservationCapturePolicy.supports(false, "play", 37))
        assertFalse(ObservationCapturePolicy.supports(false, "signed_feed", 33))
    }

    @Test fun diagnosticAndDevelopmentStillRequireDebugBuildAndAndroid14() {
        assertTrue(ObservationCapturePolicy.supports(true, "diagnostic", 34))
        assertTrue(ObservationCapturePolicy.supports(true, "development", 34))
        assertFalse(ObservationCapturePolicy.supports(false, "diagnostic", 37))
        assertFalse(ObservationCapturePolicy.supports(false, "development", 37))
        assertFalse(ObservationCapturePolicy.supports(true, "diagnostic", 33))
    }
}
