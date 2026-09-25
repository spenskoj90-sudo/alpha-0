from __future__ import annotations

import asyncio
import time
from collections import deque
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from app import main as main_module
from app.core.federated_auth import FederatedAuthError, VerifiedFederatedIdentity
from app.core.security import Decision, Principal
from app.core.store import MemoryStore


def _request(*, headers: list[tuple[bytes, bytes]] | None = None, client=("127.0.0.1", 1234)) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "raw_path": b"/test",
            "query_string": b"",
            "headers": headers or [],
            "client": client,
            "server": ("testserver", 80),
            "scheme": "http",
            "http_version": "1.1",
        }
    )


def test_security_headers_sets_all_server_owned_browser_guards() -> None:
    async def call_next(_request):
        return Response("ok")

    response = asyncio.run(main_module.security_headers(_request(), call_next))
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_rate_limiter_limits_active_bucket_and_reuses_expired_bucket(monkeypatch) -> None:
    ticks = iter([100.0, 100.1, 100.2, 200.0])
    monkeypatch.setattr(main_module.time, "monotonic", lambda: next(ticks))
    limiter = main_module.RateLimiter(limit=2, window=10, max_buckets=2)

    assert limiter.allow("a") is True
    assert limiter.allow("a") is True
    assert limiter.allow("a") is False
    # Expired queue is removed and recreated instead of permanently blocking.
    assert limiter.allow("a") is True


def test_rate_limiter_preserves_active_buckets_at_capacity_and_prunes_inactive(monkeypatch) -> None:
    limiter = main_module.RateLimiter(limit=10, window=10, max_buckets=2)
    limiter._hits = {
        "active-1": deque([95.0]),
        "active-2": deque([96.0]),
    }
    monkeypatch.setattr(main_module.time, "monotonic", lambda: 100.0)
    assert limiter.allow("new") is False
    assert set(limiter._hits) == {"active-1", "active-2"}

    limiter._hits["active-1"] = deque([80.0])
    assert limiter.allow("new") is True
    assert "active-1" not in limiter._hits
    assert "new" in limiter._hits


def test_rate_limiter_constructor_clamps_bucket_capacity(monkeypatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_MAX_BUCKETS", "0")
    assert main_module.RateLimiter().max_buckets == 1
    assert main_module.RateLimiter(max_buckets=0).max_buckets == 1


def test_request_id_prefers_valid_supplied_then_header_and_regenerates_overlong() -> None:
    request = _request(headers=[(b"x-request-id", b"header-id")])
    assert main_module.request_id(request, "supplied-id") == "supplied-id"
    assert main_module.request_id(request) == "header-id"
    generated = main_module.request_id(request, "x" * 129)
    assert generated != "x" * 129
    assert len(generated) == 36


def test_rate_limit_uses_unknown_client_and_maps_denial(monkeypatch) -> None:
    keys = []

    class Limiter:
        def allow(self, key):
            keys.append(key)
            return False

    monkeypatch.setattr(main_module, "rate_limiter", Limiter())
    with pytest.raises(HTTPException) as exc:
        main_module.rate_limit(_request(client=None), "auth")
    assert exc.value.status_code == 429
    assert exc.value.detail == "RATE_LIMITED"
    assert keys == ["auth:unknown"]


@pytest.mark.parametrize(
    ("required", "configured", "provided", "user", "status", "detail"),
    [
        (False, "", None, "u1", None, None),
        (True, "", None, "u1", 503, "DEVICE_ENROLLMENT_NOT_CONFIGURED"),
        (True, "malformed", "u1:secret", "u1", 503, "DEVICE_ENROLLMENT_NOT_CONFIGURED"),
        (True, "owner:secret", None, "owner", 503, "DEVICE_ENROLLMENT_NOT_CONFIGURED"),
        (True, "owner:secret", "other:secret", "owner", 403, "INVALID_ENROLLMENT_TOKEN"),
        (True, "owner:secret", "owner:wrong", "owner", 403, "INVALID_ENROLLMENT_TOKEN"),
        (True, "owner:secret", "owner:secret", "owner", None, None),
    ],
)
def test_enrollment_boundary_is_fail_closed(monkeypatch, required, configured, provided, user, status, detail) -> None:
    monkeypatch.setattr(main_module, "REQUIRE_ENROLLMENT", required)
    monkeypatch.setattr(main_module, "ENROLLMENT_TOKEN", configured)
    if status is None:
        main_module.require_enrollment(provided, user)
    else:
        with pytest.raises(HTTPException) as exc:
            main_module.require_enrollment(provided, user)
        assert exc.value.status_code == status
        assert exc.value.detail == detail


def test_principal_from_token_rejects_invalid_session_and_touches_bound_device(monkeypatch) -> None:
    touched = []

    class Store:
        def __init__(self, record):
            self.record = record

        def get_session(self, _token):
            return self.record

        def touch_device(self, device_id):
            touched.append(device_id)
            return True

    monkeypatch.setattr(main_module, "store", Store(None))
    with pytest.raises(HTTPException, match="INVALID_SESSION"):
        main_module.principal_from_token("bad")

    monkeypatch.setattr(
        main_module,
        "store",
        Store({"user_id": "u1", "device_id": "d1", "roles": ["user"], "scopes": ["game:read"]}),
    )
    principal = main_module.principal_from_token("ok")
    assert principal == Principal("u1", "d1", frozenset({"user"}), frozenset({"game:read"}))
    assert touched == ["d1"]

    monkeypatch.setattr(
        main_module,
        "store",
        Store({"user_id": "u2", "device_id": None, "roles": [], "scopes": []}),
    )
    principal = main_module.principal_from_token("ok")
    assert principal.device_id is None
    assert touched == ["d1"]


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("Basic abc", None),
        ("Bearer ", None),
        ("Bearer " + "x" * 4097, None),
        ("Bearer token-value ", "token-value"),
    ],
)
def test_bearer_parser_is_strict_and_bounded(header: str, expected: str | None) -> None:
    if expected is None:
        with pytest.raises(HTTPException) as exc:
            main_module.require_bearer(header)
        assert exc.value.status_code == 401
        assert exc.value.detail == "INVALID_AUTHORIZATION"
    else:
        assert main_module.require_bearer(header) == expected


def test_authorize_request_audits_allow_and_deny(monkeypatch) -> None:
    audits = []

    class Store:
        def add_audit(self, item):
            audits.append(item)

    class Engine:
        def __init__(self, decision):
            self.decision = decision

        def authorize(self, _principal, _action, _resource):
            return self.decision, "ALLOW_TEST" if self.decision is Decision.ALLOW else "DENY_TEST"

    principal = Principal("u1", "d1", frozenset({"user"}), frozenset({"game:read"}))
    monkeypatch.setattr(main_module, "store", Store())
    monkeypatch.setattr(main_module, "policy_engine", Engine(Decision.ALLOW))
    main_module.authorize_request(principal, "game:read", "game:wow", "rid")
    assert audits[-1]["decision"] == "ALLOW"

    monkeypatch.setattr(main_module, "policy_engine", Engine(Decision.DENY))
    with pytest.raises(HTTPException) as exc:
        main_module.authorize_request(principal, "game:write", "game:wow", "rid")
    assert exc.value.status_code == 403
    assert exc.value.detail == "DENY_TEST"
    assert audits[-1]["decision"] == "DENY"


def test_bind_session_to_device_memory_store_validates_session_liveness(monkeypatch) -> None:
    store = MemoryStore()
    monkeypatch.setattr(main_module, "store", store)

    with pytest.raises(HTTPException, match="INVALID_SESSION"):
        main_module.bind_session_to_device("missing", "device")

    access, _, _, _ = store.issue_session(None, "u1", 60, 120)
    store.sessions[main_module.session_hash(access)]["revoked"] = True
    with pytest.raises(HTTPException, match="INVALID_SESSION"):
        main_module.bind_session_to_device(access, "device")

    access, _, _, _ = store.issue_session(None, "u1", 60, 120)
    main_module.bind_session_to_device(access, "device")
    assert store.sessions[main_module.session_hash(access)]["device_id"] == "device"


def test_bind_session_to_device_persistent_store_checks_rowcount(monkeypatch) -> None:
    class Result:
        def __init__(self, rowcount):
            self.rowcount = rowcount

    class Conn:
        def __init__(self, rowcount):
            self.rowcount = rowcount

        def execute(self, *_args, **_kwargs):
            return Result(self.rowcount)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class Engine:
        def __init__(self, rowcount):
            self.rowcount = rowcount

        def begin(self):
            return Conn(self.rowcount)

    class Store:
        def __init__(self, rowcount):
            self.engine = Engine(rowcount)

    monkeypatch.setattr(main_module, "store", Store(0))
    with pytest.raises(HTTPException, match="INVALID_SESSION"):
        main_module.bind_session_to_device("token", "device")

    monkeypatch.setattr(main_module, "store", Store(1))
    main_module.bind_session_to_device("token", "device")


def test_device_ownership_accepts_bound_device_or_same_user_only() -> None:
    principal = Principal("u1", "d1", frozenset(), frozenset())
    assert main_module.device_owned_by(principal, {"user_id": "u2"}, "d1") is True
    assert main_module.device_owned_by(principal, {"user_id": "u1"}, "d2") is True
    assert main_module.device_owned_by(principal, {"user_id": "u2"}, "d2") is False


@pytest.mark.parametrize(
    ("code", "status"),
    [
        ("AUTH_PROVIDER_NOT_CONFIGURED", 503),
        ("FEDERATED_PROVIDER_UNAVAILABLE", 503),
        ("AUTH_PROVIDER_UNSUPPORTED", 404),
        ("FEDERATED_TOKEN_INVALID", 400),
    ],
)
def test_federated_error_maps_provider_state_to_constant_http_status(code: str, status: int) -> None:
    mapped = main_module._federated_error(FederatedAuthError(code))
    assert mapped.status_code == status
    assert mapped.detail == code


def test_revoke_user_sessions_memory_store_is_user_scoped(monkeypatch) -> None:
    store = MemoryStore()
    a, _, _, _ = store.issue_session(None, "u1", 60, 120)
    b, _, _, _ = store.issue_session(None, "u2", 60, 120)
    monkeypatch.setattr(main_module, "store", store)
    main_module.revoke_user_sessions("u1")
    assert store.sessions[main_module.session_hash(a)]["revoked"] is True
    assert store.sessions[main_module.session_hash(b)]["revoked"] is False


def test_session_or_mfa_uses_second_factor_gate_before_session_issuance(monkeypatch) -> None:
    audits = []
    challenge_exp = datetime.now(UTC)

    class Mfa:
        def issue_login_challenge(self, user_id):
            assert user_id == "u1"
            return "challenge", challenge_exp

    class Store:
        def add_audit(self, item):
            audits.append(item)

    monkeypatch.setattr(main_module, "account_mfa", Mfa())
    monkeypatch.setattr(main_module, "store", Store())
    result = main_module._session_or_mfa(
        "u1",
        _request(),
        action="auth:login",
        first_factor_reason="PASSWORD_VALID",
    )
    assert result.mfa_required is True
    assert result.challenge_token == "challenge"
    assert audits[-1]["reason_code"] == "FIRST_FACTOR_VALID_MFA_REQUIRED"


def test_federated_session_reuses_binding_registers_new_and_maps_collision(monkeypatch) -> None:
    identity = VerifiedFederatedIdentity("google", "subject", "person@gmail.com", True)
    calls = []

    class Users:
        def __init__(self, existing=None, error=None):
            self.existing = existing
            self.error = error

        def external_identity_user(self, _provider, _subject):
            return self.existing

        def register_external_account(self, *args, **kwargs):
            calls.append((args, kwargs))
            if self.error:
                raise ValueError(self.error)
            return "created-user"

    monkeypatch.setattr(main_module, "_session_or_mfa", lambda user_id, *_a, **_k: user_id)

    monkeypatch.setattr(main_module, "user_store", Users(existing="existing-user"))
    assert main_module._federated_session(identity, _request()) == "existing-user"
    assert calls == []

    monkeypatch.setattr(main_module, "user_store", Users())
    assert main_module._federated_session(identity, _request()) == "created-user"
    assert calls

    monkeypatch.setattr(main_module, "user_store", Users(error="ACCOUNT_LINK_REQUIRED"))
    with pytest.raises(HTTPException) as exc:
        main_module._federated_session(identity, _request())
    assert exc.value.status_code == 409
    assert exc.value.detail == "ACCOUNT_LINK_REQUIRED"

    monkeypatch.setattr(main_module, "user_store", Users(error="OTHER"))
    with pytest.raises(ValueError, match="OTHER"):
        main_module._federated_session(identity, _request())


def test_provider_link_principal_requires_device_bound_session(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "require_bearer", lambda _h: "token")
    monkeypatch.setattr(
        main_module,
        "principal_from_token",
        lambda _t: Principal("u1", None, frozenset(), frozenset()),
    )
    with pytest.raises(HTTPException) as exc:
        main_module._require_provider_link_principal("Bearer token")
    assert exc.value.status_code == 403
    assert exc.value.detail == "DEVICE_BOUND_SESSION_REQUIRED"

    expected = Principal("u1", "d1", frozenset(), frozenset())
    monkeypatch.setattr(main_module, "principal_from_token", lambda _t: expected)
    assert main_module._require_provider_link_principal("Bearer token") == expected


def test_link_federated_identity_enforces_subject_ownership_and_provider_uniqueness(monkeypatch) -> None:
    principal = Principal("u1", "d1", frozenset(), frozenset())
    identity = VerifiedFederatedIdentity("google", "subject", "person@gmail.com", True)
    audits = []

    class Store:
        def add_audit(self, item):
            audits.append(item)

    class Users:
        def __init__(self, existing=None, error=None):
            self.existing = existing
            self.error = error
            self.linked = 0

        def external_identity_user(self, *_args):
            return self.existing

        def link_external_identity(self, *_args):
            self.linked += 1
            if self.error:
                raise ValueError(self.error)

    monkeypatch.setattr(main_module, "store", Store())

    monkeypatch.setattr(main_module, "user_store", Users(existing="other"))
    with pytest.raises(HTTPException) as exc:
        main_module._link_federated_identity(principal, identity, _request())
    assert exc.value.status_code == 409
    assert exc.value.detail == "EXTERNAL_IDENTITY_ALREADY_LINKED"

    same = Users(existing="u1")
    monkeypatch.setattr(main_module, "user_store", same)
    assert main_module._link_federated_identity(principal, identity, _request()).status == "LINKED"
    assert same.linked == 0

    fresh = Users()
    monkeypatch.setattr(main_module, "user_store", fresh)
    assert main_module._link_federated_identity(principal, identity, _request()).status == "LINKED"
    assert fresh.linked == 1
    assert audits[-1]["reason_code"] == "FEDERATED_IDENTITY_VALID"

    for code in ("PROVIDER_ALREADY_LINKED", "EXTERNAL_IDENTITY_ALREADY_LINKED"):
        conflict = Users(error=code)
        monkeypatch.setattr(main_module, "user_store", conflict)
        with pytest.raises(HTTPException) as exc:
            main_module._link_federated_identity(principal, identity, _request())
        assert exc.value.status_code == 409
        assert exc.value.detail == code

    monkeypatch.setattr(main_module, "user_store", Users(error="OTHER"))
    with pytest.raises(ValueError, match="OTHER"):
        main_module._link_federated_identity(principal, identity, _request())
