package com.alpha0.app.net

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
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
    private class RecordingTransport(
        private val responder: (HttpRequest, Int) -> HttpResponse,
    ) : HttpTransport {
        val requests = mutableListOf<HttpRequest>()

        override fun execute(request: HttpRequest): HttpResponse {
            requests += request
            return responder(request, requests.lastIndex)
        }
    }

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
    fun sessionRefreshingTransportRotatesOnceAndRetriesWithSameCorrelationId() {
        var session: SessionCredentials? = SessionCredentials("access-old", "refresh-old")
        val delegate = RecordingTransport { request, index ->
            when (index) {
                0 -> HttpResponse(401, """{"code":"INVALID_SESSION"}""")
                1 -> {
                    assertEquals("https://core.example/v1/sessions/refresh", request.url)
                    assertTrue(request.body!!.toString(Charsets.UTF_8).contains("refresh-old"))
                    assertEquals("request-123", request.headers["X-Request-ID"])
                    HttpResponse(200, """{"session_token":"access-new","refresh_token":"refresh-new"}""")
                }
                2 -> HttpResponse(200, """{"ok":true}""")
                else -> throw AssertionError("unexpected request $index")
            }
        }
        val transport = SessionRefreshingHttpTransport(
            baseUrl = "https://core.example",
            delegate = delegate,
            sessionProvider = { session },
            onSessionRefreshed = { session = it },
            onSessionInvalidated = { session = null },
        )

        val response = transport.execute(
            HttpRequest(
                HttpMethod.GET,
                "https://core.example/v1/devices/device-1",
                headers = mapOf(
                    "Authorization" to "Bearer stale-ui-token",
                    "X-Request-ID" to "request-123",
                ),
            )
        )

        assertEquals(200, response.status)
        assertEquals(3, delegate.requests.size)
        assertEquals("Bearer access-old", delegate.requests[0].headers["Authorization"])
        assertEquals("Bearer access-new", delegate.requests[2].headers["Authorization"])
        assertEquals("request-123", delegate.requests[2].headers["X-Request-ID"])
        assertEquals(SessionCredentials("access-new", "refresh-new"), session)
    }

    @Test
    fun invalidRefreshClearsSessionAndDoesNotReplayProtectedRequest() {
        var session: SessionCredentials? = SessionCredentials("access-old", "refresh-old")
        var invalidations = 0
        val delegate = RecordingTransport { _, index ->
            when (index) {
                0 -> HttpResponse(401, """{"code":"INVALID_SESSION"}""")
                1 -> HttpResponse(401, """{"code":"INVALID_REFRESH"}""")
                else -> throw AssertionError("protected request must not be retried")
            }
        }
        val transport = SessionRefreshingHttpTransport(
            baseUrl = "https://core.example",
            delegate = delegate,
            sessionProvider = { session },
            onSessionRefreshed = { session = it },
            onSessionInvalidated = {
                session = null
                invalidations += 1
            },
        )

        val response = transport.execute(
            HttpRequest(
                HttpMethod.GET,
                "https://core.example/v1/entitlements/me",
                headers = mapOf("Authorization" to "Bearer access-old"),
            )
        )

        assertEquals(401, response.status)
        assertEquals(2, delegate.requests.size)
        assertEquals(1, invalidations)
        assertNull(session)
    }

    @Test
    fun latestStoredTokenReplacesStaleCallerBearerWithoutRefresh() {
        val session = SessionCredentials("access-current", "refresh-current")
        val delegate = RecordingTransport { request, _ ->
            assertEquals("Bearer access-current", request.headers["Authorization"])
            HttpResponse(200, "{}")
        }
        val transport = SessionRefreshingHttpTransport(
            baseUrl = "https://core.example",
            delegate = delegate,
            sessionProvider = { session },
            onSessionRefreshed = {},
            onSessionInvalidated = {},
        )

        val response = transport.execute(
            HttpRequest(
                HttpMethod.GET,
                "https://core.example/v1/account/security",
                headers = mapOf("Authorization" to "Bearer stale-compose-token"),
            )
        )

        assertEquals(200, response.status)
        assertEquals(1, delegate.requests.size)
    }

    @Test
    fun nonCoreOrUnauthenticatedRequestsAreNeverRefreshed() {
        var session: SessionCredentials? = SessionCredentials("access", "refresh")
        val delegate = RecordingTransport { request, _ -> HttpResponse(401, request.url) }
        val transport = SessionRefreshingHttpTransport(
            baseUrl = "https://core.example",
            delegate = delegate,
            sessionProvider = { session },
            onSessionRefreshed = { session = it },
            onSessionInvalidated = { session = null },
        )

        transport.execute(HttpRequest(HttpMethod.GET, "https://core.example/v1/auth/providers"))
        transport.execute(
            HttpRequest(
                HttpMethod.GET,
                "https://other.example/v1/resource",
                headers = mapOf("Authorization" to "Bearer should-not-be-rewritten"),
            )
        )

        assertEquals(2, delegate.requests.size)
        assertEquals("Bearer should-not-be-rewritten", delegate.requests[1].headers["Authorization"])
        assertEquals(SessionCredentials("access", "refresh"), session)
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
