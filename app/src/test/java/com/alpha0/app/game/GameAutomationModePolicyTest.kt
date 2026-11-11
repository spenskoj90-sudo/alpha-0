package com.alpha0.app.game

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class GameAutomationModePolicyTest {
    private fun verifiedReadOnlyEvidence() = GameAutomationEvidence(
        riskAcknowledged = true,
        operatorRulesReviewed = true,
        targetVerified = true,
        sourceVerified = true,
        observationFresh = true,
        calibrationApproved = true,
        knowledgeReviewed = true,
    )

    @Test fun defaultAndExplicitOffNeverSendInput() {
        val decision = GameAutomationModePolicy.evaluate(
            GameAutomationMode.OFF, enabled = true, GameAutomationEvidence(),
        )
        assertEquals(GameAutomationMode.OFF, decision.effectiveMode)
        assertFalse(decision.maySendInput)
        assertFalse(decision.canEnable)
    }

    @Test fun advisoryRequiresFreshVerifiedReviewedEvidenceButNeverSendsInput() {
        val decision = GameAutomationModePolicy.evaluate(
            GameAutomationMode.OBSERVE_ADVISORY, enabled = true, verifiedReadOnlyEvidence(),
        )
        assertEquals(GameAutomationMode.OBSERVE_ADVISORY, decision.effectiveMode)
        assertTrue(decision.reasons.isEmpty())
        assertFalse(decision.maySendInput)
    }

    @Test fun advisoryFailsClosedWhenTargetOrSourceIsUnverified() {
        val evidence = verifiedReadOnlyEvidence().copy(targetVerified = false, sourceVerified = false)
        val decision = GameAutomationModePolicy.evaluate(
            GameAutomationMode.OBSERVE_ADVISORY, enabled = true, evidence,
        )
        assertEquals(GameAutomationMode.OFF, decision.effectiveMode)
        assertTrue(GameAutomationGateReason.TARGET_UNVERIFIED in decision.reasons)
        assertTrue(GameAutomationGateReason.SOURCE_UNVERIFIED in decision.reasons)
        assertFalse(decision.maySendInput)
    }

    @Test fun userConfirmedRequiresOperatorPermissionActionBindingAndPerActionConsent() {
        val evidence = verifiedReadOnlyEvidence().copy(
            operatorActionPermission = GameOperatorActionPermission.PERMITTED,
            executorAvailable = true,
            actionBindingVerified = true,
            actionConsent = true,
        )
        val decision = GameAutomationModePolicy.evaluate(
            GameAutomationMode.USER_CONFIRMED, enabled = true, evidence,
        )
        assertEquals(GameAutomationMode.USER_CONFIRMED, decision.effectiveMode)
        assertTrue(decision.canEnable)
        assertTrue(decision.maySendInput)
    }

    @Test fun userConfirmedRequiresExplicitRiskAndRulesAcknowledgement() {
        val evidence = verifiedReadOnlyEvidence().copy(
            riskAcknowledged = false,
            operatorRulesReviewed = false,
            operatorActionPermission = GameOperatorActionPermission.PERMITTED,
            executorAvailable = true,
            actionBindingVerified = true,
            actionConsent = true,
        )
        val decision = GameAutomationModePolicy.evaluate(
            GameAutomationMode.USER_CONFIRMED, enabled = true, evidence,
        )
        assertEquals(GameAutomationMode.OFF, decision.effectiveMode)
        assertTrue(GameAutomationGateReason.RISK_NOT_ACKNOWLEDGED in decision.reasons)
        assertTrue(GameAutomationGateReason.OPERATOR_RULES_UNREVIEWED in decision.reasons)
        assertFalse(decision.maySendInput)
    }

    @Test fun boundedRequiresFreshArmLeaseAllowlistAndBudgets() {
        val evidence = verifiedReadOnlyEvidence().copy(
            operatorActionPermission = GameOperatorActionPermission.PERMITTED,
            executorAvailable = true,
            actionBindingVerified = true,
            actionConsent = true,
            armActive = true,
            leaseValid = true,
            allowlistApproved = true,
            budgetsValid = true,
        )
        val decision = GameAutomationModePolicy.evaluate(
            GameAutomationMode.BOUNDED_ACTIVE, enabled = true, evidence,
        )
        assertEquals(GameAutomationMode.BOUNDED_ACTIVE, decision.effectiveMode)
        assertTrue(decision.canEnable)
        assertTrue(decision.maySendInput)
    }

    @Test fun acknowledgingGameRulesCannotOverrideOperatorProhibition() {
        val verified = verifiedReadOnlyEvidence().copy(
            executorAvailable = true,
            actionBindingVerified = true,
            actionConsent = true,
            armActive = true,
            leaseValid = true,
            allowlistApproved = true,
            budgetsValid = true,
        )
        for (mode in listOf(GameAutomationMode.USER_CONFIRMED, GameAutomationMode.BOUNDED_ACTIVE)) {
            for ((permission, reason) in listOf(
                GameOperatorActionPermission.UNKNOWN to
                    GameAutomationGateReason.OPERATOR_ACTION_PERMISSION_UNKNOWN,
                GameOperatorActionPermission.PROHIBITED to
                    GameAutomationGateReason.OPERATOR_ACTION_PROHIBITED,
            )) {
                val result = GameAutomationModePolicy.evaluate(
                    mode, enabled = true, verified.copy(operatorActionPermission = permission),
                )
                assertEquals(GameAutomationMode.OFF, result.effectiveMode)
                assertFalse(result.maySendInput)
                assertTrue(reason in result.reasons)
            }
        }
        // Read-only advisory can remain available with complete observation
        // evidence, but never gains an action executor or bypasses operator rules.
        val advisory = GameAutomationModePolicy.evaluate(
            GameAutomationMode.OBSERVE_ADVISORY, enabled = true, verified,
        )
        assertEquals(GameAutomationMode.OBSERVE_ADVISORY, advisory.effectiveMode)
        assertFalse(advisory.maySendInput)
    }

    @Test fun stopLatchOverridesEveryRequestedMode() {
        val evidence = verifiedReadOnlyEvidence().copy(
            operatorActionPermission = GameOperatorActionPermission.PERMITTED,
            executorAvailable = true,
            actionBindingVerified = true,
            actionConsent = true,
            armActive = true,
            leaseValid = true,
            allowlistApproved = true,
            budgetsValid = true,
            stopLatched = true,
        )
        val decision = GameAutomationModePolicy.evaluate(
            GameAutomationMode.BOUNDED_ACTIVE, enabled = true, evidence,
        )
        assertEquals(GameAutomationMode.OFF, decision.effectiveMode)
        assertEquals(listOf(GameAutomationGateReason.STOP_LATCHED), decision.reasons)
        assertFalse(decision.maySendInput)
    }
}
