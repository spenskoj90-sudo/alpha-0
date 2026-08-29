package com.alpha0.app.security

import android.content.Context
import com.alpha0.app.diagnostics.DiagnosticLogger
import com.google.android.play.core.integrity.IntegrityManagerFactory
import com.google.android.play.core.integrity.IntegrityTokenRequest
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import kotlin.coroutines.suspendCoroutine

/**
 * Obtains a Google Play Integrity token bound to a server-issued nonce.
 * Client-side verdict lists are never treated as trusted authorization data;
 * the token must be verified by the backend via Google's decode API.
 *
 * Diagnostics log request outcome only — never the raw integrity token.
 */
class IntegrityAttestor(private val context: Context) {

    private val diag = DiagnosticLogger.get(context)

    suspend fun requestToken(serverNonce: String): String = suspendCoroutine { cont ->
        val t0 = System.currentTimeMillis()
        diag.info(
            "INTEGRITY",
            "TOKEN_REQUEST_START",
            "SUCCESS",
            details = mapOf("nonce_len" to serverNonce.length)
        )
        val manager = IntegrityManagerFactory.create(context)
        val request = IntegrityTokenRequest.builder()
            .setNonce(serverNonce)
            .build()
        manager.requestIntegrityToken(request)
            .addOnSuccessListener { response ->
                val token = response.token()
                diag.info(
                    "INTEGRITY",
                    "TOKEN_REQUEST",
                    "SUCCESS",
                    durationMs = System.currentTimeMillis() - t0,
                    details = mapOf("token_len" to token.length)
                )
                cont.resume(token)
            }
            .addOnFailureListener { error ->
                diag.error(
                    "INTEGRITY",
                    "TOKEN_REQUEST",
                    "FAILURE",
                    errorCode = error.javaClass.simpleName,
                    durationMs = System.currentTimeMillis() - t0,
                    throwable = error
                )
                cont.resumeWithException(error)
            }
    }
}
