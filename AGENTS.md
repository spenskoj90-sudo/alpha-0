# SENTINEL Agent Context Router

Read this file first. Do not load the entire repository documentation set by default.

## Authority

1. Current Human Owner instruction.
2. `docs/AI_ORCHESTRATION_OPERATING_SYSTEM.md`.
3. Repository security, branch protection, and release gates.
4. Relevant scoped `AGENTS.md`.
5. Other active docs.
6. Git history for retired material.

## Core rules

- Git `main` at an exact SHA is implementation truth.
- GPT/ChatGPT is the sole Owner-facing orchestrator and final technical integrator.
- Secondary agents/services are bounded workers only; GPT controls routing, review, and integration.
- One writer per change set; parallel lanes must be independent; integration is serialized.
- Secondary agents never merge protected `main`.
- Exact-SHA required-check verification is mandatory before GPT merges.
- Routine CI failures are fixed autonomously.
- Never weaken security, fabricate evidence, or expose secrets.
- Owner-only: production/live deployment, release publication, production credentials, signing material, branch-protection/required-check changes, repository permissions, irreversible destructive operations, fundamental product-direction changes, legal/commercial gates.
- User-facing readiness follows `docs/USER_VISIBLE_ACCEPTANCE_CONTRACT.md`.
- Prefer one compact delta reconciliation and one coherent pass; avoid repeated full audits.
- Cache discovered IDs/SHAs and use narrow logs/exact queries.
- Do not import unfinished design-lab/Lovable work.

## Context routing

- Before resuming product/game work: `docs/TASKS.md` + `docs/PLAYER_INTELLIGENCE_ROADMAP_V1.md` (#455); preserve future requirements, current priorities and the next verified step. The roadmap is not implementation evidence.

- Android: `app/AGENTS.md`
- Core/database/auth: `server/AGENTS.md`
- Authenticated Web Control Plane: `web/AGENTS.md`
- Public Website: `site/AGENTS.md`
- Companion/Overlay/Voice: `launcher/AGENTS.md`
- WoW addon/exact game environment: `wow-addon/AGENTS.md`
- Control Bridge: `control-bridge/AGENTS.md` + `docs/CONTROL_BRIDGE_ARCHITECTURE.md`
- Release/signing/deployment: `RELEASE_GATES`, `SENTINEL_EVIDENCE_PROTOCOL`, `FINAL_RELEASE_ACCEPTANCE_V1`
- Design migration: `DESIGN_SYSTEM_V3` + current design-reference provenance

## Task sizing

Use one agent for short, sequential, shared-state, security-sensitive, or tightly coupled work.

Use secondary workers only for independent bounded lanes where speed/coverage benefit exceeds context, token/credit, and integration overhead.

## Final evidence

Report exact SHA, PR/check evidence, runtime/visual evidence when applicable, unresolved external gates, and only the remaining unavoidable Owner action.

## Controlled integration review

One daily integration PR; request one Codex review on a practically final HEAD.
Prioritize actionable correctness/security regressions: privilege/auth bypass, RLS/ownership,
credential leakage, unsafe game-action authority, replay/idempotency/concurrency,
stale-state execution, provenance drift, release/signing boundaries and destructive data behavior.
Do not spend review on naming, formatting or style already covered by automated linters.
Missing physical/environment evidence is an explicit gate; never infer acceptance from a build.

## Production design ownership

GPT owns production design in alpha-0 under Design System v3. The companion design laboratory
is reference/history only. No automatic imports or lab parity requirement. Owner visual acceptance
is separate from implementation and automated contracts.
