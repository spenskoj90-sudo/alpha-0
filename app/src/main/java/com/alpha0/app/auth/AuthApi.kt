package com.alpha0.app.auth

import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

class AuthApi(private val baseUrl: String) {
    data class Session(
        val accessToken: String,
        val refreshToken: String,
        val scopes: List<String>,
    )

    sealed interface Result {
        data class Success(val session: Session) : Result
        data class Failure(val message: String) : Result
    }

    fun register(email: String, password: String): Result = request("/v1/auth/register", email, password)

    fun login(email: String, password: String): Result = request("/v1/auth/login", email, password)

    private fun request(path: String, email: String, password: String): Result {
        val normalizedBase = baseUrl.trim().trimEnd('/')
        val connection = (URL("$normalizedBase$path").openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 10_000
            readTimeout = 15_000
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
            setRequestProperty("Accept", "application/json")
        }
        return try {
            val payload = JSONObject().apply {
                put("email", email.trim().lowercase())
                put("password", password)
            }.toString()
            connection.outputStream.use { it.write(payload.toByteArray(Charsets.UTF_8)) }
            val body = (if (connection.responseCode in 200..299) connection.inputStream else connection.errorStream)
                ?.bufferedReader()?.use { it.readText() }.orEmpty()
            val json = runCatching { JSONObject(body) }.getOrNull()
            if (connection.responseCode in 200..299 && json != null) {
                val scopesJson = json.optJSONArray("scopes")
                val scopes = buildList {
                    if (scopesJson != null) for (i in 0 until scopesJson.length()) add(scopesJson.getString(i))
                }
                val access = json.optString("session_token")
                val refresh = json.optString("refresh_token")
                if (access.isBlank() || refresh.isBlank()) {
                    Result.Failure("AUTH_RESPONSE_INVALID")
                } else {
                    Result.Success(Session(access, refresh, scopes))
                }
            } else {
                Result.Failure(json?.optString("code")?.takeIf { it.isNotBlank() } ?: "HTTP_${connection.responseCode}")
            }
        } catch (e: IOException) {
            Result.Failure("NETWORK_ERROR: ${e.javaClass.simpleName}: ${e.message}")
        } catch (e: Exception) {
            Result.Failure("UNEXPECTED_ERROR: ${e.javaClass.simpleName}: ${e.message}")
        } finally {
            connection.disconnect()
        }
    }
}
