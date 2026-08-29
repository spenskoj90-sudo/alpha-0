package com.alpha0.app.security

import android.content.Context
import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.security.keystore.StrongBoxUnavailableException
import android.util.Base64
import com.alpha0.app.diagnostics.DiagnosticLogger
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

    private var diag: DiagnosticLogger? = null

    /** Optional: attach logger from Application/Activity context. */
    fun attachDiagnostics(context: Context) {
        diag = DiagnosticLogger.get(context)
    }

    private fun log(level: String, event: String, result: String, details: Map<String, Any?>? = null, t: Throwable? = null) {
        val d = diag ?: return
        when (level) {
            "ERROR" -> d.error("KEYSTORE", event, result, details = details, throwable = t)
            "WARN" -> d.warn("KEYSTORE", event, result, details = details)
            else -> d.info("KEYSTORE", event, result, details = details)
        }
    }

    private fun loadKeyStore(): KeyStore {
        return KeyStore.getInstance(KEYSTORE_PROVIDER).apply {
            load(null)
        }
    }

    private fun ensureKeyExists() {
        val keyStore = loadKeyStore()

        if (keyStore.containsAlias(KEY_ALIAS)) {
            log("INFO", "KEY_AVAILABLE", "SUCCESS", mapOf("alias_present" to true, "generated" to false))
            return
        }

        val t0 = System.currentTimeMillis()
        val generator = KeyPairGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_EC,
            KEYSTORE_PROVIDER
        )

        val builder = KeyGenParameterSpec.Builder(
            KEY_ALIAS,
            KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY
        )
            .setAlgorithmParameterSpec(
                ECGenParameterSpec(CURVE)
            )
            .setDigests(
                KeyProperties.DIGEST_SHA256
            )
            .setUserAuthenticationRequired(false)

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                builder.setIsStrongBoxBacked(true)
            }
            generator.initialize(builder.build())
            generator.generateKeyPair()
            log(
                "INFO", "KEY_GEN", "SUCCESS",
                mapOf(
                    "backend" to "StrongBox",
                    "curve" to CURVE,
                    "duration_ms" to (System.currentTimeMillis() - t0)
                )
            )
        } catch (e: StrongBoxUnavailableException) {
            log("WARN", "STRONGBOX_UNAVAILABLE", "SKIPPED", mapOf("fallback" to "TEE"), e)
            val teeBuilder = KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY
            )
                .setAlgorithmParameterSpec(
                    ECGenParameterSpec(CURVE)
                )
                .setDigests(
                    KeyProperties.DIGEST_SHA256
                )
                .setUserAuthenticationRequired(false)
            generator.initialize(teeBuilder.build())
            generator.generateKeyPair()
            log(
                "INFO", "KEY_GEN", "SUCCESS",
                mapOf(
                    "backend" to "TEE",
                    "curve" to CURVE,
                    "duration_ms" to (System.currentTimeMillis() - t0)
                )
            )
        } catch (e: Exception) {
            log("WARN", "STRONGBOX_OR_INIT_FAIL", "SKIPPED", mapOf("fallback" to "TEE_MINIMAL"), e)
            val teeBuilder = KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY
            )
                .setAlgorithmParameterSpec(
                    ECGenParameterSpec(CURVE)
                )
                .setDigests(
                    KeyProperties.DIGEST_SHA256
                )
            generator.initialize(teeBuilder.build())
            generator.generateKeyPair()
            log(
                "INFO", "KEY_GEN", "SUCCESS",
                mapOf(
                    "backend" to "TEE_MINIMAL",
                    "curve" to CURVE,
                    "duration_ms" to (System.currentTimeMillis() - t0)
                )
            )
        }
    }

    private fun getPrivateKey(): PrivateKey {
        ensureKeyExists()

        val keyStore = loadKeyStore()

        return keyStore.getKey(
            KEY_ALIAS,
            null
        ) as? PrivateKey
            ?: run {
                log("ERROR", "PRIVATE_KEY_UNAVAILABLE", "FAILURE")
                throw IllegalStateException(
                    "ALPHA-0 private key is unavailable"
                )
            }
    }

    private fun getPublicKey(): PublicKey {
        ensureKeyExists()

        val keyStore = loadKeyStore()

        return keyStore
            .getCertificate(KEY_ALIAS)
            ?.publicKey
            ?: run {
                log("ERROR", "PUBLIC_KEY_UNAVAILABLE", "FAILURE")
                throw IllegalStateException(
                    "ALPHA-0 public key is unavailable"
                )
            }
    }

    fun getIdentityInfo(): IdentityInfo {
        val publicKey = getPublicKey()

        val fingerprint = MessageDigest
            .getInstance(HASH_ALGORITHM)
            .digest(publicKey.encoded)
            .toHex()

        log(
            "INFO", "IDENTITY_INFO",
            "SUCCESS",
            mapOf(
                "fingerprint_prefix" to fingerprint.take(12),
                "algorithm" to "EC / $CURVE / $SIGNATURE_ALGORITHM"
            )
        )

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

        val t0 = System.currentTimeMillis()
        return try {
            val sig = Signature
                .getInstance(SIGNATURE_ALGORITHM)
                .apply {
                    initSign(getPrivateKey())
                    update(challenge)
                }
                .sign()
            log("INFO", "SIGN_CHALLENGE", "SUCCESS", mapOf("duration_ms" to (System.currentTimeMillis() - t0), "challenge_len" to challenge.size))
            sig
        } catch (e: Exception) {
            log("ERROR", "SIGN_CHALLENGE", "FAILURE", mapOf("duration_ms" to (System.currentTimeMillis() - t0)), e)
            throw e
        }
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
