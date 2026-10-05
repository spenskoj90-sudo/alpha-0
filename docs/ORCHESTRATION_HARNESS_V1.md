# SENTINEL Orchestration Harness v1

**Status:** ACTIVE FOUNDATION  
**Tracking:** #379  
**Authority:** `AI_ORCHESTRATION_OPERATING_SYSTEM.md`

The repository now contains a small fail-closed orchestration entrypoint at
`scripts/sentinel_orchestration.py`. It turns the lane contract into executable
repository evidence without granting a secondary worker integration authority.

## Lane manifest

`sentinel.orchestration-lanes.v1` requires every lane to declare:

- exact base SHA;
- read-only or write mode;
- owned paths;
- acceptance checks;
- dependencies;
- for write lanes, an isolated worktree and non-`main` branch.

Duplicate mutable worktrees, repository/base-SHA drift, unknown or cyclic dependencies and arbitrary
readers fail validation. The local v1 runner deliberately refuses to execute
write lanes. Write workers remain the responsibility of the supervised
orchestrator and must integrate serially through the existing exact-SHA merge gate.

## Executable read-only pass

The bundled example contains two independent read-only lanes. Run:

```bash
python scripts/sentinel_orchestration.py run \
  --manifest automation/orchestration-lanes.example.json \
  --output orchestration-run.json
```

The runner uses at most two parallel workers and emits one
`sentinel.orchestration-run.v1` result with per-lane duration, repository-file
digests, the canonical acceptance issue list and bounded run telemetry. It does
not invoke a shell, mutate Git, call providers, expose credentials or merge.

The example manifest is pinned to its implementation base SHA as evidence of
the lane contract. A new real task should generate a fresh manifest from current
protected `main`; do not silently rewrite historical run manifests to HEAD.

## Telemetry boundary

v1 records wall-clock duration, retries, merge conflicts, CI reruns, Owner
interventions and token/credit use when available. Unknown token/credit data is
`null`, never estimated.

This closes only the executable read-only decomposition/synthesis foundation of
#379. External subagent launch adapters, supervised isolated write-worker
execution and measured single-agent versus multi-agent comparisons remain open.
Production credentials, signing, release publication and live deployment remain
outside this harness.
