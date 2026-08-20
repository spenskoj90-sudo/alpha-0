package com.alpha0.app.device

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

    fun bind(accessToken: String, platform: String, publicKeyDerB64: String, fingerprintSha256: String): Result {
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
            if (status in 200..299 && json != null) {
                Result.Success(BindResult(json.optString("device_id"), json.optString("state")))
            } else {
                Result.Failure(json?.optString("code")?.takeIf { it.isNotBlank() } ?: "HTTP_$status")
            }
        } catch (e: IOException) {
            Result.Failure("NETWORK_ERROR: ${e.javaClass.simpleName}: ${e.message}")
        } catch (e: Exception) {
            Result.Failure("UNEXPECTED_ERROR: ${e.javaClass.simpleName}: ${e.message}")
        } finally {
            connection.disconnect()
        }
    }
}
