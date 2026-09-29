# SENTINEL — Compact Project Memory

**Status:** ACTIVE
**Purpose:** durable orientation for ChatGPT Project/Work. Live repository/provider evidence always outranks this file.

## Owner and interaction model

- The Human Owner is final authority.
- The Owner works through GPT/ChatGPT rather than coordinating secondary AI/services directly.
- GPT is primary orchestrator, final technical integrator and default executor.
- Routine engineering proceeds autonomously with minimal questions.
- Owner-side work is mobile-first; unavoidable manual steps should be short and Android-friendly.
- Copy/paste tasks for Work, Lovable or another surface are delivered as one complete copy-ready block.

## Canonical repositories

- Production/source of truth: `spenskoj90-sudo/alpha-0`.
- Design laboratory/reference: `spenskoj90-sudo/sentinel-aware-companion`.
- Lovable may evolve the design repository independently, but unfinished design-lab iterations are never promoted to production.
- Production translation occurs only after the design reference is complete, validated and reviewed by GPT.

## Engineering model

- Direct GPT + connected tools first.
- Work for long/browser/authenticated/background tasks.
- Codex/same-family bounded workers when repository-local execution helps.
- External model families are optional bounded review/research/design tools under GPT supervision, never independent authorities.
- One writer per mutable state; serial integration; exact-SHA merge evidence.

## Control planes

- GitHub: code, PRs, CI, issues and engineering truth.
- Render: staging runtime.
- Neon: managed PostgreSQL.
- PostHog: bounded analytics/observability.
- Google Drive: non-sensitive project evidence and handoffs.
- Resend/Stripe and federated providers: external integration surfaces under staging/production boundaries.
- Lovable/Figma: design work.
- Replit: isolated execution/prototyping.
- Linear: optional roadmap/acceptance mirror.
- OpenAI Developers: OpenAI integration support.

Always read live plugin/connection state rather than trusting this list as an installation snapshot.

## Security

- Do not put sensitive values in chat, Git, issues, logs, Project files or Google Drive documents.
- Use approved runtime/provider secret stores or Owner-controlled local custody.
- Production credentials, signing, release publication, live deployment, branch-protection/permission changes and irreversible destructive operations remain Owner-only.

## Efficiency preferences

- Prefer one coherent end-to-end pass.
- No audit-of-audit loops.
- Reuse exact-SHA evidence for unchanged artifacts.
- Do not repeat expensive tests for reassurance.
- Use the least expensive capable route and free/sandbox tiers before paid services.
- Ask the Owner only for a real protected gate or genuinely missing decision.

## Acceptance

- Source/build/CI success does not equal product visual acceptance.
- Browser/runtime automation should be used wherever possible.
- Emulator/cloud-device checks should replace avoidable manual Android repetitions.
- Final true physical-device/target-host acceptance remains external where required.
