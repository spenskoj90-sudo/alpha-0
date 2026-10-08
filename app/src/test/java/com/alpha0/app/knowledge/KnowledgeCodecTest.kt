package com.alpha0.app.knowledge

import java.security.MessageDigest
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

internal object KnowledgeFixture {
    val profile = KnowledgeProfile("fixture", "android", "1", "offline-fixture", "tank")
    fun bytes(version: String = "1"): ByteArray = JSONObject().apply {
        put("schema_version", 1); put("id", "fixture"); put("version", version)
        profile.values().forEach { (k, v) -> put(k, v) }
        put("status", "validated"); put("revoked", false)
        put("provenance", JSONArray(listOf("fixture:review")))
        put("valid_until_ms", 100000); put("max_state_age_ms", 1000)
        put("coverage", JSONArray(listOf("defensive")))
        put("rules", JSONArray().put(JSONObject().apply {
            put("id", "defensive"); put("priority", 10)
            put("requires", JSONArray().put(JSONObject().put("signal", "health").put("op", "lte").put("value", 0.3)))
            put("text", JSONObject().put("en", "Review defense").put("ru", "Проверьте защиту"))
            put("reason", JSONObject().put("en", "Low health").put("ru", "Сниженное здоровье"))
            put("provenance", JSONArray(listOf("fixture:rule"))); put("confidence", JSONObject.NULL)
        }))
    }.toString().toByteArray(Charsets.UTF_8)
    fun digest(raw: ByteArray): String = MessageDigest.getInstance("SHA-256").digest(raw).joinToString("") { "%02x".format(it) }
}

class KnowledgeCodecTest {
    private fun rejects(raw: ByteArray, digest: String = KnowledgeFixture.digest(raw), profile: KnowledgeProfile = KnowledgeFixture.profile) {
        assertThrows(IllegalArgumentException::class.java) { KnowledgeCodec.pack(raw, digest, profile) }
    }
    @Test fun completePackRequiresIndependentDigestExactProfileAndNoExecutableFields() {
        val raw = KnowledgeFixture.bytes()
        val pack = KnowledgeCodec.pack(raw, KnowledgeFixture.digest(raw), KnowledgeFixture.profile)
        assertEquals("1", pack.version)
        rejects(raw, "a".repeat(64))
        rejects(raw, profile = KnowledgeFixture.profile.copy(patch = "other"))
        val executable = JSONObject(raw.toString(Charsets.UTF_8)).put("execute", "fixture")
        rejects(executable.toString().toByteArray())
        rejects(ByteArray(262145))
    }
    @Test fun digestCannotValidateMalformedUtf8OrUnsafeNumericMetadata() {
        val raw = KnowledgeFixture.bytes()
        val offset = raw.toString(Charsets.UTF_8).indexOf("Review defense")
        raw[offset] = 255.toByte(); rejects(raw)
        for (value in listOf(true, 1.5, 9007199254740992L)) {
            val bad = JSONObject(KnowledgeFixture.bytes().toString(Charsets.UTF_8)).put("valid_until_ms", value)
            rejects(bad.toString().toByteArray())
        }
    }
    @Test fun deltaReconstructsCompleteDestinationBeforeSchemaValidation() {
        val base = KnowledgeFixture.bytes("1")
        val destination = KnowledgeFixture.bytes("2")
        val envelope = JSONObject().put("schema_version", 1).put("algorithm", "byte-splice-v1")
            .put("base_digest", KnowledgeFixture.digest(base)).put("destination_digest", KnowledgeFixture.digest(destination))
            .put("destination_size", destination.size).put("prefix_bytes", 0).put("suffix_bytes", 0)
            .put("insert_b64", java.util.Base64.getEncoder().encodeToString(destination))
        assertArrayEquals(destination, KnowledgeCodec.delta(base, envelope, KnowledgeFixture.digest(destination), KnowledgeFixture.profile))
        for (change in listOf("insert_b64" to "not/base64!", "prefix_bytes" to base.size, "destination_size" to 262145,
                              "algorithm" to "executable", "destination_digest" to "a".repeat(64))) {
            val bad = JSONObject(envelope.toString()).put(change.first, change.second)
            assertThrows(IllegalArgumentException::class.java) { KnowledgeCodec.delta(base, bad, KnowledgeFixture.digest(destination), KnowledgeFixture.profile) }
        }
    }
    @Test fun nonNumericValuesAndMissingSignalsNeverBecomeHealthRecommendations() {
        val pack = KnowledgeCodec.pack(KnowledgeFixture.bytes(), KnowledgeFixture.digest(KnowledgeFixture.bytes()), KnowledgeFixture.profile)
        assertEquals(1, pack.evaluate(mapOf("health" to 0.2), "ru", 1500).size)
        assertTrue(pack.evaluate(mapOf("health" to true), "en", 1500).isEmpty())
        assertTrue(pack.evaluate(emptyMap(), "en", 1500).isEmpty())
        assertTrue(pack.evaluate(mapOf("health" to Double.NaN), "en", 1500).isEmpty())
    }
}
