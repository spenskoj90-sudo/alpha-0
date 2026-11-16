package com.alpha0.app.game

import java.net.URI
import java.util.Locale

/**
 * A browser package, user-entered URL or a MediaProjection frame alone do not prove
 * which website owns the captured pixels. Only a separately verified origin,
 * foreground-window binding and matching capture generation can qualify.
 *
 * No production source currently issues such an attestation for LastHavens.
 */
internal data class BrowserGameTarget(
    val gameId: String,
    val exactHttpsUrl: String,
    val permittedBrowserPackages: Set<String>,
    val rulesRevision: String,
)

internal enum class BrowserOriginProofKind {
    NONE,
    TRUSTED_VISIBLE_ADDRESS_BAR,
    VERIFIED_DIGITAL_ASSET_LINKS,
}

internal data class BrowserSourceEvidence(
    val claimedGameId: String? = null,
    val claimedUrl: String? = null,
    val foregroundPackageName: String? = null,
    val originProofKind: BrowserOriginProofKind = BrowserOriginProofKind.NONE,
    /** This MUST come from an independent trusted adapter, never an in-app checkbox. */
    val originEvidenceVerified: Boolean = false,
    val selectedWindowBoundToCapture: Boolean = false,
    val captureGeneration: String? = null,
    val attestedCaptureGeneration: String? = null,
    val observedElapsedRealtimeMs: Long? = null,
    val checkedElapsedRealtimeMs: Long = 0L,
)

internal enum class BrowserSourceBlock {
    TARGET_ID_MISMATCH,
    URL_NOT_EXACT_HTTPS_TARGET,
    BROWSER_NOT_ALLOWED,
    TRUSTED_ORIGIN_PROOF_MISSING,
    WINDOW_NOT_BOUND,
    CAPTURE_GENERATION_MISMATCH,
    OBSERVATION_NOT_FRESH,
}

internal data class BrowserSourceDecision(val blockers: List<BrowserSourceBlock>) {
    val sourceVerified: Boolean get() = blockers.isEmpty()
}

/** Generic browser-origin gate. This does not grant game-action authority. */
internal object BrowserGameSourcePolicy {
    const val MAX_SOURCE_AGE_MS = 2_000L

    val LASTHAVENS = BrowserGameTarget(
        gameId = "lasthavens-browser",
        exactHttpsUrl = "https://lasthavens.com/play",
        permittedBrowserPackages = setOf("com.android.chrome"),
        rulesRevision = "lasthavens-terms-2026-11-01-rule-5",
    )

    fun evaluate(target: BrowserGameTarget, evidence: BrowserSourceEvidence): BrowserSourceDecision {
        val blocks = buildList {
            if (target.gameId.isBlank() || evidence.claimedGameId != target.gameId) {
                add(BrowserSourceBlock.TARGET_ID_MISMATCH)
            }
            if (!isExactHttpsPage(target.exactHttpsUrl, evidence.claimedUrl)) {
                add(BrowserSourceBlock.URL_NOT_EXACT_HTTPS_TARGET)
            }
            if (evidence.foregroundPackageName !in target.permittedBrowserPackages ||
                evidence.foregroundPackageName.isNullOrBlank()
            ) {
                add(BrowserSourceBlock.BROWSER_NOT_ALLOWED)
            }
            if (evidence.originProofKind == BrowserOriginProofKind.NONE ||
                !evidence.originEvidenceVerified
            ) {
                add(BrowserSourceBlock.TRUSTED_ORIGIN_PROOF_MISSING)
            }
            if (!evidence.selectedWindowBoundToCapture) {
                add(BrowserSourceBlock.WINDOW_NOT_BOUND)
            }
            if (evidence.captureGeneration.isNullOrBlank() ||
                evidence.captureGeneration != evidence.attestedCaptureGeneration
            ) {
                add(BrowserSourceBlock.CAPTURE_GENERATION_MISMATCH)
            }
            val frameAt = evidence.observedElapsedRealtimeMs
            val checkedAt = evidence.checkedElapsedRealtimeMs
            if (frameAt == null || frameAt < 0L || checkedAt < frameAt ||
                checkedAt - frameAt > MAX_SOURCE_AGE_MS
            ) {
                add(BrowserSourceBlock.OBSERVATION_NOT_FRESH)
            }
        }
        return BrowserSourceDecision(blocks)
    }

    private fun isExactHttpsPage(expectedUrl: String, receivedUrl: String?): Boolean {
        if (receivedUrl.isNullOrBlank()) return false
        return try {
            fun parse(raw: String): URI {
                require(raw.length <= 2048 && raw == raw.trim() && !raw.any { it.isWhitespace() })
                val uri = URI(raw)
                require(!uri.isOpaque && uri.scheme?.lowercase(Locale.ROOT) == "https")
                require(uri.rawUserInfo == null && uri.port == -1)
                require(uri.host != null && uri.rawQuery == null && uri.rawFragment == null)
                require(uri.rawPath != null && !uri.rawPath.contains('%'))
                return uri
            }
            val expected = parse(expectedUrl)
            val received = parse(receivedUrl)
            expected.host.equals(received.host, ignoreCase = true) &&
                expected.rawPath == received.rawPath &&
                expected.scheme.equals(received.scheme, ignoreCase = true)
        } catch (_: IllegalArgumentException) {
            false
        } catch (_: java.net.URISyntaxException) {
            false
        }
    }
}

/** Consent is scoped to the exact game and published rule revision; never global. */
internal data class GameRiskAcknowledgement(
    val gameId: String,
    val rulesRevision: String,
    val warningAcknowledged: Boolean,
    val rulesReviewed: Boolean,
) {
    fun appliesTo(target: BrowserGameTarget): Boolean =
        gameId.isNotBlank() && gameId == target.gameId &&
            rulesRevision.isNotBlank() && rulesRevision == target.rulesRevision &&
            warningAcknowledged && rulesReviewed
}
