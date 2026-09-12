package com.alpha0.app.sync

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.util.UUID

class OfflineEventQueue(
    private val maxItems: Int = 1000,
    private val persistenceFile: File? = null,
    private val maxBytes: Int = 512_000,
) {
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

    init {
        require(maxItems in 1..10_000) { "maxItems must be between 1 and 10000" }
        require(maxBytes > 0) { "maxBytes must be positive" }
        load()
    }

    @Synchronized
    fun enqueue(deviceId: String, type: String, schemaVersion: Int, occurredAt: Long, sequence: Long, payload: JSONObject): String {
        require(queue.size < maxItems) { "Offline queue capacity reached" }
        val id = UUID.randomUUID().toString()
        val item = Item(id, deviceId, type, schemaVersion, occurredAt, sequence, payload)
        val candidate = JSONArray().apply {
            queue.forEach { put(it.toJson()) }
            put(item.toJson())
        }
        require(candidate.toString().toByteArray(Charsets.UTF_8).size <= maxBytes) {
            "Offline queue byte capacity reached"
        }
        queue.addLast(item)
        persist()
        return id
    }

    @Synchronized
    fun peekBatch(limit: Int = 100): List<Item> = queue.take(limit)

    @Synchronized
    fun maxSequence(): Long? = queue.maxOfOrNull { it.sequence }

    @Synchronized
    fun acknowledge(eventIds: Set<String>) {
        while (queue.isNotEmpty() && queue.first().eventId in eventIds) queue.removeFirst()
        if (eventIds.isNotEmpty()) queue.removeAll { it.eventId in eventIds }
        persist()
    }

    @Synchronized
    fun size(): Int = queue.size

    fun toJson(): JSONArray = JSONArray().apply {
        synchronized(this@OfflineEventQueue) {
            queue.forEach { put(it.toJson()) }
        }
    }

    @Synchronized
    fun clear() {
        queue.clear()
        persist()
    }

    private fun Item.toJson(): JSONObject = JSONObject().apply {
        put("event_id", eventId)
        put("device_id", deviceId)
        put("type", type)
        put("schema_version", schemaVersion)
        put("occurred_at", occurredAt)
        put("sequence", sequence)
        put("payload", payload)
    }

    private fun load() {
        val file = persistenceFile ?: return
        if (!file.isFile) return
        try {
            val array = JSONArray(file.readText(Charsets.UTF_8))
            for (index in 0 until minOf(array.length(), maxItems)) {
                val value = array.optJSONObject(index) ?: continue
                val eventId = value.optString("event_id").takeIf { it.isNotBlank() } ?: continue
                val deviceId = value.optString("device_id").takeIf { it.isNotBlank() } ?: continue
                val type = value.optString("type").takeIf { it.isNotBlank() } ?: continue
                val payload = value.optJSONObject("payload") ?: JSONObject()
                queue.addLast(
                    Item(
                        eventId = eventId,
                        deviceId = deviceId,
                        type = type,
                        schemaVersion = value.optInt("schema_version", 1),
                        occurredAt = value.optLong("occurred_at"),
                        sequence = value.optLong("sequence"),
                        payload = payload,
                    )
                )
            }
        } catch (_: Exception) {
            // Corrupt local state is isolated; the next event starts a clean queue.
            queue.clear()
        }
    }

    private fun persist() {
        val file = persistenceFile ?: return
        val bytes = toJson().toString().toByteArray(Charsets.UTF_8)
        require(bytes.size <= maxBytes) { "Offline queue byte capacity reached" }
        file.parentFile?.mkdirs()
        val temporary = File(file.parentFile ?: file.absoluteFile.parentFile, "${file.name}.tmp")
        FileOutputStream(temporary).use { it.write(bytes); it.fd.sync() }
        check(temporary.renameTo(file)) { "Unable to atomically persist offline queue" }
    }
}
