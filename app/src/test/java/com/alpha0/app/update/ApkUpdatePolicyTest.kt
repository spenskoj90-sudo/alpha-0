package com.alpha0.app.update

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ApkUpdatePolicyTest {
    private val packageName = "com.alpha0.app.physicaltest"
    private val originalSigner = "a".repeat(64)
    private val otherSigner = "b".repeat(64)

    private fun check(
        candidatePackage: String = packageName,
        candidateVersion: Long = 100000752,
        candidateSigners: List<String> = listOf(originalSigner),
        installedSigners: List<String> = listOf(originalSigner),
    ) = ApkUpdatePolicy.check(
        packageName, 100000718, installedSigners,
        candidatePackage, candidateVersion, candidateSigners,
    )

    @Test fun sameSignerSamePackageIncreasingCodeIsEligible() {
        assertNull(check())
    }

    @Test fun higherVersionWithDifferentSignerIsBlocked() {
        assertEquals(ApkUpdatePolicy.BlockReason.SIGNER_MISMATCH, check(candidateSigners = listOf(otherSigner)))
    }

    @Test fun differentPackageCannotReplaceInstalledApp() {
        assertEquals(ApkUpdatePolicy.BlockReason.PACKAGE_MISMATCH, check(candidatePackage = "com.alpha0.app"))
    }

    @Test fun nonIncreasingVersionIsBlocked() {
        assertEquals(ApkUpdatePolicy.BlockReason.VERSION_NOT_HIGHER, check(candidateVersion = 100000718))
        assertEquals(ApkUpdatePolicy.BlockReason.VERSION_NOT_HIGHER, check(candidateVersion = 100000717))
    }

    @Test fun missingMalformedAndMultipleCertificatesFailClosed() {
        assertEquals(ApkUpdatePolicy.BlockReason.SIGNER_UNVERIFIED, check(candidateSigners = emptyList()))
        assertEquals(ApkUpdatePolicy.BlockReason.SIGNER_UNVERIFIED, check(installedSigners = emptyList()))
        assertEquals(ApkUpdatePolicy.BlockReason.SIGNER_UNVERIFIED, check(candidateSigners = listOf("bad")))
        assertEquals(
            ApkUpdatePolicy.BlockReason.SIGNER_UNVERIFIED,
            check(candidateSigners = listOf(originalSigner, otherSigner)),
        )
    }
}
