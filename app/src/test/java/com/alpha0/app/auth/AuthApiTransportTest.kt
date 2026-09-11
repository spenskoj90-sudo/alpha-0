package com.alpha0.app.auth

import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AuthApiTransportTest {
    private class FakeTransport(private val response: AuthHttpResponse) : AuthHttpTransport {
        var url: String? = null
        var body: ByteArray? = null

        override fun postJson(url: String, body: ByteArray): AuthHttpResponse {
            this.url = url
            this.body = body
            return response
        }
    }

    @Test
    fun loginUsesInjectedTransportAndParsesSession() = runBlocking {
        val transport = FakeTransport(
            AuthHttpResponse(
                200,
                "{\"session_token\":\"access\",\"refresh_token\":\"refresh\",\"scopes\":[\"game:read\"]}",
            ),
        )
        val result = AuthApi("https://example.test/", transport).login(" User@Example.TEST ", "secret")

        assertTrue(result is AuthApi.Result.Success)
        assertEquals("https://example.test/v1/auth/login", transport.url)
        assertEquals(true, String(requireNotNull(transport.body)).contains("user@example.test"))
    }

    @Test
    fun transportFailureRemainsNetworkError() = runBlocking {
        val transport = object : AuthHttpTransport {
            override fun postJson(url: String, body: ByteArray): AuthHttpResponse = throw java.io.IOException("offline")
        }
        val result = AuthApi("https://example.test", transport).refresh("refresh")
        assertEquals(AuthApi.Result.Failure("NETWORK_ERROR"), result)
    }
}
