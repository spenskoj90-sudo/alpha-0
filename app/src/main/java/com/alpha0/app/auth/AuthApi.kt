package com.alpha0.app.auth

import android.content.Context
import com.alpha0.app.diagnostics.DiagnosticLogger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.IOException

interface RefreshClient {
    suspend fun refresh(refreshToken: String): AuthApi.Result
}

class AuthApi(
    private val baseUrl: String,
    private val transport: AuthHttpTransport = UrlConnectionAuthHttpTransport(),
) : RefreshClient {
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

    suspend fun register(email: String, password: String): Result = withContext(Dispatchers.IO) {
        requestCredentials("/v1/auth/register", email, password, "REGISTER")
    }

    suspend fun login(email: String, password: String): Result = withContext(Dispatchers.IO) {
        requestCredentials("/v1/auth/login", email, password, "LOGIN")
    }

    override suspend fun refresh(refreshToken: String): Result = withContext(Dispatchers.IO) {
        requestJson(
            "/v1/sessions/refresh",
            JSONObject().apply { put("refresh_token", refreshToken) }.toString(),
            "REFRESH",
        )
    }

    private fun requestCredentials(path: String, email: String, password: String, op: String): Result {
        val payload = JSONObject().apply {
            put("email", email.trim().lowercase())
            put("password", password)
        }.toString()
        return requestJson(path, payload, op)
    }

    private fun requestJson(path: String, payload: String, op: String): Result {
        val t0 = System.currentTimeMillis()
        val normalizedBase = baseUrl.trim().trimEnd('/')
        return try {
            val response = transport.postJson(
                "$normalizedBase$path",
                payload.toByteArray(Charsets.UTF_8),
            )
            parseSessionResponse(response, op, t0)
        } catch (e: IOException) {
            val duration = System.currentTimeMillis() - t0
            diag?.error("AUTH", op, "FAILURE", errorCode = "NETWORK_ERROR", durationMs = duration, throwable = e)
            Result.Failure("NETWORK_ERROR")
        } catch (e: Exception) {
            val duration = System.currentTimeMillis() - t0
            diag?.error("AUTH", op, "FAILURE", errorCode = "UNEXPECTED_ERROR", durationMs = duration, throwable = e)
            Result.Failure("UNEXPECTED_ERROR")
        }
    }

    private fun parseSessionResponse(response: AuthHttpResponse, op: String, t0: Long): Result {
        val json = runCatching { JSONObject(response.body) }.getOrNull()
        val duration = System.currentTimeMillis() - t0
        if (response.status !in 200..299 || json == null) {
            val code = json?.optString("code")?.takeIf { it.isNotBlank() } ?: "HTTP_${response.status}"
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
