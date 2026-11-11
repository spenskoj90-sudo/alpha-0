package com.alpha0.app.game

/** User-selectable game-assistance authority. OFF is always the initial state. */
internal enum class GameAutomationMode(
    val labelKey: String,
    val descriptionKey: String,
) {
    OFF("game_automation_mode_off", "game_automation_desc_off"),
    OBSERVE_ADVISORY("game_automation_mode_advisory", "game_automation_desc_advisory"),
    USER_CONFIRMED("game_automation_mode_confirmed", "game_automation_desc_confirmed"),
    BOUNDED_ACTIVE("game_automation_mode_bounded", "game_automation_desc_bounded"),
}

internal enum class GameAutomationGateReason(val stringKey: String) {
    USER_DISABLED("game_automation_gate_user_disabled"),
    STOP_LATCHED("game_automation_gate_stop_latched"),
    RISK_NOT_ACKNOWLEDGED("game_automation_gate_risk_not_acknowledged"),
    OPERATOR_RULES_UNREVIEWED("game_automation_gate_operator_rules_unreviewed"),
    TARGET_UNVERIFIED("game_automation_gate_target_unverified"),
    SOURCE_UNVERIFIED("game_automation_gate_source_unverified"),
    OBSERVATION_STALE("game_automation_gate_observation_stale"),
    CALIBRATION_UNVERIFIED("game_automation_gate_calibration_unverified"),
    KNOWLEDGE_UNREVIEWED("game_automation_gate_knowledge_unreviewed"),
    OPERATOR_RESTRICTS_AUTOMATION("game_automation_gate_operator_restricts"),
    EXECUTOR_UNAVAILABLE("game_automation_gate_executor_unavailable"),
    ACTION_BINDING_UNVERIFIED("game_automation_gate_action_binding_unverified"),
    ACTION_CONSENT_REQUIRED("game_automation_gate_action_consent_required"),
    ARM_REQUIRED("game_automation_gate_arm_required"),
    LEASE_INVALID("game_automation_gate_lease_invalid"),
    ALLOWLIST_UNVERIFIED("game_automation_gate_allowlist_unverified"),
    BUDGET_INVALID("game_automation_gate_budget_invalid"),
}

internal data class GameAutomationEvidence(
    val riskAcknowledged: Boolean = false,
    val operatorRulesReviewed: Boolean = false,
    val operatorAllowsAutomation: Boolean = false,
    val targetVerified: Boolean = false,
    val sourceVerified: Boolean = false,
    val observationFresh: Boolean = false,
    val calibrationApproved: Boolean = false,
    val knowledgeReviewed: Boolean = false,
    val executorAvailable: Boolean = false,
    val actionBindingVerified: Boolean = false,
    val actionConsent: Boolean = false,
    val armActive: Boolean = false,
    val leaseValid: Boolean = false,
    val allowlistApproved: Boolean = false,
    val budgetsValid: Boolean = false,
    val stopLatched: Boolean = false,
)

internal data class GameAutomationModeDecision(
    val requestedMode: GameAutomationMode,
    val effectiveMode: GameAutomationMode,
    val reasons: List<GameAutomationGateReason>,
    val maySendInput: Boolean,
) {
    val canEnable: Boolean
        get() = requestedMode != GameAutomationMode.OFF &&
            effectiveMode == requestedMode && reasons.isEmpty()
}

/**
 * Pure fail-closed policy. The caller supplies evidence from trusted sources;
 * UI acknowledgements alone never establish target/source/operator permission.
 */
internal object GameAutomationModePolicy {
    fun evaluate(
        requestedMode: GameAutomationMode,
        enabled: Boolean,
        evidence: GameAutomationEvidence,
    ): GameAutomationModeDecision {
        if (requestedMode == GameAutomationMode.OFF) {
            return GameAutomationModeDecision(
                requestedMode, GameAutomationMode.OFF, emptyList(), maySendInput = false,
            )
        }
        if (!enabled) {
            return GameAutomationModeDecision(
                requestedMode, GameAutomationMode.OFF,
                listOf(GameAutomationGateReason.USER_DISABLED), maySendInput = false,
            )
        }
        if (evidence.stopLatched) {
            return GameAutomationModeDecision(
                requestedMode, GameAutomationMode.OFF,
                listOf(GameAutomationGateReason.STOP_LATCHED), maySendInput = false,
            )
        }

        val reasons = buildList {
            if (!evidence.riskAcknowledged) add(GameAutomationGateReason.RISK_NOT_ACKNOWLEDGED)
            if (!evidence.operatorRulesReviewed) add(GameAutomationGateReason.OPERATOR_RULES_UNREVIEWED)
            if (!evidence.targetVerified) add(GameAutomationGateReason.TARGET_UNVERIFIED)
            if (!evidence.sourceVerified) add(GameAutomationGateReason.SOURCE_UNVERIFIED)
            if (!evidence.observationFresh) add(GameAutomationGateReason.OBSERVATION_STALE)
            if (!evidence.calibrationApproved) add(GameAutomationGateReason.CALIBRATION_UNVERIFIED)
            if (!evidence.knowledgeReviewed) add(GameAutomationGateReason.KNOWLEDGE_UNREVIEWED)

            if (requestedMode == GameAutomationMode.USER_CONFIRMED ||
                requestedMode == GameAutomationMode.BOUNDED_ACTIVE
            ) {
                if (!evidence.operatorAllowsAutomation) add(GameAutomationGateReason.OPERATOR_RESTRICTS_AUTOMATION)
                if (!evidence.executorAvailable) add(GameAutomationGateReason.EXECUTOR_UNAVAILABLE)
                if (!evidence.actionBindingVerified) add(GameAutomationGateReason.ACTION_BINDING_UNVERIFIED)
                if (!evidence.actionConsent) add(GameAutomationGateReason.ACTION_CONSENT_REQUIRED)
            }
            if (requestedMode == GameAutomationMode.BOUNDED_ACTIVE) {
                if (!evidence.armActive) add(GameAutomationGateReason.ARM_REQUIRED)
                if (!evidence.leaseValid) add(GameAutomationGateReason.LEASE_INVALID)
                if (!evidence.allowlistApproved) add(GameAutomationGateReason.ALLOWLIST_UNVERIFIED)
                if (!evidence.budgetsValid) add(GameAutomationGateReason.BUDGET_INVALID)
            }
        }.distinct()

        val effective = if (reasons.isEmpty()) requestedMode else GameAutomationMode.OFF
        val maySendInput = reasons.isEmpty() &&
            requestedMode in setOf(GameAutomationMode.USER_CONFIRMED, GameAutomationMode.BOUNDED_ACTIVE)
        return GameAutomationModeDecision(requestedMode, effective, reasons, maySendInput)
    }
}
