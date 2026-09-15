from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from app.core.quality_api import QualityReportCreate, _issue_identity, repository

pytestmark = pytest.mark.postgres


def _payload(title: str) -> QualityReportCreate:
    return QualityReportCreate(
        category="FUNCTIONALITY",
        title=title,
        description="PostgreSQL quality-cluster concurrency regression evidence.",
        diagnostics_consent=False,
        quality_program_opt_in=True,
    )


def _principal(user_id: str) -> SimpleNamespace:
    return SimpleNamespace(user_id=user_id, device_id=None)


def _cleanup_fingerprint(store, fingerprint: str) -> None:
    with store.engine.begin() as conn:
        conn.execute(text("DELETE FROM quality_reports WHERE issue_fingerprint=:fingerprint"), {"fingerprint": fingerprint})
        conn.execute(text("DELETE FROM quality_issue_clusters WHERE fingerprint=:fingerprint"), {"fingerprint": fingerprint})


def test_postgres_same_fingerprint_converges_without_lost_counts_under_concurrency() -> None:
    from app.core.store import PostgresStore
    from app.main import store

    assert isinstance(store, PostgresStore)
    payload = _payload("Concurrent cluster convergence sentinel regression")
    fingerprint, _, _ = _issue_identity(payload)
    _cleanup_fingerprint(store, fingerprint)

    def create(index: int) -> dict:
        return repository.create(store, _principal(f"pg-quality-concurrent-{index}"), payload)

    total = 24
    with ThreadPoolExecutor(max_workers=12) as executor:
        reports = list(executor.map(create, range(total)))

    cluster_ids = {report["cluster_id"] for report in reports}
    assert len(cluster_ids) == 1
    cluster_id = next(iter(cluster_ids))

    with store.engine.connect() as conn:
        cluster = conn.execute(
            text("SELECT * FROM quality_issue_clusters WHERE id=:id"), {"id": cluster_id}
        ).mappings().one()
        report_count = conn.execute(
            text("SELECT count(*) FROM quality_reports WHERE cluster_id=:id"), {"id": cluster_id}
        ).scalar_one()
        user_count = conn.execute(
            text("SELECT count(*) FROM quality_cluster_users WHERE cluster_id=:id"), {"id": cluster_id}
        ).scalar_one()
        fingerprint_cluster_count = conn.execute(
            text("SELECT count(*) FROM quality_issue_clusters WHERE fingerprint=:fingerprint"),
            {"fingerprint": fingerprint},
        ).scalar_one()

    assert fingerprint_cluster_count == 1
    assert report_count == total
    assert user_count == total
    assert int(cluster["occurrence_count"]) == total
    assert int(cluster["affected_user_count"]) == total


def test_postgres_chained_merge_flattens_aliases_and_routes_future_ingest_to_root() -> None:
    from app.core.store import PostgresStore
    from app.main import store

    assert isinstance(store, PostgresStore)
    payload_a = _payload("Postgres alias chain alpha regression")
    payload_b = _payload("Postgres alias chain beta regression")
    payload_c = _payload("Postgres alias chain gamma regression")
    fingerprints = [_issue_identity(payload)[0] for payload in (payload_a, payload_b, payload_c)]
    for fingerprint in fingerprints:
        _cleanup_fingerprint(store, fingerprint)

    first = repository.create(store, _principal("pg-quality-chain-1"), payload_a)
    second = repository.create(store, _principal("pg-quality-chain-2"), payload_b)
    third = repository.create(store, _principal("pg-quality-chain-3"), payload_c)
    first_id = first["cluster_id"]
    second_id = second["cluster_id"]
    root_id = third["cluster_id"]

    assert repository.merge_cluster(store, first_id, second_id) is not None
    merged = repository.merge_cluster(store, second_id, root_id)
    assert merged is not None
    assert str(merged["id"]) == root_id

    routed = repository.create(store, _principal("pg-quality-chain-4"), payload_a)
    assert routed["cluster_id"] == root_id
    assert routed["cluster_occurrence_count"] == 4

    with store.engine.connect() as conn:
        aliases = conn.execute(
            text("SELECT id, merged_into_id FROM quality_issue_clusters WHERE id IN (:a,:b) ORDER BY id"),
            {"a": first_id, "b": second_id},
        ).mappings().all()
        root = conn.execute(
            text("SELECT occurrence_count, affected_user_count FROM quality_issue_clusters WHERE id=:id"),
            {"id": root_id},
        ).mappings().one()
        report_count = conn.execute(
            text("SELECT count(*) FROM quality_reports WHERE cluster_id=:id"), {"id": root_id}
        ).scalar_one()

    assert len(aliases) == 2
    assert all(str(alias["merged_into_id"]) == root_id for alias in aliases)
    assert report_count == 4
    assert int(root["occurrence_count"]) == 4
    assert int(root["affected_user_count"]) == 4
