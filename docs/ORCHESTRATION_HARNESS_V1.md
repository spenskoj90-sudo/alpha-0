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

The bundled example contains two independent read-only lanes and preserves a
historical base SHA. First create a new task manifest for the exact checked-out
candidate (after resolving it from protected main), then run:

```bash
python - <<'PY'
import json
import subprocess
from pathlib import Path
manifest = json.loads(Path("automation/orchestration-lanes.example.json").read_text())
sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
manifest["baseSha"] = sha
for lane in manifest["lanes"]:
    lane["baseSha"] = sha
Path("orchestration-task.json").write_text(json.dumps(manifest, indent=2) + "\n")
PY
python scripts/sentinel_orchestration.py run \
  --manifest orchestration-task.json \
  --output orchestration-run.json
```

The runner uses at most two parallel workers and emits one
`sentinel.orchestration-run.v1` result with per-lane duration, repository-file
digests, the canonical acceptance issue list and bounded run telemetry. Evidence
comes from regular Git blobs at the exact SHA, so uncommitted changes, untracked
files, symlinks and Git replacement refs cannot be substituted for committed
source. Each lane declares at most 32 evidence files, with a 2 MiB limit per
committed blob checked before reading its contents. Dependencies
complete before their consumers start. The runner invokes bounded read-only Git
commands without a shell; it does not mutate Git, call providers or merge.

`SUCCESS` means the approved evidence readers completed. `acceptanceChecks` are
declared task criteria, not arbitrary commands executed by this runner; source
digests do not establish build, runtime, physical or release acceptance.
`bash verify.sh` runs the harness regression suite using disposable Git fixtures,
including stale source, dirty checkout, dependency ordering and write isolation.

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
