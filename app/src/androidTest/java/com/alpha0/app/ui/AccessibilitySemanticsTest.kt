package com.alpha0.app.ui

import androidx.compose.material3.Text
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import org.junit.Rule
import org.junit.Test

class AccessibilitySemanticsTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun politeStatusExposesLiveRegion() {
        composeRule.setContent {
            Text("Ready", Modifier.testTag("status").politeStatusSemantics())
        }
        composeRule.onNodeWithTag("status").assert(
            SemanticsMatcher.expectValue(SemanticsProperties.LiveRegion, LiveRegionMode.Polite)
        )
    }

    @Test
    fun assertiveStatusExposesLiveRegion() {
        composeRule.setContent {
            Text("Load failed", Modifier.testTag("error").assertiveStatusSemantics())
        }
        composeRule.onNodeWithTag("error").assert(
            SemanticsMatcher.expectValue(SemanticsProperties.LiveRegion, LiveRegionMode.Assertive)
        )
    }

    @Test
    fun progressStatusProvidesDescriptionAndLiveRegion() {
        composeRule.setContent {
            Text("…", Modifier.testTag("progress").progressStatusSemantics("Loading SENTINEL status"))
        }
        composeRule.onNodeWithTag("progress")
            .assert(SemanticsMatcher.expectValue(SemanticsProperties.LiveRegion, LiveRegionMode.Polite))
            .assert(SemanticsMatcher.expectValue(SemanticsProperties.ContentDescription, listOf("Loading SENTINEL status")))
    }

    @Test
    fun interactiveCardExposesButtonRoleAndDescription() {
        composeRule.setContent {
            Text("Device", Modifier.testTag("card").buttonCardSemantics("Open device details"))
        }
        composeRule.onNodeWithTag("card")
            .assert(SemanticsMatcher.expectValue(SemanticsProperties.Role, Role.Button))
            .assert(SemanticsMatcher.expectValue(SemanticsProperties.ContentDescription, listOf("Open device details")))
    }
}
