package com.alpha0.app.security

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
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

    assertNotEquals(first, second)
}

@Test
fun sha256FingerprintHasExpectedLength() {
    val result = fingerprint("ALPHA-0".toByteArray())

    assertEquals(64, result.length)
}

@Test
fun sha256FingerprintContainsOnlyHexCharacters() {
    val result = fingerprint("ALPHA-0".toByteArray())

    assert(result.all { it in '0'..'9' || it in 'a'..'f' })
}

private fun fingerprint(data: ByteArray): String {
    return MessageDigest
        .getInstance("SHA-256")
        .digest(data)
        .joinToString("") {
            "%02x".format(it)
        }
}

}
