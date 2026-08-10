package com.alpha0.app

import android.app.Activity
import android.graphics.Typeface
import android.os.Bundle
import android.view.Gravity
import android.widget.LinearLayout
import android.widget.TextView
import com.alpha0.app.security.DeviceIdentity
import java.security.SecureRandom

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(48, 48, 48, 48)
        }

        val title = TextView(this).apply {
            text = "SENTINEL Alpha-0"
            textSize = 28f
            typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER
        }

        val status = TextView(this).apply {
            textSize = 17f
            gravity = Gravity.CENTER
            setPadding(0, 32, 0, 0)
        }

        root.addView(title)
        root.addView(status)
        setContentView(root)

        initializeDeviceIdentity(status)
    }

    private fun initializeDeviceIdentity(status: TextView) {
        try {
            val identity = DeviceIdentity()
            val info = identity.getIdentityInfo()
            val challenge = ByteArray(32).also { SecureRandom().nextBytes(it) }
            val signature = identity.sign(challenge)
            val signatureValid = identity.verify(challenge, signature)

            val tamperedChallenge = challenge.clone().also {
                it[0] = (it[0].toInt() xor 0x01).toByte()
            }
            val tamperedRejected = !identity.verify(tamperedChallenge, signature)
            val keyNonExportable = !identity.isPrivateKeyExported()
            val cryptoPassed = signatureValid && tamperedRejected && keyNonExportable

            status.text = """
                Device Identity

                Algorithm:
                ${info.algorithm}

                Fingerprint:
                ${info.fingerprint.take(16)}…

                Private key:
                Android Keystore / non-exportable

                Cryptographic self-test:
                Signature: ${if (signatureValid) "PASS" else "FAIL"}
                Tampered challenge: ${if (tamperedRejected) "REJECTED" else "ACCEPTED"}
                Private key export: ${if (keyNonExportable) "BLOCKED" else "EXPOSED"}

                Status:
                ${if (cryptoPassed) "READY" else "CRYPTO FAILED"}
            """.trimIndent()
        } catch (_: Exception) {
            status.text = """
                Device Identity

                Status:
                FAILED

                Secure initialization could not be completed.
            """.trimIndent()
        }
    }
}
