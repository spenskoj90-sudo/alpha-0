package com.alpha0.app.update

import android.net.Uri
import androidx.core.content.FileProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.alpha0.app.BuildConfig
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.security.MessageDigest

/**
 * Exercises the real APK archive metadata API + FileProvider before/after
 * emulator package replacement. No production secret or real account involved.
 */
@RunWith(AndroidJUnit4::class)
class UpdatePreflightInstrumentedTest {
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext
    private val candidate get() = File(context.filesDir, "synthetic_candidate.apk")
    private val candidateCode = 1700000302L

    private fun diagnosticOnly() {
        assumeTrue(BuildConfig.SENTINEL_DISTRIBUTION_CHANNEL == "diagnostic")
        assertEquals("com.alpha0.app.physicaltest", context.packageName)
    }

    @Test
    fun acceptsCompatibleNewerSameSignerApk() = runBlocking {
        diagnosticOnly()
        assertTrue("Next APK absent from target app-private storage", candidate.isFile)
        val digest = MessageDigest.getInstance("SHA-256")
        candidate.forEachBlock(64 * 1024) { bytes, count ->
            digest.update(bytes, 0, count)
        }
        val expectedDigest = digest.digest().joinToString("") { "%02x".format(it.toInt() and 0xff) }

        val result = LocalApkUpdate.stage(context, Uri.fromFile(candidate))
        assertTrue("Compatible APK should pass actual PackageManager preflight: $result",
            result is LocalApkUpdate.Result.Ready)
        val ready = result as LocalApkUpdate.Result.Ready
        assertEquals(candidateCode, ready.versionCode)
        assertEquals(expectedDigest, ready.sha256)
        assertTrue(ready.file.isFile)
        assertTrue("Unique staging filename required", ready.file.name.endsWith(".apk"))
        assertEquals(File(context.cacheDir, "sentinel_updates").canonicalPath, ready.file.parentFile.canonicalPath)
        assertTrue(ready.file.name.startsWith("candidate-"))
        val sharedUri = FileProvider.getUriForFile(
            context, context.packageName + ".diagnostics.files", ready.file)
        context.contentResolver.openInputStream(sharedUri).use { input ->
            assertTrue("System installer cannot read staged FileProvider URI",
                input != null && input.read() >= 0)
        }

        // A second choice must not alter the first installer URI's bytes.
        val second = LocalApkUpdate.stage(context, Uri.fromFile(candidate))
        assertTrue("Repeated selection must remain a compatible candidate",
            second is LocalApkUpdate.Result.Ready)
        val newerReady = second as LocalApkUpdate.Result.Ready
        assertTrue("Candidate files must be distinct", newerReady.file != ready.file)
        assertEquals("Old candidate receipt changed", expectedDigest, ready.sha256)
        assertEquals("New candidate bytes differ", expectedDigest, newerReady.sha256)
        assertTrue("Old installer file disappeared on reselection", ready.file.isFile)

        // Corrupt a staged candidate after checking it. No installer may be launched.
        assertTrue("Test must be able to edit isolated staged file", ready.file.setWritable(true))
        ready.file.appendBytes(byteArrayOf(0x41))
        assertEquals("Changed candidate must be rejected before invoking Android",
            LocalApkUpdate.InstallOutcome.BLOCKED, LocalApkUpdate.install(context, ready))
        assertTrue("New selection must remain unchanged", newerReady.file.isFile)
    }

    @Test
    fun rejectsSameVersionAfterUpgrade() = runBlocking {
        diagnosticOnly()
        assertTrue("Source test APK must survive the upgrade", candidate.isFile)
        assertEquals(candidateCode, context.packageManager.getPackageInfo(
            context.packageName, 0).longVersionCode)
        val result = LocalApkUpdate.stage(context, Uri.fromFile(candidate))
        assertTrue("Installed APK cannot be offered as an update: $result",
            result is LocalApkUpdate.Result.Blocked)
        assertEquals(ApkUpdatePolicy.BlockReason.VERSION_NOT_HIGHER,
            (result as LocalApkUpdate.Result.Blocked).reason)
        // A previously accepted candidate may still be in use by the system installer.
        // A rejected candidate must never return Ready or create an installer request.
    }
}
