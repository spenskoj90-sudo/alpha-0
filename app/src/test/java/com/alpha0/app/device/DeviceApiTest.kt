package com.alpha0.app.device

import com.alpha0.app.net.HttpMethod
import com.alpha0.app.net.HttpRequest
import com.alpha0.app.net.HttpResponse
import com.alpha0.app.net.HttpTransport
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class DeviceApiTest {
    @Test
    fun canonicalProofPayloadMatchesCoreCanonicalJsonContract() {
        val payload = DeviceApi.canonicalProofPayload(
            challenge = "challenge-value",
            timestamp = 1_700_000_000L,
            requestId = "request-id",
        )

        assertEquals(
            "{\"challenge\":\"challenge-value\",\"request_id\":\"request-id\",\"timestamp\":1700000000}",
            payload.toString(Charsets.UTF_8),
        )
    }

    @Test
    fun canonicalProofPayloadEscapesStringValuesDeterministically() {
        val first = DeviceApi.canonicalProofPayload(
            challenge = "challenge\\\"value",
            timestamp = 42L,
            requestId = "request\\id",
        )
        val second = DeviceApi.canonicalProofPayload(
            challenge = "challenge\\\"value",
            timestamp = 42L,
            requestId = "request\\id",
        )

        assertArrayEquals(first, second)
    }

    @Test
    fun bindUsesSharedTransportAndPreservesBearerHeader() {
        var captured: HttpRequest? = null
        val transport = object : HttpTransport {
            override fun execute(request: HttpRequest): HttpResponse {
                captured = request
                return HttpResponse(
                    200,
                    "{\"device_id\":\"device-123\",\"state\":\"BOUND\",\"challenge\":\"challenge\"}",
                )
            }
        }

        val result = DeviceApi("https://example.test/", transport).bind(
            accessToken = "access",
            platform = "ANDROID",
            publicKeyDerB64 = "public-key",
            fingerprintSha256 = "fingerprint",
        )

        assertTrue(result is DeviceApi.Result.Success)
        val request = requireNotNull(captured)
        assertEquals(HttpMethod.POST, request.method)
        assertEquals("https://example.test/v1/devices/bind", request.url)
        assertEquals("Bearer access", request.headers["Authorization"])
        assertEquals("application/json", request.headers["Content-Type"])
        assertTrue(String(requireNotNull(request.body)).contains("fingerprint"))
    }
}
