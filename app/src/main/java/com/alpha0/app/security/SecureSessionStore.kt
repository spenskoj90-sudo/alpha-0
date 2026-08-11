package com.alpha0.app.security

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.nio.ByteBuffer
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

class SecureSessionStore {
    companion object {
        private const val PROVIDER = "AndroidKeyStore"
        private const val ALIAS = "alpha0.session.aes.v1"
        private const val TRANSFORMATION = "AES/GCM/NoPadding"
        private const val PREFS = "sentinel_session"
        private const val TOKEN = "token"
    }

    private fun key(): SecretKey {
        val store = KeyStore.getInstance(PROVIDER).apply { load(null) }
        if (!store.containsAlias(ALIAS)) {
            KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, PROVIDER).apply {
                init(
                    KeyGenParameterSpec.Builder(
                        ALIAS,
                        KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
                    ).setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                        .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                        .build()
                )
                generateKey()
            }
        }
        return store.getKey(ALIAS, null) as SecretKey
    }

    fun save(context: android.content.Context, token: String) {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val iv = cipher.iv
        val ciphertext = cipher.doFinal(token.toByteArray(Charsets.UTF_8))
        val packed = ByteBuffer.allocate(4 + iv.size + ciphertext.size).apply {
            putInt(iv.size); put(iv); put(ciphertext)
        }.array()
        context.getSharedPreferences(PREFS, android.content.Context.MODE_PRIVATE)
            .edit().putString(TOKEN, Base64.encodeToString(packed, Base64.NO_WRAP)).apply()
    }

    fun load(context: android.content.Context): String? {
        val encoded = context.getSharedPreferences(PREFS, android.content.Context.MODE_PRIVATE)
            .getString(TOKEN, null) ?: return null
        return try {
            val packed = Base64.decode(encoded, Base64.DEFAULT)
            val buffer = ByteBuffer.wrap(packed)
            val ivLength = buffer.int
            require(ivLength in 12..16)
            val iv = ByteArray(ivLength); buffer.get(iv)
            val ciphertext = ByteArray(buffer.remaining()); buffer.get(ciphertext)
            Cipher.getInstance(TRANSFORMATION).apply {
                init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, iv))
            }.doFinal(ciphertext).toString(Charsets.UTF_8)
        } catch (_: Exception) {
            clear(context)
            null
        }
    }

    fun clear(context: android.content.Context) {
        context.getSharedPreferences(PREFS, android.content.Context.MODE_PRIVATE)
            .edit().remove(TOKEN).apply()
    }
}
