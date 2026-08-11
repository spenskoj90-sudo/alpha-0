package com.alpha0.app.sync

import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

class OfflineEventQueue(private val maxItems: Int = 1000) {
    data class Item(
        val eventId: String,
        val deviceId: String,
        val type: String,
        val schemaVersion: Int,
        val occurredAt: Long,
        val sequence: Long,
        val payload: JSONObject
    )

    private val queue = ArrayDeque<Item>()

    @Synchronized
    fun enqueue(deviceId: String, type: String, schemaVersion: Int, occurredAt: Long, sequence: Long, payload: JSONObject): String {
        require(queue.size < maxItems) { "Offline queue capacity reached" }
        val id = UUID.randomUUID().toString()
        queue.addLast(Item(id, deviceId, type, schemaVersion, occurredAt, sequence, payload))
        return id
    }

    @Synchronized
    fun peekBatch(limit: Int = 100): List<Item> = queue.take(limit)

    @Synchronized
    fun acknowledge(eventIds: Set<String>) {
        while (queue.isNotEmpty() && queue.first().eventId in eventIds) queue.removeFirst()
        if (eventIds.isNotEmpty()) queue.removeAll { it.eventId in eventIds }
    }

    @Synchronized
    fun size(): Int = queue.size

    fun toJson(): JSONArray = JSONArray().apply {
        synchronized(this@OfflineEventQueue) {
            queue.forEach { item ->
                put(JSONObject().apply {
                    put("event_id", item.eventId)
                    put("device_id", item.deviceId)
                    put("type", item.type)
                    put("schema_version", item.schemaVersion)
                    put("occurred_at", item.occurredAt)
                    put("sequence", item.sequence)
                    put("payload", item.payload)
                })
            }
        }
    }
}
