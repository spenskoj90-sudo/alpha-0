package com.alpha0.app.game

/** A display-only fingerprint. Its existence never authorizes game capture trust. */
internal object GameSignerFingerprint {
    private val digestPattern = Regex("[0-9a-f]{64}")

    /** Eight spaced groups keep all SHA-256 hex digits readable on narrow screens. */
    fun grouped(sha256: String?): String? = sha256
        ?.takeIf(digestPattern::matches)
        ?.chunked(8)
        ?.joinToString(" ")
}
