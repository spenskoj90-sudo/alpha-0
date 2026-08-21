from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.admin import require_admin
from app.core.security import fingerprint_public_key, session_hash
from app.core.wow_catalog import MMOTOP_REALM_SEEDS, WOW_PATCHES, get_patch, get_realm

router = APIRouter(tags=["world-of-warcraft", "device-security"])


class RealmObservation(BaseModel):
    status: str = Field(pattern="^(ONLINE|DEGRADED|OFFLINE|UNKNOWN)$")
    latency_ms: int | None = Field(default=None, ge=0)
    player_count: int | None = Field(default=None, ge=0)
    endpoint_host: str | None = Field(default=None, max_length=255)
    endpoint_port: int | None = Field(default=None, ge=1, le=65535)
    client_build: str | None = Field(default=None, max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeviceRotateRequest(BaseModel):
    platform: str = Field(pattern="^android$")
    public_key_der_b64: str = Field(min_length=32, max_length=4096)
    fingerprint_sha256: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-fA-F]{64}$")


@router.get("/v1/wow/patches")
def patches() -> dict[str, object]:
    return {"patches": [item.__dict__ for item in WOW_PATCHES]}


@router.get("/v1/wow/realms")
def realms() -> dict[str, object]:
    return {"realms": [item.__dict__ for item in MMOTOP_REALM_SEEDS]}


@router.get("/v1/wow/patches/{patch_id}")
def patch(patch_id: str) -> dict[str, object]:
    item = get_patch(patch_id)
    if item is None:
        raise HTTPException(status_code=404, detail="WOW_PATCH_NOT_FOUND")
    return item.__dict__


@router.get("/v1/wow/realms/{realm_id}")
def realm(realm_id: str) -> dict[str, object]:
    item = get_realm(realm_id)
    if item is None:
        raise HTTPException(status_code=404, detail="WOW_REALM_NOT_FOUND")
    return item.__dict__


@router.post("/v1/wow/realms/{realm_id}/observations")
def observe(realm_id: str, payload: RealmObservation, x_sentinel_admin_token: str | None = Header(default=None)) -> dict[str, object]:
    require_admin(x_sentinel_admin_token)
    item = get_realm(realm_id)
    if item is None:
        raise HTTPException(status_code=404, detail="WOW_REALM_NOT_FOUND")
    return {"realm_id": realm_id, "observed_at": datetime.now(UTC).isoformat(), **payload.model_dump()}


def _security_context():
    """Lazy import avoids the app.main -> wow_api import cycle."""
    from app.main import principal_from_token, require_bearer, store
    return principal_from_token, require_bearer, store


def _rotate_memory(store, old_device_id: str, user_id: str, platform: str, public_key: str, fingerprint: str, challenge: str) -> str:
    with store.lock:
        old = store.devices.get(old_device_id)
        if not old or old["user_id"] != user_id or old["state"] != "ACTIVE":
            raise HTTPException(status_code=404, detail="DEVICE_NOT_ACTIVE")
        old["state"] = "REVOKED"
        for session in store.sessions.values():
            if session.get("device_id") == old_device_id:
                session["revoked"] = True
        new_device_id = secrets.token_urlsafe(24)
        store.devices[new_device_id] = {"user_id": user_id, "platform": platform, "public_key": public_key, "fingerprint": fingerprint, "state": "ACTIVE", "key_version": old.get("key_version", 1) + 1, "last_sequence": -1}
        store.challenges[session_hash(challenge)] = {"device_id": new_device_id, "expires_at": __import__("time").time() + 120, "consumed": False}
        return new_device_id


def _rotate_postgres(store, old_device_id: str, user_id: str, platform: str, public_key: str, fingerprint: str, challenge: str) -> str:
    new_device_id = secrets.token_hex(16)
    with store.engine.begin() as conn:
        identity_id = conn.execute(__import__("sqlalchemy").text("SELECT id FROM identities WHERE user_handle=:u"), {"u": user_id}).scalar_one_or_none()
        old = conn.execute(__import__("sqlalchemy").text("SELECT id, state, key_version FROM device_bindings WHERE id=:d AND identity_id=:i FOR UPDATE"), {"d": old_device_id, "i": identity_id}).mappings().first()
        if not old or old["state"] != "ACTIVE":
            raise HTTPException(status_code=404, detail="DEVICE_NOT_ACTIVE")
        conn.execute(__import__("sqlalchemy").text("UPDATE device_bindings SET state='REVOKED', revoked_at=now() WHERE id=:d"), {"d": old_device_id})
        conn.execute(__import__("sqlalchemy").text("UPDATE sessions SET revoked_at=now() WHERE device_id=:d AND revoked_at IS NULL"), {"d": old_device_id})
        conn.execute(__import__("sqlalchemy").text("INSERT INTO device_bindings(id,identity_id,state,platform,public_key_der_b64,fingerprint_sha256,key_version) VALUES (:id,:i,'ACTIVE',:p,:k,:f,:v)"), {"id": new_device_id, "i": identity_id, "p": platform, "k": public_key, "f": fingerprint, "v": int(old["key_version"]) + 1})
        conn.execute(__import__("sqlalchemy").text("INSERT INTO device_challenges(device_id,nonce_hash,expires_at) VALUES (:d,:n,now()+interval '120 seconds')"), {"d": new_device_id, "n": session_hash(challenge)})
    return new_device_id


@router.post("/v1/devices/{device_id}/rotate")
def rotate_device(device_id: str, payload: DeviceRotateRequest, authorization_header: str = Header(..., alias="Authorization")) -> dict[str, str]:
    principal_from_token, require_bearer, store = _security_context()
    principal = principal_from_token(require_bearer(authorization_header))
    if principal.device_id != device_id:
        raise HTTPException(status_code=403, detail="DEVICE_SCOPE_MISMATCH")
    try:
        fingerprint = fingerprint_public_key(payload.public_key_der_b64)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="INVALID_PUBLIC_KEY") from exc
    if fingerprint.lower() != payload.fingerprint_sha256.lower():
        raise HTTPException(status_code=400, detail="FINGERPRINT_MISMATCH")
    challenge = secrets.token_urlsafe(32)
    if hasattr(store, "devices"):
        new_device_id = _rotate_memory(store, device_id, principal.user_id, payload.platform, payload.public_key_der_b64, fingerprint, challenge)
    else:
        new_device_id = _rotate_postgres(store, device_id, principal.user_id, payload.platform, payload.public_key_der_b64, fingerprint, challenge)
    store.add_audit({"actor_user_id": principal.user_id, "actor_device_id": new_device_id, "action": "device:rotate", "resource": "device", "decision": "ALLOW", "reason_code": "ROTATED", "request_id": None})
    return {"device_id": new_device_id, "state": "ACTIVE", "challenge": challenge}


@router.post("/v1/devices/{device_id}/revoke")
def revoke_device(device_id: str, authorization_header: str = Header(..., alias="Authorization")) -> dict[str, bool]:
    principal_from_token, require_bearer, store = _security_context()
    principal = principal_from_token(require_bearer(authorization_header))
    if principal.device_id != device_id:
        raise HTTPException(status_code=403, detail="DEVICE_SCOPE_MISMATCH")
    if hasattr(store, "devices"):
        with store.lock:
            device = store.devices.get(device_id)
            if not device or device["user_id"] != principal.user_id or device["state"] != "ACTIVE":
                raise HTTPException(status_code=404, detail="DEVICE_NOT_ACTIVE")
            device["state"] = "REVOKED"
            for session in store.sessions.values():
                if session.get("device_id") == device_id:
                    session["revoked"] = True
    else:
        with store.engine.begin() as conn:
            result = conn.execute(__import__("sqlalchemy").text("UPDATE device_bindings SET state='REVOKED', revoked_at=now() WHERE id=:d AND state='ACTIVE' AND identity_id=(SELECT id FROM identities WHERE user_handle=:u)"), {"d": device_id, "u": principal.user_id})
            if result.rowcount != 1:
                raise HTTPException(status_code=404, detail="DEVICE_NOT_ACTIVE")
            conn.execute(__import__("sqlalchemy").text("UPDATE sessions SET revoked_at=now() WHERE device_id=:d AND revoked_at IS NULL"), {"d": device_id})
    store.add_audit({"actor_user_id": principal.user_id, "actor_device_id": device_id, "action": "device:revoke", "resource": "device", "decision": "ALLOW", "reason_code": "REVOKED", "request_id": None})
    return {"revoked": True}


@router.get("/v1/devices/me")
def my_device(authorization_header: str = Header(..., alias="Authorization")) -> dict[str, Any]:
    principal_from_token, require_bearer, store = _security_context()
    principal = principal_from_token(require_bearer(authorization_header))
    if not principal.device_id:
        raise HTTPException(status_code=404, detail="DEVICE_NOT_BOUND")
    return _device_payload(principal.user_id, principal.device_id, store)


@router.get("/v1/devices/{device_id}")
def device_detail(device_id: str, authorization_header: str = Header(..., alias="Authorization")) -> dict[str, Any]:
    principal_from_token, require_bearer, store = _security_context()
    principal = principal_from_token(require_bearer(authorization_header))
    return _device_payload(principal.user_id, device_id, store)


def _device_payload(user_id: str, device_id: str, store) -> dict[str, Any]:
    device = store.get_device(device_id)
    if not device or device.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")
    result: dict[str, Any] = {
        "device_id": device_id,
        "state": device["state"],
        "platform": device["platform"],
        "fingerprint_sha256": device["fingerprint"],
        "algorithm": "EC / secp256r1 / SHA256withECDSA",
        "key_version": device.get("key_version", 1),
        "last_sequence": device.get("last_sequence", -1),
        "last_seen_at": device.get("last_seen_at"),
        "bound_at": device.get("created_at"),
        "security_status": "SECURE" if device["state"] == "ACTIVE" else "AT_RISK",
    }
    if not hasattr(store, "devices"):
        with store.engine.begin() as conn:
            row = conn.execute(__import__("sqlalchemy").text("SELECT created_at,last_seen_at FROM device_bindings WHERE id=:d AND identity_id=(SELECT id FROM identities WHERE user_handle=:u)"), {"d": device_id, "u": user_id}).mappings().first()
        if row:
            result["bound_at"] = row["created_at"].isoformat() if row["created_at"] else None
            result["last_seen_at"] = row["last_seen_at"].isoformat() if row["last_seen_at"] else None
    return result


@router.get("/v1/entitlements/me")
def my_entitlements(authorization_header: str = Header(..., alias="Authorization")) -> dict[str, list[dict[str, Any]]]:
    principal_from_token, require_bearer, store = _security_context()
    principal = principal_from_token(require_bearer(authorization_header))
    items = store.list_entitlements(principal.user_id)
    from app.core.game_catalog import get_game
    enriched: list[dict[str, Any]] = []
    for item in items:
        game = get_game(item["game_id"])
        enriched.append({"id": item["id"], "game_id": item["game_id"], "game_name": game.name if game else item["game_id"], "platform": game.platform.value if game else "unknown", "status": item["status"], "source": item["source"], "valid_from": item["valid_from"], "valid_until": item["valid_until"]})
    return {"entitlements": enriched}


@router.get("/v1/entitlements/{entitlement_id}")
def entitlement_detail(entitlement_id: str, authorization_header: str = Header(..., alias="Authorization")) -> dict[str, Any]:
    principal_from_token, require_bearer, store = _security_context()
    principal = principal_from_token(require_bearer(authorization_header))
    item = next((value for value in store.list_entitlements(principal.user_id) if value["id"] == entitlement_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="ENTITLEMENT_NOT_FOUND")
    from app.core.game_catalog import get_game
    game = get_game(item["game_id"])
    return {"id": item["id"], "game_id": item["game_id"], "game_name": game.name if game else item["game_id"], "platform": game.platform.value if game else "unknown", "family": game.family if game else "unknown", "versioning": game.versioning if game else "unknown", "launcher_supported": game.launcher_supported if game else False, "interaction_mode": game.interaction_mode if game else "unknown", "status": item["status"], "source": item["source"], "valid_from": item["valid_from"], "valid_until": item["valid_until"]}
