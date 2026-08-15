package com.alpha0.app.network

import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL

class SentinelApiClient(private val baseUrl: String) {
    data class Session(
        val accessToken: String,
        val refreshToken: String,
        val expiresAt: String,
        val scopes: List<String>
    )

    class ApiException(val statusCode: Int, val code: String, override val message: String) : Exception(message)

    fun register(email: String, password: String): Session = authenticate("/v1/auth/register", email, password)

    fun login(email: String, password: String): Session = authenticate("/v1/auth/login", email, password)

    private fun authenticate(path: String, email: String, password: String): Session {
        val connection = (URL(baseUrl.trimEnd('/') + path).openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 10_000
            readTimeout = 15_000
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
            setRequestProperty("Accept", "application/json")
        }
        try {
            val body = JSONObject().apply {
                put("email", email.trim())
                put("password", password)
            }.toString()
            connection.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }

            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val response = stream?.use { input ->
                BufferedReader(InputStreamReader(input, Charsets.UTF_8)).use { it.readText() }
            }.orEmpty()
            val json = runCatching { JSONObject(response) }.getOrNull()
            if (status !in 200..299) {
                val code = json?.optString("code").orEmpty().ifBlank { "HTTP_$status" }
                val message = json?.optString("message").orEmpty().ifBlank { "Authentication failed" }
                throw ApiException(status, code, message)
            }

            val parsed = JSONObject(response)
            return Session(
                accessToken = parsed.getString("session_token"),
                refreshToken = parsed.getString("refresh_token"),
                expiresAt = parsed.getString("expires_at"),
                scopes = parsed.optJSONArray("scopes")?.let { array ->
                    List(array.length()) { index -> array.getString(index) }
                } ?: emptyList()
            )
        } finally {
            connection.disconnect()
        }
    }
}
