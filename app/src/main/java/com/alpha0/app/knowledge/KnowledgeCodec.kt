package com.alpha0.app.knowledge

import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.security.MessageDigest
import java.util.Base64
import org.json.JSONArray
import org.json.JSONObject
import org.json.JSONTokener

const val MAX_KNOWLEDGE_BYTES = 262144
internal const val MAX_KNOWLEDGE_JSON_BYTES = 353624
internal const val MAX_SAFE_INTEGER = 9007199254740991L
internal val KNOWLEDGE_DIGEST = Regex("[0-9a-f]{64}")

internal fun knowledgeHash(raw: ByteArray): String = MessageDigest.getInstance("SHA-256").digest(raw).joinToString("") { "%02x".format(it) }
internal fun exact(value: JSONObject, keys: Set<String>) { require(value.keys().asSequence().toSet() == keys) { "KNOWLEDGE_FIELDS_INVALID" } }
internal fun strictString(value: JSONObject, key: String, maximum: Int): String {
    val item = value.get(key)
    require(item is String && item.isNotEmpty() && item.length <= maximum) { "KNOWLEDGE_STRING_INVALID" }
    return item
}
internal fun strictInteger(value: JSONObject, key: String, minimum: Long = 0, maximum: Long = MAX_SAFE_INTEGER): Long {
    val item = value.get(key)
    require(item is Int || item is Long) { "KNOWLEDGE_INTEGER_INVALID" }
    val number = (item as Number).toLong()
    require(number in minimum..maximum) { "KNOWLEDGE_INTEGER_INVALID" }
    return number
}
internal fun strictJson(raw: ByteArray, maximum: Int = MAX_KNOWLEDGE_JSON_BYTES): JSONObject {
    require(raw.size in 1..maximum) { "KNOWLEDGE_SIZE_INVALID" }
    try {
        val text = Charsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
            .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(raw)).toString()
        KnowledgeJsonGrammar(text).validate()
        val tokener = JSONTokener(text)
        val result = tokener.nextValue()
        require(result is JSONObject && tokener.nextClean() == '\u0000') { "KNOWLEDGE_JSON_INVALID" }
        return result
    } catch (error: Exception) { throw IllegalArgumentException("KNOWLEDGE_JSON_INVALID", error) }
}
/** Android's JSONTokener is permissive and differs from the JVM test library.
 * Bound recursion and reject duplicate keys/non-JSON syntax before either parser. */
private class KnowledgeJsonGrammar(private val text: String) {
    private var position = 0
    private fun space() { while (position < text.length && text[position] in " \t\r\n") position++ }
    private fun take(character: Char): Boolean { space(); return if (position < text.length && text[position] == character) { position++; true } else false }
    fun validate() { value(0); space(); require(position == text.length) }
    private fun string(): String {
        space(); val start = position; require(take('"'))
        var finished = false
        while (position < text.length) {
            val character = text[position++]
            if (character == '"') { finished = true; break }
            require(character.code >= 32)
            if (character == '\\') {
                require(position < text.length)
                when (text[position++]) {
                    '"', '\\', '/', 'b', 'f', 'n', 'r', 't' -> Unit
                    'u' -> { require(position + 4 <= text.length && text.substring(position, position + 4).all { it in "0123456789abcdefABCDEF" }); position += 4 }
                    else -> throw IllegalArgumentException("KNOWLEDGE_JSON_INVALID")
                }
            }
        }
        require(finished)
        return JSONTokener(text.substring(start, position)).nextValue() as String
    }
    private fun value(depth: Int) {
        require(depth <= 32); space(); require(position < text.length)
        when (text[position]) {
            '{' -> {
                position++; val keys = mutableSetOf<String>()
                if (take('}')) return
                do { require(keys.add(string()) && take(':')); value(depth + 1) } while (take(','))
                require(take('}'))
            }
            '[' -> { position++; if (take(']')) return; do { value(depth + 1) } while (take(',')); require(take(']')) }
            '"' -> string()
            't', 'f', 'n' -> {
                val literal = when (text[position]) { 't' -> "true"; 'f' -> "false"; else -> "null" }
                require(text.startsWith(literal, position)); position += literal.length
            }
            else -> {
                val start = position
                while (position < text.length && text[position] !in " \t\r\n,]}") position++
                val number = text.substring(start, position)
                require(number.length in 1..128 && Regex("-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?").matches(number))
            }
        }
    }
}
internal fun stringArray(array: JSONArray, minimum: Int, maximum: Int, length: Int): List<String> {
    require(array.length() in minimum..maximum) { "KNOWLEDGE_ARRAY_INVALID" }
    return (0 until array.length()).map { index ->
        val value = array.get(index)
        require(value is String && value.isNotEmpty() && value.length <= length) { "KNOWLEDGE_ARRAY_INVALID" }
        value
    }
}

data class KnowledgeProfile(val game: String, val platform: String, val patch: String, val environment: String, val profile: String) {
    init {
        require(platform in setOf("android", "windows")) { "KNOWLEDGE_PROFILE_INVALID" }
        require(values().all { (key, value) -> value.isNotEmpty() && value.length <= if (key == "patch") 64 else 128 }) { "KNOWLEDGE_PROFILE_INVALID" }
    }
    fun values(): Map<String, String> = linkedMapOf("game" to game, "platform" to platform, "patch" to patch, "environment" to environment, "profile" to profile)
    internal fun key(): String = JSONObject(values()).toString()
    companion object {
        internal val keys = setOf("game", "platform", "patch", "environment", "profile")
        internal fun fromJson(value: JSONObject, exactFields: Boolean = false): KnowledgeProfile {
            if (exactFields) exact(value, keys)
            return KnowledgeProfile(strictString(value, "game", 128), strictString(value, "platform", 128),
                strictString(value, "patch", 64), strictString(value, "environment", 128), strictString(value, "profile", 128))
        }
    }
}

data class KnowledgeRecommendation(val text: String, val reason: String, val priority: Int, val confidence: Double?,
    val provenance: List<String>, val observedAtMs: Long, val packDigest: String, val ruleId: String)
internal data class KnowledgeCondition(val signal: String, val operation: String, val expected: Any) {
    fun matches(signals: Map<String, Any?>): Boolean? {
        val actual = signals[signal] ?: return null
        if (expected is Boolean || expected is String) return if (actual.javaClass == expected.javaClass && operation == "eq") actual == expected else null
        if (actual !is Number || expected !is Number) return null
        val value = actual.toDouble(); val target = expected.toDouble()
        if (!value.isFinite() || (value % 1.0 == 0.0 && kotlin.math.abs(value) > MAX_SAFE_INTEGER)) return null
        return when (operation) { "eq" -> value == target; "lt" -> value < target; "lte" -> value <= target; "gt" -> value > target; "gte" -> value >= target; else -> null }
    }
}
internal data class KnowledgeRule(val id: String, val priority: Int, val requires: List<KnowledgeCondition>,
    val text: Map<String, String>, val reason: Map<String, String>, val provenance: List<String>, val confidence: Double?)

class ValidatedKnowledgePack internal constructor(val digest: String, val profile: KnowledgeProfile, val version: String,
    val validUntilMs: Long, val maxStateAgeMs: Long, private val provenance: List<String>, private val rules: List<KnowledgeRule>) {
    internal fun evaluate(signals: Map<String, Any?>, locale: String, observedAtMs: Long): List<KnowledgeRecommendation> {
        if (signals.size > 64) return emptyList()
        val language = if (locale == "ru") "ru" else "en"
        return rules.sortedWith(compareByDescending<KnowledgeRule> { it.priority }.thenBy { it.id })
            .filter { rule -> rule.requires.all { it.matches(signals) == true } }.take(12).map { rule ->
                KnowledgeRecommendation(rule.text.getValue(language), rule.reason.getValue(language), rule.priority,
                    rule.confidence, (provenance + rule.provenance).distinct(), observedAtMs, digest, rule.id)
            }
    }
}

object KnowledgeCodec {
    fun pack(raw: ByteArray, independentDigest: String, profile: KnowledgeProfile): ValidatedKnowledgePack {
        require(raw.size in 1..MAX_KNOWLEDGE_BYTES && KNOWLEDGE_DIGEST.matches(independentDigest) && knowledgeHash(raw) == independentDigest) { "KNOWLEDGE_DIGEST_INVALID" }
        val value = strictJson(raw, MAX_KNOWLEDGE_BYTES)
        exact(value, setOf("schema_version", "id", "version", "status", "provenance", "revoked", "valid_until_ms", "max_state_age_ms", "rules", "coverage") + KnowledgeProfile.keys)
        require(strictInteger(value, "schema_version", 1, 1) == 1L && KnowledgeProfile.fromJson(value) == profile) { "KNOWLEDGE_PROFILE_INVALID" }
        strictString(value, "id", 128)
        require(value.get("status") == "validated" && value.get("revoked") == false) { "KNOWLEDGE_PACK_INVALID" }
        val version = strictString(value, "version", 64)
        val provenance = stringArray(value.getJSONArray("provenance"), 1, 16, 256)
        val expiry = strictInteger(value, "valid_until_ms", 1)
        val age = strictInteger(value, "max_state_age_ms", 1, 30000)
        val coverage = value.getJSONArray("coverage")
        require(coverage.length() <= 64 && (0 until coverage.length()).all { coverage.get(it) is String && (coverage.get(it) as String).length <= 256 }) { "KNOWLEDGE_COVERAGE_INVALID" }
        val rawRules = value.getJSONArray("rules"); require(rawRules.length() <= 128) { "KNOWLEDGE_RULE_INVALID" }
        val rules = (0 until rawRules.length()).map { index ->
            val rule = rawRules.getJSONObject(index)
            if (!rule.has("confidence")) rule.put("confidence", JSONObject.NULL)
            exact(rule, setOf("id", "priority", "requires", "text", "reason", "provenance", "confidence"))
            val ruleProvenance = stringArray(rule.getJSONArray("provenance"), 1, 16, 256)
            require((provenance + ruleProvenance).distinct().size <= 20) { "KNOWLEDGE_PROVENANCE_INVALID" }
            val conditions = rule.getJSONArray("requires"); require(conditions.length() in 1..16) { "KNOWLEDGE_CONDITION_INVALID" }
            val requires = (0 until conditions.length()).map { position ->
                val condition = conditions.getJSONObject(position)
                exact(condition, setOf("signal", "op", "value"))
                val signal = strictString(condition, "signal", 128)
                require(Regex("[a-zA-Z0-9_.:-]+").matches(signal)) { "KNOWLEDGE_CONDITION_INVALID" }
                val operation = strictString(condition, "op", 3)
                require(operation in setOf("eq", "lt", "lte", "gt", "gte")) { "KNOWLEDGE_CONDITION_INVALID" }
                val expected = condition.get("value")
                require(expected is Boolean || expected is String || expected is Number) { "KNOWLEDGE_CONDITION_INVALID" }
                if (expected is Number) {
                    val number = expected.toDouble()
                    require(number.isFinite() && (number % 1.0 != 0.0 || kotlin.math.abs(number) <= MAX_SAFE_INTEGER)) { "KNOWLEDGE_CONDITION_INVALID" }
                } else require(operation == "eq") { "KNOWLEDGE_CONDITION_INVALID" }
                KnowledgeCondition(signal, operation, expected)
            }
            fun localized(key: String): Map<String, String> {
                val text = rule.getJSONObject(key); exact(text, setOf("en", "ru"))
                return mapOf("en" to strictString(text, "en", 2000), "ru" to strictString(text, "ru", 2000))
            }
            val confidence = rule.get("confidence")
            require(confidence === JSONObject.NULL || confidence is Number && confidence.toDouble().isFinite() && confidence.toDouble() in 0.0..1.0) { "KNOWLEDGE_RULE_INVALID" }
            KnowledgeRule(strictString(rule, "id", 128), strictInteger(rule, "priority", 0, 100).toInt(), requires,
                localized("text"), localized("reason"), ruleProvenance, if (confidence is Number) confidence.toDouble() else null)
        }
        require(rules.map { it.id }.distinct().size == rules.size) { "KNOWLEDGE_DUPLICATE_RULE" }
        return ValidatedKnowledgePack(independentDigest, profile, version, expiry, age, provenance, rules)
    }

    fun delta(base: ByteArray, envelope: JSONObject, independentDigest: String, profile: KnowledgeProfile): ByteArray {
        require(base.size in 1..MAX_KNOWLEDGE_BYTES) { "KNOWLEDGE_BASE_INVALID" }
        exact(envelope, setOf("schema_version", "algorithm", "base_digest", "destination_digest", "destination_size", "prefix_bytes", "suffix_bytes", "insert_b64"))
        require(strictInteger(envelope, "schema_version", 1, 1) == 1L && envelope.get("algorithm") == "byte-splice-v1" &&
            envelope.get("base_digest") == knowledgeHash(base) && KNOWLEDGE_DIGEST.matches(independentDigest) && envelope.get("destination_digest") == independentDigest) { "KNOWLEDGE_DELTA_INVALID" }
        val size = strictInteger(envelope, "destination_size", 1, MAX_KNOWLEDGE_BYTES.toLong()).toInt()
        val prefix = strictInteger(envelope, "prefix_bytes", 0, MAX_KNOWLEDGE_BYTES.toLong()).toInt()
        val suffix = strictInteger(envelope, "suffix_bytes", 0, MAX_KNOWLEDGE_BYTES.toLong()).toInt()
        require(prefix + suffix <= base.size) { "KNOWLEDGE_DELTA_INVALID" }
        val encoded = envelope.get("insert_b64")
        require(encoded is String && encoded.length <= 4 * ((MAX_KNOWLEDGE_BYTES + 2) / 3) && encoded.length % 4 == 0) { "KNOWLEDGE_DELTA_INVALID" }
        val insert = Base64.getDecoder().decode(encoded)
        require(Base64.getEncoder().encodeToString(insert) == encoded && prefix + insert.size + suffix == size) { "KNOWLEDGE_DELTA_INVALID" }
        val result = base.copyOfRange(0, prefix) + insert + if (suffix == 0) byteArrayOf() else base.copyOfRange(base.size - suffix, base.size)
        pack(result, independentDigest, profile)
        return result
    }
}
