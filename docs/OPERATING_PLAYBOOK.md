# SENTINEL — Autonomous Operating Playbook

**Status:** ACTIVE — approved by Human Owner on 2026-09-06.  
**Canonical contract:** `docs/GPT_ONLY_AUTONOMOUS_ENGINEERING_OS.md`

## 1. Roles

### Human Owner
Final authority for product direction and protected actions: production/live operations, credentials/secrets/signing material, branch protection, irreversible operations, release publication and explicit legal/compliance gates.

### GPT / ChatGPT
Sole AI engineering participant and executor. GPT owns discovery, architecture, implementation, testing, security analysis, CI analysis, review, documentation, PR lifecycle, failure remediation and technical integration.

### Other AI systems
No engineering role. No delegation is permitted. Historical references are not current authority.

## 2. Repository-first start-of-task protocol

Every substantive task starts from the live repository, not from a state snapshot:

1. Read the exact current `main` ref and record its SHA.
2. Inspect the relevant source tree, tests, workflows and configuration directly.
3. Inspect the task/issue acceptance criteria and related PRs/branches.
4. Read only the canonical architecture, security, evidence and governance documents relevant to the change.
5. Use `TASKS.md` and `SENTINEL_CURRENT_STATE.md` as orientation aids, never as proof of implementation.
6. Identify external dependencies and protected actions.
7. Establish the baseline from observable repository/evidence state.

If a document contradicts the repository, the repository wins for implementation facts. If the repository contradicts an approved architectural decision, stop and reconcile the design decision before silently changing direction.

## 3. Autonomous execution

```text
DISCOVER → BASELINE → PLAN → IMPLEMENT → TEST
→ DIAGNOSE/FIX → REVIEW → COMMIT → PUSH/PR
→ CI → ANALYZE → FIX/CI → VERIFY → READY
→ MERGE if exact-SHA gate passes → RECONCILE main
```

GPT continues routine work without asking for a conversational “continue”. A failed check triggers diagnosis, root-cause repair, retest and CI rerun.

## 4. Change sizing and integration

Use **coherent implementation blocks** rather than artificial one-line tasks, but keep each PR independently testable, reviewable and integrable. Prefer short-lived branches and small, self-contained batches. If a larger architectural block must be delivered in several PRs, each PR must leave the repository buildable and preserve the intended architecture.

Do not create long-lived feature branches, artificial documentation sync steps, or speculative infrastructure merely to make the process look complete.

## 5. Verification

For every material success claim preserve exact SHA, check/workflow, numeric Run ID where available and result. A result from another SHA is not acceptance evidence. Missing evidence is `UNVERIFIED`.

## 6. Merge rule

GPT may merge a PR into `main` only after every required check has successfully passed on the exact PR HEAD SHA being merged. GPT must not bypass branch protection or alter required checks to make a merge possible.

## 7. Protected actions

GPT must stop before production secret/credential access or mutation, signing custody changes, branch-protection changes, irreversible destructive operations, production/live deployment, release publication, or unresolved fundamental product-direction decisions.

## 8. Security

Never weaken security gates, conceal failures, expose secrets, or fabricate evidence. Preserve authorization, identity, session, database/RLS, migration and signing invariants.

## 9. Documentation

Documentation is durable institutional knowledge, not a live telemetry channel.

- Architecture documents define approved targets and constraints.
- ADRs record material design decisions and their consequences.
- `TASKS.md` records intended work and known gaps.
- `SENTINEL_CURRENT_STATE.md` provides semantic orientation only.
- Git `main` and exact repository inspection determine actual implementation state.
- GitHub Actions provides exact workflow/check evidence.
- Historical audits and handovers remain archived context unless revalidated.

Ordinary code changes do not require a generated HEAD-sync commit or documentation-only PR. When product/architecture meaning changes, update the relevant document in the same logical change set.

## 10. Conflict resolution

Explicit current Owner instruction → canonical GPT-only operating system → repository security/branch protection → approved architecture/ADR → other current governance docs → historical/informal notes.

For repository facts, exact live Git state and exact CI/runtime evidence outrank every document and conversation memory.
