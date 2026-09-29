# SENTINEL — ChatGPT Working Environment

**Status:** ACTIVE
**Effective:** 2026-09-29

## Canonical control planes

- Engineering truth: GitHub `spenskoj90-sudo/alpha-0`.
- Design laboratory: `spenskoj90-sudo/sentinel-aware-companion` / Lovable. It may consume safe read-only production context; its writes stay in the design repository until GPT validates and imports a finished SHA.
- Staging runtime: Render.
- Managed PostgreSQL: Neon.
- Product analytics/runtime observability: PostHog SENTINEL project.
- Evidence/document storage: Google Drive `Sentinel/`.
- Roadmap/acceptance mirror: Linear SENTINEL project.
- Public deployment candidates: Render/Vercel as explicitly selected per surface; no production publication without the Owner gate.
- Project evidence plane: SENTINEL Control Bridge.

## Connected ChatGPT integrations verified 2026-09-29

Installed and available: GitHub, Render, Google Drive, Gmail, Neon, Resend, Figma, Linear, Lovable, Replit, PostHog, Stripe, Vercel, OpenAI Developers.

Permission posture:
- GitHub, Render, Google Drive, Neon, Resend, Figma, Linear, Lovable, Replit and PostHog: app-specific **Allow all actions**.
- Gmail, Stripe and Vercel: **Allow read actions**; writes require confirmation.
- Global default: **Allow low-risk actions**; important/sensitive actions remain guarded.

Do not repeatedly re-check permissions unless a tool fails, reports disconnection, or materially changes state.

## Explicit non-authorities

- Supabase is not the active SENTINEL database control plane.
- Dropbox is not the active SENTINEL file store.
- Generated conversation previews are not product evidence.
- Replit is not production source of truth.
- Lovable is not production source of truth.
- Figma is not an implementation authority by itself.
- Conversational memory is not engineering truth.

## Google Drive

Current root: `Sentinel/`.

Known folders:
- `Документация`
- `Архив`
- `Release evidence`
- `Провайдеры и доступы`
- `Безопасность`
- `Тестовые сборки`
- `Логи`

Reuse this structure; do not create duplicate folder trees without a concrete need.

**Security:** Google Drive is not a plaintext secret vault. Raw API keys, passwords, signing keys, private keys, recovery codes, and production secrets must stay in provider-native secret stores or Owner-controlled secure custody. Drive may store non-secret inventories, setup instructions, evidence, safe identifiers, and references to where a secret is held.

## Current staging endpoints

- Core: `https://sentinel-core-staging.onrender.com`
- Authenticated Web Control Plane: `https://sentinel-web-staging-fxhn.onrender.com`
- Public Website preview: `https://sentinel-public-site-staging.onrender.com`
- Control Bridge: `https://sentinel-control-bridge-staging.onrender.com`

These are staging endpoints, not production publication.

## Execution economy

Prefer:
- direct connected-tool actions;
- one coherent pass;
- compact exact-SHA evidence;
- delta reconciliation rather than full re-audit;
- reuse of cached IDs/SHAs;
- browser/synthetic/emulator verification before Owner physical testing;
- free/sandbox tiers until measured requirements justify paid infrastructure.

Do not add another service merely because it exists. A new tool/model must remove a real bottleneck or improve verified quality.

## ChatGPT / OpenAI boundary

ChatGPT subscription usage and OpenAI API billing are separate.

Do not start paid API orchestration merely because an API key exists. Use the existing ChatGPT/plugin/Work toolchain first. Any paid API path needs a concrete need and cost guardrail.

## Automated staging evidence

Protected-main pushes run `.github/workflows/staging-synthetic.yml` to bind runtime evidence to an exact deployed SHA. Runtime evidence does not equal Owner visual acceptance.
