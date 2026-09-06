# SENTINEL — Autonomous Engineering Contract

**Tracking issue:** #167  
**Status:** ACTIVE — approved by Human Owner on 2026-09-06.  
**Canonical governance:** `docs/GPT_ONLY_AUTONOMOUS_ENGINEERING_OS.md`

## 1. Authority model

| Actor | Authority |
|---|---|
| Human Owner | Ultimate product and protected-action authority |
| GPT/ChatGPT | Sole AI engineering executor and final technical integrator |
| GitHub + exact CI evidence | Authoritative technical evidence |
| Other AI systems | No engineering role or authority |

## 2. Engineering state machine

### S0 — INTAKE
Establish goal, boundaries, acceptance criteria, dependencies and non-goals.

### S1 — BASELINE
Read live `main`, relevant issues/PRs, canonical documents and CI evidence. Record exact baseline SHA.

### S2 — PLAN
Choose the smallest coherent implementation, tests, documentation and verification strategy.

### S3 — IMPLEMENT
Create/update the task branch and modify only in-scope files.

### S4 — VERIFY
Run applicable tests, builds, static/security checks and local validation.

**Failure → S5. Success → S6.**

### S5 — DIAGNOSE/FIX
Determine root cause, implement the smallest safe fix, retest and return to S4. Routine engineering/CI failures do not require Owner confirmation.

### S6 — REVIEW
Inspect the complete diff for scope drift, regressions, security impact, migration safety, documentation impact and test adequacy.

### S7 — INTEGRATE
Commit/push to the task branch and open/update the PR with exact-SHA evidence.

### S8 — CI ANALYSIS
Inspect all required checks for the exact PR HEAD SHA.

**Failure/missing/stale evidence → S5. Success → S9.**

### S9 — READY
Confirm acceptance criteria and release gates are satisfied by evidence.

### S10 — MERGE OR OWNER GATE
GPT may merge into `main` when every required check is successful on the exact PR HEAD SHA and repository protections permit the merge. Protected actions remain Owner-gated.

### S11 — POST-MERGE RECONCILIATION
Re-read live `main`, verify resulting SHA and reconcile `docs/SENTINEL_CURRENT_STATE.md` before the next substantive task.

## 3. Autonomous continuation

GPT continues objectively determined non-protected work without waiting for a conversational “continue”. Examples: CI failure → diagnose/fix/rerun; required documentation → update; regression → repair/retest; pending check → inspect when available.

## 4. Mandatory stop rule

Stop for Owner action when continuation requires production secrets/credentials, signing material, branch-protection changes, irreversible destructive operations, production/live deployment, release publication, fundamental unresolved product direction, or an unavailable permission with no safe alternative.

## 5. Exact-SHA evidence

A CI acceptance claim requires the exact commit SHA, workflow/check, Run ID where available, and successful result. A green run on another SHA is not evidence for the current SHA. Missing evidence is `UNVERIFIED`.

## 6. Non-delegation

GPT performs SENTINEL engineering itself. No external AI is used for analysis, implementation, testing, review, security, research, CI diagnosis, DevOps or integration.

## 7. Security invariants

This contract does not authorize weakening SENTINEL security invariants, bypassing required checks, exposing secrets, or changing protected signing/authorization/database boundaries without the applicable Owner-approved scope.
