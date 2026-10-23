package com.alpha0.app.update

/** Conservative in-place APK replacement policy; Android remains the final install authority. */
internal object ApkUpdatePolicy {
    enum class BlockReason {
        PACKAGE_MISMATCH, VERSION_NOT_HIGHER, SIGNER_UNVERIFIED, SIGNER_MISMATCH
    }

    fun check(
        installedPackage: String,
        installedVersion: Long,
        installedSignerDigests: List<String>,
        candidatePackage: String,
        candidateVersion: Long,
        candidateSignerDigests: List<String>,
    ): BlockReason? {
        if (installedPackage != candidatePackage) return BlockReason.PACKAGE_MISMATCH
        if (installedVersion <= 0L || candidateVersion <= installedVersion) return BlockReason.VERSION_NOT_HIGHER
        val fingerprint = Regex("[0-9a-f]{64}")
        if (
            installedSignerDigests.size != 1 || candidateSignerDigests.size != 1 ||
            !fingerprint.matches(installedSignerDigests.single()) ||
            !fingerprint.matches(candidateSignerDigests.single())
        ) return BlockReason.SIGNER_UNVERIFIED
        if (installedSignerDigests.single() != candidateSignerDigests.single()) {
            return BlockReason.SIGNER_MISMATCH
        }
        return null
    }
}
