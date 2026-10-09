package com.alpha0.app.knowledge

import com.sun.net.httpserver.HttpServer
import java.net.InetSocketAddress
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import org.junit.Assert.*
import org.junit.Test

class KnowledgeHttpTest {
    private class Broker(override val origin: String) : KnowledgeSessionBroker {
        @Volatile var current: KnowledgeSessionSnapshot? = KnowledgeSessionSnapshot(origin, "session-a", "access-old", "refresh-old")
        override fun snapshot() = current
        @Synchronized override fun rotate(expected: KnowledgeSessionSnapshot, access: String, refresh: String): Boolean {
            if (current != expected) return false
            current = expected.copy(accessToken = access, refreshToken = refresh); return true
        }
        @Synchronized override fun invalidate(expected: KnowledgeSessionSnapshot): Boolean {
            if (current != expected) return false
            current = null; return true
        }
    }
    private fun budget(ms: Long = 10000) = KnowledgeBudget({ System.nanoTime() / 1000000 }, ms)
    @Test fun realLoopbackHttpRefreshStaysOriginBoundAndUsesRotatedBearer() {
        val server = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0)
        val refreshes = AtomicInteger(); val queries = mutableListOf<String?>()
        server.createContext("/v1/knowledge/manifest") { exchange ->
            queries += exchange.requestURI.rawQuery
            val valid = exchange.requestHeaders.getFirst("Authorization") == "Bearer access-new"
            val body = if (valid) "{\"status\":\"unavailable\"}" else "{\"code\":\"INVALID_SESSION\"}"
            exchange.sendResponseHeaders(if (valid) 200 else 401, body.length.toLong()); exchange.responseBody.use { it.write(body.toByteArray()) }
        }
        server.createContext("/v1/sessions/refresh") { exchange ->
            refreshes.incrementAndGet()
            assertTrue(exchange.requestBody.readBytes().toString(Charsets.UTF_8).contains("refresh-old"))
            val body = "{\"session_token\":\"access-new\",\"refresh_token\":\"refresh-new\"}"
            exchange.sendResponseHeaders(200, body.length.toLong()); exchange.responseBody.use { it.write(body.toByteArray()) }
        }
        server.start(); val broker = Broker("http://127.0.0.1:${server.address.port}")
        val transport = KnowledgeHttpTransport(broker)
        try {
            assertEquals("unavailable", transport.manifest(KnowledgeFixture.profile, null, budget()).getString("status"))
            assertEquals(1, refreshes.get()); assertEquals("access-new", broker.current!!.accessToken)
            assertTrue(queries.all { it != null && it.contains("platform=android") && !it.contains("access-") && !it.contains("refresh-") })
        } finally { transport.close(); server.stop(0) }
    }
    @Test fun deltaUsesCanonicalCoreRouteWithExactProfileAndBearer() {
        val destination = "b".repeat(64)
        val base = "a".repeat(64)
        val requests = java.util.concurrent.LinkedBlockingQueue<Triple<String, String?, String?>>()
        val unavailable = java.util.concurrent.atomic.AtomicBoolean(false)
        val server = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0)
        server.createContext("/v1/knowledge/deltas/") { exchange ->
            requests.offer(Triple(exchange.requestURI.path, exchange.requestURI.rawQuery,
                exchange.requestHeaders.getFirst("Authorization")))
            if (unavailable.get()) {
                exchange.sendResponseHeaders(404, -1)
                exchange.close()
            } else {
                val payload = """{"schema_version":1}""".toByteArray(Charsets.UTF_8)
                exchange.sendResponseHeaders(200, payload.size.toLong())
                exchange.responseBody.use { it.write(payload) }
            }
        }
        server.start()
        val transport = KnowledgeHttpTransport(Broker("http://127.0.0.1:${server.address.port}"))
        try {
            assertEquals(1, transport.delta(KnowledgeFixture.profile, destination, base, budget()).getInt("schema_version"))
            val request = requests.poll(2, TimeUnit.SECONDS)
            assertNotNull(request)
            assertEquals("/v1/knowledge/deltas/$destination", request!!.first)
            assertTrue(request.second.orEmpty().contains("base_digest=$base"))
            assertTrue(request.second.orEmpty().contains("platform=android"))
            assertEquals("Bearer access-old", request.third)

            unavailable.set(true)
            assertEquals("KNOWLEDGE_DELTA_UNAVAILABLE",
                assertThrows(KnowledgeFailure::class.java) {
                    transport.delta(KnowledgeFixture.profile, destination, base, budget())
                }.code)
        } finally { transport.close(); server.stop(0) }
    }
    @Test fun redirectsAndStreamedOversizeCannotReachInstallation() {
        val server = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0)
        var oversized = false
        server.createContext("/v1/knowledge/packs") { exchange ->
            if (!oversized) { exchange.responseHeaders.set("Location", "https://foreign.invalid/"); exchange.sendResponseHeaders(302, -1); exchange.close() }
            else { exchange.sendResponseHeaders(200, 0); exchange.responseBody.use { it.write(ByteArray(262145)) } }
        }
        server.start(); val transport = KnowledgeHttpTransport(Broker("http://127.0.0.1:${server.address.port}"))
        try {
            val redirected = assertThrows(KnowledgeFailure::class.java) { transport.pack(KnowledgeFixture.profile, "a".repeat(64), budget()) }
            assertEquals("KNOWLEDGE_REDIRECT_DENIED", redirected.code)
            oversized = true
            assertEquals("KNOWLEDGE_SIZE_INVALID", assertThrows(KnowledgeFailure::class.java) { transport.pack(KnowledgeFixture.profile, "a".repeat(64), budget()) }.code)
        } finally { transport.close(); server.stop(0) }
    }
    @Test fun logoutDuringRefreshDoesNotResurrectOrOverwriteNewLogin() {
        val server = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0)
        val entered = CountDownLatch(1); val finish = CountDownLatch(1)
        server.createContext("/v1/knowledge/manifest") { exchange ->
            val body = "{\"code\":\"INVALID_SESSION\"}"; exchange.sendResponseHeaders(401, body.length.toLong()); exchange.responseBody.use { it.write(body.toByteArray()) }
        }
        server.createContext("/v1/sessions/refresh") { exchange ->
            entered.countDown(); finish.await(2, TimeUnit.SECONDS)
            val body = "{\"session_token\":\"retired-access\",\"refresh_token\":\"retired-refresh\"}"
            exchange.sendResponseHeaders(200, body.length.toLong()); exchange.responseBody.use { it.write(body.toByteArray()) }
        }
        server.start(); val broker = Broker("http://127.0.0.1:${server.address.port}"); val transport = KnowledgeHttpTransport(broker)
        val worker = Executors.newSingleThreadExecutor()
        try {
            val pending = worker.submit<String> { runCatching { transport.manifest(KnowledgeFixture.profile, null, budget()) }.exceptionOrNull().let { (it as KnowledgeFailure).code } }
            assertTrue(entered.await(2, TimeUnit.SECONDS)); broker.current = broker.current!!.copy(sessionId = "session-new", accessToken = "fresh-access", refreshToken = "fresh-refresh")
            finish.countDown(); assertEquals("KNOWLEDGE_SESSION_CHANGED", pending.get(2, TimeUnit.SECONDS))
            assertEquals("fresh-access", broker.current!!.accessToken)
        } finally { finish.countDown(); worker.shutdownNow(); transport.close(); server.stop(0) }
    }
    @Test fun deadlineIncludesRefreshAndUnknownRotationIsNotBlindlyRetried() {
        val server = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0)
        val refreshes = AtomicInteger()
        server.createContext("/v1/knowledge/manifest") { exchange ->
            val body = "{\"code\":\"INVALID_SESSION\"}"; exchange.sendResponseHeaders(401, body.length.toLong()); exchange.responseBody.use { it.write(body.toByteArray()) }
        }
        server.createContext("/v1/sessions/refresh") { exchange ->
            refreshes.incrementAndGet(); Thread.sleep(100)
            runCatching { exchange.sendResponseHeaders(200, 0); exchange.responseBody.close() }
        }
        server.start(); val broker = Broker("http://127.0.0.1:${server.address.port}"); val transport = KnowledgeHttpTransport(broker)
        try {
            val started = System.nanoTime()
            val failure = assertThrows(KnowledgeFailure::class.java) { transport.manifest(KnowledgeFixture.profile, null, budget(50)) }
            assertEquals("KNOWLEDGE_TIMEOUT", failure.code)
            assertTrue(TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - started) < 1000)
            if (refreshes.get() > 0) assertNull(broker.current)
            assertTrue(refreshes.get() <= 1)
        } finally { transport.close(); server.stop(0) }
    }
}
