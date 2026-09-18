package com.alpha0.app.auth

import android.content.Context
import android.net.Uri
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialException
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import java.security.MessageDigest

class FederatedAuthCoordinator(
    private val context: Context,
    private val api: AuthApi,
    private val callbackScheme: String,
    private val stateStore: FederatedAuthStateStore = FederatedAuthStateStore(),
    private val credentialManager: CredentialManager = CredentialManager.create(context),
) {
    data class BrowserLaunch(val provider: String, val url: String)

    sealed interface BrowserLaunchResult {
        data class Success(val value: BrowserLaunch) : BrowserLaunchResult
        data class Failure(val message: String) : BrowserLaunchResult
    }

    suspend fun signInWithGoogle(): AuthApi.Result {
        val challenge = when (val result = api.googleChallenge()) {
            is AuthApi.GoogleChallengeResult.Success -> result.value
            is AuthApi.GoogleChallengeResult.Failure -> return AuthApi.Result.Failure(result.message)
        }
        val option = GetGoogleIdOption.Builder()
            .setServerClientId(challenge.clientId)
            .setFilterByAuthorizedAccounts(false)
            .setAutoSelectEnabled(false)
            .setNonce(challenge.nonce)
            .build()
        val request = GetCredentialRequest.Builder()
            .addCredentialOption(option)
            .build()
        val credential = try {
            credentialManager.getCredential(context, request).credential
        } catch (_: GetCredentialException) {
            return AuthApi.Result.Failure("GOOGLE_CREDENTIAL_CANCELLED")
        } catch (_: Exception) {
            return AuthApi.Result.Failure("GOOGLE_CREDENTIAL_ERROR")
        }
        if (
            credential !is CustomCredential ||
            credential.type != GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL
        ) {
            return AuthApi.Result.Failure("GOOGLE_CREDENTIAL_INVALID")
        }
        val token = try {
            GoogleIdTokenCredential.createFrom(credential.data).idToken
        } catch (_: Exception) {
            return AuthApi.Result.Failure("GOOGLE_CREDENTIAL_INVALID")
        }
        if (token.isBlank()) return AuthApi.Result.Failure("GOOGLE_CREDENTIAL_INVALID")
        return api.loginGoogle(token, challenge.nonce)
    }

    suspend fun beginBrowser(provider: String): BrowserLaunchResult {
        val normalized = provider.trim().lowercase()
        if (normalized !in setOf("telegram", "vk")) {
            return BrowserLaunchResult.Failure("AUTH_PROVIDER_UNSUPPORTED")
        }
        return when (
            val result = api.startBrowserProvider(
                normalized,
                "$callbackScheme://callback",
            )
        ) {
            is AuthApi.BrowserStartResult.Failure -> BrowserLaunchResult.Failure(result.message)
            is AuthApi.BrowserStartResult.Success -> {
                val start = result.value
                val uri = runCatching { Uri.parse(start.authorizationUrl) }.getOrNull()
                    ?: return BrowserLaunchResult.Failure("AUTH_RESPONSE_INVALID")
                val expectedHost = if (normalized == "telegram") "oauth.telegram.org" else "id.vk.ru"
                if (uri.scheme != "https" || uri.host != expectedHost) {
                    return BrowserLaunchResult.Failure("AUTH_PROVIDER_ENDPOINT_INVALID")
                }
                stateStore.save(
                    context,
                    FederatedAuthStateStore.Pending(
                        provider = normalized,
                        state = start.state,
                        codeVerifier = start.codeVerifier,
                        createdAtMillis = System.currentTimeMillis(),
                    ),
                )
                BrowserLaunchResult.Success(BrowserLaunch(normalized, start.authorizationUrl))
            }
        }
    }

    suspend fun completeBrowserCallback(uri: Uri): AuthApi.Result {
        if (uri.scheme != callbackScheme || uri.host != "callback") {
            return AuthApi.Result.Failure("AUTH_CALLBACK_INVALID")
        }
        val pending = stateStore.consume(context)
            ?: return AuthApi.Result.Failure("AUTH_CALLBACK_EXPIRED")
        val callbackState = uri.getQueryParameter("state")
            ?: return AuthApi.Result.Failure("AUTH_CALLBACK_INVALID")
        if (!constantTimeEquals(callbackState, pending.state)) {
            return AuthApi.Result.Failure("AUTH_CALLBACK_STATE_MISMATCH")
        }
        val providerError = uri.getQueryParameter("error")
        if (!providerError.isNullOrBlank()) {
            return AuthApi.Result.Failure("AUTH_PROVIDER_CANCELLED")
        }
        val code = uri.getQueryParameter("code")
            ?: return AuthApi.Result.Failure("AUTH_CALLBACK_INVALID")
        if (code.isBlank() || code.length > 4096) {
            return AuthApi.Result.Failure("AUTH_CALLBACK_INVALID")
        }
        val deviceId = uri.getQueryParameter("device_id")?.takeIf { it.isNotBlank() && it.length <= 512 }
        return api.completeBrowserProvider(
            provider = pending.provider,
            code = code,
            state = callbackState,
            codeVerifier = pending.codeVerifier,
            deviceId = deviceId,
        )
    }

    fun cancelPendingBrowserFlow() {
        stateStore.clear(context)
    }

    private fun constantTimeEquals(left: String, right: String): Boolean =
        MessageDigest.isEqual(
            left.toByteArray(Charsets.UTF_8),
            right.toByteArray(Charsets.UTF_8),
        )
}
