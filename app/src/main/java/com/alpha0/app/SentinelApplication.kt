package com.alpha0.app

import android.app.Application
import com.alpha0.app.diagnostics.DiagnosticRuntime
import io.sentry.SentryEvent
import io.sentry.SentryOptions
import io.sentry.android.core.SentryAndroid

/**
 * Optional Android runtime crash reporting plus app-private structured diagnostics.
 *
 * The dedicated physicalTest build is intentionally local-only: it installs richer
 * forensic diagnostics but never starts Sentry, even if a DSN is present in the build
 * environment. Release telemetry stays disabled unless the Owner-managed DSN, exact
 * source SHA and an allowlisted runtime environment are all present.
 */
class SentinelApplication : Application() {

    override fun onCreate() {
        super.onCreate()
        val diagnostics = DiagnosticRuntime.install(this)
        if (diagnostics.isForensicTest()) {
            diagnostics.info("TELEMETRY", "REMOTE_TELEMETRY_DISABLED_FOR_FORENSIC_TEST", result = "SKIPPED")
            return
        }

        val dsn = BuildConfig.SENTRY_DSN.trim()
        val sourceSha = BuildConfig.SENTINEL_SOURCE_SHA.trim()
        val environment = BuildConfig.SENTINEL_RUNTIME_ENVIRONMENT.trim()
        if (dsn.isEmpty() || !SOURCE_SHA.matches(sourceSha) || environment !in ALLOWED_ENVIRONMENTS) {
            diagnostics.info(
                "TELEMETRY",
                "SENTRY_INIT",
                result = "SKIPPED",
                details = mapOf(
                    "has_dsn" to dsn.isNotEmpty(),
                    "has_source_identity" to SOURCE_SHA.matches(sourceSha),
                    "environment_allowed" to (environment in ALLOWED_ENVIRONMENTS),
                )
            )
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
        diagnostics.info(
            "TELEMETRY",
            "SENTRY_INIT",
            details = mapOf("environment" to environment, "source_sha_prefix" to sourceSha.take(12)),
        )
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
