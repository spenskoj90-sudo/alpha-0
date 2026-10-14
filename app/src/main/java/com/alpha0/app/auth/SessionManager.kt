package com.alpha0.app.auth

import android.content.Context
import com.alpha0.app.security.SecureSessionStore
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

class SessionManager(
    private val api: RefreshClient,
    private val store: SecureSessionStore,
) {
    private val refreshMutex = Mutex()

    suspend fun refreshStoredSession(context: Context): AuthApi.Result = refreshMutex.withLock {
        val current = store.load(context) ?: return@withLock AuthApi.Result.Failure("NO_SESSION")
        api.refreshWithCommit(current.refreshToken, { store.load(context) == current }) { result -> when (result) {
            is AuthApi.Result.Success -> {
                if (store.replaceIfCurrent(context, current, result.session.accessToken, result.session.refreshToken)) result
                else AuthApi.Result.Failure("SESSION_CHANGED")
            }
            is AuthApi.Result.MfaRequired -> {
                store.clearIfCurrent(context, current)
                AuthApi.Result.Failure("INVALID_REFRESH_RESPONSE")
            }
            is AuthApi.Result.Failure -> {
                if (result.message == "INVALID_REFRESH" || result.message == "SESSION_REVOKED") {
                    store.clearIfCurrent(context, current)
                }
                result
            }
        } }
    }
}
