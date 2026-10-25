#!/usr/bin/env python3
"""Read-only, account-level GitHub Actions capacity estimate for Sentinel + Forma.

Uses the *existing* authenticated GitHub CLI, without requesting or logging tokens.
GitHub job wall time is NOT an invoice or a billed-minute ledger; check Billing UI.
No writes, secrets API access, build trigger, file download, or workspace mutation.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import subprocess
import sys
from collections import defaultdict

REPOS = ("spenskoj90-sudo/alpha-0", "spenskoj90-sudo/forma-fitness-android")
LIMIT = 2000
INTERNAL_TARGET = 1500

def api(path: str) -> object:
    proc = subprocess.run(
        ["gh", "api", "--method", "GET", path], capture_output=True, text=True, check=False,
    )
    if proc.returncode:
        raise RuntimeError("GitHub CLI request failed; confirm read-only login and permissions")
    return json.loads(proc.stdout)

def rounded_job_minutes(job: dict) -> int:
    try:
        start = dt.datetime.fromisoformat(job["started_at"].replace("Z", "+00:00"))
        end = dt.datetime.fromisoformat(job["completed_at"].replace("Z", "+00:00"))
        return math.ceil(max(0.0, (end - start).total_seconds()) / 60.0)
    except (ValueError, TypeError, KeyError, AttributeError):
        return 0

def sum_jobs(jobs: list[dict]) -> tuple[int, int, list[tuple[str, int]]]:
    rows = [(str(j.get("name", "unnamed")), rounded_job_minutes(j))
            for j in jobs if j.get("started_at") and j.get("completed_at")]
    return sum(m for _, m in rows), len(rows), rows

def collect(repo: str, count: int) -> list[dict]:
    result = api(f"repos/{repo}/actions/runs?per_page={count}&status=completed")
    runs = result.get("workflow_runs", [])
    out = []
    for run in runs:
        jobs_obj = api(f"repos/{repo}/actions/runs/{run['id']}/jobs?per_page=100")
        if jobs_obj.get("total_count", 0) > 100:
            # Avoid claiming completeness if pagination would omit jobs.
            raise RuntimeError("Run has >100 jobs; exact audit requires pagination")
        minutes, n_jobs, rows = sum_jobs(jobs_obj.get("jobs", []))
        out.append({
            "repo": repo,
            "name": run.get("name", "unknown"),
            "run_id": run["id"],
            "event": run.get("event"),
            "branch": run.get("head_branch"),
            "conclusion": run.get("conclusion"),
            "rounded_wall_minutes": minutes,
            "jobs": n_jobs,
            "slowest": sorted(rows, key=lambda x: x[1], reverse=True)[:3],
        })
    return out

def render(all_runs: list[dict], *, target: int = INTERNAL_TARGET) -> str:
    total = sum(r["rounded_wall_minutes"] for r in all_runs)
    grouped = defaultdict(lambda: {"runs":0, "minutes":0})
    for r in all_runs:
        key = (r["repo"], r["name"])
        grouped[key]["runs"] += 1
        grouped[key]["minutes"] += r["rounded_wall_minutes"]
    lines = [
        "CI CAPACITY ESTIMATE — read-only, NOT GitHub Billing",
        f"Sample: {len(all_runs)} recent completed workflow runs across {len(REPOS)} repositories",
        f"Rounded runner wall time of sampled jobs: {total} minutes (NOT billed minutes)",
        f"Internal target: {target} nominal minutes/month; Free account allowance: {LIMIT} included billed minutes/month",
        "Sample size and runner OS/pricing may differ from account-level billed-minute usage.",
        "A partial recent-run sample is NOT a full-month quota audit.",
        "Top observed workflow consumption:",
    ]
    for (repo, name), x in sorted(grouped.items(), key=lambda it: it[1]["minutes"], reverse=True)[:15]:
        lines.append(f"  {repo}: {name} — {x['minutes']} nominal min / {x['runs']} sampled runs")
    return "\n".join(lines)

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--last", type=int, default=10, help="Recent completed runs per repo, 1..30; read-only")
    a = p.parse_args()
    if not 1 <= a.last <= 30:
        p.error("--last must be from 1 to 30")
    result = []
    try:
        for repo in REPOS:
            result.extend(collect(repo, a.last))
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Read-only audit unavailable: {type(exc).__name__}. No data or settings changed.", file=sys.stderr)
        return 1
    print(render(result))
    print("Next: read GitHub Settings > Billing and licensing > Actions for ACTUAL billed usage, costs and budget limits.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
