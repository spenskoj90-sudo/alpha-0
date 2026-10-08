package com.alpha0.app.knowledge

import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.IOException
import java.io.RandomAccessFile
import java.nio.channels.FileLock
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.util.UUID
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicLong
import java.util.concurrent.atomic.AtomicReference
import org.json.JSONArray
import org.json.JSONObject

class KnowledgeFailure(val code: String) : IOException(code)
class KnowledgeBudget(private val clock: () -> Long, timeoutMs: Long = 10000) {
    private val started = clock()
    private val deadline = started + timeoutMs
    private val cancelled = AtomicBoolean(false)
    init { require(started >= 0 && timeoutMs in 1..10000 && deadline >= started) }
    fun cancel() { cancelled.set(true) }
    fun remainingMs(): Long {
        if (cancelled.get()) throw KnowledgeFailure("KNOWLEDGE_SESSION_CHANGED")
        val now = clock()
        if (now < started || now >= deadline) throw KnowledgeFailure("KNOWLEDGE_TIMEOUT")
        return deadline - now
    }
    fun check() { remainingMs() }
}
interface KnowledgeDistributionTransport {
    fun manifest(profile: KnowledgeProfile, knownDigest: String?, budget: KnowledgeBudget): JSONObject
    fun pack(profile: KnowledgeProfile, digest: String, budget: KnowledgeBudget): ByteArray
    fun delta(profile: KnowledgeProfile, destination: String, base: String, budget: KnowledgeBudget): JSONObject
}

// These values come only from the main/service-owned reviewed adapter closure.
// Game UI/client source_verified assertions never construct the shipped binding.
internal data class TrustedKnowledgeBinding(val profile: KnowledgeProfile, val sourceId: String, val sessionId: String, val authority: String)
internal data class TrustedKnowledgeObservation(val binding: TrustedKnowledgeBinding, val sourceId: String,
    val observedAtMs: Long, val signals: Map<String, Any?>, val observedMonotonicMs: Long)
data class KnowledgeCacheStatus(val state: String, val digest: String? = null, val remainingLeaseMs: Long? = null, val actionAuthority: Boolean = false)

/** No lease survives restart. A trusted manifest precedes every cache reuse;
 * complete digest/schema/profile validation precedes atomic installation. */
internal class KnowledgeCache(private val directory: File, private val authority: String,
    private val transport: KnowledgeDistributionTransport, private val wallClock: () -> Long = System::currentTimeMillis,
    private val monotonicClock: () -> Long = { System.nanoTime() / 1000000 }) : AutoCloseable {
    private data class Record(val revision: Long, val digest: String?, val revoked: List<String>)
    private data class Lease(val binding: TrustedKnowledgeBinding, val pack: ValidatedKnowledgePack,
        val started: Long, val deadline: Long, val serverTime: Long, val epoch: Long)
    private val lock = Any()
    private val pending = AtomicBoolean(false)
    private val ownerFile: RandomAccessFile
    private val ownerLock: FileLock
    @Volatile private var records = mutableMapOf<String, Record>()
    @Volatile private var active: Lease? = null
    private val epoch = AtomicLong(0)
    private val budget = AtomicReference<KnowledgeBudget?>()
    private var stateInvalid = false
    @Volatile private var closed = false
    init {
        require(authority.isNotEmpty() && authority.length <= 512)
        require((directory.isDirectory || directory.mkdirs()) && directory.isDirectory)
        ownerFile = RandomAccessFile(File(directory, "writer.lock"), "rw")
        ownerLock = try { ownerFile.channel.tryLock() ?: throw IllegalStateException("KNOWLEDGE_CACHE_OWNED") }
        catch (error: Exception) { ownerFile.close(); throw IllegalStateException("KNOWLEDGE_CACHE_OWNED", error) }
        loadState()
    }
    private fun loadState() {
        val file = File(directory, "state.json")
        if (!file.exists()) return
        try {
            val state = strictJson(readBounded(file, 32768), 32768)
            exact(state, setOf("schema_version", "authority", "records"))
            require(strictInteger(state, "schema_version", 1, 1) == 1L && state.get("authority") == authority)
            val stored = state.getJSONObject("records"); require(stored.length() <= 16)
            stored.keys().forEach { key ->
                require(KNOWLEDGE_DIGEST.matches(key))
                val record = stored.getJSONObject(key); exact(record, setOf("revision", "digest", "revoked"))
                val revision = strictInteger(record, "revision", 1)
                val digest = if (record.isNull("digest")) null else strictString(record, "digest", 64).also { require(KNOWLEDGE_DIGEST.matches(it)) }
                val revoked = stringArray(record.getJSONArray("revoked"), 0, 64, 64)
                require(revoked.all { KNOWLEDGE_DIGEST.matches(it) } && revoked.distinct().size == revoked.size && digest !in revoked)
                records[key] = Record(revision, digest, revoked)
            }
        } catch (_: Exception) { records.clear(); stateInvalid = true }
    }
    private fun key(profile: KnowledgeProfile) = knowledgeHash(profile.key().toByteArray(Charsets.UTF_8))
    private fun readBounded(file: File, maximum: Int): ByteArray {
        FileInputStream(file).use { stream ->
            val output = java.io.ByteArrayOutputStream(minOf(maximum, 8192))
            val chunk = ByteArray(8192)
            while (true) {
                val count = stream.read(chunk); if (count < 0) break
                if (output.size() + count > maximum) throw KnowledgeFailure("KNOWLEDGE_SIZE_INVALID")
                output.write(chunk, 0, count)
            }
            return output.toByteArray()
        }
    }
    private fun cached(digest: String, profile: KnowledgeProfile): ByteArray? = try {
        readBounded(File(directory, "$digest.json"), MAX_KNOWLEDGE_BYTES).also { KnowledgeCodec.pack(it, digest, profile) }
    } catch (_: Exception) { null }
    private fun atomicWrite(filename: String, raw: ByteArray, beforePublish: () -> Unit = {}) {
        val temporary = File(directory, ".${UUID.randomUUID()}.tmp")
        try {
            FileOutputStream(temporary).use { it.write(raw); it.fd.sync() }
            beforePublish()
            Files.move(temporary.toPath(), File(directory, filename).toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
        } finally { temporary.delete() }
    }
    private fun persist(key: String, record: Record, beforePublish: () -> Unit) {
        if (key !in records && records.size >= 16) throw KnowledgeFailure("KNOWLEDGE_CACHE_BOUND")
        val next = records.toMutableMap().apply { put(key, record) }
        val values = JSONObject()
        next.forEach { (id, item) -> values.put(id, JSONObject().put("revision", item.revision)
            .put("digest", item.digest ?: JSONObject.NULL).put("revoked", JSONArray(item.revoked))) }
        val raw = JSONObject().put("schema_version", 1).put("authority", authority).put("records", values).toString().toByteArray(Charsets.UTF_8)
        if (raw.size > 32768) throw KnowledgeFailure("KNOWLEDGE_CACHE_BOUND")
        atomicWrite("state.json", raw, beforePublish); records = next
    }
    // Stop invalidates presentation without waiting for network or storage fsync.
    fun clear() { epoch.incrementAndGet(); active = null; budget.get()?.cancel() }
    fun status(): KnowledgeCacheStatus {
        val lease = active ?: return KnowledgeCacheStatus("UNAVAILABLE")
        if (lease.epoch != epoch.get() || closed) return KnowledgeCacheStatus("UNAVAILABLE")
        val now = monotonicClock(); val wall = wallClock()
        if (now < lease.started || now >= lease.deadline || wall <= 0 || wall >= lease.pack.validUntilMs) return KnowledgeCacheStatus("EXPIRED")
        return KnowledgeCacheStatus("READY", lease.pack.digest, lease.deadline - now)
    }
    fun refresh(binding: TrustedKnowledgeBinding): KnowledgeCacheStatus {
        if (!pending.compareAndSet(false, true)) throw KnowledgeFailure("KNOWLEDGE_REFRESH_IN_PROGRESS")
        var requestBudget: KnowledgeBudget? = null
        var operation = -1L
        try {
            val started = monotonicClock()
            val operationBudget = KnowledgeBudget(monotonicClock)
            requestBudget = operationBudget
            val profileKey = key(binding.profile)
            val previous = synchronized(lock) {
                if (closed || stateInvalid) throw KnowledgeFailure("KNOWLEDGE_STATE_INVALID")
                if (binding.authority != authority || binding.sourceId.isEmpty() || binding.sourceId.length > 256 || binding.sessionId.isEmpty() || binding.sessionId.length > 256) throw KnowledgeFailure("KNOWLEDGE_PROFILE_SESSION_INVALID")
                if (active != null && active?.binding != binding) { active = null; epoch.incrementAndGet() }
                operation = epoch.get(); budget.set(operationBudget); records[profileKey]
            }
            fun current() { operationBudget.check(); if (operation != epoch.get() || closed) throw KnowledgeFailure("KNOWLEDGE_SESSION_CHANGED") }
            val manifest = transport.manifest(binding.profile, previous?.digest, operationBudget); current()
            exact(manifest, setOf("schema_version", "status", "profile", "revision", "digest", "version", "lease_until_ms", "server_time_ms", "execution_authority"))
            require(strictInteger(manifest, "schema_version", 1, 1) == 1L && manifest.get("execution_authority") == false)
            require(KnowledgeProfile.fromJson(manifest.getJSONObject("profile"), true) == binding.profile)
            val revision = strictInteger(manifest, "revision")
            val serverTime = strictInteger(manifest, "server_time_ms", 1)
            val state = strictString(manifest, "status", 16)
            require(state in setOf("available", "unchanged", "revoked", "unavailable"))
            if (previous != null && revision < previous.revision) throw KnowledgeFailure("KNOWLEDGE_REVISION_ROLLBACK")
            if (state == "revoked" || state == "unavailable") {
                val revoked = previous?.revoked.orEmpty().toMutableList()
                if (state == "revoked") {
                    val digest = strictString(manifest, "digest", 64); require(KNOWLEDGE_DIGEST.matches(digest))
                    if (digest !in revoked) revoked += digest
                }
                require(revoked.size <= 64)
                synchronized(lock) {
                    current(); active = null
                    if (revision > 0) persist(profileKey, Record(revision, null, revoked), ::current)
                }
                return status()
            }
            val digest = strictString(manifest, "digest", 64)
            val version = strictString(manifest, "version", 64)
            val until = strictInteger(manifest, "lease_until_ms", 1)
            val duration = until - serverTime
            require(KNOWLEDGE_DIGEST.matches(digest) && revision > 0 && duration in 1..60000)
            if (digest in previous?.revoked.orEmpty() || previous != null && revision == previous.revision && previous.digest != digest) throw KnowledgeFailure("KNOWLEDGE_REVOKED_OR_INVALID_REVISION")
            var raw = cached(digest, binding.profile)
            if (raw == null && previous?.digest != null && previous.digest != digest) {
                val base = cached(previous.digest, binding.profile)
                if (base != null) {
                    try {
                        val envelope = transport.delta(binding.profile, digest, previous.digest, operationBudget); current()
                        raw = KnowledgeCodec.delta(base, envelope, digest, binding.profile)
                    } catch (error: KnowledgeFailure) { if (error.code != "KNOWLEDGE_DELTA_UNAVAILABLE") throw error }
                }
            }
            if (raw == null) raw = transport.pack(binding.profile, digest, operationBudget)
            current()
            val destination = requireNotNull(raw)
            val pack = KnowledgeCodec.pack(destination, digest, binding.profile)
            val elapsed = monotonicClock() - started
            require(pack.version == version && pack.validUntilMs >= until && started >= 0 && elapsed in 0 until duration)
            synchronized(lock) {
                current(); atomicWrite("$digest.json", destination, ::current)
                persist(profileKey, Record(revision, digest, previous?.revoked.orEmpty()), ::current)
                current(); active = Lease(binding, pack, started, started + duration, serverTime, operation)
                val referenced = records.values.mapNotNull { it.digest }.toSet()
                directory.listFiles()?.filter { KNOWLEDGE_DIGEST.matches(it.name.removeSuffix(".json")) && it.name.endsWith(".json") && it.name.removeSuffix(".json") !in referenced }?.forEach { it.delete() }
            }
            return status()
        } catch (error: Exception) {
            synchronized(lock) {
                if (operation == epoch.get() && (error !is KnowledgeFailure || error.code !in setOf("KNOWLEDGE_NETWORK_ERROR", "KNOWLEDGE_TIMEOUT"))) active = null
            }
            if (error is KnowledgeFailure) throw error
            throw KnowledgeFailure("KNOWLEDGE_INVALID")
        } finally { if (requestBudget != null) budget.compareAndSet(requestBudget, null); pending.set(false) }
    }
    fun evaluate(observation: TrustedKnowledgeObservation, locale: String): List<KnowledgeRecommendation> {
        val lease = active ?: return emptyList()
        if (lease.epoch != epoch.get() || status().state != "READY" || observation.binding != lease.binding || observation.sourceId != lease.binding.sourceId) return emptyList()
        val mono = monotonicClock(); val wall = wallClock()
        val now = maxOf(wall, lease.serverTime + mono - lease.started)
        if (now >= lease.pack.validUntilMs || observation.observedAtMs <= 0 || observation.observedAtMs > now ||
            now - observation.observedAtMs > lease.pack.maxStateAgeMs || observation.observedMonotonicMs < 0 ||
            observation.observedMonotonicMs > mono || mono - observation.observedMonotonicMs > lease.pack.maxStateAgeMs) return emptyList()
        if (records[key(lease.binding.profile)]?.digest != lease.pack.digest) return emptyList()
        val result = lease.pack.evaluate(observation.signals, locale, observation.observedAtMs)
        return if (lease.epoch == epoch.get()) result else emptyList()
    }
    override fun close() = synchronized(lock) {
        if (!closed) { clear(); closed = true; ownerLock.release(); ownerFile.close() }
    }
}
