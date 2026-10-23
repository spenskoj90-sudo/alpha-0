package com.alpha0.app.security

import androidx.test.ext.junit.runners.AndroidJUnit4
import android.content.Context
import java.security.KeyStore
import androidx.test.platform.app.InstrumentationRegistry
import com.alpha0.app.BuildConfig
import com.alpha0.app.ui.AppLanguage
import com.alpha0.app.ui.AppPreferences
import com.alpha0.app.ui.AppThemeMode
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.Assume.assumeTrue
import org.junit.runner.RunWith

/**
 * Synthetic values only. The normal debug instrumentation skips these tests;
 * the dedicated E2E workflow selects the physicalTest build type explicitly.
 * This source is never part of the installed application APK.
 */
@RunWith(AndroidJUnit4::class)
class UpgradeContinuityInstrumentedTest {
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext
    private val prefsName = "sentinel_upgrade_e2e_only"
    private val proofKey = "device_fingerprint_sha256"
    private val sampleAccess = "synthetic-upgrade-access"
    private val sampleRefresh = "synthetic-upgrade-refresh"
    private val sampleDevice = "synthetic-upgrade-device"

    @Test
    fun seedDeviceState() {
        assumeTrue(BuildConfig.SENTINEL_DISTRIBUTION_CHANNEL == "diagnostic")
        assertEquals("com.alpha0.app.physicaltest", BuildConfig.APPLICATION_ID)
        val identity = DeviceIdentity().also { it.attachDiagnostics(context) }
        val fingerprint = identity.getIdentityInfo().fingerprint
        assertTrue(Regex("[0-9a-f]{64}").matches(fingerprint))
        assertTrue(
            context.getSharedPreferences(prefsName, 0).edit()
                .putString(proofKey, fingerprint).commit()
        )
        assertTrue(identity.verify("synthetic-challenge".toByteArray(),
            identity.sign("synthetic-challenge".toByteArray())))
        SecureSessionStore().save(context, sampleAccess, sampleRefresh, sampleDevice)
        // Explicitly flush the preceding async SharedPreferences write before
        // the instrumentation process exits and the package is replaced.
        val encryptedPrefs = context.getSharedPreferences("sentinel_session", Context.MODE_PRIVATE)
        assertTrue("Synthetic encrypted session absent before upgrade",
            encryptedPrefs.contains("access_token") && encryptedPrefs.contains("refresh_token"))
        assertTrue("Synthetic encrypted session not durable", encryptedPrefs.edit().commit())
        assertTrue("Synthetic session AES alias missing before upgrade",
            KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
                .containsAlias("alpha0.session.aes.v1"))
        val settings = AppPreferences(context)
        settings.setLanguage(AppLanguage.RUSSIAN)
        settings.setTheme(AppThemeMode.DARK)
        val saved = SecureSessionStore().load(context)
        assertEquals(sampleDevice, saved?.deviceId)
    }

    @Test
    fun verifyPreservedDeviceState() {
        assumeTrue(BuildConfig.SENTINEL_DISTRIBUTION_CHANNEL == "diagnostic")
        assertEquals("com.alpha0.app.physicaltest", BuildConfig.APPLICATION_ID)
        val before = context.getSharedPreferences(prefsName, 0)
            .getString(proofKey, null)
        assertTrue("Missing pre-update identity proof", before != null &&
            Regex("[0-9a-f]{64}").matches(before))
        val identity = DeviceIdentity().also { it.attachDiagnostics(context) }
        assertEquals("Android Keystore identity changed", before, identity.getIdentityInfo().fingerprint)
        val challenge = "post-upgrade-synthetic-challenge".toByteArray()
        assertTrue("Preserved private key must sign", identity.verify(challenge, identity.sign(challenge)))
        val encryptedPrefs = context.getSharedPreferences("sentinel_session", Context.MODE_PRIVATE)
        assertTrue("Encrypted access record absent after upgrade",
            encryptedPrefs.contains("access_token"))
        assertTrue("Encrypted refresh record absent after upgrade",
            encryptedPrefs.contains("refresh_token"))
        assertTrue("Synthetic session AES alias absent after upgrade",
            KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
                .containsAlias("alpha0.session.aes.v1"))
        val session = SecureSessionStore().load(context)
        assertEquals("Encrypted access session lost", sampleAccess, session?.accessToken)
        assertEquals("Encrypted refresh session lost", sampleRefresh, session?.refreshToken)
        assertEquals("Device registration value lost", sampleDevice, session?.deviceId)
        assertEquals(AppLanguage.RUSSIAN, AppPreferences(context).language())
        assertEquals(AppThemeMode.DARK, AppPreferences(context).theme())
    }
}
