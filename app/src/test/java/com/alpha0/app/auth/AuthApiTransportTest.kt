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
import java.net.SocketTimeoutException

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

    @Test
    fun loginTimeoutIsSafeToRetry() = runBlocking {
        val transport = object : HttpTransport {
            override fun execute(request: HttpRequest): HttpResponse = throw SocketTimeoutException("staging wake")
        }

        val result = AuthApi("https://example.test", transport).login("user@example.test", "secret")

        assertEquals(AuthApi.Result.Failure("REQUEST_TIMEOUT"), result)
    }

    @Test
    fun registrationTimeoutDoesNotClaimThatTheWriteFailed() = runBlocking {
        val transport = object : HttpTransport {
            override fun execute(request: HttpRequest): HttpResponse = throw SocketTimeoutException("staging wake")
        }

        val result = AuthApi("https://example.test", transport).register("user@example.test", "secret")

        assertEquals(AuthApi.Result.Failure("REGISTER_OUTCOME_UNKNOWN"), result)
    }

    @Test
    fun passwordResetRequestUsesNonEnumeratingActionEndpoint() = runBlocking {
        val transport = FakeTransport(HttpResponse(202, "{\"status\":\"ACCEPTED\"}"))
        val result = AuthApi("https://example.test", transport).requestPasswordReset(" User@Example.TEST ")

        assertEquals(AuthApi.ActionResult.Success("ACCEPTED"), result)
        val request = requireNotNull(transport.request)
        assertEquals("https://example.test/v1/auth/password-reset/request", request.url)
        assertTrue(String(requireNotNull(request.body)).contains("user@example.test"))
    }

    @Test
    fun passwordResetConfirmationSendsCodeAndNewPasswordToDedicatedEndpoint() = runBlocking {
        val transport = FakeTransport(HttpResponse(200, "{\"status\":\"PASSWORD_UPDATED\"}"))
        val result = AuthApi("https://example.test", transport)
            .confirmPasswordReset("one-time-code-value-that-is-long-enough", "new-password-value")

        assertEquals(AuthApi.ActionResult.Success("PASSWORD_UPDATED"), result)
        val request = requireNotNull(transport.request)
        assertEquals("https://example.test/v1/auth/password-reset/confirm", request.url)
        val body = String(requireNotNull(request.body))
        assertTrue(body.contains("one-time-code-value-that-is-long-enough"))
        assertTrue(body.contains("new-password-value"))
    }

    @Test
    fun emailVerificationConfirmationUsesDedicatedActionParser() = runBlocking {
        val transport = FakeTransport(HttpResponse(200, "{\"status\":\"VERIFIED\"}"))
        val result = AuthApi("https://example.test", transport)
            .confirmEmailVerification("one-time-email-verification-code-value")

        assertEquals(AuthApi.ActionResult.Success("VERIFIED"), result)
        assertEquals("https://example.test/v1/auth/email-verification/confirm", requireNotNull(transport.request).url)
    }

}
