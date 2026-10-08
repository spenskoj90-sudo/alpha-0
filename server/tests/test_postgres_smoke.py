import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import time
import uuid

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from sqlalchemy import text

pytestmark = pytest.mark.postgres


def _key_material():
    key = ec.generate_private_key(ec.SECP256R1())
    public = key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return key, base64.b64encode(public).decode(), hashlib.sha256(public).hexdigest()


def test_postgres_committed_reset_survives_tombstone_write_failure(monkeypatch):
    from sqlalchemy import event
    from app import main as main_module
    from app.core.email_provider import TestEmailTransport
    from app.main import app, store, user_store
    transport = TestEmailTransport()
    monkeypatch.setattr(main_module, 'email_transport', transport)
    client = TestClient(app)
    email = f'pg-reset-publication-{uuid.uuid4().hex}@example.com'
    old_password, new_password = 'PG-reset-before-password-123', 'PG-reset-after-password-456'
    registered = client.post('/v1/auth/register', json={'email': email, 'password': old_password}).json()
    assert client.post('/v1/auth/password-reset/request', json={'email': email}).status_code == 202
    code = transport.snapshot()[-1].text.split('Reset code: ', 1)[1].splitlines()[0]
    def fail_tombstone(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().startswith('INSERT INTO web_session_families('):
            raise RuntimeError('TOMBSTONE_WRITE_UNAVAILABLE')
    event.listen(store.engine, 'before_cursor_execute', fail_tombstone)
    try:
        response = client.post('/v1/auth/password-reset/confirm',
            headers={'X-Sentinel-Web-Session': 'pg-reset-family-' + uuid.uuid4().hex + 'x' * 24},
            json={'email': email, 'token': code, 'password': new_password})
    finally:
        event.remove(store.engine, 'before_cursor_execute', fail_tombstone)
    assert response.status_code == 200
    assert response.json() == {'status': 'PASSWORD_UPDATED'}
    assert response.headers['x-sentinel-web-reset-revocation'] == 'identity'
    assert 'x-sentinel-web-generation' not in response.headers
    assert store.get_session(registered['session_token']) is None
    assert store.rotate_refresh(registered['refresh_token'], 3600, 7200) is None
    assert user_store.authenticate(email, old_password) is None
    assert user_store.authenticate(email, new_password) == email
    assert client.post('/v1/auth/password-reset/confirm', json={'email': email, 'token': code, 'password': new_password}).status_code == 400


def test_postgres_auth_event_and_audit_flow():
    from app.main import REFRESH_TTL_SECONDS, SESSION_TTL_SECONDS, app, store
    from app.core.store import PostgresStore

    assert isinstance(store, PostgresStore)
    client = TestClient(app)
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json()["status"] == "UP"

    key, public64, fingerprint = _key_material()
    user_id = "pg-smoke"
    enrollment = "pg-smoke:secret"

    reg = client.post(
        "/v1/devices/register",
        headers={"X-Enrollment-Token": enrollment},
        json={
            "user_id": user_id,
            "platform": "android",
            "public_key_der_b64": public64,
            "fingerprint_sha256": fingerprint,
        },
    )
    assert reg.status_code == 200
    device = reg.json()
    device_id = device["device_id"]

    body = {
        "challenge": device["challenge"],
        "timestamp": int(time.time()),
        "request_id": "pg-smoke-1",
    }
    signed = json.dumps(
        {"challenge": body["challenge"], "timestamp": body["timestamp"], "request_id": body["request_id"]},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    body["signature_b64"] = base64.b64encode(key.sign(signed, ec.ECDSA(hashes.SHA256()))).decode()
    proof = client.post(f"/v1/devices/{device_id}/prove", json=body)
    assert proof.status_code == 200
    session = proof.json()

    event = {
        "events": [
            {
                "event_id": "pg-event-1",
                "device_id": device_id,
                "type": "character.snapshot",
                "schema_version": 1,
                "occurred_at": "2026-08-12T06:00:00Z",
                "sequence": 0,
                "payload": {"hp": 100},
            }
        ]
    }
    ingested = client.post(
        "/v1/events:batch",
        headers={"Authorization": "Bearer " + session["session_token"], "Idempotency-Key": "pg-smoke-batch"},
        json=event,
    )
    assert ingested.status_code == 200
    assert ingested.json()["accepted"] == 1

    refreshed = client.post("/v1/sessions/refresh", json={"refresh_token": session["refresh_token"]})
    assert refreshed.status_code == 200

    audit = client.get(
        "/v1/audit",
        headers={"Authorization": "Bearer " + refreshed.json()["session_token"]},
    )
    assert audit.status_code == 200
    assert audit.json()["events"]

    with store.engine.connect() as conn:
        device_state = conn.execute(
            text("SELECT state FROM device_bindings WHERE id = CAST(:id AS uuid)"),
            {"id": device_id},
        ).scalar_one()
        active_sessions = conn.execute(
            text(
                "SELECT COUNT(*) FROM sessions WHERE device_id = CAST(:id AS uuid) AND revoked_at IS NULL"
            ),
            {"id": device_id},
        ).scalar_one()
        prove_allow = conn.execute(
            text(
                "SELECT COUNT(*) FROM audit_events "
                "WHERE action = 'device:prove' AND decision = 'ALLOW' "
                "AND device_id = CAST(:id AS uuid)"
            ),
            {"id": device_id},
        ).scalar_one()
        event_count = conn.execute(
            text("SELECT COUNT(*) FROM game_events WHERE event_id = :eid"),
            {"eid": "pg-event-1"},
        ).scalar_one()
        migration_versions = {
            row[0]
            for row in conn.execute(text("SELECT version FROM schema_migrations")).fetchall()
        }

    assert device_state == "ACTIVE"
    assert active_sessions >= 1
    assert prove_allow >= 1
    assert event_count == 1
    assert {"001_initial", "002_p1_rls", "003_user_auth"}.issubset(migration_versions)

    # Recycle the SQLAlchemy connection pool and prove the application still reads durable state.
    store.engine.dispose()
    health_after_recycle = client.get("/healthz")
    assert health_after_recycle.status_code == 200
    audit_after_recycle = client.get(
        "/v1/audit",
        headers={"Authorization": "Bearer " + refreshed.json()["session_token"]},
    )
    assert audit_after_recycle.status_code == 200
    assert audit_after_recycle.json()["events"]

    # Minimal Postgres bind happy-path: session without device, then bind a new key.
    bind_key, bind_public64, bind_fingerprint = _key_material()
    bind_access, _, _, _ = store.issue_session(None, user_id, SESSION_TTL_SECONDS, REFRESH_TTL_SECONDS)
    bound = client.post(
        "/v1/devices/bind",
        headers={"Authorization": "Bearer " + bind_access},
        json={
            "platform": "android",
            "public_key_der_b64": bind_public64,
            "fingerprint_sha256": bind_fingerprint,
        },
    )
    assert bound.status_code == 200, bound.text
    bound_device_id = bound.json()["device_id"]
    assert bound_device_id != device_id

    with store.engine.connect() as conn:
        bind_state = conn.execute(
            text("SELECT state FROM device_bindings WHERE id = CAST(:id AS uuid)"),
            {"id": bound_device_id},
        ).scalar_one()
        linked = conn.execute(
            text(
                "SELECT COUNT(*) FROM sessions WHERE device_id = CAST(:id AS uuid) "
                "AND revoked_at IS NULL"
            ),
            {"id": bound_device_id},
        ).scalar_one()
    assert bind_state == "ACTIVE"
    assert linked >= 1

    # Optional revoke continuation of the bound device.
    revoked = client.post(
        f"/v1/devices/{bound_device_id}/revoke",
        headers={"Authorization": "Bearer " + bind_access},
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json() == {"revoked": True}

    with store.engine.connect() as conn:
        revoked_state = conn.execute(
            text("SELECT state FROM device_bindings WHERE id = CAST(:id AS uuid)"),
            {"id": bound_device_id},
        ).scalar_one()
        revoked_sessions = conn.execute(
            text(
                "SELECT COUNT(*) FROM sessions WHERE device_id = CAST(:id AS uuid) "
                "AND revoked_at IS NOT NULL"
            ),
            {"id": bound_device_id},
        ).scalar_one()
        still_active = conn.execute(
            text(
                "SELECT COUNT(*) FROM sessions WHERE device_id = CAST(:id AS uuid) "
                "AND revoked_at IS NULL"
            ),
            {"id": bound_device_id},
        ).scalar_one()
    assert revoked_state == "REVOKED"
    assert revoked_sessions >= 1
    assert still_active == 0


def test_postgres_web_operation_cancellation_tombstone_and_legacy_refresh_revocation():
    from app.main import app, store
    from app.core.store import PostgresStore

    assert isinstance(store, PostgresStore)
    client = TestClient(app)
    suffix = uuid.uuid4().hex
    email = f"pg-web-generation-{suffix}@example.com"
    password = "Postgres-web-generation-password-123"
    family = "pg-web-family-" + suffix + "x" * 32
    registered = client.post("/v1/auth/register", json={"email": email, "password": password})
    assert registered.status_code == 200
    second_browser = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert second_browser.status_code == 200
    with store.engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE sessions SET refresh_lineage_hash=NULL WHERE identity_id=("
                "SELECT id FROM identities WHERE user_handle=:user) AND device_id IS NULL"
            ),
            {"user": email},
        )

    pending = store.begin_web_session_operation(family)
    failed = store.begin_web_session_operation(family)
    assert store.cancel_web_session_operation(family, failed) is True
    issued = store.issue_web_session(None, email, 3600, 7200, family, pending)
    assert issued is not None

    tombstone = store.revoke_web_session_family_latest(family)
    assert tombstone > failed
    assert store.get_session(issued[0]) is None

    legacy_refresh = registered.json()["refresh_token"]
    logout = client.post(
        "/v1/sessions/web/revoke",
        headers={"X-Sentinel-Web-Session": family},
        json={"refresh_token": legacy_refresh},
    )
    assert logout.status_code == 200
    assert client.post(
        "/v1/sessions/refresh", json={"refresh_token": legacy_refresh}
    ).status_code == 401
    assert client.post(
        "/v1/sessions/refresh", json={"refresh_token": second_browser.json()["refresh_token"]}
    ).status_code == 200


def test_postgres_web_registration_claim_is_cross_worker_and_fail_fast():
    from app.main import claimed_web_registration
    from app.core.security import session_hash
    from app.main import store

    family = "pg-registration-claim-" + uuid.uuid4().hex + "z" * 24

    def claim_once():
        with claimed_web_registration(family) as claimed:
            return claimed

    with claimed_web_registration(family) as creator_claimed:
        assert creator_claimed is True
        assert store.engine.pool.checkedout() == 0
        with ThreadPoolExecutor(max_workers=1) as pool:
            assert pool.submit(claim_once).result() is False

    with store.engine.connect() as conn:
        assert conn.execute(
            text("SELECT COUNT(*) FROM web_registration_claims WHERE family_hash=:family"),
            {"family": session_hash(family)},
        ).scalar_one() == 0
    assert claim_once() is True

    with store.engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO web_registration_claims(family_hash,claim_token_hash,expires_at) "
                "VALUES (:family,'expired-test-claim',now()-interval '1 second')"
            ),
            {"family": session_hash(family)},
        )
    assert claim_once() is True


def test_postgres_legacy_refresh_rotation_cannot_escape_concurrent_logout():
    from app.main import app, store
    from app.core.store import PostgresStore

    assert isinstance(store, PostgresStore)
    client = TestClient(app)
    suffix = uuid.uuid4().hex
    email = f"pg-legacy-lineage-race-{suffix}@example.com"
    registered = client.post(
        "/v1/auth/register",
        json={"email": email, "password": "Postgres-legacy-lineage-race-123"},
    )
    assert registered.status_code == 200
    refresh = registered.json()["refresh_token"]
    with store.engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE sessions SET refresh_lineage_hash=NULL WHERE identity_id=("
                "SELECT id FROM identities WHERE user_handle=:user)"
            ),
            {"user": email},
        )
    family = "pg-legacy-race-family-" + suffix + "y" * 24
    operation = store.begin_web_session_operation(family)

    with ThreadPoolExecutor(max_workers=2) as pool:
        rotate_future = pool.submit(store.rotate_refresh, refresh, 3600, 7200)
        logout_future = pool.submit(store.revoke_web_session_family, family, operation, refresh)
        rotated = rotate_future.result()
        assert logout_future.result() is True

    assert store.rotate_refresh(refresh, 3600, 7200) is None
    if rotated is not None:
        assert store.get_session(rotated[0]) is None
        assert store.rotate_refresh(rotated[1], 3600, 7200) is None


def test_postgres_entitlement_listing_supports_scoped_and_admin_reads():
    from app.main import REFRESH_TTL_SECONDS, SESSION_TTL_SECONDS, app, store
    from app.core.store import PostgresStore

    assert isinstance(store, PostgresStore)
    client = TestClient(app)
    suffix = uuid.uuid4().hex
    user_id = f"pg-entitlements-{suffix}@example.com"
    entitlement_id = str(uuid.uuid4())
    store.create_entitlement(
        {
            "id": entitlement_id,
            "user_id": user_id,
            "game_id": "diablo-immortal-android",
            "source": "postgres-regression",
            "status": "ACTIVE",
            "valid_from": "2026-09-18T00:00:00+00:00",
            "valid_until": "2027-09-18T00:00:00+00:00",
        }
    )

    scoped = store.list_entitlements(user_id)
    assert any(item["id"] == entitlement_id for item in scoped)
    assert all(item["user_id"] == user_id for item in scoped)

    unscoped = store.list_entitlements()
    assert any(item["id"] == entitlement_id for item in unscoped)

    access, _, _, _ = store.issue_session(
        None,
        user_id,
        SESSION_TTL_SECONDS,
        REFRESH_TTL_SECONDS,
    )
    response = client.get(
        "/v1/entitlements/me",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()["entitlements"]
    assert any(
        item["id"] == entitlement_id
        and item["game_name"] == "Diablo Immortal"
        and item["platform"] == "android"
        for item in payload
    )


def test_postgres_account_security_tokens_are_hashed_single_use_and_recovery_revokes_sessions(monkeypatch):
    from app import main as main_module
    from app.core.email_provider import TestEmailTransport
    from app.main import app, store

    transport = TestEmailTransport()
    monkeypatch.setattr(main_module, "email_transport", transport)
    client = TestClient(app)
    email = f"pg-auth-{uuid.uuid4().hex}@example.com"
    old_password = "Postgres-account-old-password-123"
    new_password = "Postgres-account-new-password-456"

    registered = client.post("/v1/auth/register", json={"email": email, "password": old_password})
    assert registered.status_code == 200
    old_access = registered.json()["session_token"]

    verification_token = transport.snapshot()[-1].text.split("Verification code: ", 1)[1].splitlines()[0]
    with store.engine.connect() as conn:
        stored = conn.execute(text("SELECT token_hash,code_hash FROM auth_action_tokens a JOIN users u ON u.identity_id=a.identity_id WHERE u.email=:email AND a.purpose='EMAIL_VERIFY' AND a.consumed_at IS NULL"), {"email": email}).mappings().one()
    from app.core.auth import verify_password
    assert len(verification_token) == 8 and verification_token.isascii() and verification_token.isdigit()
    assert stored["token_hash"] != hashlib.sha256(verification_token.encode()).hexdigest()
    assert verify_password(verification_token, stored["code_hash"])
    assert client.post("/v1/auth/email-verification/confirm", json={"token": verification_token, "email": email}).status_code == 200

    requested = client.post("/v1/auth/password-reset/request", json={"email": email})
    assert requested.status_code == 202
    reset_token = transport.snapshot()[-1].text.split("Reset code: ", 1)[1].splitlines()[0]
    confirmed = client.post(
        "/v1/auth/password-reset/confirm",
        json={"token": reset_token, "email": email, "password": new_password},
    )
    assert confirmed.status_code == 200
    assert store.get_session(old_access) is None
    assert client.post("/v1/auth/login", json={"email": email, "password": old_password}).status_code == 401
    assert client.post("/v1/auth/login", json={"email": email, "password": new_password}).status_code == 200
    assert client.post(
        "/v1/auth/password-reset/confirm",
        json={"token": reset_token, "email": email, "password": "Postgres-account-replay-password-789"},
    ).status_code == 400


def test_postgres_federated_identity_and_challenge_persistence_are_rls_protected():
    from app.main import store, user_store

    subject = f"telegram-{uuid.uuid4().hex}"
    user_id = user_store.register_external_account(
        "telegram",
        subject,
        email=None,
        email_verified=False,
    )
    security = user_store.security_state(user_id)
    assert security is not None
    assert security["email"] is None
    assert security["password_enabled"] is False
    assert security["providers"] == ["telegram"]

    callback_uri = "com.alpha0.app.auth.dev://callback"
    raw_state = user_store.issue_federated_challenge(
        "telegram",
        "OAUTH_STATE",
        300,
        redirect_uri=callback_uri,
    )
    state_hash = hashlib.sha256(raw_state.encode()).hexdigest()
    with store.engine.connect() as conn:
        persisted = conn.execute(
            text(
                "SELECT challenge_hash, provider, purpose, redirect_uri "
                "FROM federated_auth_challenges WHERE challenge_hash=:challenge_hash"
            ),
            {"challenge_hash": state_hash},
        ).mappings().one()
        raw_count = conn.execute(
            text("SELECT COUNT(*) FROM federated_auth_challenges WHERE challenge_hash=:raw"),
            {"raw": raw_state},
        ).scalar_one()
        provider_binding = conn.execute(
            text(
                "SELECT COUNT(*) FROM external_identities "
                "WHERE provider='telegram' AND provider_subject=:subject"
            ),
            {"subject": subject},
        ).scalar_one()

    assert persisted["provider"] == "telegram"
    assert persisted["purpose"] == "OAUTH_STATE"
    assert persisted["redirect_uri"] == callback_uri
    assert raw_count == 0
    assert provider_binding == 1
    assert user_store.consume_federated_challenge("telegram", "OAUTH_STATE", raw_state) == (True, callback_uri)
    assert user_store.consume_federated_challenge("telegram", "OAUTH_STATE", raw_state) == (False, None)
