package com.alpha0.app.sync

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test

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
}
