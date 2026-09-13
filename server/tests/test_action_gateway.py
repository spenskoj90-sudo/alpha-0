from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.action_gateway import ActionDecision, ActionGateway, ActionMode, ActionRequest
from app.core.game_adapter import CapabilityStatus
from app.core.security import AuthorizationEngine, Decision, Policy, Principal


@pytest.fixture
def principal() -> Principal:
    return Principal(
        user_id="user-1",
        device_id="device-1",
        roles=frozenset(),
        scopes=frozenset({"game:write"}),
    )


def authorization_engine() -> AuthorizationEngine:
    return AuthorizationEngine(
        [
            Policy(
                Decision.ALLOW,
                "game:interact",
                "game:target",
                scopes=frozenset({"game:write"}),
            )
        ]
    )


@pytest.fixture
def gateway() -> ActionGateway:
    return ActionGateway(authorization_engine())


def action_request(mode: ActionMode = ActionMode.USER_CONFIRMED) -> ActionRequest:
    return ActionRequest(
        action="game:interact",
        resource="game:target",
        mode=mode,
        capability="command_bridge",
        capability_status=CapabilityStatus.LIMITED,
    )


def test_policy_allow_never_executes_and_recommendation_requires_confirmation(
    gateway: ActionGateway, principal: Principal
) -> None:
    result = gateway.authorize(
        principal,
        action_request(ActionMode.RECOMMENDATION),
        required_capabilities=("command_bridge",),
    )

    assert result.decision is ActionDecision.CONFIRM
    assert result.reason_code == "USER_CONFIRMATION_REQUIRED"


def test_user_confirmed_action_requires_policy_and_usable_capability(
    gateway: ActionGateway, principal: Principal
) -> None:
    result = gateway.authorize(
        principal,
        action_request(),
        required_capabilities=("command_bridge",),
    )

    assert result.decision is ActionDecision.ALLOW
    assert result.reason_code == "POLICY_ALLOW_USER_CONFIRMED"


def test_automatic_execution_is_denied_even_when_policy_and_capability_allow(
    gateway: ActionGateway, principal: Principal
) -> None:
    result = gateway.authorize(
        principal,
        ActionRequest(
            action="game:interact",
            resource="game:target",
            mode=ActionMode.AUTOMATIC,
            capability="command_bridge",
            capability_status=CapabilityStatus.AVAILABLE,
            evidence_level="L3",
        ),
        required_capabilities=("command_bridge",),
    )

    assert result.decision is ActionDecision.DENY
    assert result.reason_code == "AUTOMATIC_EXECUTION_DISABLED"


def test_unverified_capability_cannot_authorize_action(
    gateway: ActionGateway, principal: Principal
) -> None:
    result = gateway.authorize(
        principal,
        ActionRequest(
            action="game:interact",
            resource="game:target",
            mode=ActionMode.USER_CONFIRMED,
            capability="command_bridge",
            capability_status=CapabilityStatus.UNVERIFIED,
        ),
        required_capabilities=("command_bridge",),
    )

    assert result.decision is ActionDecision.DENY
    assert result.reason_code == "CAPABILITY_NOT_VERIFIED"


def test_missing_required_capability_is_denied(
    gateway: ActionGateway, principal: Principal
) -> None:
    result = gateway.authorize(
        principal,
        ActionRequest(
            action="game:interact",
            resource="game:target",
            mode=ActionMode.USER_CONFIRMED,
            capability="overlay",
            capability_status=CapabilityStatus.LIMITED,
        ),
        required_capabilities=("command_bridge",),
    )

    assert result.decision is ActionDecision.DENY
    assert result.reason_code == "REQUIRED_CAPABILITY_MISSING"


def test_policy_deny_wins_over_capability(principal: Principal) -> None:
    gateway = ActionGateway(
        AuthorizationEngine(
            [
                Policy(
                    Decision.DENY,
                    "game:interact",
                    "game:target",
                    scopes=frozenset({"game:write"}),
                ),
                Policy(
                    Decision.ALLOW,
                    "game:interact",
                    "game:target",
                    scopes=frozenset({"game:write"}),
                ),
            ]
        )
    )

    result = gateway.authorize(
        principal,
        ActionRequest(
            action="game:interact",
            resource="game:target",
            mode=ActionMode.USER_CONFIRMED,
            capability="command_bridge",
            capability_status=CapabilityStatus.AVAILABLE,
            evidence_level="L3",
        ),
        required_capabilities=("command_bridge",),
    )

    assert result.decision is ActionDecision.DENY
    assert result.reason_code == "POLICY_DENY"


def test_paid_feature_fails_closed_without_server_resolver(principal: Principal) -> None:
    gateway = ActionGateway(authorization_engine())
    result = gateway.authorize(
        principal,
        action_request(),
        required_capabilities=("command_bridge",),
        required_entitlements=("companion",),
    )

    assert result.decision is ActionDecision.DENY
    assert result.reason_code == "ENTITLEMENT_RESOLVER_UNAVAILABLE"


def test_paid_feature_cannot_be_granted_when_server_resolver_denies(principal: Principal) -> None:
    gateway = ActionGateway(authorization_engine(), entitlement_resolver=lambda _user_id: ())
    result = gateway.authorize(
        principal,
        action_request(),
        required_capabilities=("command_bridge",),
        required_entitlements=("companion",),
    )

    assert result.decision is ActionDecision.DENY
    assert result.reason_code == "FEATURE_ENTITLEMENT_REQUIRED"


def test_paid_feature_allows_only_after_server_resolver_grants(principal: Principal) -> None:
    gateway = ActionGateway(
        authorization_engine(),
        entitlement_resolver=lambda user_id: ("companion",) if user_id == "user-1" else (),
    )
    result = gateway.authorize(
        principal,
        action_request(),
        required_capabilities=("command_bridge",),
        required_entitlements=("companion",),
    )

    assert result.decision is ActionDecision.ALLOW
    assert result.reason_code == "POLICY_ALLOW_USER_CONFIRMED"


def test_entitlement_resolver_failure_denies_action(principal: Principal) -> None:
    def broken_resolver(_user_id: str):
        raise RuntimeError("provider unavailable")

    gateway = ActionGateway(authorization_engine(), entitlement_resolver=broken_resolver)
    result = gateway.authorize(
        principal,
        action_request(),
        required_entitlements=("companion",),
    )

    assert result.decision is ActionDecision.DENY
    assert result.reason_code == "ENTITLEMENT_RESOLUTION_FAILED"


def test_invalid_action_input_is_bounded() -> None:
    with pytest.raises(ValidationError):
        ActionRequest(action="game interact", resource="game:target")
