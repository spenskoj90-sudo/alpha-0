package com.alpha0.app.auth

import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

/** Small injectable HTTP boundary used by the Android authentication API. */
interface AuthHttpTransport {
    @Throws(IOException::class)
    fun postJson(url: String, body: ByteArray): AuthHttpResponse
}

data class AuthHttpResponse(
    val status: Int,
    val body: String,
)

/** JVM/Android implementation; networking remains outside AuthApi. */
class UrlConnectionAuthHttpTransport(
    private val connectTimeoutMs: Int = 10_000,
    private val readTimeoutMs: Int = 15_000,
) : AuthHttpTransport {
    override fun postJson(url: String, body: ByteArray): AuthHttpResponse {
        val connection = (URL(url).openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = connectTimeoutMs
            readTimeout = readTimeoutMs
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
            setRequestProperty("Accept", "application/json")
        }
        return try {
            connection.outputStream.use { it.write(body) }
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val responseBody = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
            AuthHttpResponse(status, responseBody)
        } finally {
            connection.disconnect()
        }
    }
}
