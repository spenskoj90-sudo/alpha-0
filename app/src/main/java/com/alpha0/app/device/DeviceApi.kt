package com.alpha0.app.device

import android.content.Context
import com.alpha0.app.diagnostics.DiagnosticLogger
import com.alpha0.app.security.DeviceIdentity
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.util.Base64
import java.util.UUID

class DeviceApi(private val baseUrl: String) {
    data class BindResult(
        val deviceId: String,
        val state: String,
        val challenge: String,
    )

    data class ProvenSession(
        val deviceId: String,
        val accessToken: String,
        val refreshToken: String,
        val scopes: List<String>,
    )

    sealed interface Result {
        data class Success(val value: BindResult) : Result
        data class Failure(val message: String) : Result
    }

    sealed interface ChallengeResult {
        data class Success(val challenge: String) : ChallengeResult
        data class Failure(val message: String) : ChallengeResult
    }

    sealed interface ProofResult {
        data class Success(val value: ProvenSession) : ProofResult
        data class Failure(val message: String) : ProofResult
    }

    @Volatile
    private var diag: DiagnosticLogger? = null

    fun attachDiagnostics(context: Context) {
        diag = DiagnosticLogger.get(context)
    }

    fun bind(accessToken: String, platform: String, publicKeyDerB64: String, fingerprintSha256: String): Result {
        require(accessToken.isNotBlank()) { "accessToken must not be blank" }
        val t0 = System.currentTimeMillis()
        val connection = openJsonConnection("/v1/devices/bind", accessToken)
        return try {
            val payload = JSONObject().apply {
                put("platform", platform)
                put("public_key_der_b64", publicKeyDerB64)
                put("fingerprint_sha256", fingerprintSha256)
            }.toString()
            connection.outputStream.use { it.write(payload.toByteArray(Charsets.UTF_8)) }
            val response = readJsonResponse(connection)
            val duration = System.currentTimeMillis() - t0
            if (response.status in 200..299 && response.json != null) {
                val deviceId = response.json.optString("device_id")
                val state = response.json.optString("state")
                val challenge = response.json.optString("challenge")
                if (deviceId.isBlank() || state.isBlank() || challenge.isBlank()) {
                    diag?.warn("DEVICE", "BIND", "FAILURE", errorCode = "DEVICE_BIND_RESPONSE_INVALID", durationMs = duration)
                    return Result.Failure("DEVICE_BIND_RESPONSE_INVALID")
                }
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
                Result.Success(BindResult(deviceId, state, challenge))
            } else {
                val code = response.errorCode()
                diag?.warn("DEVICE", "BIND", "FAILURE", errorCode = code, durationMs = duration)
                Result.Failure(code)
            }
        } catch (e: IOException) {
            val duration = System.currentTimeMillis() - t0
            diag?.error("DEVICE", "BIND", "FAILURE", errorCode = "NETWORK_ERROR", durationMs = duration, throwable = e)
            Result.Failure("NETWORK_ERROR")
        } catch (e: Exception) {
            val duration = System.currentTimeMillis() - t0
            diag?.error("DEVICE", "BIND", "FAILURE", errorCode = "UNEXPECTED_ERROR", durationMs = duration, throwable = e)
            Result.Failure("UNEXPECTED_ERROR")
        } finally {
            connection.disconnect()
        }
    }

    fun challenge(accessToken: String, deviceId: String): ChallengeResult {
        require(accessToken.isNotBlank()) { "accessToken must not be blank" }
        require(deviceId.isNotBlank()) { "deviceId must not be blank" }
        val t0 = System.currentTimeMillis()
        val connection = openJsonConnection("/v1/devices/$deviceId/challenge", accessToken)
        return try {
            connection.outputStream.use { it.write("{}".toByteArray(Charsets.UTF_8)) }
            val response = readJsonResponse(connection)
            val duration = System.currentTimeMillis() - t0
            if (response.status in 200..299 && response.json != null) {
                val challenge = response.json.optString("challenge")
                if (challenge.isBlank()) {
                    diag?.warn("DEVICE", "CHALLENGE", "FAILURE", errorCode = "DEVICE_CHALLENGE_RESPONSE_INVALID", durationMs = duration)
                    return ChallengeResult.Failure("DEVICE_CHALLENGE_RESPONSE_INVALID")
                }
                diag?.info("DEVICE", "CHALLENGE", "SUCCESS", durationMs = duration, details = mapOf("device_id_prefix" to deviceId.take(12)))
                ChallengeResult.Success(challenge)
            } else {
                val code = response.errorCode()
                diag?.warn("DEVICE", "CHALLENGE", "FAILURE", errorCode = code, durationMs = duration)
                ChallengeResult.Failure(code)
            }
        } catch (e: IOException) {
            val duration = System.currentTimeMillis() - t0
            diag?.error("DEVICE", "CHALLENGE", "FAILURE", errorCode = "NETWORK_ERROR", durationMs = duration, throwable = e)
            ChallengeResult.Failure("NETWORK_ERROR")
        } catch (e: Exception) {
            val duration = System.currentTimeMillis() - t0
            diag?.error("DEVICE", "CHALLENGE", "FAILURE", errorCode = "UNEXPECTED_ERROR", durationMs = duration, throwable = e)
            ChallengeResult.Failure("UNEXPECTED_ERROR")
        } finally {
            connection.disconnect()
        }
    }

    fun prove(deviceId: String, challenge: String, deviceIdentity: DeviceIdentity): ProofResult {
        require(deviceId.isNotBlank()) { "deviceId must not be blank" }
        require(challenge.isNotBlank()) { "challenge must not be blank" }
        val t0 = System.currentTimeMillis()
        val timestamp = System.currentTimeMillis() / 1000L
        val requestId = UUID.randomUUID().toString()
        val signedPayload = canonicalProofPayload(challenge, timestamp, requestId)
        val signature = Base64.getEncoder().encodeToString(deviceIdentity.sign(signedPayload))
        val connection = openJsonConnection("/v1/devices/$deviceId/prove")
        return try {
            val payload = JSONObject().apply {
                put("challenge", challenge)
                put("timestamp", timestamp)
                put("request_id", requestId)
                put("signature_b64", signature)
            }.toString()
            connection.outputStream.use { it.write(payload.toByteArray(Charsets.UTF_8)) }
            val response = readJsonResponse(connection)
            val duration = System.currentTimeMillis() - t0
            if (response.status in 200..299 && response.json != null) {
                val access = response.json.optString("session_token")
                val refresh = response.json.optString("refresh_token")
                if (access.isBlank() || refresh.isBlank()) {
                    diag?.warn("DEVICE", "PROVE", "FAILURE", errorCode = "DEVICE_PROOF_RESPONSE_INVALID", durationMs = duration)
                    return ProofResult.Failure("DEVICE_PROOF_RESPONSE_INVALID")
                }
                val scopesJson = response.json.optJSONArray("scopes")
                val scopes = buildList {
                    if (scopesJson != null) for (index in 0 until scopesJson.length()) {
                        add(scopesJson.getString(index))
                    }
                }
                diag?.info(
                    "DEVICE", "PROVE", "SUCCESS",
                    durationMs = duration,
                    details = mapOf("device_id_prefix" to deviceId.take(12), "scopes_count" to scopes.size)
                )
                ProofResult.Success(ProvenSession(deviceId, access, refresh, scopes))
            } else {
                val code = response.errorCode()
                diag?.warn("DEVICE", "PROVE", "FAILURE", errorCode = code, durationMs = duration)
                ProofResult.Failure(code)
            }
        } catch (e: IOException) {
            val duration = System.currentTimeMillis() - t0
            diag?.error("DEVICE", "PROVE", "FAILURE", errorCode = "NETWORK_ERROR", durationMs = duration, throwable = e)
            ProofResult.Failure("NETWORK_ERROR")
        } catch (e: Exception) {
            val duration = System.currentTimeMillis() - t0
            diag?.error("DEVICE", "PROVE", "FAILURE", errorCode = "UNEXPECTED_ERROR", durationMs = duration, throwable = e)
            ProofResult.Failure("UNEXPECTED_ERROR")
        } finally {
            connection.disconnect()
        }
    }

    private data class JsonResponse(val status: Int, val json: JSONObject?) {
        fun errorCode(): String = json?.optString("code")?.takeIf { it.isNotBlank() } ?: "HTTP_$status"
    }

    private fun openJsonConnection(path: String, accessToken: String? = null): HttpURLConnection {
        val normalizedBase = baseUrl.trim().trimEnd('/')
        return (URL("$normalizedBase$path").openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 10_000
            readTimeout = 15_000
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
            setRequestProperty("Accept", "application/json")
            if (!accessToken.isNullOrBlank()) {
                setRequestProperty("Authorization", "Bearer $accessToken")
            }
        }
    }

    private fun readJsonResponse(connection: HttpURLConnection): JsonResponse {
        val status = connection.responseCode
        val body = (if (status in 200..299) connection.inputStream else connection.errorStream)
            ?.bufferedReader()?.use { it.readText() }.orEmpty()
        return JsonResponse(status, runCatching { JSONObject(body) }.getOrNull())
    }

    companion object {
        internal fun canonicalProofPayload(challenge: String, timestamp: Long, requestId: String): ByteArray {
            require(challenge.isNotBlank()) { "challenge must not be blank" }
            require(requestId.isNotBlank()) { "requestId must not be blank" }
            val canonical = buildString {
                append("{\"challenge\":")
                append(JSONObject.quote(challenge))
                append(",\"request_id\":")
                append(JSONObject.quote(requestId))
                append(",\"timestamp\":")
                append(timestamp)
                append('}')
            }
            return canonical.toByteArray(Charsets.UTF_8)
        }
    }
}
