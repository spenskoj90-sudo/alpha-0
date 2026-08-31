package com.alpha0.app

import android.app.Application
import io.sentry.Sentry
import io.sentry.SentryEvent
import io.sentry.SentryOptions
import io.sentry.android.core.SentryAndroid
import io.sentry.protocol.User

/**
 * Application entry for optional Sentry initialization.
 *
 * DSN is supplied exclusively via BuildConfig.SENTRY_DSN (populated from
 * the CI secret SENTRY_DSN for release builds only). Debug / PR builds
 * receive an empty string and never contact Sentry.
 *
 * Privacy: beforeSend strips user identity, emails, and any token-like
 * values so only technical crash context is transmitted.
 */
class SentinelApplication : Application() {

    override fun onCreate() {
        super.onCreate()
        val dsn = BuildConfig.SENTRY_DSN.trim()
        if (dsn.isEmpty()) {
            return
        }
        SentryAndroid.init(this) { options ->
            options.dsn = dsn
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
        /** Remove PII / credentials before any event leaves the device. */
        fun scrubEvent(event: SentryEvent): SentryEvent? {
            event.user = null
            event.request?.headers?.clear()
            event.breadcrumbs?.forEach { crumb ->
                crumb.data?.keys?.toList()?.forEach { key ->
                    val lower = key.lowercase()
                    if (lower.contains("email") ||
                        lower.contains("token") ||
                        lower.contains("password") ||
                        lower.contains("authorization") ||
                        lower.contains("user") ||
                        lower.contains("session") ||
                        lower.contains("device_id") ||
                        lower.contains("fingerprint")
                    ) {
                        crumb.data?.remove(key)
                    }
                }
            }
            event.extra?.keys?.toList()?.forEach { key ->
                val lower = key.lowercase()
                if (lower.contains("email") ||
                    lower.contains("token") ||
                    lower.contains("password") ||
                    lower.contains("authorization") ||
                    lower.contains("user") ||
                    lower.contains("session") ||
                    lower.contains("device_id") ||
                    lower.contains("fingerprint")
                ) {
                    event.extra?.remove(key)
                }
            }
            // Drop any user object that might have been set later
            event.user = User()
            event.user?.email = null
            event.user?.id = null
            event.user?.username = null
            event.user?.ipAddress = null
            return event
        }
    }
}
