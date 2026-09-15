package com.alpha0.app.diagnostics

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.SystemClock
import android.util.Log
import androidx.core.content.FileProvider
import com.alpha0.app.BuildConfig
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.security.MessageDigest
import java.time.Instant
import java.util.Locale
import java.util.UUID
import java.util.concurrent.atomic.AtomicLong
import java.util.concurrent.locks.ReentrantLock
import java.util.zip.GZIPOutputStream
import kotlin.concurrent.withLock

/**
 * Bounded, structured diagnostics used by both physical acceptance and user tickets.
 *
 * There are deliberately two modes:
 * - FORENSIC_TEST: isolated physical-test APK, larger local ring and richer stack traces.
 * - PRODUCTION/DEVELOPMENT: privacy-bounded breadcrumbs suitable for an explicit
 *   user-submitted quality report snapshot.
 *
 * Hard security/privacy rules:
 * - never retain passwords, access/refresh/session tokens, JWTs, authorization headers,
 *   private keys, Play Integrity tokens, cookies, DATABASE_URL or API credentials;
 * - never capture screenshots, raw microphone/audio, WoW SavedVariables, chat text,
 *   network request/response bodies, or arbitrary user-entered form contents here;
 * - no automatic upload. Production diagnostics remain local until the user submits a
 *   report with diagnostic attachment enabled;
 * - request identifiers are one-way shortened with SHA-256;
 * - all files are bounded and stored in app-private storage.
 */
class DiagnosticLogger private constructor(private val context: Context) {

    data class TicketSnapshot(
        val json: JSONObject,
        val eventCount: Int,
        val encodedBytes: Int,
    )

    companion object {
        private const val TAG = "SentinelDiag"
        private const val LOG_DIR = "sentinel_diagnostics"
        private const val LOG_FILE = "sentinel_diag.jsonl"
        private const val EXPORT_FILE = "sentinel_forensic_diagnostics.jsonl.gz"
        private const val MAX_DETAIL_LEN = 1024
        private const val MAX_PRODUCTION_STACK_LEN = 4096
        private const val MAX_FORENSIC_STACK_LEN = 16384
        private const val MAX_TICKET_EVENTS = 600
        private const val MAX_TICKET_BYTES = 350 * 1024
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
            "nonce_raw", "challenge_raw", "cookie", "set-cookie", "savedvariables",
            "chat_text", "request_body", "response_body", "audio_bytes", "microphone_bytes"
        )

        fun isSensitiveDetailKey(raw: String): Boolean {
            val key = raw.lowercase(Locale.US)
            return SENSITIVE_KEYS.any { key.contains(it) }
        }

        /**
         * Scrub secret-like and common personally identifying fragments from free-form
         * exception/OS messages. Structured event details should still use opaque IDs.
         */
        fun sanitizeTextForDiagnostics(raw: String?, maxLen: Int = MAX_DETAIL_LEN): String {
            if (raw.isNullOrBlank()) return ""
            var value = raw.take(maxLen)
            value = value.replace(Regex("(?i)(bearer\\s+)[a-z0-9._~+\\-/]+"), "$1[REDACTED]")
            value = value.replace(
                Regex("(?i)(password|access_token|refresh_token|session_token|token|secret|api_key|authorization)[=:]\\s*\\S+"),
                "$1=[REDACTED]"
            )
            value = value.replace(
                Regex("eyJ[a-zA-Z0-9_-]{8,}\\.[a-zA-Z0-9_-]{8,}\\.[a-zA-Z0-9_-]{8,}"),
                "[REDACTED_JWT]"
            )
            value = value.replace(
                Regex("[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,128}\\.[A-Za-z]{2,24}"),
                "[REDACTED_EMAIL]"
            )
            value = value.replace(
                Regex("-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\\s\\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
                "[REDACTED_PRIVATE_KEY]"
            )
            return value
        }
    }

    private val mode = BuildConfig.SENTINEL_DIAGNOSTICS_MODE
    private val maxBytes = BuildConfig.SENTINEL_DIAGNOSTICS_MAX_BYTES.toLong().coerceAtLeast(64 * 1024L)
    private val sequence = AtomicLong(0)
    private val droppedEvents = AtomicLong(0)
    private val sessionId = UUID.randomUUID().toString()

    fun isForensicTest(): Boolean = mode == "FORENSIC_TEST"

    fun mode(): String = mode

    fun sessionId(): String = sessionId

    private fun logFile(): File {
        val dir = File(context.filesDir, LOG_DIR)
        if (!dir.exists()) dir.mkdirs()
        return File(dir, LOG_FILE)
    }

    /**
     * Emit one structured event. Callers must use stable component/event identifiers and
     * must never place arbitrary user-entered text or payloads in [details].
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
                put("ts", Instant.now().toString())
                put("elapsed_ms", SystemClock.elapsedRealtime())
                put("sequence", sequence.incrementAndGet())
                put("level", level.uppercase(Locale.US).take(16))
                put("component", component.take(64))
                put("event", event.take(96))
                put("result", result.uppercase(Locale.US).take(24))
                redactRequestId(requestId)?.let { put("request_id", it) }
                errorCode?.take(96)?.let { put("error_code", it) }
                durationMs?.coerceAtLeast(0)?.let { put("duration_ms", it) }
                if (details != null && details.isNotEmpty()) {
                    put("details", sanitizeDetails(details))
                }
                if (throwable != null) {
                    put("exception_class", throwable.javaClass.name.take(160))
                    put("exception_msg", sanitizeTextForDiagnostics(throwable.message, MAX_DETAIL_LEN))
                    val stackLimit = if (isForensicTest()) MAX_FORENSIC_STACK_LEN else MAX_PRODUCTION_STACK_LEN
                    put(
                        "exception_stack",
                        sanitizeTextForDiagnostics(throwable.stackTraceToString(), stackLimit)
                    )
                }
            }
            appendLine(obj.toString())
            when (level.uppercase(Locale.US)) {
                "ERROR" -> Log.e(TAG, "${component}/${event} $result ${errorCode ?: ""}")
                "WARN" -> Log.w(TAG, "${component}/${event} $result ${errorCode ?: ""}")
                "DEBUG" -> if (isForensicTest()) Log.d(TAG, "${component}/${event} $result")
                else -> Log.i(TAG, "${component}/${event} $result")
            }
        } catch (e: Exception) {
            Log.w(TAG, "diag write failed: ${e.javaClass.simpleName}")
        }
    }

    fun debug(component: String, event: String, result: String = "SUCCESS", details: Map<String, Any?>? = null) {
        if (isForensicTest()) event("DEBUG", component, event, result, details = details)
    }

    fun info(component: String, event: String, result: String = "SUCCESS", requestId: String? = null, durationMs: Long? = null, details: Map<String, Any?>? = null) =
        event("INFO", component, event, result, requestId, null, durationMs, details)

    fun warn(component: String, event: String, result: String = "FAILURE", requestId: String? = null, errorCode: String? = null, durationMs: Long? = null, details: Map<String, Any?>? = null) =
        event("WARN", component, event, result, requestId, errorCode, durationMs, details)

    fun error(component: String, event: String, result: String = "FAILURE", requestId: String? = null, errorCode: String? = null, durationMs: Long? = null, details: Map<String, Any?>? = null, throwable: Throwable? = null) =
        event("ERROR", component, event, result, requestId, errorCode, durationMs, details, throwable)

    private fun sanitizeDetails(raw: Map<String, Any?>): JSONObject {
        val out = JSONObject()
        for ((rawKey, value) in raw.entries.take(32)) {
            val key = rawKey.take(64)
            if (isSensitiveDetailKey(key)) {
                out.put(key, "[REDACTED]")
                continue
            }
            when (value) {
                null -> out.put(key, JSONObject.NULL)
                is Number, is Boolean -> out.put(key, value)
                else -> out.put(key, sanitizeTextForDiagnostics(value.toString(), MAX_DETAIL_LEN))
            }
        }
        return out
    }

    private fun appendLine(line: String) {
        val encodedBytes = line.toByteArray(Charsets.UTF_8).size + 1L
        lock.withLock {
            val file = logFile()
            if (file.exists() && file.length() + encodedBytes > maxBytes) {
                rotateDown(file)
            }
            file.appendText(line + "\n", Charsets.UTF_8)
            if (file.length() > maxBytes) {
                rotateDown(file)
            }
        }
    }

    private fun rotateDown(file: File) {
        try {
            val lines = file.readLines(Charsets.UTF_8)
            if (lines.isEmpty()) {
                file.writeText("", Charsets.UTF_8)
                return
            }
            var retained = lines.takeLast((lines.size / 2).coerceAtLeast(1))
            while (retained.joinToString("\n", postfix = "\n").toByteArray(Charsets.UTF_8).size > maxBytes / 2 && retained.size > 1) {
                retained = retained.drop(1)
            }
            droppedEvents.addAndGet((lines.size - retained.size).toLong())
            file.writeText(retained.joinToString("\n", postfix = "\n"), Charsets.UTF_8)
        } catch (_: Exception) {
            file.writeText("", Charsets.UTF_8)
            droppedEvents.incrementAndGet()
        }
    }

    /** Read current bounded log content for local forensic export/tests. */
    fun readAll(): String = lock.withLock {
        val file = logFile()
        if (!file.exists()) "" else file.readText(Charsets.UTF_8)
    }

    fun clear() = lock.withLock {
        val file = logFile()
        if (file.exists()) file.writeText("", Charsets.UTF_8)
        droppedEvents.set(0)
    }

    fun logFilePath(): String = logFile().absolutePath

    /**
     * Freeze a privacy-bounded snapshot of the already-recorded ring for a quality ticket.
     * The snapshot is deliberately capped below the server's 384 KiB hard limit.
     */
    fun createTicketSnapshot(maxEvents: Int = MAX_TICKET_EVENTS): TicketSnapshot {
        val events = lock.withLock {
            val file = logFile()
            if (!file.exists()) emptyList() else file.readLines(Charsets.UTF_8)
                .asSequence()
                .filter { it.isNotBlank() }
                .mapNotNull { runCatching { JSONObject(it) }.getOrNull() }
                .takeLast(maxEvents.coerceIn(1, MAX_TICKET_EVENTS))
                .toMutableList()
        }
        val root = JSONObject().apply {
            put("schema", "sentinel.diagnostic-snapshot.v1")
            put("mode", if (isForensicTest()) "FORENSIC_TEST" else "PRODUCTION")
            put("generated_at", Instant.now().toString())
            put("app_version", BuildConfig.VERSION_NAME.take(64))
            val sourceSha = BuildConfig.SENTINEL_SOURCE_SHA.trim()
            if (Regex("[0-9a-f]{40}").matches(sourceSha)) put("source_sha", sourceSha)
            put("build_type", BuildConfig.BUILD_TYPE.take(32))
            put("session_id", sessionId)
            put("dropped_events", droppedEvents.get())
            put("events", JSONArray(events))
        }
        while (root.toString().toByteArray(Charsets.UTF_8).size > MAX_TICKET_BYTES && events.size > 1) {
            events.removeAt(0)
            root.put("events", JSONArray(events))
            root.put("dropped_events", droppedEvents.get() + 1)
        }
        val bytes = root.toString().toByteArray(Charsets.UTF_8).size
        return TicketSnapshot(root, events.size, bytes)
    }

    /**
     * Physical-test/development-only full forensic export. Production builds cannot
     * invoke this path; production support data must flow through the reviewed ticket UI.
     */
    fun exportShare(activityContext: Context): Boolean {
        if (!BuildConfig.SENTINEL_DIAGNOSTICS_EXPORT_ENABLED) return false
        return try {
            val source = logFile()
            if (!source.exists() || source.length() == 0L) return false
            val export = File(source.parentFile, EXPORT_FILE)
            FileInputStream(source).use { input ->
                GZIPOutputStream(FileOutputStream(export)).use { output -> input.copyTo(output) }
            }
            val authority = "${BuildConfig.APPLICATION_ID}.diagnostics.files"
            val uri: Uri = FileProvider.getUriForFile(context, authority, export)
            val send = Intent(Intent.ACTION_SEND).apply {
                type = "application/gzip"
                putExtra(Intent.EXTRA_SUBJECT, "SENTINEL physical-test diagnostics")
                putExtra(Intent.EXTRA_STREAM, uri)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
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
