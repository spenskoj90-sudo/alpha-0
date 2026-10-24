# SENTINEL — H design laboratory

Status: **DESIGN SOURCE + BROWSER PROTOTYPE**, not an accepted production identity.
Based on protected main `5e8a2b3a1001b81dad462ab9ceede9299acb8c55` (2026-10-24).
Production v3 and all product applications remain unchanged.

## Open the interactive study

Requires Python 3 and a modern browser. No package installation is needed to run it:

```sh
python design/h-system/serve.py
```

Open <http://127.0.0.1:4173/>. The server binds loopback only.
Use the top selector for Public website, Android, Windows, Web Control or Library.
Every URL preserves `?surface=…&lang=ru|en`; direct routes and browser history work.
For example `/capture?surface=android&lang=en`, `/overlay?surface=windows&lang=ru`,
`/security?surface=control&lang=en`, `/brand?surface=library&lang=ru`.
The same paths on different surfaces are separate designs, not shared authorization.

**Do not open index.html as file://:** ES modules and JSON assets require the local HTTP server.
All data and credentials in form journeys must be fictional. No values are sent or stored.
There is no production API, actual login, admin authority, checkout, screen capture,
microphone capture, game input, live game telemetry or download installation.

## What this pass contains

- Four original vector identity studies: Confluence, Waypoint, Parallax, Nexus. None selected.
- 55 editable 24-unit SVG icon masters, one 1.65 stroke/round-cap/round-join grammar.
- Brand exports at 16/20/24/32/48/72/108/192/512px; ICO, adaptive foreground,
  monochrome and notification VectorDrawable **candidate sources**.
- Seven original vector concept illustrations: source/context/decision, Android,
  Companion/Overlay, game modules, consent, process and features.
- 14 individually authored public pages; 20 Android, 21 Windows and 14 Web Control routes.
- RU/EN, provisional dark/light themes and four accent studies; no palette selected.
- Local consent/revoke/stale/recovery/Stop, MFA, update-error/rollback and Overlay-density journeys.
- Locally bundled licensed Onest, Inter and JetBrains Mono Latin/Cyrillic fonts.

Editable Figma: <https://www.figma.com/design/BdF9XW7eYmZrOkdnnH98Jc?node-id=13-4>.
The existing two palette-study pages are retained. Starter plan limits are handled
without a purchase: H is organized spatially on the third page; dark/light tokens
use separate one-mode collections.

Figma contains 23 component sets / 108 variants, 55 icon components, 4 identity masters,
7 illustration components, 138 RU/EN route frames and 28 extra journey-state frames.
The recorded structural audit found 955 instances, no image-filled UI nodes and no
horizontal overflow among top-level screen children. This is structural evidence,
not a claim that every nested layout and state has passed exhaustive visual review.
Authoring scripts and returned IDs are in `figma/`; apply them only through Figma,
not Node. They are evidence of this authoring pass, not an idempotent full-file importer.

## Verification

```sh
node --test design/h-system/tests/*.test.mjs
PLAYWRIGHT_MODULE=/absolute/path/to/playwright CHROMIUM_EXECUTABLE=/optional/path/to/chromium \
  node design/h-system/tests/browser.cjs
```

If Playwright owns its browser, omit CHROMIUM_EXECUTABLE. Existing repository CI uses
`web/node_modules/@playwright/test`. `H_QA_OUTPUT` controls screenshot/report output.
The suite starts its own loopback server on port 4176 and checks all 69 routes in
RU/EN at 320/390/768/1024/1440px, internal links and explicit interaction regressions.
The H Design Preview workflow publishes exact-PR-HEAD source and screenshots as an artifact.

## Important remaining H work

This is a substantial first implementation, **not completion of H1–H11**:

- Brand concepts need further art direction, bespoke wordmark development, full platform
  splash/installer/tray/PWA compositions and physical small-size acceptance.
- Component variants need richer content-specific design and a complete applicability matrix;
  a state label and reusable template alone do not prove finished product UX.
- Many future game modules deliberately show UNKNOWN/PLANNED structures. They require deeper
  module-specific interaction design; no verified source exists to fill them honestly.
- Phone/tablet native hierarchy, desktop window behavior, 200% text and additional
  breakpoints, all accent/theme combinations and every state need additional visual passes.
- Figma route studies are component compositions and linked state frames; real focus, Escape,
  history and state transitions are exercised in the browser prototype, not native apps.
- TalkBack, NVDA, Android OEM/system dialogs, exact WoW environment and Windows high-DPI/host
  runtime are untested here. No physical, Owner-visible, Owner-accepted or release acceptance inferred.
- Palette and identity selection stay deferred until the full system meets the Owner review gate.

Continue from these artifacts instead of restarting an audit or asking for a color selection.
