package com.alpha0.app.update

import android.content.Context
import android.net.Uri
import android.os.Build
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
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

    sealed interface Check {
        data class Available(val release: SignedUpdateFeed.Release) : Check
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

    private fun readBounded(conn: HttpsURLConnection, maxBytes: Int): ByteArray {
        if (conn.responseCode != HttpsURLConnection.HTTP_OK) throw IllegalArgumentException("HTTP_NOT_OK")
        conn.inputStream.use { source ->
            val bytes = java.io.ByteArrayOutputStream()
            val buffer = ByteArray(8192)
            while (true) {
                val n = source.read(buffer)
                if (n < 0) break
                if (n == 0) throw IllegalArgumentException("STREAM_NO_PROGRESS")
                if (bytes.size() + n > maxBytes) throw IllegalArgumentException("TOO_LARGE")
                bytes.write(buffer, 0, n)
            }
            return bytes.toByteArray()
        }
    }

    suspend fun check(context: Context, feedUrl: String, verifyingKey: String): Check =
        withContext(Dispatchers.IO) {
            if (feedUrl.isBlank() || verifyingKey.isBlank()) return@withContext Check.NotConfigured
            val signer = LocalApkUpdate.installedSignerSha256(context)
                ?: return@withContext Check.Unavailable
            val installedVersion = runCatching {
                val info = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    context.packageManager.getPackageInfo(context.packageName, android.content.pm.PackageManager.PackageInfoFlags.of(0L))
                } else {
                    @Suppress("DEPRECATION")
                    context.packageManager.getPackageInfo(context.packageName, 0)
                }
                info.longVersionCode
            }.getOrNull() ?: return@withContext Check.Unavailable
            var conn: HttpsURLConnection? = null
            try {
                // Reuse the exact signed-manifest URL policy before any network request.
                if (!SignedUpdateFeed.acceptsHttpsUrl(feedUrl)) {
                    return@withContext Check.Unavailable
                }
                conn = connection(feedUrl)
                val data = readBounded(conn, FEED_CAP_BYTES)
                val release = SignedUpdateFeed.verify(
                    data, verifyingKey, feedUrl, context.packageName, installedVersion, signer,
                ) ?: return@withContext Check.Unavailable
                Check.Available(release)
            } catch (cancel: CancellationException) {
                throw cancel
            } catch (_: Exception) {
                Check.Unavailable
            } finally {
                conn?.disconnect()
            }
        }

    /**
     * Download only from the verified manifest's same-origin HTTPS URL. Recheck
     * hash, version, installed signer and package via LocalApkUpdate before READY.
     */
    suspend fun download(context: Context, release: SignedUpdateFeed.Release): LocalApkUpdate.Result =
        withContext(Dispatchers.IO) {
            var temporary: File? = null
            var conn: HttpsURLConnection? = null
            try {
                // A future caller must never make a request using an unchecked offer.
                if (release.packageName != context.packageName ||
                    !SignedUpdateFeed.acceptsHttpsUrl(release.apkUrl) ||
                    !release.apkUrl.endsWith(".apk") ||
                    !Regex("[0-9a-f]{64}").matches(release.apkSha256)
                ) return@withContext LocalApkUpdate.Result.Failed
                val dir = File(context.cacheDir, "sentinel_feed_download")
                if (!dir.isDirectory && !dir.mkdirs()) return@withContext LocalApkUpdate.Result.Failed
                val temp = File.createTempFile("verified-", ".apk", dir)
                temporary = temp
                val digest = MessageDigest.getInstance("SHA-256")
                var size = 0L
                conn = connection(release.apkUrl)
                if (conn.responseCode != HttpsURLConnection.HTTP_OK) {
                    return@withContext LocalApkUpdate.Result.Failed
                }
                conn.inputStream.use { input ->
                    FileOutputStream(temp).use { output ->
                        val buffer = ByteArray(64 * 1024)
                        while (true) {
                            val n = input.read(buffer)
                            if (n < 0) break
                            if (n == 0) throw IllegalArgumentException("STREAM_NO_PROGRESS")
                            size += n.toLong()
                            if (size > APK_CAP_BYTES) throw IllegalArgumentException("APK_TOO_LARGE")
                            output.write(buffer, 0, n)
                            digest.update(buffer, 0, n)
                        }
                        output.fd.sync()
                    }
                }
                if (size == 0L ||
                    !MessageDigest.isEqual(digest.digest(), release.apkSha256.chunked(2)
                        .map { it.toInt(16).toByte() }.toByteArray())
                ) return@withContext LocalApkUpdate.Result.Failed

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
