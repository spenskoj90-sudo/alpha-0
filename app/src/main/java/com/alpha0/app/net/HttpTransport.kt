package com.alpha0.app.net

import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID
import org.json.JSONObject

enum class HttpMethod {
    GET,
    POST,
}

data class HttpRequest(
    val method: HttpMethod,
    val url: String,
    val headers: Map<String, String> = emptyMap(),
    val body: ByteArray? = null,
)

data class HttpResponse(
    val status: Int,
    val body: String,
)

interface HttpTransport {
    @Throws(IOException::class)
    fun execute(request: HttpRequest): HttpResponse
}

data class SessionCredentials(
    val accessToken: String,
    val refreshToken: String,
)

/**
 * Authenticated Core transport wrapper.
 *
 * A bearer request is always sent with the latest stored access token. Only an
 * INVALID_SESSION response triggers serialized one-time refresh-token rotation
 * and one retry with the same request/correlation metadata. Invalid refresh state is cleared
 * fail-closed; transient refresh transport failures are not converted into
 * credential deletion.
 */
class SessionRefreshingHttpTransport(
    baseUrl: String,
    private val delegate: HttpTransport,
    private val sessionProvider: () -> SessionCredentials?,
    private val onSessionRefreshed: (SessionCredentials) -> Unit,
    private val onSessionInvalidated: () -> Unit,
    private val requestIdFactory: () -> String = { UUID.randomUUID().toString() },
) : HttpTransport {
    private val normalizedBaseUrl = baseUrl.trim().trimEnd('/')
    private val refreshLock = Any()

    init {
        require(normalizedBaseUrl.startsWith("https://") || normalizedBaseUrl.startsWith("http://")) {
            "Core base URL must use HTTP(S)"
        }
    }

    override fun execute(request: HttpRequest): HttpResponse {
        if (!isCoreRequest(request.url) || bearerHeader(request) == null || isRefreshRequest(request.url)) {
            return delegate.execute(request)
        }

        val correlatedRequest = withRequestId(request)
        val initial = sessionProvider() ?: return delegate.execute(correlatedRequest)
        val first = delegate.execute(withBearer(correlatedRequest, initial.accessToken))
        if (!isSessionAuthenticationFailure(first)) return first

        return synchronized(refreshLock) {
            val latest = sessionProvider() ?: return@synchronized first
            val latestAttempt = if (latest.accessToken != initial.accessToken) {
                delegate.execute(withBearer(correlatedRequest, latest.accessToken))
            } else {
                first
            }
            if (!isSessionAuthenticationFailure(latestAttempt)) return@synchronized latestAttempt

            val refreshed = refreshSession(latest, correlatedRequest) ?: return@synchronized latestAttempt
            val retry = delegate.execute(withBearer(correlatedRequest, refreshed.accessToken))
            if (isSessionAuthenticationFailure(retry)) onSessionInvalidated()
            retry
        }
    }

    private fun refreshSession(
        current: SessionCredentials,
        originalRequest: HttpRequest,
    ): SessionCredentials? {
        val headers = linkedMapOf(
            "Accept" to "application/json",
            "Content-Type" to "application/json",
        )
        originalRequest.headers.entries
            .firstOrNull { it.key.equals("X-Request-ID", ignoreCase = true) }
            ?.value
            ?.let { headers["X-Request-ID"] = it }

        val response = delegate.execute(
            HttpRequest(
                method = HttpMethod.POST,
                url = "$normalizedBaseUrl/v1/sessions/refresh",
                headers = headers,
                body = JSONObject().apply {
                    put("refresh_token", current.refreshToken)
                }.toString().toByteArray(Charsets.UTF_8),
            )
        )

        if (response.status !in 200..299) {
            if (response.status == 401) onSessionInvalidated()
            return null
        }

        val json = runCatching { JSONObject(response.body) }.getOrNull()
        val access = json?.optString("session_token").orEmpty()
        val refresh = json?.optString("refresh_token").orEmpty()
        if (access.isBlank() || refresh.isBlank()) {
            onSessionInvalidated()
            return null
        }

        return SessionCredentials(access, refresh).also(onSessionRefreshed)
    }

    private fun isCoreRequest(url: String): Boolean =
        url == normalizedBaseUrl || url.startsWith("$normalizedBaseUrl/")

    private fun isRefreshRequest(url: String): Boolean =
        url == "$normalizedBaseUrl/v1/sessions/refresh"

    private fun isSessionAuthenticationFailure(response: HttpResponse): Boolean {
        if (response.status != 401) return false
        val json = runCatching { JSONObject(response.body) }.getOrNull() ?: return false
        val code = json.optString("code").takeIf { it.isNotBlank() }
            ?: json.optString("detail").takeIf { it.isNotBlank() }
        return code == "INVALID_SESSION"
    }

    private fun withRequestId(request: HttpRequest): HttpRequest {
        if (request.headers.keys.any { it.equals("X-Request-ID", ignoreCase = true) }) return request
        return request.copy(headers = LinkedHashMap(request.headers).apply {
            put("X-Request-ID", requestIdFactory())
        })
    }

    private fun bearerHeader(request: HttpRequest): String? =
        request.headers.entries
            .firstOrNull { it.key.equals("Authorization", ignoreCase = true) }
            ?.value
            ?.takeIf { it.startsWith("Bearer ") && it.length > "Bearer ".length }

    private fun withBearer(request: HttpRequest, accessToken: String): HttpRequest {
        val headers = LinkedHashMap(request.headers)
        val existing = headers.keys.firstOrNull { it.equals("Authorization", ignoreCase = true) }
        if (existing != null) headers.remove(existing)
        headers["Authorization"] = "Bearer $accessToken"
        return request.copy(headers = headers)
    }
}


/**
 * Shared Android/JVM HTTP boundary.
 *
 * Security/resource invariants:
 * - platform TLS/hostname verification is retained for HTTPS;
 * - only HTTP(S) URLs are accepted (HTTP remains necessary for local loopback development);
 * - redirects are not followed implicitly, avoiding cross-origin credential forwarding;
 * - connect/read timeouts are bounded;
 * - response bodies are bounded before conversion to text;
 * - every request has an X-Request-ID fallback while caller-supplied correlation is preserved;
 * - no automatic retry is performed here; caller-specific idempotency policy remains authoritative.
 */
class UrlConnectionHttpTransport(
    private val connectTimeoutMs: Int = 10_000,
    private val readTimeoutMs: Int = 15_000,
    private val maxResponseBytes: Int = 1_048_576,
    private val requestIdFactory: () -> String = { UUID.randomUUID().toString() },
    private val connectionFactory: (URL) -> HttpURLConnection = { url ->
        (url.openConnection() as? HttpURLConnection)
            ?: throw IOException("unsupported URL connection")
    },
) : HttpTransport {
    init {
        require(connectTimeoutMs > 0) { "connectTimeoutMs must be positive" }
        require(readTimeoutMs > 0) { "readTimeoutMs must be positive" }
        require(maxResponseBytes > 0) { "maxResponseBytes must be positive" }
    }

    override fun execute(request: HttpRequest): HttpResponse {
        val url = URL(request.url)
        val scheme = url.protocol.lowercase()
        if (scheme != "http" && scheme != "https") {
            throw IOException("unsupported URL scheme")
        }

        val connection = connectionFactory(url)
        return try {
            connection.requestMethod = request.method.name
            connection.connectTimeout = connectTimeoutMs
            connection.readTimeout = readTimeoutMs
            connection.instanceFollowRedirects = false
            connection.doInput = true
            val headers = LinkedHashMap(request.headers)
            if (headers.keys.none { it.equals("X-Request-ID", ignoreCase = true) }) {
                headers["X-Request-ID"] = requestIdFactory()
            }
            headers.forEach { (name, value) ->
                validateHeader(name, value)
                connection.setRequestProperty(name, value)
            }
            request.body?.let { body ->
                connection.doOutput = true
                connection.outputStream.use { output -> output.write(body) }
            }

            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            HttpResponse(status = status, body = readBounded(stream))
        } finally {
            connection.disconnect()
        }
    }

    private fun validateHeader(name: String, value: String) {
        if (name.isBlank() || name.any { it == '\r' || it == '\n' } || value.any { it == '\r' || it == '\n' }) {
            throw IOException("invalid HTTP header")
        }
    }

    private fun readBounded(stream: InputStream?): String {
        if (stream == null) return ""
        val output = ByteArrayOutputStream(minOf(maxResponseBytes, 8_192))
        val buffer = ByteArray(8_192)
        var total = 0
        stream.use { input ->
            while (true) {
                val read = input.read(buffer)
                if (read < 0) break
                total += read
                if (total > maxResponseBytes) {
                    throw IOException("HTTP response exceeds configured limit")
                }
                output.write(buffer, 0, read)
            }
        }
        return output.toString(Charsets.UTF_8.name())
    }
}
