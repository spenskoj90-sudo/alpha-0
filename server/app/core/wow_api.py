from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.admin import require_admin
from app.core.wow_catalog import MMOTOP_REALM_SEEDS, WOW_PATCHES, get_patch, get_realm

router = APIRouter(prefix="/v1/wow", tags=["world-of-warcraft"])


class RealmObservation(BaseModel):
    status: str = Field(pattern="^(ONLINE|DEGRADED|OFFLINE|UNKNOWN)$")
    latency_ms: int | None = Field(default=None, ge=0)
    player_count: int | None = Field(default=None, ge=0)
    endpoint_host: str | None = Field(default=None, max_length=255)
    endpoint_port: int | None = Field(default=None, ge=1, le=65535)
    client_build: str | None = Field(default=None, max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.get("/patches")
def patches() -> dict[str, object]:
    return {"patches": [item.__dict__ for item in WOW_PATCHES]}


@router.get("/realms")
def realms() -> dict[str, object]:
    return {"realms": [item.__dict__ for item in MMOTOP_REALM_SEEDS]}


@router.get("/patches/{patch_id}")
def patch(patch_id: str) -> dict[str, object]:
    item = get_patch(patch_id)
    if item is None:
        raise HTTPException(status_code=404, detail="WOW_PATCH_NOT_FOUND")
    return item.__dict__


@router.get("/realms/{realm_id}")
def realm(realm_id: str) -> dict[str, object]:
    item = get_realm(realm_id)
    if item is None:
        raise HTTPException(status_code=404, detail="WOW_REALM_NOT_FOUND")
    return item.__dict__


@router.post("/realms/{realm_id}/observations")
def observe(realm_id: str, payload: RealmObservation, x_sentinel_admin_token: str | None = Header(default=None)) -> dict[str, object]:
    require_admin(x_sentinel_admin_token)
    item = get_realm(realm_id)
    if item is None:
        raise HTTPException(status_code=404, detail="WOW_REALM_NOT_FOUND")
    return {"realm_id": realm_id, "observed_at": datetime.now(UTC).isoformat(), **payload.model_dump()}
