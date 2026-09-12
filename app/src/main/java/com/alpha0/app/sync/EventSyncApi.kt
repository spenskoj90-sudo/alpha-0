package com.alpha0.app.sync

import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID

interface EventBatchClient {
    fun sendBatch(accessToken: String, events: List<OfflineEventQueue.Item>): EventSyncApi.Result
}

class EventSyncApi(private val baseUrl: String) : EventBatchClient {
    data class BatchResult(
        val accepted: Int,
        val duplicates: Int,
    )

    sealed interface Result {
        data class Success(val value: BatchResult) : Result
        data class Failure(val code: String) : Result
    }

    override fun sendBatch(accessToken: String, events: List<OfflineEventQueue.Item>): Result {
        require(accessToken.isNotBlank()) { "accessToken must not be blank" }
        require(events.isNotEmpty()) { "events must not be empty" }
        require(events.size <= 100) { "events must contain at most 100 items" }

        val normalizedBase = baseUrl.trim().trimEnd('/')
        val connection = (URL("$normalizedBase/v1/events:batch").openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 10_000
            readTimeout = 15_000
            doOutput = true
            setRequestProperty("Authorization", "Bearer $accessToken")
            setRequestProperty("Content-Type", "application/json")
            setRequestProperty("Accept", "application/json")
            setRequestProperty("X-Request-ID", UUID.randomUUID().toString())
            setRequestProperty("Idempotency-Key", UUID.randomUUID().toString())
        }

        return try {
            val payload = JSONObject().apply {
                put("events", JSONArray().apply {
                    events.forEach { item ->
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
                })
            }.toString()
            connection.outputStream.use { it.write(payload.toByteArray(Charsets.UTF_8)) }
            val status = connection.responseCode
            val body = (if (status in 200..299) connection.inputStream else connection.errorStream)
                ?.bufferedReader()?.use { it.readText() }.orEmpty()
            val json = runCatching { JSONObject(body) }.getOrNull()
            if (status !in 200..299 || json == null) {
                return Result.Failure(json?.optString("code")?.takeIf { it.isNotBlank() } ?: "HTTP_$status")
            }
            val accepted = json.optInt("accepted", -1)
            val duplicates = json.optInt("duplicates", -1)
            if (accepted < 0 || duplicates < 0 || accepted + duplicates != events.size) {
                return Result.Failure("INVALID_BATCH_RESPONSE")
            }
            Result.Success(BatchResult(accepted, duplicates))
        } catch (_: IOException) {
            Result.Failure("NETWORK_ERROR")
        } catch (_: Exception) {
            Result.Failure("UNEXPECTED_ERROR")
        } finally {
            connection.disconnect()
        }
    }
}
