package com.alpha0.app.update

import java.io.IOException
import java.io.InputStream
import java.security.MessageDigest

/** Bounded streaming SHA-256 for a user-selected APK or an app-private staged file.
 * An InputStream returning zero bytes for a positive read violates the read contract;
 * never spin indefinitely on an untrusted document provider. */
internal object ApkByteStream {
    data class Fingerprint(val bytes: Long, val sha256: ByteArray)

    fun consume(
        input: InputStream,
        maxBytes: Long,
        write: (ByteArray, Int) -> Unit = { _, _ -> },
        checkCancellation: () -> Unit = {},
    ): Fingerprint {
        require(maxBytes > 0)
        val digest = MessageDigest.getInstance("SHA-256")
        val buffer = ByteArray(64 * 1024)
        var total = 0L
        while (true) {
            checkCancellation()
            val count = input.read(buffer)
            // A read may have blocked until cancellation/deadline occurred.
            checkCancellation()
            if (count < 0) break
            if (count == 0) throw IOException("APK_INPUT_NO_PROGRESS")
            if (count > maxBytes - total) throw IOException("APK_INPUT_TOO_LARGE")
            write(buffer, count)
            digest.update(buffer, 0, count)
            total += count
        }
        if (total == 0L) throw IOException("APK_INPUT_EMPTY")
        return Fingerprint(total, digest.digest())
    }
}
