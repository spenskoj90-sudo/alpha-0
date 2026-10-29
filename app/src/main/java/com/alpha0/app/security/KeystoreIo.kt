package com.alpha0.app.security

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Never perform Android Keystore operations from Compose/UI callbacks.
 * The caller's coroutine resumes on its original dispatcher to publish UI state.
 */
internal suspend fun <T> keystoreIo(block: () -> T): T =
    withContext(Dispatchers.IO) { block() }
