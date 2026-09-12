package com.alpha0.app.sync

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class EventSyncCoordinatorTest {
    private fun item(sequence: Long) = OfflineEventQueue.Item(
        eventId = "event-$sequence",
        deviceId = "device-1234",
        type = "character.snapshot",
        schemaVersion = 1,
        occurredAt = 1_700_000_000_000,
        sequence = sequence,
        payload = JSONObject().put("hp", 100),
    )

    @Test
    fun successfulFlushAcknowledgesAcceptedAndDuplicateEvents() {
        val queue = OfflineEventQueue(maxItems = 10)
        queue.enqueue(item(0).deviceId, item(0).type, 1, item(0).occurredAt, 0, item(0).payload)
        queue.enqueue(item(1).deviceId, item(1).type, 1, item(1).occurredAt, 1, item(1).payload)
        val client = object : EventBatchClient {
            override fun sendBatch(accessToken: String, events: List<OfflineEventQueue.Item>): EventSyncApi.Result =
                EventSyncApi.Result.Success(EventSyncApi.BatchResult(accepted = 1, duplicates = 1))
        }

        val result = EventSyncCoordinator(queue, client).flush("token")

        assertEquals(2, result.attempted)
        assertEquals(1, result.accepted)
        assertEquals(1, result.duplicates)
        assertEquals(0, queue.size())
    }

    @Test
    fun failedFlushKeepsEventsForRetry() {
        val queue = OfflineEventQueue(maxItems = 10)
        queue.enqueue(item(0).deviceId, item(0).type, 1, item(0).occurredAt, 0, item(0).payload)
        val client = object : EventBatchClient {
            override fun sendBatch(accessToken: String, events: List<OfflineEventQueue.Item>): EventSyncApi.Result =
                EventSyncApi.Result.Failure("NETWORK_ERROR")
        }

        val result = EventSyncCoordinator(queue, client).flush("token")

        assertEquals(1, result.attempted)
        assertEquals("NETWORK_ERROR", result.failureCode)
        assertEquals(1, queue.size())
        assertNotNull(queue.peekBatch().firstOrNull())
    }

    @Test
    fun emptyQueueDoesNotCallClient() {
        val queue = OfflineEventQueue(maxItems = 10)
        var called = false
        val client = object : EventBatchClient {
            override fun sendBatch(accessToken: String, events: List<OfflineEventQueue.Item>): EventSyncApi.Result {
                called = true
                return EventSyncApi.Result.Failure("UNEXPECTED")
            }
        }

        val result = EventSyncCoordinator(queue, client).flush("token")

        assertEquals(0, result.attempted)
        assertTrue(!called)
    }
}
