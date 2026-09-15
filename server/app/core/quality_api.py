from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any, Literal

from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import text

from app.core.admin import require_admin

router = APIRouter(tags=["quality", "diagnostics"])

DIAGNOSTIC_RETENTION_DAYS = 30
MAX_DIAGNOSTIC_BYTES = 384 * 1024
MAX_DIAGNOSTIC_EVENTS = 600
REPORT_STATUSES = {"RECEIVED", "TRIAGED", "IN_PROGRESS", "RESOLVED", "WONT_FIX"}
SENSITIVE_DETAIL_FRAGMENTS = (
    "password",
    "access_token",
    "refresh_token",
    "session_token",
    "authorization",
    "private_key",
    "credential",
    "database_url",
    "api_key",
    "integrity_token",
    "play_integrity_token",
    "cookie",
    "set-cookie",
)
SECRET_VALUE_PATTERNS = (
    re.compile(r"(?i)bearer\s+[a-z0-9._~+/-]{12,}"),
    re.compile(r"(?i)(?:password|secret|access_token|refresh_token|session_token|api_key)\s*[=:]\s*\S+"),
    re.compile(r"eyJ[a-zA-Z0-9_-]{8,}\.[a-zA-Z0-9_-]{8,}\.[a-zA-Z0-9_-]{8,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)

DiagnosticPrimitive = str | int | float | bool | None


class DiagnosticEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ts: datetime
    elapsed_ms: int = Field(ge=0)
    sequence: int = Field(ge=0)
    level: Literal["DEBUG", "INFO", "WARN", "ERROR"]
    component: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$")
    event: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9._:-]+$")
    result: str = Field(min_length=1, max_length=24, pattern=r"^[A-Z0-9_-]+$")
    request_id: str | None = Field(default=None, max_length=16, pattern=r"^[0-9a-f]+$")
    error_code: str | None = Field(default=None, max_length=96, pattern=r"^[A-Za-z0-9._:-]+$")
    duration_ms: int | None = Field(default=None, ge=0, le=86_400_000)
    details: dict[str, DiagnosticPrimitive] = Field(default_factory=dict)
    exception_class: str | None = Field(default=None, max_length=160)
    exception_msg: str | None = Field(default=None, max_length=1024)
    exception_stack: str | None = Field(default=None, max_length=16_384)

    @field_validator("details")
    @classmethod
    def bounded_safe_details(cls, value: dict[str, DiagnosticPrimitive]) -> dict[str, DiagnosticPrimitive]:
        if len(value) > 32:
            raise ValueError("too many diagnostic detail fields")
        for raw_key, raw_value in value.items():
            key = raw_key.strip()
            if not key or len(key) > 64 or not re.fullmatch(r"[A-Za-z0-9._:-]+", key):
                raise ValueError("invalid diagnostic detail key")
            lowered = key.lower()
            if any(fragment in lowered for fragment in SENSITIVE_DETAIL_FRAGMENTS):
                raise ValueError("sensitive diagnostic detail key")
            if isinstance(raw_value, str):
                if len(raw_value) > 1024:
                    raise ValueError("diagnostic detail value too long")
                _assert_safe_string(raw_value)
        return value

    @field_validator("exception_msg", "exception_stack")
    @classmethod
    def safe_exception_text(cls, value: str | None) -> str | None:
        if value:
            _assert_safe_string(value)
        return value


class DiagnosticSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal["sentinel.diagnostic-snapshot.v1"]
    mode: Literal["PRODUCTION", "FORENSIC_TEST"]
    generated_at: datetime
    app_version: str = Field(min_length=1, max_length=64)
    source_sha: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    build_type: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9._-]+$")
    session_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$")
    dropped_events: int = Field(default=0, ge=0)
    events: list[DiagnosticEvent] = Field(min_length=1, max_length=MAX_DIAGNOSTIC_EVENTS)

    @model_validator(mode="after")
    def bounded_serialized_size(self) -> "DiagnosticSnapshot":
        encoded = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(encoded) > MAX_DIAGNOSTIC_BYTES:
            raise ValueError("diagnostic snapshot too large")
        return self


class QualityReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Literal[
        "DESIGN",
        "FUNCTIONALITY",
        "GAME_INTEGRATION",
        "PERFORMANCE",
        "ACCESSIBILITY",
        "VOICE_AUDIO",
        "SECURITY_PRIVACY",
        "OTHER",
    ]
    title: str = Field(min_length=5, max_length=160)
    description: str = Field(min_length=1, max_length=4000)
    diagnostics_consent: bool = False
    quality_program_opt_in: bool = False
    diagnostics: DiagnosticSnapshot | None = None

    @field_validator("title", "description")
    @classmethod
    def trim_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("report text must not be blank")
        return normalized

    @model_validator(mode="after")
    def consent_matches_payload(self) -> "QualityReportCreate":
        if self.diagnostics_consent != (self.diagnostics is not None):
            raise ValueError("diagnostics payload requires explicit matching consent")
        return self


class QualityReportStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["TRIAGED", "IN_PROGRESS", "RESOLVED", "WONT_FIX"]


class QualityReportRepository:
    """Persistence seam for user quality reports.

    Production uses the existing Postgres engine. MemoryStore-backed test/dev runs
    use a bounded process-local dictionary. Diagnostic payloads expire independently
    from the ticket metadata so support history can remain while sensitive runtime
    context is automatically removed after the retention window.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._memory: dict[str, dict[str, Any]] = {}

    def _is_memory(self, store: Any) -> bool:
        return not hasattr(store, "engine")

    def _prune_memory(self) -> None:
        now = datetime.now(UTC)
        for item in self._memory.values():
            expires = item.get("diagnostics_expires_at")
            if expires and expires <= now and item.get("diagnostics") is not None:
                item["diagnostics"] = None
                item["diagnostics_bytes"] = 0

    def _prune_postgres(self, store: Any) -> None:
        with store.engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE quality_reports SET diagnostics_json=NULL, diagnostics_bytes=0 "
                    "WHERE diagnostics_json IS NOT NULL AND diagnostics_expires_at <= now()"
                )
            )

    def create(self, store: Any, principal: Any, payload: QualityReportCreate) -> dict[str, Any]:
        report_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        diagnostics_document = payload.diagnostics.model_dump(mode="json") if payload.diagnostics else None
        diagnostics_json = json.dumps(diagnostics_document, sort_keys=True, separators=(",", ":")) if diagnostics_document else None
        diagnostics_bytes = len(diagnostics_json.encode("utf-8")) if diagnostics_json else 0
        expires = now + timedelta(days=DIAGNOSTIC_RETENTION_DAYS) if diagnostics_json else None
        record = {
            "id": report_id,
            "user_id": principal.user_id,
            "device_id": principal.device_id,
            "category": payload.category,
            "title": payload.title,
            "description": payload.description,
            "status": "RECEIVED",
            "diagnostics_consent": payload.diagnostics_consent,
            "quality_program_opt_in": payload.quality_program_opt_in,
            "diagnostics": diagnostics_document,
            "diagnostics_bytes": diagnostics_bytes,
            "diagnostics_expires_at": expires,
            "created_at": now,
            "updated_at": now,
        }
        if self._is_memory(store):
            with self._lock:
                self._prune_memory()
                if len(self._memory) >= 2000:
                    oldest = min(self._memory.values(), key=lambda item: item["created_at"])
                    del self._memory[oldest["id"]]
                self._memory[report_id] = record
            return dict(record)

        self._prune_postgres(store)
        with store.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO quality_reports "
                    "(id,user_id,device_id,category,title,description,status,diagnostics_consent,quality_program_opt_in,"
                    "diagnostics_json,diagnostics_bytes,diagnostics_expires_at,created_at,updated_at) "
                    "VALUES (:id,:user_id,:device_id,:category,:title,:description,:status,:diagnostics_consent,:quality_program_opt_in,"
                    "CAST(:diagnostics_json AS jsonb),:diagnostics_bytes,:diagnostics_expires_at,:created_at,:updated_at)"
                ),
                {
                    **{k: record[k] for k in (
                        "id", "user_id", "device_id", "category", "title", "description", "status",
                        "diagnostics_consent", "quality_program_opt_in", "diagnostics_bytes",
                        "diagnostics_expires_at", "created_at", "updated_at",
                    )},
                    "diagnostics_json": diagnostics_json,
                },
            )
        return dict(record)

    def get(self, store: Any, report_id: str) -> dict[str, Any] | None:
        if self._is_memory(store):
            with self._lock:
                self._prune_memory()
                item = self._memory.get(report_id)
                return dict(item) if item else None
        self._prune_postgres(store)
        with store.engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM quality_reports WHERE id=:id"), {"id": report_id}
            ).mappings().first()
        return _postgres_record(row) if row else None

    def list(self, store: Any, limit: int, status: str | None = None) -> list[dict[str, Any]]:
        if self._is_memory(store):
            with self._lock:
                self._prune_memory()
                items = [dict(item) for item in self._memory.values() if status is None or item["status"] == status]
            return sorted(items, key=lambda item: item["created_at"], reverse=True)[:limit]
        self._prune_postgres(store)
        query = "SELECT * FROM quality_reports"
        params: dict[str, Any] = {"limit": limit}
        if status is not None:
            query += " WHERE status=:status"
            params["status"] = status
        query += " ORDER BY created_at DESC LIMIT :limit"
        with store.engine.connect() as conn:
            rows = conn.execute(text(query), params).mappings().all()
        return [_postgres_record(row) for row in rows]

    def set_status(self, store: Any, report_id: str, status: str) -> dict[str, Any] | None:
        now = datetime.now(UTC)
        if self._is_memory(store):
            with self._lock:
                item = self._memory.get(report_id)
                if not item:
                    return None
                item["status"] = status
                item["updated_at"] = now
                return dict(item)
        with store.engine.begin() as conn:
            row = conn.execute(
                text(
                    "UPDATE quality_reports SET status=:status, updated_at=:updated_at "
                    "WHERE id=:id RETURNING *"
                ),
                {"id": report_id, "status": status, "updated_at": now},
            ).mappings().first()
        return _postgres_record(row) if row else None


repository = QualityReportRepository()


def _assert_safe_string(value: str) -> None:
    for pattern in SECRET_VALUE_PATTERNS:
        if pattern.search(value):
            raise ValueError("diagnostic payload appears to contain a secret")


def _postgres_record(row: Any) -> dict[str, Any]:
    result = dict(row)
    diagnostics = result.pop("diagnostics_json", None)
    if isinstance(diagnostics, str):
        diagnostics = json.loads(diagnostics)
    result["diagnostics"] = diagnostics
    return result


def _security_context():
    from app.main import principal_from_token, rate_limit, request_id, require_bearer, store
    return principal_from_token, rate_limit, request_id, require_bearer, store


def _public_report(record: dict[str, Any], *, include_diagnostics: bool) -> dict[str, Any]:
    result = {
        "id": record["id"],
        "category": record["category"],
        "title": record["title"],
        "description": record["description"],
        "status": record["status"],
        "diagnostics_consent": bool(record["diagnostics_consent"]),
        "quality_program_opt_in": bool(record["quality_program_opt_in"]),
        "diagnostics_retained": record.get("diagnostics") is not None,
        "diagnostics_bytes": int(record.get("diagnostics_bytes") or 0),
        "diagnostics_expires_at": _iso(record.get("diagnostics_expires_at")),
        "created_at": _iso(record["created_at"]),
        "updated_at": _iso(record["updated_at"]),
    }
    if include_diagnostics:
        result["diagnostics"] = record.get("diagnostics")
    return result


def _admin_report(record: dict[str, Any], *, include_diagnostics: bool) -> dict[str, Any]:
    result = _public_report(record, include_diagnostics=include_diagnostics)
    result["user_id"] = record["user_id"]
    result["device_id"] = record.get("device_id")
    return result


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return str(value)


@router.post("/v1/quality/reports")
def create_quality_report(
    payload: QualityReportCreate,
    request: Request,
    authorization_header: str = Header(..., alias="Authorization"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> dict[str, Any]:
    principal_from_token, rate_limit, request_id, require_bearer, store = _security_context()
    rid = request_id(request, x_request_id)
    rate_limit(request, "quality-report")
    principal = principal_from_token(require_bearer(authorization_header))
    record = repository.create(store, principal, payload)
    store.add_audit(
        {
            "actor_user_id": principal.user_id,
            "actor_device_id": principal.device_id,
            "action": "quality:report:create",
            "resource": f"quality-report:{record['id']}",
            "decision": "ALLOW",
            "reason_code": "USER_SUBMITTED",
            "request_id": rid,
        }
    )
    return {
        "report": _public_report(record, include_diagnostics=False),
        "request_id": rid,
        "diagnostics_retention_days": DIAGNOSTIC_RETENTION_DAYS,
    }


@router.get("/v1/quality/reports/{report_id}")
def get_own_quality_report(
    report_id: str,
    authorization_header: str = Header(..., alias="Authorization"),
) -> dict[str, Any]:
    principal_from_token, _, _, require_bearer, store = _security_context()
    principal = principal_from_token(require_bearer(authorization_header))
    record = repository.get(store, report_id)
    if not record or record["user_id"] != principal.user_id:
        raise HTTPException(status_code=404, detail="QUALITY_REPORT_NOT_FOUND")
    return {"report": _public_report(record, include_diagnostics=False)}


@router.get("/v1/admin/quality/reports")
def admin_list_quality_reports(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    status: str | None = Query(default=None),
    x_sentinel_admin_token: str | None = Header(default=None, alias="X-Sentinel-Admin-Token"),
) -> dict[str, Any]:
    _, _, _, _, store = _security_context()
    require_admin(x_sentinel_admin_token, request, store)
    if status is not None and status not in REPORT_STATUSES:
        raise HTTPException(status_code=400, detail="QUALITY_REPORT_STATUS_INVALID")
    reports = repository.list(store, limit=limit, status=status)
    return {"reports": [_admin_report(item, include_diagnostics=False) for item in reports]}


@router.get("/v1/admin/quality/reports/{report_id}")
def admin_get_quality_report(
    report_id: str,
    request: Request,
    x_sentinel_admin_token: str | None = Header(default=None, alias="X-Sentinel-Admin-Token"),
) -> dict[str, Any]:
    _, _, _, _, store = _security_context()
    require_admin(x_sentinel_admin_token, request, store)
    record = repository.get(store, report_id)
    if not record:
        raise HTTPException(status_code=404, detail="QUALITY_REPORT_NOT_FOUND")
    return {"report": _admin_report(record, include_diagnostics=True)}


@router.post("/v1/admin/quality/reports/{report_id}/status")
def admin_update_quality_report_status(
    report_id: str,
    payload: QualityReportStatusUpdate,
    request: Request,
    x_sentinel_admin_token: str | None = Header(default=None, alias="X-Sentinel-Admin-Token"),
) -> dict[str, Any]:
    _, _, _, _, store = _security_context()
    require_admin(x_sentinel_admin_token, request, store)
    record = repository.set_status(store, report_id, payload.status)
    if not record:
        raise HTTPException(status_code=404, detail="QUALITY_REPORT_NOT_FOUND")
    store.add_audit(
        {
            "actor_user_id": None,
            "actor_device_id": None,
            "action": "quality:report:status",
            "resource": f"quality-report:{report_id}",
            "decision": "ALLOW",
            "reason_code": payload.status,
            "request_id": None,
        }
    )
    return {"report": _admin_report(record, include_diagnostics=False)}
