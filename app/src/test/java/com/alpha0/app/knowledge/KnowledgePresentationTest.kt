package com.alpha0.app.knowledge

import java.nio.file.Files
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class KnowledgePresentationTest {
    @Test fun unverifiedShippedProfileNeverOpensCacheOrNetwork() {
        val opened = AtomicInteger()
        val controller = KnowledgePresentation({ null }, { null }, { opened.incrementAndGet(); throw AssertionError("untrusted cache") })
        try {
            controller.start()
            assertEquals("WAITING_FOR_VERIFIED_PROFILE", controller.state().state)
            assertTrue(controller.state().items.isEmpty()); assertFalse(controller.state().actionAuthority)
            assertEquals(0, opened.get())
            controller.stop(); assertEquals("STOPPED", controller.state().state)
        } finally { controller.close() }
    }
    @Test fun lateFetchAfterStopCannotPublishReadyAndRestartNeedsFreshManifest() {
        val entered = CountDownLatch(1); val finish = CountDownLatch(1); val fetched = CountDownLatch(1)
        val raw = KnowledgeFixture.bytes(); val digest = KnowledgeFixture.digest(raw)
        val binding = TrustedKnowledgeBinding(KnowledgeFixture.profile, "source-a", "session-a", "http://127.0.0.1")
        val directory = Files.createTempDirectory("presentation").toFile()
        val transport = object : KnowledgeDistributionTransport {
            override fun manifest(profile: KnowledgeProfile, knownDigest: String?, budget: KnowledgeBudget): JSONObject {
                entered.countDown(); finish.await(2, TimeUnit.SECONDS)
                return JSONObject().put("schema_version", 1).put("status", "available").put("profile", JSONObject(profile.values()))
                    .put("revision", 1).put("digest", digest).put("version", "1").put("server_time_ms", 1000)
                    .put("lease_until_ms", 61000).put("execution_authority", false)
            }
            override fun pack(profile: KnowledgeProfile, digest: String, budget: KnowledgeBudget): ByteArray { fetched.countDown(); return raw }
            override fun delta(profile: KnowledgeProfile, destination: String, base: String, budget: KnowledgeBudget) = throw AssertionError()
        }
        val controller = KnowledgePresentation({ binding }, { null }, { KnowledgeCache(directory, it, transport, { 1000 }) })
        try {
            controller.start(); assertTrue(entered.await(2, TimeUnit.SECONDS))
            val before = System.nanoTime(); controller.stop()
            assertTrue(TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - before) < 250)
            assertEquals("STOPPED", controller.state().state); finish.countDown()
            assertFalse(fetched.await(150, TimeUnit.MILLISECONDS)); assertEquals("STOPPED", controller.state().state)
            assertFalse(java.io.File(directory, "state.json").exists())
        } finally { finish.countDown(); controller.close(); directory.deleteRecursively() }
    }
}
