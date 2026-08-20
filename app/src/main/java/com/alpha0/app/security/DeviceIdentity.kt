package com.alpha0.app.security

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.MessageDigest
import java.security.PrivateKey
import java.security.PublicKey
import java.security.Signature
import java.security.spec.ECGenParameterSpec
import java.util.Locale

class DeviceIdentity {

companion object {
    private const val KEYSTORE_PROVIDER = "AndroidKeyStore"
    private const val KEY_ALIAS = "alpha0.device.identity.v1"

    private const val CURVE = "secp256r1"
    private const val SIGNATURE_ALGORITHM = "SHA256withECDSA"
    private const val HASH_ALGORITHM = "SHA-256"
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
        .setDigests(
            KeyProperties.DIGEST_SHA256
        )
        .build()

    generator.initialize(spec)
    generator.generateKeyPair()
}

private fun getPrivateKey(): PrivateKey {
    ensureKeyExists()

    val keyStore = loadKeyStore()

    return keyStore.getKey(
        KEY_ALIAS,
        null
    ) as? PrivateKey
        ?: throw IllegalStateException(
            "ALPHA-0 private key is unavailable"
        )
}

private fun getPublicKey(): PublicKey {
    ensureKeyExists()

    val keyStore = loadKeyStore()

    return keyStore
        .getCertificate(KEY_ALIAS)
        ?.publicKey
        ?: throw IllegalStateException(
            "ALPHA-0 public key is unavailable"
        )
}

fun getIdentityInfo(): IdentityInfo {
    val publicKey = getPublicKey()

    val fingerprint = MessageDigest
        .getInstance(HASH_ALGORITHM)
        .digest(publicKey.encoded)
        .toHex()

    return IdentityInfo(
        fingerprint = fingerprint,
        algorithm = "EC / $CURVE / $SIGNATURE_ALGORITHM"
    )
}

fun getPublicKeyDerBase64(): String {
    return Base64.encodeToString(getPublicKey().encoded, Base64.NO_WRAP)
}

fun sign(challenge: ByteArray): ByteArray {
    require(challenge.isNotEmpty()) {
        "Challenge must not be empty"
    }

    return Signature
        .getInstance(SIGNATURE_ALGORITHM)
        .apply {
            initSign(getPrivateKey())
            update(challenge)
        }
        .sign()
}

fun verify(
    challenge: ByteArray,
    signatureBytes: ByteArray
): Boolean {
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

private fun ByteArray.toHex(): String {
    return joinToString("") {
        String.format(Locale.US, "%02x", it)
    }
}

}