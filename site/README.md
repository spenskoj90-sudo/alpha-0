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
