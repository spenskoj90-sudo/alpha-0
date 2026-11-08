package com.alpha0.app.game

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class GameSignerFingerprintTest {
    @Test fun completeDigestIsShownWithoutTruncationOrChangingItsBytes() {
        val digest = "0123456789abcdef".repeat(4)
        val grouped = GameSignerFingerprint.grouped(digest)!!
        assertEquals(digest, grouped.replace(" ", ""))
        assertEquals(8, grouped.split(' ').size)
        assertEquals(List(8) { 8 }, grouped.split(' ').map { it.length })
    }

    @Test fun missingMalformedOrAmbiguousLocalMetadataIsNotPresentedAsFingerprint() {
        for (bad in listOf<String?>(
                null, "", "a".repeat(63), "a".repeat(65),
                "A".repeat(64), "z".repeat(64),
                "a".repeat(32) + "\n" + "a".repeat(31),
                "a".repeat(32) + " " + "a".repeat(31),
            )) assertNull(GameSignerFingerprint.grouped(bad))
    }
}
