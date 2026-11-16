package com.alpha0.app.game

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class BrowserGameSourcePolicyTest {
    private val target = BrowserGameSourcePolicy.LASTHAVENS

    /** Synthetic attestation only; no Android/Chrome source provider is connected. */
    private fun syntheticEvidence() = BrowserSourceEvidence(
        claimedGameId = target.gameId,
        claimedUrl = target.exactHttpsUrl,
        foregroundPackageName = "com.android.chrome",
        originProofKind = BrowserOriginProofKind.TRUSTED_VISIBLE_ADDRESS_BAR,
        originEvidenceVerified = true,
        selectedWindowBoundToCapture = true,
        captureGeneration = "capture-42",
        attestedCaptureGeneration = "capture-42",
        observedElapsedRealtimeMs = 12_000L,
        checkedElapsedRealtimeMs = 12_200L,
    )

    @Test fun defaultUnknownEvidenceIsClosed() {
        val decision = BrowserGameSourcePolicy.evaluate(target, BrowserSourceEvidence())
        assertFalse(decision.sourceVerified)
        assertEquals(BrowserSourceBlock.values().size, decision.blockers.size)
    }

    @Test fun exactSyntheticProofOnlyEstablishesBrowserSourceNotGameActions() {
        val decision = BrowserGameSourcePolicy.evaluate(target, syntheticEvidence())
        assertTrue(decision.sourceVerified)
        assertEquals(emptyList<BrowserSourceBlock>(), decision.blockers)
        // No Android capture provider currently constructs this synthetic proof in production.
    }

    @Test fun forgedHostsSchemesPathsAndUriDecorationsAreRejected() {
        val bad = listOf(
            "http://lasthavens.com/play",
            "https://lasthavens.com.attacker.example/play",
            "https://lasthavens.com@attacker.example/play",
            "https://attacker.example@lasthavens.com/play",
            "https://lasthavens.com:444/play",
            "https://lasthavens.com:443/play",
            "https://lasthavens.com/play/",
            "https://lasthavens.com/play?redirect=/evil",
            "https://lasthavens.com/play#fragment",
            "https://lasthavens.com/%70lay",
            "https://lasthavens.com.evil.test/play",
            "https://lasthavens.com./play",
            " https://lasthavens.com/play",
            "https://lasthavens.com/play ",
        )
        for (url in bad) {
            val decision = BrowserGameSourcePolicy.evaluate(target, syntheticEvidence().copy(claimedUrl = url))
            assertTrue("Unexpectedly accepted: $url", BrowserSourceBlock.URL_NOT_EXACT_HTTPS_TARGET in decision.blockers)
            assertFalse(decision.sourceVerified)
        }
    }

    @Test fun chromePackageOrTypedUrlAloneNeverProvesTarget() {
        val evidence = syntheticEvidence().copy(
            originProofKind = BrowserOriginProofKind.NONE,
            originEvidenceVerified = false,
        )
        val result = BrowserGameSourcePolicy.evaluate(target, evidence)
        assertTrue(BrowserSourceBlock.TRUSTED_ORIGIN_PROOF_MISSING in result.blockers)
        assertFalse(result.sourceVerified)
    }

    @Test fun verifiedDigitalAssetLinksStillRequiresForegroundWindowAndCaptureBinding() {
        val evidence = syntheticEvidence().copy(
            originProofKind = BrowserOriginProofKind.VERIFIED_DIGITAL_ASSET_LINKS,
            selectedWindowBoundToCapture = false,
        )
        val result = BrowserGameSourcePolicy.evaluate(target, evidence)
        assertTrue(BrowserSourceBlock.WINDOW_NOT_BOUND in result.blockers)
        assertFalse(result.sourceVerified)
    }

    @Test fun mismatchedCaptureGenerationIsClosedEvenWhenUrlMatches() {
        val result = BrowserGameSourcePolicy.evaluate(
            target, syntheticEvidence().copy(attestedCaptureGeneration = "capture-previous"),
        )
        assertTrue(BrowserSourceBlock.CAPTURE_GENERATION_MISMATCH in result.blockers)
        assertFalse(result.sourceVerified)
    }

    @Test fun expiredFutureAndMissingTimestampsAreClosed() {
        for (frameAt in listOf(null, -1L, 9_999L, 12_201L)) {
            val result = BrowserGameSourcePolicy.evaluate(
                target, syntheticEvidence().copy(observedElapsedRealtimeMs = frameAt),
            )
            assertTrue(BrowserSourceBlock.OBSERVATION_NOT_FRESH in result.blockers)
            assertFalse(result.sourceVerified)
        }
    }

    @Test fun wrongTargetAndWrongBrowserCannotBeReusedAcrossGames() {
        val result = BrowserGameSourcePolicy.evaluate(
            target, syntheticEvidence().copy(
                claimedGameId = "other-game",
                foregroundPackageName = "com.unrelated.browser",
            ),
        )
        assertTrue(BrowserSourceBlock.TARGET_ID_MISMATCH in result.blockers)
        assertTrue(BrowserSourceBlock.BROWSER_NOT_ALLOWED in result.blockers)
    }

    @Test fun riskAcknowledgementIsScopedToExactGameAndRulesRevision() {
        val valid = GameRiskAcknowledgement(target.gameId, target.rulesRevision, true, true)
        assertTrue(valid.appliesTo(target))
        assertFalse(valid.copy(rulesReviewed = false).appliesTo(target))
        assertFalse(valid.copy(warningAcknowledged = false).appliesTo(target))
        assertFalse(valid.copy(gameId = "different-game").appliesTo(target))
        assertFalse(valid.copy(rulesRevision = "old-rules").appliesTo(target))
        assertFalse(valid.appliesTo(target.copy(rulesRevision = "newer-rules")))
    }
}
