#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SHA40 = re.compile(r"^[0-9a-f]{40}$")
READERS = {"repository_contract", "acceptance_contract"}
MAX_LANES = 8
MAX_OWNED_PATHS = 32
MAX_EVIDENCE_BYTES = 2 * 1024 * 1024

class ManifestError(ValueError):
    pass

def validate_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(manifest, dict) or manifest.get("schema") != "sentinel.orchestration-lanes.v1":
        raise ManifestError("unsupported manifest schema")
    base = manifest.get("baseSha")
    if not isinstance(base, str) or not SHA40.fullmatch(base):
        raise ManifestError("baseSha must be an exact lowercase SHA")
    lanes = manifest.get("lanes")
    if not isinstance(lanes, list) or not 1 <= len(lanes) <= MAX_LANES:
        raise ManifestError("lanes must contain 1..8 entries")
    ids, worktrees = set(), set()
    for lane in lanes:
        if not isinstance(lane, dict):
            raise ManifestError("each lane must be an object")
        lane_id = lane.get("id")
        if not isinstance(lane_id, str) or not lane_id or lane_id != lane_id.strip() or lane_id in ids:
            raise ManifestError("lane ids must be non-empty and unique")
        ids.add(lane_id)
        if lane.get("baseSha") != base:
            raise ManifestError(f"lane {lane_id} baseSha must equal manifest baseSha")
        mode = lane.get("mode")
        if mode not in ("read_only", "write"):
            raise ManifestError(f"lane {lane_id} has invalid mode")
        for key in ("ownedPaths", "acceptanceChecks"):
            value = lane.get(key)
            if not isinstance(value, list) or not value or not all(isinstance(x, str) and x for x in value):
                raise ManifestError(f"lane {lane_id} requires {key}")
        for path in lane["ownedPaths"]:
            if (PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts
                    or str(PurePosixPath(path)) != path or path == "." or "\x00" in path):
                raise ManifestError(f"lane {lane_id} requires canonical repository-relative paths")
        if len(lane["ownedPaths"]) > MAX_OWNED_PATHS:
            raise ManifestError(f"lane {lane_id} exceeds the evidence file count limit")
        deps = lane.get("dependencies", [])
        if not isinstance(deps, list) or not all(isinstance(x, str) and x for x in deps):
            raise ManifestError(f"lane {lane_id} has invalid dependencies")
        if mode == "read_only":
            if not isinstance(lane.get("reader"), str) or lane["reader"] not in READERS:
                raise ManifestError(f"lane {lane_id} uses an unapproved reader")
            if lane.get("worktree") not in (None, "", "."):
                raise ManifestError(f"read-only lane {lane_id} must use repository snapshot")
        else:
            worktree = lane.get("worktree")
            branch = lane.get("branch")
            if (not isinstance(worktree, str) or not worktree.strip()
                    or not isinstance(branch, str) or not branch.strip()
                    or branch != branch.strip() or branch in ("main", "refs/heads/main")):
                raise ManifestError(f"write lane {lane_id} requires isolated worktree and non-main branch")
            resolved = (ROOT / worktree).resolve()
            if resolved == ROOT or ROOT in resolved.parents or resolved in ROOT.parents:
                raise ManifestError("write lanes must be outside the shared repository")
            if any(resolved == other or resolved in other.parents or other in resolved.parents
                   for other in worktrees):
                raise ManifestError("write lanes cannot share a mutable worktree")
            worktrees.add(resolved)
    graph: dict[str, set[str]] = {}
    for lane in lanes:
        deps = set(lane.get("dependencies", []))
        if lane["id"] in deps or not deps.issubset(ids):
            raise ManifestError(f"lane {lane['id']} has invalid dependencies")
        graph[lane["id"]] = deps
    visiting, visited = set(), set()
    def visit(lane_id: str) -> None:
        if lane_id in visiting:
            raise ManifestError("lane dependencies must form an acyclic graph")
        if lane_id in visited:
            return
        visiting.add(lane_id)
        for dep in graph[lane_id]:
            visit(dep)
        visiting.remove(lane_id)
        visited.add(lane_id)
    for lane_id in graph:
        visit(lane_id)
    return lanes

def _snapshot_file(base_sha: str, relative: str) -> bytes:
    """Read committed regular-file bytes, never working-tree or symlink contents."""
    try:
        entry = subprocess.run(
            ["git", "--no-replace-objects", "ls-tree", "-z", base_sha, "--", relative], cwd=ROOT,
            check=True, capture_output=True, timeout=5,
        ).stdout
        metadata, separator, name = entry.rstrip(b"\x00").partition(b"\t")
        fields = metadata.split()
        if (not separator or name != relative.encode("utf-8") or len(fields) != 3
                or fields[0] not in (b"100644", b"100755") or fields[1] != b"blob"):
            raise ManifestError(f"committed regular evidence file missing: {relative}")
        object_sha = fields[2].decode("ascii")
        size = int(subprocess.run(
            ["git", "--no-replace-objects", "cat-file", "-s", object_sha], cwd=ROOT,
            check=True, capture_output=True, text=True, timeout=5,
        ).stdout.strip())
        if size > MAX_EVIDENCE_BYTES:
            raise ManifestError(f"source evidence exceeds the byte limit: {relative}")
        return subprocess.run(
            ["git", "--no-replace-objects", "cat-file", "blob", object_sha], cwd=ROOT,
            check=True, capture_output=True, timeout=5,
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise ManifestError(f"unable to read source evidence: {relative}") from exc

def _digests(base_sha: str, paths: list[str]) -> dict[str, str]:
    result = {}
    for relative in paths:
        result[relative] = hashlib.sha256(_snapshot_file(base_sha, relative)).hexdigest()
    return result

def _run_lane(lane: dict[str, Any]) -> dict[str, Any]:
    started = time.monotonic()
    result: dict[str, Any] = {"reader": lane["reader"], "digests": _digests(lane["baseSha"], lane["ownedPaths"])}
    if lane["reader"] == "acceptance_contract":
        tasks = _snapshot_file(lane["baseSha"], "docs/TASKS.md").decode("utf-8")
        result["activeAcceptanceIssues"] = sorted({int(x) for x in re.findall(r"- \[ \] \*\*#(\d+)", tasks)})
    return {"id": lane["id"], "mode": "read_only", "status": "SUCCESS",
            "durationMs": round((time.monotonic() - started) * 1000, 3), "result": result}

def _repository_head() -> str:
    try:
        return subprocess.run(
            ["git", "--no-replace-objects", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True, timeout=5,
        ).stdout.strip().lower()
    except (OSError, subprocess.SubprocessError) as exc:
        raise ManifestError("unable to resolve repository HEAD") from exc

def run(manifest: dict[str, Any]) -> dict[str, Any]:
    lanes = validate_manifest(manifest)
    if _repository_head() != manifest["baseSha"]:
        raise ManifestError("repository HEAD must equal manifest baseSha")
    if any(lane["mode"] == "write" for lane in lanes):
        raise ManifestError("local harness refuses write-lane execution; supervised isolated workers are required")
    started = time.monotonic()
    workers = min(2, len(lanes))
    results = []
    remaining = list(lanes)
    completed = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        while remaining:
            ready = [lane for lane in remaining if set(lane.get("dependencies", [])).issubset(completed)]
            wave = list(pool.map(_run_lane, ready))
            results.extend(wave)
            completed.update(lane["id"] for lane in ready)
            remaining = [lane for lane in remaining if lane["id"] not in completed]
    return {
        "schema": "sentinel.orchestration-run.v1", "baseSha": manifest["baseSha"],
        "status": "SUCCESS", "laneCount": len(results), "parallelWorkers": workers,
        "wallClockMs": round((time.monotonic() - started) * 1000, 3),
        "metrics": {"retries": 0, "mergeConflicts": 0, "ciReruns": 0,
                    "ownerInterventions": 0, "tokenOrCreditUse": None},
        "lanes": results,
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    command = parser.add_subparsers(dest="command", required=True).add_parser("run")
    command.add_argument("--manifest", required=True, type=Path)
    command.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        payload = run(manifest)
    except (OSError, json.JSONDecodeError, ManifestError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "lanes": payload["laneCount"], "output": str(args.output)}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
