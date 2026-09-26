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
        data class MfaRequired(val challengeToken: String, val expiresAt: String?) : Result
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

    sealed interface CoreReadinessResult {
        data object Success : CoreReadinessResult
        data class Failure(val message: String) : CoreReadinessResult
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

    data class AccountSecurity(
        val email: String?,
        val emailVerified: Boolean,
        val passwordEnabled: Boolean,
        val providers: List<String>,
        val mfaEnabled: Boolean,
        val mfaRecoveryCodesRemaining: Int,
    )

    sealed interface AccountSecurityResult {
        data class Success(val value: AccountSecurity) : AccountSecurityResult
        data class Failure(val message: String) : AccountSecurityResult
    }

    data class TotpEnrollment(val secret: String, val otpauthUri: String)

    sealed interface TotpEnrollmentResult {
        data class Success(val value: TotpEnrollment) : TotpEnrollmentResult
        data class Failure(val message: String) : TotpEnrollmentResult
    }

    sealed interface RecoveryCodesResult {
        data class Success(val status: String, val codes: List<String>) : RecoveryCodesResult
        data class Failure(val message: String) : RecoveryCodesResult
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

    suspend fun completeMfa(challengeToken: String, code: String): Result = withContext(Dispatchers.IO) {
        requestJson(
            "/v1/auth/mfa/complete",
            JSONObject().apply {
                put("challenge_token", challengeToken)
                put("code", code.trim())
            }.toString(),
            "MFA_COMPLETE",
        )
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

    suspend fun requestAccountEmailVerification(accessToken: String): ActionResult = withContext(Dispatchers.IO) {
        requestAction(
            "/v1/account/email-verification/request",
            "{}",
            "ACCOUNT_EMAIL_VERIFY_REQUEST",
            mapOf("Authorization" to "Bearer $accessToken"),
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

    suspend fun coreReadiness(): CoreReadinessResult = withContext(Dispatchers.IO) {
        val t0 = System.currentTimeMillis()
        val normalizedBase = baseUrl.trim().trimEnd('/')
        try {
            val response = transport.execute(
                HttpRequest(
                    method = HttpMethod.GET,
                    url = "$normalizedBase/healthz",
                    headers = mapOf("Accept" to "application/json"),
                )
            )
            val json = runCatching { JSONObject(response.body) }.getOrNull()
            val duration = System.currentTimeMillis() - t0
            if (response.status !in 200..299 || json?.optString("status") != "UP") {
                val code = json?.optString("code")?.takeIf { it.isNotBlank() }
                    ?: json?.optString("error")?.takeIf { it.isNotBlank() }
                    ?: "HTTP_${response.status}"
                diag?.warn("AUTH", "CORE_READINESS", "FAILURE", errorCode = code, durationMs = duration)
                CoreReadinessResult.Failure(code)
            } else {
                diag?.info("AUTH", "CORE_READINESS", "SUCCESS", durationMs = duration)
                CoreReadinessResult.Success
            }
        } catch (_: SocketTimeoutException) {
            val duration = System.currentTimeMillis() - t0
            diag?.warn("AUTH", "CORE_READINESS", "FAILURE", errorCode = "REQUEST_TIMEOUT", durationMs = duration)
            CoreReadinessResult.Failure("REQUEST_TIMEOUT")
        } catch (_: IOException) {
            val duration = System.currentTimeMillis() - t0
            diag?.warn("AUTH", "CORE_READINESS", "FAILURE", errorCode = "NETWORK_ERROR", durationMs = duration)
            CoreReadinessResult.Failure("NETWORK_ERROR")
        } catch (e: Exception) {
            val duration = System.currentTimeMillis() - t0
            diag?.error("AUTH", "CORE_READINESS", "FAILURE", errorCode = "UNEXPECTED_ERROR", durationMs = duration, throwable = e)
            CoreReadinessResult.Failure("UNEXPECTED_ERROR")
        }
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

    suspend fun startBrowserProvider(provider: String, redirectUri: String): BrowserStartResult = withContext(Dispatchers.IO) {
        val normalizedProvider = provider.trim().lowercase()
        val t0 = System.currentTimeMillis()
        val normalizedBase = baseUrl.trim().trimEnd('/')
        try {
            val response = transport.execute(
                HttpRequest(
                    method = HttpMethod.POST,
                    url = "$normalizedBase/v1/auth/providers/$normalizedProvider/start",
                    headers = mapOf(
                        "Content-Type" to "application/json",
                        "Accept" to "application/json",
                    ),
                    body = JSONObject().apply { put("redirect_uri", redirectUri) }
                        .toString()
                        .toByteArray(Charsets.UTF_8),
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

    suspend fun accountSecurity(accessToken: String): AccountSecurityResult = withContext(Dispatchers.IO) {
        val normalizedBase = baseUrl.trim().trimEnd('/')
        try {
            val response = transport.execute(
                HttpRequest(
                    method = HttpMethod.GET,
                    url = "$normalizedBase/v1/account/security",
                    headers = mapOf(
                        "Authorization" to "Bearer $accessToken",
                        "Accept" to "application/json",
                    ),
                )
            )
            val json = runCatching { JSONObject(response.body) }.getOrNull()
            if (response.status !in 200..299 || json == null) {
                val code = json?.optString("code")?.takeIf { it.isNotBlank() } ?: "HTTP_${response.status}"
                AccountSecurityResult.Failure(code)
            } else {
                val providerArray = json.optJSONArray("providers")
                val providers = buildList {
                    if (providerArray != null) {
                        for (i in 0 until providerArray.length()) {
                            val provider = providerArray.optString(i)
                            if (provider.isNotBlank()) add(provider)
                        }
                    }
                }
                AccountSecurityResult.Success(
                    AccountSecurity(
                        email = json.optString("email").takeIf { it.isNotBlank() },
                        emailVerified = json.optBoolean("email_verified", false),
                        passwordEnabled = json.optBoolean("password_enabled", false),
                        providers = providers,
                        mfaEnabled = json.optBoolean("mfa_enabled", false),
                        mfaRecoveryCodesRemaining = json.optInt("mfa_recovery_codes_remaining", 0),
                    )
                )
            }
        } catch (_: IOException) {
            AccountSecurityResult.Failure("NETWORK_ERROR")
        } catch (e: Exception) {
            diag?.error("AUTH", "ACCOUNT_SECURITY", "FAILURE", errorCode = "UNEXPECTED_ERROR", throwable = e)
            AccountSecurityResult.Failure("UNEXPECTED_ERROR")
        }
    }

    suspend fun enrollTotp(accessToken: String): TotpEnrollmentResult = withContext(Dispatchers.IO) {
        val t0 = System.currentTimeMillis()
        val normalizedBase = baseUrl.trim().trimEnd('/')
        try {
            val response = transport.execute(
                HttpRequest(
                    method = HttpMethod.POST,
                    url = "$normalizedBase/v1/account/mfa/totp/enroll",
                    headers = mapOf(
                        "Authorization" to "Bearer $accessToken",
                        "Content-Type" to "application/json",
                        "Accept" to "application/json",
                    ),
                    body = "{}".toByteArray(Charsets.UTF_8),
                )
            )
            val json = runCatching { JSONObject(response.body) }.getOrNull()
            val duration = System.currentTimeMillis() - t0
            if (response.status !in 200..299 || json == null) {
                val code = json?.optString("code")?.takeIf { it.isNotBlank() } ?: "HTTP_${response.status}"
                diag?.warn("AUTH", "MFA_ENROLL", "FAILURE", errorCode = code, durationMs = duration)
                TotpEnrollmentResult.Failure(code)
            } else {
                val secret = json.optString("secret")
                val uri = json.optString("otpauth_uri")
                if (secret.isBlank() || uri.isBlank()) TotpEnrollmentResult.Failure("AUTH_RESPONSE_INVALID")
                else TotpEnrollmentResult.Success(TotpEnrollment(secret, uri))
            }
        } catch (_: SocketTimeoutException) {
            TotpEnrollmentResult.Failure("REQUEST_TIMEOUT")
        } catch (_: IOException) {
            TotpEnrollmentResult.Failure("NETWORK_ERROR")
        } catch (e: Exception) {
            diag?.error("AUTH", "MFA_ENROLL", "FAILURE", errorCode = "UNEXPECTED_ERROR", throwable = e)
            TotpEnrollmentResult.Failure("UNEXPECTED_ERROR")
        }
    }

    suspend fun confirmTotp(accessToken: String, code: String): RecoveryCodesResult = withContext(Dispatchers.IO) {
        requestRecoveryCodes("/v1/account/mfa/totp/confirm", accessToken, code, "MFA_CONFIRM")
    }

    suspend fun rotateRecoveryCodes(accessToken: String, code: String): RecoveryCodesResult = withContext(Dispatchers.IO) {
        requestRecoveryCodes("/v1/account/mfa/recovery-codes/rotate", accessToken, code, "MFA_RECOVERY_ROTATE")
    }

    suspend fun disableTotp(accessToken: String, code: String): ActionResult = withContext(Dispatchers.IO) {
        requestAction(
            "/v1/account/mfa/totp/disable",
            JSONObject().apply { put("code", code.trim()) }.toString(),
            "MFA_DISABLE",
            mapOf("Authorization" to "Bearer $accessToken"),
        )
    }

    suspend fun linkGoogle(
        accessToken: String,
        idToken: String,
        nonce: String,
    ): ActionResult = withContext(Dispatchers.IO) {
        requestAction(
            "/v1/account/providers/google/link",
            JSONObject().apply {
                put("id_token", idToken)
                put("nonce", nonce)
            }.toString(),
            "GOOGLE_LINK",
            mapOf("Authorization" to "Bearer $accessToken"),
        )
    }

    suspend fun linkBrowserProvider(
        accessToken: String,
        provider: String,
        code: String,
        state: String,
        codeVerifier: String,
        deviceId: String?,
    ): ActionResult = withContext(Dispatchers.IO) {
        requestAction(
            "/v1/account/providers/${provider.trim().lowercase()}/link",
            JSONObject().apply {
                put("code", code)
                put("state", state)
                put("code_verifier", codeVerifier)
                if (!deviceId.isNullOrBlank()) put("device_id", deviceId)
            }.toString(),
            "BROWSER_AUTH_LINK",
            mapOf("Authorization" to "Bearer $accessToken"),
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

    private fun requestRecoveryCodes(
        path: String,
        accessToken: String,
        code: String,
        op: String,
    ): RecoveryCodesResult {
        val t0 = System.currentTimeMillis()
        val normalizedBase = baseUrl.trim().trimEnd('/')
        return try {
            val response = transport.execute(
                HttpRequest(
                    method = HttpMethod.POST,
                    url = "$normalizedBase$path",
                    headers = mapOf(
                        "Authorization" to "Bearer $accessToken",
                        "Content-Type" to "application/json",
                        "Accept" to "application/json",
                    ),
                    body = JSONObject().apply { put("code", code.trim()) }.toString().toByteArray(Charsets.UTF_8),
                )
            )
            val json = runCatching { JSONObject(response.body) }.getOrNull()
            val duration = System.currentTimeMillis() - t0
            if (response.status !in 200..299 || json == null) {
                val errorCode = json?.optString("code")?.takeIf { it.isNotBlank() } ?: "HTTP_${response.status}"
                diag?.warn("AUTH", op, "FAILURE", errorCode = errorCode, durationMs = duration)
                RecoveryCodesResult.Failure(errorCode)
            } else {
                val status = json.optString("status")
                val values = json.optJSONArray("recovery_codes")
                val codes = buildList {
                    if (values != null) for (i in 0 until values.length()) {
                        values.optString(i).takeIf { it.isNotBlank() }?.let(::add)
                    }
                }
                if (status.isBlank() || codes.isEmpty()) RecoveryCodesResult.Failure("AUTH_RESPONSE_INVALID")
                else RecoveryCodesResult.Success(status, codes)
            }
        } catch (_: SocketTimeoutException) {
            RecoveryCodesResult.Failure("REQUEST_TIMEOUT")
        } catch (_: IOException) {
            RecoveryCodesResult.Failure("NETWORK_ERROR")
        } catch (e: Exception) {
            diag?.error("AUTH", op, "FAILURE", errorCode = "UNEXPECTED_ERROR", throwable = e)
            RecoveryCodesResult.Failure("UNEXPECTED_ERROR")
        }
    }

    private fun requestAction(
        path: String,
        payload: String,
        op: String,
        extraHeaders: Map<String, String> = emptyMap(),
    ): ActionResult {
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
                    ) + extraHeaders,
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
        if (json.optBoolean("mfa_required", false)) {
            val challenge = json.optString("challenge_token")
            if (challenge.isBlank()) {
                diag?.warn("AUTH", op, "FAILURE", errorCode = "AUTH_RESPONSE_INVALID", durationMs = duration)
                return Result.Failure("AUTH_RESPONSE_INVALID")
            }
            diag?.info("AUTH", op, "MFA_REQUIRED", durationMs = duration)
            return Result.MfaRequired(
                challengeToken = challenge,
                expiresAt = json.optString("expires_at").takeIf { it.isNotBlank() },
            )
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
