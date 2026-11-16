package com.alpha0.app.auth

import java.net.URLEncoder
import java.security.MessageDigest
import java.util.Base64
import org.junit.Assert.*
import org.junit.Test

class BrowserAuthPolicyTest {
    private val state = "s".repeat(43)
    private val verifier = "v".repeat(64)
    private val challenge = Base64.getUrlEncoder().withoutPadding().encodeToString(MessageDigest.getInstance("SHA-256").digest(verifier.toByteArray()))
    private fun url(provider: String): String {
        val host = if (provider == "telegram") "https://oauth.telegram.org/auth" else "https://id.vk.ru/authorize"
        val redirect = if (provider == "telegram") "com.alpha0.app.auth://callback" else "vk123://vk.ru/blank.html"
        val scope = if (provider == "telegram") "openid profile" else "email"
        val encode = { x: String -> URLEncoder.encode(x, "UTF-8") }
        val fields = mutableMapOf("client_id" to "123", "redirect_uri" to redirect, "response_type" to "code", "scope" to scope, "state" to state, "code_challenge" to challenge, "code_challenge_method" to "S256")
        if (provider == "telegram") fields["nonce"] = state
        return host + "?" + fields.entries.joinToString("&") { encode(it.key) + "=" + encode(it.value) }
    }
    @Test fun disabledAndMismatchedPinsDoNotEnableProvider() {
        assertTrue(browserClientIdAllowed(null, null))
        assertFalse(browserClientIdAllowed("0", "0"))
        assertFalse(browserClientIdAllowed("123", null))
        assertFalse(browserClientIdAllowed("123", "456"))
        assertTrue(browserClientIdAllowed("123", "123"))
    }
    @Test fun providerFlowsAcceptOnlyPinnedIdentityAndBoundPkce() {
        for (provider in listOf("telegram", "vk")) {
            val redirect = if (provider == "telegram") "com.alpha0.app.auth://callback" else "vk123://vk.ru/blank.html"
            val good = url(provider)
            fun check(value: String, pin: String = "123", actualState: String = state, actualVerifier: String = verifier) =
                trustedBrowserAuthorization(value, provider, pin, redirect, actualState, actualVerifier)
            assertTrue(check(good))
            assertFalse(check(good, pin = "456"))
            assertFalse(check(good, pin = "0"))
            assertFalse(check(good, actualState = "x".repeat(43)))
            assertFalse(check(good, actualVerifier = "x".repeat(64)))
            assertFalse(check(good + "&client_id=123"))
            assertFalse(check(good + "&%63lient_id=123"))
            assertFalse(check(good.replace("client_id=123", "client_id=456")))
            assertFalse(check(good + "&redirect_uri=evil"))
            assertFalse(check(good.replace("https://", "http://")))
            assertFalse(check(good.replace("code_challenge_method=S256", "code_challenge_method=plain")))
            assertFalse(check(good + "#fragment"))
        }
    }
}
