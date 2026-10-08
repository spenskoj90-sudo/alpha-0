package com.alpha0.app.game

import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import com.alpha0.app.ui.AppThemeMode
import com.alpha0.app.ui.SentinelTheme
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

/** UI permission/state boundaries; not physical game or MediaProjection acceptance. */
class GameObservationScreenInstrumentedTest {
    @get:Rule val compose = createComposeRule()

    @Test fun unverifiedTargetShowsKnowledgeWaitingInsteadOfRecommendations() {
        compose.setContent {
            SentinelTheme(AppThemeMode.LIGHT) {
                GameObservationPanel(StockGameInstall("fixture", 1), GameObservationViewState(), true, false, false, 100,
                    {}, {}, {}, {})
            }
        }
        compose.onNodeWithText("Waiting for a verified target profile").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Review defense").assertDoesNotExist()
    }

    @Test fun missingGameCannotStartCaptureEvenWithConsent() {
        compose.setContent {
            SentinelTheme(AppThemeMode.LIGHT) {
                GameObservationPanel(null, GameObservationViewState(), true, true, false, 100,
                    {}, {}, {}, {})
            }
        }
        compose.onNodeWithTag("game-capture-start").performScrollTo().assertIsNotEnabled()
        compose.onNodeWithTag("game-capture-stop").assertDoesNotExist()
    }

    @Test fun captureRequiresExplicitConsentAndActiveSessionExposesStop() {
        val consent = mutableStateOf(false)
        val state = mutableStateOf(GameObservationViewState())
        var stopped = false
        compose.setContent {
            SentinelTheme(AppThemeMode.DARK) {
                GameObservationPanel(StockGameInstall("fixture", 1), state.value, true, consent.value, false, 100,
                    { consent.value = it }, {}, { stopped = true }, {})
            }
        }
        compose.onNodeWithTag("game-capture-start").performScrollTo().assertIsNotEnabled()
        compose.onNodeWithText("I agree to local screen analysis for this session.").performScrollTo().performClick()
        compose.onNodeWithTag("game-capture-start").assertIsEnabled()
        compose.runOnIdle { state.value = GameObservationViewState(ObservationSnapshot(status = ObservationStatus.PAUSED)) }
        compose.onNodeWithTag("game-capture-start").assertDoesNotExist()
        compose.onNodeWithTag("game-capture-stop").performScrollTo().performClick()
        compose.runOnIdle { assertTrue(stopped) }
    }
}
