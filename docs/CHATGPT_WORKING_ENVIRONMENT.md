# SENTINEL — ChatGPT Working Environment

**Status:** ACTIVE
**Effective:** 2026-09-29

## Canonical control planes

- Engineering truth: GitHub `spenskoj90-sudo/alpha-0`.
- Design laboratory: `spenskoj90-sudo/sentinel-aware-companion` / Lovable.
- Staging runtime: Render.
- Managed PostgreSQL: Neon.
- Analytics/runtime observability: PostHog.
- Non-sensitive evidence/document storage: Google Drive `Sentinel/`.
- Roadmap mirror when useful: Linear.
- Project evidence plane: SENTINEL Control Bridge.

Live plugin/account state must be queried through ChatGPT Plugin Management or the relevant connector rather than copied into this file as permanent truth.

## Preferred ChatGPT workflow

1. Use normal Chat plus connected plugins for focused repository/service work.
2. Use ChatGPT Work for long-running, multi-step, authenticated-browser, visual/browser-acceptance or background execution.
3. Use Codex/same-family workers only when repository-local compute or isolated implementation materially helps.
4. Use external model families only as bounded supervised tools when independent error patterns are worth the context/cost.

The Owner should not have to coordinate secondary workers. GPT prepares or runs the work and returns one consolidated result.

## Design boundary

Lovable is a design laboratory. It may receive bounded read context from the production repository but writes to the design repository. A design iteration is promoted only after it is complete and validated. An in-progress Lovable commit is never imported merely because the project UI says ready.

## Explicit non-authorities

- Supabase is not the active SENTINEL database control plane.
- Dropbox is not an active SENTINEL file store.
- Generated conversation previews are not product evidence.
- Replit is not production source of truth.
- Figma is optional review/authoring, not a shipping dependency.

## Protected data

Sensitive values belong only in approved provider/runtime secret stores or Owner-controlled local custody. Do not place them in Git, ChatGPT Project files, Google Drive operational documents, issues, logs or chat.

Google Drive may store non-sensitive inventories, recovery instructions, evidence and handoffs.

## Current staging endpoints

- Core: `https://sentinel-core-staging.onrender.com`
- Authenticated Web: `https://sentinel-web-staging-fxhn.onrender.com`
- Public Website: `https://sentinel-public-site-staging.onrender.com`
- Control Bridge: `https://sentinel-control-bridge-staging.onrender.com`

These are staging endpoints, not production publication.

## Runtime evidence

Protected-main pushes run the staging synthetic gate. It verifies exact deployed source identity and bounded Core/Web/Public Site runtime behavior. Runtime evidence is not Owner visual acceptance.
