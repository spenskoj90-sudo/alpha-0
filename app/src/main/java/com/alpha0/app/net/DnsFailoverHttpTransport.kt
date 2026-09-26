package com.alpha0.app.net

import java.io.IOException
import java.net.UnknownHostException
import java.util.UUID

/**
 * Alternate-ingress transport for the canonical Core origin.
 *
 * Safety rules:
 * - UnknownHostException may fail over once for any request because DNS resolution
 *   failed before a connection could be established.
 * - Other I/O failures may fail over only for GET because reads are replay-safe.
 * - Non-idempotent writes are never replayed after a generic I/O/timeout failure,
 *   because the primary outcome may be ambiguous.
 */
class DnsFailoverHttpTransport(
    primaryBaseUrl: String,
    fallbackBaseUrl: String?,
    private val delegate: HttpTransport,
    private val requestIdFactory: () -> String = { UUID.randomUUID().toString() },
    private val onDnsFailover: (primaryOrigin: String, fallbackOrigin: String) -> Unit = { _, _ -> },
    private val onSafeReadFailover: (
        reason: String,
        primaryOrigin: String,
        fallbackOrigin: String,
    ) -> Unit = { _, _, _ -> },
) : HttpTransport {
    private val primary = normalize(primaryBaseUrl)
    private val fallback = fallbackBaseUrl?.trim()?.takeIf { it.isNotEmpty() }?.let(::normalize)

    init {
        require(primary.startsWith("https://") || primary.startsWith("http://")) {
            "primary Core URL must use HTTP(S)"
        }
        if (fallback != null) {
            require(fallback.startsWith("https://") || fallback.startsWith("http://")) {
                "fallback Core URL must use HTTP(S)"
            }
            require(fallback != primary) { "fallback Core URL must differ from primary" }
        }
    }

    override fun execute(request: HttpRequest): HttpResponse {
        val retryUrl = rewriteToFallback(request.url)
        if (retryUrl == null) return delegate.execute(request)

        val correlated = withRequestId(request)
        return try {
            delegate.execute(correlated)
        } catch (error: UnknownHostException) {
            onDnsFailover(primary, fallback!!)
            delegate.execute(correlated.copy(url = retryUrl))
        } catch (error: IOException) {
            if (request.method != HttpMethod.GET) throw error
            onSafeReadFailover(error.javaClass.simpleName.take(96), primary, fallback!!)
            delegate.execute(correlated.copy(url = retryUrl))
        }
    }

    private fun rewriteToFallback(url: String): String? {
        val alternate = fallback ?: return null
        val suffix = when {
            url == primary -> ""
            url.startsWith("$primary/") -> url.removePrefix(primary)
            else -> return null
        }
        return "$alternate$suffix"
    }

    private fun withRequestId(request: HttpRequest): HttpRequest {
        if (request.headers.keys.any { it.equals("X-Request-ID", ignoreCase = true) }) return request
        return request.copy(headers = LinkedHashMap(request.headers).apply {
            put("X-Request-ID", requestIdFactory())
        })
    }

    private fun normalize(value: String): String = value.trim().trimEnd('/')
}
