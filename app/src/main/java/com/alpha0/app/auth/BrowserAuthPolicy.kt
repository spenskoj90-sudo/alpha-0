package com.alpha0.app.auth

import java.net.URI
import java.net.URLDecoder
import java.security.MessageDigest
import java.util.Base64

internal fun browserClientIdAllowed(pin: String?, supplied: String?): Boolean =
    if (pin == null) true else pin.matches(Regex("[1-9][0-9]{0,19}")) && pin == supplied

/** Validates the exact signed-feed browser flow before opening a provider. */
internal fun trustedBrowserAuthorization(url: String, provider: String, pin: String,
    redirect: String, state: String, verifier: String): Boolean = try {
    require(url.length <= 8192 && pin.matches(Regex("[1-9][0-9]{0,19}")))
    require(state.matches(Regex("[A-Za-z0-9_-]{32,256}")))
    require(verifier.matches(Regex("[A-Za-z0-9._~-]{43,128}")))
    val endpoint = when (provider) {
        "telegram" -> "https://oauth.telegram.org/auth"
        "vk" -> "https://id.vk.ru/authorize"
        else -> return false
    }
    val uri = URI(url)
    require(uri.scheme == "https" && uri.rawUserInfo == null && uri.rawFragment == null)
    require("${uri.scheme}://${uri.rawAuthority}${uri.rawPath}" == endpoint)
    val query = requireNotNull(uri.rawQuery).split('&')
    val params = mutableMapOf<String, String>()
    for (part in query) {
        val index = part.indexOf('='); require(index > 0)
        val name = URLDecoder.decode(part.substring(0, index), "UTF-8")
        val value = URLDecoder.decode(part.substring(index + 1), "UTF-8")
        require(params.put(name, value) == null)
    }
    val required = mutableSetOf("client_id", "redirect_uri", "response_type", "scope", "state", "code_challenge", "code_challenge_method")
    if (provider == "telegram") required.add("nonce")
    require(params.keys == required)
    val challenge = Base64.getUrlEncoder().withoutPadding().encodeToString(MessageDigest.getInstance("SHA-256").digest(verifier.toByteArray(Charsets.US_ASCII)))
    params["client_id"] == pin && params["redirect_uri"] == redirect && params["state"] == state &&
        params["response_type"] == "code" && params["code_challenge_method"] == "S256" &&
        params["code_challenge"] == challenge &&
        params["scope"] == (if (provider == "telegram") "openid profile" else "email") &&
        (provider != "telegram" || params["nonce"] == state)
} catch (_: Exception) { false }
