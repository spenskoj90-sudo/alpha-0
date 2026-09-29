# SENTINEL — GPT-Orchestrated Controlled Engineering Operating System

**Status:** ACTIVE
**Effective:** 2026-09-29
**Authority:** Human Owner
**Tracking issue:** #377

This is the canonical engineering-governance contract for SENTINEL. It replaces both the historical strict GPT-only restriction and ambiguous multi-agent wording that could imply independent AI authority.

## Human Owner

The Human Owner is the ultimate authority and final decision-maker.

Owner-only gates remain live production changes, release publication, protected credentials/signing custody, branch-protection or repository-permission changes, irreversible destructive operations, unresolved fundamental product direction, and explicit legal/compliance approvals.

Routine engineering, testing, staging work, non-production configuration and reversible repository edits do not require repeated Owner approval.

## GPT is the single operational interface

GPT/ChatGPT is the primary engineering orchestrator and final technical integrator.

The Owner works through GPT. GPT may use connected tools, ChatGPT Work, Codex, bounded OpenAI subagents, external model families, Lovable, Replit, Figma and other approved services, but GPT retains task routing, state reconciliation, architecture/security review, final diff review, integration ordering, exact-SHA validation, permitted merge authority and final Owner-facing status.

A secondary worker never becomes a co-owner, final reviewer or independent integration authority.

## Routing order

Use the least expensive capable route:

1. direct GPT + connected tools;
2. ChatGPT Work for long, browser-heavy, authenticated or background work;
3. Codex / same-family bounded workers for repository-local execution or truly independent lanes;
4. external model families only for bounded review/research/design when independent error patterns justify the extra context and cost.

Do not add agents merely to create parallelism. Small, sequential, shared-state and tightly coupled security work defaults to one accountable writer.

## Secondary-agent boundary

Secondary AI agents and external model families are permitted only under GPT orchestration.

- Secondary workers receive least-privilege context.
- External-model participation defaults to read-only review/research.
- Writing work uses isolated branches/worktrees or an isolated design/prototype repository.
- One logical change set has one accountable writer.
- Two agents never concurrently edit the same mutable worktree.
- Parallel branches are integrated serially.
- Secondary agents never merge protected `main`.
- Protected production/signing/admin material is never delegated to secondary workers.
- Majority vote is never evidence; findings require source, test or runtime confirmation.

Lovable is a design laboratory. Replit is an isolated execution/prototype surface. Figma is optional authoring/review. None is production source of truth.

## Autonomous lifecycle

`DISCOVER → BASELINE → ROUTE → EXECUTE → TEST → DIAGNOSE/FIX → REVIEW → PR → CI → EXACT-SHA VERIFY → SERIAL MERGE → POST-MERGE VERIFY`

Routine build/test/lint/security/workflow failures remain inside this loop until resolved.

Do not create repeated audit-only passes. A substantive pass should end in a verified change, a bounded evidence/decision update, or a genuine Owner/external blocker with the smallest possible manual action.

## Pass and token economy

- Prefer one coherent vertical pass over many micro-requests.
- Load root `AGENTS.md`, then only scoped instructions and relevant contracts.
- Reuse valid evidence tied to the same unchanged SHA/artifact.
- Never rerun expensive tests solely for reassurance.
- Parallelize only when expected wall-clock/coverage gain exceeds orchestration overhead.
- Keep delegated prompts bounded to owned files, acceptance criteria and necessary context.
- Fix root causes rather than repeatedly re-auditing symptoms.

## Security and protected data

Security controls are deterministic boundaries, not prompt conventions.

- Never weaken a control to obtain green CI.
- Never fabricate CI, runtime, device or acceptance evidence.
- Protected credentials remain Owner-controlled.
- Sensitive values belong in approved runtime/provider secret stores or Owner-controlled local custody, not Git, chat, issues, logs, Project files or Drive documents.
- Google Drive is for non-sensitive project evidence, handoffs and recovery/inventory instructions.
- Prefer free/sandbox/test tiers while sufficient; paid activation is an Owner/commercial decision.

## Exact-SHA integration gate

GPT may merge a PR into `main` only when the exact PR HEAD is known, applicable required checks are current and successful for the required commit, no required result is pending/failed/missing/stale, the final diff remains in scope, base state has not unexpectedly changed, and no repository/security control is bypassed.

Branch/ruleset changes remain Owner-only.

## User-visible and physical acceptance

Automated evidence is not visual/physical acceptance.

For user-facing work, follow `docs/USER_VISIBLE_ACCEPTANCE_CONTRACT.md`. Use browser/runtime automation and emulator/cloud-device testing wherever available. Batch true physical Android/target-host checks so the Owner is not asked to repeat low-value tests after every small change.

## Context and memory hierarchy

For mutable facts: live Git/provider/runtime evidence > current repository contracts > current Project instructions > memory/chat summaries > historical material.

Stable project context is summarized in `docs/CHATGPT_PROJECT_MEMORY.md`. If memory or old chats disagree with current repository governance, the repository contract wins.

## Governance priority

1. explicit current Human Owner instruction;
2. this operating system;
3. repository security, branch protection and release/evidence gates;
4. relevant scoped `AGENTS.md`;
5. other active docs;
6. historical Git/chat records.

Only the Human Owner may fundamentally amend this operating model.
