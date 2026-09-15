# SENTINEL diagnostics and quality improvement v1

Status: **ACTIVE**

This document defines the diagnostic boundary used by SENTINEL for physical acceptance, production support tickets, and the optional user quality-improvement program. It does not authorize release publication or production deployment.

## 1. Two deliberately different Android builds

### `physicalTest`

The physical-test APK exists only for controlled real-device acceptance and engineering reproduction.

- application ID: `com.alpha0.app.physicaltest`;
- build type: `physicalTest`;
- diagnostic mode: `FORENSIC_TEST`;
- app-private rolling trace: 16 MiB;
- richer lifecycle, runtime, API timing, previous-process-exit and StrictMode evidence;
- sanitized exception stack traces are retained locally;
- full trace can be exported as a compressed file through the Android share sheet;
- Sentry/automatic remote telemetry is disabled in this build even if a DSN is available;
- this APK must never be published as the mass-user release;
- CI produces an exact-source-SHA APK and SHA-256 artifact retained for 90 days.

The build does **not** weaken authorization, device binding, Play Integrity boundaries, transport security or any server-side policy. It adds observation only.

### Production/release Android app

The production app keeps only a small privacy-bounded local diagnostic ring needed to understand recent failures.

- diagnostic mode: `PRODUCTION`;
- app-private rolling trace: 512 KiB;
- no full forensic export control;
- no automatic upload of the local diagnostic ring;
- external Sentry remains independently fail-closed and minimized by `observability/telemetry-contract.v1.json`;
- a support/quality ticket can be submitted with no diagnostic attachment at all.

## 2. Data that diagnostics may contain

Structured diagnostics may contain technical data such as:

- UTC and monotonic timing;
- application version/build type and exact source SHA when present;
- stable screen-route identifiers, not route parameters;
- lifecycle/runtime state;
- operation names, HTTP status/error code and request duration;
- redacted one-way request correlation prefixes;
- device OS/API level and bounded manufacturer/model strings;
- exception class and sanitized technical message/stack;
- bounded booleans, counters and low-cardinality technical fields.

## 3. Data forbidden by default

Neither physical-test nor production diagnostics may deliberately capture:

- passwords;
- access, refresh or session tokens;
- Authorization headers;
- API credentials or private keys;
- raw Play Integrity tokens/challenges/nonces;
- cookies;
- raw HTTP request/response bodies;
- screenshots or view-hierarchy dumps;
- raw microphone/audio bytes;
- WoW SavedVariables;
- game chat/transcripts;
- arbitrary user-entered ticket title/description text as diagnostic breadcrumbs.

Sensitive structured keys are redacted on-device. Secret-like free-form exception text is scrubbed. The Core independently validates and rejects diagnostic snapshots containing forbidden key/value patterns; client redaction is therefore not the only boundary.

## 4. Ticket snapshot semantics

When an authenticated user opens **Report a problem**, the app freezes a bounded snapshot of diagnostic events that were already present before the user begins writing the ticket. This matters because the support text must not be silently copied into telemetry.

The report UI shows:

- how many structured events are in the snapshot;
- approximate snapshot size;
- diagnostic mode;
- a plain-language description of included and excluded data;
- a separate checkbox for attaching diagnostics;
- a separate optional checkbox for participating in the SENTINEL quality-improvement program.

Attaching diagnostics and joining the quality-improvement program are different decisions. A user may submit a support report without diagnostics and may attach diagnostics without opting into broader quality-improvement use.

## 5. Server boundary and retention

`POST /v1/quality/reports` requires an authenticated session and is rate-limited. The server:

- validates a closed diagnostic schema;
- limits a snapshot to 600 events and 384 KiB;
- rejects unknown fields and sensitive diagnostic keys;
- rejects obvious secret-like values fail-closed;
- records whether diagnostic attachment was explicitly consented;
- records quality-program opt-in separately;
- retains diagnostic payloads for at most 30 days;
- automatically removes expired diagnostic payloads while retaining ticket metadata/text for support history;
- writes a Core audit event for report creation.

Reports are not automatically converted into public GitHub issues. Private triage happens first through the Core admin quality queue.

## 6. Admin triage

The existing admin security boundary exposes authenticated quality-report endpoints for:

- queue/listing;
- individual report detail;
- access to a still-retained sanitized diagnostic snapshot;
- status transitions to `TRIAGED`, `IN_PROGRESS`, `RESOLVED` or `WONT_FIX`.

The web admin UI proxies these calls without persisting the admin token.

After triage, an actionable engineering defect may be represented in GitHub/Linear with only the minimum reproduction information needed. Private user text or retained diagnostic payloads must not be copied to public trackers unless separately reviewed and intentionally minimized.

## 7. Physical-device workflow

For a real Android acceptance run:

1. Select one exact protected-`main` SHA with a completed MAIN PASS.
2. Download `sentinel-physical-test-apk-<sha>` from the **Physical Test APK** workflow for that exact SHA.
3. Verify the bundled `physical-test-apk.sha256` before installation.
4. Install the `.physicaltest` application. It can coexist with the release package because its application ID is different.
5. Execute the physical acceptance procedure normally. Do not weaken device/security controls for the test build.
6. If behavior is wrong, reproduce it once where safe, then use **Report a problem** and/or **Export full forensic log**. The full forensic export is available only in the physical-test build.
7. Preserve the exact source SHA, APK SHA-256, device/OS context and exported log as engineering evidence.
8. Fix only defects supported by the real evidence, rerun CI, produce a new exact-SHA test APK and repeat the measured scenario.
9. Remove the test application/data from the device after the acceptance campaign is complete.

A diagnostic trace is evidence for diagnosis; it is not by itself a PASS. Final release gates remain governed by `docs/FINAL_RELEASE_ACCEPTANCE_V1.md`.

## 8. Production quality-improvement program

The quality-improvement option is intended to let willing users act as distributed testers for real-world shortcomings involving, for example:

- design/visual behavior;
- application functionality;
- game integration;
- performance;
- accessibility;
- voice/audio behavior;
- security/privacy observations;
- other reproducible quality defects.

Participation must remain voluntary. The feature must never turn into hidden background surveillance, raw gameplay capture or unrestricted telemetry collection.

## 9. Machine-enforced invariants

The contract is regression-tested by `scripts/test_telemetry_contract.py`, Android unit tests, Core quality-report tests and the exact-SHA `Physical Test APK` workflow. Any future change that removes application-ID isolation, enables full production forensic export, enables physical-test remote telemetry, weakens diagnostic consent, exceeds bounded retention or removes secret rejection must be treated as a security/privacy-sensitive change.
