from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.core.quality_api import (
    QualityReportCreate,
    QualityReportRepository,
)


class MemoryStore:
    pass


def _principal(user: str, device: str | None = None):
    return SimpleNamespace(user_id=user, device_id=device)


def _report(
    *,
    category: str = "OTHER",
    title: str = "Distinct bounded report title",
    description: str = "Bounded report description with enough context",
    diagnostics=None,
):
    return QualityReportCreate(
        category=category,
        title=title,
        description=description,
        diagnostics_consent=diagnostics is not None,
        quality_program_opt_in=True,
        diagnostics=diagnostics,
    )


def _create(repo: QualityReportRepository, user: str, *, device: str | None = None, **kwargs):
    return repo.create(MemoryStore(), _principal(user, device), _report(**kwargs))


def test_memory_prune_drops_only_expired_retained_diagnostics() -> None:
    repo = QualityReportRepository()
    now = datetime.now(UTC)
    repo._memory = {
        "expired": {
            "diagnostics_expires_at": now - timedelta(seconds=1),
            "diagnostics": {"x": 1},
            "diagnostics_bytes": 10,
        },
        "live": {
            "diagnostics_expires_at": now + timedelta(seconds=60),
            "diagnostics": {"x": 1},
            "diagnostics_bytes": 10,
        },
        "already-empty": {
            "diagnostics_expires_at": now - timedelta(seconds=1),
            "diagnostics": None,
            "diagnostics_bytes": 0,
        },
    }
    repo._prune_memory()
    assert repo._memory["expired"]["diagnostics"] is None
    assert repo._memory["expired"]["diagnostics_bytes"] == 0
    assert repo._memory["live"]["diagnostics"] == {"x": 1}
    assert repo._memory["already-empty"]["diagnostics"] is None


def test_memory_root_resolution_flattens_aliases_and_detects_missing_target_and_cycle() -> None:
    repo = QualityReportRepository()
    root = {"id": "root", "merged_into_id": None}
    middle = {"id": "middle", "merged_into_id": "root"}
    leaf = {"id": "leaf", "merged_into_id": "middle"}
    repo._memory_clusters = {"root": root, "middle": middle, "leaf": leaf}

    assert repo._resolve_memory_root(leaf) is root
    assert leaf["merged_into_id"] == "root"
    assert middle["merged_into_id"] == "root"

    missing = {"id": "missing-alias", "merged_into_id": "absent"}
    repo._memory_clusters["missing-alias"] = missing
    with pytest.raises(RuntimeError, match="target missing"):
        repo._resolve_memory_root(missing)

    a = {"id": "a", "merged_into_id": "b"}
    b = {"id": "b", "merged_into_id": "a"}
    repo._memory_clusters.update({"a": a, "b": b})
    with pytest.raises(RuntimeError, match="cycle or excessive depth"):
        repo._resolve_memory_root(a)


def test_memory_create_tracks_distinct_users_devices_versions_and_escalates_unlocked_severity() -> None:
    repo = QualityReportRepository()
    first = _create(
        repo,
        "u1",
        device="d1",
        category="DESIGN",
        title="Visual spacing differs on settings page",
        description="Spacing differs on settings page on first render",
    )
    cluster_id = first["cluster_id"]
    cluster = repo._memory_clusters[cluster_id]
    assert cluster["severity"] == "LOW"
    assert cluster["affected_user_count"] == 1
    assert cluster["affected_device_count"] == 1

    # Force a second report into the same fingerprint while exercising escalation.
    record = {
        **repo._memory[first["id"]],
        "id": "manual-second",
        "user_id": "u2",
        "device_id": "d2",
        "inferred_severity": "HIGH",
        "created_at": datetime.now(UTC) + timedelta(seconds=1),
        "updated_at": datetime.now(UTC) + timedelta(seconds=1),
    }
    created = repo._create_memory(record, "TEXT", "2.0.0", "b" * 40)
    assert created["cluster_id"] == cluster_id
    assert cluster["severity"] == "HIGH"
    assert cluster["occurrence_count"] == 2
    assert cluster["affected_user_count"] == 2
    assert cluster["affected_device_count"] == 2
    assert cluster["affected_version_count"] == 1
    assert cluster["last_app_version"] == "2.0.0"
    assert cluster["last_source_sha"] == "b" * 40


def test_memory_create_respects_locked_severity_and_preserves_last_nonempty_release_identity() -> None:
    repo = QualityReportRepository()
    first = _create(repo, "u1", category="DESIGN")
    cluster = repo._memory_clusters[first["cluster_id"]]
    cluster["severity"] = "LOW"
    cluster["severity_locked"] = True
    cluster["last_app_version"] = "1.0.0"
    cluster["last_source_sha"] = "a" * 40

    record = {
        **repo._memory[first["id"]],
        "id": "second",
        "user_id": "u2",
        "device_id": None,
        "inferred_severity": "CRITICAL",
        "created_at": datetime.now(UTC) + timedelta(seconds=1),
        "updated_at": datetime.now(UTC) + timedelta(seconds=1),
    }
    repo._create_memory(record, "TEXT", None, None)
    assert cluster["severity"] == "LOW"
    assert cluster["last_app_version"] == "1.0.0"
    assert cluster["last_source_sha"] == "a" * 40
    assert cluster["affected_device_count"] == 0


def test_memory_create_evicts_oldest_report_at_capacity(monkeypatch) -> None:
    repo = QualityReportRepository()
    base = datetime.now(UTC) - timedelta(days=1)
    repo._memory = {
        str(i): {
            "id": str(i),
            "created_at": base + timedelta(seconds=i),
            "diagnostics_expires_at": None,
            "diagnostics": None,
            "diagnostics_bytes": 0,
        }
        for i in range(5000)
    }
    created = _create(repo, "u-new")
    assert len(repo._memory) == 5000
    assert "0" not in repo._memory
    assert created["id"] in repo._memory


def test_memory_get_list_and_status_update_cover_missing_filter_and_sort_paths() -> None:
    repo = QualityReportRepository()
    older = _create(repo, "u1", title="Alpha failure report", description="alpha details")
    newer = _create(repo, "u2", title="Beta failure report", description="beta details")
    repo._memory[older["id"]]["created_at"] -= timedelta(seconds=10)

    assert repo.get(MemoryStore(), "missing") is None
    assert repo.get(MemoryStore(), older["id"])["id"] == older["id"]
    assert [item["id"] for item in repo.list(MemoryStore(), limit=1)] == [newer["id"]]
    assert repo.list(MemoryStore(), limit=10, status="RESOLVED") == []

    assert repo.set_status(MemoryStore(), "missing", "RESOLVED") is None
    resolved = repo.set_status(MemoryStore(), older["id"], "RESOLVED")
    assert resolved["status"] == "RESOLVED"
    assert [item["id"] for item in repo.list(MemoryStore(), limit=10, status="RESOLVED")] == [older["id"]]


def test_memory_cluster_listing_filters_and_hides_merged_aliases() -> None:
    repo = QualityReportRepository()
    first = _create(repo, "u1", category="FUNCTIONALITY", title="Function alpha failure")
    second = _create(repo, "u2", category="DESIGN", title="Visual beta spacing")
    first_id, second_id = first["cluster_id"], second["cluster_id"]
    repo._memory_clusters[first_id]["status"] = "TRIAGED"
    repo._memory_clusters[first_id]["severity"] = "HIGH"
    repo._memory_clusters[second_id]["severity"] = "LOW"

    assert [x["id"] for x in repo.list_clusters(MemoryStore(), 10, status="TRIAGED")] == [first_id]
    assert [x["id"] for x in repo.list_clusters(MemoryStore(), 10, severity="LOW")] == [second_id]
    assert [x["id"] for x in repo.list_clusters(MemoryStore(), 10, category="DESIGN")] == [second_id]

    repo._memory_clusters[second_id]["merged_into_id"] = first_id
    assert second_id not in {x["id"] for x in repo.list_clusters(MemoryStore(), 10)}


def test_memory_get_cluster_optionally_includes_only_direct_member_reports() -> None:
    repo = QualityReportRepository()
    first = _create(repo, "u1", title="First unique issue")
    second = _create(repo, "u2", title="Second separate issue")
    assert repo.get_cluster(MemoryStore(), "missing") is None

    simple = repo.get_cluster(MemoryStore(), first["cluster_id"], include_reports=False)
    assert "reports" not in simple

    detailed = repo.get_cluster(MemoryStore(), first["cluster_id"], include_reports=True)
    assert [item["id"] for item in detailed["reports"]] == [first["id"]]
    assert all(item["id"] != second["id"] for item in detailed["reports"])


def test_memory_cluster_update_rejects_missing_or_merged_and_propagates_status() -> None:
    repo = QualityReportRepository()
    first = _create(repo, "u1", title="Same cluster report title", description="same cluster details")
    second = _create(repo, "u2", title="Same cluster report title", description="same cluster details")
    cluster_id = first["cluster_id"]

    assert repo.update_cluster(MemoryStore(), "missing", status="TRIAGED", severity=None) is None

    updated = repo.update_cluster(MemoryStore(), cluster_id, status="IN_PROGRESS", severity=None)
    assert updated["status"] == "IN_PROGRESS"
    assert repo._memory[first["id"]]["status"] == "IN_PROGRESS"
    assert repo._memory[second["id"]]["status"] == "IN_PROGRESS"
    assert updated["severity_locked"] is False

    updated = repo.update_cluster(MemoryStore(), cluster_id, status=None, severity="CRITICAL")
    assert updated["severity"] == "CRITICAL"
    assert updated["severity_locked"] is True

    repo._memory_clusters[cluster_id]["merged_into_id"] = "other"
    assert repo.update_cluster(MemoryStore(), cluster_id, status="RESOLVED", severity=None) is None


def test_memory_merge_validates_identity_missing_and_already_merged_states() -> None:
    repo = QualityReportRepository()
    first = _create(repo, "u1", title="First cluster issue")
    second = _create(repo, "u2", title="Second cluster issue")
    source, target = first["cluster_id"], second["cluster_id"]

    with pytest.raises(ValueError, match="must differ"):
        repo.merge_cluster(MemoryStore(), source, source)
    assert repo.merge_cluster(MemoryStore(), "missing", target) is None
    assert repo.merge_cluster(MemoryStore(), source, "missing") is None

    repo._memory_clusters[source]["merged_into_id"] = target
    assert repo.merge_cluster(MemoryStore(), source, target) is None


def test_memory_merge_combines_membership_time_severity_and_flattens_incoming_aliases() -> None:
    repo = QualityReportRepository()
    source_report = _create(repo, "source-user", device="source-device", category="FUNCTIONALITY", title="Source cluster issue")
    target_report = _create(repo, "target-user", device="target-device", category="DESIGN", title="Target cluster issue")
    source = source_report["cluster_id"]
    target = target_report["cluster_id"]

    source_cluster = repo._memory_clusters[source]
    target_cluster = repo._memory_clusters[target]
    source_cluster["severity"] = "HIGH"
    source_cluster["_versions"].add("1.0")
    source_cluster["affected_version_count"] = 1
    target_cluster["_versions"].add("2.0")
    target_cluster["affected_version_count"] = 1
    source_cluster["first_seen_at"] -= timedelta(hours=1)
    target_cluster["last_seen_at"] += timedelta(hours=1)

    alias = {
        **source_cluster,
        "id": "incoming-alias",
        "merged_into_id": source,
        "_users": set(),
        "_devices": set(),
        "_versions": set(),
    }
    repo._memory_clusters["incoming-alias"] = alias

    merged = repo.merge_cluster(MemoryStore(), source, target)
    assert merged["id"] == target
    assert merged["severity"] == "HIGH"
    assert merged["occurrence_count"] == 2
    assert merged["affected_user_count"] == 2
    assert merged["affected_device_count"] == 2
    assert merged["affected_version_count"] == 2
    assert repo._memory[source_report["id"]]["cluster_id"] == target
    assert repo._memory_clusters[source]["merged_into_id"] == target
    assert repo._memory_clusters["incoming-alias"]["merged_into_id"] == target


def test_memory_merge_does_not_override_locked_target_severity() -> None:
    repo = QualityReportRepository()
    source = _create(repo, "u1", category="FUNCTIONALITY", title="High source issue")["cluster_id"]
    target = _create(repo, "u2", category="DESIGN", title="Locked low target issue")["cluster_id"]
    repo._memory_clusters[source]["severity"] = "CRITICAL"
    repo._memory_clusters[target]["severity"] = "LOW"
    repo._memory_clusters[target]["severity_locked"] = True

    merged = repo.merge_cluster(MemoryStore(), source, target)
    assert merged["severity"] == "LOW"
