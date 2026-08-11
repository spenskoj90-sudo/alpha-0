package com.alpha0.app.security

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.MessageDigest
import java.security.PrivateKey
import java.security.PublicKey
import java.security.Signature
import java.security.spec.ECGenParameterSpec

class DeviceIdentity {

    companion object {
        private const val KEYSTORE_PROVIDER = "AndroidKeyStore"
        private const val KEY_ALIAS = "alpha0.device.identity.v1"

        private const val CURVE = "secp256r1"
        private const val SIGNATURE_ALGORITHM = "SHA256withECDSA"
        private const val HASH_ALGORITHM = "SHA-256"
        private val KEY_CREATION_LOCK = Any()
    }

    data class IdentityInfo(
        val fingerprint: String,
        val algorithm: String
    )

    private fun loadKeyStore(): KeyStore {
        return KeyStore.getInstance(KEYSTORE_PROVIDER).apply {
            load(null)
        }
    }

    private fun ensureKeyExists() {
        synchronized(KEY_CREATION_LOCK) {
            val keyStore = loadKeyStore()

            if (keyStore.containsAlias(KEY_ALIAS)) {
                return
            }

            val generator = KeyPairGenerator.getInstance(
                KeyProperties.KEY_ALGORITHM_EC,
                KEYSTORE_PROVIDER
            )

            val spec = KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY
            )
                .setAlgorithmParameterSpec(ECGenParameterSpec(CURVE))
                .setDigests(KeyProperties.DIGEST_SHA256)
                .build()

            generator.initialize(spec)
            generator.generateKeyPair()
        }
    }

    private fun getPrivateKey(): PrivateKey {
        ensureKeyExists()

        return loadKeyStore().getKey(KEY_ALIAS, null) as? PrivateKey
            ?: throw IllegalStateException("SENTINEL private key is unavailable")
    }

    private fun getPublicKey(): PublicKey {
        ensureKeyExists()

        return loadKeyStore().getCertificate(KEY_ALIAS)?.publicKey
            ?: throw IllegalStateException("SENTINEL public key is unavailable")
    }

    fun getIdentityInfo(): IdentityInfo {
        val publicKey = getPublicKey()
        val fingerprint = MessageDigest
            .getInstance(HASH_ALGORITHM)
            .digest(publicKey.encoded)
            .let(Hex::encode)

        return IdentityInfo(
            fingerprint = fingerprint,
            algorithm = "EC / $CURVE / $SIGNATURE_ALGORITHM"
        )
    }

    /**
     * Android Keystore private keys are intentionally non-exportable. The provider
     * exposes no encoded private-key material; a non-null encoding would indicate
     * that the provider contract has changed and should fail the self-test.
     */
    fun isPrivateKeyNonExportable(): Boolean {
        return try {
            getPrivateKey().encoded == null
        } catch (_: Exception) {
            false
        }
    }

    fun sign(challenge: ByteArray): ByteArray {
        require(challenge.isNotEmpty()) { "Challenge must not be empty" }

        return Signature
            .getInstance(SIGNATURE_ALGORITHM)
            .apply {
                initSign(getPrivateKey())
                update(challenge)
            }
            .sign()
    }

    fun verify(challenge: ByteArray, signatureBytes: ByteArray): Boolean {
        if (challenge.isEmpty() || signatureBytes.isEmpty()) {
            return false
        }

        return try {
            Signature
                .getInstance(SIGNATURE_ALGORITHM)
                .apply {
                    initVerify(getPublicKey())
                    update(challenge)
                }
                .verify(signatureBytes)
        } catch (_: Exception) {
            false
        }
    }
}
