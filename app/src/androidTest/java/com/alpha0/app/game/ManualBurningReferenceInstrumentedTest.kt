package com.alpha0.app.game

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.assertTextContains
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import com.alpha0.app.ui.AppThemeMode
import com.alpha0.app.ui.SentinelTheme
import org.junit.Rule
import org.junit.Test

/** Local UI states; not actual capture, publisher or gameplay acceptance. */
class ManualBurningReferenceInstrumentedTest {
    @get:Rule val compose = createComposeRule()

    @Test fun unknownSafeWaterFlyingAndResetRemainsManualOnly() {
        compose.setContent {
            SentinelTheme(AppThemeMode.LIGHT) {
                Column(Modifier.verticalScroll(rememberScrollState())) {
                    ManualBurningReferencePanel(StockGameInstall("4.0.2", 922), null, false)
                }
            }
        }
        compose.onNodeWithTag("game-manual-burn-toggle").performScrollTo().performClick()
        compose.onNodeWithTag("game-manual-burn-result").performScrollTo()
            .assertTextContains("Unknown", substring = true)
        compose.onNodeWithTag("game-manual-burn-burning-yes").performScrollTo().performClick()
        compose.onNodeWithTag("game-manual-burn-flying-no").performScrollTo().performClick()
        compose.onNodeWithTag("game-manual-burn-water-no").performScrollTo().performClick()
        compose.onNodeWithTag("game-manual-burn-result").performScrollTo()
            .assertTextContains("Unknown", substring = true)
        compose.onNodeWithTag("game-manual-burn-safe-yes").performScrollTo().performClick()
        compose.onNodeWithTag("game-manual-burn-result").performScrollTo()
            .assertTextContains("possible", substring = true)
        compose.onNodeWithTag("game-manual-burn-flying-yes").performScrollTo().performClick()
        compose.onNodeWithTag("game-manual-burn-result").performScrollTo()
            .assertTextContains("Flying", substring = true)
        compose.onNodeWithTag("game-manual-burn-flying-no").performScrollTo().performClick()
        compose.onNodeWithTag("game-manual-burn-water-yes").performScrollTo().performClick()
        compose.onNodeWithTag("game-manual-burn-result").performScrollTo()
            .assertTextContains("water", substring = true)
        compose.onNodeWithTag("game-manual-burn-reset").performScrollTo().performClick()
        compose.onNodeWithTag("game-manual-burn-result").performScrollTo()
            .assertTextContains("Unknown", substring = true)
    }

    @Test fun activeCapturePausesAndRevokesManualAnswers() {
        val active = mutableStateOf(false)
        compose.setContent {
            SentinelTheme(AppThemeMode.DARK) {
                Column(Modifier.verticalScroll(rememberScrollState())) {
                    ManualBurningReferencePanel(StockGameInstall("4.0.2", 922), null, active.value)
                }
            }
        }
        compose.onNodeWithTag("game-manual-burn-toggle").performScrollTo().performClick()
        compose.runOnIdle { active.value = true }
        compose.onNodeWithTag("game-manual-burn-result").performScrollTo()
            .assertTextContains("paused", substring = true)
        compose.onNodeWithTag("game-manual-burn-burning-yes").assertDoesNotExist()
        compose.runOnIdle { active.value = false }
        compose.onNodeWithTag("game-manual-burn-burning-yes").assertDoesNotExist()
    }
}
