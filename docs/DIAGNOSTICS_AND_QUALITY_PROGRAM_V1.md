# SENTINEL diagnostics and quality improvement v1

Status: **ACTIVE**

This document defines the diagnostic boundary used by SENTINEL for physical acceptance, production support tickets, and the optional user quality-improvement program. It also defines how large volumes of related reports are grouped and prioritized. It does not authorize release publication or production deployment.

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
- persistent user/device/fingerprint identifiers inside diagnostic event details;
- arbitrary user-entered ticket title/description text as diagnostic breadcrumbs.

Sensitive structured keys are removed on-device. Secret-like free-form exception text is scrubbed. The Core independently validates and rejects diagnostic snapshots containing forbidden identity/secret key/value patterns; client redaction is therefore not the only boundary.

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
- removes expired diagnostic payloads in bounded indexed cleanup batches while retaining ticket metadata/text for support history;
- writes a Core audit event for report creation.

Reports are not automatically converted into public GitHub issues. Private triage happens first through the Core admin quality plane.

## 6. Problem groups, deduplication and scale

Every individual report remains immutable support/evidence material, but routine engineering work is organized around a **problem group** (`quality_issue_clusters`). A group represents one likely underlying defect observed by one or many users.

Automatic grouping is deliberately conservative and deterministic:

1. When diagnostics contain a strong failure signal, the Core derives a fingerprint from category plus technical component/event/error code or exception signal. The app version is **not** part of this fingerprint, so the same defect continuing across releases remains one group while affected versions are counted separately.
2. When there is no strong diagnostic signal, the Core derives a stable fingerprint from normalized low-risk title terms. This is intentionally less aggressive than semantic/AI merging.
3. If two clusters are related but automatic evidence is not strong enough to collapse them, an admin may manually merge the source group into a confirmed target. Source reports are reassigned; they are never discarded.
4. A manually merged fingerprint becomes an alias of one active root group. If an active target is later merged again, all known aliases are flattened to the new root. New reports always resolve an alias chain to the ultimate active root before counters are changed. Missing targets, cycles or excessive alias depth fail closed rather than creating a hidden intermediate work queue.

The grouping path never requires an external AI service and never sends private ticket content to another model/provider.

For each active group the Core maintains:

- category and canonical first title;
- deterministic fingerprint type (`DIAGNOSTIC` or `TEXT`);
- inferred/overridden severity: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`;
- workflow status: `RECEIVED`, `TRIAGED`, `IN_PROGRESS`, `RESOLVED`, `WONT_FIX`;
- report occurrence count;
- distinct affected-user count;
- distinct affected-device count when a bound device exists;
- distinct affected-app-version count;
- first/last-seen timestamps;
- latest app version and exact source SHA when diagnostics provide them;
- a bounded priority score from severity, recurrence and affected-user breadth.

The queue is ordered by priority score and then recent observation time. The priority model intentionally gives severity the largest weight while allowing a widespread medium-severity regression to rise above isolated low-severity reports. A user-selected category is not by itself authority to self-promote a report to `CRITICAL`: automatic `CRITICAL` inference requires a machine-observed crash/process/security/integrity signal. A `SECURITY_PRIVACY` report without such a signal starts at bounded non-critical severity and remains visible for triage. Admin severity override is sticky: once an operator explicitly sets severity, later automatic observations may not silently downgrade or replace that decision.

PostgreSQL has dedicated indexes for active-group priority/status/category, report membership and diagnostic expiry. Distinct user/device/version membership uses separate keyed tables so the Core does not have to scan every report to answer basic impact questions during normal ingestion. Same-fingerprint ingestion serializes through the fingerprint cluster row before occurrence/breadth counters are updated. Manual cluster merges are rare operator actions and use a transaction-scoped PostgreSQL advisory lock plus row locks so competing merge operations cannot create a divergent alias graph while normal ingestion continues to converge on the active root.

A report creation response may return only safe aggregate acknowledgement: opaque problem-group ID, inferred severity and the current related-report count. It never exposes other users, their text or their diagnostics.

## 7. Admin triage

The existing admin security boundary exposes authenticated quality endpoints for both evidence and groups.

Problem-group operations include:

- priority-sorted queue/listing with status/severity/category filters;
- group detail and member-report evidence list;
- group-wide workflow status changes;
- explicit severity override;
- manual merge of confirmed duplicate/related groups.

A group status update propagates to all member reports so one confirmed fix can close a large duplicate population consistently. Individual reports remain inspectable for exceptional evidence or per-report handling.

The Web admin UI presents problem groups as the primary operational queue and the raw reports as a secondary evidence queue. The Web proxy does not persist the admin token.

After triage, an actionable engineering defect may be represented in GitHub/Linear with only the minimum reproduction information needed. Private user text or retained diagnostic payloads must not be copied to public trackers unless separately reviewed and intentionally minimized.

## 8. Physical-device workflow

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

## 9. Production quality-improvement program

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

## 10. Machine-enforced invariants

The contract is regression-tested by `scripts/test_telemetry_contract.py`, Android unit tests, Core quality-report tests, PostgreSQL migration/recovery tests, Web build and the exact-SHA `Physical Test APK` workflow. PostgreSQL tests exercise concurrent same-fingerprint ingestion and alias-chain convergence in addition to ordinary deduplication. Any future change that removes application-ID isolation, enables full production forensic export, enables physical-test remote telemetry, weakens diagnostic consent, exceeds bounded retention, removes secret/identity rejection, loses duplicate-cluster evidence, allows aliases to terminate at a merged intermediate group, permits user category selection alone to assert `CRITICAL`, or bypasses group-level audit/authorization must be treated as a security/privacy-sensitive change.