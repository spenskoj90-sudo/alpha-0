package com.alpha0.app.knowledge

import java.nio.file.Files
import java.util.concurrent.atomic.AtomicReference
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class PresentationFenceTest {
    private fun runFence(missing: Boolean, adapterThrows: Boolean = false) {
        val raw = KnowledgeFixture.bytes()
        val digest = KnowledgeFixture.digest(raw)
        val binding = TrustedKnowledgeBinding(KnowledgeFixture.profile, "source", "session", "fixture-origin", KnowledgeFixture.target)
        val frame = TrustedKnowledgeObservation(binding, "source", 1500, mapOf("health" to 0.2), 10, "frame-1", 1, 10, 10)
        val observed = AtomicReference<KnowledgeObservationInput>(KnowledgeObservationInput.AwaitingFirstFrame)
        val throwFromAdapter = java.util.concurrent.atomic.AtomicBoolean(false)
        val directory = Files.createTempDirectory("knowledge-presentation-fence").toFile()
        val transport = object : KnowledgeDistributionTransport {
            override fun manifest(profile: KnowledgeProfile, knownDigest: String?, budget: KnowledgeBudget): JSONObject =
                JSONObject().put("schema_version", 1).put("status", "available").put("profile", JSONObject(profile.values()))
                    .put("revision", 1).put("digest", digest).put("version", "1").put("server_time_ms", 1500)
                    .put("lease_until_ms", 61500).put("execution_authority", false)
            override fun pack(profile: KnowledgeProfile, digest: String, budget: KnowledgeBudget): ByteArray = raw
            override fun delta(profile: KnowledgeProfile, destination: String, base: String, budget: KnowledgeBudget): JSONObject = throw AssertionError()
        }
        val controller = KnowledgePresentation({ binding }, {
            if (throwFromAdapter.get()) throw IllegalStateException("service callback failed")
            observed.get()
        },
            { KnowledgeCache(directory, it, transport, { 1500 }, { 10 }) }, clock = { 10 })
        try {
            controller.start()
            val deadline = System.nanoTime() + 3_000_000_000L
            while (controller.state().state != "WAITING_FOR_VERIFIED_OBSERVATION" && System.nanoTime() < deadline) Thread.sleep(10)
            assertEquals("WAITING_FOR_VERIFIED_OBSERVATION", controller.state().state)
            observed.set(KnowledgeObservationInput.Frame(frame))
            assertEquals(1, controller.state().items.size)
            if (adapterThrows) throwFromAdapter.set(true)
            else observed.set(if (missing) KnowledgeObservationInput.Unavailable
                else KnowledgeObservationInput.Frame(frame.copy(sourceId = "foreign")))
            assertTrue(controller.state().items.isEmpty())
            assertEquals("UNAVAILABLE", controller.state().state)
            throwFromAdapter.set(false)
            observed.set(KnowledgeObservationInput.Frame(frame))
            assertTrue("old advice must not recover within the same epoch", controller.state().items.isEmpty())
        } finally { controller.close(); directory.deleteRecursively() }
    }
    @Test fun foreignSourceCannotReviveEarlierAdvice() = runFence(false)
    @Test fun disappearingObservationCannotReviveEarlierAdvice() = runFence(true)
    @Test fun adapterExceptionCannotReviveOldAdvice() = runFence(false, adapterThrows = true)
    @Test fun boundedProcessingHidesOldAdviceAndRequiresNewFrame() {
        val raw = KnowledgeFixture.bytes()
        val digest = KnowledgeFixture.digest(raw)
        val binding = TrustedKnowledgeBinding(KnowledgeFixture.profile, "source", "session", "fixture-origin", KnowledgeFixture.target)
        val first = TrustedKnowledgeObservation(binding, "source", 1500, mapOf("health" to 0.2), 10, "frame-1", 1, 10, 10)
        val second = first.copy(observedMonotonicMs = 12, frameId = "frame-2", frameSequence = 2,
            frameCapturedMonotonicMs = 11, ocrCompletedMonotonicMs = 12)
        val clock = java.util.concurrent.atomic.AtomicLong(10)
        val observed = AtomicReference<KnowledgeObservationInput>(KnowledgeObservationInput.AwaitingFirstFrame)
        val dir = Files.createTempDirectory("knowledge-processing-fence").toFile()
        val transport = object : KnowledgeDistributionTransport {
            override fun manifest(profile: KnowledgeProfile, knownDigest: String?, budget: KnowledgeBudget): JSONObject =
                JSONObject().put("schema_version", 1).put("status", "available").put("profile", JSONObject(profile.values()))
                    .put("revision", 1).put("digest", digest).put("version", "1").put("server_time_ms", 1500)
                    .put("lease_until_ms", 61500).put("execution_authority", false)
            override fun pack(profile: KnowledgeProfile, digest: String, budget: KnowledgeBudget): ByteArray = raw
            override fun delta(profile: KnowledgeProfile, destination: String, base: String, budget: KnowledgeBudget): JSONObject = throw AssertionError()
        }
        val controller = KnowledgePresentation({ binding }, { observed.get() },
            { KnowledgeCache(dir, it, transport, { 1500 }, { clock.get() }) }, clock = { clock.get() })
        try {
            controller.start()
            val deadline = System.nanoTime() + 3_000_000_000L
            while (controller.state().state != "WAITING_FOR_VERIFIED_OBSERVATION" && System.nanoTime() < deadline)
                Thread.sleep(10)
            assertEquals("WAITING_FOR_VERIFIED_OBSERVATION", controller.state().state)
            observed.set(KnowledgeObservationInput.Frame(first))
            assertEquals(1, controller.state().items.size)
            clock.set(11)
            observed.set(KnowledgeObservationInput.Processing(2, 11))
            assertEquals("WAITING_FOR_VERIFIED_OBSERVATION", controller.state().state)
            assertTrue(controller.state().items.isEmpty())
            clock.set(12)
            observed.set(KnowledgeObservationInput.Frame(second))
            assertEquals(1, controller.state().items.size)
            clock.set(13)
            observed.set(KnowledgeObservationInput.Processing(3, 13))
            assertTrue(controller.state().items.isEmpty())
            clock.set(5014)
            assertEquals("UNAVAILABLE", controller.state().state)
            observed.set(KnowledgeObservationInput.Frame(second.copy(frameId = "frame-3", frameSequence = 3,
                frameCapturedMonotonicMs = 13, ocrCompletedMonotonicMs = 13, observedMonotonicMs = 13)))
            assertTrue(controller.state().items.isEmpty())
        } finally { controller.close(); dir.deleteRecursively() }
    }
}
