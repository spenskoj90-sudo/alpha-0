package com.alpha0.app.auth

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.nio.ByteBuffer
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Short-lived PKCE state store.
 *
 * The verifier is encrypted with an Android Keystore AES/GCM key because a browser
 * round trip can recreate the Activity or the process. Entries expire quickly and
 * are deleted on successful consumption or malformed callback handling.
 */
class FederatedAuthStateStore {
    data class Pending(
        val provider: String,
        val operation: String,
        val state: String,
        val codeVerifier: String,
        val createdAtMillis: Long,
    )

    companion object {
        private const val PROVIDER = "AndroidKeyStore"
        private const val ALIAS = "alpha0.federated-auth.aes.v1"
        private const val TRANSFORMATION = "AES/GCM/NoPadding"
        private const val PREFS = "sentinel_federated_auth"
        private const val PAYLOAD = "pending_payload"
        private const val MAX_AGE_MILLIS = 10 * 60 * 1000L
        private val LOCK = Any()
    }

    fun save(context: Context, pending: Pending) = synchronized(LOCK) {
        val raw = listOf(
            pending.provider,
            pending.operation,
            pending.state,
            pending.codeVerifier,
            pending.createdAtMillis.toString(),
        ).joinToString("\n")
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(PAYLOAD, encrypt(raw))
            .apply()
    }

    sealed interface ConsumeResult {
        data class Matched(val pending: Pending) : ConsumeResult
        data object Expired : ConsumeResult
        data object OperationMismatch : ConsumeResult
        data object ProviderMismatch : ConsumeResult
        data object StateMismatch : ConsumeResult
    }

    /**
     * A valid-looking but unsolicited callback must not burn the one-time
     * encrypted pending state. Only an exact provider/operation/constant-time
     * state match removes it, durably, before the API exchanges the code.
     * LOCK also serializes browser flow replacement, cancellation and callbacks
     * within this app process.
     */
    fun consumeMatching(
        context: Context,
        provider: String,
        operation: String,
        state: String,
    ): ConsumeResult = synchronized(LOCK) {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val encoded = prefs.getString(PAYLOAD, null) ?: return@synchronized ConsumeResult.Expired
        val pending = decodePending(encoded)
        if (pending == null) {
            prefs.edit().remove(PAYLOAD).apply()
            return@synchronized ConsumeResult.Expired
        }
        when (PendingCallbackPolicy.classify(
            pending.provider, pending.operation, pending.state, provider, operation, state,
        )) {
            PendingCallbackMatch.OPERATION_MISMATCH -> ConsumeResult.OperationMismatch
            PendingCallbackMatch.PROVIDER_MISMATCH -> ConsumeResult.ProviderMismatch
            PendingCallbackMatch.STATE_MISMATCH -> ConsumeResult.StateMismatch
            PendingCallbackMatch.MATCH -> {
                // Fail closed if persistence fails: a crash must not resurrect a
                // supposedly consumed login in the on-disk preferences.
                if (prefs.edit().remove(PAYLOAD).commit()) ConsumeResult.Matched(pending)
                else ConsumeResult.Expired
            }
        }
    }

    private fun decodePending(encoded: String): Pending? = try {
        val parts = decrypt(encoded).split("\n")
        if (parts.size != 5) null else {
            val created = parts[4].toLongOrNull()
            val now = System.currentTimeMillis()
            if (created == null || created > now + 60_000L ||
                now - created > MAX_AGE_MILLIS
            ) null else {
                val provider = parts[0]
                val operation = parts[1]
                val state = parts[2]
                val verifier = parts[3]
                if (provider !in setOf("telegram", "vk") ||
                    operation !in setOf("login", "link") ||
                    state.length < 32 || verifier.length < 43
                ) null else Pending(provider, operation, state, verifier, created)
            }
        }
    } catch (_: Exception) {
        null
    }

    fun clear(context: Context) = synchronized(LOCK) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().clear().apply()
    }

    private fun key(): SecretKey {
        val store = KeyStore.getInstance(PROVIDER).apply { load(null) }
        if (!store.containsAlias(ALIAS)) {
            KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, PROVIDER).apply {
                init(
                    KeyGenParameterSpec.Builder(
                        ALIAS,
                        KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
                    )
                        .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                        .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                        .build()
                )
                generateKey()
            }
        }
        return store.getKey(ALIAS, null) as SecretKey
    }

    private fun encrypt(value: String): String {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val iv = cipher.iv
        val ciphertext = cipher.doFinal(value.toByteArray(Charsets.UTF_8))
        val packed = ByteBuffer.allocate(4 + iv.size + ciphertext.size).apply {
            putInt(iv.size)
            put(iv)
            put(ciphertext)
        }.array()
        return Base64.encodeToString(packed, Base64.NO_WRAP)
    }

    private fun decrypt(encoded: String): String {
        val packed = Base64.decode(encoded, Base64.DEFAULT)
        val buffer = ByteBuffer.wrap(packed)
        val ivLength = buffer.int
        require(ivLength in 12..16)
        val iv = ByteArray(ivLength)
        buffer.get(iv)
        val ciphertext = ByteArray(buffer.remaining())
        buffer.get(ciphertext)
        return Cipher.getInstance(TRANSFORMATION).apply {
            init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, iv))
        }.doFinal(ciphertext).toString(Charsets.UTF_8)
    }
}
