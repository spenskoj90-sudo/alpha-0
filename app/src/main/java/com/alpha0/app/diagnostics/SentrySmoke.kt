package com.alpha0.app.diagnostics

import com.alpha0.app.BuildConfig
import io.sentry.Sentry

/**
 * TEMPORARY release-only Sentry path verification (Owner activation).
 *
 * Remove this file and the Dashboard smoke UI after the first event is
 * confirmed in the Sentry project dashboard.
 *
 * Gate: not a debug build AND BuildConfig.SENTRY_DSN is non-empty
 * (populated only by CI release jobs that inject secrets.SENTRY_DSN).
 */
object SentrySmoke {

    const val MESSAGE = "SENTINEL_SENTRY_SMOKE"

    fun isEnabled(): Boolean =
        !BuildConfig.DEBUG && BuildConfig.SENTRY_DSN.trim().isNotEmpty()

    /**
     * Captures a controlled exception without killing the process.
     * Sufficient to verify DSN, init, and network path to Sentry.
     * Returns false when the gate is closed (no-op).
     */
    fun captureSmoke(): Boolean {
        if (!isEnabled()) return false
        Sentry.captureException(RuntimeException(MESSAGE))
        return true
    }
}
