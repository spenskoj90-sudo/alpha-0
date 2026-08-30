package com.alpha0.app.auth

import android.content.Context
import com.alpha0.app.security.SecureSessionStore

class SessionManager(
    private val api: AuthApi,
    private val store: SecureSessionStore,
) {
    private val refreshLock = Any()

    fun refreshStoredSession(context: Context): AuthApi.Result {
        synchronized(refreshLock) {
            val current = store.load(context) ?: return AuthApi.Result.Failure("NO_SESSION")
            return when (val result = api.refresh(current.refreshToken)) {
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
}
