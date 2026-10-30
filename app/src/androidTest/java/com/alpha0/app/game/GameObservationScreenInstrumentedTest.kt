package com.alpha0.app.game

import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.assertTextContains
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
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
        compose.onNodeWithTag("game-capture-stop").assertIsDisplayed().performClick()
        compose.runOnIdle { assertTrue(stopped) }
    }

    @Test fun localSignerMetadataNeverClaimsPublisherOrCaptureSource() {
        val install = mutableStateOf(StockGameInstall("fixture", 1, "a".repeat(64)))
        compose.setContent {
            SentinelTheme(AppThemeMode.LIGHT) {
                GameObservationPanel(install.value, GameObservationViewState(), true, false, false, 100,
                    {}, {}, {}, {})
            }
        }
        compose.onNodeWithText("Installed game package: com.shatteredpixel.shatteredpixeldungeon")
            .performScrollTo().assertIsDisplayed()
        compose.onNodeWithText(
            "Installed APK signer detected locally; publisher identity and selected capture app remain UNVERIFIED.",
        ).performScrollTo().assertIsDisplayed()
        compose.runOnIdle { install.value = StockGameInstall("fixture", 1) }
        compose.onNodeWithText("Installed APK signer UNKNOWN. Game version and capture-source identity are not verified.")
            .performScrollTo().assertIsDisplayed()
    }

    @Test fun stopRemainsVisibleWithoutScrollingWhenCalibrationIsBelowFold() {
        val state = mutableStateOf(GameObservationViewState(
            ObservationSnapshot(status = ObservationStatus.OBSERVING, frames = 8),
        ))
        var stops = 0
        compose.setContent {
            SentinelTheme(AppThemeMode.DARK) {
                GameObservationPanel(StockGameInstall("fixture", 1), state.value, true, false, false, 100,
                    {}, {}, { stops++ }, {})
            }
        }
        // A screen-filling diagnostic/calibration column must not push Stop off screen.
        compose.onNodeWithTag("game-capture-stop").assertIsDisplayed().performClick()
        compose.runOnIdle { assertTrue(stops == 1) }
        compose.runOnIdle {
            state.value = GameObservationViewState(
                ObservationSnapshot(status = ObservationStatus.STOPPED),
            )
        }
        compose.onNodeWithTag("game-capture-stop").assertDoesNotExist()
    }

    @Test fun numericCalibrationFormClearsOnStopAndFreshCapture() {
        val active = mutableStateOf(GameObservationViewState(
            ObservationSnapshot(status = ObservationStatus.PAUSED, captureId = "capture-a"),
            StockGameInstall("fixture", 1),
        ))
        compose.setContent {
            SentinelTheme(AppThemeMode.LIGHT) {
                GameObservationPanel(StockGameInstall("fixture", 1), active.value, true, false, false, 100,
                    {}, {}, {}, {})
            }
        }
        compose.onNodeWithTag("game-calibration-current")
            .performScrollTo().performTextInput("15")
        compose.onNodeWithTag("game-calibration-maximum")
            .performScrollTo().performTextInput("20")
        compose.onNodeWithTag("game-calibration-current").assertTextContains("15")
        // Even while the numeric field owns IME focus, the user's Stop remains reachable.
        compose.onNodeWithTag("game-capture-stop").assertIsDisplayed()
        compose.runOnIdle {
            active.value = GameObservationViewState(
                ObservationSnapshot(status = ObservationStatus.STOPPED), StockGameInstall("fixture", 1),
            )
        }
        // The previous capture's typed private comparison must not survive Stop.
        compose.onNodeWithTag("game-calibration-current").assertTextContains("", substring = false)
        compose.onNodeWithTag("game-calibration-maximum").assertTextContains("", substring = false)
        compose.runOnIdle {
            active.value = GameObservationViewState(
                ObservationSnapshot(status = ObservationStatus.WAITING, captureId = "capture-b"),
                StockGameInstall("fixture", 1),
            )
        }
        compose.onNodeWithTag("game-calibration-current").assertTextContains("", substring = false)
    }

    @Test fun recentOcrHypothesisDegradesToHistoryThenDisappearsOnStop() {
        val health = HealthCandidate(8, 20, 0)
        val snapshot = ObservationSnapshot(
            status = ObservationStatus.OBSERVING, captureId = "capture-a",
            frames = 1, lastFrameAt = 110L, health = health,
            lastHealth = HealthObservation(health, 110L),
            lastRecognizedFrameAt = 110L,
            lastCompletedFrameSequence = 1L, lastCompletedFrameAt = 110L,
            lastCompletedOcrAt = 111L, lastOcrLatencyMs = 1L,
        )
        val state = mutableStateOf(GameObservationViewState(snapshot, StockGameInstall("fixture", 1)))
        val now = mutableStateOf(111L)
        compose.setContent {
            SentinelTheme(AppThemeMode.DARK) {
                GameObservationPanel(StockGameInstall("fixture", 1), state.value, true, false, false, now.value,
                    {}, {}, {}, {})
            }
        }
        compose.onNodeWithText("Recent OCR hypothesis · NOT verified game state")
            .performScrollTo().assertIsDisplayed()
        compose.runOnIdle { now.value = 5111L }
        compose.onNodeWithText("Historical OCR only · NOT current health")
            .performScrollTo().assertIsDisplayed()
        compose.runOnIdle {
            state.value = GameObservationViewState(ObservationSnapshot(status = ObservationStatus.STOPPED))
        }
        compose.onNodeWithText("Historical OCR only · NOT current health").assertDoesNotExist()
    }

    @Test fun captureFailureAnnouncesExactlyOneErrorAndAccessibleState() {
        val failed = GameObservationViewState(ObservationSnapshot(
            status = ObservationStatus.FAILED, reason = "CAPTURE_RESIZE_FAILED",
        ))
        compose.setContent {
            SentinelTheme(AppThemeMode.LIGHT) {
                GameObservationPanel(StockGameInstall("fixture", 1), failed, true, false, false, 100,
                    {}, {}, {}, {})
            }
        }
        compose.onNodeWithTag("game-observation-state").assert(
            SemanticsMatcher.expectValue(SemanticsProperties.LiveRegion, LiveRegionMode.Polite)
        )
        compose.onAllNodesWithTag("game-observer-error").assertCountEquals(1)
        compose.onNodeWithTag("game-observer-error").performScrollTo().assert(
            SemanticsMatcher.expectValue(SemanticsProperties.LiveRegion, LiveRegionMode.Assertive)
        )
        compose.onNodeWithTag("game-capture-stop").assertDoesNotExist()
    }

    @Test fun revokedCaptureShowsOneAssertiveReasonAndNoStopOrLiveEvidence() {
        val snapshot = mutableStateOf(GameObservationViewState(
            ObservationSnapshot(status = ObservationStatus.STOPPED, reason = "CAPTURE_REVOKED"),
        ))
        compose.setContent {
            SentinelTheme(AppThemeMode.DARK) {
                GameObservationPanel(StockGameInstall("fixture", 1), snapshot.value, true, false, false, 200,
                    {}, {}, {}, {})
            }
        }
        compose.onAllNodesWithTag("game-observer-error").assertCountEquals(1)
        compose.onNodeWithTag("game-observer-error").performScrollTo()
            .assertTextContains("Android ended screen sharing or its permission was revoked.", substring = true)
            .assert(SemanticsMatcher.expectValue(SemanticsProperties.LiveRegion, LiveRegionMode.Assertive))
        compose.onNodeWithTag("game-capture-stop").assertDoesNotExist()
        compose.onNodeWithTag("game-hud-evidence-status").assertDoesNotExist()
        compose.runOnIdle {
            snapshot.value = GameObservationViewState(
                ObservationSnapshot(status = ObservationStatus.STOPPED, reason = "USER_STOP"),
            )
        }
        compose.onNodeWithTag("game-observer-error").assertDoesNotExist()
    }

    @Test fun expiredCaptureAndInvalidSessionShowDistinctRecoveryNotices() {
        val snapshot = mutableStateOf(GameObservationViewState(
            ObservationSnapshot(status = ObservationStatus.STOPPED, reason = "TIME_LIMIT"),
        ))
        compose.setContent {
            SentinelTheme(AppThemeMode.LIGHT) {
                GameObservationPanel(StockGameInstall("fixture", 1), snapshot.value, true, false, false, 200,
                    {}, {}, {}, {})
            }
        }
        compose.onNodeWithTag("game-observer-notice").performScrollTo()
            .assertTextContains("The five-minute test ended.", substring = true)
            .assert(SemanticsMatcher.expectValue(SemanticsProperties.LiveRegion, LiveRegionMode.Polite))
        compose.runOnIdle {
            snapshot.value = GameObservationViewState(
                ObservationSnapshot(status = ObservationStatus.STOPPED, reason = "SESSION_CHECK_TIMEOUT"),
            )
        }
        compose.onNodeWithTag("game-observer-notice").assertDoesNotExist()
        compose.onNodeWithTag("game-observer-error").performScrollTo()
            .assertTextContains("account session or installed game could not be verified", substring = true)
    }

    @Test fun longHistoricalOcrWarningExposesFullAccessibleText() {
        val health = HealthCandidate(4, 20, 0)
        val paused = GameObservationViewState(ObservationSnapshot(
            status = ObservationStatus.PAUSED, captureId = "capture-a",
            frames = 1, lastHealth = HealthObservation(health, 110L),
        ))
        compose.setContent {
            SentinelTheme(AppThemeMode.DARK) {
                GameObservationPanel(StockGameInstall("fixture", 1), paused, true, false, false, 5111,
                    {}, {}, {}, {})
            }
        }
        compose.onNodeWithTag("game-hud-evidence-status").performScrollTo()
            .assertTextContains("Historical OCR only · NOT current health")
            .assert(SemanticsMatcher.expectValue(SemanticsProperties.LiveRegion, LiveRegionMode.Polite))
        compose.onNodeWithTag("game-capture-stop").assertIsDisplayed()
    }

    @Test fun journeyExplainsNextStepAndKeepsInputOff() {
        val observation = mutableStateOf(GameObservationViewState())
        compose.setContent {
            SentinelTheme(AppThemeMode.LIGHT) {
                GameObservationPanel(StockGameInstall("fixture", 1), observation.value, true, false, false, 100,
                    {}, {}, {}, {})
            }
        }
        compose.onNodeWithText("Review the disclosure and explicitly agree to this diagnostic session before requesting Android capture.")
            .performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Game input: OFF. This screen only collects local diagnostic evidence; it cannot authorize recommendations or actions.")
            .performScrollTo().assertIsDisplayed()
        compose.runOnIdle {
            observation.value = GameObservationViewState(ObservationSnapshot(status = ObservationStatus.OBSERVING))
        }
        compose.onNodeWithText("Wait for a completed OCR frame. Missing or stale values remain UNKNOWN.")
            .performScrollTo().assertIsDisplayed()
    }
}
