package com.alpha0.app.sync

import java.nio.file.Files
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class OfflineEventQueuePersistenceTest {
    @Test
    fun queueRestoresEventsAfterReopenAndAcknowledgesDurably() {
        val directory = Files.createTempDirectory("sentinel-queue").toFile()
        val file = directory.resolve("events.json")
        val first = OfflineEventQueue(maxItems = 10, persistenceFile = file)
        val eventId = first.enqueue("device-1234", "character.snapshot", 1, 1_700_000_000_000, 7, JSONObject().put("hp", 100))

        val reopened = OfflineEventQueue(maxItems = 10, persistenceFile = file)
        assertEquals(1, reopened.size())
        assertEquals(eventId, reopened.peekBatch().single().eventId)
        reopened.acknowledge(setOf(eventId))

        val afterAck = OfflineEventQueue(maxItems = 10, persistenceFile = file)
        assertEquals(0, afterAck.size())
        assertTrue(file.isFile)
    }

    @Test
    fun byteBoundPreventsOversizedDurableQueue() {
        val directory = Files.createTempDirectory("sentinel-queue-limit").toFile()
        val file = directory.resolve("events.json")
        val queue = OfflineEventQueue(maxItems = 10, persistenceFile = file, maxBytes = 256)

        try {
            queue.enqueue("device-1234", "character.snapshot", 1, 1_700_000_000_000, 1, JSONObject().put("blob", "x".repeat(500)))
            throw AssertionError("expected byte bound")
        } catch (error: IllegalArgumentException) {
            assertTrue(error.message!!.contains("byte capacity"))
        }
        assertEquals(0, queue.size())
    }
}

