package com.alpha0.app.net

import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URL

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

/**
 * Shared Android/JVM HTTP boundary.
 *
 * Security/resource invariants:
 * - platform TLS/hostname verification is retained for HTTPS;
 * - only HTTP(S) URLs are accepted (HTTP remains necessary for local loopback development);
 * - redirects are not followed implicitly, avoiding cross-origin credential forwarding;
 * - connect/read timeouts are bounded;
 * - response bodies are bounded before conversion to text;
 * - no automatic retry is performed here; caller-specific idempotency policy remains authoritative.
 */
class UrlConnectionHttpTransport(
    private val connectTimeoutMs: Int = 10_000,
    private val readTimeoutMs: Int = 15_000,
    private val maxResponseBytes: Int = 1_048_576,
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
            request.headers.forEach { (name, value) ->
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
