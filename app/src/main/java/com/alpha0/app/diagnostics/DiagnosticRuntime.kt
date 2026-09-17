package com.alpha0.app.diagnostics

import android.app.Activity
import android.app.ActivityManager
import android.app.Application
import android.content.ComponentCallbacks2
import android.content.Context
import android.content.res.Configuration
import android.os.Build
import android.os.Bundle
import android.os.StrictMode
import com.alpha0.app.BuildConfig
import java.io.InputStreamReader
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Process-level diagnostics instrumentation.
 *
 * FORENSIC_TEST adds high-signal local instrumentation while preserving all normal
 * authorization/security behavior. It never grants permissions, reads other apps'
 * logs, captures screens, records microphone audio, or sends telemetry automatically.
 */
object DiagnosticRuntime {
    private const val MAX_EXIT_TRACE_CHARS = 16_384
    private val installed = AtomicBoolean(false)
    private val strictModeExecutor = Executors.newSingleThreadExecutor { runnable ->
        Thread(runnable, "sentinel-strictmode").apply { isDaemon = true }
    }

    fun install(application: Application): DiagnosticLogger {
        val logger = DiagnosticLogger.get(application)
        if (!installed.compareAndSet(false, true)) return logger

        val metrics = application.resources.displayMetrics
        val configuration = application.resources.configuration
        logger.info(
            "RUNTIME",
            "PROCESS_START",
            details = mapOf(
                "diagnostics_mode" to logger.mode(),
                "build_type" to BuildConfig.BUILD_TYPE,
                "version_name" to BuildConfig.VERSION_NAME,
                "version_code" to BuildConfig.VERSION_CODE,
                "source_sha" to BuildConfig.SENTINEL_SOURCE_SHA,
                "runtime_environment" to BuildConfig.SENTINEL_RUNTIME_ENVIRONMENT,
                "api_origin" to BuildConfig.SENTINEL_API_BASE_URL,
                "sdk" to Build.VERSION.SDK_INT,
                "manufacturer" to Build.MANUFACTURER.take(64),
                "model" to Build.MODEL.take(64),
                "density_dpi" to metrics.densityDpi,
                "font_scale" to configuration.fontScale,
                "orientation" to configuration.orientation,
            )
        )
        installUncaughtExceptionCapture(logger)
        installLifecycleCapture(application, logger)
        installMemoryCapture(application, logger)
        capturePreviousExitReasons(application, logger)
        if (logger.isForensicTest()) installForensicStrictMode(logger)
        return logger
    }

    private fun installUncaughtExceptionCapture(logger: DiagnosticLogger) {
        val previous = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
            logger.error(
                "RUNTIME",
                "UNCAUGHT_EXCEPTION",
                errorCode = "UNCAUGHT_EXCEPTION",
                details = mapOf("thread" to thread.name.take(64)),
                throwable = throwable,
            )
            previous?.uncaughtException(thread, throwable)
        }
    }

    private fun installLifecycleCapture(application: Application, logger: DiagnosticLogger) {
        application.registerActivityLifecycleCallbacks(object : Application.ActivityLifecycleCallbacks {
            override fun onActivityCreated(activity: Activity, savedInstanceState: Bundle?) = lifecycle(logger, activity, "CREATED")
            override fun onActivityStarted(activity: Activity) = lifecycle(logger, activity, "STARTED")
            override fun onActivityResumed(activity: Activity) = lifecycle(logger, activity, "RESUMED")
            override fun onActivityPaused(activity: Activity) = lifecycle(logger, activity, "PAUSED")
            override fun onActivityStopped(activity: Activity) = lifecycle(logger, activity, "STOPPED")
            override fun onActivitySaveInstanceState(activity: Activity, outState: Bundle) = lifecycle(logger, activity, "STATE_SAVED")
            override fun onActivityDestroyed(activity: Activity) = lifecycle(logger, activity, "DESTROYED")
        })
    }

    private fun lifecycle(logger: DiagnosticLogger, activity: Activity, state: String) {
        logger.debug(
            "LIFECYCLE",
            "ACTIVITY_$state",
            details = mapOf("activity" to activity.javaClass.simpleName.take(64)),
        )
    }

    private fun installMemoryCapture(application: Application, logger: DiagnosticLogger) {
        application.registerComponentCallbacks(object : ComponentCallbacks2 {
            override fun onConfigurationChanged(newConfig: Configuration) {
                logger.debug(
                    "RUNTIME",
                    "CONFIGURATION_CHANGED",
                    details = mapOf(
                        "orientation" to newConfig.orientation,
                        "font_scale" to newConfig.fontScale,
                    )
                )
            }

            override fun onLowMemory() {
                logger.warn("RUNTIME", "LOW_MEMORY", errorCode = "LOW_MEMORY")
            }

            override fun onTrimMemory(level: Int) {
                logger.warn(
                    "RUNTIME",
                    "TRIM_MEMORY",
                    result = "OBSERVED",
                    details = mapOf("level" to level),
                )
            }
        })
    }

    private fun capturePreviousExitReasons(context: Context, logger: DiagnosticLogger) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return
        try {
            val manager = context.getSystemService(ActivityManager::class.java) ?: return
            manager.getHistoricalProcessExitReasons(context.packageName, 0, 5).forEach { reason ->
                val details = linkedMapOf<String, Any?>(
                    "reason" to reason.reason,
                    "status" to reason.status,
                    "importance" to reason.importance,
                    "timestamp_ms" to reason.timestamp,
                    "pss_kb" to reason.pss,
                    "rss_kb" to reason.rss,
                    "description" to DiagnosticLogger.sanitizeTextForDiagnostics(reason.description, 512),
                )
                if (logger.isForensicTest()) {
                    readExitTrace(reason.traceInputStream)?.let { details["trace_excerpt"] = it }
                }
                logger.info("RUNTIME", "PREVIOUS_PROCESS_EXIT", result = "OBSERVED", details = details)
            }
        } catch (error: Exception) {
            logger.warn(
                "RUNTIME",
                "PROCESS_EXIT_HISTORY_UNAVAILABLE",
                errorCode = error.javaClass.simpleName.take(96),
            )
        }
    }

    private fun readExitTrace(stream: java.io.InputStream?): String? {
        if (stream == null) return null
        return runCatching {
            stream.use { input ->
                InputStreamReader(input, Charsets.UTF_8).use { reader ->
                    val buffer = CharArray(MAX_EXIT_TRACE_CHARS)
                    val count = reader.read(buffer, 0, buffer.size)
                    if (count <= 0) null else DiagnosticLogger.sanitizeTextForDiagnostics(String(buffer, 0, count), MAX_EXIT_TRACE_CHARS)
                }
            }
        }.getOrNull()
    }

    private fun installForensicStrictMode(logger: DiagnosticLogger) {
        val listener = StrictMode.OnThreadViolationListener { violation ->
            logger.warn(
                "STRICTMODE",
                "THREAD_VIOLATION",
                errorCode = violation.javaClass.simpleName.take(96),
                throwable = violation,
            )
        }
        val vmListener = StrictMode.OnVmViolationListener { violation ->
            logger.warn(
                "STRICTMODE",
                "VM_VIOLATION",
                errorCode = violation.javaClass.simpleName.take(96),
                throwable = violation,
            )
        }
        StrictMode.setThreadPolicy(
            StrictMode.ThreadPolicy.Builder()
                .detectNetwork()
                .detectCustomSlowCalls()
                .penaltyListener(strictModeExecutor, listener)
                .build()
        )
        StrictMode.setVmPolicy(
            StrictMode.VmPolicy.Builder()
                .detectActivityLeaks()
                .detectLeakedClosableObjects()
                .detectLeakedRegistrationObjects()
                .detectLeakedSqlLiteObjects()
                .detectCleartextNetwork()
                .penaltyListener(strictModeExecutor, vmListener)
                .build()
        )
        logger.info("STRICTMODE", "FORENSIC_POLICIES_ENABLED")
    }
}
