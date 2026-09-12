package com.alpha0.app.sync

class EventSyncCoordinator(
    private val queue: OfflineEventQueue,
    private val api: EventBatchClient,
) {
    data class FlushResult(
        val attempted: Int,
        val accepted: Int,
        val duplicates: Int,
        val failureCode: String? = null,
    )

    fun flush(accessToken: String, limit: Int = 100): FlushResult {
        require(accessToken.isNotBlank()) { "accessToken must not be blank" }
        require(limit in 1..100) { "limit must be between 1 and 100" }
        val batch = queue.peekBatch(limit)
        if (batch.isEmpty()) return FlushResult(0, 0, 0)

        return when (val result = api.sendBatch(accessToken, batch)) {
            is EventSyncApi.Result.Success -> {
                queue.acknowledge(batch.map { it.eventId }.toSet())
                FlushResult(batch.size, result.value.accepted, result.value.duplicates)
            }
            is EventSyncApi.Result.Failure -> FlushResult(batch.size, 0, 0, result.code)
        }
    }
}
