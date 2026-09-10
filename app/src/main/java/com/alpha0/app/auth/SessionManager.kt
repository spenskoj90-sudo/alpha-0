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
        when (val result = api.refresh(current.refreshToken)) {
            is AuthApi.Result.Success -> {
                store.save(context, result.session.accessToken, result.session.refreshToken, current.deviceId)
                result
            }
            is AuthApi.Result.Failure -> {
                if (result.message == "INVALID_REFRESH" || result.message == "SESSION_REVOKED") {
                    store.clear(context)
                }
                result
            }
        }
    }
}
