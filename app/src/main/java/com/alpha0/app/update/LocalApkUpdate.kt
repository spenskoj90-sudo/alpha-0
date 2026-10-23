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

/** Local user-selected diagnostic APKs. Android owns final, explicit installation consent. */
internal object LocalApkUpdate {
    private const val MAX_APK_BYTES = 256L * 1024 * 1024
    private const val MIME_APK = "application/vnd.android.package-archive"
    private const val UPDATE_FOLDER = "sentinel_updates"

    sealed interface Result {
        data class Ready(val file: File, val versionCode: Long, val sha256: String) : Result
        data class Blocked(val reason: ApkUpdatePolicy.BlockReason) : Result
        data object Failed : Result
    }

    enum class InstallOutcome { LAUNCHED, PERMISSION_REQUIRED, BLOCKED, FAILED }

    private fun candidateInfo(context: Context, file: File): PackageInfo? {
        val manager = context.packageManager
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            manager.getPackageArchiveInfo(
                file.absolutePath,
                PackageManager.PackageInfoFlags.of(PackageManager.GET_SIGNING_CERTIFICATES.toLong()),
            )
        } else {
            @Suppress("DEPRECATION")
            manager.getPackageArchiveInfo(file.absolutePath, PackageManager.GET_SIGNING_CERTIFICATES)
        }
    }

    private fun installedInfo(context: Context): PackageInfo {
        val manager = context.packageManager
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            manager.getPackageInfo(
                context.packageName,
                PackageManager.PackageInfoFlags.of(PackageManager.GET_SIGNING_CERTIFICATES.toLong()),
            )
        } else {
            @Suppress("DEPRECATION")
            manager.getPackageInfo(context.packageName, PackageManager.GET_SIGNING_CERTIFICATES)
        }
    }

    private fun signers(info: PackageInfo): List<String> {
        val signing = info.signingInfo ?: return emptyList()
        // Signing rotation and multi-signer lineage need a separate, verified contract.
        if (signing.hasMultipleSigners()) return emptyList()
        return signing.apkContentsSigners?.map { signature ->
            MessageDigest.getInstance("SHA-256").digest(signature.toByteArray())
                .joinToString("") { "%02x".format(it.toInt() and 0xff) }
        } ?: emptyList()
    }

    private fun policyCheck(context: Context, file: File): ApkUpdatePolicy.BlockReason? {
        val candidate = candidateInfo(context, file) ?: throw IllegalArgumentException("INVALID_APK")
        val installed = installedInfo(context)
        return ApkUpdatePolicy.check(
            installed.packageName, installed.longVersionCode, signers(installed),
            candidate.packageName, candidate.longVersionCode, signers(candidate),
        )
    }

    /**
     * Every candidate gets a distinct private file. A second selection must not silently
     * replace bytes at a FileProvider URI already granted to Android's installer.
     */
    suspend fun stage(context: Context, uri: Uri): Result = withContext(Dispatchers.IO) {
        val folder = File(context.cacheDir, UPDATE_FOLDER)
        if (!folder.isDirectory && !folder.mkdirs()) return@withContext Result.Failed
        var temporary: File? = null
        var staged: File? = null
        try {
            val temp = File.createTempFile("candidate-", ".tmp", folder)
            temporary = temp
            val candidateFile = File(folder, temp.name.removeSuffix(".tmp") + ".apk")
            staged = candidateFile
            val digest = MessageDigest.getInstance("SHA-256")
            var size = 0L
            val input = context.contentResolver.openInputStream(uri)
                ?: throw IllegalArgumentException("APK_UNREADABLE")
            input.use { source ->
                FileOutputStream(temp).use { output ->
                    val buffer = ByteArray(64 * 1024)
                    while (true) {
                        val count = source.read(buffer)
                        if (count < 0) break
                        if (count == 0) continue
                        size += count.toLong()
                        if (size > MAX_APK_BYTES) throw IllegalArgumentException("APK_TOO_LARGE")
                        output.write(buffer, 0, count)
                        digest.update(buffer, 0, count)
                    }
                    output.fd.sync()
                }
            }
            if (size == 0L || !temp.renameTo(candidateFile)) throw IllegalArgumentException("INVALID_APK")
            val reason = policyCheck(context, candidateFile)
            if (reason != null) {
                candidateFile.delete()
                Result.Blocked(reason)
            } else {
                val candidate = candidateInfo(context, candidateFile) ?: throw IllegalArgumentException("INVALID_APK")
                val sha = digest.digest().joinToString("") { "%02x".format(it.toInt() and 0xff) }
                if (!candidateFile.setReadOnly()) throw IllegalArgumentException("STAGING_NOT_READ_ONLY")
                Result.Ready(candidateFile, candidate.longVersionCode, sha)
            }
        } catch (cancel: CancellationException) {
            staged?.delete()
            throw cancel
        } catch (_: Exception) {
            staged?.delete()
            Result.Failed
        } finally {
            temporary?.delete()
        }
    }

    private fun trustedStagedFile(context: Context, file: File): Boolean {
        val folder = File(context.cacheDir, UPDATE_FOLDER)
        return file.isFile &&
            file.parentFile?.canonicalFile == folder.canonicalFile &&
            Regex("candidate-[A-Za-z0-9_-]+\\.apk").matches(file.name) &&
            file.length() in 1..MAX_APK_BYTES
    }

    private fun digestMatches(file: File, expected: String): Boolean {
        if (!Regex("[0-9a-f]{64}").matches(expected)) return false
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(64 * 1024)
            var read = 0L
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                if (count == 0) continue
                read += count.toLong()
                if (read > MAX_APK_BYTES) return false
                digest.update(buffer, 0, count)
            }
        }
        val expectedBytes = expected.chunked(2).map { it.toInt(16).toByte() }.toByteArray()
        return MessageDigest.isEqual(expectedBytes, digest.digest())
    }

    /**
     * Re-check on an IO dispatcher immediately before handing off to Android.
     * This blocks a stale Ready result and a changed APK while the user reads the prompt.
     */
    suspend fun install(context: Context, ready: Result.Ready): InstallOutcome {
        val valid = withContext(Dispatchers.IO) {
            try {
                if (!trustedStagedFile(context, ready.file) || !digestMatches(ready.file, ready.sha256)) {
                    return@withContext false
                }
                val candidate = candidateInfo(context, ready.file)
                    ?: return@withContext false
                candidate.longVersionCode == ready.versionCode &&
                    policyCheck(context, ready.file) == null
            } catch (_: Exception) {
                false
            }
        }
        if (!valid) return InstallOutcome.BLOCKED
        return withContext(Dispatchers.Main) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O &&
                !context.packageManager.canRequestPackageInstalls()
            ) return@withContext InstallOutcome.PERMISSION_REQUIRED
            try {
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
}
