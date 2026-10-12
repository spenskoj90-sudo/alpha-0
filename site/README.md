# SENTINEL public website

This directory is the unauthenticated public SENTINEL surface.

It is deliberately separate from `web/`, which remains the authenticated Web Control Plane and owns account, session, billing, intelligence and admin boundaries.

## Current status

- Static-export Next.js surface.
- No account/session/billing/admin API routes.
- No production domain is encoded in source.
- Search indexing is disabled while SENTINEL remains pre-release.
- No public download CTA is exposed before signed publication acceptance.

## Build

```bash
npm ci
npm run lint
npm run build
```

The output is written to `out/`.

## Deployment boundary

Production deployment is Owner-gated. The hosting edge must apply the repository security-header baseline (CSP, HSTS, no-sniff, referrer policy, frame denial and restrictive permissions policy). Static export does not itself assert edge-header configuration.

## Design authority

The site follows SENTINEL Design System v3.0: Calm Precision / Trusted Intelligence. Brand raster/glyph assets are byte-identical copies of the repository-managed production family.

## Public navigation

The compact home links to separate `/features`, `/games`, `/modules`, `/pricing`,
`/help` and `/access` exports, alongside existing security/privacy/status pages.
RU/EN selection persists across navigation; page titles follow the locale.
The access page links to the existing staging Control Plane and collects no credentials.
Prices are intentionally unpublished. Game entries retain research/foundation/observer
status and cannot grant capabilities or imply verified support.

`app/components/game-profiles.json` is a public-field projection of
`server/app/data/game-capability-catalog.v1.json`. After changing the canonical catalog,
regenerate the projection; CI rejects drift through `scripts/verify_public_site_routes.py`.
From the repository root after building: `python scripts/verify_public_site_routes.py`.
For an isolated static browser run: from `web`, use
`npx playwright test --config public-site.playwright.config.ts`.
