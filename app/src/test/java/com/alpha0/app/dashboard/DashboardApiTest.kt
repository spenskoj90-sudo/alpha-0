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
    fun getAuditUsesCallerSessionAndParsesServerHistory() {
        var captured: HttpRequest? = null
        val transport = object : HttpTransport {
            override fun execute(request: HttpRequest): HttpResponse {
                captured = request
                return HttpResponse(
                    200,
                    """{"events":[{"action":"auth:provider-link","resource":"provider:google","decision":"ALLOW","reason_code":"FEDERATED_IDENTITY_VALID","request_id":"req-1","created_at":"2026-09-26T06:00:00Z"}]}""",
                )
            }
        }

        val result = DashboardApi("https://example.test/", transport).getAudit("access")

        assertTrue(result is DashboardApi.Result.Success)
        val events = (result as DashboardApi.Result.Success).value
        assertEquals(1, events.size)
        assertEquals("auth:provider-link", events.single().action)
        assertEquals("provider:google", events.single().resource)
        assertEquals("ALLOW", events.single().decision)
        assertEquals("FEDERATED_IDENTITY_VALID", events.single().reasonCode)
        assertEquals("req-1", events.single().requestId)
        assertEquals("2026-09-26T06:00:00Z", events.single().createdAt)
        val request = requireNotNull(captured)
        assertEquals(HttpMethod.GET, request.method)
        assertEquals("https://example.test/v1/audit", request.url)
        assertEquals("Bearer access", request.headers["Authorization"])
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

    @Test
    fun signOutRevokesServerSessionBeforeLocalClear() {
        var captured: HttpRequest? = null
        val transport = object : HttpTransport {
            override fun execute(request: HttpRequest): HttpResponse {
                captured = request
                return HttpResponse(200, "{\"revoked\":true}")
            }
        }

        val result = DashboardApi("https://example.test", transport).revokeSession("access")

        assertEquals(DashboardApi.Result.Success(true), result)
        val request = requireNotNull(captured)
        assertEquals(HttpMethod.POST, request.method)
        assertEquals("https://example.test/v1/sessions/revoke", request.url)
        assertEquals("Bearer access", request.headers["Authorization"])
    }
}
