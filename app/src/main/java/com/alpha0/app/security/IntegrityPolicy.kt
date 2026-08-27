package com.alpha0.app.security

enum class IntegrityTier {
    MEETS_STRONG_INTEGRITY,
    MEETS_DEVICE_INTEGRITY,
    MEETS_BASIC_INTEGRITY,
    FAILED,
    UNKNOWN
}

object IntegrityPolicy {
    private val criticalActions = setOf(
        "device:rotate",
        "device:revoke",
        "event:write",
        "admin:entitlement:create",
        "knowledge:recommend"
    )
    private val basicActions = setOf("character:read", "game:read", "audit:read")

    fun classify(verdicts: Set<String>): IntegrityTier {
        return when {
            "MEETS_STRONG_INTEGRITY" in verdicts -> IntegrityTier.MEETS_STRONG_INTEGRITY
            "MEETS_DEVICE_INTEGRITY" in verdicts -> IntegrityTier.MEETS_DEVICE_INTEGRITY
            "MEETS_BASIC_INTEGRITY" in verdicts -> IntegrityTier.MEETS_BASIC_INTEGRITY
            verdicts.isEmpty() -> IntegrityTier.UNKNOWN
            else -> IntegrityTier.FAILED
        }
    }

    fun allows(tier: IntegrityTier, action: String): Boolean {
        return when (tier) {
            IntegrityTier.MEETS_STRONG_INTEGRITY -> true
            IntegrityTier.MEETS_DEVICE_INTEGRITY -> action !in criticalActions
            IntegrityTier.MEETS_BASIC_INTEGRITY -> action in basicActions
            IntegrityTier.FAILED, IntegrityTier.UNKNOWN -> false
        }
    }
}
