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


    @Test
    fun providerCatalogParsesOnlyServerDeclaredProviderState() = runBlocking {
        val transport = FakeTransport(
            HttpResponse(
                200,
                "{\"providers\":[{\"provider\":\"google\",\"enabled\":true,\"flow\":\"credential-manager\",\"client_id\":\"web-client\"},{\"provider\":\"vk\",\"enabled\":false,\"flow\":\"oauth-pkce\",\"client_id\":null}]}",
            ),
        )
        val result = AuthApi("https://example.test", transport).providerCatalog()

        assertTrue(result is AuthApi.ProviderCatalogResult.Success)
        val providers = (result as AuthApi.ProviderCatalogResult.Success).providers
        assertEquals(2, providers.size)
        assertEquals("google", providers[0].provider)
        assertEquals(true, providers[0].enabled)
        assertEquals("https://example.test/v1/auth/providers", requireNotNull(transport.request).url)
        assertEquals(HttpMethod.GET, requireNotNull(transport.request).method)
    }

    @Test
    fun googleChallengeAndLoginUseNonceBoundEndpoints() = runBlocking {
        val challengeTransport = FakeTransport(
            HttpResponse(
                200,
                "{\"provider\":\"google\",\"client_id\":\"web-client\",\"nonce\":\"abcdefghijklmnopqrstuvwxyz1234567890\"}",
            ),
        )
        val challenge = AuthApi("https://example.test", challengeTransport).googleChallenge()
        assertTrue(challenge is AuthApi.GoogleChallengeResult.Success)
        assertEquals(
            "https://example.test/v1/auth/providers/google/challenge",
            requireNotNull(challengeTransport.request).url,
        )

        val loginTransport = FakeTransport(
            HttpResponse(
                200,
                "{\"session_token\":\"access\",\"refresh_token\":\"refresh\",\"scopes\":[\"game:read\"]}",
            ),
        )
        val login = AuthApi("https://example.test", loginTransport)
            .loginGoogle("header.payload.signature", "abcdefghijklmnopqrstuvwxyz1234567890")
        assertTrue(login is AuthApi.Result.Success)
        val body = String(requireNotNull(requireNotNull(loginTransport.request).body))
        assertTrue(body.contains("header.payload.signature"))
        assertTrue(body.contains("abcdefghijklmnopqrstuvwxyz1234567890"))
    }

    @Test
    fun browserProviderStartAndCompleteKeepPkceMaterialServerBound() = runBlocking {
        val startTransport = FakeTransport(
            HttpResponse(
                200,
                "{\"provider\":\"telegram\",\"authorization_url\":\"https://oauth.telegram.org/auth?state=public\",\"state\":\"abcdefghijklmnopqrstuvwxyz1234567890\",\"code_verifier\":\"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890-._~\"}",
            ),
        )
        val start = AuthApi("https://example.test", startTransport).startBrowserProvider("telegram")
        assertTrue(start is AuthApi.BrowserStartResult.Success)
        assertEquals(
            "https://example.test/v1/auth/providers/telegram/start",
            requireNotNull(startTransport.request).url,
        )

        val completeTransport = FakeTransport(
            HttpResponse(
                200,
                "{\"session_token\":\"access\",\"refresh_token\":\"refresh\",\"scopes\":[\"game:read\"]}",
            ),
        )
        val complete = AuthApi("https://example.test", completeTransport).completeBrowserProvider(
            provider = "telegram",
            code = "authorization-code",
            state = "abcdefghijklmnopqrstuvwxyz1234567890",
            codeVerifier = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890-._~",
            deviceId = null,
        )
        assertTrue(complete is AuthApi.Result.Success)
        val request = requireNotNull(completeTransport.request)
        assertEquals("https://example.test/v1/auth/providers/telegram/complete", request.url)
        val body = String(requireNotNull(request.body))
        assertTrue(body.contains("authorization-code"))
        assertTrue(body.contains("code_verifier"))
    }

}
