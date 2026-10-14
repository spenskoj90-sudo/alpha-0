package com.alpha0.app.knowledge

import android.content.Context
import android.os.SystemClock
import com.alpha0.app.BuildConfig
import com.alpha0.app.game.GameObservationRuntime
import com.alpha0.app.security.SecureSessionStore
import java.io.File
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

/** Single process/service-owned consumer. The shipped recognition adapter is
 * UNCALIBRATED; neither UI fields nor OCR/client flags may grant trust. */
object AndroidKnowledgeRuntime {
    private val mutableState = MutableStateFlow(KnowledgeViewState("STOPPED"))
    val state = mutableState.asStateFlow()
    private var controller: KnowledgePresentation? = null
    private var transport: KnowledgeHttpTransport? = null

    @Synchronized fun install(context: Context) {
        if (controller != null) return
        val application = context.applicationContext
        val origin = BuildConfig.SENTINEL_API_BASE_URL.trimEnd('/')
        val store = SecureSessionStore()
        val broker = object : KnowledgeSessionBroker {
            override val origin = origin
            private fun snapshot(session: SecureSessionStore.Companion.Session) =
                KnowledgeSessionSnapshot(origin, session.epoch.toString(), session.accessToken, session.refreshToken)
            override fun snapshot() = store.load(application)?.let(::snapshot)
            override fun rotate(expected: KnowledgeSessionSnapshot, access: String, refresh: String): Boolean {
                val current = store.load(application) ?: return false
                return snapshot(current) == expected && store.replaceIfCurrent(application, current, access, refresh)
            }
            override fun invalidate(expected: KnowledgeSessionSnapshot): Boolean {
                val current = store.load(application) ?: return false
                val cleared = snapshot(current) == expected && store.clearIfCurrent(application, current)
                if (cleared) GameObservationRuntime.stop("SESSION_CLOSED")
                return cleared
            }
        }
        val http = KnowledgeHttpTransport(broker)
        transport = http
        controller = KnowledgePresentation(
            getBinding = { verifiedBinding() },
            getObservation = { verifiedObservation() },
            cacheFactory = { authority ->
                require(authority == origin)
                KnowledgeCache(File(application.noBackupFilesDir, "knowledge-${knowledgeHash(origin.toByteArray(Charsets.UTF_8))}"),
                    origin, http, monotonicClock = SystemClock::elapsedRealtime)
            },
            locale = { application.resources.configuration.locales.get(0).language },
            onChange = { mutableState.value = it },
            clock = SystemClock::elapsedRealtime,
        )
    }
    // A reviewed exact target/version/environment/source calibration is required
    // before implementing these adapters. Fixtures never populate either closure.
    private fun verifiedBinding(): TrustedKnowledgeBinding? = null
    private fun verifiedObservation(): TrustedKnowledgeObservation? = null
    @Synchronized internal fun start() { controller?.start() }
    @Synchronized internal fun stop() { controller?.stop(); mutableState.value = KnowledgeViewState("STOPPED") }
}
