package com.sentinel.server

import com.sun.net.httpserver.HttpExchange
import java.net.URLDecoder
import java.nio.charset.StandardCharsets
import java.time.Duration
import java.time.Instant
import java.util.concurrent.ConcurrentHashMap

internal const val MAX_BODY_BYTES = 16 * 1024
internal const val MAX_FORM_FIELDS = 16
internal const val MAX_FIELD_VALUE_BYTES = 4096

/** Small in-process guard for Alpha-0. Production deployments should also rate-limit at the gateway. */
internal class SlidingWindowRateLimiter(
    private val maxRequests: Int,
    private val window: Duration,
    private val clock: () -> Instant = Instant::now
) {
    private val buckets = ConcurrentHashMap<String, ArrayDeque<Instant>>()

    init {
        require(maxRequests > 0)
        require(!window.isZero && !window.isNegative)
    }

    fun allow(key: String): Boolean {
        if (key.isBlank()) return false
        val now = clock()
        val cutoff = now.minus(window)
        val queue = buckets.computeIfAbsent(key) { ArrayDeque() }
        synchronized(queue) {
            while (queue.firstOrNull()?.isBefore(cutoff) == true) queue.removeFirst()
            if (queue.size >= maxRequests) return false
            queue.addLast(now)
            return true
        }
    }
}

internal fun clientRateLimitKey(exchange: HttpExchange, fallback: String): String =
    exchange.remoteAddress?.address?.hostAddress?.takeIf { it.isNotBlank() } ?: fallback

internal fun requireFormContentType(exchange: HttpExchange) {
    val contentType = exchange.requestHeaders.getFirst("Content-Type")?.substringBefore(';')?.trim()?.lowercase()
    require(contentType == "application/x-www-form-urlencoded")
}

internal fun readForm(exchange: HttpExchange): Map<String, String> {
    requireFormContentType(exchange)
    val length = exchange.requestHeaders.getFirst("Content-Length")?.toLongOrNull()
    require(length == null || length in 1..MAX_BODY_BYTES)
    val bytes = exchange.requestBody.use { it.readNBytes(MAX_BODY_BYTES + 1) }
    require(bytes.size <= MAX_BODY_BYTES)
    val text = bytes.toString(StandardCharsets.UTF_8)
    if (text.isEmpty()) return emptyMap()
    val result = LinkedHashMap<String, String>()
    val fields = text.split('&')
    require(fields.size <= MAX_FORM_FIELDS)
    for (field in fields) {
        require(field.isNotEmpty())
        val parts = field.split('=', limit = 2)
        require(parts.size == 2)
        val key = URLDecoder.decode(parts[0], StandardCharsets.UTF_8)
        val value = URLDecoder.decode(parts[1], StandardCharsets.UTF_8)
        require(key.isNotBlank() && key.length <= MAX_FIELD_VALUE_BYTES)
        require(value.length <= MAX_FIELD_VALUE_BYTES)
        require(result.putIfAbsent(key, value) == null) // reject duplicate parameters instead of last-one-wins ambiguity
    }
    return result
}

internal fun Map<String, String>.required(name: String): String =
    this[name]?.takeIf { it.isNotBlank() && it.length <= MAX_FIELD_VALUE_BYTES } ?: error("missing field")
