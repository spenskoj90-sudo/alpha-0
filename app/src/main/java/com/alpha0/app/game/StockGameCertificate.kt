package com.alpha0.app.game

import java.security.MessageDigest

/** Observed current APK signer fingerprint, not publisher or capture-source attestation. */
internal object StockGameCertificate {
    fun digest(currentSigners: List<ByteArray>): String? {
        val cert = currentSigners.singleOrNull() ?: return null
        if (cert.isEmpty() || cert.size > 16384) return null
        val hash = MessageDigest.getInstance("SHA-256").digest(cert)
        val digits = "0123456789abcdef"
        return buildString(hash.size * 2) {
            for (byte in hash) {
                val n = byte.toInt() and 0xff
                append(digits[n ushr 4])
                append(digits[n and 15])
            }
        }
    }
}
