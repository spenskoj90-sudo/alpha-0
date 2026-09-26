package com.alpha0.app.ui

import androidx.compose.ui.test.assertExists
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

class AdaptiveChromeInstrumentedTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun compactTopBarKeepsPhysicalIdentityAndExportReachable() {
        var exported = false
        composeRule.setContent {
            SentinelTheme(AppThemeMode.DARK) {
                SentinelTopBar(
                    title = "SENTINEL",
                    canGoBack = false,
                    onBack = {},
                    onNavigate = {},
                    compact = true,
                    compactContext = "PHYSICAL TEST · 1.0.0-rc2-physical-test · 4d272d9f5f7f · STAGING",
                    compactActionLabel = "Export logs",
                    onCompactAction = { exported = true },
                )
            }
        }

        composeRule.onNodeWithText("SENTINEL").assertExists()
        composeRule.onNodeWithText(
            "PHYSICAL TEST · 1.0.0-rc2-physical-test · 4d272d9f5f7f · STAGING",
        ).assertExists()
        composeRule.onNodeWithText("Export logs").performClick()
        composeRule.runOnIdle { assertTrue(exported) }
    }

    @Test
    fun sideRailExposesAllPrimaryDestinationsAndRoutesClicks() {
        var route: String? = null
        composeRule.setContent {
            SentinelTheme(AppThemeMode.DARK) {
                SentinelSideRail(selectedRoute = "home") { route = it }
            }
        }

        listOf("Home", "Games", "Security", "Activity").forEach {
            composeRule.onNodeWithText(it).assertExists()
        }
        composeRule.onNodeWithText("Games").performClick()
        composeRule.runOnIdle { assertEquals("games", route) }
    }
}
