package com.alpha0.app.auth

import android.content.Context
import com.alpha0.app.diagnostics.DiagnosticLogger
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

interface RefreshClient {
    fun refresh(refreshToken: String): AuthApi.Result
}

class AuthApi(private val baseUrl: String) : RefreshClient {
    data class Session(
        val accessToken: String,
        val refreshToken: String,
        val scopes: List<String>,
    )

    sealed interface Result {
        data class Success(val session: Session) : Result
        data class Failure(val message: String) : Result
    }

    @Volatile
    private var diag: DiagnosticLogger? = null

    fun attachDiagnostics(context: Context) {
        diag = DiagnosticLogger.get(context)
    }

    fun register(email: String, password: String): Result = requestCredentials("/v1/auth/register", email, password, "REGISTER")

    fun login(email: String, password: String): Result = requestCredentials("/v1/auth/login", email, password, "LOGIN")

    override fun refresh(refreshToken: String): Result {
        val t0 = System.currentTimeMillis()
        val normalizedBase = baseUrl.trim().trimEnd('/')
        val connection = (URL("$normalizedBase/v1/sessions/refresh").openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 10_000
            readTimeout = 15_000
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
            setRequestProperty("Accept", "application/json")
        }
        return try {
            connection.outputStream.bufferedWriter().use {
                it.write(JSONObject().apply { put("refresh_token", refreshToken) }.toString())
            }
            parseSessionResponse(connection, "REFRESH", t0)
        } catch (e: IOException) {
            val duration = System.currentTimeMillis() - t0
            diag?.error("AUTH", "REFRESH", "FAILURE", errorCode = "NETWORK_ERROR", durationMs = duration, throwable = e)
            Result.Failure("NETWORK_ERROR: ${e.javaClass.simpleName}: ${e.message}")
        } catch (e: Exception) {
            val duration = System.currentTimeMillis() - t0
            diag?.error("AUTH", "REFRESH", "FAILURE", errorCode = "UNEXPECTED_ERROR", durationMs = duration, throwable = e)
            Result.Failure("UNEXPECTED_ERROR: ${e.javaClass.simpleName}: ${e.message}")
        } finally {
            connection.disconnect()
        }
    }

    private fun requestCredentials(path: String, email: String, password: String, op: String): Result {
        val t0 = System.currentTimeMillis()
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
            parseSessionResponse(connection, op, t0)
        } catch (e: IOException) {
            val duration = System.currentTimeMillis() - t0
            diag?.error("AUTH", op, "FAILURE", errorCode = "NETWORK_ERROR", durationMs = duration, throwable = e)
            Result.Failure("NETWORK_ERROR: ${e.javaClass.simpleName}: ${e.message}")
        } catch (e: Exception) {
            val duration = System.currentTimeMillis() - t0
            diag?.error("AUTH", op, "FAILURE", errorCode = "UNEXPECTED_ERROR", durationMs = duration, throwable = e)
            Result.Failure("UNEXPECTED_ERROR: ${e.javaClass.simpleName}: ${e.message}")
        } finally {
            connection.disconnect()
        }
    }

    private fun parseSessionResponse(connection: HttpURLConnection, op: String, t0: Long): Result {
        val status = connection.responseCode
        val body = (if (status in 200..299) connection.inputStream else connection.errorStream)
            ?.bufferedReader()?.use { it.readText() }.orEmpty()
        val json = runCatching { JSONObject(body) }.getOrNull()
        val duration = System.currentTimeMillis() - t0
        if (status !in 200..299 || json == null) {
            val code = json?.optString("code")?.takeIf { it.isNotBlank() } ?: "HTTP_$status"
            diag?.warn("AUTH", op, "FAILURE", errorCode = code, durationMs = duration)
            return Result.Failure(code)
        }
        val scopesJson = json.optJSONArray("scopes")
        val scopes = buildList {
            if (scopesJson != null) for (i in 0 until scopesJson.length()) add(scopesJson.getString(i))
        }
        val access = json.optString("session_token")
        val refresh = json.optString("refresh_token")
        if (access.isBlank() || refresh.isBlank()) {
            diag?.warn("AUTH", op, "FAILURE", errorCode = "AUTH_RESPONSE_INVALID", durationMs = duration)
            return Result.Failure("AUTH_RESPONSE_INVALID")
        }
        diag?.info("AUTH", op, "SUCCESS", durationMs = duration, details = mapOf("scopes_count" to scopes.size))
        return Result.Success(Session(access, refresh, scopes))
    }
}
