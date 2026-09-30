package com.alpha0.app.ui

import android.content.Context
import android.content.pm.ActivityInfo
import android.content.res.Configuration
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsSelected
import androidx.compose.ui.test.junit4.v2.createEmptyComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.core.app.ActivityScenario
import androidx.test.core.app.ApplicationProvider
import com.alpha0.app.MainActivity
import com.alpha0.app.security.SecureSessionStore
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Rule
import org.junit.Test

/** Real application entrypoint on the disposable GitHub emulator; no live credentials or Core. */
class ActivityAcceptanceInstrumentedTest {
    @get:Rule
    val composeRule = createEmptyComposeRule()

    private val context: Context = ApplicationProvider.getApplicationContext()
    private var scenario: ActivityScenario<MainActivity>? = null

    @Before
    fun prepareSignedOutApplication() {
        SecureSessionStore().clear(context)
        context.getSharedPreferences("sentinel_ui_preferences", Context.MODE_PRIVATE).edit().clear().commit()
        AppPreferences(context).apply {
            setLanguage(AppLanguage.ENGLISH)
            setTheme(AppThemeMode.LIGHT)
        }
    }

    @After
    fun closeApplication() {
        scenario?.close()
        SecureSessionStore().clear(context)
        context.getSharedPreferences("sentinel_ui_preferences", Context.MODE_PRIVATE).edit().clear().commit()
    }

    @Test
    fun signedOutAuthSurvivesActivityRecreationAndBothOrientations() {
        scenario = ActivityScenario.launch(MainActivity::class.java)
        loginIsVisible()
        scenario!!.recreate()
        loginIsVisible()
        rotate(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE, Configuration.ORIENTATION_LANDSCAPE)
        loginIsVisible()
        rotate(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT, Configuration.ORIENTATION_PORTRAIT)
        loginIsVisible()
        scenario!!.recreate()
        loginIsVisible()
        assertNull(SecureSessionStore().load(context))
    }

    @Test
    fun labeledSettingsActionsPersistRuEnAndLightDarkAcrossRecreationAndRotation() {
        scenario = ActivityScenario.launch(MainActivity::class.java)
        loginIsVisible()
        composeRule.onNodeWithContentDescription("Menu").performClick()
        composeRule.onNodeWithText("Settings", useUnmergedTree = false).performClick()
        choice("English").assertIsSelected()
        choice("Русский").performClick()
        choice("Тёмная тема").performClick().assertIsSelected()
        assertPreferences(AppLanguage.RUSSIAN, AppThemeMode.DARK)

        scenario!!.recreate()
        choice("Русский").assertIsSelected()
        choice("Тёмная тема").assertIsSelected()
        rotate(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE, Configuration.ORIENTATION_LANDSCAPE)
        choice("Русский").assertIsSelected()
        choice("Тёмная тема").assertIsSelected()
        rotate(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT, Configuration.ORIENTATION_PORTRAIT)

        choice("English").performClick()
        choice("Light").performClick().assertIsSelected()
        assertPreferences(AppLanguage.ENGLISH, AppThemeMode.LIGHT)
        scenario!!.recreate()
        choice("English").assertIsSelected()
        choice("Light").assertIsSelected()
        composeRule.onNodeWithContentDescription("Back").performClick()
        loginIsVisible()
    }

    private fun loginIsVisible() {
        composeRule.onNodeWithText("Sign in to your account").performScrollTo().assertIsDisplayed()
        composeRule.onNodeWithText("Sign in", substring = false).performScrollTo().assertIsDisplayed()
    }

    private fun choice(label: String) = composeRule.onNodeWithText(label)
        .performScrollTo()
        .assert(SemanticsMatcher.expectValue(SemanticsProperties.Role, Role.RadioButton))

    private fun assertPreferences(language: AppLanguage, theme: AppThemeMode) {
        assertEquals(language, AppPreferences(context).language())
        assertEquals(theme, AppPreferences(context).theme())
    }

    private fun rotate(requested: Int, expected: Int) {
        scenario!!.onActivity { it.requestedOrientation = requested }
        composeRule.waitUntil(timeoutMillis = 15_000) {
            var observed = false
            scenario!!.onActivity { observed = it.resources.configuration.orientation == expected }
            observed
        }
        composeRule.waitForIdle()
    }
}
