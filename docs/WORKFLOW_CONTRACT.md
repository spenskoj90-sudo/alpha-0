# SENTINEL — Engineering Workflow Contract

**Status:** ACTIVE
**Effective:** 2026-09-29
**Canonical governance:** `docs/AI_ORCHESTRATION_OPERATING_SYSTEM.md`

## Source of truth

Git `main` at an exact SHA is authoritative for repository facts. Runtime/provider state is read from the relevant live service. Conversation memory and old attachments are orientation only.

## Default execution

`DISCOVER → BASELINE → ROUTE → EXECUTE → TEST → FIX → REVIEW → PR → CI → EXACT-SHA VERIFY → SERIAL MERGE → POST-MERGE VERIFY`

Use direct GPT + connected tools by default. Route to Work/Codex/secondary workers only when the task shape benefits.

## Vertical-pass rule

Prefer one coherent pass that includes implementation, relevant tests, security/failure behavior, runtime evidence and semantic documentation. Do not split one fixable block into repeated audit/prompt cycles.

Reuse evidence tied to an unchanged SHA/artifact. Do not rerun expensive validation without a reason.

## Parallel lanes

Writing lanes declare base SHA, owned subsystem/files, acceptance checks, isolated branch/worktree, and dependencies.

One mutable worktree has one writer. Parallel results integrate serially through GPT.

## Integration

GPT/ChatGPT is final technical integrator. Before merge GPT reviews the complete diff against current `main`, verifies exact required-check evidence and ensures no stale or missing result is being reused.

Secondary workers cannot merge protected `main`.

## Failure loop

Routine CI/test/security/lint/build failures trigger diagnosis, repair, retest and rerun without Owner intervention.

## Owner gates

Stop only for production credentials/secrets, signing material, branch-protection/permission changes, irreversible destructive operations, production/live deployment, release publication, unresolved fundamental product direction, or explicit legal/compliance gates.

## Security and acceptance

Never weaken controls or expose/fabricate secrets/evidence.

User-facing work additionally follows `docs/USER_VISIBLE_ACCEPTANCE_CONTRACT.md`: source/build/screenshots alone do not establish readiness.
