from __future__ import annotations

from enum import StrEnum
from typing import Callable, Iterable

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
    Optional feature entitlements are resolved server-side from a trusted
    resolver; callers cannot self-assert paid grants in ActionRequest.
    The gateway has no execution method and therefore cannot directly mutate
    a game, process, entitlement, or external system.
    """

    def __init__(
        self,
        authorization: AuthorizationEngine,
        *,
        entitlement_resolver: Callable[[str], Iterable[str]] | None = None,
    ) -> None:
        self._authorization = authorization
        self._entitlement_resolver = entitlement_resolver

    def authorize(
        self,
        principal: Principal,
        request: ActionRequest,
        *,
        required_capabilities: Iterable[str] = (),
        required_entitlements: Iterable[str] = (),
    ) -> ActionDecisionResult:
        required = tuple(required_capabilities)
        required_features = frozenset(required_entitlements)
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

        if required_features:
            if self._entitlement_resolver is None:
                return ActionDecisionResult(
                    decision=ActionDecision.DENY,
                    reason_code="ENTITLEMENT_RESOLVER_UNAVAILABLE",
                )
            try:
                granted = frozenset(self._entitlement_resolver(principal.user_id))
            except Exception:
                return ActionDecisionResult(
                    decision=ActionDecision.DENY,
                    reason_code="ENTITLEMENT_RESOLUTION_FAILED",
                )
            if not required_features.issubset(granted):
                return ActionDecisionResult(
                    decision=ActionDecision.DENY,
                    reason_code="FEATURE_ENTITLEMENT_REQUIRED",
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
