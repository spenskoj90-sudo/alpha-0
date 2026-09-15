from __future__ import annotations

import hashlib
import json
import math
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
MAX_CLUSTER_ALIAS_HOPS = 64
QUALITY_CLUSTER_MERGE_ADVISORY_LOCK = 834_607_112
REPORT_STATUSES = {"RECEIVED", "TRIAGED", "IN_PROGRESS", "RESOLVED", "WONT_FIX"}
CLUSTER_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
SEVERITY_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
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
    "device_id",
    "fingerprint",
    "user_id",
    "email",
    "realm",
    "character",
    "savedvariables",
    "chat_text",
    "transcript",
    "request_body",
    "response_body",
    "audio_bytes",
    "microphone_bytes",
)
SECRET_VALUE_PATTERNS = (
    re.compile(r"(?i)bearer\s+[a-z0-9._~+/-]{12,}"),
    re.compile(r"(?i)(?:password|secret|access_token|refresh_token|session_token|api_key)\s*[=:]\s*\S+"),
    re.compile(r"eyJ[a-zA-Z0-9_-]{8,}\.[a-zA-Z0-9_-]{8,}\.[a-zA-Z0-9_-]{8,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
TEXT_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "has", "have", "i",
    "in", "is", "it", "my", "not", "of", "on", "or", "that", "the", "this", "to", "was", "when",
    "with", "after", "before", "did", "does", "do", "problem", "issue", "error", "sentinel",
}

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


class QualityClusterUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["RECEIVED", "TRIAGED", "IN_PROGRESS", "RESOLVED", "WONT_FIX"] | None = None
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] | None = None

    @model_validator(mode="after")
    def at_least_one_change(self) -> "QualityClusterUpdate":
        if self.status is None and self.severity is None:
            raise ValueError("cluster update requires status or severity")
        return self


class QualityClusterMerge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_cluster_id: str = Field(min_length=36, max_length=36)


class QualityReportRepository:
    """Persistence and issue-intelligence seam for quality reports.

    Production uses Postgres. Tests/dev use bounded process-local dictionaries. Each
    report remains independent evidence, while a cluster is the operational unit used
    for frequency, breadth, severity and triage. Automatic grouping is conservative:
    strong diagnostic signatures win; otherwise normalized text produces a stable
    fingerprint. Admins can merge clusters when human review establishes equivalence.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._memory: dict[str, dict[str, Any]] = {}
        self._memory_clusters: dict[str, dict[str, Any]] = {}

    def _is_memory(self, store: Any) -> bool:
        return not hasattr(store, "engine")

    def _prune_memory(self) -> None:
        now = datetime.now(UTC)
        for item in self._memory.values():
            expires = item.get("diagnostics_expires_at")
            if expires and expires <= now and item.get("diagnostics") is not None:
                item["diagnostics"] = None
                item["diagnostics_bytes"] = 0

    def _resolve_memory_root(self, cluster: dict[str, Any]) -> dict[str, Any]:
        aliases: list[str] = []
        seen: set[str] = set()
        current = cluster
        while current.get("merged_into_id"):
            current_id = str(current["id"])
            if current_id in seen or len(seen) >= MAX_CLUSTER_ALIAS_HOPS:
                raise RuntimeError("quality cluster alias cycle or excessive depth")
            seen.add(current_id)
            aliases.append(current_id)
            next_id = str(current["merged_into_id"])
            next_cluster = self._memory_clusters.get(next_id)
            if next_cluster is None:
                raise RuntimeError("merged quality cluster target missing")
            current = next_cluster
        root_id = str(current["id"])
        for alias_id in aliases:
            alias = self._memory_clusters.get(alias_id)
            if alias is not None:
                alias["merged_into_id"] = root_id
        return current

    def _prune_postgres(self, conn: Any) -> None:
        conn.execute(
            text(
                "WITH expired AS ("
                " SELECT id FROM quality_reports"
                " WHERE diagnostics_json IS NOT NULL AND diagnostics_expires_at <= now()"
                " ORDER BY diagnostics_expires_at ASC LIMIT 200"
                ") UPDATE quality_reports q SET diagnostics_json=NULL, diagnostics_bytes=0"
                " FROM expired e WHERE q.id=e.id"
            )
        )

    def _lock_postgres_root(self, conn: Any, cluster: Any) -> Any:
        current = cluster
        seen: set[str] = set()
        while current.get("merged_into_id"):
            current_id = str(current["id"])
            if current_id in seen or len(seen) >= MAX_CLUSTER_ALIAS_HOPS:
                raise RuntimeError("quality cluster alias cycle or excessive depth")
            seen.add(current_id)
            next_cluster = conn.execute(
                text("SELECT * FROM quality_issue_clusters WHERE id=:id FOR UPDATE"),
                {"id": current["merged_into_id"]},
            ).mappings().first()
            if next_cluster is None:
                raise RuntimeError("merged quality cluster target missing")
            current = next_cluster
        return current

    def create(self, store: Any, principal: Any, payload: QualityReportCreate) -> dict[str, Any]:
        report_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        diagnostics_document = payload.diagnostics.model_dump(mode="json") if payload.diagnostics else None
        diagnostics_json = json.dumps(diagnostics_document, sort_keys=True, separators=(",", ":")) if diagnostics_document else None
        diagnostics_bytes = len(diagnostics_json.encode("utf-8")) if diagnostics_json else 0
        expires = now + timedelta(days=DIAGNOSTIC_RETENTION_DAYS) if diagnostics_json else None
        fingerprint, signature_kind, inferred_severity = _issue_identity(payload)
        app_version = payload.diagnostics.app_version if payload.diagnostics else None
        source_sha = payload.diagnostics.source_sha if payload.diagnostics else None
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
            "issue_fingerprint": fingerprint,
            "inferred_severity": inferred_severity,
            "created_at": now,
            "updated_at": now,
        }
        if self._is_memory(store):
            return self._create_memory(record, signature_kind, app_version, source_sha)
        return self._create_postgres(store, record, diagnostics_json, signature_kind, app_version, source_sha)

    def _create_memory(
        self,
        record: dict[str, Any],
        signature_kind: str,
        app_version: str | None,
        source_sha: str | None,
    ) -> dict[str, Any]:
        with self._lock:
            self._prune_memory()
            if len(self._memory) >= 5000:
                oldest = min(self._memory.values(), key=lambda item: item["created_at"])
                del self._memory[oldest["id"]]
            cluster = next(
                (item for item in self._memory_clusters.values() if item["fingerprint"] == record["issue_fingerprint"]),
                None,
            )
            if cluster is not None:
                cluster = self._resolve_memory_root(cluster)
            if cluster is None:
                cluster_id = str(uuid.uuid4())
                cluster = {
                    "id": cluster_id,
                    "fingerprint": record["issue_fingerprint"],
                    "signature_kind": signature_kind,
                    "category": record["category"],
                    "canonical_title": record["title"],
                    "severity": record["inferred_severity"],
                    "severity_locked": False,
                    "status": "RECEIVED",
                    "priority_score": 0,
                    "occurrence_count": 0,
                    "affected_user_count": 0,
                    "affected_device_count": 0,
                    "affected_version_count": 0,
                    "first_seen_at": record["created_at"],
                    "last_seen_at": record["created_at"],
                    "last_app_version": app_version,
                    "last_source_sha": source_sha,
                    "merged_into_id": None,
                    "created_at": record["created_at"],
                    "updated_at": record["created_at"],
                    "_users": set(),
                    "_devices": set(),
                    "_versions": set(),
                }
                self._memory_clusters[cluster_id] = cluster
            record["cluster_id"] = cluster["id"]
            self._memory[record["id"]] = record
            cluster["occurrence_count"] += 1
            cluster["_users"].add(record["user_id"])
            if record.get("device_id"):
                cluster["_devices"].add(str(record["device_id"]))
            if app_version:
                cluster["_versions"].add(app_version)
            cluster["affected_user_count"] = len(cluster["_users"])
            cluster["affected_device_count"] = len(cluster["_devices"])
            cluster["affected_version_count"] = len(cluster["_versions"])
            cluster["last_seen_at"] = record["created_at"]
            cluster["last_app_version"] = app_version or cluster.get("last_app_version")
            cluster["last_source_sha"] = source_sha or cluster.get("last_source_sha")
            cluster["updated_at"] = record["created_at"]
            if not cluster["severity_locked"] and SEVERITY_RANK[record["inferred_severity"]] > SEVERITY_RANK[cluster["severity"]]:
                cluster["severity"] = record["inferred_severity"]
            cluster["priority_score"] = _priority_score(
                cluster["severity"], cluster["occurrence_count"], cluster["affected_user_count"]
            )
            record["cluster_occurrence_count"] = cluster["occurrence_count"]
            record["cluster_priority_score"] = cluster["priority_score"]
            record["cluster_severity"] = cluster["severity"]
            return dict(record)

    def _create_postgres(
        self,
        store: Any,
        record: dict[str, Any],
        diagnostics_json: str | None,
        signature_kind: str,
        app_version: str | None,
        source_sha: str | None,
    ) -> dict[str, Any]:
        cluster_seed_id = str(uuid.uuid4())
        with store.engine.begin() as conn:
            self._prune_postgres(conn)
            conn.execute(
                text(
                    "INSERT INTO quality_issue_clusters "
                    "(id,fingerprint,signature_kind,category,canonical_title,severity,severity_locked,status,priority_score,"
                    "occurrence_count,affected_user_count,affected_device_count,affected_version_count,first_seen_at,last_seen_at,"
                    "last_app_version,last_source_sha,created_at,updated_at) "
                    "VALUES (:id,:fingerprint,:signature_kind,:category,:canonical_title,:severity,false,'RECEIVED',0,0,0,0,0,"
                    ":seen,:seen,:app_version,:source_sha,:seen,:seen) ON CONFLICT (fingerprint) DO NOTHING"
                ),
                {
                    "id": cluster_seed_id,
                    "fingerprint": record["issue_fingerprint"],
                    "signature_kind": signature_kind,
                    "category": record["category"],
                    "canonical_title": record["title"],
                    "severity": record["inferred_severity"],
                    "seen": record["created_at"],
                    "app_version": app_version,
                    "source_sha": source_sha,
                },
            )
            cluster = conn.execute(
                text("SELECT * FROM quality_issue_clusters WHERE fingerprint=:fingerprint FOR UPDATE"),
                {"fingerprint": record["issue_fingerprint"]},
            ).mappings().first()
            if cluster is None:
                raise RuntimeError("quality cluster was not created")
            cluster = self._lock_postgres_root(conn, cluster)
            cluster_id = str(cluster["id"])
            record["cluster_id"] = cluster_id
            conn.execute(
                text(
                    "INSERT INTO quality_reports "
                    "(id,user_id,device_id,category,title,description,status,diagnostics_consent,quality_program_opt_in,"
                    "diagnostics_json,diagnostics_bytes,diagnostics_expires_at,cluster_id,issue_fingerprint,inferred_severity,created_at,updated_at) "
                    "VALUES (:id,:user_id,:device_id,:category,:title,:description,:status,:diagnostics_consent,:quality_program_opt_in,"
                    "CAST(:diagnostics_json AS jsonb),:diagnostics_bytes,:diagnostics_expires_at,:cluster_id,:issue_fingerprint,:inferred_severity,"
                    ":created_at,:updated_at)"
                ),
                {
                    **{k: record[k] for k in (
                        "id", "user_id", "device_id", "category", "title", "description", "status",
                        "diagnostics_consent", "quality_program_opt_in", "diagnostics_bytes", "diagnostics_expires_at",
                        "cluster_id", "issue_fingerprint", "inferred_severity", "created_at", "updated_at",
                    )},
                    "diagnostics_json": diagnostics_json,
                },
            )
            new_user = conn.execute(
                text(
                    "INSERT INTO quality_cluster_users (cluster_id,user_id,first_seen_at,last_seen_at) "
                    "VALUES (:cluster_id,:value,:seen,:seen) ON CONFLICT (cluster_id,user_id) DO UPDATE SET last_seen_at=EXCLUDED.last_seen_at "
                    "RETURNING (xmax = 0) AS inserted"
                ),
                {"cluster_id": cluster_id, "value": record["user_id"], "seen": record["created_at"]},
            ).mappings().first()
            user_increment = 1 if new_user and bool(new_user["inserted"]) else 0
            device_increment = 0
            if record.get("device_id"):
                new_device = conn.execute(
                    text(
                        "INSERT INTO quality_cluster_devices (cluster_id,device_id,first_seen_at,last_seen_at) "
                        "VALUES (:cluster_id,:value,:seen,:seen) ON CONFLICT (cluster_id,device_id) DO UPDATE SET last_seen_at=EXCLUDED.last_seen_at "
                        "RETURNING (xmax = 0) AS inserted"
                    ),
                    {"cluster_id": cluster_id, "value": record["device_id"], "seen": record["created_at"]},
                ).mappings().first()
                device_increment = 1 if new_device and bool(new_device["inserted"]) else 0
            version_increment = 0
            if app_version:
                new_version = conn.execute(
                    text(
                        "INSERT INTO quality_cluster_versions (cluster_id,app_version,first_seen_at,last_seen_at) "
                        "VALUES (:cluster_id,:value,:seen,:seen) ON CONFLICT (cluster_id,app_version) DO UPDATE SET last_seen_at=EXCLUDED.last_seen_at "
                        "RETURNING (xmax = 0) AS inserted"
                    ),
                    {"cluster_id": cluster_id, "value": app_version, "seen": record["created_at"]},
                ).mappings().first()
                version_increment = 1 if new_version and bool(new_version["inserted"]) else 0
            severity = str(cluster["severity"])
            if not bool(cluster["severity_locked"]) and SEVERITY_RANK[record["inferred_severity"]] > SEVERITY_RANK[severity]:
                severity = record["inferred_severity"]
            occurrence_count = int(cluster["occurrence_count"]) + 1
            affected_user_count = int(cluster["affected_user_count"]) + user_increment
            affected_device_count = int(cluster["affected_device_count"]) + device_increment
            affected_version_count = int(cluster["affected_version_count"]) + version_increment
            priority = _priority_score(severity, occurrence_count, affected_user_count)
            conn.execute(
                text(
                    "UPDATE quality_issue_clusters SET severity=:severity,priority_score=:priority,"
                    "occurrence_count=:occurrences,affected_user_count=:users,affected_device_count=:devices,"
                    "affected_version_count=:versions,last_seen_at=:seen,last_app_version=COALESCE(:app_version,last_app_version),"
                    "last_source_sha=COALESCE(:source_sha,last_source_sha),updated_at=:seen WHERE id=:id"
                ),
                {
                    "id": cluster_id,
                    "severity": severity,
                    "priority": priority,
                    "occurrences": occurrence_count,
                    "users": affected_user_count,
                    "devices": affected_device_count,
                    "versions": affected_version_count,
                    "seen": record["created_at"],
                    "app_version": app_version,
                    "source_sha": source_sha,
                },
            )
        record["cluster_occurrence_count"] = occurrence_count
        record["cluster_priority_score"] = priority
        record["cluster_severity"] = severity
        return dict(record)

    def get(self, store: Any, report_id: str) -> dict[str, Any] | None:
        if self._is_memory(store):
            with self._lock:
                self._prune_memory()
                item = self._memory.get(report_id)
                return dict(item) if item else None
        with store.engine.begin() as conn:
            self._prune_postgres(conn)
            row = conn.execute(text("SELECT * FROM quality_reports WHERE id=:id"), {"id": report_id}).mappings().first()
        return _postgres_record(row) if row else None

    def list(self, store: Any, limit: int, status: str | None = None) -> list[dict[str, Any]]:
        if self._is_memory(store):
            with self._lock:
                self._prune_memory()
                items = [dict(item) for item in self._memory.values() if status is None or item["status"] == status]
            return sorted(items, key=lambda item: item["created_at"], reverse=True)[:limit]
        query = "SELECT * FROM quality_reports"
        params: dict[str, Any] = {"limit": limit}
        if status is not None:
            query += " WHERE status=:status"
            params["status"] = status
        query += " ORDER BY created_at DESC LIMIT :limit"
        with store.engine.begin() as conn:
            self._prune_postgres(conn)
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
                text("UPDATE quality_reports SET status=:status, updated_at=:updated_at WHERE id=:id RETURNING *"),
                {"id": report_id, "status": status, "updated_at": now},
            ).mappings().first()
        return _postgres_record(row) if row else None

    def list_clusters(
        self,
        store: Any,
        limit: int,
        status: str | None = None,
        severity: str | None = None,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        if self._is_memory(store):
            with self._lock:
                items = [
                    _copy_cluster(item)
                    for item in self._memory_clusters.values()
                    if item.get("merged_into_id") is None
                    and (status is None or item["status"] == status)
                    and (severity is None or item["severity"] == severity)
                    and (category is None or item["category"] == category)
                ]
            return sorted(items, key=lambda item: (item["priority_score"], item["last_seen_at"]), reverse=True)[:limit]
        clauses = ["merged_into_id IS NULL"]
        params: dict[str, Any] = {"limit": limit}
        if status:
            clauses.append("status=:status")
            params["status"] = status
        if severity:
            clauses.append("severity=:severity")
            params["severity"] = severity
        if category:
            clauses.append("category=:category")
            params["category"] = category
        query = "SELECT * FROM quality_issue_clusters WHERE " + " AND ".join(clauses)
        query += " ORDER BY priority_score DESC, last_seen_at DESC LIMIT :limit"
        with store.engine.connect() as conn:
            rows = conn.execute(text(query), params).mappings().all()
        return [dict(row) for row in rows]

    def get_cluster(self, store: Any, cluster_id: str, include_reports: bool = False) -> dict[str, Any] | None:
        if self._is_memory(store):
            with self._lock:
                cluster = self._memory_clusters.get(cluster_id)
                if not cluster:
                    return None
                result = _copy_cluster(cluster)
                if include_reports:
                    result["reports"] = [
                        dict(item) for item in sorted(self._memory.values(), key=lambda value: value["created_at"], reverse=True)
                        if item.get("cluster_id") == cluster_id
                    ][:200]
                return result
        with store.engine.connect() as conn:
            row = conn.execute(text("SELECT * FROM quality_issue_clusters WHERE id=:id"), {"id": cluster_id}).mappings().first()
            if not row:
                return None
            result = dict(row)
            if include_reports:
                reports = conn.execute(
                    text("SELECT * FROM quality_reports WHERE cluster_id=:id ORDER BY created_at DESC LIMIT 200"),
                    {"id": cluster_id},
                ).mappings().all()
                result["reports"] = [_postgres_record(item) for item in reports]
        return result

    def update_cluster(
        self,
        store: Any,
        cluster_id: str,
        *,
        status: str | None,
        severity: str | None,
    ) -> dict[str, Any] | None:
        now = datetime.now(UTC)
        if self._is_memory(store):
            with self._lock:
                cluster = self._memory_clusters.get(cluster_id)
                if not cluster or cluster.get("merged_into_id"):
                    return None
                if status:
                    cluster["status"] = status
                    for report in self._memory.values():
                        if report.get("cluster_id") == cluster_id:
                            report["status"] = status
                            report["updated_at"] = now
                if severity:
                    cluster["severity"] = severity
                    cluster["severity_locked"] = True
                cluster["priority_score"] = _priority_score(
                    cluster["severity"], cluster["occurrence_count"], cluster["affected_user_count"]
                )
                cluster["updated_at"] = now
                return _copy_cluster(cluster)
        with store.engine.begin() as conn:
            cluster = conn.execute(
                text("SELECT * FROM quality_issue_clusters WHERE id=:id AND merged_into_id IS NULL FOR UPDATE"),
                {"id": cluster_id},
            ).mappings().first()
            if not cluster:
                return None
            next_status = status or str(cluster["status"])
            next_severity = severity or str(cluster["severity"])
            next_locked = True if severity else bool(cluster["severity_locked"])
            priority = _priority_score(next_severity, int(cluster["occurrence_count"]), int(cluster["affected_user_count"]))
            row = conn.execute(
                text(
                    "UPDATE quality_issue_clusters SET status=:status,severity=:severity,severity_locked=:locked,"
                    "priority_score=:priority,updated_at=:updated_at WHERE id=:id RETURNING *"
                ),
                {
                    "id": cluster_id,
                    "status": next_status,
                    "severity": next_severity,
                    "locked": next_locked,
                    "priority": priority,
                    "updated_at": now,
                },
            ).mappings().first()
            if status:
                conn.execute(
                    text("UPDATE quality_reports SET status=:status,updated_at=:updated_at WHERE cluster_id=:id"),
                    {"id": cluster_id, "status": status, "updated_at": now},
                )
        return dict(row) if row else None

    def merge_cluster(self, store: Any, source_id: str, target_id: str) -> dict[str, Any] | None:
        if source_id == target_id:
            raise ValueError("source and target clusters must differ")
        now = datetime.now(UTC)
        if self._is_memory(store):
            with self._lock:
                source = self._memory_clusters.get(source_id)
                target = self._memory_clusters.get(target_id)
                if not source or not target or source.get("merged_into_id") or target.get("merged_into_id"):
                    return None
                for report in self._memory.values():
                    if report.get("cluster_id") == source_id:
                        report["cluster_id"] = target_id
                        report["updated_at"] = now
                target["_users"].update(source["_users"])
                target["_devices"].update(source["_devices"])
                target["_versions"].update(source["_versions"])
                target["occurrence_count"] += source["occurrence_count"]
                target["affected_user_count"] = len(target["_users"])
                target["affected_device_count"] = len(target["_devices"])
                target["affected_version_count"] = len(target["_versions"])
                target["first_seen_at"] = min(target["first_seen_at"], source["first_seen_at"])
                target["last_seen_at"] = max(target["last_seen_at"], source["last_seen_at"])
                if not target["severity_locked"] and SEVERITY_RANK[source["severity"]] > SEVERITY_RANK[target["severity"]]:
                    target["severity"] = source["severity"]
                target["priority_score"] = _priority_score(
                    target["severity"], target["occurrence_count"], target["affected_user_count"]
                )
                target["updated_at"] = now
                aliases = {source_id}
                changed = True
                while changed:
                    changed = False
                    for candidate in self._memory_clusters.values():
                        candidate_id = str(candidate["id"])
                        merged_into_id = candidate.get("merged_into_id")
                        if merged_into_id and str(merged_into_id) in aliases and candidate_id not in aliases:
                            aliases.add(candidate_id)
                            changed = True
                for alias_id in aliases:
                    alias = self._memory_clusters.get(alias_id)
                    if alias is not None:
                        alias["merged_into_id"] = target_id
                        alias["updated_at"] = now
                return _copy_cluster(target)
        with store.engine.begin() as conn:
            conn.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": QUALITY_CLUSTER_MERGE_ADVISORY_LOCK})
            source = conn.execute(
                text("SELECT * FROM quality_issue_clusters WHERE id=:id FOR UPDATE"), {"id": source_id}
            ).mappings().first()
            target = conn.execute(
                text("SELECT * FROM quality_issue_clusters WHERE id=:id FOR UPDATE"), {"id": target_id}
            ).mappings().first()
            if not source or not target or source.get("merged_into_id") or target.get("merged_into_id"):
                return None
            conn.execute(
                text("UPDATE quality_reports SET cluster_id=:target,updated_at=:now WHERE cluster_id=:source"),
                {"source": source_id, "target": target_id, "now": now},
            )
            conn.execute(
                text(
                    "INSERT INTO quality_cluster_users (cluster_id,user_id,first_seen_at,last_seen_at) "
                    "SELECT :target,user_id,first_seen_at,last_seen_at FROM quality_cluster_users WHERE cluster_id=:source "
                    "ON CONFLICT (cluster_id,user_id) DO UPDATE SET first_seen_at=LEAST(quality_cluster_users.first_seen_at,EXCLUDED.first_seen_at),"
                    "last_seen_at=GREATEST(quality_cluster_users.last_seen_at,EXCLUDED.last_seen_at)"
                ),
                {"source": source_id, "target": target_id},
            )
            conn.execute(
                text(
                    "INSERT INTO quality_cluster_devices (cluster_id,device_id,first_seen_at,last_seen_at) "
                    "SELECT :target,device_id,first_seen_at,last_seen_at FROM quality_cluster_devices WHERE cluster_id=:source "
                    "ON CONFLICT (cluster_id,device_id) DO UPDATE SET first_seen_at=LEAST(quality_cluster_devices.first_seen_at,EXCLUDED.first_seen_at),"
                    "last_seen_at=GREATEST(quality_cluster_devices.last_seen_at,EXCLUDED.last_seen_at)"
                ),
                {"source": source_id, "target": target_id},
            )
            conn.execute(
                text(
                    "INSERT INTO quality_cluster_versions (cluster_id,app_version,first_seen_at,last_seen_at) "
                    "SELECT :target,app_version,first_seen_at,last_seen_at FROM quality_cluster_versions WHERE cluster_id=:source "
                    "ON CONFLICT (cluster_id,app_version) DO UPDATE SET first_seen_at=LEAST(quality_cluster_versions.first_seen_at,EXCLUDED.first_seen_at),"
                    "last_seen_at=GREATEST(quality_cluster_versions.last_seen_at,EXCLUDED.last_seen_at)"
                ),
                {"source": source_id, "target": target_id},
            )
            occurrence_count = conn.execute(
                text("SELECT count(*) FROM quality_reports WHERE cluster_id=:id"), {"id": target_id}
            ).scalar_one()
            user_count = conn.execute(
                text("SELECT count(*) FROM quality_cluster_users WHERE cluster_id=:id"), {"id": target_id}
            ).scalar_one()
            device_count = conn.execute(
                text("SELECT count(*) FROM quality_cluster_devices WHERE cluster_id=:id"), {"id": target_id}
            ).scalar_one()
            version_count = conn.execute(
                text("SELECT count(*) FROM quality_cluster_versions WHERE cluster_id=:id"), {"id": target_id}
            ).scalar_one()
            severity = str(target["severity"])
            if not bool(target["severity_locked"]) and SEVERITY_RANK[str(source["severity"])] > SEVERITY_RANK[severity]:
                severity = str(source["severity"])
            priority = _priority_score(severity, int(occurrence_count), int(user_count))
            first_seen = min(target["first_seen_at"], source["first_seen_at"])
            last_seen = max(target["last_seen_at"], source["last_seen_at"])
            row = conn.execute(
                text(
                    "UPDATE quality_issue_clusters SET severity=:severity,priority_score=:priority,occurrence_count=:occurrences,"
                    "affected_user_count=:users,affected_device_count=:devices,affected_version_count=:versions,"
                    "first_seen_at=:first_seen,last_seen_at=:last_seen,updated_at=:now WHERE id=:id RETURNING *"
                ),
                {
                    "id": target_id,
                    "severity": severity,
                    "priority": priority,
                    "occurrences": occurrence_count,
                    "users": user_count,
                    "devices": device_count,
                    "versions": version_count,
                    "first_seen": first_seen,
                    "last_seen": last_seen,
                    "now": now,
                },
            ).mappings().first()
            conn.execute(
                text(
                    "WITH RECURSIVE aliases AS ("
                    " SELECT id FROM quality_issue_clusters WHERE id=:source"
                    " UNION ALL"
                    " SELECT q.id FROM quality_issue_clusters q JOIN aliases a ON q.merged_into_id=a.id"
                    ") UPDATE quality_issue_clusters SET merged_into_id=:target,updated_at=:now"
                    " WHERE id IN (SELECT id FROM aliases) AND id<>:target"
                ),
                {"source": source_id, "target": target_id, "now": now},
            )
        return dict(row) if row else None


repository = QualityReportRepository()


def _assert_safe_string(value: str) -> None:
    for pattern in SECRET_VALUE_PATTERNS:
        if pattern.search(value):
            raise ValueError("diagnostic payload appears to contain a secret")


def _normalized_text_tokens(value: str) -> list[str]:
    tokens = [token for token in re.findall(r"[a-z0-9]{3,}", value.lower()) if token not in TEXT_STOP_WORDS]
    return sorted(set(tokens))[:16]


def _issue_identity(payload: QualityReportCreate) -> tuple[str, str, str]:
    strong_event: DiagnosticEvent | None = None
    if payload.diagnostics:
        for event in reversed(payload.diagnostics.events):
            if event.error_code or event.level == "ERROR" or event.event in {"UNCAUGHT_EXCEPTION", "PREVIOUS_PROCESS_EXIT"}:
                strong_event = event
                break
    if strong_event:
        raw_signature = "|".join(
            [
                payload.category,
                "DIAGNOSTIC",
                strong_event.component.upper(),
                strong_event.event.upper(),
                (strong_event.error_code or strong_event.exception_class or strong_event.result).upper(),
            ]
        )
        signature_kind = "DIAGNOSTIC"
    else:
        tokens = _normalized_text_tokens(payload.title)
        if len(tokens) < 3:
            tokens = _normalized_text_tokens(payload.title + " " + payload.description[:600])
        raw_signature = "|".join([payload.category, "TEXT", *tokens])
        signature_kind = "TEXT"
    fingerprint = hashlib.sha256(raw_signature.encode("utf-8")).hexdigest()
    return fingerprint, signature_kind, _infer_severity(payload, strong_event)


def _infer_severity(payload: QualityReportCreate, event: DiagnosticEvent | None) -> str:
    if event:
        combined = f"{event.event} {event.error_code or ''} {event.exception_class or ''}".upper()
        if any(token in combined for token in ("UNCAUGHT", "CRASH", "ANR", "PROCESS_EXIT", "SECURITY", "INTEGRITY")):
            return "CRITICAL"
        if payload.category == "SECURITY_PRIVACY":
            return "HIGH"
        if event.level in {"ERROR", "WARN"} and payload.category in {
            "FUNCTIONALITY", "GAME_INTEGRATION", "ACCESSIBILITY", "VOICE_AUDIO", "PERFORMANCE"
        }:
            return "HIGH"
    if payload.category in {"FUNCTIONALITY", "GAME_INTEGRATION", "ACCESSIBILITY", "VOICE_AUDIO", "PERFORMANCE", "SECURITY_PRIVACY"}:
        return "MEDIUM"
    if payload.category == "DESIGN":
        return "LOW"
    return "MEDIUM"


def _priority_score(severity: str, occurrence_count: int, affected_user_count: int) -> int:
    base = {"CRITICAL": 70, "HIGH": 50, "MEDIUM": 30, "LOW": 15}[severity]
    recurrence = min(15, int(round(4 * math.log2(max(1, occurrence_count)))))
    breadth = min(15, int(round(4 * math.log2(max(1, affected_user_count)))))
    return min(100, base + recurrence + breadth)


def _copy_cluster(cluster: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in cluster.items() if not key.startswith("_")}


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
        "problem_group_id": record.get("cluster_id"),
        "inferred_severity": record.get("inferred_severity"),
        "related_report_count": record.get("cluster_occurrence_count"),
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
    result["issue_fingerprint"] = record.get("issue_fingerprint")
    return result


def _admin_cluster(record: dict[str, Any], *, include_reports: bool) -> dict[str, Any]:
    result = {
        "id": str(record["id"]),
        "fingerprint": record["fingerprint"],
        "signature_kind": record["signature_kind"],
        "category": record["category"],
        "canonical_title": record["canonical_title"],
        "severity": record["severity"],
        "severity_locked": bool(record["severity_locked"]),
        "status": record["status"],
        "priority_score": int(record["priority_score"]),
        "occurrence_count": int(record["occurrence_count"]),
        "affected_user_count": int(record["affected_user_count"]),
        "affected_device_count": int(record["affected_device_count"]),
        "affected_version_count": int(record["affected_version_count"]),
        "first_seen_at": _iso(record["first_seen_at"]),
        "last_seen_at": _iso(record["last_seen_at"]),
        "last_app_version": record.get("last_app_version"),
        "last_source_sha": record.get("last_source_sha"),
        "merged_into_id": str(record["merged_into_id"]) if record.get("merged_into_id") else None,
        "created_at": _iso(record["created_at"]),
        "updated_at": _iso(record["updated_at"]),
    }
    if include_reports:
        result["reports"] = [_admin_report(item, include_diagnostics=False) for item in record.get("reports", [])]
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


@router.get("/v1/admin/quality/clusters")
def admin_list_quality_clusters(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    category: str | None = Query(default=None),
    x_sentinel_admin_token: str | None = Header(default=None, alias="X-Sentinel-Admin-Token"),
) -> dict[str, Any]:
    _, _, _, _, store = _security_context()
    require_admin(x_sentinel_admin_token, request, store)
    if status is not None and status not in REPORT_STATUSES:
        raise HTTPException(status_code=400, detail="QUALITY_CLUSTER_STATUS_INVALID")
    if severity is not None and severity not in CLUSTER_SEVERITIES:
        raise HTTPException(status_code=400, detail="QUALITY_CLUSTER_SEVERITY_INVALID")
    clusters = repository.list_clusters(store, limit=limit, status=status, severity=severity, category=category)
    return {"clusters": [_admin_cluster(item, include_reports=False) for item in clusters]}


@router.get("/v1/admin/quality/clusters/{cluster_id}")
def admin_get_quality_cluster(
    cluster_id: str,
    request: Request,
    x_sentinel_admin_token: str | None = Header(default=None, alias="X-Sentinel-Admin-Token"),
) -> dict[str, Any]:
    _, _, _, _, store = _security_context()
    require_admin(x_sentinel_admin_token, request, store)
    cluster = repository.get_cluster(store, cluster_id, include_reports=True)
    if not cluster:
        raise HTTPException(status_code=404, detail="QUALITY_CLUSTER_NOT_FOUND")
    return {"cluster": _admin_cluster(cluster, include_reports=True)}


@router.post("/v1/admin/quality/clusters/{cluster_id}")
def admin_update_quality_cluster(
    cluster_id: str,
    payload: QualityClusterUpdate,
    request: Request,
    x_sentinel_admin_token: str | None = Header(default=None, alias="X-Sentinel-Admin-Token"),
) -> dict[str, Any]:
    _, _, _, _, store = _security_context()
    require_admin(x_sentinel_admin_token, request, store)
    cluster = repository.update_cluster(store, cluster_id, status=payload.status, severity=payload.severity)
    if not cluster:
        raise HTTPException(status_code=404, detail="QUALITY_CLUSTER_NOT_FOUND")
    store.add_audit(
        {
            "actor_user_id": None,
            "actor_device_id": None,
            "action": "quality:cluster:update",
            "resource": f"quality-cluster:{cluster_id}",
            "decision": "ALLOW",
            "reason_code": payload.status or payload.severity or "UPDATED",
            "request_id": None,
        }
    )
    return {"cluster": _admin_cluster(cluster, include_reports=False)}


@router.post("/v1/admin/quality/clusters/{cluster_id}/merge")
def admin_merge_quality_cluster(
    cluster_id: str,
    payload: QualityClusterMerge,
    request: Request,
    x_sentinel_admin_token: str | None = Header(default=None, alias="X-Sentinel-Admin-Token"),
) -> dict[str, Any]:
    _, _, _, _, store = _security_context()
    require_admin(x_sentinel_admin_token, request, store)
    try:
        cluster = repository.merge_cluster(store, cluster_id, payload.target_cluster_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="QUALITY_CLUSTER_MERGE_INVALID") from exc
    if not cluster:
        raise HTTPException(status_code=404, detail="QUALITY_CLUSTER_NOT_FOUND")
    store.add_audit(
        {
            "actor_user_id": None,
            "actor_device_id": None,
            "action": "quality:cluster:merge",
            "resource": f"quality-cluster:{cluster_id}",
            "decision": "ALLOW",
            "reason_code": f"MERGED_INTO:{payload.target_cluster_id}",
            "request_id": None,
        }
    )
    return {"cluster": _admin_cluster(cluster, include_reports=False)}
