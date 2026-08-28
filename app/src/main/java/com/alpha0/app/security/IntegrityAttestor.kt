package com.alpha0.app.security

import android.content.Context
import com.google.android.play.core.integrity.IntegrityManagerFactory
import com.google.android.play.core.integrity.IntegrityTokenRequest
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import kotlin.coroutines.suspendCoroutine

/**
 * Obtains a Google Play Integrity token bound to a server-issued nonce.
 * Client-side verdict lists are never treated as trusted authorization data;
 * the token must be verified by the backend via Google's decode API.
 */
class IntegrityAttestor(private val context: Context) {

    suspend fun requestToken(serverNonce: String): String = suspendCoroutine { cont ->
        val manager = IntegrityManagerFactory.create(context)
        val request = IntegrityTokenRequest.builder()
            .setNonce(serverNonce)
            .build()
        manager.requestIntegrityToken(request)
            .addOnSuccessListener { response ->
                cont.resume(response.token())
            }
            .addOnFailureListener { error ->
                cont.resumeWithException(error)
            }
    }
}
