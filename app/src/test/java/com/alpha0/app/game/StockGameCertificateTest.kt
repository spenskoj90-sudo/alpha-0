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
    @Test fun `same game version with different installed signer is different identity`() {
        val first = StockGameInstall("4.0.0", 912, StockGameCertificate.digest(listOf(byteArrayOf(1))))
        val second = first.copy(signerSha256 = StockGameCertificate.digest(listOf(byteArrayOf(2))))
        assertNotEquals(first, second)
        assertNull(StockGameInstall("4.0.0", 912).signerSha256)
    }
}
