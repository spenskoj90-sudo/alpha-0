package com.alpha0.app.update

import android.content.Context
import android.net.Uri
import android.os.Build
import android.os.SystemClock
import com.alpha0.app.BuildConfig
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.net.URL
import java.security.MessageDigest
import javax.net.ssl.HttpsURLConnection

/**
 * Network layer for the user-initiated diagnostic signed update feed.
 * No background installations, unauthenticated fallback, redirect following or key retrieval.
 * A verified feed is only an offer. The staged APK is independently checked by LocalApkUpdate.
 */
internal object FeedUpdateClient {
    private const val FEED_CAP_BYTES = 8 * 1024
    private const val APK_CAP_BYTES = 256L * 1024 * 1024
    private const val FEED_TOTAL_TIMEOUT_MS = 30_000L
    private const val APK_TOTAL_TIMEOUT_MS = 1_800_000L

    sealed interface Check {
        /** Exact signed bytes are retained only in process memory for download-time revalidation. */
        data class Available(val release: SignedUpdateFeed.Release, val signedFeedBytes: ByteArray) : Check
        data class Current(val versionCode: Long) : Check
        data object NotConfigured : Check
        data object Unavailable : Check
    }

    private fun connection(url: String): HttpsURLConnection {
        val connection = (URL(url).openConnection() as HttpsURLConnection)
        connection.instanceFollowRedirects = false
        connection.connectTimeout = 10_000
        connection.readTimeout = 15_000
        connection.useCaches = false
        connection.requestMethod = "GET"
        return connection
    }

    private fun readBounded(conn: HttpsURLConnection, maxBytes: Int, checkRead: () -> Unit): ByteArray {
        checkRead()
        if (conn.responseCode != HttpsURLConnection.HTTP_OK) throw IllegalArgumentException("HTTP_NOT_OK")
        conn.inputStream.use { source ->
            val bytes = java.io.ByteArrayOutputStream()
            val buffer = ByteArray(8192)
            while (true) {
                checkRead()
                val n = source.read(buffer)
                checkRead() // Abort even when the most recent blocking read finished too late.
                if (n < 0) break
                if (n == 0) throw IllegalArgumentException("STREAM_NO_PROGRESS")
                if (bytes.size() + n > maxBytes) throw IllegalArgumentException("TOO_LARGE")
                bytes.write(buffer, 0, n)
            }
            return bytes.toByteArray()
        }
    }

    private fun installedVersionCode(context: Context): Long? = runCatching {
        val info = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            context.packageManager.getPackageInfo(
                context.packageName, android.content.pm.PackageManager.PackageInfoFlags.of(0L),
            )
        } else {
            @Suppress("DEPRECATION")
            context.packageManager.getPackageInfo(context.packageName, 0)
        }
        info.longVersionCode
    }.getOrNull()

    suspend fun check(context: Context, feedUrl: String, verifyingKey: String): Check =
        withContext(Dispatchers.IO) {
            if (feedUrl.isBlank() || verifyingKey.isBlank()) return@withContext Check.NotConfigured
            val signer = LocalApkUpdate.installedSignerSha256(context)
                ?: return@withContext Check.Unavailable
            val installedVersion = installedVersionCode(context) ?: return@withContext Check.Unavailable
            var conn: HttpsURLConnection? = null
            try {
                // Reuse the exact signed-manifest URL policy before any network request.
                if (!SignedUpdateFeed.acceptsHttpsUrl(feedUrl)) {
                    return@withContext Check.Unavailable
                }
                val cancellation = currentCoroutineContext()
                val deadline = TransferDeadline(SystemClock::elapsedRealtime, FEED_TOTAL_TIMEOUT_MS)
                conn = connection(feedUrl)
                val data = readBounded(conn, FEED_CAP_BYTES) {
                    cancellation.ensureActive()
                    deadline.check()
                }
                val release = SignedUpdateFeed.verify(
                    data, verifyingKey, feedUrl, context.packageName, installedVersion, signer,
                    allowInstalledVersionForStatus = true,
                ) ?: return@withContext Check.Unavailable
                // Only a valid, pinned and signed equal-version manifest can show CURRENT.
                // Older releases fail verification; an equal-version APK cannot be downloaded here.
                if (release.versionCode == installedVersion) Check.Current(installedVersion)
                else Check.Available(release, data.copyOf())
            } catch (cancel: CancellationException) {
                throw cancel
            } catch (_: Exception) {
                Check.Unavailable
            } finally {
                conn?.disconnect()
            }
        }

    /**
     * A release description alone cannot authorize a network request. Reverify
     * the exact signed offer with the build-pinned feed key and the CURRENT
     * installed package/version/signer before opening the APK connection.
     * LocalApkUpdate independently checks the downloaded APK before READY.
     */
    suspend fun download(context: Context, offer: Check.Available): LocalApkUpdate.Result =
        withContext(Dispatchers.IO) {
            var temporary: File? = null
            var conn: HttpsURLConnection? = null
            try {
                val release = offer.release
                val signer = LocalApkUpdate.installedSignerSha256(context)
                    ?: return@withContext LocalApkUpdate.Result.Failed
                val version = installedVersionCode(context)
                    ?: return@withContext LocalApkUpdate.Result.Failed
                if (!SignedUpdateFeed.authenticDownloadOffer(
                        offer.signedFeedBytes, release,
                        BuildConfig.SENTINEL_UPDATE_FEED_VERIFYING_KEY,
                        BuildConfig.SENTINEL_UPDATE_FEED_URL,
                        context.packageName, version, signer,
                    )
                ) return@withContext LocalApkUpdate.Result.Failed
                val dir = File(context.cacheDir, "sentinel_feed_download")
                if (!dir.isDirectory && !dir.mkdirs()) return@withContext LocalApkUpdate.Result.Failed
                val temp = File.createTempFile("verified-", ".apk", dir)
                temporary = temp
                val cancellation = currentCoroutineContext()
                val deadline = TransferDeadline(SystemClock::elapsedRealtime, APK_TOTAL_TIMEOUT_MS)
                conn = connection(release.apkUrl)
                cancellation.ensureActive()
                deadline.check()
                if (conn.responseCode != HttpsURLConnection.HTTP_OK) {
                    return@withContext LocalApkUpdate.Result.Failed
                }
                deadline.check()
                // A read timeout only bounds each blocking read, not a slow trickling
                // response. The total elapsed budget is checked before/after chunks.
                // No installed-package or signature trust is granted until
                // LocalApkUpdate independently inspects bytes.
                val fingerprint = conn.inputStream.use { input ->
                    FileOutputStream(temp).use { output ->
                        ApkByteStream.consume(
                            input = input,
                            maxBytes = APK_CAP_BYTES,
                            write = { buffer, count -> output.write(buffer, 0, count) },
                            checkCancellation = {
                                cancellation.ensureActive()
                                deadline.check()
                            },
                        ).also { output.fd.sync() }
                    }
                }
                if (!MessageDigest.isEqual(fingerprint.sha256, release.apkSha256.chunked(2)
                        .map { it.toInt(16).toByte() }.toByteArray())
                ) return@withContext LocalApkUpdate.Result.Failed
                cancellation.ensureActive()

                val staged = LocalApkUpdate.stage(context, Uri.fromFile(temp))
                when (staged) {
                    is LocalApkUpdate.Result.Ready -> {
                        if (staged.versionCode == release.versionCode && staged.sha256 == release.apkSha256) {
                            staged
                        } else {
                            staged.file.delete()
                            LocalApkUpdate.Result.Failed
                        }
                    }
                    is LocalApkUpdate.Result.Blocked -> staged
                    LocalApkUpdate.Result.Failed -> LocalApkUpdate.Result.Failed
                }
            } catch (cancel: CancellationException) {
                throw cancel
            } catch (_: Exception) {
                LocalApkUpdate.Result.Failed
            } finally {
                conn?.disconnect()
                temporary?.delete()
            }
        }
}
