package com.alpha0.app.sync

import com.alpha0.app.net.HttpMethod
import com.alpha0.app.net.HttpRequest
import com.alpha0.app.net.HttpResponse
import com.alpha0.app.net.HttpTransport
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.UUID

class EventSyncApiTest {
    private fun event(id: String, sequence: Long) = OfflineEventQueue.Item(
        eventId = id,
        deviceId = "device-1234",
        type = "demo.event",
        schemaVersion = 1,
        occurredAt = 1_700_000_000L + sequence,
        sequence = sequence,
        payload = JSONObject().put("sequence", sequence)
    )

    @Test
    fun idempotencyKeyIsStableForSameOrderedBatch() {
        val batch = listOf(event("event-a", 1), event("event-b", 2))

        val first = EventSyncApi.batchIdempotencyKey(batch)
        val second = EventSyncApi.batchIdempotencyKey(batch)

        assertEquals(first, second)
        assertEquals(64, first.length)
    }

    @Test
    fun idempotencyKeyChangesWhenBatchMembershipOrOrderChanges() {
        val first = EventSyncApi.batchIdempotencyKey(
            listOf(event("event-a", 1), event("event-b", 2))
        )
        val reordered = EventSyncApi.batchIdempotencyKey(
            listOf(event("event-b", 2), event("event-a", 1))
        )
        val changed = EventSyncApi.batchIdempotencyKey(
            listOf(event("event-a", 1), event("event-c", 3))
        )

        assertNotEquals(first, reordered)
        assertNotEquals(first, changed)
    }

    @Test
    fun sendBatchUsesSharedTransportAndPreservesRequestIdentity() {
        var captured: HttpRequest? = null
        val transport = object : HttpTransport {
            override fun execute(request: HttpRequest): HttpResponse {
                captured = request
                return HttpResponse(200, "{\"accepted\":1,\"duplicates\":0}")
            }
        }
        val batch = listOf(event("event-a", 1))

        val result = EventSyncApi("https://example.test/", transport).sendBatch("access", batch)

        assertTrue(result is EventSyncApi.Result.Success)
        val request = requireNotNull(captured)
        assertEquals(HttpMethod.POST, request.method)
        assertEquals("https://example.test/v1/events:batch", request.url)
        assertEquals("Bearer access", request.headers["Authorization"])
        assertEquals(EventSyncApi.batchIdempotencyKey(batch), request.headers["Idempotency-Key"])
        UUID.fromString(requireNotNull(request.headers["X-Request-ID"]))
        assertTrue(String(requireNotNull(request.body)).contains("event-a"))
    }
}
