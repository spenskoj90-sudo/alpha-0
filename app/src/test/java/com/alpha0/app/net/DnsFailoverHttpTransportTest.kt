package com.alpha0.app.net

import java.io.IOException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import org.junit.Assert.assertEquals
import org.junit.Assert.fail
import org.junit.Test

class DnsFailoverHttpTransportTest {
    private class RecordingTransport(
        private val responder: (HttpRequest, Int) -> HttpResponse,
    ) : HttpTransport {
        val requests = mutableListOf<HttpRequest>()

        override fun execute(request: HttpRequest): HttpResponse {
            requests += request
            return responder(request, requests.lastIndex)
        }
    }

    @Test
    fun unknownHostRetriesOnceThroughFallbackWithSameCorrelationAndPayload() {
        val delegate = RecordingTransport { request, index ->
            if (index == 0) throw UnknownHostException("core.example")
            assertEquals("https://relay.example/mobile-core/v1/auth/login", request.url)
            HttpResponse(200, """{"ok":true}""")
        }
        var failovers = 0
        val transport = DnsFailoverHttpTransport(
            primaryBaseUrl = "https://core.example",
            fallbackBaseUrl = "https://relay.example/mobile-core",
            delegate = delegate,
            requestIdFactory = { "dns-failover-request" },
            onDnsFailover = { primary, fallback ->
                assertEquals("https://core.example", primary)
                assertEquals("https://relay.example/mobile-core", fallback)
                failovers += 1
            },
        )
        val body = """{"email":"redacted@example.test"}""".toByteArray()

        val response = transport.execute(
            HttpRequest(
                HttpMethod.POST,
                "https://core.example/v1/auth/login",
                headers = mapOf(
                    "Authorization" to "Bearer opaque",
                    "Idempotency-Key" to "idem-1",
                ),
                body = body,
            )
        )

        assertEquals(200, response.status)
        assertEquals(2, delegate.requests.size)
        assertEquals("https://core.example/v1/auth/login", delegate.requests[0].url)
        assertEquals("dns-failover-request", delegate.requests[0].headers["X-Request-ID"])
        assertEquals("dns-failover-request", delegate.requests[1].headers["X-Request-ID"])
        assertEquals("Bearer opaque", delegate.requests[1].headers["Authorization"])
        assertEquals("idem-1", delegate.requests[1].headers["Idempotency-Key"])
        assertEquals(body.toList(), delegate.requests[1].body!!.toList())
        assertEquals(1, failovers)
    }

    @Test
    fun genericIoFailureIsNeverRetriedForPostBecauseOutcomeMayBeAmbiguous() {
        val delegate = RecordingTransport { _, _ -> throw IOException("connection reset") }
        val transport = DnsFailoverHttpTransport(
            primaryBaseUrl = "https://core.example",
            fallbackBaseUrl = "https://relay.example/mobile-core",
            delegate = delegate,
        )

        try {
            transport.execute(HttpRequest(HttpMethod.POST, "https://core.example/v1/auth/register", body = "{}".toByteArray()))
            fail("expected IOException")
        } catch (_: IOException) {
            assertEquals(1, delegate.requests.size)
        }
    }

    @Test
    fun genericReadIoFailureFailsOverOnceBecauseGetIsReplaySafe() {
        val delegate = RecordingTransport { request, index ->
            if (index == 0) throw IOException("unexpected end of stream")
            assertEquals("https://relay.example/mobile-core/v1/auth/providers", request.url)
            HttpResponse(200, """{"providers":[]}""")
        }
        var reason: String? = null
        val transport = DnsFailoverHttpTransport(
            primaryBaseUrl = "https://core.example",
            fallbackBaseUrl = "https://relay.example/mobile-core",
            delegate = delegate,
            requestIdFactory = { "read-failover-request" },
            onSafeReadFailover = { observed, primary, fallback ->
                reason = observed
                assertEquals("https://core.example", primary)
                assertEquals("https://relay.example/mobile-core", fallback)
            },
        )

        val response = transport.execute(HttpRequest(HttpMethod.GET, "https://core.example/v1/auth/providers"))

        assertEquals(200, response.status)
        assertEquals(2, delegate.requests.size)
        assertEquals("read-failover-request", delegate.requests[0].headers["X-Request-ID"])
        assertEquals("read-failover-request", delegate.requests[1].headers["X-Request-ID"])
        assertEquals("IOException", reason)
    }

    @Test
    fun connectTimeoutOnHealthReadFailsOverWithoutReplayingWrites() {
        val delegate = RecordingTransport { request, index ->
            if (index == 0) throw SocketTimeoutException("connect timed out")
            assertEquals("https://relay.example/mobile-core/healthz", request.url)
            HttpResponse(200, """{"status":"UP"}""")
        }
        val transport = DnsFailoverHttpTransport(
            primaryBaseUrl = "https://core.example",
            fallbackBaseUrl = "https://relay.example/mobile-core",
            delegate = delegate,
        )

        val response = transport.execute(HttpRequest(HttpMethod.GET, "https://core.example/healthz"))

        assertEquals(200, response.status)
        assertEquals(2, delegate.requests.size)
    }

    @Test
    fun requestOutsidePrimaryOriginIsNeverRedirectedToFallback() {
        val delegate = RecordingTransport { request, _ ->
            assertEquals("https://identity.example/challenge", request.url)
            HttpResponse(200, "{}")
        }
        val transport = DnsFailoverHttpTransport(
            primaryBaseUrl = "https://core.example",
            fallbackBaseUrl = "https://relay.example/mobile-core",
            delegate = delegate,
        )

        assertEquals(200, transport.execute(HttpRequest(HttpMethod.GET, "https://identity.example/challenge")).status)
        assertEquals(1, delegate.requests.size)
    }

    @Test
    fun blankFallbackKeepsCanonicalSingleAttemptBehavior() {
        val delegate = RecordingTransport { _, _ -> throw UnknownHostException("core.example") }
        val transport = DnsFailoverHttpTransport(
            primaryBaseUrl = "https://core.example",
            fallbackBaseUrl = "",
            delegate = delegate,
        )

        try {
            transport.execute(HttpRequest(HttpMethod.GET, "https://core.example/v1/auth/providers"))
            fail("expected UnknownHostException")
        } catch (_: UnknownHostException) {
            assertEquals(1, delegate.requests.size)
        }
    }
}
