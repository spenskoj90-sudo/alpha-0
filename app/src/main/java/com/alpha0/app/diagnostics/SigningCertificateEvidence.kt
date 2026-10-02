package com.alpha0.app.diagnostics

import java.security.MessageDigest

/** Public certificate metadata only; no private key or device identity access. */
object SigningCertificateEvidence {
    private fun hashes(certificates: List<ByteArray>, limit: Int): List<String> {
        require(certificates.size <= limit) { "SIGNING_IDENTITY_UNAVAILABLE" }
        return certificates.map { certificate ->
            require(certificate.isNotEmpty() && certificate.size <= 16_384) { "SIGNING_IDENTITY_UNAVAILABLE" }
            MessageDigest.getInstance("SHA-256").digest(certificate)
                .joinToString("") { byte -> "%02x".format(byte.toInt() and 0xff) }
        }.also { require(it.distinct().size == it.size) { "SIGNING_IDENTITY_UNAVAILABLE" } }
    }

    fun details(
        packageName: String,
        versionCode: Long,
        currentSigners: List<ByteArray>,
        history: List<ByteArray>,
        multipleSigners: Boolean,
    ): Map<String, Any> {
        require(packageName.length <= 200 && Regex("[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z][A-Za-z0-9_]*)+").matches(packageName))
        require(versionCode in 1..2_100_000_000L)
        val current = hashes(currentSigners, 4).sorted()
        val pastAndCurrent = hashes(history, 8)
        require(current.isNotEmpty()) { "SIGNING_IDENTITY_UNAVAILABLE" }
        if (multipleSigners) {
            require(current.size >= 2 && pastAndCurrent.isEmpty()) { "SIGNING_IDENTITY_UNAVAILABLE" }
        } else {
            require(current.size == 1 && current.single() in pastAndCurrent) { "SIGNING_IDENTITY_UNAVAILABLE" }
        }
        return mapOf(
            "package_name" to packageName,
            "installed_version_code" to versionCode,
            "signer_count" to current.size,
            "signer_cert_sha256" to current.joinToString(","),
            "signer_history_sha256" to pastAndCurrent.joinToString(","),
            "multiple_signers" to multipleSigners,
            "identity_evidence" to "PACKAGE_MANAGER",
        )
    }
}
