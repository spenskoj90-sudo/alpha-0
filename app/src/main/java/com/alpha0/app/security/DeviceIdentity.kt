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
        private const val ROTATION_ALIAS_A = "alpha0.device.identity.rotation.a.v1"
        private const val ROTATION_ALIAS_B = "alpha0.device.identity.rotation.b.v1"
        private const val PREFS = "sentinel_device_identity"
        private const val ACTIVE_ALIAS = "active_alias"

        private const val CURVE = "secp256r1"
        private const val SIGNATURE_ALGORITHM = "SHA256withECDSA"
        private const val HASH_ALGORITHM = "SHA-256"
    }

    data class IdentityInfo(
        val fingerprint: String,
        val algorithm: String
    )

    data class RotationCandidate internal constructor(
        internal val alias: String,
        val fingerprint: String,
        val publicKeyDerBase64: String,
    )

    private var diag: DiagnosticLogger? = null
    private var appContext: Context? = null

    /** Optional: attach logger from Application/Activity context. */
    fun attachDiagnostics(context: Context) {
        appContext = context.applicationContext
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

    private fun activeAlias(): String = appContext
        ?.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        ?.getString(ACTIVE_ALIAS, KEY_ALIAS)
        ?.takeIf { it in setOf(KEY_ALIAS, ROTATION_ALIAS_A, ROTATION_ALIAS_B) }
        ?: KEY_ALIAS

    private fun ensureKeyExists(alias: String = activeAlias()) {
        val keyStore = loadKeyStore()

        if (keyStore.containsAlias(alias)) {
            log("INFO", "KEY_AVAILABLE", "SUCCESS", mapOf("alias_present" to true, "generated" to false))
            return
        }

        val t0 = System.currentTimeMillis()
        val generator = KeyPairGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_EC,
            KEYSTORE_PROVIDER
        )

        val builder = KeyGenParameterSpec.Builder(
            alias,
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
                alias,
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
                alias,
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

    private fun getPrivateKey(alias: String = activeAlias()): PrivateKey {
        ensureKeyExists(alias)

        val keyStore = loadKeyStore()

        return keyStore.getKey(
            alias,
            null
        ) as? PrivateKey
            ?: run {
                log("ERROR", "PRIVATE_KEY_UNAVAILABLE", "FAILURE")
                throw IllegalStateException(
                    "ALPHA-0 private key is unavailable"
                )
            }
    }

    private fun getPublicKey(alias: String = activeAlias()): PublicKey {
        ensureKeyExists(alias)

        val keyStore = loadKeyStore()

        return keyStore
            .getCertificate(alias)
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

    /**
     * Generates a staged hardware-backed identity without replacing the active key.
     * The caller must commit it only after Core accepts the rotation, or abort it on
     * every failure path. Two alternating aliases make repeated rotations possible.
     */
    @Synchronized
    fun prepareRotation(): RotationCandidate {
        checkNotNull(appContext) { "attachDiagnostics must be called before key rotation" }
        val current = activeAlias()
        val candidateAlias = if (current == ROTATION_ALIAS_A) ROTATION_ALIAS_B else ROTATION_ALIAS_A
        val keyStore = loadKeyStore()
        if (keyStore.containsAlias(candidateAlias)) keyStore.deleteEntry(candidateAlias)
        ensureKeyExists(candidateAlias)
        val publicKey = getPublicKey(candidateAlias)
        val fingerprint = MessageDigest
            .getInstance(HASH_ALGORITHM)
            .digest(publicKey.encoded)
            .toHex()
        log(
            "INFO",
            "KEY_ROTATION_PREPARED",
            "SUCCESS",
            mapOf("fingerprint_prefix" to fingerprint.take(12)),
        )
        return RotationCandidate(
            alias = candidateAlias,
            fingerprint = fingerprint,
            publicKeyDerBase64 = Base64.encodeToString(publicKey.encoded, Base64.NO_WRAP),
        )
    }

    @Synchronized
    fun commitRotation(candidate: RotationCandidate) {
        val context = checkNotNull(appContext) { "attachDiagnostics must be called before key rotation" }
        val previous = activeAlias()
        val keyStore = loadKeyStore()
        check(candidate.alias != previous && keyStore.containsAlias(candidate.alias)) {
            "Rotation candidate is not available"
        }
        check(
            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit()
                .putString(ACTIVE_ALIAS, candidate.alias)
                .commit()
        ) { "Unable to persist rotated identity" }
        if (previous != candidate.alias && keyStore.containsAlias(previous)) {
            keyStore.deleteEntry(previous)
        }
        log(
            "INFO",
            "KEY_ROTATION_COMMITTED",
            "SUCCESS",
            mapOf("fingerprint_prefix" to candidate.fingerprint.take(12)),
        )
    }

    @Synchronized
    fun abortRotation(candidate: RotationCandidate) {
        if (candidate.alias == activeAlias()) return
        val keyStore = loadKeyStore()
        if (keyStore.containsAlias(candidate.alias)) keyStore.deleteEntry(candidate.alias)
        log("INFO", "KEY_ROTATION_ABORTED", "SKIPPED")
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
