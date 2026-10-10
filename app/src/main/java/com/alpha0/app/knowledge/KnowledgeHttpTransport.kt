package com.alpha0.app.knowledge

import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URI
import java.net.URLEncoder
import java.util.UUID
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.ExecutionException
import java.util.concurrent.ThreadPoolExecutor
import java.util.concurrent.TimeUnit
import java.util.concurrent.TimeoutException
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference
import org.json.JSONObject
import com.alpha0.app.net.CoreRefreshSerialization

/** Principal and tokens stay inside the service-owned broker; never UI assertions. */
internal data class KnowledgeSessionSnapshot(val origin: String, val sessionId: String, val accessToken: String, val refreshToken: String)
internal interface KnowledgeSessionBroker {
    val origin: String
    fun snapshot(): KnowledgeSessionSnapshot?
    fun rotate(expected: KnowledgeSessionSnapshot, access: String, refresh: String): Boolean
    fun invalidate(expected: KnowledgeSessionSnapshot): Boolean
}

/** A bounded worker also puts DNS, refresh and streamed reads inside the caller's
 * single monotonic budget. Unknown one-use rotation invalidates only its old
 * principal; it is never retried or allowed to overwrite a later login. */
internal class KnowledgeHttpTransport(private val broker: KnowledgeSessionBroker) : KnowledgeDistributionTransport, AutoCloseable {
    private val origin = broker.origin.removeSuffix("/")
    private val closed = AtomicBoolean(false)
    private val rotation = AtomicReference<KnowledgeSessionSnapshot?>()
    private val worker = ThreadPoolExecutor(1, 1, 0, TimeUnit.MILLISECONDS, ArrayBlockingQueue(1),
        { job -> Thread(job, "sentinel-knowledge-http").apply { isDaemon = true } }, ThreadPoolExecutor.AbortPolicy())
    init {
        val parsed = URI(origin)
        require(parsed.rawUserInfo == null && parsed.rawQuery == null && parsed.rawFragment == null &&
            parsed.rawPath.orEmpty().isEmpty() && parsed.host != null &&
            (parsed.scheme == "https" || parsed.scheme == "http" && parsed.host in setOf("127.0.0.1", "localhost", "[::1]", "::1")))
    }
    private fun query(profile: KnowledgeProfile, extra: Map<String, String?> = emptyMap()): String =
        (profile.values() + extra)
            .filterValues { it != null }.entries.joinToString("&") { (name, value) ->
                "${URLEncoder.encode(name, "UTF-8")}=${URLEncoder.encode(value, "UTF-8")}"
            }
    override fun manifest(profile: KnowledgeProfile, knownDigest: String?, budget: KnowledgeBudget): JSONObject {
        require(knownDigest == null || KNOWLEDGE_DIGEST.matches(knownDigest))
        return strictJson(get("/v1/knowledge/manifest?${query(profile, mapOf("known_digest" to knownDigest))}", MAX_KNOWLEDGE_JSON_BYTES, budget), MAX_KNOWLEDGE_JSON_BYTES)
    }
    override fun pack(profile: KnowledgeProfile, digest: String, budget: KnowledgeBudget): ByteArray {
        require(KNOWLEDGE_DIGEST.matches(digest))
        return get("/v1/knowledge/packs/$digest?${query(profile)}", MAX_KNOWLEDGE_BYTES, budget)
    }
    override fun delta(profile: KnowledgeProfile, destination: String, base: String, budget: KnowledgeBudget): JSONObject {
        require(KNOWLEDGE_DIGEST.matches(destination) && KNOWLEDGE_DIGEST.matches(base))
        return strictJson(get("/v1/knowledge/deltas/$destination?${query(profile, mapOf("base_digest" to base))}", MAX_KNOWLEDGE_JSON_BYTES, budget, true), MAX_KNOWLEDGE_JSON_BYTES)
    }
    private data class Response(val status: Int, val bytes: ByteArray)
    private fun get(path: String, maximum: Int, budget: KnowledgeBudget, delta: Boolean = false): ByteArray {
        if (closed.get()) throw KnowledgeFailure("KNOWLEDGE_SESSION_CHANGED")
        budget.check()
        val future = try { worker.submit<ByteArray> { authenticated(path, maximum, budget, delta) } }
        catch (_: java.util.concurrent.RejectedExecutionException) { throw KnowledgeFailure("KNOWLEDGE_NETWORK_ERROR") }
        try { return future.get(budget.remainingMs(), TimeUnit.MILLISECONDS) }
        catch (_: TimeoutException) {
            rotation.get()?.let { broker.invalidate(it) }
            budget.cancel(); future.cancel(true)
            throw KnowledgeFailure("KNOWLEDGE_TIMEOUT")
        } catch (error: ExecutionException) {
            val cause = error.cause
            if (cause is KnowledgeFailure) throw cause
            throw KnowledgeFailure("KNOWLEDGE_NETWORK_ERROR")
        } catch (_: InterruptedException) {
            rotation.get()?.let { broker.invalidate(it) }; budget.cancel(); future.cancel(true)
            Thread.currentThread().interrupt(); throw KnowledgeFailure("KNOWLEDGE_SESSION_CHANGED")
        }
    }
    private fun principal(): KnowledgeSessionSnapshot = broker.snapshot()?.also {
        if (it.origin.removeSuffix("/") != origin || it.sessionId.isEmpty()) throw KnowledgeFailure("KNOWLEDGE_SESSION_CHANGED")
    } ?: throw KnowledgeFailure("KNOWLEDGE_ACCESS_DENIED")
    private fun authenticated(path: String, maximum: Int, budget: KnowledgeBudget, delta: Boolean): ByteArray {
        var session = principal()
        var response = request(path, session.accessToken, null, maximum, budget)
        if (response.status == 401 && runCatching { strictJson(response.bytes, maximum).optString("code") }.getOrNull() == "INVALID_SESSION") {
            synchronized(CoreRefreshSerialization.lock) {
            budget.check()
            val latest = principal()
            if (latest.sessionId != session.sessionId) throw KnowledgeFailure("KNOWLEDGE_SESSION_CHANGED")
            if (latest != session) { session = latest } else {
            rotation.set(session)
            try {
                val result = request("/v1/sessions/refresh", null, JSONObject().put("refresh_token", session.refreshToken).toString(), 32768, budget)
                budget.check()
                if (result.status != 200) { broker.invalidate(session); throw KnowledgeFailure("KNOWLEDGE_ACCESS_DENIED") }
                val payload = strictJson(result.bytes, 32768)
                val access = strictString(payload, "session_token", 8192)
                val refresh = strictString(payload, "refresh_token", 8192)
                require(access.none { it == '\r' || it == '\n' } && refresh.none { it == '\r' || it == '\n' })
                if (!broker.rotate(session, access, refresh)) throw KnowledgeFailure("KNOWLEDGE_SESSION_CHANGED")
                session = principal()
            } catch (error: Exception) {
                // The POST may have committed. Discard only this expected principal.
                rotation.get()?.let { broker.invalidate(it) }
                if (error is KnowledgeFailure) throw error
                throw KnowledgeFailure("KNOWLEDGE_NETWORK_ERROR")
            } finally { rotation.set(null) }
            }
            }
            response = request(path, session.accessToken, null, maximum, budget)
        }
        budget.check()
        if (principal() != session) throw KnowledgeFailure("KNOWLEDGE_SESSION_CHANGED")
        when (response.status) {
            200 -> return response.bytes
            401, 403 -> { broker.invalidate(session); throw KnowledgeFailure("KNOWLEDGE_ACCESS_DENIED") }
            404 -> if (delta) throw KnowledgeFailure("KNOWLEDGE_DELTA_UNAVAILABLE")
        }
        throw KnowledgeFailure(if (response.status >= 500) "KNOWLEDGE_NETWORK_ERROR" else "KNOWLEDGE_INVALID")
    }
    private fun request(path: String, access: String?, body: String?, maximum: Int, budget: KnowledgeBudget): Response {
        budget.check()
        val connection = URI(origin + path).toURL().openConnection() as HttpURLConnection
        try {
            connection.instanceFollowRedirects = false
            connection.connectTimeout = budget.remainingMs().coerceAtMost(Int.MAX_VALUE.toLong()).toInt()
            connection.readTimeout = connection.connectTimeout
            connection.requestMethod = if (body == null) "GET" else "POST"
            connection.useCaches = false
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("Cache-Control", "no-store")
            connection.setRequestProperty("X-Request-ID", UUID.randomUUID().toString())
            if (access != null) {
                require(access.isNotEmpty() && access.length <= 8192 && access.none { it == '\r' || it == '\n' })
                connection.setRequestProperty("Authorization", "Bearer $access")
            }
            if (body != null) {
                val bytes = body.toByteArray(Charsets.UTF_8)
                connection.doOutput = true; connection.setRequestProperty("Content-Type", "application/json")
                connection.setFixedLengthStreamingMode(bytes.size)
                connection.outputStream.use { it.write(bytes) }
            }
            val status = connection.responseCode; budget.check()
            if (status in 300..399) throw KnowledgeFailure("KNOWLEDGE_REDIRECT_DENIED")
            connection.getHeaderField("Content-Length")?.let {
                if (!it.all(Char::isDigit) || it.toLongOrNull()?.let { length -> length > maximum } != false) throw KnowledgeFailure("KNOWLEDGE_SIZE_INVALID")
            }
            val stream = if (status >= 400) connection.errorStream else connection.inputStream
            val output = ByteArrayOutputStream(minOf(maximum, 8192))
            stream?.use {
                val chunk = ByteArray(8192)
                while (true) {
                    budget.check(); connection.readTimeout = budget.remainingMs().coerceAtMost(Int.MAX_VALUE.toLong()).toInt()
                    val count = it.read(chunk); budget.check(); if (count < 0) break
                    if (output.size() + count > maximum) throw KnowledgeFailure("KNOWLEDGE_SIZE_INVALID")
                    output.write(chunk, 0, count)
                }
            }
            return Response(status, output.toByteArray())
        } catch (_: java.net.SocketTimeoutException) { throw KnowledgeFailure("KNOWLEDGE_TIMEOUT") }
        finally { connection.disconnect() }
    }
    override fun close() {
        closed.set(true); rotation.get()?.let { broker.invalidate(it) }; worker.shutdownNow()
    }
}
