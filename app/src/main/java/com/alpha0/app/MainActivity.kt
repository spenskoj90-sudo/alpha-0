package com.alpha0.app

import android.app.Activity
import android.graphics.Typeface
import android.os.Bundle
import android.view.Gravity
import android.widget.LinearLayout
import android.widget.TextView
import com.alpha0.app.security.DeviceIdentity

class MainActivity : Activity() {

override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)

    val root = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        gravity = Gravity.CENTER
        setPadding(48, 48, 48, 48)
    }

    val title = TextView(this).apply {
        text = "ALPHA-0"
        textSize = 32f
        typeface = Typeface.DEFAULT_BOLD
        gravity = Gravity.CENTER
    }

    val status = TextView(this).apply {
        textSize = 18f
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
        val identity = DeviceIdentity().getIdentityInfo()

        status.text = """
            BUILD-002A

            Device Identity initialized.

            Algorithm:
            ${identity.algorithm}

            Fingerprint:
            ${identity.fingerprint}

            Private key:
            Android Keystore

            Status:
            READY
        """.trimIndent()

    } catch (error: Exception) {
        status.text = """
            BUILD-002A

            Device Identity:
            FAILED

            ${error.javaClass.simpleName}

            ${error.message ?: "Unknown error"}
        """.trimIndent()
    }
}

}
