package com.alpha0.app.update

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.InputStream
import java.security.MessageDigest
import java.util.concurrent.CancellationException
import org.junit.Assert.*
import org.junit.Test

/** Pure JVM fault-injection; Android document providers and owner-device installs remain separate gates. */
class ApkByteStreamTest {
    @Test fun streamingCopyMatchesExactBytesAndDigestAcrossChunks() {
        val payload = ByteArray(200_007) { (it * 31).toByte() }
        val copied = ByteArrayOutputStream()
        val result = ApkByteStream.consume(ByteArrayInputStream(payload), payload.size.toLong(),
            write = { bytes, count -> copied.write(bytes, 0, count) })
        assertEquals(payload.size.toLong(), result.bytes)
        assertArrayEquals(payload, copied.toByteArray())
        assertArrayEquals(MessageDigest.getInstance("SHA-256").digest(payload), result.sha256)
    }

    @Test fun zeroReadDoesNotSpin() {
        var calls = 0
        val bad = object : InputStream() {
            override fun read(): Int = 0
            override fun read(b: ByteArray, off: Int, len: Int): Int { calls++; return 0 }
        }
        assertThrows(IOException::class.java) { ApkByteStream.consume(bad, 10) }
        assertEquals(1, calls)
    }

    @Test fun emptyOrOverLimitInputFailsClosedWithoutWritingOversizeChunk() {
        assertThrows(IOException::class.java) { ApkByteStream.consume(ByteArrayInputStream(byteArrayOf()), 100) }
        var wrote = false
        assertThrows(IOException::class.java) {
            ApkByteStream.consume(ByteArrayInputStream(ByteArray(20)), 19,
                write = { _, _ -> wrote = true })
        }
        assertFalse(wrote)
        val exact = ApkByteStream.consume(ByteArrayInputStream(ByteArray(20)), 20)
        assertEquals(20L, exact.bytes)
    }

    @Test fun cancellationAndOutputFailuresPropagate() {
        assertThrows(CancellationException::class.java) {
            ApkByteStream.consume(ByteArrayInputStream(byteArrayOf(1)), 10,
                checkCancellation = { throw CancellationException("stopped") })
        }
        assertThrows(IOException::class.java) {
            ApkByteStream.consume(ByteArrayInputStream(byteArrayOf(1)), 10,
                write = { _, _ -> throw IOException("disk failure") })
        }
    }
}
