# SENTINEL Agent Context Router

Read this file first. Do not load the entire repository documentation set by default.

## Authority

1. Current Human Owner instruction.
2. docs/AI_ORCHESTRATION_OPERATING_SYSTEM.md.
3. Repository security, branch protection, and release gates.
4. Relevant scoped AGENTS.md.
5. Other active docs.
6. Historical or superseded docs.

## Core rules

- Git main at an exact SHA is implementation truth.
- GPT/ChatGPT is primary orchestrator and final technical integrator.
- Secondary agents are allowed only under the controlled multi-agent rules.
- One writer per worktree/change set; parallel branches integrate serially.
- Secondary agents never merge main.
- Exact-SHA required-check verification is mandatory before GPT merges.
- Routine CI failures are diagnosed and fixed autonomously.
- Never weaken security, fabricate evidence, or expose secrets.
- Owner-only: production/live deployment, release publication, production credentials, signing material, branch-protection/permission changes, irreversible destructive operations, and fundamental unresolved product direction.
- User-facing readiness follows docs/USER_VISIBLE_ACCEPTANCE_CONTRACT.md.

## Context routing

- Android: app/AGENTS.md
- Core/database/auth: server/AGENTS.md
- Authenticated Web Control Plane: web/AGENTS.md
- Public Website: site/AGENTS.md
- Companion/Overlay/Voice: launcher/AGENTS.md
- WoW addon/exact game environment: wow-addon/AGENTS.md
- Release/signing/deployment: RELEASE_GATES, SENTINEL_EVIDENCE_PROTOCOL, FINAL_RELEASE_ACCEPTANCE_V1
- Design migration: DESIGN_SYSTEM_V3 and current design-reference provenance

## Task sizing

Prefer one coherent vertical pass. Parallelize only independent bounded lanes. Do not create extra agents merely to appear parallel.

## Final evidence

Report exact SHA, PR/check evidence, runtime/visual evidence when applicable, unresolved external gates, and any remaining Owner-only action.
