package com.alpha0.app.knowledge

import java.util.concurrent.Executors
import java.util.concurrent.ScheduledFuture
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicLong

data class KnowledgeViewState(val state: String, val items: List<KnowledgeRecommendation> = emptyList(), val actionAuthority: Boolean = false)

/** The adapter closures are service-owned. No renderer/OCR assertion is a trust
 * input. One actor owns cache creation/refresh; Stop never waits for that actor. */
internal class KnowledgePresentation(private val getBinding: () -> TrustedKnowledgeBinding?,
    private val getObservation: () -> KnowledgeObservationInput, private val cacheFactory: (String) -> KnowledgeCache,
    private val locale: () -> String = { "en" }, private val onChange: (KnowledgeViewState) -> Unit = {},
    private val clock: () -> Long = { System.nanoTime() / 1000000 }) : AutoCloseable {
    private val lifecycle = Any()
    private val epoch = AtomicLong()
    private val running = AtomicBoolean(false)
    private val refreshing = AtomicBoolean(false)
    private val closed = AtomicBoolean(false)
    private val worker = Executors.newSingleThreadScheduledExecutor { job -> Thread(job, "sentinel-knowledge-consumer").apply { isDaemon = true } }
    @Volatile private var cache: KnowledgeCache? = null
    @Volatile private var cacheAuthority: String? = null
    @Volatile private var binding: TrustedKnowledgeBinding? = null
    @Volatile private var last = KnowledgeViewState("STOPPED")
    @Volatile private var sourceFailureLatched = false
    private var timer: ScheduledFuture<*>? = null
    @Volatile private var lastRefresh = Long.MIN_VALUE

    fun state(): KnowledgeViewState = try {
        when {
            !running.get() -> KnowledgeViewState("STOPPED")
            sourceFailureLatched -> KnowledgeViewState("UNAVAILABLE")
            else -> evaluateState()
        }
    } catch (_: Exception) {
        // Service callback failure must never strand previously published advice.
        sourceFailureLatched = true
        cache?.clear()
        KnowledgeViewState("UNAVAILABLE")
    }
    private fun evaluateState(): KnowledgeViewState {
        val current = getBinding()
        if (current == null || current != binding) {
            cache?.clear()
            return KnowledgeViewState("WAITING_FOR_VERIFIED_PROFILE")
        }
        val stored = cache ?: return last
        val status = stored.status()
        if (status.state != "READY") return if (last.state in setOf("DENIED", "UNAVAILABLE", "LOADING")) last else KnowledgeViewState("UNAVAILABLE")
        val input = getObservation()
        val result = when (input) {
            KnowledgeObservationInput.AwaitingFirstFrame -> {
                stored.observationAwaitingFirstFrame()
                KnowledgeViewState("WAITING_FOR_VERIFIED_OBSERVATION")
            }
            is KnowledgeObservationInput.Processing ->
                if (stored.observationProcessing(input.sequence, input.capturedMonotonicMs))
                    KnowledgeViewState("WAITING_FOR_VERIFIED_OBSERVATION") else KnowledgeViewState("UNAVAILABLE")
            KnowledgeObservationInput.Unavailable -> {
                stored.observationUnavailable()
                KnowledgeViewState("UNAVAILABLE")
            }
            is KnowledgeObservationInput.Frame -> KnowledgeViewState("READY", stored.evaluate(input.value, locale()))
        }
        if (!running.get() || getBinding() != current) return KnowledgeViewState("WAITING_FOR_VERIFIED_PROFILE")
        return if (stored.observationBlocked()) KnowledgeViewState("UNAVAILABLE") else result
    }
    fun start() = synchronized(lifecycle) {
        if (closed.get()) return@synchronized
        if (running.getAndSet(true)) return@synchronized
        epoch.incrementAndGet(); lastRefresh = Long.MIN_VALUE; sourceFailureLatched = false
        val initial = try { getBinding() } catch (_: Exception) { sourceFailureLatched = true; null }
        last = KnowledgeViewState(when {
            sourceFailureLatched -> "UNAVAILABLE"
            initial == null -> "WAITING_FOR_VERIFIED_PROFILE"
            else -> "LOADING"
        })
        onChange(last)
        timer = worker.scheduleAtFixedRate({
            val operation = epoch.get()
            if (running.get()) {
                val value = try {
                    val now = clock()
                    if (lastRefresh == Long.MIN_VALUE || now < lastRefresh || now - lastRefresh >= 30000) refresh(operation)
                    state()
                } catch (_: Exception) {
                    sourceFailureLatched = true
                    cache?.clear()
                    KnowledgeViewState("UNAVAILABLE")
                }
                publish(operation, value)
            }
        }, 0, 1, TimeUnit.SECONDS)
    }
    private fun publish(operation: Long, value: KnowledgeViewState) = synchronized(lifecycle) {
        if (running.get() && operation == epoch.get()) { last = value; onChange(value) }
    }
    private fun refresh(operation: Long) {
        if (sourceFailureLatched || !refreshing.compareAndSet(false, true)) return
        try {
            lastRefresh = clock()
            val trusted = getBinding() ?: run { cache?.clear(); binding = null; publish(operation, KnowledgeViewState("WAITING_FOR_VERIFIED_PROFILE")); return }
            if (!running.get() || operation != epoch.get()) return
            if (cacheAuthority != trusted.authority) {
                cache?.close(); cache = null; cacheAuthority = null
                val opened = cacheFactory(trusted.authority)
                if (!running.get() || operation != epoch.get()) { opened.close(); return }
                cache = opened; cacheAuthority = trusted.authority
            }
            binding = trusted
            cache!!.refresh(trusted)
            if (getBinding() != trusted) { cache?.clear(); publish(operation, KnowledgeViewState("WAITING_FOR_VERIFIED_PROFILE")); return }
            publish(operation, state())
        } catch (error: Exception) {
            val network = error is KnowledgeFailure && error.code in setOf("KNOWLEDGE_NETWORK_ERROR", "KNOWLEDGE_TIMEOUT")
            if (!network) cache?.clear()
            val value = if (network && cache?.status()?.state == "READY") state()
                else KnowledgeViewState(if (error is KnowledgeFailure && error.code == "KNOWLEDGE_ACCESS_DENIED") "DENIED" else "UNAVAILABLE")
            publish(operation, value)
        } finally { refreshing.set(false); if (closed.get()) { cache?.close(); cache = null } }
    }
    fun stop() = synchronized(lifecycle) {
        running.set(false); epoch.incrementAndGet(); cache?.clear()
        timer?.cancel(true); timer = null; binding = null
        last = KnowledgeViewState("STOPPED"); onChange(last)
    }
    override fun close() {
        closed.set(true)
        stop(); worker.shutdownNow()
        // Cache writer lock is released by the same actor after outstanding I/O.
        if (worker.awaitTermination(1, TimeUnit.SECONDS)) cache?.close()
    }
}
