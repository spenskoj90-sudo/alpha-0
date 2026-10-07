# Audit remediation — 2026-10-07

Status: reviewed SOURCE + local BUILD evidence; integration CI and post-merge runtime must be read live. This is the first security/evidence slice, not completion of the entire audit program.

Base main: `77f5c742412d5c394e9143ad3bf7188e4edee85a`. Integration branch: `integration/2026-10-07`. Companion WIP remains preserved at `ad51886eefa6bd223586a257f6ee08904f517db6`.

## Implemented in this slice

- F01: Web/Site lockfiles resolve sharp 0.35.5; fresh lock audits each report zero vulnerabilities. Security thresholds remain unchanged.
- F02: process-shared, origin-bound pending-only refresh coordination (cap 256), no settled-token cache or Core replay grace. Failed refresh and final protected-request 401 never erase/replace session cookies. Independent review found the final-401 write case; its regression failed first, then passed after the fix.
- F03: validated HTTP(S) Core origin without credentials/path/query/fragment; per-call 45-second timeout, caller-signal composition, manual redirect rejection and 1 MiB streamed response bound before parsing/proxying.
- F04/F05: Bridge reports checklist summary and UNVERIFIED release evidence; it cannot assert release acceptance. Canonical provider configuration names are process-local presence only, not Core enablement/delivery. Malformed surface summaries fail closed.
- F11: known surface dependency metadata keeps dependency/audit/CodeQL/supply-chain/P1/release lanes while avoiding unrelated host builds. Core dependencies keep protocol consumers; unknown/shared inputs and push remain full verification.
- F13: engineering and external acceptance queues separated; verifier validates seven external issue IDs within their section. Native production design authority reconciled, imported asset pins/Owner visual gates preserved. Knowledge API inventory added, 17 source SQL files distinguished from dated DB evidence, old handoff marked historical, full-suite machine release scope explicit.

## Verification

- Web: 117 tests / 24 files PASS; coverage statements 96.44%, branches 92.30%, lines 98.61%; existing thresholds unchanged. Web lint/build PASS.
- Site: npm ci, lint/static build PASS; no `npm test` script exists (the attempted command was an invocation error, not a product regression).
- Bridge: 13 pytest tests PASS and compileall PASS. Local Python 3.12.14 is below Bridge declared floor; pinned Python 3.14.7 CI remains required.
- Classifier: 14 tests PASS. Repository `verify.sh`: 83 PASS / 0 FAIL.
- Core: 1097 non-PostgreSQL tests PASS. The unfiltered local suite had 28 failures and 6 setup errors in PostgreSQL-marked tests because `DATABASE_URL` is absent. No local DB PASS is claimed; the exact-HEAD PostgreSQL integration/recovery CI gate remains mandatory. Affected modules: account_mfa_postgres, event_runtime (DB cases), knowledge_distribution_postgres, postgres_quality_clusters, postgres_refresh_concurrency, postgres_rls_inventory, postgres_runtime_retention, postgres_smoke, rls_policies, runtime_database_role, store_session_contract (DB cases), owned_device_list (PG parameters), postgres_email_codes.
- Independent read-only reviewer examined the first slice; no Critical findings and one Important final-401 cookie write fixed with RED→GREEN and the full Web suite. Native Fetch probes independently confirmed deadline failure for stalled headers/body. No review found another actionable regression in this slice.

## Decisions and limits

- Cross-process refreshes are not joined. A late losing request can return 401, but cannot clear a newer browser session. A full durable BFF/browser-generation design is separate engineering.
- Arbitrarily late **successful** cookie-writing responses can still overwrite a newer login/logout or later session generation. This pre-existing architectural limitation is not certified solved; pending joining can increase the number of such responses. F02 is a reproduced failed-response fix, not complete session-generation serialization.
- Incoming NextRequest disconnect signal is not automatically forwarded; caller signals are composed and all upstream calls still have their own deadline. No connection/cookie evidence is inferred from unit tests.
- Registry audit is a fresh dependency check; native all-platform packages, physical Android/Windows, game calibration, microphone, Owner visual acceptance and release acceptance remain separate gates.
- Existing browser/runtime checkpoint in the UX JSON is explicitly dated and SHA-bound. It does not attest this integration HEAD or Owner acceptance.

## Continue

Follow the unchecked engineering queue in TASKS: maintenance coupled metadata → preserved Companion WIP lifecycle/trusted-profile seam → Android consumer → truthful game presentation → Web verification/MFA/device workflows → justified orchestration/benchmark work. Real reviewed strategies and stock-game recommendations require verified source/calibration; keep UNVERIFIED and AUTOMATIC_EXECUTION_DISABLED until appropriate evidence. Never weaken full-suite release gates or signing/update custody to close the queue.

One continuation schedule is configured for 13 hourly passes on 2026-10-07, 11:00–23:00 Europe/Moscow. A scheduled invocation is not execution or completion evidence; each pass resumes the existing writer/PR and records concrete results. Disable it when only external/Owner gates remain.
