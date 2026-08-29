package com.alpha0.app.device

import android.content.Context
import com.alpha0.app.diagnostics.DiagnosticLogger
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

class DeviceApi(private val baseUrl: String) {
    data class BindResult(
        val deviceId: String,
        val state: String
    )

    sealed interface Result {
        data class Success(val value: BindResult) : Result
        data class Failure(val message: String) : Result
    }

    @Volatile
    private var diag: DiagnosticLogger? = null

    fun attachDiagnostics(context: Context) {
        diag = DiagnosticLogger.get(context)
    }

    fun bind(accessToken: String, platform: String, publicKeyDerB64: String, fingerprintSha256: String): Result {
        val t0 = System.currentTimeMillis()
        val normalizedBase = baseUrl.trim().trimEnd('/')
        val connection = (URL("$normalizedBase/v1/devices/bind").openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 10_000
            readTimeout = 15_000
            doOutput = true
            setRequestProperty("Authorization", "Bearer $accessToken")
            setRequestProperty("Content-Type", "application/json")
            setRequestProperty("Accept", "application/json")
        }
        return try {
            val payload = JSONObject().apply {
                put("platform", platform)
                put("public_key_der_b64", publicKeyDerB64)
                put("fingerprint_sha256", fingerprintSha256)
            }.toString()
            connection.outputStream.use { it.write(payload.toByteArray(Charsets.UTF_8)) }
            val status = connection.responseCode
            val body = (if (status in 200..299) connection.inputStream else connection.errorStream)
                ?.bufferedReader()?.use { it.readText() }.orEmpty()
            val json = runCatching { JSONObject(body) }.getOrNull()
            val duration = System.currentTimeMillis() - t0
            if (status in 200..299 && json != null) {
                val deviceId = json.optString("device_id")
                val state = json.optString("state")
                diag?.info(
                    "DEVICE", "BIND",
                    "SUCCESS",
                    durationMs = duration,
                    details = mapOf(
                        "state" to state,
                        "device_id_prefix" to deviceId.take(12),
                        "fingerprint_prefix" to fingerprintSha256.take(12)
                    )
                )
                Result.Success(BindResult(deviceId, state))
            } else {
                val code = json?.optString("code")?.takeIf { it.isNotBlank() } ?: "HTTP_$status"
                diag?.warn("DEVICE", "BIND", "FAILURE", errorCode = code, durationMs = duration)
                Result.Failure(code)
            }
        } catch (e: IOException) {
            val duration = System.currentTimeMillis() - t0
            diag?.error("DEVICE", "BIND", "FAILURE", errorCode = "NETWORK_ERROR", durationMs = duration, throwable = e)
            Result.Failure("NETWORK_ERROR: ${e.javaClass.simpleName}: ${e.message}")
        } catch (e: Exception) {
            val duration = System.currentTimeMillis() - t0
            diag?.error("DEVICE", "BIND", "FAILURE", errorCode = "UNEXPECTED_ERROR", durationMs = duration, throwable = e)
            Result.Failure("UNEXPECTED_ERROR: ${e.javaClass.simpleName}: ${e.message}")
        } finally {
            connection.disconnect()
        }
    }
}
