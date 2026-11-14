package com.alpha0.app.auth

import java.net.URI
import java.net.URLDecoder

/**
 * Strict inbound Telegram/VK browser redirect parsing before consuming a
 * Keystore-encrypted pending PKCE state. A well-formed redirect is NOT proof of
 * provider identity or of authentication: the pending state and Core must still
 * authenticate the returned code. All channels share this fail-closed boundary.
 */
internal object StrictInboundBrowserCallback {
    sealed interface Parsed {
        val state: String
        val provider: String

        data class Code(
            override val state: String,
            override val provider: String,
            val code: String,
            val deviceId: String?,
        ) : Parsed

        data class ProviderError(
            override val state: String,
            override val provider: String,
            val error: String,
        ) : Parsed
    }

    private val allowedNames = setOf("state", "code", "device_id", "error", "error_description", "error_uri")
    private val statePattern = Regex("[A-Za-z0-9_-]{32,256}")

    fun parseAny(raw: String, telegramRedirect: String, vkRedirect: String): Parsed? =
        parse(raw, "telegram", telegramRedirect, vkRedirect)
            ?: parse(raw, "vk", telegramRedirect, vkRedirect)

    fun parse(raw: String, provider: String, telegramRedirect: String, vkRedirect: String): Parsed? = try {
        require(raw.length in 1..8192 && provider in setOf("telegram", "vk"))
        val expected = URI(if (provider == "telegram") telegramRedirect else vkRedirect)
        val actual = URI(raw)
        require(!actual.isOpaque && !expected.isOpaque)
        require(actual.scheme == expected.scheme && actual.rawAuthority == expected.rawAuthority &&
            actual.rawPath.orEmpty() == expected.rawPath.orEmpty() && actual.rawFragment == null)
        require(actual.rawUserInfo == null && actual.port == -1)
        require(expected.rawUserInfo == null && expected.port == -1 &&
            expected.rawQuery == null && expected.rawFragment == null)
        val query = requireNotNull(actual.rawQuery)
        require(query.isNotEmpty())
        val fields = mutableMapOf<String, String>()
        for (part in query.split('&')) {
            val separator = part.indexOf('=')
            require(separator > 0)
            val name = part.substring(0, separator)
            require(name in allowedNames && name !in fields)
            val value = URLDecoder.decode(part.substring(separator + 1), Charsets.UTF_8.name())
            require(value.length <= 4096 && '\uFFFD' !in value &&
                value.none { it.code < 32 || it.code == 127 })
            fields[name] = value
        }
        val state = requireNotNull(fields["state"])
        require(statePattern.matches(state))
        val code = fields["code"]
        val error = fields["error"]
        require((code != null) != (error != null))
        if (code != null) {
            require(fields.keys.all { it in setOf("state", "code", "device_id") })
            require(code.isNotBlank() && code.length <= 4096)
            val deviceId = fields["device_id"]
            require(deviceId == null || (deviceId.isNotBlank() && deviceId.length <= 512))
            Parsed.Code(state, provider, code, deviceId)
        } else {
            require(fields.keys.all { it in setOf("state", "error", "error_description", "error_uri") })
            require(!error.isNullOrBlank() && error.length <= 128)
            require((fields["error_description"]?.length ?: 0) <= 512)
            require((fields["error_uri"]?.length ?: 0) <= 2048)
            Parsed.ProviderError(state, provider, error)
        }
    } catch (_: Exception) {
        null
    }
}
