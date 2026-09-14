package com.alpha0.app

import android.app.Application
import io.sentry.SentryEvent
import io.sentry.SentryOptions
import io.sentry.android.core.SentryAndroid

/**
 * Optional Android runtime crash reporting.
 *
 * Telemetry stays disabled unless the Owner-managed DSN, exact source SHA and an
 * allowlisted runtime environment are all present. That makes every emitted
 * release event attributable to one repository source instead of a floating
 * build label.
 */
class SentinelApplication : Application() {

    override fun onCreate() {
        super.onCreate()
        val dsn = BuildConfig.SENTRY_DSN.trim()
        val sourceSha = BuildConfig.SENTINEL_SOURCE_SHA.trim()
        val environment = BuildConfig.SENTINEL_RUNTIME_ENVIRONMENT.trim()
        if (dsn.isEmpty() || !SOURCE_SHA.matches(sourceSha) || environment !in ALLOWED_ENVIRONMENTS) {
            return
        }

        val releaseIdentity =
            "com.alpha0.app@${BuildConfig.VERSION_NAME}+${BuildConfig.VERSION_CODE}.${sourceSha.take(12)}"
        SentryAndroid.init(this) { options ->
            options.dsn = dsn
            options.release = releaseIdentity
            options.environment = environment
            options.setTag("sentinel.component", "android")
            options.setTag("sentinel.source_sha", sourceSha)
            options.isEnableUncaughtExceptionHandler = true
            options.isSendDefaultPii = false
            options.isAttachScreenshot = false
            options.isAttachViewHierarchy = false
            options.beforeSend = SentryOptions.BeforeSendCallback { event, _ ->
                scrubEvent(event)
            }
        }
    }

    companion object {
        private val SOURCE_SHA = Regex("[0-9a-f]{40}")
        private val ALLOWED_ENVIRONMENTS =
            setOf("development", "ci", "release-candidate", "production")

        /**
         * Data minimization before any event leaves the device.
         *
         * Runtime crash diagnostics keep the exception/stack trace and static
         * release/component correlation configured above. Identity, request
         * payloads/headers, arbitrary breadcrumbs and extras are removed as a
         * whole rather than relying on a growing sensitive-key denylist.
         */
        fun scrubEvent(event: SentryEvent): SentryEvent? {
            event.user = null
            event.request = null
            event.breadcrumbs?.clear()
            event.extras?.keys?.toList()?.forEach(event::removeExtra)
            return event
        }
    }
}
