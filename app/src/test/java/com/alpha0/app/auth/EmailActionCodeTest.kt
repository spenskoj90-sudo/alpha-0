package com.alpha0.app.auth

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class EmailActionCodeTest {
    @Test fun wholeCodePastePreservesLeadingZeros() {
        assertEquals("00001234", normalizeEmailActionCode(" 0000\u00a01234\n"))
        assertTrue(validEmailActionCode("00001234"))
        assertFalse(validEmailActionCode("１２３４５６７８"))
        assertFalse(validEmailActionCode("1234567"))
        assertFalse(validEmailActionCode("123456789"))
    }
    @Test fun earlierOpaqueEmailsRemainUsableWithoutStrippingInternalCharacters() {
        val earlier = "a".repeat(43)
        assertTrue(validEmailActionCode(earlier))
        assertEquals(earlier, normalizeEmailActionCode(" $earlier "))
        assertFalse(validEmailActionCode("a".repeat(20) + " " + "a".repeat(22)))
    }
}
