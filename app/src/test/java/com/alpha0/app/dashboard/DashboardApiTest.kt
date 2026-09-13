package com.alpha0.app.dashboard

import com.alpha0.app.net.HttpMethod
import com.alpha0.app.net.HttpRequest
import com.alpha0.app.net.HttpResponse
import com.alpha0.app.net.HttpTransport
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.IOException

class DashboardApiTest {
    @Test
    fun getDeviceUsesSharedTransportAndBearerHeader() {
        var captured: HttpRequest? = null
        val transport = object : HttpTransport {
            override fun execute(request: HttpRequest): HttpResponse {
                captured = request
                return HttpResponse(
                    200,
                    "{\"device_id\":\"device-1\",\"state\":\"BOUND\",\"platform\":\"ANDROID\",\"fingerprint_sha256\":\"fp\",\"algorithm\":\"ES256\",\"security_status\":\"OK\"}",
                )
            }
        }

        val result = DashboardApi("https://example.test/", transport).getDevice("access", "device-1")

        assertTrue(result is DashboardApi.Result.Success)
        val request = requireNotNull(captured)
        assertEquals(HttpMethod.GET, request.method)
        assertEquals("https://example.test/v1/devices/device-1", request.url)
        assertEquals("Bearer access", request.headers["Authorization"])
        assertEquals("application/json", request.headers["Accept"])
    }

    @Test
    fun networkFailureDoesNotExposeExceptionDetails() {
        val transport = object : HttpTransport {
            override fun execute(request: HttpRequest): HttpResponse {
                throw IOException("socket path /private/data leaked")
            }
        }

        val result = DashboardApi("https://example.test", transport).getEntitlements("access")

        assertEquals(DashboardApi.Result.Failure("NETWORK_ERROR"), result)
    }
}
