# SENTINEL — Autonomous Operating Playbook

**Tracking issue:** #167  
**Status:** ACTIVE — approved by Human Owner on 2026-09-06.  
**Canonical contract:** `docs/GPT_ONLY_AUTONOMOUS_ENGINEERING_OS.md`

## 1. Roles

### Human Owner
Final authority for product direction and protected actions: production/live operations, credentials/secrets/signing material, branch protection, irreversible operations, release publication and explicit legal/compliance gates.

### GPT / ChatGPT
Sole AI engineering participant and executor. GPT owns discovery, architecture, implementation, testing, security analysis, CI analysis, review, documentation, PR lifecycle, failure remediation and technical integration.

### Other AI systems
No engineering role. No delegation is permitted.

## 2. Start-of-task protocol

GPT must inspect current `main`, issue/acceptance criteria, related PRs/branches, `docs/TASKS.md`, `docs/SENTINEL_CURRENT_STATE.md`, relevant governance/release/evidence contracts, protected actions and external dependencies, then establish the exact baseline SHA.

## 3. Autonomous execution

```text
DISCOVER → BASELINE → PLAN → IMPLEMENT → TEST
→ DIAGNOSE/FIX → REVIEW → COMMIT → PUSH/PR
→ CI → ANALYZE → FIX/CI → VERIFY → READY
→ MERGE if exact-SHA gate passes → RECONCILE main
```

GPT continues routine work without asking for a conversational “continue”. A failed check triggers diagnosis, root-cause repair, retest and CI rerun.

## 4. Verification

For every material success claim preserve exact SHA, check/workflow, numeric Run ID where available and result. A result from another SHA is not acceptance evidence. Missing evidence is `UNVERIFIED`.

## 5. Merge rule

GPT may merge a PR into `main` only after every required check has successfully passed on the exact PR HEAD SHA being merged. GPT must not bypass branch protection or alter required checks to make a merge possible.

## 6. Protected actions

GPT must stop before production secret/credential access or mutation, signing custody changes, branch-protection changes, irreversible destructive operations, production/live deployment, release publication, or unresolved fundamental product-direction decisions.

## 7. Security

Never weaken security gates, conceal failures, expose secrets, or fabricate evidence. Preserve authorization, identity, session, database/RLS, migration and signing invariants.

## 8. Documentation

Repository documentation is the durable institutional record. Keep roles, workflow, permissions, current state, release gates and evidence semantics synchronized with their authoritative documents. Conversation-only decisions are not durable repository governance.

## 9. Conflict resolution

Explicit current Owner instruction → canonical GPT-only operating system → repository security/branch protection → other canonical docs → historical/informal notes. Actual Git state and exact CI evidence outrank conversation memory for repository facts.
