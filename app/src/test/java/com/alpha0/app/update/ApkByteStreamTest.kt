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

    @Test fun cancellationAfterFirstChunkStopsFurtherNetworkCopy() {
        val payload = ByteArray(150_000) { (it * 17).toByte() }
        val source = ByteArrayInputStream(payload)
        var copied = 0
        assertThrows(CancellationException::class.java) {
            ApkByteStream.consume(source, payload.size.toLong(),
                write = { _, count -> copied += count },
                checkCancellation = { if (copied > 0) throw CancellationException("cancel download") })
        }
        assertEquals(64 * 1024, copied)
        assertEquals(payload.size - copied, source.available())
    }

    @Test fun elapsedNetworkDeadlineRejectsSlowTrickleAndClockRollback() {
        var now = 100L
        val deadline = TransferDeadline({ now }, 30L)
        deadline.check()
        now = 129L
        deadline.check()
        now = 130L
        assertThrows(IOException::class.java) { deadline.check() }
        now = 99L
        assertThrows(IOException::class.java) { deadline.check() }
        assertThrows(IllegalArgumentException::class.java) { TransferDeadline({ -1L }, 30L) }
        assertThrows(IllegalArgumentException::class.java) { TransferDeadline({ 0L }, 1_800_001L) }
    }

    @Test fun transferDeadlineAfterSlowReadRejectsBytesBeforeAnyWrite() {
        var now = 0L
        val deadline = TransferDeadline({ now }, 30L)
        var copied = 0
        val slowInput = object : InputStream() {
            override fun read(): Int = error("Unexpected single byte read")
            override fun read(b: ByteArray, off: Int, len: Int): Int {
                now = 31L
                b[off] = 7
                return 1
            }
        }
        assertThrows(IOException::class.java) {
            ApkByteStream.consume(slowInput, 1024L,
                write = { _, n -> copied += n },
                checkCancellation = deadline::check)
        }
        assertEquals(0, copied)
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
