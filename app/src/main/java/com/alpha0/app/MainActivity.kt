package com.alpha0.app

import android.app.Activity
import android.os.Bundle
import androidx.activity.compose.setContent
import com.alpha0.app.security.DeviceIdentity
import com.alpha0.app.ui.CharacterDashboard
import com.alpha0.app.ui.SentinelTheme

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val identity = runCatching { DeviceIdentity().getIdentityInfo() }
        setContent {
            SentinelTheme {
                CharacterDashboard(
                    characterName = "Operator",
                    level = 27,
                    health = 94,
                    energy = 82,
                    syncState = if (identity.isSuccess) "DEVICE IDENTITY READY" else "DEVICE IDENTITY FAILED"
                )
            }
        }
    }
}
