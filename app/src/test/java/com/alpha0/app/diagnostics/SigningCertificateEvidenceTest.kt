package com.alpha0.app.diagnostics

import org.junit.Assert.*
import org.junit.Test

class SigningCertificateEvidenceTest {
    private val certificate = "abc".toByteArray()
    private val expected = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"

    @Test fun records_public_digest_and_actual_package_without_raw_certificate() {
        val details = SigningCertificateEvidence.details("com.alpha0.app.physicaltest", 100000525, listOf(certificate), listOf(certificate), false)
        assertEquals(expected, details["signer_cert_sha256"])
        assertEquals(expected, details["signer_history_sha256"])
        assertEquals("com.alpha0.app.physicaltest", details["package_name"])
        assertEquals(100000525L, details["installed_version_code"])
        assertFalse(details.toString().contains("abc"))
        assertTrue(details.keys.none { DiagnosticLogger.isSensitiveDetailKey(it) })
        assertFalse(details.containsKey("signerLineageVerified"))
    }

    @Test fun rotation_history_does_not_claim_update_compatibility() {
        val details = SigningCertificateEvidence.details("com.alpha0.app", 2, listOf(certificate), listOf("old".toByteArray(), certificate), false)
        assertEquals(2, details["signer_history_sha256"].toString().split(",").size)
        assertFalse(details.containsKey("updateCompatible"))
    }

    @Test fun multiple_signers_are_distinct_from_rotation() {
        val details = SigningCertificateEvidence.details("com.alpha0.app", 2, listOf(certificate, "other".toByteArray()), emptyList(), true)
        assertEquals(2, details["signer_count"])
        assertEquals("", details["signer_history_sha256"])
        assertEquals(true, details["multiple_signers"])
    }

    @Test fun rejects_missing_inconsistent_duplicate_and_unbounded_certificates() {
        val invalid = listOf(
            Pair(emptyList<ByteArray>(), emptyList()),
            Pair(listOf(byteArrayOf()), listOf(byteArrayOf())),
            Pair(listOf(ByteArray(16_385)), listOf(ByteArray(16_385))),
            Pair(listOf(certificate), listOf("other".toByteArray())),
            Pair(listOf(certificate, certificate), emptyList()),
            Pair(listOf(certificate), List(9) { certificate }),
        )
        invalid.forEach { (current, history) ->
            assertThrows(IllegalArgumentException::class.java) {
                SigningCertificateEvidence.details("com.alpha0.app", 2, current, history, false)
            }
        }
    }
}
