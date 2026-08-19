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
        private const val ALIAS = "alpha0.session.aes.v1"
        private const val TRANSFORMATION = "AES/GCM/NoPadding"
        private const val PREFS = "sentinel_session"
        private const val ACCESS_TOKEN = "access_token"
        private const val REFRESH_TOKEN = "refresh_token"

        data class Session(val accessToken: String, val refreshToken: String)
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

    fun save(context: Context, accessToken: String, refreshToken: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putString(ACCESS_TOKEN, encrypt(accessToken))
            .putString(REFRESH_TOKEN, encrypt(refreshToken))
            .apply()
    }

    fun load(context: Context): Session? {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val access = prefs.getString(ACCESS_TOKEN, null) ?: return null
        val refresh = prefs.getString(REFRESH_TOKEN, null) ?: return null
        return try {
            Session(decrypt(access), decrypt(refresh))
        } catch (_: Exception) {
            clear(context)
            null
        }
    }

    fun clear(context: Context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().clear().apply()
    }

    private fun encrypt(value: String): String {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val iv = cipher.iv
        val ciphertext = cipher.doFinal(value.toByteArray(Charsets.UTF_8))
        val packed = ByteBuffer.allocate(4 + iv.size + ciphertext.size).apply {
            putInt(iv.size); put(iv); put(ciphertext)
        }.array()
        return Base64.encodeToString(packed, Base64.NO_WRAP)
    }

    private fun decrypt(encoded: String): String {
        val packed = Base64.decode(encoded, Base64.DEFAULT)
        val buffer = ByteBuffer.wrap(packed)
        val ivLength = buffer.int
        require(ivLength in 12..16)
        val iv = ByteArray(ivLength); buffer.get(iv)
        val ciphertext = ByteArray(buffer.remaining()); buffer.get(ciphertext)
        return Cipher.getInstance(TRANSFORMATION).apply {
            init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, iv))
        }.doFinal(ciphertext).toString(Charsets.UTF_8)
    }
}
