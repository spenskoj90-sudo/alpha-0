package com.alpha0.app.game

import java.io.File
import java.io.FileInputStream
import java.security.MessageDigest
import java.util.concurrent.CancellationException

/** Locally observed APK byte identity. Never attests the MediaProjection window. */
internal object GameBinaryEvidence {
    enum class Status { NOT_CHECKED, MATCHED_GITHUB_ANDROID, MATCHED_GITHUB_GPLAY, OTHER_OR_SPLIT, UNAVAILABLE, UNSUPPORTED_VERSION }
    data class AssetPin(val status: Status, val size: Long, val sha256: String)

    /** Official upstream v4.0.2 GitHub release asset metadata, read 2026-11-08. */
    private val officialPins = listOf(
        AssetPin(Status.MATCHED_GITHUB_ANDROID, 30_275_058L, "ceef4cdd4beddcb3d85379ac004cb4ab5d918b89dc7366b4ce9c4a3585a5e78e"),
        AssetPin(Status.MATCHED_GITHUB_GPLAY, 31_318_705L, "b7be54496503b613e241a7b67021fb6ed152ccf93f28c131a6af25daa3c30483"),
    )
    private val digestPattern = Regex("[0-9a-f]{64}")
    private const val MAX_APK_BYTES = 32L * 1024 * 1024

    fun inspect(
        file: File,
        versionName: String,
        versionCode: Long,
        signerSha256: String?,
        pins: List<AssetPin> = officialPins,
        checkCancellation: () -> Unit = {},
    ): Status {
        if (versionName != "4.0.2" || versionCode != 922L) return Status.UNSUPPORTED_VERSION
        if (signerSha256 == null || !digestPattern.matches(signerSha256)) return Status.UNAVAILABLE
        if (!file.isFile || !file.canRead()) return Status.UNAVAILABLE
        val size = file.length()
        if (size !in 1..MAX_APK_BYTES) return Status.UNAVAILABLE
        val candidates = pins.filter { it.size == size && digestPattern.matches(it.sha256) }
        if (candidates.isEmpty()) return Status.OTHER_OR_SPLIT
        val modified = file.lastModified()
        return try {
            val digest = MessageDigest.getInstance("SHA-256")
            FileInputStream(file).use { input ->
                val buffer = ByteArray(64 * 1024)
                var count = 0L
                while (true) {
                    checkCancellation()
                    val n = input.read(buffer)
                    if (n < 0) break
                    if (n == 0) throw IllegalStateException("NO_PROGRESS")
                    count += n
                    if (count > size || count > MAX_APK_BYTES) throw IllegalStateException("APK_CHANGED")
                    digest.update(buffer, 0, n)
                }
                if (count != size) throw IllegalStateException("APK_SHORT_READ")
            }
            if (!file.isFile || file.length() != size || file.lastModified() != modified) Status.UNAVAILABLE
            else {
                val actual = digest.digest().joinToString("") { "%02x".format(it.toInt() and 0xff) }
                candidates.singleOrNull { it.sha256 == actual }?.status ?: Status.OTHER_OR_SPLIT
            }
        } catch (cancel: CancellationException) {
            throw cancel
        } catch (_: Exception) {
            Status.UNAVAILABLE
        }
    }
}
