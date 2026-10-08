package com.alpha0.app

import io.sentry.Hint
import io.sentry.SentryLogEvent
import io.sentry.SentryLogLevel
import io.sentry.SentryMetricsEvent
import io.sentry.SentryOptions
import io.sentry.protocol.SentryId
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Test

class TelemetryPrivacyTest {
    @Test fun manualLogsAndMetricsCannotBypassDisabledChannels() {
        val options = SentryOptions()
        SentinelApplication.restrictTelemetryChannels(options)
        assertFalse(options.logs.isEnabled)
        assertFalse(options.metrics.isEnabled)
        // Manual APIs ignore enabled flags in 8.59; both payload filters must drop.
        val log = SentryLogEvent(SentryId(), "private fixture payload", SentryLogLevel.INFO)
        val metric = SentryMetricsEvent(SentryId(), 1.0, "private fixture metric", "counter", 1.0)
        assertNull(options.logs.beforeSend!!.execute(log))
        assertNull(options.metrics.beforeSend!!.execute(metric, Hint()))
    }
}
