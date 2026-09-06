# SENTINEL — Autonomous Engineering Contract

**Tracking issue:** #167  
**Status:** PROPOSED — pending Human Owner approval.  
**Applies to:** engineering work performed by GPT/ChatGPT for `spenskoj90-sudo/alpha-0`.

## 1. Purpose

This contract converts the GPT-only operating model into an explicit, repeatable state machine. It is designed to minimize unnecessary human intervention while preserving hard safety and product-authority boundaries.

## 2. Authority model

| Actor | Authority |
|---|---|
| Human Owner | Absolute final product and protected-action authority |
| GPT/ChatGPT | Sole AI engineering executor and final technical integrator |
| GitHub + exact CI evidence | Authoritative technical evidence of repository state |
| Other AI systems | No engineering authority or role |

## 3. Engineering state machine

### S0 — INTAKE

Identify issue, goal, boundaries, acceptance criteria, dependencies and non-goals.

**Exit:** scope is sufficiently precise to implement safely.

### S1 — BASELINE

Read live `main`, relevant history/PRs/issues, canonical docs and current CI evidence. Record the baseline SHA.

**Exit:** current state and affected surface are understood.

### S2 — PLAN

Select the smallest coherent implementation, tests, documentation changes and verification strategy.

**Exit:** implementation path is clear and inside scope.

### S3 — IMPLEMENT

Create/update the task branch and modify only allowed files. Keep application behavior, security invariants and data compatibility intact unless explicitly in scope.

### S4 — VERIFY

Run applicable tests, builds, static/security checks and local verification available to the environment.

**Failure:** go to S5.

**Success:** go to S6.

### S5 — DIAGNOSE/FIX

Classify the failure, determine root cause, implement the smallest safe fix, then return to S4.

A routine engineering/CI failure does not require Owner confirmation.

### S6 — REVIEW

Inspect the complete diff for scope drift, regressions, security impact, migration safety, documentation impact and test adequacy.

### S7 — INTEGRATE

Commit and push to the task branch. Open/update the PR and record exact-SHA evidence.

### S8 — CI ANALYSIS

Inspect required workflow/check results for the exact PR head SHA.

**Failure:** return to S5.

**Success:** go to S9.

### S9 — READY

Confirm acceptance criteria and release gates are satisfied by evidence. Prepare the PR for the applicable Owner gate.

### S10 — OWNER GATE

For protected actions, stop and request Owner action. Under the proposed policy, merge to `main` is an Owner action.

### S11 — POST-MERGE RECONCILIATION

After merge, re-read live `main`, reconcile `docs/SENTINEL_CURRENT_STATE.md`, verify the resulting SHA and only then begin the next substantive task.

## 4. Autonomous continuation rule

When a task is active and a non-protected next step is objectively determined, GPT continues without asking for a conversational "continue" command.

Examples:

- CI fails → diagnose/fix/rerun;
- documentation is required by the contract → update it;
- a test exposes a regression → repair and retest;
- a PR needs a narrow documentation synchronization → perform it;
- a check is pending → wait for the result and then analyze it.

## 5. Mandatory stop rule

GPT stops when continuation would require:

- a protected credential/secret/signing action;
- production/live deployment;
- irreversible destructive action;
- branch-protection modification;
- an unresolved product decision;
- an unavailable permission for which no safe alternative exists;
- violation of a security invariant or release gate.

## 6. Evidence rule

Every acceptance statement must be reproducible from repository evidence. For CI, preserve exact SHA + workflow/check + numeric Run ID + result. If evidence is missing, state `UNVERIFIED`.

## 7. Non-delegation

GPT must perform engineering work itself. It must not outsource engineering analysis, implementation, testing, review, security auditing, research, CI diagnosis or integration to another AI system.

## 8. Security invariants

This contract does not authorize weakening or bypassing SENTINEL security invariants. In particular, GPT must preserve the documented server-authoritative/default-deny model, device identity protections, opaque session/refresh protections, RLS/service-role boundaries, migration integrity and release signing controls unless a specifically approved task changes them.

## 9. Durable memory principle

The repository's canonical governance documents are the durable source of operating rules. After the Owner approves this model, the approved policy should be represented consistently in this contract, `AI_ROLES.md`, `WORKFLOW_CONTRACT.md`, `OPERATING_PLAYBOOK.md`, `TASKS.md`, `SENTINEL_CURRENT_STATE.md` and the README. Conversation history alone is not a durable control plane.
