package com.alpha0.app.auth

import com.alpha0.app.net.HttpMethod
import com.alpha0.app.net.HttpRequest
import com.alpha0.app.net.HttpResponse
import com.alpha0.app.net.HttpTransport
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.IOException

class AuthApiTransportTest {
    private class FakeTransport(private val response: HttpResponse) : HttpTransport {
        var request: HttpRequest? = null

        override fun execute(request: HttpRequest): HttpResponse {
            this.request = request
            return response
        }
    }

    @Test
    fun loginUsesInjectedSharedTransportAndParsesSession() = runBlocking {
        val transport = FakeTransport(
            HttpResponse(
                200,
                "{\"session_token\":\"access\",\"refresh_token\":\"refresh\",\"scopes\":[\"game:read\"]}",
            ),
        )
        val result = AuthApi("https://example.test/", transport).login(" User@Example.TEST ", "secret")

        assertTrue(result is AuthApi.Result.Success)
        val request = requireNotNull(transport.request)
        assertEquals(HttpMethod.POST, request.method)
        assertEquals("https://example.test/v1/auth/login", request.url)
        assertEquals("application/json", request.headers["Content-Type"])
        assertEquals("application/json", request.headers["Accept"])
        assertEquals(true, String(requireNotNull(request.body)).contains("user@example.test"))
    }

    @Test
    fun transportFailureRemainsNetworkError() = runBlocking {
        val transport = object : HttpTransport {
            override fun execute(request: HttpRequest): HttpResponse = throw IOException("offline")
        }
        val result = AuthApi("https://example.test", transport).refresh("refresh")
        assertEquals(AuthApi.Result.Failure("NETWORK_ERROR"), result)
    }
}
