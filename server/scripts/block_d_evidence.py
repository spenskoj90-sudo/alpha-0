from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from time import perf_counter

from app.core.operational_observability import BoundedOperationalRegistry, normalize_request_id
from app.core.operational_resilience import run_operational_failure_matrix


def _measure_ms(fn) -> float:
    started = perf_counter()
    fn()
    return round((perf_counter() - started) * 1000.0, 3)


def _evidence_sha() -> str:
    explicit = os.getenv("SENTINEL_EVIDENCE_SHA")
    if explicit:
        return explicit
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if event_path:
        try:
            event = json.loads(Path(event_path).read_text(encoding="utf-8"))
            head = event.get("pull_request", {}).get("head", {}).get("sha")
            if isinstance(head, str) and len(head) == 40:
                return head
        except (OSError, ValueError, TypeError):
            pass
    return os.getenv("GITHUB_SHA", "LOCAL")


def build_evidence() -> dict[str, object]:
    normalize_iterations = 20_000
    registry_iterations = 20_000
    snapshot_iterations = 500

    normalize_ms = _measure_ms(
        lambda: [normalize_request_id(f"ci-request-{index}") for index in range(normalize_iterations)]
    )

    registry = BoundedOperationalRegistry(max_series=32, latency_window=64, max_traces=64)

    def record_many() -> None:
        for index in range(registry_iterations):
            registry.record(
                component="ci-benchmark",
                operation=f"operation-{index % 8}",
                outcome="ok" if index % 5 else "degraded",
                elapsed_ms=float(index % 50),
            )

    registry_ms = _measure_ms(record_many)
    snapshot_ms = _measure_ms(lambda: [registry.snapshot() for _ in range(snapshot_iterations)])

    budgets = [
        {"operation": "normalize_request_id_20k", "observed_ms": normalize_ms, "budget_ms": 2_000.0},
        {"operation": "operational_registry_record_20k", "observed_ms": registry_ms, "budget_ms": 5_000.0},
        {"operation": "operational_registry_snapshot_500", "observed_ms": snapshot_ms, "budget_ms": 2_000.0},
    ]
    for item in budgets:
        item["passed"] = item["observed_ms"] <= item["budget_ms"]

    failure_matrix = [item.as_dict() for item in run_operational_failure_matrix()]
    return {
        "schema": "sentinel.block-d.evidence.v1",
        "evidence_scope": "ci-local-regression-guard-not-production-slo",
        "commit": _evidence_sha(),
        "budgets": budgets,
        "failure_injection": failure_matrix,
        "registry_capacity": registry.snapshot()["capacity"],
        "passed": all(item["passed"] for item in budgets) and all(item["passed"] for item in failure_matrix),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="block-d-evidence.json")
    args = parser.parse_args()
    evidence = build_evidence()
    path = Path(args.output)
    path.write_text(json.dumps(evidence, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(path.read_text(encoding="utf-8"))
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
