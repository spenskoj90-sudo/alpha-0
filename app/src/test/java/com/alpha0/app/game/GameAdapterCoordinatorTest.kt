package com.alpha0.app.game

import com.alpha0.app.sync.EventSyncApi
import com.alpha0.app.sync.EventSyncCoordinator
import com.alpha0.app.sync.EventBatchClient
import com.alpha0.app.sync.OfflineEventQueue
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

class GameAdapterCoordinatorTest {
    @Test
    fun collectAndFlushSendsQueuedGameFactsAndAcknowledgesThem() {
        val queue = OfflineEventQueue(maxItems = 10)
        val adapter = object : GameAdapter {
            override val gameId = "demo"
            override fun start() = Unit
            override fun stop() = Unit
            override fun pollFacts() = listOf(
                GameFact("character.snapshot", JSONObject().put("hp", 100), 1_700_000_000)
            )
        }
        var received: List<OfflineEventQueue.Item>? = null
        val client = object : EventBatchClient {
            override fun sendBatch(accessToken: String, events: List<OfflineEventQueue.Item>): EventSyncApi.Result {
                received = events
                return EventSyncApi.Result.Success(EventSyncApi.BatchResult(1, 0))
            }
        }

        val result = GameAdapterCoordinator("device-1234", queue, adapter)
            .collectAndFlush("token", EventSyncCoordinator(queue, client))

        assertEquals(1, result.attempted)
        assertEquals(1, result.accepted)
        assertEquals(0, queue.size())
        assertNotNull(received)
        assertEquals("demo.character.snapshot", received!!.single().type)
        assertEquals(0L, received!!.single().sequence)
    }

    @Test
    fun sequenceRecoveryUsesEntireQueueNotOnlyFirstBatch() {
        val queue = OfflineEventQueue(maxItems = 200)
        repeat(101) { index ->
            queue.enqueue(
                deviceId = "device-1234",
                type = "demo.seed",
                schemaVersion = 1,
                occurredAt = 1_700_000_000L + index,
                sequence = index.toLong(),
                payload = JSONObject().put("index", index)
            )
        }
        val adapter = object : GameAdapter {
            override val gameId = "demo"
            override fun start() = Unit
            override fun stop() = Unit
            override fun pollFacts() = listOf(
                GameFact("character.snapshot", JSONObject().put("hp", 100), 1_700_000_200)
            )
        }

        GameAdapterCoordinator("device-1234", queue, adapter).collect()

        assertEquals(102, queue.size())
        assertEquals(101L, queue.maxSequence())
    }
}
