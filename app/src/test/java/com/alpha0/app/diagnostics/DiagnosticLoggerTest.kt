package com.alpha0.app.diagnostics

import android.content.Context
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [28])
class DiagnosticLoggerTest {

    private fun ctx(): Context = RuntimeEnvironment.getApplication()

    @Test
    fun initialization_and_event_generation() {
        val log = DiagnosticLogger.get(ctx())
        log.clear()
        log.info("APP", "APP_START", "SUCCESS", details = mapOf("sdk" to 28))
        val content = log.readAll()
        assertTrue(content.contains("APP_START"))
        assertTrue(content.contains("\"component\":\"APP\""))
        assertTrue(content.contains("\"result\":\"SUCCESS\""))
    }

    @Test
    fun request_id_is_redacted() {
        val raw = "req-abcdef0123456789-secret"
        val redacted = DiagnosticLogger.redactRequestId(raw)
        assertNotNull(redacted)
        assertFalse(redacted!!.contains("secret"))
        assertFalse(redacted.contains(raw))
        assertTrue(redacted.length <= 16)
    }

    @Test
    fun sensitive_keys_are_redacted_in_details() {
        val log = DiagnosticLogger.get(ctx())
        log.clear()
        log.info(
            "AUTH",
            "LOGIN",
            "SUCCESS",
            details = mapOf(
                "password" to "super-secret",
                "access_token" to "tok_abc",
                "safe_field" to "ok"
            )
        )
        val content = log.readAll()
        assertFalse(content.contains("super-secret"))
        assertFalse(content.contains("tok_abc"))
        assertTrue(content.contains("[REDACTED]") || content.contains("REDACTED"))
        assertTrue(content.contains("safe_field"))
    }

    @Test
    fun exception_logging_has_class_not_secret() {
        val log = DiagnosticLogger.get(ctx())
        log.clear()
        log.error(
            "API",
            "CALL",
            "FAILURE",
            errorCode = "NETWORK",
            throwable = RuntimeException("password=hunter2 token=xyz")
        )
        val content = log.readAll()
        assertTrue(content.contains("RuntimeException"))
        assertFalse(content.contains("hunter2"))
        assertFalse(content.contains("token=xyz"))
    }

    @Test
    fun bounded_log_size_does_not_grow_unbounded() {
        val log = DiagnosticLogger.get(ctx())
        log.clear()
        // Write enough events to exceed soft bound path
        repeat(2000) { i ->
            log.info("TEST", "EVT", "SUCCESS", details = mapOf("i" to i, "pad" to "x".repeat(200)))
        }
        val content = log.readAll()
        // Must stay under hard bound (~512KiB) with margin
        assertTrue("log too large: ${content.length}", content.length < 600_000)
        assertTrue(content.contains("EVT"))
    }

    @Test
    fun no_raw_integrity_or_bearer_in_generated_log() {
        val log = DiagnosticLogger.get(ctx())
        log.clear()
        log.info(
            "INTEGRITY",
            "TOKEN_REQUEST",
            "SUCCESS",
            details = mapOf(
                "integrity_token" to "ya29.raw-token-value",
                "authorization" to "Bearer abc.def.ghi",
                "token_len" to 42
            )
        )
        val content = log.readAll()
        assertFalse(content.contains("ya29.raw-token-value"))
        assertFalse(content.contains("Bearer abc.def.ghi"))
        assertTrue(content.contains("token_len") || content.contains("REDACTED"))
    }
}
