package com.alpha0.app.security

import org.junit.Assert.assertEquals
import org.junit.Test

class HexTest {

    @Test
    fun encodesBytesAsLowercaseHex() {
        val input = byteArrayOf(0x00, 0x01, 0x0f, 0x10, 0x7f, 0x80.toByte(), 0xff.toByte())

        assertEquals("00010f107f80ff", Hex.encode(input))
    }

    @Test
    fun encodesEmptyArray() {
        assertEquals("", Hex.encode(byteArrayOf()))
    }
}
