# SENTINEL Web Product and Public Website Architecture

**Status:** ACTIVE  
**Date:** 2026-09-28  
**Baseline inspected:** protected `main` at `de1b9e3fe3a63bdef19be8ac8beeed33c4de9d07`  
**Design direction:** SENTINEL Design System v3.0 — CALM PRECISION / TRUSTED INTELLIGENCE

## 1. Purpose

This document separates two product surfaces that had previously been easy to conflate:

1. **Public Website** — unauthenticated product introduction, release/status/security information and future acquisition entrypoints.
2. **Web Control Plane** — authenticated account, intelligence, billing, device, security and privileged operational workflows.

They are intentionally not the same trust surface.

## 2. Current authenticated Web Control Plane

**User-visible status: FUNCTIONAL FOUNDATION / PRODUCT UX INCOMPLETE / OWNER-VISUAL-UNACCEPTED.** This document records architecture and implementation scope, not a visual-completion claim.


The existing production-side Web application remains under `web/` and uses Next.js 16.3.8 / React 19.3.0.

Verified implementation anchors include:

- `web/app/page.tsx` — current Control Plane overview shell;
- `web/app/admin/page.tsx` — distinct elevated Admin utility;
- `web/app/components/account-control.tsx` — account/session/MFA/billing-facing product control;
- `web/app/components/recommendation-panel.tsx` — authenticated intelligence retrieval/presentation;
- `web/app/api/account/`;
- `web/app/api/session/`;
- `web/app/api/billing/`;
- `web/app/api/intelligence/`;
- `web/app/api/admin/`;
- `web/app/api/mobile-core/`.

Security boundaries remain server-authoritative. The Web application keeps Core tokens and pre-session MFA challenges outside ordinary client-side JavaScript state through the existing HttpOnly/session proxy design.

## 3. Product UX gaps in the current Control Plane

The current Web foundation is functional but does not yet represent the complete product design inventory.

On the inspected baseline, the Overview page provides navigation entries for Overview, Intelligence, Games, Activity, Security, Devices, Account, Subscription, Settings, Support and Billing, but several of those destinations are still represented primarily as overview cards/in-page anchors rather than full dedicated product surfaces.

Therefore:

- Web backend/session/security integration is materially ahead of its final product UX.
- The current page must not be mistaken for the final information architecture.
- The next design-reference migration should expand the Control Plane into complete dedicated surfaces while preserving the existing account/session/billing/admin authority boundaries.
- Reference UI from Lovable/design laboratory must be translated into the native `web/` architecture, not copied wholesale.

## 4. Public Website architecture

**User-visible status: FOUNDATION ONLY / OWNER-VISUAL-UNACCEPTED.** The current surface is intentionally minimal and must not be described as a finished SENTINEL website. Build success only proves that the static implementation is technically valid. Owner-visible acceptance requires a real browser-openable exact-build surface; screenshots alone do not satisfy the acceptance contract.

The public website foundation is implemented under:

`site/`

It is an independent Next.js package and static export.

Current routes:

- `/` — product introduction;
- `/security/` — security/authority principles;
- `/status/` — deliberately conservative pre-release status;
- `/privacy/` — engineering privacy principles with an explicit notice that this is not the final legal privacy notice.

The public site has no `app/api/` tree and therefore owns no account, session, billing, intelligence, admin or provider authority.

### Why static export

A static public surface provides a smaller runtime attack surface and prevents marketing/content code from becoming an implicit trusted application backend.

The hosting edge remains responsible for production security headers and transport policy. Repository source does not claim that those headers are live until deployment evidence exists.

## 5. Brand and design authority

The public site reuses byte-identical repository-managed SENTINEL brand assets rather than recreating the mark.

It follows the active v3 semantics:

- low-radius structural geometry;
- dark/light modes;
- primary intelligence cyan / operational signal teal;
- visible focus;
- forced-colors fallback;
- reduced-motion fallback;
- restrained motion and no cyberpunk/HUD decoration;
- explicit pre-release/evidence language.

The public site must remain consistent with the final reconciled design-reference SHA when the ongoing design-laboratory pass completes.

## 6. Release truth

The public website must not turn planned capability into an availability claim.

Until the corresponding gates are actually accepted, it must continue to state that:

- Android physical exact-candidate acceptance is pending;
- intended Windows Companion host acceptance is pending;
- exact WoW environment acceptance is pending;
- selected STT/TTS plus physical microphone acceptance is pending;
- production providers/credentials are external/Owner activation;
- signing, publication and production deployment are final Owner gates.

There is intentionally no public download CTA before signed publication acceptance.

## 7. Future deployment topology

Recommended logical topology after release readiness:

```text
public domain / www
        |
        v
SENTINEL Public Website (site/, static)
        |
        +----> authenticated app hostname / entry
                       |
                       v
              Web Control Plane (web/)
                       |
                       v
                 SENTINEL Core
                  /         \
             Android     Companion
```

Exact production hostnames and DNS are not encoded yet because production deployment is Owner-gated.

## 8. Next Control Plane migration pass

After the design laboratory produces its next accepted final SHA:

1. update the canonical design-reference provenance;
2. diff the final screen/state/component registries against `web/`;
3. preserve existing account/session/MFA/billing/admin security boundaries;
4. create dedicated product routes for the incomplete Control Plane surfaces;
5. implement loading/empty/error/offline/stale/degraded states rather than generic placeholders;
6. validate dark/light, keyboard, forced colors, reduced motion and responsive layouts;
7. extend design drift tests;
8. run exact-SHA PR CI before integration.

## 9. Validation contract

The required protected-branch `Web build` job now validates both:

- `web/` — tests, coverage, lint, build;
- `site/` — deterministic install, lint, static build.

The Security workflow audits dependencies for both packages, while repository verification checks the public-site package/lock consistency, static-export boundary and absence of an API tree.

The public site is not considered deployed merely because its source and build pass CI.
