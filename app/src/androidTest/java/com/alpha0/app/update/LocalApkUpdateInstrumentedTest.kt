package com.alpha0.app.update

import android.net.Uri
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/** Exercises Android's real APK archive parser/signing metadata on a device/emulator. */
@RunWith(AndroidJUnit4::class)
class LocalApkUpdateInstrumentedTest {
    @Test
    fun installed_apk_cannot_be_submitted_as_its_own_upgrade() = runBlocking {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val installedApk = File(context.applicationInfo.sourceDir)
        assertTrue(installedApk.isFile)

        val result = LocalApkUpdate.stage(context, Uri.fromFile(installedApk))

        assertTrue("Expected a version rejection from the real PackageManager", result is LocalApkUpdate.Result.Blocked)
        assertEquals(
            ApkUpdatePolicy.BlockReason.VERSION_NOT_HIGHER,
            (result as LocalApkUpdate.Result.Blocked).reason,
        )
        assertFalse(File(context.cacheDir, "sentinel_updates").listFiles().orEmpty().any { it.extension == "apk" })
    }
}
