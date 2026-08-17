package com.alpha0.app.auth

import android.util.Log
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
        val url = "$normalizedBase$path"
        val connection = (URL(url).openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 10_000
            readTimeout = 15_000
            doOutput = true
            setFixedLengthStreamingMode(
                JSONObject().apply {
                    put("email", email.trim().lowercase())
                    put("password", password)
                }.toString().toByteArray(Charsets.UTF_8).size.toLong(),
            )
            setRequestProperty("Content-Type", "application/json; charset=utf-8")
            setRequestProperty("Accept", "application/json")
            // Avoid stale keep-alive sockets while diagnosing the local Android/Termux transport.
            setRequestProperty("Connection", "close")
            useCaches = false
        }

        return try {
            val payload = JSONObject().apply {
                put("email", email.trim().lowercase())
                put("password", password)
            }.toString().toByteArray(Charsets.UTF_8)
            connection.outputStream.use { it.write(payload) }

            val responseCode = connection.responseCode
            val responseStream = if (responseCode in 200..299) {
                connection.inputStream
            } else {
                connection.errorStream
            }
            val body = responseStream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            val json = runCatching { JSONObject(body) }.getOrNull()

            if (responseCode in 200..299 && json != null) {
                val scopesJson = json.optJSONArray("scopes")
                val scopes = buildList {
                    if (scopesJson != null) {
                        for (i in 0 until scopesJson.length()) {
                            add(scopesJson.getString(i))
                        }
                    }
                }
                val access = json.optString("session_token")
                val refresh = json.optString("refresh_token")
                if (access.isBlank() || refresh.isBlank()) {
                    Result.Failure("AUTH_RESPONSE_INVALID")
                } else {
                    Result.Success(Session(access, refresh, scopes))
                }
            } else {
                Result.Failure(
                    json?.optString("code")?.takeIf { it.isNotBlank() }
                        ?: "HTTP_$responseCode",
                )
            }
        } catch (exception: IOException) {
            Log.w(TAG, "HTTP transport failure for $url: ${exception.javaClass.simpleName}", exception)
            Result.Failure("NETWORK_ERROR")
        } catch (exception: RuntimeException) {
            Log.w(TAG, "HTTP response parsing failure for $url: ${exception.javaClass.simpleName}", exception)
            Result.Failure("NETWORK_RESPONSE_INVALID")
        } finally {
            connection.disconnect()
        }
    }

    private companion object {
        const val TAG = "SENTINEL_AUTH"
    }
}
