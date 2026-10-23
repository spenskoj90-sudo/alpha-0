package com.alpha0.app.update

import android.content.ClipData
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import androidx.core.content.FileProvider
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest

/** User-selected APK only; no background download, network trust or silent installation. */
internal object LocalApkUpdate {
    private const val MAX_APK_BYTES = 256L * 1024 * 1024
    private const val MIME_APK = "application/vnd.android.package-archive"

    sealed interface Result {
        data class Ready(val file: File, val versionCode: Long, val sha256: String) : Result
        data class Blocked(val reason: ApkUpdatePolicy.BlockReason) : Result
        data object Failed : Result
    }

    enum class InstallOutcome { LAUNCHED, PERMISSION_REQUIRED, FAILED }

    suspend fun stage(context: Context, uri: Uri): Result = withContext(Dispatchers.IO) {
        val folder = File(context.cacheDir, "sentinel_updates")
        if (!folder.isDirectory && !folder.mkdirs()) return@withContext Result.Failed
        val temporary = File(folder, "candidate.tmp")
        val staged = File(folder, "candidate.apk")
        temporary.delete()
        staged.delete()
        try {
            val digest = MessageDigest.getInstance("SHA-256")
            var size = 0L
            val input = context.contentResolver.openInputStream(uri) ?: return@withContext Result.Failed
            input.use { source ->
                FileOutputStream(temporary).use { output ->
                    val buffer = ByteArray(64 * 1024)
                    while (true) {
                        val count = source.read(buffer)
                        if (count < 0) break
                        size += count.toLong()
                        if (size > MAX_APK_BYTES) throw IllegalArgumentException("APK_TOO_LARGE")
                        output.write(buffer, 0, count)
                        digest.update(buffer, 0, count)
                    }
                    output.fd.sync()
                }
            }
            if (size == 0L || !temporary.renameTo(staged)) throw IllegalArgumentException("INVALID_APK")
            val flags = PackageManager.GET_SIGNING_CERTIFICATES.toLong()
            val packageManager = context.packageManager
            val candidate = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                packageManager.getPackageArchiveInfo(staged.absolutePath, PackageManager.PackageInfoFlags.of(flags))
            } else {
                @Suppress("DEPRECATION")
                packageManager.getPackageArchiveInfo(staged.absolutePath, PackageManager.GET_SIGNING_CERTIFICATES)
            } ?: throw IllegalArgumentException("INVALID_APK")
            val installed = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                packageManager.getPackageInfo(context.packageName, PackageManager.PackageInfoFlags.of(flags))
            } else {
                @Suppress("DEPRECATION")
                packageManager.getPackageInfo(context.packageName, PackageManager.GET_SIGNING_CERTIFICATES)
            }
            val reason = ApkUpdatePolicy.check(
                installed.packageName, installed.longVersionCode, signers(installed),
                candidate.packageName, candidate.longVersionCode, signers(candidate),
            )
            if (reason != null) {
                staged.delete()
                Result.Blocked(reason)
            } else {
                val sha = digest.digest().joinToString("") { "%02x".format(it.toInt() and 0xff) }
                Result.Ready(staged, candidate.longVersionCode, sha)
            }
        } catch (cancel: CancellationException) {
            temporary.delete()
            staged.delete()
            throw cancel
        } catch (_: Exception) {
            temporary.delete()
            staged.delete()
            Result.Failed
        } finally {
            temporary.delete()
        }
    }

    private fun signers(info: PackageInfo): List<String> {
        val signing = info.signingInfo ?: return emptyList()
        // Rotation and multi-signer cases demand separately verified lineage, not an assumed match.
        if (signing.hasMultipleSigners()) return emptyList()
        return signing.apkContentsSigners?.map { signature ->
            MessageDigest.getInstance("SHA-256").digest(signature.toByteArray())
                .joinToString("") { "%02x".format(it.toInt() and 0xff) }
        } ?: emptyList()
    }

    fun install(context: Context, ready: Result.Ready): InstallOutcome {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O &&
            !context.packageManager.canRequestPackageInstalls()
        ) return InstallOutcome.PERMISSION_REQUIRED
        return try {
            val uri = FileProvider.getUriForFile(
                context, context.packageName + ".diagnostics.files", ready.file,
            )
            val intent = Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(uri, MIME_APK)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                clipData = ClipData.newRawUri("SENTINEL update", uri)
            }
            context.startActivity(intent)
            InstallOutcome.LAUNCHED
        } catch (_: Exception) {
            InstallOutcome.FAILED
        }
    }
}
