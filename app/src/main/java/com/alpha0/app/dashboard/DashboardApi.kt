package com.alpha0.app.dashboard

import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

class DashboardApi(private val baseUrl: String) {
    data class Device(
        val deviceId: String,
        val state: String,
        val platform: String,
        val fingerprint: String,
        val algorithm: String,
        val boundAt: String?,
        val lastSeenAt: String?,
        val securityStatus: String
    )

    data class Entitlement(
        val id: String,
        val gameId: String,
        val gameName: String,
        val platform: String,
        val status: String,
        val source: String,
        val validUntil: String
    )

    data class GameDetails(
        val id: String,
        val gameId: String,
        val gameName: String,
        val platform: String,
        val family: String,
        val versioning: String,
        val status: String,
        val source: String,
        val validFrom: String,
        val validUntil: String,
        val launcherSupported: Boolean,
        val interactionMode: String
    )

    data class DeviceActionResult(
        val deviceId: String? = null,
        val revoked: Boolean = false,
        val sessionToken: String? = null,
        val refreshToken: String? = null,
        val expiresAt: String? = null,
        val scopes: List<String> = emptyList()
    )

    sealed interface Result<out T> {
        data class Success<T>(val value: T) : Result<T>
        data class Failure(val message: String) : Result<Nothing>
    }

    fun getDevice(accessToken: String, deviceId: String): Result<Device> = request(accessToken, "/v1/devices/$deviceId") { json ->
        Device(
            deviceId = json.optString("device_id"),
            state = json.optString("state"),
            platform = json.optString("platform"),
            fingerprint = json.optString("fingerprint_sha256"),
            algorithm = json.optString("algorithm"),
            boundAt = json.optString("bound_at").takeIf { it.isNotBlank() },
            lastSeenAt = json.optString("last_seen_at").takeIf { it.isNotBlank() },
            securityStatus = json.optString("security_status")
        )
    }

    fun rotateDevice(accessToken: String, deviceId: String, platform: String, publicKeyDerB64: String, fingerprintSha256: String): Result<DeviceActionResult> = request(accessToken, "/v1/devices/$deviceId/rotate", "POST", JSONObject().apply {
        put("platform", platform)
        put("public_key_der_b64", publicKeyDerB64)
        put("fingerprint_sha256", fingerprintSha256)
    }) { json ->
        DeviceActionResult(
            deviceId = json.optString("device_id").takeIf { it.isNotBlank() },
            sessionToken = json.optString("session_token").takeIf { it.isNotBlank() },
            refreshToken = json.optString("refresh_token").takeIf { it.isNotBlank() },
            expiresAt = json.optString("expires_at").takeIf { it.isNotBlank() },
            scopes = json.optJSONArray("scopes")?.let { array ->
                buildList { for (index in 0 until array.length()) add(array.optString(index)) }
            } ?: emptyList()
        )
    }

    fun revokeDevice(accessToken: String, deviceId: String): Result<DeviceActionResult> = request(accessToken, "/v1/devices/$deviceId/revoke", "POST") {
        DeviceActionResult(revoked = it.optBoolean("revoked"))
    }

    fun getEntitlements(accessToken: String): Result<List<Entitlement>> = request(accessToken, "/v1/entitlements/me") { json ->
        val array = json.optJSONArray("entitlements") ?: JSONArray()
        buildList {
            for (index in 0 until array.length()) {
                val item = array.getJSONObject(index)
                add(
                    Entitlement(
                        id = item.optString("id"),
                        gameId = item.optString("game_id"),
                        gameName = item.optString("game_name"),
                        platform = item.optString("platform"),
                        status = item.optString("status"),
                        source = item.optString("source"),
                        validUntil = item.optString("valid_until")
                    )
                )
            }
        }
    }

    fun getEntitlement(accessToken: String, entitlementId: String): Result<GameDetails> = request(accessToken, "/v1/entitlements/$entitlementId") { json ->
        GameDetails(
            id = json.optString("id"),
            gameId = json.optString("game_id"),
            gameName = json.optString("game_name"),
            platform = json.optString("platform"),
            family = json.optString("family"),
            versioning = json.optString("versioning"),
            status = json.optString("status"),
            source = json.optString("source"),
            validFrom = json.optString("valid_from"),
            validUntil = json.optString("valid_until"),
            launcherSupported = json.optBoolean("launcher_supported"),
            interactionMode = json.optString("interaction_mode")
        )
    }

    private fun <T> request(accessToken: String, path: String, parser: (JSONObject) -> T): Result<T> = request(accessToken, path, "GET", null, parser)

    private fun <T> request(accessToken: String, path: String, method: String, body: JSONObject? = null, parser: (JSONObject) -> T): Result<T> {
        val connection = (URL("${baseUrl.trimEnd('/')}$path").openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 10_000
            readTimeout = 15_000
            setRequestProperty("Authorization", "Bearer $accessToken")
            setRequestProperty("Accept", "application/json")
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
            }
        }
        return try {
            if (body != null) {
                connection.outputStream.bufferedWriter().use { it.write(body.toString()) }
            }
            val status = connection.responseCode
            val bodyText = (if (status in 200..299) connection.inputStream else connection.errorStream)
                ?.bufferedReader()?.use { it.readText() }.orEmpty()
            val json = runCatching { JSONObject(bodyText) }.getOrNull()
            if (status in 200..299 && json != null) {
                Result.Success(parser(json))
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
