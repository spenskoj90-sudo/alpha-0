package com.alpha0.app.game

import com.alpha0.app.sync.OfflineEventQueue
import org.json.JSONObject

interface GameAdapter {
    val gameId: String
    fun start()
    fun stop()
    fun pollFacts(): List<GameFact>
}

data class GameFact(
    val type: String,
    val payload: JSONObject,
    val occurredAtEpochSeconds: Long
)

class GameAdapterCoordinator(
    private val deviceId: String,
    private val queue: OfflineEventQueue,
    private val adapter: GameAdapter
) {
    private var sequence: Long = 0

    fun collect() {
        adapter.pollFacts().forEach { fact ->
            queue.enqueue(
                deviceId = deviceId,
                type = "${adapter.gameId}.${fact.type}",
                schemaVersion = 1,
                occurredAt = fact.occurredAtEpochSeconds,
                sequence = sequence++,
                payload = fact.payload
            )
        }
    }
}
