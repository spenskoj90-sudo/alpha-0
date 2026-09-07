from __future__ import annotations

from enum import StrEnum
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field

from app.core.game_adapter import CapabilityStatus
from app.core.security import AuthorizationEngine, Decision, Principal


class ActionDecision(StrEnum):
    ALLOW = "ALLOW"
    CONFIRM = "CONFIRM"
    DENY = "DENY"


class ActionMode(StrEnum):
    RECOMMENDATION = "RECOMMENDATION"
    USER_CONFIRMED = "USER_CONFIRMED"
    AUTOMATIC = "AUTOMATIC"


class ActionRequest(BaseModel):
    """Validated intent for an action-capable integration.

    This object represents an authorization request only. It is never an
    instruction to execute an external/game action.
    """

    model_config = ConfigDict(extra="forbid")

    action: str = Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9._:-]+$")
    resource: str = Field(min_length=1, max_length=500, pattern=r"^[A-Za-z0-9._:/*-]+$")
    mode: ActionMode = ActionMode.RECOMMENDATION
    capability: str | None = Field(default=None, min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    capability_status: CapabilityStatus | None = None
    evidence_level: str | None = Field(default=None, max_length=8, pattern=r"^L[1-3]$")


class ActionDecisionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: ActionDecision
    reason_code: str


class ActionGateway:
    """Fail-closed boundary between authorization and any future executor.

    Capability is a prerequisite signal, never an authorization source.
    The gateway has no execution method and therefore cannot directly mutate
    a game, process, entitlement, or external system.
    """

    def __init__(self, authorization: AuthorizationEngine) -> None:
        self._authorization = authorization

    def authorize(
        self,
        principal: Principal,
        request: ActionRequest,
        *,
        required_capabilities: Iterable[str] = (),
    ) -> ActionDecisionResult:
        required = tuple(required_capabilities)
        if request.mode is ActionMode.AUTOMATIC:
            return ActionDecisionResult(
                decision=ActionDecision.DENY,
                reason_code="AUTOMATIC_EXECUTION_DISABLED",
            )

        if request.capability_status in {
            CapabilityStatus.UNAVAILABLE,
            CapabilityStatus.UNVERIFIED,
        }:
            return ActionDecisionResult(
                decision=ActionDecision.DENY,
                reason_code="CAPABILITY_NOT_VERIFIED",
            )

        if required and request.capability not in required:
            return ActionDecisionResult(
                decision=ActionDecision.DENY,
                reason_code="REQUIRED_CAPABILITY_MISSING",
            )

        decision, reason = self._authorization.authorize(
            principal,
            request.action,
            request.resource,
        )
        if decision is Decision.DENY:
            return ActionDecisionResult(
                decision=ActionDecision.DENY,
                reason_code=reason,
            )

        if request.mode is ActionMode.USER_CONFIRMED:
            return ActionDecisionResult(
                decision=ActionDecision.ALLOW,
                reason_code="POLICY_ALLOW_USER_CONFIRMED",
            )

        return ActionDecisionResult(
            decision=ActionDecision.CONFIRM,
            reason_code="USER_CONFIRMATION_REQUIRED",
        )
