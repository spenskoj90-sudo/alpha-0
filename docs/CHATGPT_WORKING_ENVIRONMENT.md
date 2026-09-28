# SENTINEL — ChatGPT Working Environment

**Status:** ACTIVE
**Effective:** 2026-09-28

## Canonical control planes

- Engineering truth: GitHub `spenskoj90-sudo/alpha-0`.
- Design laboratory: `spenskoj90-sudo/sentinel-aware-companion` / Lovable; production parity only after explicit reconciliation.
- Staging runtime: Render.
- Managed PostgreSQL: Neon.
- Product analytics / error/runtime observability: PostHog SENTINEL organization/project.
- Evidence/document storage: Google Drive `Sentinel/`.
- Roadmap/acceptance mirror: Linear SENTINEL project.
- Public deployment candidate: Vercel/Render as explicitly chosen per surface; no production publication without Owner gate.
- Project-specific agent evidence plane: SENTINEL Control Bridge MCP.

## Explicit non-authorities

- Supabase is not an active SENTINEL database control plane.
- Dropbox is not an active SENTINEL file store.
- Generated conversation previews are not product evidence.
- Replit may be used only as an isolated rapid-prototype worker; it is not production source of truth.
- Figma Starter/View limits make it selective rather than the everyday primary design transport.

## Runtime visibility target

Every release-facing surface should eventually expose machine-readable exact-build/runtime evidence so GPT can validate it without asking the Owner to relay basic failures manually.

Web/Core staging must keep declared repository runtime versions aligned with Render runtime configuration.

## Secret handling

Secrets are stored only in provider/runtime secret stores or Owner-controlled local custody. Do not place raw secrets in Git, Project attachments, Google Drive operational docs, issue bodies, logs or chat messages.

OpenAI API keys belong to the consuming orchestration runtime. The Control Bridge itself does not require an OpenAI API key.

## Current staging endpoints

- Core: `https://sentinel-core-staging.onrender.com`
- Authenticated Web Control Plane: `https://sentinel-web-staging-fxhn.onrender.com`
- Public Website preview: `https://sentinel-public-site-staging.onrender.com`
- Control Bridge MCP foundation: `https://sentinel-control-bridge-staging.onrender.com`

These are staging endpoints, not production release publication. Web/Core runtime pins are Node 24.21.0 and Python 3.14.7 respectively. Public Site is an Owner-visible preview surface but remains product-incomplete until design migration and visual acceptance.

## Current ChatGPT plan boundary

The current Human Owner uses ChatGPT Plus.

As of 2026-09-28, ChatGPT Plus cannot directly attach a custom remote MCP server as a full custom ChatGPT app. Therefore:

- the SENTINEL Control Bridge staging service remains a fail-closed infrastructure foundation;
- do not represent it as an active ChatGPT Plus tool;
- use current built-in plugins, ChatGPT Work and scheduled automations for the primary Plus workflow;
- connect the bridge only through a separately billed OpenAI API orchestration runtime or after moving to a ChatGPT plan/workspace that supports the required custom MCP capability;
- ChatGPT subscription/usage credits and OpenAI API billing are separate. Do not start paid API orchestration merely because an API key exists; define a cost/budget guardrail first.

## Automated staging evidence

Protected-main pushes run `.github/workflows/staging-synthetic.yml`. It waits for the exact SHA on Control Bridge and verifies Core health/version, Web reachability, the real Web→Core invalid-login path, Public Website reachability and the pre-release robots guard. The resulting JSON artifact is runtime evidence, not visual acceptance.
