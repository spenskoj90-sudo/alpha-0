# SENTINEL audit closure evidence — 2026-08-13

## Gate A — external secrets / keystore (separate from code/CI)

The following external values/files are required only to close the release-signing/keystore gate. They must **not** be committed to Git:

1. Android release keystore file (`.jks` or `.keystore`) or an equivalent binary supplied through a protected file channel.
2. Keystore store password.
3. Key alias.
4. Key password.
5. A SHA-256 fingerprint of the supplied keystore/certificate, so the received material can be verified without exposing the private key.
6. If CI must validate the same material: the exact secret names/format expected by the workflow (`base64` keystore payload plus the three password/alias values), supplied through GitHub Actions Secrets or another protected channel.

Do **not** paste private key material, passwords, or secret values into this chat. A protected file/secret channel is preferred; if only text transfer is available, provide non-secret fingerprints/metadata here and place secret values in the repository's secret manager.

## Release baseline

Selected baseline: `sentinel-1.0.0-rc1-final` at the exact release-candidate HEAD. P0 items explicitly accepted by the owner are not reopened.

- `main`: `70702f3f992097cea9553c406b5d8febb3a47539`
- P0 reference HEAD supplied for this pass: `8888c17c64af6a981d054dce7f74ca3bb6b4dada`
- PR #19 head: `sentinel-1.0.0-rc1-final`

## P0 implementation status — accepted / not reopened

| P0 item | Status | Evidence policy |
|---|---|---|
| PostgreSQL persistence | ACCEPTED | owner-accepted; existing CI evidence remains authoritative |
| Authorization bypass fix | ACCEPTED | owner-accepted; existing security suite remains authoritative |
| Negative security suite | ACCEPTED | owner-accepted; existing suite remains authoritative |
| Core/Web validation | ACCEPTED | owner-accepted; existing green jobs remain authoritative |

## Full Validation at supplied HEAD

At the supplied HEAD, Build & Test run `31675634466` completed the following successfully: Android build/tests, PostgreSQL integration/recovery, Web build, Container build, Deployment smoke/health, and repository verification. The dedicated Android instrumentation job failed on the hosted runner during emulator handling: the emulator reported no KVM access, ADB repeatedly reported `device offline`, and final cleanup failed with ADB exit code `224` after boot completed. The job was rerun once; at the time this document was written the rerun was still in progress. No code-level instrumentation failure has been observed in the available log.

Important exact-HEAD distinction: PR-triggered Build & Test checks out the synthetic merge commit `e707dc43e4b34060217c2319dccb5b3ef2022adb`, whose first parent is the requested release-candidate HEAD. The dedicated Android push workflow can validate the branch head directly. Evidence from a synthetic merge commit is never relabeled as exact-head evidence.

## P1 implementation/evidence status

| P1 item | Status | Evidence / remaining gate |
|---|---|---|
| session refresh/revoke | IMPLEMENTED + TESTED | existing API tests cover refresh rotation/replay and revoke |
| device rotate/revoke | PARTIAL | Android key lifecycle exists; server API lifecycle extension still requires production-path integration test |
| entitlement engine | IMPLEMENTED + UNIT TESTED | deterministic fail-closed engine added |
| billing runtime | IMPLEMENTED + UNIT TESTED | provider-neutral state machine; live Stripe intentionally excluded |
| outbox | IMPLEMENTED + UNIT TESTED | deterministic state machine added |
| worker manager | IMPLEMENTED + UNIT TESTED | retry/complete semantics tested |
| RLS policies | IMPLEMENTED + POLICY TEST | explicit policies added; production context/role configuration remains an operational gate |
| SCA/dependency report | AUTOMATED | exact-SHA P1 Evidence workflow produces pip/npm/Gradle artifacts |
| reproducible deployment test | PARTIAL | container/deployment smoke is green; deterministic reproducibility needs a successful artifact comparison run |
| performance/load baseline | AUTOMATED | existing regression guards + P1 evidence workflow capture output; full load profile remains separate |
| backup/restore evidence | SMOKE ONLY | CI backup/restore smoke is green; production-level evidence still requires production-equivalent target access |

## Evidence rule

This document records implementation and evidence mapping only. It never turns a non-green or unavailable external gate into PASS. Every final gate must reference the exact commit and its actual CI/runtime artifact.

## External boundaries

Production credentials, live Stripe integrations, live infrastructure and external Android keystore secrets are intentionally not touched by repository automation. Gate A is independent and must be closed separately.
