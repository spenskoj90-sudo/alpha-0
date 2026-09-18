package com.alpha0.app.auth

import android.content.Context
import com.alpha0.app.diagnostics.DiagnosticLogger
import com.alpha0.app.net.HttpMethod
import com.alpha0.app.net.HttpRequest
import com.alpha0.app.net.HttpResponse
import com.alpha0.app.net.HttpTransport
import com.alpha0.app.net.UrlConnectionHttpTransport
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.IOException
import java.net.SocketTimeoutException

interface RefreshClient {
    suspend fun refresh(refreshToken: String): AuthApi.Result
}

class AuthApi(
    private val baseUrl: String,
    private val transport: HttpTransport = UrlConnectionHttpTransport(),
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

    sealed interface ActionResult {
        data class Success(val status: String) : ActionResult
        data class Failure(val message: String) : ActionResult
    }

    data class ProviderStatus(
        val provider: String,
        val enabled: Boolean,
        val flow: String,
        val clientId: String?,
    )

    sealed interface ProviderCatalogResult {
        data class Success(val providers: List<ProviderStatus>) : ProviderCatalogResult
        data class Failure(val message: String) : ProviderCatalogResult
    }

    data class GoogleChallenge(val clientId: String, val nonce: String)

    sealed interface GoogleChallengeResult {
        data class Success(val value: GoogleChallenge) : GoogleChallengeResult
        data class Failure(val message: String) : GoogleChallengeResult
    }

    data class BrowserStart(
        val provider: String,
        val authorizationUrl: String,
        val state: String,
        val codeVerifier: String,
    )

    sealed interface BrowserStartResult {
        data class Success(val value: BrowserStart) : BrowserStartResult
        data class Failure(val message: String) : BrowserStartResult
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

    suspend fun requestEmailVerification(email: String): ActionResult = withContext(Dispatchers.IO) {
        requestAction(
            "/v1/auth/email-verification/request",
            JSONObject().apply { put("email", email.trim().lowercase()) }.toString(),
            "EMAIL_VERIFY_REQUEST",
        )
    }

    suspend fun confirmEmailVerification(token: String): ActionResult = withContext(Dispatchers.IO) {
        requestAction(
            "/v1/auth/email-verification/confirm",
            JSONObject().apply { put("token", token.trim()) }.toString(),
            "EMAIL_VERIFY_CONFIRM",
        )
    }

    suspend fun requestPasswordReset(email: String): ActionResult = withContext(Dispatchers.IO) {
        requestAction(
            "/v1/auth/password-reset/request",
            JSONObject().apply { put("email", email.trim().lowercase()) }.toString(),
            "PASSWORD_RESET_REQUEST",
        )
    }

    suspend fun confirmPasswordReset(token: String, password: String): ActionResult = withContext(Dispatchers.IO) {
        requestAction(
            "/v1/auth/password-reset/confirm",
            JSONObject().apply {
                put("token", token.trim())
                put("password", password)
            }.toString(),
            "PASSWORD_RESET_CONFIRM",
        )
    }

    suspend fun providerCatalog(): ProviderCatalogResult = withContext(Dispatchers.IO) {
        val t0 = System.currentTimeMillis()
        val normalizedBase = baseUrl.trim().trimEnd('/')
        try {
            val response = transport.execute(
                HttpRequest(
                    method = HttpMethod.GET,
                    url = "$normalizedBase/v1/auth/providers",
                    headers = mapOf("Accept" to "application/json"),
                )
            )
            val json = runCatching { JSONObject(response.body) }.getOrNull()
            val duration = System.currentTimeMillis() - t0
            if (response.status !in 200..299 || json == null) {
                val code = json?.optString("code")?.takeIf { it.isNotBlank() } ?: "HTTP_${response.status}"
                diag?.warn("AUTH", "PROVIDER_CATALOG", "FAILURE", errorCode = code, durationMs = duration)
                ProviderCatalogResult.Failure(code)
            } else {
                val items = json.optJSONArray("providers")
                val providers = buildList {
                    if (items != null) {
                        for (i in 0 until items.length()) {
                            val item = items.optJSONObject(i) ?: continue
                            val provider = item.optString("provider")
                            val flow = item.optString("flow")
                            if (provider.isBlank() || flow.isBlank()) continue
                            add(
                                ProviderStatus(
                                    provider = provider,
                                    enabled = item.optBoolean("enabled", false),
                                    flow = flow,
                                    clientId = item.optString("client_id").takeIf { it.isNotBlank() },
                                )
                            )
                        }
                    }
                }
                diag?.info("AUTH", "PROVIDER_CATALOG", "SUCCESS", durationMs = duration)
                ProviderCatalogResult.Success(providers)
            }
        } catch (e: IOException) {
            diag?.warn("AUTH", "PROVIDER_CATALOG", "FAILURE", errorCode = "NETWORK_ERROR")
            ProviderCatalogResult.Failure("NETWORK_ERROR")
        } catch (e: Exception) {
            diag?.error("AUTH", "PROVIDER_CATALOG", "FAILURE", errorCode = "UNEXPECTED_ERROR", throwable = e)
            ProviderCatalogResult.Failure("UNEXPECTED_ERROR")
        }
    }

    suspend fun googleChallenge(): GoogleChallengeResult = withContext(Dispatchers.IO) {
        val t0 = System.currentTimeMillis()
        val normalizedBase = baseUrl.trim().trimEnd('/')
        try {
            val response = transport.execute(
                HttpRequest(
                    method = HttpMethod.POST,
                    url = "$normalizedBase/v1/auth/providers/google/challenge",
                    headers = mapOf("Accept" to "application/json"),
                )
            )
            val json = runCatching { JSONObject(response.body) }.getOrNull()
            val duration = System.currentTimeMillis() - t0
            if (response.status !in 200..299 || json == null) {
                val code = json?.optString("code")?.takeIf { it.isNotBlank() } ?: "HTTP_${response.status}"
                diag?.warn("AUTH", "GOOGLE_CHALLENGE", "FAILURE", errorCode = code, durationMs = duration)
                GoogleChallengeResult.Failure(code)
            } else {
                val clientId = json.optString("client_id")
                val nonce = json.optString("nonce")
                if (clientId.isBlank() || nonce.length < 32) {
                    GoogleChallengeResult.Failure("AUTH_RESPONSE_INVALID")
                } else {
                    GoogleChallengeResult.Success(GoogleChallenge(clientId, nonce))
                }
            }
        } catch (e: IOException) {
            GoogleChallengeResult.Failure("NETWORK_ERROR")
        } catch (e: Exception) {
            diag?.error("AUTH", "GOOGLE_CHALLENGE", "FAILURE", errorCode = "UNEXPECTED_ERROR", throwable = e)
            GoogleChallengeResult.Failure("UNEXPECTED_ERROR")
        }
    }

    suspend fun loginGoogle(idToken: String, nonce: String): Result = withContext(Dispatchers.IO) {
        requestJson(
            "/v1/auth/providers/google/login",
            JSONObject().apply {
                put("id_token", idToken)
                put("nonce", nonce)
            }.toString(),
            "GOOGLE_LOGIN",
        )
    }

    suspend fun startBrowserProvider(provider: String): BrowserStartResult = withContext(Dispatchers.IO) {
        val normalizedProvider = provider.trim().lowercase()
        val t0 = System.currentTimeMillis()
        val normalizedBase = baseUrl.trim().trimEnd('/')
        try {
            val response = transport.execute(
                HttpRequest(
                    method = HttpMethod.POST,
                    url = "$normalizedBase/v1/auth/providers/$normalizedProvider/start",
                    headers = mapOf("Accept" to "application/json"),
                )
            )
            val json = runCatching { JSONObject(response.body) }.getOrNull()
            val duration = System.currentTimeMillis() - t0
            if (response.status !in 200..299 || json == null) {
                val code = json?.optString("code")?.takeIf { it.isNotBlank() } ?: "HTTP_${response.status}"
                diag?.warn("AUTH", "BROWSER_AUTH_START", "FAILURE", errorCode = code, durationMs = duration)
                BrowserStartResult.Failure(code)
            } else {
                val returnedProvider = json.optString("provider")
                val authorizationUrl = json.optString("authorization_url")
                val state = json.optString("state")
                val verifier = json.optString("code_verifier")
                if (
                    returnedProvider != normalizedProvider ||
                    !authorizationUrl.startsWith("https://") ||
                    state.length < 32 ||
                    verifier.length < 43
                ) {
                    BrowserStartResult.Failure("AUTH_RESPONSE_INVALID")
                } else {
                    BrowserStartResult.Success(
                        BrowserStart(returnedProvider, authorizationUrl, state, verifier)
                    )
                }
            }
        } catch (e: IOException) {
            BrowserStartResult.Failure("NETWORK_ERROR")
        } catch (e: Exception) {
            diag?.error("AUTH", "BROWSER_AUTH_START", "FAILURE", errorCode = "UNEXPECTED_ERROR", throwable = e)
            BrowserStartResult.Failure("UNEXPECTED_ERROR")
        }
    }

    suspend fun completeBrowserProvider(
        provider: String,
        code: String,
        state: String,
        codeVerifier: String,
        deviceId: String?,
    ): Result = withContext(Dispatchers.IO) {
        requestJson(
            "/v1/auth/providers/${provider.trim().lowercase()}/complete",
            JSONObject().apply {
                put("code", code)
                put("state", state)
                put("code_verifier", codeVerifier)
                if (!deviceId.isNullOrBlank()) put("device_id", deviceId)
            }.toString(),
            "BROWSER_AUTH_COMPLETE",
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
            val response = transport.execute(
                HttpRequest(
                    method = HttpMethod.POST,
                    url = "$normalizedBase$path",
                    headers = mapOf(
                        "Content-Type" to "application/json",
                        "Accept" to "application/json",
                    ),
                    body = payload.toByteArray(Charsets.UTF_8),
                )
            )
            parseSessionResponse(response, op, t0)
        } catch (e: IOException) {
            val duration = System.currentTimeMillis() - t0
            val code = when {
                e is SocketTimeoutException && op == "REGISTER" -> "REGISTER_OUTCOME_UNKNOWN"
                e is SocketTimeoutException -> "REQUEST_TIMEOUT"
                else -> "NETWORK_ERROR"
            }
            diag?.error("AUTH", op, "FAILURE", errorCode = code, durationMs = duration, throwable = e)
            Result.Failure(code)
        } catch (e: Exception) {
            val duration = System.currentTimeMillis() - t0
            diag?.error("AUTH", op, "FAILURE", errorCode = "UNEXPECTED_ERROR", durationMs = duration, throwable = e)
            Result.Failure("UNEXPECTED_ERROR")
        }
    }

    private fun requestAction(path: String, payload: String, op: String): ActionResult {
        val t0 = System.currentTimeMillis()
        val normalizedBase = baseUrl.trim().trimEnd('/')
        return try {
            val response = transport.execute(
                HttpRequest(
                    method = HttpMethod.POST,
                    url = "$normalizedBase$path",
                    headers = mapOf(
                        "Content-Type" to "application/json",
                        "Accept" to "application/json",
                    ),
                    body = payload.toByteArray(Charsets.UTF_8),
                )
            )
            val json = runCatching { JSONObject(response.body) }.getOrNull()
            val duration = System.currentTimeMillis() - t0
            if (response.status !in 200..299 || json == null) {
                val code = json?.optString("code")?.takeIf { it.isNotBlank() } ?: "HTTP_${response.status}"
                diag?.warn("AUTH", op, "FAILURE", errorCode = code, durationMs = duration)
                ActionResult.Failure(code)
            } else {
                val status = json.optString("status")
                if (status.isBlank()) {
                    ActionResult.Failure("AUTH_RESPONSE_INVALID")
                } else {
                    diag?.info("AUTH", op, "SUCCESS", durationMs = duration)
                    ActionResult.Success(status)
                }
            }
        } catch (e: SocketTimeoutException) {
            diag?.warn("AUTH", op, "FAILURE", errorCode = "REQUEST_TIMEOUT", durationMs = System.currentTimeMillis() - t0)
            ActionResult.Failure("REQUEST_TIMEOUT")
        } catch (e: IOException) {
            diag?.warn("AUTH", op, "FAILURE", errorCode = "NETWORK_ERROR", durationMs = System.currentTimeMillis() - t0)
            ActionResult.Failure("NETWORK_ERROR")
        } catch (e: Exception) {
            diag?.error("AUTH", op, "FAILURE", errorCode = "UNEXPECTED_ERROR", durationMs = System.currentTimeMillis() - t0, throwable = e)
            ActionResult.Failure("UNEXPECTED_ERROR")
        }
    }

    private fun parseSessionResponse(response: HttpResponse, op: String, t0: Long): Result {
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
