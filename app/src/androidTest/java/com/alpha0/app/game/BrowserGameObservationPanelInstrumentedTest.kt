package com.alpha0.app.game

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.assertTextContains
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import com.alpha0.app.ui.AppThemeMode
import com.alpha0.app.ui.SentinelTheme
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

/** UI-only checks; no proof of Chrome tab origin or real-game permission. */
class BrowserGameObservationPanelInstrumentedTest {
    @get:Rule val compose = createComposeRule()

    @Test fun lastHavensNeverInheritsShatteredCaptureOrEnablesInput() {
        val latch = GameAutomationStopLatch()
        val opened = mutableListOf<String>()
        compose.setContent {
            SentinelTheme(AppThemeMode.LIGHT) {
                BrowserGameObservationPanel(
                    onReturnToShattered = {},
                    onOpenOfficialUrl = { opened.add(it); true },
                    stopLatch = latch,
                )
            }
        }
        compose.onNodeWithTag("game-browser-source-status").performScrollTo()
            .assertTextContains("UNVERIFIED", substring = true)
        compose.onNodeWithTag("game-automation-mode-bounded_active").performScrollTo().performClick()
        compose.onNodeWithTag("game-automation-risk-ack").performScrollTo().performClick()
        compose.onNodeWithTag("game-automation-rules-reviewed").performScrollTo().performClick()
        compose.onNodeWithTag("game-automation-enable").performScrollTo().assertIsNotEnabled()
        compose.onNodeWithTag("game-browser-open").performScrollTo().performClick()
        compose.runOnIdle {
            assertEquals(listOf("https://lasthavens.com/play"), opened)
            assertTrue(latch.state.value.latched)
        }
        compose.onNodeWithTag("game-automation-stop-latched").performScrollTo().assertIsDisplayed()
        compose.onNodeWithTag("game-automation-reset-stop").performScrollTo().assertIsNotEnabled()
    }

    @Test fun openingRulesAndMissingBrowserRemainReadOnlyWithVisibleError() {
        val opened = mutableListOf<String>()
        compose.setContent {
            SentinelTheme(AppThemeMode.DARK) {
                BrowserGameObservationPanel(
                    onReturnToShattered = {},
                    onOpenOfficialUrl = { opened.add(it); false },
                    stopLatch = GameAutomationStopLatch(),
                )
            }
        }
        compose.onNodeWithTag("game-browser-rules").performScrollTo().performClick()
        compose.runOnIdle { assertEquals(listOf("https://lasthavens.com/terms"), opened) }
        compose.onNodeWithTag("game-browser-open-error").performScrollTo().assertIsDisplayed()
        compose.onNodeWithTag("game-automation-enable").performScrollTo().assertIsNotEnabled()
        compose.onNodeWithTag("game-automation-stop").assertIsDisplayed()
    }
}
