# SENTINEL — Autonomous Operating Playbook

**Tracking issue:** #167  
**Status:** PROPOSED — pending Human Owner approval.  
**Canonical contract:** `docs/WORKFLOW_CONTRACT.md`

## 1. Roles

### Human Owner

Final authority for product direction, protected repository actions, production environments, credentials/secrets/signing material, releases, irreversible operations and final acceptance.

### GPT / ChatGPT

Sole AI engineering participant and executor. GPT owns the normal engineering lifecycle: discovery, architecture, implementation, testing, security analysis, CI analysis, review, documentation, PR preparation, regression repair and technical integration.

### Other AI systems

No engineering role. GPT does not delegate engineering, review, security, testing, research, architecture or integration to other AI systems.

## 2. Start-of-task protocol

Before substantive work GPT must:

1. inspect current `main` HEAD;
2. inspect the issue and acceptance criteria;
3. inspect relevant open PRs/branches;
4. read `docs/TASKS.md`;
5. read `docs/SENTINEL_CURRENT_STATE.md`;
6. read `docs/WORKFLOW_CONTRACT.md`;
7. read `docs/RELEASE_GATES.md` and `docs/SENTINEL_EVIDENCE_PROTOCOL.md` when relevant;
8. identify protected actions and external dependencies;
9. establish the exact baseline SHA.

## 3. Autonomous execution protocol

```text
1. DISCOVER
2. BASELINE
3. PLAN
4. IMPLEMENT
5. TEST
6. DIAGNOSE/FIX if needed
7. REVIEW
8. COMMIT
9. PUSH / PR
10. CI
11. ANALYZE CI
12. FIX + CI again if needed
13. VERIFY exact-SHA evidence
14. PREPARE READY state
15. OWNER GATE when required
16. RECONCILE main after merge
17. NEXT TASK
```

GPT should keep moving through this loop rather than stopping after a single implementation pass.

## 4. Scope

One issue should map to one logical change set and one PR. Use predictable branches:

`<type>/<short-description>-<issue-number>`

No direct push or force-push to `main`. No unrelated cleanup inside an active task.

## 5. Verification

For every material success claim preserve:

- exact commit SHA;
- workflow/check name;
- numeric Run ID;
- conclusion/result;
- artifact/log reference when required.

`PASS` without exact evidence is not acceptance. A different SHA is not evidence for the current SHA.

## 6. Failure handling

A failed check triggers diagnosis and repair. GPT should:

- inspect the failing job/log;
- determine whether the failure is code, test, environment, dependency, permission or infrastructure related;
- fix only the root cause within scope;
- rerun the relevant checks;
- re-review the changed diff;
- update the evidence trail.

Do not weaken gates or conceal failures merely to obtain a green result.

## 7. Protected actions

GPT must stop before:

- production secret/credential access or mutation;
- release signing-key/certificate custody changes;
- branch-protection changes;
- irreversible destructive repository/database operations;
- production/live deployment;
- publishing a release tag/GitHub Release;
- material product-direction decisions not resolvable from the approved requirements.

**Merge into `main` remains an Owner gate under the proposed policy.** GPT prepares the PR and evidence; the Owner performs the merge.

## 8. External dependencies

When a task depends on an external service, GPT records the dependency and exact blocker. Missing operator permissions are not treated as implementation defects. Never expose secret values in issues, commits, PRs or evidence.

## 9. Documentation

Repository documentation is the durable institutional record. Update the authoritative document whenever a process, security invariant, architecture fact, release gate or current-state fact changes.

Minimum routing:

- roles → `docs/AI_ROLES.md`;
- engineering process → `docs/WORKFLOW_CONTRACT.md` + this file;
- permissions/tools → `docs/AUTONOMOUS_PERMISSIONS.md`;
- current state → `docs/SENTINEL_CURRENT_STATE.md`;
- CI/release gates → `docs/RELEASE_GATES.md`;
- evidence semantics → `docs/SENTINEL_EVIDENCE_PROTOCOL.md`;
- repository orientation → `README.md`.

## 10. Conflict resolution

Git state and exact CI evidence outrank conversation memory. `main` outranks unmerged branches for current product state. Canonical contracts outrank informal notes. Unknown or contradictory facts remain `UNVERIFIED`.
