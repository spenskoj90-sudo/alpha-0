package com.alpha0.app.quality

import com.alpha0.app.diagnostics.DiagnosticLogger
import com.alpha0.app.net.HttpMethod
import com.alpha0.app.net.HttpRequest
import com.alpha0.app.net.HttpTransport
import com.alpha0.app.net.UrlConnectionHttpTransport
import org.json.JSONObject
import java.io.IOException

class QualityReportApi(
    private val baseUrl: String,
    private val diagnostics: DiagnosticLogger,
    private val transport: HttpTransport = UrlConnectionHttpTransport(),
) {
    data class SubmittedReport(
        val id: String,
        val status: String,
        val diagnosticsRetained: Boolean,
        val diagnosticsExpiresAt: String?,
        val requestId: String?,
    )

    sealed interface SubmitResult {
        data class Success(val value: SubmittedReport) : SubmitResult
        data class Failure(val code: String) : SubmitResult
    }

    fun submit(
        accessToken: String,
        category: String,
        title: String,
        description: String,
        diagnosticsConsent: Boolean,
        qualityProgramOptIn: Boolean,
        snapshot: DiagnosticLogger.TicketSnapshot?,
    ): SubmitResult {
        val correlationId = diagnostics.newCorrelationId()
        val started = System.nanoTime()
        diagnostics.info(
            "QUALITY",
            "REPORT_SUBMIT_START",
            requestId = correlationId,
            details = mapOf(
                "category" to category,
                "diagnostics_attached" to diagnosticsConsent,
                "quality_program_opt_in" to qualityProgramOptIn,
                "snapshot_events" to (snapshot?.eventCount ?: 0),
                "snapshot_bytes" to (snapshot?.encodedBytes ?: 0),
            )
        )
        return try {
            val normalizedBase = baseUrl.trim().trimEnd('/')
            val body = JSONObject().apply {
                put("category", category)
                put("title", title.trim())
                put("description", description.trim())
                put("diagnostics_consent", diagnosticsConsent)
                put("quality_program_opt_in", qualityProgramOptIn)
                if (diagnosticsConsent && snapshot != null) put("diagnostics", snapshot.json)
            }
            val response = transport.execute(
                HttpRequest(
                    method = HttpMethod.POST,
                    url = "$normalizedBase/v1/quality/reports",
                    headers = mapOf(
                        "Authorization" to "Bearer $accessToken",
                        "Accept" to "application/json",
                        "Content-Type" to "application/json",
                        "X-Request-ID" to correlationId,
                    ),
                    body = body.toString().toByteArray(Charsets.UTF_8),
                )
            )
            val durationMs = (System.nanoTime() - started) / 1_000_000
            val json = runCatching { JSONObject(response.body) }.getOrNull()
            if (response.status in 200..299 && json != null) {
                val report = json.optJSONObject("report") ?: JSONObject()
                val submitted = SubmittedReport(
                    id = report.optString("id"),
                    status = report.optString("status", "RECEIVED"),
                    diagnosticsRetained = report.optBoolean("diagnostics_retained", false),
                    diagnosticsExpiresAt = report.optString("diagnostics_expires_at").takeIf { it.isNotBlank() },
                    requestId = json.optString("request_id").takeIf { it.isNotBlank() },
                )
                diagnostics.info(
                    "QUALITY",
                    "REPORT_SUBMIT_SUCCESS",
                    requestId = correlationId,
                    durationMs = durationMs,
                    details = mapOf(
                        "diagnostics_retained" to submitted.diagnosticsRetained,
                        "status" to submitted.status,
                    )
                )
                SubmitResult.Success(submitted)
            } else {
                val code = json?.optString("code")?.takeIf { it.isNotBlank() } ?: "HTTP_${response.status}"
                diagnostics.warn(
                    "QUALITY",
                    "REPORT_SUBMIT_FAILURE",
                    requestId = correlationId,
                    errorCode = code,
                    durationMs = durationMs,
                    details = mapOf("http_status" to response.status),
                )
                SubmitResult.Failure(code)
            }
        } catch (_: IOException) {
            diagnostics.warn(
                "QUALITY",
                "REPORT_SUBMIT_FAILURE",
                requestId = correlationId,
                errorCode = "NETWORK_ERROR",
            )
            SubmitResult.Failure("NETWORK_ERROR")
        } catch (error: Exception) {
            diagnostics.error(
                "QUALITY",
                "REPORT_SUBMIT_FAILURE",
                requestId = correlationId,
                errorCode = "UNEXPECTED_ERROR",
                throwable = error,
            )
            SubmitResult.Failure("UNEXPECTED_ERROR")
        }
    }
}
