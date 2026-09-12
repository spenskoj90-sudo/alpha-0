package com.alpha0.app.device

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Test

class DeviceApiTest {
    @Test
    fun canonicalProofPayloadMatchesCoreCanonicalJsonContract() {
        val payload = DeviceApi.canonicalProofPayload(
            challenge = "challenge-value",
            timestamp = 1_700_000_000L,
            requestId = "request-id",
        )

        assertEquals(
            "{\"challenge\":\"challenge-value\",\"request_id\":\"request-id\",\"timestamp\":1700000000}",
            payload.toString(Charsets.UTF_8),
        )
    }

    @Test
    fun canonicalProofPayloadEscapesStringValuesDeterministically() {
        val first = DeviceApi.canonicalProofPayload(
            challenge = "challenge\\\"value",
            timestamp = 42L,
            requestId = "request\\id",
        )
        val second = DeviceApi.canonicalProofPayload(
            challenge = "challenge\\\"value",
            timestamp = 42L,
            requestId = "request\\id",
        )

        assertArrayEquals(first, second)
    }
}
