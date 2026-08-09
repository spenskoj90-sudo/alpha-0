package com.alpha0.app.security

import org.junit.Assert.assertEquals
import org.junit.Test
import java.security.MessageDigest

class FingerprintTest {

    @Test
    fun sha256FingerprintIsDeterministic() {
        val input = "ALPHA-0".toByteArray()

        val first = fingerprint(input)
        val second = fingerprint(input)

        assertEquals(first, second)
    }

    @Test
    fun sha256FingerprintChangesWhenInputChanges() {
        val first = fingerprint("ALPHA-0".toByteArray())
        val second = fingerprint("ALPHA-0-CHANGED".toByteArray())

        assert(first != second)
    }

    private fun fingerprint(data: ByteArray): String {
        return MessageDigest
            .getInstance("SHA-256")
            .digest(data)
            .joinToString("") { "%02x".format(it) }
    }
}
