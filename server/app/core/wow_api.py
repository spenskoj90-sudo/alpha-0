from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.admin import require_admin
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
