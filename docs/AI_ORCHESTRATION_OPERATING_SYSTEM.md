# SENTINEL — Controlled Multi-Agent Engineering Operating System

**Status:** ACTIVE
**Effective:** 2026-09-28
**Authority:** Human Owner
**Tracking issue:** #377

This is the canonical engineering-governance contract for SENTINEL. It replaces the former GPT-only participation restriction while preserving repository-first truth, exact-SHA integration, security gates, user-visible acceptance, and Owner-only protected actions.

## Human Owner

The Human Owner is the ultimate authority and final decision-maker.

Owner-only gates:
- production/live deployment;
- release publication and release tags;
- production secrets and credentials;
- signing keys, certificates and release-signing custody;
- branch-protection or required-check policy changes;
- repository permission changes;
- irreversible destructive operations;
- fundamental product-direction decisions;
- explicit legal, compliance or operator approvals.

No AI agent may bypass these gates.

## Primary orchestrator and final integrator

GPT/ChatGPT is the primary engineering orchestrator and final technical integrator.

GPT owns:
- decomposition and task routing;
- canonical repository-state reconciliation;
- architecture and invariant reconciliation;
- integration ordering;
- final diff review;
- exact-SHA required-check verification;
- merge into main when the exact-SHA gate passes;
- post-merge verification;
- truthful Owner-facing status.

Secondary agents may contribute bounded work but do not become independent integration authorities.

## Permitted secondary agents

Secondary AI agents and external model families are permitted when their role is explicit, bounded, least-privilege, and evidence-producing.

Permitted modes:
1. Parallel OpenAI/Codex subagents for independent repository exploration, testing, documentation, review, or isolated implementation.
2. External-model specialists for independent research, adversarial review, architecture challenge, UX/design critique, test ideas, or isolated implementation when model diversity has a concrete expected benefit.
3. Controlled design/product services used as laboratories or bounded implementation helpers. Their output is input evidence, not canonical production truth.

Secondary-agent output is never trusted merely because it is independent or comes from a different model family. It must be validated against source, tests, runtime evidence, and project invariants.

## Single-integrator and one-writer rules

- One logical change set has one accountable writer at a time.
- Agents that may write use separate branches/worktrees or otherwise isolated mutable state.
- Two agents must not concurrently edit the same mutable worktree.
- Parallel branches are integrated serially.
- Secondary agents never push directly to protected main.
- Secondary agents never merge a PR into main.
- GPT re-reads the complete resulting diff and exact current base before integration.
- After one parallel branch lands, remaining branches are revalidated against the new main before merge.

Parallel execution never weakens trunk discipline.

## Task routing

### Prefer one agent
Use one primary agent when:
- the task is short or inherently sequential;
- each step depends directly on the previous step;
- workers would contend over the same files or state;
- the change crosses authentication, authorization, RLS, migrations, signing, release lineage, or another tightly coupled security boundary;
- coordination overhead is likely to exceed available parallel work.

### Prefer parallel same-family agents
Use parallel GPT/Codex workers when work can be split into independent, bounded lanes such as:
- Android vs Web vs Public Site vs Companion work;
- independent test suites;
- separate repository audits;
- provider/infrastructure investigation;
- documentation/evidence reconciliation;
- independent failure hypotheses;
- broad current-information research.

### Add external-model review selectively
Use a different model family when independent error patterns are valuable, especially for:
- adversarial code/security review;
- architecture challenge;
- UX/design critique;
- independent specification interpretation;
- alternative implementation proposals.

External-model participation is not a mandatory ceremony. Use it only when expected value exceeds extra cost, latency, context transfer, and integration overhead.

### External-model implementation
External-model implementation is allowed only when:
- scope and owned files are explicit;
- work occurs in isolated mutable state;
- no protected credentials are exposed;
- no shared-state write race exists;
- GPT performs final integration review and exact-SHA validation.

## Security boundary for secondary agents

Secondary agents receive least-privilege context.

They must not receive or retrieve:
- production secrets or credentials;
- signing material;
- protected deployment tokens;
- unnecessary personal/private user data;
- repository administrative credentials.

External providers receive only the minimum source/context required for the bounded task. Provider retention, account scope, and data-handling terms are environment dependencies.

No secondary agent may change branch protection, required checks, repository permissions, production deployment authority, or release authority.

## Autonomous lifecycle

DISCOVER → BASELINE → DECOMPOSE/ROUTE → EXECUTE → TEST → DIAGNOSE/FIX → REVIEW → PR → CI → EXACT-SHA VERIFY → SERIAL INTEGRATE → POST-MERGE RUNTIME/UX VERIFY

Independent lanes may run in parallel between ROUTE and REVIEW. Integration is serialized.

Routine build, test, lint, security, workflow, or CI failures are not Owner gates. GPT continues diagnose/fix/retest autonomously.

## Exact-SHA merge gate

GPT may merge a PR into main only when:
1. target branch is main;
2. exact PR HEAD SHA is known;
3. required checks are identified;
4. every required check completed successfully;
5. every required result belongs to that exact HEAD SHA;
6. no required check is pending, failed, missing, or stale;
7. the final diff remains in scope;
8. base/integration state has not changed unexpectedly after validation.

Never bypass or weaken branch protection or security gates to obtain a merge.

## Evidence and user-visible truth

Repository source, tests, CI, and runtime evidence keep their existing authority hierarchy.

For user-facing surfaces, docs/USER_VISIBLE_ACCEPTANCE_CONTRACT.md remains binding:
- source/build success is not visual acceptance;
- screenshots alone are not runnable-product evidence;
- the Owner must open and accept the applicable runnable surface before it is called ready.

Secondary-agent consensus is not evidence by itself.

## Orchestration efficiency

Multi-agent execution is a means, not a goal.

For recurring task classes, measure or record:
- task success;
- wall-clock duration;
- agent/tool/token or credit consumption;
- merge conflicts/rework;
- CI reruns;
- Owner interventions.

If orchestration costs more than direct execution without improving coverage or latency, return that task class to single-agent mode.

## Context routing

The repository root AGENTS.md is the compact entrypoint for agent context.

Agents:
1. read root AGENTS.md;
2. load only scoped AGENTS.md and canonical documents relevant to the active task;
3. avoid loading the full documentation corpus by default.

This reduces context dilution and stale-rule collisions.

## Governance priority

1. explicit current Human Owner instruction;
2. this operating system;
3. repository security and branch protections;
4. active evidence/release/security contracts;
5. scoped AGENTS.md instructions;
6. other active architecture/operations documentation;
7. historical/superseded material.

For implementation facts, live Git/runtime evidence outranks prose.

## Amendment rule

Only the Human Owner may fundamentally amend this operating model. GPT may reconcile subordinate documents after an explicit Owner decision.
