package com.sentinel.server

import com.sentinel.core.authorization.*
import com.sentinel.core.db.PostgresDataSourceFactory
import com.sentinel.core.device.*
import com.sentinel.core.session.*
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpServer
import java.net.InetSocketAddress
import java.nio.charset.StandardCharsets
import java.security.MessageDigest
import java.time.Duration
import java.time.Instant
import java.util.Base64
import java.util.concurrent.Executors

private const val MAX_TTL_SECONDS = 900L
private const val DEFAULT_TTL_SECONDS = 60L

fun main() {
    val env = System.getenv()
    val dataSource = PostgresDataSourceFactory.fromEnvironment(env)
    val deviceStore = JdbcDeviceRegistryStore(dataSource)
    val registry = DeviceRegistry(deviceStore)
    val challengeIssuer = JdbcChallengeIssuer(dataSource)
    val challengeStore: ChallengeStore = JdbcAtomicChallengeAuditStore(dataSource)
    val auditSink = challengeStore as com.sentinel.core.audit.AuditSink
    val verifier = BoundDeviceChallengeVerifier(registry, DeviceChallengeVerifier(challengeStore, auditSink))
    val sessions = SessionManager(JdbcSessionStore(dataSource))
    val rotator = SessionRotator(JdbcSessionStore(dataSource))
    val recovery = DeviceRecoveryService(deviceStore)
    val enrollmentToken = env["SENTINEL_ENROLLMENT_TOKEN"]?.takeIf { it.isNotBlank() }
        ?: error("Missing required environment variable: SENTINEL_ENROLLMENT_TOKEN")
    val allowedOperators = env["SENTINEL_OPERATOR_SUBJECTS"]
        ?.split(',')?.map(String::trim)?.filter(String::isNotBlank)?.toSet() ?: emptySet()
    val authorization = AuthorizationMiddleware(
        sessions,
        AuthorizationProfileStore { subject ->
            if (subject !in allowedOperators && "*" !in allowedOperators) return@AuthorizationProfileStore null
            AuthorizationProfile(
                roles = setOf("operator"), requiredRole = "operator", permissions = setOf("protected:read"),
                scope = ScopeRuleset(1, listOf(ScopeRule("protected", null, setOf("read")))),
                entitlement = Entitlement("sentinel-bootstrap", EntitlementStatus.ACTIVE, Instant.EPOCH, null),
                policy = Policy { true }
            )
        },
        auditSink = auditSink
    )

    val registrationLimiter = SlidingWindowRateLimiter(30, Duration.ofMinutes(1))
    val activationLimiter = SlidingWindowRateLimiter(20, Duration.ofMinutes(1))
    val recoveryLimiter = SlidingWindowRateLimiter(10, Duration.ofMinutes(1))
    val challengeIssueLimiter = SlidingWindowRateLimiter(60, Duration.ofMinutes(1))
    val challengeVerifyLimiter = SlidingWindowRateLimiter(60, Duration.ofMinutes(1))
    val sessionLimiter = SlidingWindowRateLimiter(60, Duration.ofMinutes(1))
    val protectedLimiter = SlidingWindowRateLimiter(120, Duration.ofMinutes(1))

    val server = HttpServer.create(
        InetSocketAddress(env["SENTINEL_BIND_HOST"] ?: "127.0.0.1", env["SENTINEL_PORT"]?.toIntOrNull() ?: 8080),
        64
    )
    server.createContext("/healthz") { exchange ->
        if (exchange.requestMethod != "GET") respond(exchange, 405, "{\"error\":\"method_not_allowed\"}")
        else respond(exchange, 200, "{\"status\":\"ok\"}")
    }
    server.createContext("/v1/devices/register") { exchange ->
        if (exchange.requestMethod != "POST") respond(exchange, 405, "{\"error\":\"method_not_allowed\"}")
        else if (!registrationLimiter.allow(clientRateLimitKey(exchange, "unknown"))) respond(exchange, 429, "{\"error\":\"rate_limited\"}")
        else runCatching {
            val form = readForm(exchange)
            val publicKey = Base64.getUrlDecoder().decode(form.required("publicKey"))
            val fingerprint = form.required("fingerprint")
            when (registry.registerPending(fingerprint, publicKey)) {
                is DeviceRegistryResult.Registered -> respond(exchange, 201, "{\"status\":\"pending\",\"fingerprint\":\"$fingerprint\"}")
                else -> respond(exchange, 409, "{\"error\":\"registration_rejected\"}")
            }
        }.onFailure { respond(exchange, 400, "{\"error\":\"bad_request\"}") }
    }
    server.createContext("/v1/devices/activate") { exchange ->
        if (exchange.requestMethod != "POST") respond(exchange, 405, "{\"error\":\"method_not_allowed\"}")
        else if (!activationLimiter.allow(clientRateLimitKey(exchange, "unknown"))) respond(exchange, 429, "{\"error\":\"rate_limited\"}")
        else if (!constantTimeEquals(exchange.requestHeaders.getFirst("X-Sentinel-Enrollment-Token"), enrollmentToken)) respond(exchange, 403, "{\"error\":\"forbidden\"}")
        else runCatching {
            when (registry.activate(readForm(exchange).required("fingerprint"))) {
                is DeviceRegistryResult.Activated -> respond(exchange, 200, "{\"status\":\"active\"}")
                else -> respond(exchange, 409, "{\"error\":\"activation_rejected\"}")
            }
        }.onFailure { respond(exchange, 400, "{\"error\":\"bad_request\"}") }
    }
    server.createContext("/v1/devices/recovery/issue") { exchange ->
        if (exchange.requestMethod != "POST") respond(exchange, 405, "{\"error\":\"method_not_allowed\"}")
        else if (!recoveryLimiter.allow(clientRateLimitKey(exchange, "unknown"))) respond(exchange, 429, "{\"error\":\"rate_limited\"}")
        else if (!constantTimeEquals(exchange.requestHeaders.getFirst("X-Sentinel-Enrollment-Token"), enrollmentToken)) respond(exchange, 403, "{\"error\":\"forbidden\"}")
        else runCatching {
            when (val result = recovery.issueCode(readForm(exchange).required("fingerprint"))) {
                is RecoveryResult.Issued -> respond(exchange, 201, "{\"code\":\"${result.code}\",\"expiresAt\":\"${result.expiresAt}\"}")
                else -> respond(exchange, 409, "{\"error\":\"recovery_unavailable\"}")
            }
        }.onFailure { respond(exchange, 400, "{\"error\":\"bad_request\"}") }
    }
    server.createContext("/v1/devices/recovery/rotate") { exchange ->
        if (exchange.requestMethod != "POST") respond(exchange, 405, "{\"error\":\"method_not_allowed\"}")
        else if (!recoveryLimiter.allow(clientRateLimitKey(exchange, "unknown"))) respond(exchange, 429, "{\"error\":\"rate_limited\"}")
        else runCatching {
            val form = readForm(exchange)
            val publicKey = Base64.getUrlDecoder().decode(form.required("publicKey"))
            when (recovery.rotateKey(form.required("fingerprint"), publicKey, form.required("recoveryCode"))) {
                RecoveryResult.Recovered -> respond(exchange, 200, "{\"status\":\"recovered\"}")
                else -> respond(exchange, 403, "{\"error\":\"recovery_rejected\"}")
            }
        }.onFailure { respond(exchange, 400, "{\"error\":\"bad_request\"}") }
    }
    server.createContext("/v1/challenges/issue") { exchange ->
        if (exchange.requestMethod != "POST") respond(exchange, 405, "{\"error\":\"method_not_allowed\"}")
        else if (!challengeIssueLimiter.allow(clientRateLimitKey(exchange, "unknown"))) respond(exchange, 429, "{\"error\":\"rate_limited\"}")
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
        else if (!challengeVerifyLimiter.allow(clientRateLimitKey(exchange, "unknown"))) respond(exchange, 429, "{\"error\":\"rate_limited\"}")
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
    server.createContext("/v1/sessions/rotate") { exchange ->
        if (exchange.requestMethod != "POST") respond(exchange, 405, "{\"error\":\"method_not_allowed\"}")
        else if (!sessionLimiter.allow(clientRateLimitKey(exchange, "unknown"))) respond(exchange, 429, "{\"error\":\"rate_limited\"}")
        else runCatching {
            val token = bearer(exchange) ?: return@runCatching respond(exchange, 401, "{\"error\":\"unauthorized\"}")
            when (val result = rotator.rotate(token, Duration.ofMinutes(30))) {
                is SessionRotationResult.Rotated -> respond(exchange, 200, "{\"sessionId\":\"${result.credential.sessionId}\",\"token\":\"${result.credential.token}\",\"expiresAt\":\"${result.credential.expiresAt}\"}")
                else -> respond(exchange, 401, "{\"error\":\"unauthorized\"}")
            }
        }.onFailure { respond(exchange, 400, "{\"error\":\"bad_request\"}") }
    }
    server.createContext("/v1/sessions/revoke") { exchange ->
        if (exchange.requestMethod != "POST") respond(exchange, 405, "{\"error\":\"method_not_allowed\"}")
        else if (!sessionLimiter.allow(clientRateLimitKey(exchange, "unknown"))) respond(exchange, 429, "{\"error\":\"rate_limited\"}")
        else runCatching {
            val token = bearer(exchange) ?: return@runCatching respond(exchange, 401, "{\"error\":\"unauthorized\"}")
            when (val auth = sessions.authenticate(token)) {
                is SessionResult.Authenticated -> respond(exchange, if (sessions.revoke(auth.sessionId)) 204 else 503, "")
                else -> respond(exchange, 401, "{\"error\":\"unauthorized\"}")
            }
        }.onFailure { respond(exchange, 400, "{\"error\":\"bad_request\"}") }
    }
    server.createContext("/v1/protected/ping") { exchange ->
        if (exchange.requestMethod != "GET") respond(exchange, 405, "{\"error\":\"method_not_allowed\"}")
        else if (!protectedLimiter.allow(clientRateLimitKey(exchange, "unknown"))) respond(exchange, 429, "{\"error\":\"rate_limited\"}")
        else when (val decision = authorization.authorize(bearer(exchange) ?: "", "read", Resource("protected", "ping"))) {
            is ProtectedAuthorizationResult.Allow -> respond(exchange, 200, "{\"status\":\"ok\",\"subject\":\"${decision.subjectId}\"}")
            is ProtectedAuthorizationResult.Deny -> respond(exchange, decision.status, "{\"error\":\"${decision.reason}\"}")
        }
    }
    server.executor = Executors.newFixedThreadPool(8)
    server.start()
    Runtime.getRuntime().addShutdownHook(Thread { server.stop(1) })
    println("SENTINEL server listening on ${env["SENTINEL_BIND_HOST"] ?: "127.0.0.1"}:${env["SENTINEL_PORT"] ?: "8080"}")
}

private fun bearer(exchange: HttpExchange): String? {
    val value = exchange.requestHeaders.getFirst("Authorization") ?: return null
    if (!value.startsWith("Bearer ")) return null
    val token = value.removePrefix("Bearer ").trim()
    return token.takeIf { it.isNotBlank() && it.length <= 256 }
}

private fun constantTimeEquals(left: String?, right: String): Boolean =
    left != null && MessageDigest.isEqual(left.toByteArray(StandardCharsets.UTF_8), right.toByteArray(StandardCharsets.UTF_8))

private fun respond(exchange: HttpExchange, status: Int, body: String) {
    val bytes = body.toByteArray(StandardCharsets.UTF_8)
    exchange.responseHeaders.set("Content-Type", "application/json; charset=utf-8")
    exchange.responseHeaders.set("Cache-Control", "no-store")
    exchange.responseHeaders.set("X-Content-Type-Options", "nosniff")
    exchange.responseHeaders.set("X-Frame-Options", "DENY")
    exchange.responseHeaders.set("Referrer-Policy", "no-referrer")
    exchange.responseHeaders.set("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    exchange.sendResponseHeaders(status, if (status == 204) -1 else bytes.size.toLong())
    if (status != 204) exchange.responseBody.use { it.write(bytes) } else exchange.close()
}
