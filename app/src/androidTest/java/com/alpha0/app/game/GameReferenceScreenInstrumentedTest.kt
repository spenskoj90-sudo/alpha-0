package com.alpha0.app.game

import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsSelected
import androidx.compose.ui.test.assertTextContains
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import com.alpha0.app.ui.AppThemeMode
import com.alpha0.app.ui.SentinelTheme
import org.junit.Rule
import org.junit.Test
import org.junit.Assert.assertEquals
import java.util.concurrent.atomic.AtomicInteger

/** Read-only reference UI, not a real player or MediaProjection proof. */
class GameReferenceScreenInstrumentedTest {
    @get:Rule val compose = createComposeRule()

    @Test fun referenceShowsManualRulesWithoutCaptureControls() {
        compose.setContent {
            SentinelTheme(AppThemeMode.LIGHT) {
                GameReferencePanel(StockGameInstall("4.0.2", 922))
            }
        }
        compose.onNodeWithTag("game-manual-result").performScrollTo()
            .assertTextContains("Unknown", substring = true)
        compose.onNodeWithTag("game-manual-burn-toggle").performScrollTo()
            .assertIsDisplayed().performClick()
        compose.onNodeWithTag("game-manual-burn-result").performScrollTo()
            .assertTextContains("Unknown", substring = true)
        compose.onNodeWithTag("game-capture-start").assertDoesNotExist()
        compose.onNodeWithTag("game-capture-stop").assertDoesNotExist()
    }

    @Test fun referenceRoutePausesManualFactsAcrossCaptureLifecycle() {
        val capturing = mutableStateOf(false)
        compose.setContent {
            SentinelTheme(AppThemeMode.LIGHT) {
                GameReferencePanel(
                    StockGameInstall("4.0.2", 922),
                    captureId = if (capturing.value) "capture-live" else null,
                    captureActive = capturing.value,
                )
            }
        }
        compose.onNodeWithTag("game-manual-low-yes").performScrollTo().performClick()
        compose.runOnUiThread { capturing.value = true }
        compose.onNodeWithTag("game-manual-result").performScrollTo()
            .assertTextContains("paused", substring = true)
        compose.onNodeWithTag("game-manual-burn-result").performScrollTo()
            .assertTextContains("paused", substring = true)
        compose.onNodeWithTag("game-manual-low-yes").assertDoesNotExist()
        compose.onNodeWithTag("game-manual-burn-toggle").assertDoesNotExist()

        compose.runOnUiThread { capturing.value = false }
        // User self-reported facts must not survive a stopped capture epoch.
        compose.onNodeWithTag("game-manual-low-unknown").performScrollTo()
            .assertIsSelected()
        compose.onNodeWithTag("game-manual-burn-toggle").performScrollTo()
            .assertIsDisplayed()
    }

    @Test fun absentGameRemainsUnsupportedInsteadOfInventingSource() {
        compose.setContent {
            SentinelTheme(AppThemeMode.DARK) { GameReferencePanel(null) }
        }
        compose.onNodeWithText("Install the ordinary Shattered Pixel Dungeon app", substring = true)
            .performScrollTo().assertIsDisplayed()
        compose.onNodeWithTag("game-manual-burn-result").performScrollTo()
            .assertTextContains("requires", substring = true)
        compose.onNodeWithTag("game-capture-start").assertDoesNotExist()
    }

    @Test fun activeReferenceHasPersistentStopWithoutEnablingCaptureControls() {
        val capturing = mutableStateOf(true)
        val stops = AtomicInteger(0)
        compose.setContent {
            SentinelTheme(AppThemeMode.LIGHT) {
                GameReferencePanel(
                    installed = StockGameInstall("4.0.2", 922),
                    captureId = "observing-session",
                    captureActive = capturing.value,
                    onStop = {
                        stops.incrementAndGet()
                        capturing.value = false
                    },
                )
            }
        }
        // The fixed bottom-bar action is reachable without scrolling through
        // the manual rules, and dispatches exactly once through the supplied
        // production Stop boundary (not a semantics-only shortcut).
        compose.waitForIdle()
        compose.onNodeWithTag("game-capture-stop")
            .assertIsDisplayed().assertIsEnabled().performClick()
        compose.waitUntil(timeoutMillis = 3000) { stops.get() == 1 }
        compose.runOnIdle { assertEquals(1, stops.get()) }
        compose.onNodeWithTag("game-capture-stop").assertDoesNotExist()
        compose.onNodeWithTag("game-capture-start").assertDoesNotExist()
        compose.onNodeWithTag("game-manual-low-unknown").performScrollTo()
            .assertIsSelected()
    }
}
