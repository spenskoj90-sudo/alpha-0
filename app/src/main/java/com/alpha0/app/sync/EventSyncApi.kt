package com.alpha0.app.sync

import com.alpha0.app.net.HttpMethod
import com.alpha0.app.net.HttpRequest
import com.alpha0.app.net.HttpTransport
import com.alpha0.app.net.UrlConnectionHttpTransport
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.security.MessageDigest
import java.util.UUID

interface EventBatchClient {
    fun sendBatch(accessToken: String, events: List<OfflineEventQueue.Item>): EventSyncApi.Result
}

class EventSyncApi(
    private val baseUrl: String,
    private val transport: HttpTransport = UrlConnectionHttpTransport(),
) : EventBatchClient {
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

        return try {
            val response = transport.execute(
                HttpRequest(
                    method = HttpMethod.POST,
                    url = "$normalizedBase/v1/events:batch",
                    headers = mapOf(
                        "Authorization" to "Bearer $accessToken",
                        "Content-Type" to "application/json",
                        "Accept" to "application/json",
                        "X-Request-ID" to UUID.randomUUID().toString(),
                        "Idempotency-Key" to batchIdempotencyKey(events),
                    ),
                    body = payload.toByteArray(Charsets.UTF_8),
                )
            )
            val json = runCatching { JSONObject(response.body) }.getOrNull()
            if (response.status !in 200..299 || json == null) {
                return Result.Failure(json?.optString("code")?.takeIf { it.isNotBlank() } ?: "HTTP_${response.status}")
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
        }
    }

    companion object {
        internal fun batchIdempotencyKey(events: List<OfflineEventQueue.Item>): String {
            require(events.isNotEmpty()) { "events must not be empty" }
            val canonical = events.joinToString(separator = "\n") { it.eventId }
            val digest = MessageDigest.getInstance("SHA-256")
                .digest(canonical.toByteArray(Charsets.UTF_8))
            return digest.joinToString(separator = "") { byte -> "%02x".format(byte.toInt() and 0xff) }
        }
    }
}
