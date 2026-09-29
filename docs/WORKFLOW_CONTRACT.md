# SENTINEL — Engineering Workflow Contract

**Status:** ACTIVE
**Effective:** 2026-09-29
**Canonical governance:** docs/AI_ORCHESTRATION_OPERATING_SYSTEM.md
**Tracking issue:** #377

## Source of truth

Git main at an exact SHA is authoritative for repository facts. Runtime/provider state must be read from the relevant live system. Conversation memory and summaries are orientation only.

## Execution graph

COMPACT RECONCILE → ROUTE → EXECUTE → TEST → FIX → REVIEW → PR → CI → EXACT-SHA VERIFY → SERIAL MERGE → POST-MERGE VERIFY

ROUTE stays single-GPT by default. It may create independent parallel lanes only when the expected speed/coverage benefit exceeds context and integration overhead. Each lane has isolated mutable state and an explicit owner.

## Parallel-lane contract

Every writing lane defines:
- base SHA;
- task/issue;
- owned subsystem/files;
- acceptance checks;
- branch/worktree;
- dependencies.

One mutable worktree has one writer. Agents do not silently cross file ownership.

## Integration contract

GPT/ChatGPT is the sole Owner-facing orchestrator and final technical integrator.

Parallel results integrate serially. Before each merge, GPT revalidates the branch against current main, reviews the complete diff, and verifies every required check on exact PR HEAD SHA.

Secondary agents cannot merge protected main.

## Failure loop

Routine CI/test/security/lint/build failures trigger diagnosis, repair, retest, and rerun. They do not require Owner approval.

## Owner gates

Stop for production credentials/secrets, signing material, branch-protection/permission changes, irreversible destructive operations, production/live deployment, release publication, fundamental unresolved product direction, or explicit legal/compliance gates.

## Security and user-visible evidence

Never weaken controls for green CI. Never expose or fabricate secrets/evidence.

User-facing work additionally follows docs/USER_VISIBLE_ACCEPTANCE_CONTRACT.md: build success and screenshots do not establish readiness.

## Context efficiency

Start from root AGENTS.md, then load only scoped instructions and canonical contracts relevant to the task. Do not preload the whole documentation corpus. Reuse already-known IDs/SHAs and prefer delta checks over repeated full audits.
