package com.alpha0.app.game

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.assertDoesNotExist
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.assertTextContains
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import com.alpha0.app.ui.AppThemeMode
import com.alpha0.app.ui.SentinelTheme
import org.junit.Rule
import org.junit.Test

class ManualHealingReferenceInstrumentedTest {
    @get:Rule val compose = createComposeRule()

    @Test fun unknownFactsNeverBecomeGameAdviceAndResetClearsThem() {
        compose.setContent {
            SentinelTheme(AppThemeMode.LIGHT) {
                Column(Modifier.verticalScroll(rememberScrollState())) {
                    ManualHealingReferencePanel(StockGameInstall("4.0.2", 922), null, false)
                }
            }
        }
        compose.onNodeWithTag("game-manual-result").performScrollTo().assertTextContains("Unknown", substring = true)
        compose.onNodeWithTag("game-manual-reset").performScrollTo().assertIsNotEnabled()
        compose.onNodeWithTag("game-manual-low-yes").performScrollTo().performClick()
        compose.onNodeWithTag("game-manual-pharma-no").performScrollTo().performClick()
        compose.onNodeWithTag("game-manual-result").performScrollTo().assertTextContains("Unknown", substring = true)
        compose.onNodeWithTag("game-manual-potion-yes").performScrollTo().performClick()
        compose.onNodeWithTag("game-manual-result").performScrollTo().assertTextContains("possible option", substring = true)
        compose.onNodeWithTag("game-manual-pharma-yes").performScrollTo().performClick()
        compose.onNodeWithTag("game-manual-result").performScrollTo().assertTextContains("poisons", substring = true)
        compose.onNodeWithTag("game-manual-reset").performScrollTo().performClick()
        compose.onNodeWithTag("game-manual-result").performScrollTo().assertTextContains("Unknown", substring = true)
    }

    @Test fun wrongVersionNeverShowsManualControls() {
        compose.setContent {
            SentinelTheme(AppThemeMode.DARK) {
                ManualHealingReferencePanel(StockGameInstall("4.0.1", 922), null, false)
            }
        }
        compose.onNodeWithTag("game-manual-result").assertTextContains("4.0.2", substring = true)
        compose.onNodeWithTag("game-manual-low-yes").assertDoesNotExist()
    }
}
