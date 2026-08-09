package com.alpha0.app.security

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyInfo
import android.security.keystore.KeyProperties
import java.security.KeyFactory
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.MessageDigest
import java.security.PrivateKey
import java.security.Signature
import java.security.spec.ECGenParameterSpec
import java.util.Locale

class DeviceIdentity {

    companion object {
        private const val KEYSTORE_PROVIDER = "AndroidKeyStore"
        private const val KEY_ALIAS = "alpha0.device.identity.v1"
        private const val HASH_ALGORITHM = "SHA-256"
        private const val SIGNATURE_ALGORITHM = "SHA256withECDSA"
        private const val CURVE = "secp256r1"
    }

    data class IdentityInfo(
        val fingerprint: String,
        val algorithm: String,
        val hardwareBacked: Boolean
    )

    private fun loadKeyStore(): KeyStore {
        return KeyStore.getInstance(KEYSTORE_PROVIDER).apply {
            load(null)
        }
    }

    private fun ensureKeyExists() {
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
            .setAlgorithmParameterSpec(
                ECGenParameterSpec(CURVE)
            )
            .setDigests(KeyProperties.DIGEST_SHA256)
            .build()

        generator.initialize(spec)
        generator.generateKeyPair()
    }

    private fun getPrivateKey(): PrivateKey {
        ensureKeyExists()

        val keyStore = loadKeyStore()

        return keyStore.getKey(KEY_ALIAS, null) as PrivateKey
    }

    private fun getPublicKeyBytes(): ByteArray {
        ensureKeyExists()

        val keyStore = loadKeyStore()

        return keyStore
            .getCertificate(KEY_ALIAS)
            .publicKey
            .encoded
    }

    fun getIdentityInfo(): IdentityInfo {
        val privateKey = getPrivateKey()
        val publicKey = getPublicKeyBytes()

        val fingerprint = MessageDigest
            .getInstance(HASH_ALGORITHM)
            .digest(publicKey)
            .toHex()

        val keyFactory = KeyFactory.getInstance(
            privateKey.algorithm,
            KEYSTORE_PROVIDER
        )

        val keyInfo = keyFactory
            .getKeySpec(privateKey, KeyInfo::class.java)

        return IdentityInfo(
            fingerprint = fingerprint,
            algorithm = privateKey.algorithm,
            hardwareBacked = keyInfo.isInsideSecurityHardware
        )
    }

    fun sign(challenge: ByteArray): ByteArray {
        val privateKey = getPrivateKey()

        return Signature
            .getInstance(SIGNATURE_ALGORITHM)
            .apply {
                initSign(privateKey)
                update(challenge)
            }
            .sign()
    }

    fun verify(
        challenge: ByteArray,
        signatureBytes: ByteArray
    ): Boolean {
        val keyStore = loadKeyStore()

        val publicKey = keyStore
            .getCertificate(KEY_ALIAS)
            .publicKey

        return Signature
            .getInstance(SIGNATURE_ALGORITHM)
            .apply {
                initVerify(publicKey)
                update(challenge)
            }
            .verify(signatureBytes)
    }

    fun isPrivateKeyExported(): Boolean {
        val privateKey = getPrivateKey()
        return privateKey.encoded != null
    }

    private fun ByteArray.toHex(): String {
        return joinToString("") {
            String.format(Locale.US, "%02x", it)
        }
    }
}
