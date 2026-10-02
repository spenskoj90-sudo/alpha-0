package com.alpha0.app.diagnostics

import android.content.pm.PackageManager
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.alpha0.app.BuildConfig
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class SigningCertificateEvidenceInstrumentedTest {
    @Test fun installed_package_certificate_metadata_is_bound_and_export_safe() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        @Suppress("DEPRECATION")
        val info = context.packageManager.getPackageInfo(context.packageName, PackageManager.GET_SIGNING_CERTIFICATES)
        val signing = requireNotNull(info.signingInfo)
        val details = SigningCertificateEvidence.details(
            context.packageName, info.longVersionCode,
            signing.apkContentsSigners.orEmpty().map { it.toByteArray() },
            if (signing.hasMultipleSigners()) emptyList()
            else signing.signingCertificateHistory.orEmpty().map { it.toByteArray() },
            signing.hasMultipleSigners(),
        )
        assertEquals(BuildConfig.APPLICATION_ID, details["package_name"])
        assertEquals(BuildConfig.VERSION_CODE.toLong(), details["installed_version_code"])
        assertTrue(details["signer_cert_sha256"].toString().split(",").all { Regex("[0-9a-f]{64}").matches(it) })
        assertTrue(details.keys.none { DiagnosticLogger.isSensitiveDetailKey(it) })
        assertFalse(details.containsKey("updateCompatible"))
    }
}
