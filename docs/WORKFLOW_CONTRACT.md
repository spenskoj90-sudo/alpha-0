# SENTINEL — Autonomous Engineering Workflow Contract

**Tracking issue:** #167  
**Status:** ACTIVE — approved by Human Owner on 2026-09-06.  
**Authority:** Human Owner is final authority for product direction and protected actions. GPT/ChatGPT is the sole AI engineering participant and executor.  
**Canonical governance:** `docs/GPT_ONLY_AUTONOMOUS_ENGINEERING_OS.md`

## 1. Operating model

The organization contains exactly two actors:

1. **Human Owner** — ultimate authority.
2. **GPT/ChatGPT** — sole AI engineer and final technical integrator.

No other AI may be delegated engineering work.

## 2. Source of truth

GitHub repository state is authoritative for repository facts. GPT reconciles live `main`, issues/PRs, diffs, canonical governance/current-state documents and exact CI evidence. Conversation memory never substitutes for current Git state.

`docs/SENTINEL_CURRENT_STATE.md` is a semantic state summary. It must not contain a mutable self-referential `main` HEAD or workflow-run mirror. Git and Actions are the live source for those values.

## 3. Autonomous lifecycle

```text
DISCOVER → BASELINE → PLAN → IMPLEMENT → TEST
→ DIAGNOSE/FIX → REVIEW → COMMIT → PUSH/PR
→ CI → ANALYZE → FIX/CI → READY
→ MERGE when exact-SHA gate passes
→ POST-MERGE VERIFY → NEXT TASK
```

Routine CI failures are not a conversational stop condition. GPT diagnoses, fixes, retests and reruns CI autonomously.

## 4. Branch and scope discipline

- Never push directly to `main`.
- Never force-push a protected branch.
- Prefer one issue = one logical change set = one PR.
- Keep changes inside declared boundaries.
- Split unrelated work into a separate issue/branch.

## 5. Autonomous actions

Subject to actual permissions and task scope GPT may inspect, edit, test, build, commit, push permitted branches, create/update PRs and issues, inspect CI/logs/artifacts, diagnose/fix failures, update governance/current-state documentation and merge a PR after the exact-SHA merge gate passes.

## 6. Exact-SHA merge gate

GPT may merge into `main` only if all required checks have completed successfully against the exact PR HEAD SHA being merged. Before merging, verify the target branch, exact SHA, required checks, successful conclusions, SHA association, absence of pending/failed/missing/stale required checks, scope integrity and absence of unexpected mutations.

A green result on another SHA is not evidence for the current PR HEAD.

## 7. Protected Owner gates

GPT must not autonomously:

- read, print, create, rotate or disclose production secrets/credentials;
- change production signing material or signing custody;
- alter branch protection or required-check policy;
- perform irreversible destructive data/repository operations;
- deploy to production/live environments;
- publish a release tag/GitHub Release;
- make a fundamental product-direction decision unresolved by approved requirements;
- bypass a required human/legal/compliance approval.

Merge into `main` is **not** an Owner gate when the exact-SHA merge gate is fully satisfied and repository protections permit the merge.

## 8. Security

Never bypass security checks, weaken authorization, expose secrets, or modify protected controls merely to obtain green CI or a merge. Preserve documented SENTINEL security invariants.

## 9. Evidence

For material acceptance claims preserve exact SHA, workflow/check name, Run ID where available, result and relevant artifact/log evidence. If evidence is unavailable, state `UNVERIFIED`.

## 10. Non-delegation

GPT must not outsource engineering analysis, implementation, testing, review, security auditing, research, CI diagnosis, DevOps or integration to another AI system.

## 11. Workflow hygiene

The repository should keep the minimum workflow set that provides required validation and intentional release/deployment actions.

- Pull-request validation is the primary branch-development gate.
- Push validation is limited to `main` where post-merge evidence is useful.
- Feature-branch push triggers should not duplicate pull-request validation.
- Automatic workflows must not create self-mutating documentation PRs for derived metadata.
- Concurrency should cancel obsolete non-release validation for the same branch/PR so stale commits do not consume runner capacity unnecessarily.
- Release-candidate signing/build workflows are manual or explicitly release-scoped; they must not run on every ordinary `main` push.
- Release publication remains tag-triggered and Owner-gated.

## 12. Documentation synchronization

Process rules belong in this contract and `docs/OPERATING_PLAYBOOK.md`; roles in `docs/AI_ROLES.md`; permissions in `docs/AUTONOMOUS_PERMISSIONS.md`; semantic current facts in `docs/SENTINEL_CURRENT_STATE.md`; release gates in `docs/RELEASE_GATES.md`; evidence semantics in `docs/SENTINEL_EVIDENCE_PROTOCOL.md`.

Documentation updates are part of the same logical change when product or architecture state materially changes. There is no separate HEAD-sync workflow or generated documentation PR for every `main` commit.
