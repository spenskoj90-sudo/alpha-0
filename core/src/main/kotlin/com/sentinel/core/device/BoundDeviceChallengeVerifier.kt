package com.sentinel.core.device

/**
 * Composition boundary that prevents a valid cryptographic proof from bypassing
 * enrollment state. Revoked devices are denied even if a previously issued
 * challenge remains cryptographically valid.
 */
class BoundDeviceChallengeVerifier(
    private val registry: DeviceRegistry,
    private val verifier: DeviceChallengeVerifier
) {
    fun verify(proof: PresentedDeviceProof): DeviceVerificationResult {
        if (proof.publicKeyEncoded.isEmpty() || proof.publicKeyEncoded.size > 512) {
            return DeviceVerificationResult.Rejected(DeviceVerificationFailure.MALFORMED_REQUEST)
        }
        val fingerprint = java.security.MessageDigest.getInstance("SHA-256")
            .digest(proof.publicKeyEncoded)
            .joinToString("") { "%02x".format(it.toInt() and 0xff) }
        if (!registry.isActive(fingerprint)) {
            return DeviceVerificationResult.Rejected(DeviceVerificationFailure.DEVICE_MISMATCH)
        }
        return verifier.verify(proof)
    }
}
