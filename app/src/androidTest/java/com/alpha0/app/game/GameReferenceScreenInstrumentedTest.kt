package com.alpha0.app.game

import androidx.compose.ui.test.assertIsDisplayed
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
}
