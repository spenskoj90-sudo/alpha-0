# Command Center Live Intelligence v2

## Status

Repository implementation contract for the authenticated Web recommendation path.

## Runtime path

1. The browser invokes same-origin `POST /api/intelligence/recommendations`.
2. The Next.js control plane requires the existing HttpOnly Web session boundary and same-origin write check.
3. The Web proxy constructs a fixed, bounded command-center context. Browser-supplied recommendation context and `X-Recommendation-Provider` are not forwarded.
4. The proxy calls Core `POST /v1/recommendations` with the opaque access token only on the server side.
5. Core remains authoritative for `knowledge:recommend`, provider routing, confidence, provenance and the observational-only recommendation contract.
6. A Core `401` may rotate the one-time refresh token once through the existing Web session boundary; the same correlation ID is preserved across initial call, refresh and retry.
7. The browser receives only bounded recommendation output and correlation headers. Core access/refresh tokens never enter client-side JavaScript.

## UI behavior

The Command Center no longer renders a hard-coded recommendation as though it were live evidence. The player explicitly requests live intelligence and sees one of four bounded states:

- authenticated Core recommendation with confidence, provider/model identity and provenance;
- authentication required;
- request in progress;
- fail-closed unavailable/invalid-response state.

No failed request falls back to a static card labelled or implied as live.

## Authority and safety boundary

This path is observational only. It does not grant game authority, execute actions, change entitlement state, select an external provider from the browser, or accept browser-authored normalized game evidence as trusted runtime state.

The current Web request intentionally uses a minimal command-center context. Exact live game evidence remains owned by validated Core/Companion/UGS paths and must not be inferred from browser state. Provider activation, external credentials and exact-environment acceptance remain separate Owner/environment gates.

## Evidence expectations

Routine Web tests must cover:

- same-origin enforcement;
- Web-session requirement;
- access-token confinement to server-side Core calls;
- rejection/non-forwarding of browser provider/context overrides;
- correlation continuity across one-time refresh and retry;
- deterministic Web build/lint/test success on the exact PR head.

Canonical acceptance still requires the repository evidence protocol and required exact-head CI gates.
