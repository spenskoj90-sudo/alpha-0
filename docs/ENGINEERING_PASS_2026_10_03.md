# Engineering pass — 2026-10-03

Owner spec: single integration branch from live protected main e7089ae659cd58a05bdd4621155a9df013daab12; full canonical main validation; no production activation, signing custody or action-authority expansion.

## Implementation plan
1. Add conservative NUL-safe change classification and reusable workflow. Preserve check names, test unknown paths, deletion/rename, base/head binding, dependency/design/API cross-impact, classifier failure and full non-PR execution. Split Web/site steps; keep scan/verification unconditional. PR release preflight runs contracts only, main retains exact-SHA collect/verify/attest.
2. Extend existing game catalog with environment/profile evidence and versioned knowledge pack schema. Add digest-bound validation, deterministic evaluation, revocation/cache safety; no network or LLM in combat path, no authorization authority.
3. Extend observer/action foundation only within default-deny boundaries and update production Intelligence presentation with unknown/stale/offline provenance, RU/EN and accessibility.
4. Reconcile provider contracts with official sources and connected control planes; prepare exact public configuration and unavoidable login/custody steps.
5. Targeted tests, coherent final diff review, one PR and one Codex review, exact HEAD CI, merge, full main and staging verification.

## Review focus
Classifier false negatives; required statuses on skipped dependencies; artifact provenance; untrusted pack conditions; stale/cross-profile execution; missing confidence displayed as unknown.

## Execution ledger
Baseline: repository verification 81 PASS / 0 FAIL. Main 28/28 successful check runs; no open PR. User explicitly authorizes autonomous engineering and supplies design/architecture and inline integration method.

Implemented: conservative reusable classification with real NUL git diff/rename tests; unconditional scan and verification, unchanged required names; protected-main full classification; PR release contracts only. CodeQL stays full on PR until external app-bound required context compatibility is demonstrated (no branch protection changes).

Runtime: 26 game/platform/environment inventory profiles; authenticated read endpoint; draft digest-bound WotLK role/strategy coverage foundation; strict data-only deterministic evaluator and bounded memory/persistent allowlisted pack cache with revocation. PostgreSQL canonical distribution and Android/Companion combat evaluation remain future implementation, not claimed.

UX: nullable uncalibrated confidence; Web evidence/unknown/stale/offline/cancelled-session/acknowledgement presentation; Companion/Overlay FACT/INFERENCE propagation; production-owned reduced glyph and four Android navigation icons; explicit opt-in Android numeric calibration with unverified environment metadata. Existing automatic-execution gate stays disabled.

Provider configuration: reject placeholder public IDs/Telegram secrets, partially invalid callback allowlists and VK client/callback mismatch. Console handoff is in PROVIDER_HANDOFF_2026_10_03.md.

Local validation: Core 1050 passed, 31 PostgreSQL deselected, 87.86% coverage; knowledge-pack new boundary tests targeted; 108 Web tests with 96.28% statements/92.08% branches; 72 Companion tests; Web/site build and Web lint; repository verification 82 PASS. Local browser install failed at external Chromium download, so browser and Android acceptance are delegated to canonical CI, not claimed as local PASS.

CI baseline: docs/ci-baseline-2026-10-03.json records actual prior PR #437 job durations: 2000 runner-seconds, including release preflight 415s and emulator291s. This cross-cutting integration appropriately selects all heavy jobs; measure new PR preflight and classifier overhead separately, never equate modeled narrow-diff savings with observed savings.
