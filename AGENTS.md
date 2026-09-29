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
