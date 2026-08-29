package com.alpha0.app.diagnostics

import android.content.Context
import android.content.Intent
import android.util.Log
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.UUID
import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

/**
 * Bounded, structured diagnostic logger for physical-device acceptance.
 *
 * Security rules (hard):
 * - Never log private keys, passwords, access/refresh tokens, JWTs,
 *   raw Play Integrity tokens, Google credentials, DATABASE_URL,
 *   session secrets, keystore passwords, or full sensitive identifiers.
 * - request_id is stored only as a short SHA-256 prefix (redacted).
 * - No network telemetry; export is local share Intent only.
 * - Safe for release builds; no debug bypass of security controls.
 */
class DiagnosticLogger private constructor(private val context: Context) {

    companion object {
        private const val TAG = "SentinelDiag"
        private const val LOG_DIR = "sentinel_diagnostics"
        private const val LOG_FILE = "sentinel_diag.jsonl"
        private const val MAX_BYTES = 512 * 1024 // 512 KiB hard bound
        private const val MAX_DETAIL_LEN = 512
        private val lock = ReentrantLock()
        @Volatile private var instance: DiagnosticLogger? = null

        fun get(context: Context): DiagnosticLogger {
            val app = context.applicationContext
            return instance ?: lock.withLock {
                instance ?: DiagnosticLogger(app).also { instance = it }
            }
        }

        /** Redact a request id to a short, non-reversible prefix. */
        fun redactRequestId(raw: String?): String? {
            if (raw.isNullOrBlank()) return null
            return try {
                val dig = MessageDigest.getInstance("SHA-256")
                    .digest(raw.toByteArray(Charsets.UTF_8))
                dig.take(6).joinToString("") { b -> "%02x".format(b) }
            } catch (_: Exception) {
                "redacted"
            }
        }

        private val SENSITIVE_KEYS = setOf(
            "password", "token", "access_token", "refresh_token", "session_token",
            "jwt", "authorization", "secret", "keystore", "private_key", "credential",
            "database_url", "api_key", "integrity_token", "play_integrity_token",
            "nonce_raw", "challenge_raw"
        )
    }

    private val isoFmt = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US).apply {
        timeZone = java.util.TimeZone.getTimeZone("UTC")
    }

    private fun logFile(): File {
        val dir = File(context.filesDir, LOG_DIR)
        if (!dir.exists()) dir.mkdirs()
        return File(dir, LOG_FILE)
    }

    /**
     * Emit one structured event.
     * @param level INFO|WARN|ERROR|DEBUG
     * @param component logical area (e.g. APP, KEYSTORE, DEVICE, AUTH, INTEGRITY, SESSION, API)
     * @param event short event name (e.g. APP_START, KEY_GEN, BIND_RESULT)
     * @param result SUCCESS|FAILURE|SKIPPED|UNKNOWN
     * @param requestId optional; will be redacted
     * @param errorCode optional safe code
     * @param durationMs optional
     * @param details optional map; sensitive keys stripped / values truncated
     */
    fun event(
        level: String,
        component: String,
        event: String,
        result: String = "UNKNOWN",
        requestId: String? = null,
        errorCode: String? = null,
        durationMs: Long? = null,
        details: Map<String, Any?>? = null,
        throwable: Throwable? = null
    ) {
        try {
            val obj = JSONObject().apply {
                put("ts", isoFmt.format(Date()))
                put("level", level.uppercase(Locale.US).take(16))
                put("component", component.take(64))
                put("event", event.take(64))
                put("result", result.uppercase(Locale.US).take(16))
                redactRequestId(requestId)?.let { put("request_id", it) }
                errorCode?.take(64)?.let { put("error_code", it) }
                durationMs?.let { put("duration_ms", it) }
                if (details != null && details.isNotEmpty()) {
                    put("details", sanitizeDetails(details))
                }
                if (throwable != null) {
                    put("exception_class", throwable.javaClass.simpleName.take(128))
                    put("exception_msg", safeMessage(throwable.message))
                }
            }
            appendLine(obj.toString())
            // Also mirror to logcat at a safe level (no secrets by construction)
            when (level.uppercase(Locale.US)) {
                "ERROR" -> Log.e(TAG, "${component}/${event} $result ${errorCode ?: ""}")
                "WARN" -> Log.w(TAG, "${component}/${event} $result ${errorCode ?: ""}")
                else -> Log.i(TAG, "${component}/${event} $result")
            }
        } catch (e: Exception) {
            Log.w(TAG, "diag write failed: ${e.javaClass.simpleName}")
        }
    }

    fun info(component: String, event: String, result: String = "SUCCESS", requestId: String? = null, durationMs: Long? = null, details: Map<String, Any?>? = null) =
        event("INFO", component, event, result, requestId, null, durationMs, details)

    fun warn(component: String, event: String, result: String = "FAILURE", requestId: String? = null, errorCode: String? = null, durationMs: Long? = null, details: Map<String, Any?>? = null) =
        event("WARN", component, event, result, requestId, errorCode, durationMs, details)

    fun error(component: String, event: String, result: String = "FAILURE", requestId: String? = null, errorCode: String? = null, durationMs: Long? = null, details: Map<String, Any?>? = null, throwable: Throwable? = null) =
        event("ERROR", component, event, result, requestId, errorCode, durationMs, details, throwable)

    private fun sanitizeDetails(raw: Map<String, Any?>): JSONObject {
        val out = JSONObject()
        for ((k, v) in raw) {
            val key = k.lowercase(Locale.US)
            if (SENSITIVE_KEYS.any { key.contains(it) }) {
                out.put(k, "[REDACTED]")
                continue
            }
            when (v) {
                null -> out.put(k, JSONObject.NULL)
                is Number, is Boolean -> out.put(k, v)
                else -> {
                    val s = v.toString()
                    out.put(k, if (s.length > MAX_DETAIL_LEN) s.take(MAX_DETAIL_LEN) + "…" else s)
                }
            }
        }
        return out
    }

    private fun safeMessage(msg: String?): String {
        if (msg.isNullOrBlank()) return ""
        var s = msg.take(MAX_DETAIL_LEN)
        // crude token-like scrub
        s = s.replace(Regex("(?i)(bearer\\s+)[a-z0-9._\\-]+"), "$1[REDACTED]")
        s = s.replace(Regex("(?i)(password|token|secret)[=:]\\s*\\S+"), "$1=[REDACTED]")
        return s
    }

    private fun appendLine(line: String) {
        lock.withLock {
            val file = logFile()
            // Bound size: if over limit, truncate to last ~half
            if (file.exists() && file.length() > MAX_BYTES) {
                rotateDown(file)
            }
            file.appendText(line + "\n", Charsets.UTF_8)
        }
    }

    private fun rotateDown(file: File) {
        try {
            val text = file.readText(Charsets.UTF_8)
            val keepFrom = (text.length / 2).coerceAtLeast(0)
            val idx = text.indexOf('\n', keepFrom).let { if (it < 0) keepFrom else it + 1 }
            file.writeText(text.substring(idx.coerceAtMost(text.length)), Charsets.UTF_8)
        } catch (_: Exception) {
            file.writeText("", Charsets.UTF_8)
        }
    }

    /** Read current log content (for tests / export). */
    fun readAll(): String = lock.withLock {
        val f = logFile()
        if (!f.exists()) "" else f.readText(Charsets.UTF_8)
    }

    fun clear() = lock.withLock {
        val f = logFile()
        if (f.exists()) f.writeText("", Charsets.UTF_8)
    }

    fun logFilePath(): String = logFile().absolutePath

    /**
     * Export diagnostic log via system share sheet (local only).
     * Returns true if Intent was launched.
     */
    fun exportShare(activityContext: Context): Boolean {
        return try {
            val content = readAll()
            if (content.isBlank()) {
                Log.i(TAG, "export: empty log")
                return false
            }
            val send = Intent(Intent.ACTION_SEND).apply {
                type = "text/plain"
                putExtra(Intent.EXTRA_SUBJECT, "SENTINEL diagnostic log")
                putExtra(Intent.EXTRA_TEXT, content)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            activityContext.startActivity(Intent.createChooser(send, "Export SENTINEL diagnostics"))
            true
        } catch (e: Exception) {
            Log.w(TAG, "export failed: ${e.javaClass.simpleName}")
            false
        }
    }

    /** Generate a correlation id for a local operation chain (not a server secret). */
    fun newCorrelationId(): String = UUID.randomUUID().toString()
}
