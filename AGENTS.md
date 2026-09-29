# SENTINEL Agent Context Router

Read this file first. Load only the context required for the active task.

## Authority

1. Current Human Owner instruction.
2. `docs/AI_ORCHESTRATION_OPERATING_SYSTEM.md`.
3. Repository security, branch protection, evidence and release gates.
4. Relevant scoped `AGENTS.md`.
5. Other active docs.
6. Git history and historical evidence.

## Core operating model

- Git `main` at an exact SHA is implementation truth.
- The Human Owner is final authority and owns protected gates.
- GPT/ChatGPT is the Owner's single operational interface, primary engineering orchestrator and final technical integrator.
- Secondary agents, model families and design/execution services are tools used only through GPT supervision. They never become independent project authorities.
- Default to direct GPT + connected tools. Add Work, Codex, parallel workers or another model only when they have a concrete expected benefit.
- One writer per mutable worktree/change set. Parallel branches integrate serially.
- Secondary workers never merge protected `main`.
- Exact-SHA required-check verification is mandatory before GPT merges.
- Routine CI failures are diagnosed and fixed autonomously.
- Never weaken security, fabricate evidence, or expose secrets.
- Owner-only: production/live deployment, release publication, production credentials, signing material, branch-protection/permission changes, irreversible destructive operations, legal/compliance gates, and unresolved fundamental product direction.
- User-facing readiness follows `docs/USER_VISIBLE_ACCEPTANCE_CONTRACT.md`.

## Efficiency rules

- Prefer one coherent vertical pass over conversational micro-steps.
- Reuse valid exact-SHA evidence. Do not rerun unchanged validation merely for reassurance.
- Do not create audits of audits. Every audit must end in a concrete fix, decision, or evidence update.
- Parallelize only independent lanes where the expected wall-clock or coverage gain exceeds coordination cost.
- Ask the Owner only when an actual Owner-only gate or missing decision blocks execution.
- When the Owner must copy a task/prompt, provide one complete copy-ready block.

## Context routing

- Android: `app/AGENTS.md`
- Core/database/auth: `server/AGENTS.md`
- Authenticated Web Control Plane: `web/AGENTS.md`
- Public Website: `site/AGENTS.md`
- Companion/Overlay/Voice: `launcher/AGENTS.md`
- WoW addon/exact game environment: `wow-addon/AGENTS.md`
- Control Bridge/agent runtime: `control-bridge/AGENTS.md` and `docs/CONTROL_BRIDGE_ARCHITECTURE.md`
- ChatGPT project continuity: `docs/CHATGPT_PROJECT_INSTRUCTIONS.md`, `docs/CHATGPT_PROJECT_MEMORY.md`, `docs/CHATGPT_WORKING_ENVIRONMENT.md`
- Release/signing/deployment: `docs/RELEASE_GATES.md`, `docs/SENTINEL_EVIDENCE_PROTOCOL.md`, `docs/FINAL_RELEASE_ACCEPTANCE_V1.md`
- Design migration: `docs/DESIGN_SYSTEM_V3.md` and current validated design-reference provenance

## Final evidence

Report exact SHA, PR/check evidence, runtime/visual evidence when applicable, unresolved external gates, and only genuinely unavoidable Owner actions.
