from __future__ import annotations

from fastapi import APIRouter, Header, Query, Request

from .admin import require_admin
from .companion_resilience import validate_recovery_matrix
from .operational_observability import observability_registry

router = APIRouter(tags=["admin-observability"])


@router.get("/v1/admin/observability")
def observability_snapshot(
    request: Request,
    x_sentinel_admin_token: str | None = Header(default=None, alias="X-Sentinel-Admin-Token"),
    trace_limit: int = Query(default=64, ge=0, le=128),
) -> dict[str, object]:
    """Return a bounded privacy-safe operator snapshot.

    This endpoint deliberately exposes no raw request/response bodies, account
    identifiers, network peer addresses, voice content, credentials or dynamic
    label dimensions. It is protected by the existing admin control plane.
    """
    from app.main import request_id, store

    require_admin(x_sentinel_admin_token, request, store)
    rid = request_id(request)
    snapshot = observability_registry.snapshot(trace_limit=trace_limit)
    recovery = [
        {
            "name": case.name,
            "expected_outcome": case.expected_outcome.value,
            "recovery": case.recovery,
        }
        for case in validate_recovery_matrix()
    ]
    store.add_audit(
        {
            "actor_user_id": None,
            "actor_device_id": None,
            "action": "admin:observability:read",
            "resource": "observability",
            "decision": "ALLOW",
            "reason_code": "OPERATOR_SNAPSHOT_READ",
            "request_id": rid,
        }
    )
    return {
        **snapshot,
        "request_id": rid,
        "recovery_matrix": recovery,
    }
