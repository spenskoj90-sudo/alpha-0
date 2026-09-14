package com.alpha0.app.net

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID

class HttpTransportTest {
    private class FakeConnection(
        url: URL,
        private val statusCode: Int,
        private val responseBytes: ByteArray,
    ) : HttpURLConnection(url) {
        val written = ByteArrayOutputStream()
        var disconnected = false

        override fun disconnect() {
            disconnected = true
        }

        override fun usingProxy(): Boolean = false

        override fun connect() = Unit

        override fun getResponseCode(): Int = statusCode

        override fun getInputStream(): InputStream {
            if (statusCode !in 200..299) throw IOException("error response")
            return ByteArrayInputStream(responseBytes)
        }

        override fun getErrorStream(): InputStream? =
            if (statusCode in 200..299) null else ByteArrayInputStream(responseBytes)

        override fun getOutputStream(): OutputStream = written
    }

    @Test
    fun urlConnectionTransportAppliesBoundedPolicyAndSingleAttempt() {
        var opens = 0
        lateinit var connection: FakeConnection
        val transport = UrlConnectionHttpTransport(
            connectTimeoutMs = 123,
            readTimeoutMs = 456,
            maxResponseBytes = 1_024,
            requestIdFactory = { "11111111-1111-1111-1111-111111111111" },
            connectionFactory = { url ->
                opens += 1
                FakeConnection(url, 200, "{\"ok\":true}".toByteArray()).also { connection = it }
            },
        )

        val response = transport.execute(
            HttpRequest(
                method = HttpMethod.POST,
                url = "https://example.test/v1/resource",
                headers = mapOf("Authorization" to "Bearer opaque", "Accept" to "application/json"),
                body = "{}".toByteArray(),
            )
        )

        assertEquals(1, opens)
        assertEquals(200, response.status)
        assertEquals("{\"ok\":true}", response.body)
        assertEquals("POST", connection.requestMethod)
        assertEquals(123, connection.connectTimeout)
        assertEquals(456, connection.readTimeout)
        assertFalse(connection.instanceFollowRedirects)
        assertEquals("Bearer opaque", connection.getRequestProperty("Authorization"))
        assertEquals("11111111-1111-1111-1111-111111111111", connection.getRequestProperty("X-Request-ID"))
        assertEquals("{}", connection.written.toString(Charsets.UTF_8.name()))
        assertTrue(connection.disconnected)
    }

    @Test
    fun generatedCorrelationIdIsUuidWhenCallerDoesNotProvideOne() {
        lateinit var connection: FakeConnection
        val transport = UrlConnectionHttpTransport(
            connectionFactory = { url -> FakeConnection(url, 200, ByteArray(0)).also { connection = it } },
        )
        transport.execute(HttpRequest(HttpMethod.GET, "https://example.test/resource"))
        UUID.fromString(connection.getRequestProperty("X-Request-ID"))
    }

    @Test
    fun explicitCorrelationIdIsPreservedForIdempotentCallerFlows() {
        lateinit var connection: FakeConnection
        val transport = UrlConnectionHttpTransport(
            requestIdFactory = { "generated-must-not-replace-explicit" },
            connectionFactory = { url -> FakeConnection(url, 200, ByteArray(0)).also { connection = it } },
        )
        transport.execute(
            HttpRequest(
                HttpMethod.GET,
                "https://example.test/resource",
                headers = mapOf("X-Request-ID" to "event-sync-explicit-id"),
            )
        )
        assertEquals("event-sync-explicit-id", connection.getRequestProperty("X-Request-ID"))
    }

    @Test
    fun responseBodyLimitFailsClosed() {
        val transport = UrlConnectionHttpTransport(
            maxResponseBytes = 5,
            connectionFactory = { url -> FakeConnection(url, 200, "123456".toByteArray()) },
        )

        try {
            transport.execute(HttpRequest(HttpMethod.GET, "https://example.test/oversized"))
            fail("expected IOException")
        } catch (_: IOException) {
            // Expected: callers map transport I/O failures to stable fail-closed error codes.
        }
    }

    @Test
    fun unsupportedSchemeIsRejectedBeforeConnectionOpen() {
        var opens = 0
        val transport = UrlConnectionHttpTransport(
            connectionFactory = { url ->
                opens += 1
                FakeConnection(url, 200, ByteArray(0))
            },
        )

        try {
            transport.execute(HttpRequest(HttpMethod.GET, "ftp://example.test/resource"))
            fail("expected IOException")
        } catch (_: IOException) {
            assertEquals(0, opens)
        }
    }
}
