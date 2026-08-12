package com.alpha0.app.security

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

class SecureSessionStore {
    companion object {
        private const val PROVIDER = "AndroidKeyStore"
        private const val ALIAS = "sentinel.session.aes.v1"
        private const val TRANSFORMATION = "AES/GCM/NoPadding"
        private const val PREFS = "sentinel_session"
        private const val TOKEN = "token"
        private const val IV_MIN = 12
        private const val IV_MAX = 16
    }

    private fun key(): SecretKey {
        val store = KeyStore.getInstance(PROVIDER).apply { load(null) }
        if (!store.containsAlias(ALIAS)) {
            KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, PROVIDER).apply {
                init(
                    KeyGenParameterSpec.Builder(
                        ALIAS,
                        KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
                    )
                        .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                        .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                        .setRandomizedEncryptionRequired(true)
                        .build()
                )
                generateKey()
            }
        }
        return store.getKey(ALIAS, null) as SecretKey
    }

    fun save(context: Context, token: String) {
        require(token.isNotBlank()) { "Session token must not be empty" }
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val iv = cipher.iv
        val ciphertext = cipher.doFinal(token.toByteArray(Charsets.UTF_8))
        val packed = ByteBuffer.allocate(4 + iv.size + ciphertext.size).apply {
            putInt(iv.size)
            put(iv)
            put(ciphertext)
        }.array()
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(TOKEN, Base64.encodeToString(packed, Base64.NO_WRAP))
            .commit()
    }

    fun load(context: Context): String? {
        val encoded = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(TOKEN, null) ?: return null
        return try {
            val packed = Base64.decode(encoded, Base64.DEFAULT)
            require(packed.size >= 4)
            val buffer = ByteBuffer.wrap(packed)
            val ivLength = buffer.int
            require(ivLength in IV_MIN..IV_MAX)
            require(buffer.remaining() > 16)
            val iv = ByteArray(ivLength)
            buffer.get(iv)
            val ciphertext = ByteArray(buffer.remaining())
            buffer.get(ciphertext)
            Cipher.getInstance(TRANSFORMATION).apply {
                init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, iv))
            }.doFinal(ciphertext).toString(Charsets.UTF_8)
        } catch (_: Exception) {
            clear(context)
            null
        }
    }

    fun clear(context: Context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .remove(TOKEN)
            .commit()
    }
}
