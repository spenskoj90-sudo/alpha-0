package com.sentinel.server

import com.sentinel.core.audit.JdbcAuditSink
import com.sentinel.core.db.PostgresDataSourceFactory
import com.sentinel.core.device.BoundDeviceChallengeVerifier
import com.sentinel.core.device.DeviceChallengeVerifier
import com.sentinel.core.device.DeviceRegistry
import com.sentinel.core.device.IssuedDeviceChallenge
import com.sentinel.core.device.JdbcChallengeIssuer
import com.sentinel.core.device.JdbcChallengeStore
import com.sentinel.core.device.JdbcDeviceRegistryStore
import com.sentinel.core.device.PresentedDeviceProof
import com.sentinel.core.device.DeviceRegistryResult
import com.sentinel.core.device.DeviceVerificationResult
import com.sentinel.core.session.JdbcSessionStore
import com.sentinel.core.session.SessionManager
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpServer
import java.net.InetSocketAddress
import java.net.URLDecoder
import java.nio.charset.StandardCharsets
import java.security.MessageDigest
import java.time.Duration
import java.time.Instant
import java.util.Base64
import java.util.concurrent.Executors

private const val MAX_BODY_BYTES = 16 * 1024
private const val MAX_TTL_SECONDS = 900L
private const val DEFAULT_TTL_SECONDS = 60L

fun main() {
    val env = System.getenv()
    val dataSource = PostgresDataSourceFactory.fromEnvironment(env)
    val registry = DeviceRegistry(JdbcDeviceRegistryStore(dataSource))
    val challengeIssuer = JdbcChallengeIssuer(dataSource)
    val challengeStore = JdbcChallengeStore(dataSource)
    val audit = JdbcAuditSink(dataSource)
    val verifier = BoundDeviceChallengeVerifier(registry, DeviceChallengeVerifier(challengeStore, audit))
    val sessions = SessionManager(JdbcSessionStore(dataSource))
    val enrollmentToken = env["SENTINEL_ENROLLMENT_TOKEN"]?.takeIf { it.isNotBlank() }
        ?: error("Missing required environment variable: SENTINEL_ENROLLMENT_TOKEN")

    val server = HttpServer.create(InetSocketAddress(env["SENTINEL_BIND_HOST"] ?: "127.0.0.1", env["SENTINEL_PORT"]?.toIntOrNull() ?: 8080), 64)
    server.createContext("/healthz") { exchange ->
        if (exchange.requestMethod != "GET") respond(exchange, 405, "{\"error\":\"method_not_allowed\"}")
        else respond(exchange, 200, "{\"status\":\"ok\"}")
    }
    server.createContext("/v1/devices/register") { exchange ->
        if (exchange.requestMethod != "POST") respond(exchange, 405, "{\"error\":\"method_not_allowed\"}")
        else runCatching {
            val form = readForm(exchange)
            val publicKey = Base64.getUrlDecoder().decode(form.required("publicKey"))
            val fingerprint = form.required("fingerprint")
            when (registry.registerPending(fingerprint, publicKey)) {
                is DeviceRegistryResult.Registered -> respond(exchange, 201, "{\"status\":\"pending\",\"fingerprint\":\"$fingerprint\"}")
                is DeviceRegistryResult.Rejected -> respond(exchange, 409, "{\"error\":\"registration_rejected\"}")
                else -> respond(exchange, 500, "{\"error\":\"unexpected_state\"}")
            }
        }.onFailure { respond(exchange, 400, "{\"error\":\"bad_request\"}") }
    }
    server.createContext("/v1/devices/activate") { exchange ->
        if (exchange.requestMethod != "POST") respond(exchange, 405, "{\"error\":\"method_not_allowed\"}")
        else if (!constantTimeEquals(exchange.requestHeaders.getFirst("X-Sentinel-Enrollment-Token"), enrollmentToken)) {
            respond(exchange, 403, "{\"error\":\"forbidden\"}")
        } else runCatching {
            val fingerprint = readForm(exchange).required("fingerprint")
            when (registry.activate(fingerprint)) {
                is DeviceRegistryResult.Activated -> respond(exchange, 200, "{\"status\":\"active\",\"fingerprint\":\"$fingerprint\"}")
                else -> respond(exchange, 409, "{\"error\":\"activation_rejected\"}")
            }
        }.onFailure { respond(exchange, 400, "{\"error\":\"bad_request\"}") }
    }
    server.createContext("/v1/challenges/issue") { exchange ->
        if (exchange.requestMethod != "POST") respond(exchange, 405, "{\"error\":\"method_not_allowed\"}")
        else runCatching {
            val form = readForm(exchange)
            val fingerprint = form.required("fingerprint")
            if (!registry.isActive(fingerprint)) return@runCatching respond(exchange, 403, "{\"error\":\"forbidden\"}")
            val ttl = form["ttlSeconds"]?.toLongOrNull() ?: DEFAULT_TTL_SECONDS
            if (ttl !in 1..MAX_TTL_SECONDS) return@runCatching respond(exchange, 400, "{\"error\":\"invalid_ttl\"}")
            val challenge = challengeIssuer.issue(fingerprint, Instant.now().plusSeconds(ttl))
                ?: return@runCatching respond(exchange, 503, "{\"error\":\"challenge_unavailable\"}")
            val nonce = Base64.getUrlEncoder().withoutPadding().encodeToString(challenge.nonce)
            respond(exchange, 201, "{\"challengeId\":\"${challenge.id}\",\"nonce\":\"$nonce\",\"expiresAt\":\"${challenge.expiresAt}\"}")
        }.onFailure { respond(exchange, 400, "{\"error\":\"bad_request\"}") }
    }
    server.createContext("/v1/challenges/verify") { exchange ->
        if (exchange.requestMethod != "POST") respond(exchange, 405, "{\"error\":\"method_not_allowed\"}")
        else runCatching {
            val form = readForm(exchange)
            val proof = PresentedDeviceProof(
                form.required("challengeId"),
                Base64.getUrlDecoder().decode(form.required("publicKey")),
                Base64.getUrlDecoder().decode(form.required("signature"))
            )
            when (val result = verifier.verify(proof)) {
                is DeviceVerificationResult.Verified -> {
                    val credential = sessions.issue(result.fingerprint, Duration.ofMinutes(30))
                        ?: return@runCatching respond(exchange, 503, "{\"error\":\"session_unavailable\"}")
                    respond(exchange, 200, "{\"sessionId\":\"${credential.sessionId}\",\"token\":\"${credential.token}\",\"expiresAt\":\"${credential.expiresAt}\"}")
                }
                is DeviceVerificationResult.Rejected -> respond(exchange, 401, "{\"error\":\"authentication_failed\"}")
            }
        }.onFailure { respond(exchange, 400, "{\"error\":\"bad_request\"}") }
    }
    server.createContext("/v1/sessions/revoke") { exchange ->
        if (exchange.requestMethod != "POST") respond(exchange, 405, "{\"error\":\"method_not_allowed\"}")
        else runCatching {
            val authorization = exchange.requestHeaders.getFirst("Authorization") ?: ""
            if (!authorization.startsWith("Bearer ")) return@runCatching respond(exchange, 401, "{\"error\":\"unauthorized\"}")
            val token = authorization.removePrefix("Bearer ")
            when (val auth = sessions.authenticate(token)) {
                is com.sentinel.core.session.SessionResult.Authenticated -> {
                    respond(exchange, if (sessions.revoke(auth.sessionId)) 204 else 503, "")
                }
                else -> respond(exchange, 401, "{\"error\":\"unauthorized\"}")
            }
        }.onFailure { respond(exchange, 400, "{\"error\":\"bad_request\"}") }
    }

    server.executor = Executors.newFixedThreadPool(8)
    server.start()
    println("SENTINEL server listening on ${env["SENTINEL_BIND_HOST"] ?: "127.0.0.1"}:${env["SENTINEL_PORT"] ?: "8080"}")
}

private fun readForm(exchange: HttpExchange): Map<String, String> {
    val length = exchange.requestHeaders.getFirst("Content-Length")?.toLongOrNull()
    require(length == null || length in 1..MAX_BODY_BYTES)
    val bytes = exchange.requestBody.use { it.readNBytes(MAX_BODY_BYTES + 1) }
    require(bytes.size <= MAX_BODY_BYTES)
    val body = bytes.toString(StandardCharsets.UTF_8)
    return body.split('&').filter { it.isNotEmpty() }.associate {
        val parts = it.split('=', limit = 2)
        require(parts.size == 2)
        URLDecoder.decode(parts[0], "UTF-8") to URLDecoder.decode(parts[1], "UTF-8")
    }
}

private fun Map<String, String>.required(name: String): String =
    this[name]?.takeIf { it.isNotBlank() && it.length <= 4096 } ?: error("missing field")

private fun constantTimeEquals(left: String?, right: String): Boolean =
    left != null && MessageDigest.isEqual(left.toByteArray(StandardCharsets.UTF_8), right.toByteArray(StandardCharsets.UTF_8))

private fun respond(exchange: HttpExchange, status: Int, body: String) {
    val bytes = body.toByteArray(StandardCharsets.UTF_8)
    exchange.responseHeaders.set("Content-Type", "application/json; charset=utf-8")
    exchange.responseHeaders.set("Cache-Control", "no-store")
    exchange.sendResponseHeaders(status, if (status == 204) -1 else bytes.size.toLong())
    if (status != 204) exchange.responseBody.use { it.write(bytes) } else exchange.close()
}
