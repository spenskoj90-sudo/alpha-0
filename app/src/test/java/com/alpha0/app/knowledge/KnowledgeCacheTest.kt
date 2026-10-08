package com.alpha0.app.knowledge

import java.io.File
import java.nio.file.Files
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class KnowledgeCacheTest {
    private fun manifest(raw: ByteArray, revision: Long = 1, status: String = "available", time: Long = 1500): JSONObject = JSONObject()
        .put("schema_version", 1).put("status", status).put("profile", JSONObject(KnowledgeFixture.profile.values()))
        .put("revision", revision).put("digest", KnowledgeFixture.digest(raw)).put("version", "1")
        .put("lease_until_ms", time + 60000).put("server_time_ms", time).put("execution_authority", false)
    private class FixtureTransport : KnowledgeDistributionTransport {
        var raw = KnowledgeFixture.bytes()
        var reply = JSONObject()
        var error: String? = null
        var afterManifest: (() -> Unit)? = null
        var packCall: (() -> ByteArray)? = null
        override fun manifest(profile: KnowledgeProfile, knownDigest: String?, budget: KnowledgeBudget): JSONObject {
            error?.let { throw KnowledgeFailure(it) }; afterManifest?.invoke(); return reply
        }
        override fun pack(profile: KnowledgeProfile, digest: String, budget: KnowledgeBudget): ByteArray = packCall?.invoke() ?: raw
        override fun delta(profile: KnowledgeProfile, destination: String, base: String, budget: KnowledgeBudget): JSONObject = throw KnowledgeFailure("KNOWLEDGE_DELTA_UNAVAILABLE")
    }
    private fun binding() = TrustedKnowledgeBinding(KnowledgeFixture.profile, "fixture-source", "session-a", "fixture-origin")
    private fun observation(time: Long = 1500, source: String = "fixture-source", monotonic: Long = 10L) = TrustedKnowledgeObservation(binding(), source, time, mapOf("health" to 0.2), monotonic)
    @Test fun leaseSubtractsAllNetworkTimeAndUsesMonotonicFreshness() {
        val directory = Files.createTempDirectory("knowledge-test-").toFile()
        val transport = FixtureTransport().apply { reply = manifest(raw) }
        var mono = 10L; var wall = 1500L
        val cache = KnowledgeCache(directory, "fixture-origin", transport, { wall }, { mono })
        try {
            transport.afterManifest = { mono += 1500; wall += 1500 }
            cache.refresh(binding())
            assertEquals(58500L, cache.status().remainingLeaseMs)
            assertEquals(1, cache.evaluate(observation(wall, monotonic = mono), "ru").size)
            assertTrue(cache.evaluate(observation(wall, "foreign-source"), "en").isEmpty())
            wall = 1; mono += 60000
            assertTrue(cache.evaluate(observation(1500), "en").isEmpty())
        } finally { cache.close(); directory.deleteRecursively() }
    }
    @Test fun restartRevalidatesDigestAndRequiresNewAuthenticatedLease() {
        val directory = Files.createTempDirectory("knowledge-test-").toFile()
        val transport = FixtureTransport().apply { reply = manifest(raw) }
        val first = KnowledgeCache(directory, "fixture-origin", transport, { 1500L }, { 10L })
        first.refresh(binding()); first.close()
        val restarted = KnowledgeCache(directory, "fixture-origin", transport, { 1500L }, { 10L })
        try {
            assertTrue(restarted.evaluate(observation(), "en").isEmpty())
            File(directory, KnowledgeFixture.digest(transport.raw) + ".json").writeText("corrupt")
            restarted.refresh(binding()) // corrupt cache cannot bypass complete download validation
            assertEquals(1, restarted.evaluate(observation(), "en").size)
        } finally { restarted.close(); directory.deleteRecursively() }
    }
    @Test fun revocationTombstoneAndRollbackDenialSurviveRestart() {
        val directory = Files.createTempDirectory("knowledge-test-").toFile()
        val transport = FixtureTransport().apply { reply = manifest(raw) }
        var cache = KnowledgeCache(directory, "fixture-origin", transport, { 1500L }, { 10L })
        try {
            cache.refresh(binding())
            transport.reply = manifest(transport.raw, 2, "revoked")
            cache.refresh(binding()); assertTrue(cache.evaluate(observation(), "en").isEmpty())
            cache.close(); cache = KnowledgeCache(directory, "fixture-origin", transport, { 1500L }, { 10L })
            transport.reply = manifest(transport.raw, 1)
            assertThrows(KnowledgeFailure::class.java) { cache.refresh(binding()) }
            transport.reply = manifest(transport.raw, 3)
            assertThrows(KnowledgeFailure::class.java) { cache.refresh(binding()) }
            assertTrue(cache.evaluate(observation(), "en").isEmpty())
        } finally { cache.close(); directory.deleteRecursively() }
    }
    @Test fun stopIsImmediateAndLateFetchCannotInstall() {
        val directory = Files.createTempDirectory("knowledge-test-").toFile()
        val transport = FixtureTransport().apply { reply = manifest(raw) }
        val entered = CountDownLatch(1); val finish = CountDownLatch(1)
        transport.packCall = { entered.countDown(); finish.await(2, TimeUnit.SECONDS); transport.raw }
        val cache = KnowledgeCache(directory, "fixture-origin", transport, { 1500L }, { 10L })
        val worker = Executors.newSingleThreadExecutor()
        try {
            val pending = worker.submit { runCatching { cache.refresh(binding()) } }
            assertTrue(entered.await(2, TimeUnit.SECONDS)); cache.clear()
            assertTrue(cache.evaluate(observation(), "en").isEmpty()); finish.countDown(); pending.get(2, TimeUnit.SECONDS)
            assertFalse(File(directory, "state.json").exists())
        } finally { finish.countDown(); worker.shutdownNow(); cache.close(); directory.deleteRecursively() }
    }
    @Test fun accessDenialAndCorruptDurableStateFailClosed() {
        val directory = Files.createTempDirectory("knowledge-test-").toFile()
        val transport = FixtureTransport().apply { reply = manifest(raw) }
        var cache = KnowledgeCache(directory, "fixture-origin", transport, { 1500L }, { 10L })
        try {
            cache.refresh(binding()); transport.error = "KNOWLEDGE_ACCESS_DENIED"
            assertThrows(KnowledgeFailure::class.java) { cache.refresh(binding()) }
            assertTrue(cache.evaluate(observation(), "en").isEmpty())
            cache.close(); File(directory, "state.json").writeText("corrupt")
            cache = KnowledgeCache(directory, "fixture-origin", transport, { 1500L }, { 10L })
            transport.error = null
            assertThrows(KnowledgeFailure::class.java) { cache.refresh(binding()) }
            assertTrue(cache.evaluate(observation(), "en").isEmpty())
        } finally { cache.close(); directory.deleteRecursively() }
    }
    @Test fun oneCacheWriterOwnsDirectory() {
        val directory = Files.createTempDirectory("knowledge-test-").toFile()
        val transport = FixtureTransport()
        val cache = KnowledgeCache(directory, "fixture-origin", transport)
        try { assertThrows(IllegalStateException::class.java) { KnowledgeCache(directory, "fixture-origin", transport) } }
        finally { cache.close(); directory.deleteRecursively() }
    }
}
