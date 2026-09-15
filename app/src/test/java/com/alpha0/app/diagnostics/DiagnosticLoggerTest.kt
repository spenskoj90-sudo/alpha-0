package com.alpha0.app.diagnostics

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Pure JVM tests for diagnostic privacy/security helpers. */
class DiagnosticLoggerTest {

    @Test
    fun request_id_redaction_is_stable_and_short() {
        val raw = "req-abcdef0123456789-secret-value"
        val a = DiagnosticLogger.redactRequestId(raw)
        val b = DiagnosticLogger.redactRequestId(raw)
        assertNotNull(a)
        assertEquals(a, b)
        assertFalse(a!!.contains("secret"))
        assertFalse(a.contains(raw))
        assertTrue(a.length in 8..16)
        assertTrue(a.all { it in '0'..'9' || it in 'a'..'f' })
    }

    @Test
    fun request_id_null_or_blank_returns_null() {
        assertEquals(null, DiagnosticLogger.redactRequestId(null))
        assertEquals(null, DiagnosticLogger.redactRequestId(""))
        assertEquals(null, DiagnosticLogger.redactRequestId("   "))
    }

    @Test
    fun different_request_ids_produce_different_redactions() {
        val a = DiagnosticLogger.redactRequestId("alpha-req-1")
        val b = DiagnosticLogger.redactRequestId("alpha-req-2")
        assertNotNull(a)
        assertNotNull(b)
        assertFalse(a == b)
    }

    @Test
    fun redact_does_not_echo_jwt_like_input() {
        val jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature"
        val redacted = DiagnosticLogger.redactRequestId(jwt)!!
        assertFalse(redacted.contains("eyJ"))
        assertFalse(redacted.contains("payload"))
        assertFalse(redacted.contains("signature"))
    }

    @Test
    fun sensitive_detail_key_detection_is_fail_closed() {
        for (key in listOf("access_token", "Authorization", "private_key_pem", "play_integrity_token", "request_body")) {
            assertTrue("expected sensitive key: $key", DiagnosticLogger.isSensitiveDetailKey(key))
        }
        assertFalse(DiagnosticLogger.isSensitiveDetailKey("network_transport"))
        assertFalse(DiagnosticLogger.isSensitiveDetailKey("route"))
    }

    @Test
    fun freeform_scrubber_removes_secret_and_email_material() {
        val raw = "Bearer abcdefghijklmnop token=supersecret user@example.com"
        val safe = DiagnosticLogger.sanitizeTextForDiagnostics(raw)
        assertFalse(safe.contains("abcdefghijklmnop"))
        assertFalse(safe.contains("supersecret"))
        assertFalse(safe.contains("user@example.com"))
        assertTrue(safe.contains("[REDACTED]"))
        assertTrue(safe.contains("[REDACTED_EMAIL]"))
    }

    @Test
    fun scrubber_obeys_output_bound() {
        val safe = DiagnosticLogger.sanitizeTextForDiagnostics("x".repeat(5000), 128)
        assertTrue(safe.length <= 128)
    }
}
