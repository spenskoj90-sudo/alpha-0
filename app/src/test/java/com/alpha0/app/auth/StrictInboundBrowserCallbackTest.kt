package com.alpha0.app.auth

import org.junit.Assert.*
import org.junit.Test

/** Local parser contract; real provider redirect and Android Keystore acceptance remain separate. */
class StrictInboundBrowserCallbackTest {
    private val state = "a".repeat(43)
    private val telegram = "com.alpha0.app.auth://callback"
    private val vk = "vk123://vk.ru/blank.html"

    private fun parse(raw: String) = StrictInboundBrowserCallback.parseAny(raw, telegram, vk)
    private fun good(provider: String) = (if (provider == "telegram") telegram else vk) +
        "?state=$state&code=A%2BB%2Ftest"

    @Test fun exactSuccessPreservesProviderAndDecodedCode() {
        for (provider in listOf("telegram", "vk")) {
            val code = parse(good(provider)) as StrictInboundBrowserCallback.Parsed.Code
            assertEquals(provider, code.provider)
            assertEquals(state, code.state)
            assertEquals("A+B/test", code.code)
            assertNull(code.deviceId)
            val withDevice = parse(good(provider) + "&device_id=device-1") as StrictInboundBrowserCallback.Parsed.Code
            assertEquals("device-1", withDevice.deviceId)
        }
    }

    @Test fun validProviderCancellationIsNotTreatedAsAnAuthorizationCode() {
        for (provider in listOf("telegram", "vk")) {
            val base = if (provider == "telegram") telegram else vk
            val error = parse("$base?state=$state&error=access_denied&error_description=User+cancelled")
            assertTrue(error is StrictInboundBrowserCallback.Parsed.ProviderError)
            assertEquals("access_denied", (error as StrictInboundBrowserCallback.Parsed.ProviderError).error)
            assertNull(parse("$base?state=$state&error=access_denied&code=forged"))
            assertNull(parse("$base?state=$state&error=access_denied&device_id=forged"))
        }
    }

    @Test fun malformedDuplicatedOrCrossOriginCallbacksAreRejected() {
        for (provider in listOf("telegram", "vk")) {
            val base = good(provider)
            val expected = if (provider == "telegram") telegram else vk
            val malformed = listOf(
                base + "&state=$state", base + "&code=other", base + "&%73tate=$state",
                base + "&client_id=other", base + "&redirect_uri=https%3A%2F%2Fevil.invalid",
                base + "&extra=1", base + "&", base + "#fragment",
                base.replace("?", "/extra?"), base.replace("?", ":443?"),
                base.replace("?", "@evil.invalid?"), base.replace("?", ";param?"),
                base.replace("state=$state", "state=short"),
                base.replace("state=$state", "state="),
                base.replace("code=A%2BB%2Ftest", "code="),
                base.replace("code=A%2BB%2Ftest", "code=%00"),
                base.replace("code=A%2BB%2Ftest", "code=%FF"),
                base.replace("code=A%2BB%2Ftest", "code=%G1"),
                base + "&device_id=", base + "&device_id=" + "x".repeat(513),
                base + "&error=access_denied",
                "$expected?state=$state", "$expected?code=valid",
            )
            malformed.forEach { assertNull("$provider: $it", parse(it)) }
        }
        assertNull(StrictInboundBrowserCallback.parse(good("telegram"), "vk", telegram, vk))
        assertNull(StrictInboundBrowserCallback.parse(good("vk"), "telegram", telegram, vk))
    }

    @Test fun boundedRepeatedRejectionDoesNotPoisonParser() {
        val valid = good("telegram")
        repeat(1200) { index ->
            val malformed = when (index % 4) {
                0 -> valid + "&state=$state"
                1 -> valid + "#$index"
                2 -> valid + "&code=$index"
                else -> valid + "&unknown=$index"
            }
            assertNull(parse(malformed))
        }
        assertTrue(parse(valid) is StrictInboundBrowserCallback.Parsed.Code)
    }
}
