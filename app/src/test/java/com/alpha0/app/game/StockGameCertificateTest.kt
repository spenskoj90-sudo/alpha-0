package com.alpha0.app.game

import org.junit.Assert.*
import org.junit.Test
import java.security.MessageDigest

class StockGameCertificateTest {
    @Test fun `one current signer hashes deterministically to lowercase SHA-256`() {
        val bytes = byteArrayOf(0, 1, 2, 127, -1)
        val expected = MessageDigest.getInstance("SHA-256").digest(bytes)
            .joinToString("") { "%02x".format(it.toInt() and 0xff) }
        assertEquals(expected, StockGameCertificate.digest(listOf(bytes)))
        assertEquals(64, expected.length)
    }
    @Test fun `missing ambiguous or oversized signer stays unknown`() {
        assertNull(StockGameCertificate.digest(emptyList()))
        assertNull(StockGameCertificate.digest(listOf(byteArrayOf())))
        assertNull(StockGameCertificate.digest(listOf(byteArrayOf(1), byteArrayOf(2))))
        assertNull(StockGameCertificate.digest(listOf(ByteArray(16385))))
    }
    @Test fun `consent and service fence rejects identity drift or absent metadata`() {
        val expected = StockGameInstall("4.0.0", 912, "a".repeat(64))
        assertTrue(GameInstallFence.matches("4.0.0", 912, "a".repeat(64), expected))
        assertFalse(GameInstallFence.matches(null, 912, expected.signerSha256, expected))
        assertFalse(GameInstallFence.matches("4.0.0", null, expected.signerSha256, expected))
        assertFalse(GameInstallFence.matches("4.0.0", 912, expected.signerSha256, null))
        assertFalse(GameInstallFence.matches("4.0.1", 912, expected.signerSha256, expected))
        assertFalse(GameInstallFence.matches("4.0.0", 913, expected.signerSha256, expected))
        assertFalse(GameInstallFence.matches("4.0.0", 912, "b".repeat(64), expected))
        assertFalse(GameInstallFence.matches("4.0.0", 912, null, expected))
        // UNKNOWN is explicit metadata, not an omitted Intent field. Missing
        // SIGNER is rejected even if the current signer is itself unknown.
        val unknown = StockGameInstall("4.0.0", 912)
        assertTrue(GameInstallFence.matches("4.0.0", 912, null, unknown, signerSupplied = true))
        assertFalse(GameInstallFence.matches("4.0.0", 912, null, unknown, signerSupplied = false))
        assertFalse(GameInstallFence.matches("4.0.0", 912, expected.signerSha256, expected, signerSupplied = false))
    }
    @Test fun `game resume stops active capture on installed identity change`() {
        val expected = StockGameInstall("4.0.2", 922, "a".repeat(64))
        val changed = listOf<StockGameInstall?>(
            null,
            expected.copy(versionName = "4.0.3"),
            expected.copy(versionCode = 923),
            expected.copy(signerSha256 = "b".repeat(64)),
            expected.copy(signerSha256 = null),
        )
        for (status in listOf(ObservationStatus.WAITING, ObservationStatus.OBSERVING, ObservationStatus.PAUSED)) {
            val active = GameObservationViewState(ObservationSnapshot(status = status, captureId = "capture"), expected)
            assertFalse(GameInstallFence.activeCaptureRequiresStop(active, expected))
            changed.forEach { assertTrue(GameInstallFence.activeCaptureRequiresStop(active, it)) }
            assertTrue(GameInstallFence.activeCaptureRequiresStop(active.copy(installed = null), expected))
        }
    }

    @Test fun `inactive capture is not stopped because game metadata changes`() {
        val expected = StockGameInstall("4.0.2", 922, "a".repeat(64))
        for (status in listOf(ObservationStatus.STOPPED, ObservationStatus.FAILED)) {
            val inactive = GameObservationViewState(ObservationSnapshot(status = status), expected)
            assertFalse(GameInstallFence.activeCaptureRequiresStop(inactive, null))
            assertFalse(GameInstallFence.activeCaptureRequiresStop(inactive, expected.copy(versionCode = 923)))
        }
    }
    @Test fun `same game version with different installed signer is different identity`() {
        val first = StockGameInstall("4.0.0", 912, StockGameCertificate.digest(listOf(byteArrayOf(1))))
        val second = first.copy(signerSha256 = StockGameCertificate.digest(listOf(byteArrayOf(2))))
        assertNotEquals(first, second)
        assertNull(StockGameInstall("4.0.0", 912).signerSha256)
    }
}
