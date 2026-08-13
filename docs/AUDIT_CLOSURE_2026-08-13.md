# SENTINEL audit closure evidence — 2026-08-13

## Gate A — external secrets / keystore (separate from code/CI)

The following external values/files are required only to close the release-signing/keystore gate. They must **not** be committed to Git:

1. Android release keystore file (`.jks` or `.keystore`) or an equivalent binary supplied through a protected file channel.
2. Keystore store password.
3. Key alias.
4. Key password.
5. A SHA-256 fingerprint of the supplied keystore/certificate, so the received material can be verified without exposing the private key.
6. If CI must validate the same material: the exact secret names/format expected by the workflow (`base64` keystore payload plus the three password/alias values), supplied through GitHub Actions Secrets or another protected channel.

Do **not** paste private key material, passwords, or secret values into this chat. A protected file/secret channel is preferred; non-secret fingerprints/metadata may be provided in chat while secret values remain in the repository secret manager.

## External boundary — explicitly not pursued in this pass

- **Gate A:** OPEN; owner will provide the keystore/secrets through a protected channel.
- **Production-level backup/restore:** OPEN; requires a real production or production-equivalent staging database, representative backup set, restore target, credentials, network access, and evidence that the restored service is functionally equivalent. CI smoke restore is not relabeled as production evidence.
- **Production load characterization:** OPEN; requires real staging/production-equivalent infrastructure, representative traffic/data profile, agreed SLOs, load generator access, and monitoring. No production load is simulated or claimed here.
- **Live Stripe:** intentionally untouched.

## Release baseline

The prior owner-supplied P0 baseline was `8888c17c64af6a981d054dce7f74ca3bb6b4dada`. P0 items explicitly accepted by the owner are not reopened. Code changes for this continuation are isolated on `p1-close-2026-08-13`; the final release evidence must use the exact final HEAD recorded in the final report.

## P0 implementation status — accepted / not reopened

| P0 item | Status | Evidence policy |
|---|---|---|
| PostgreSQL persistence | ACCEPTED | owner-accepted; existing CI evidence remains authoritative |
| Authorization bypass fix | ACCEPTED | owner-accepted; existing security suite remains authoritative |
| Negative security suite | ACCEPTED | owner-accepted; existing suite remains authoritative |
| Core/Web validation | ACCEPTED | owner-accepted; existing green jobs remain authoritative |

## Android instrumentation infrastructure decision

The previous Linux hosted emulator path is not retried. Its confirmed failure mode was missing `/dev/kvm`, persistent `adb: device offline`, and final ADB cleanup exit code `224` after the emulator eventually reported boot completion.

### Alternatives evaluated

| Option | Assessment | Decision |
|---|---|---|
| GitHub hosted macOS Intel (`macos-15-intel`) | Minimal workflow change; existing emulator runner remains usable; Android Emulator uses macOS Hypervisor.framework; no new cloud credentials | **SELECTED** |
| Firebase Test Lab | Strong cloud/real-device coverage, but requires Firebase/GCP project setup, IAM, Cloud Storage permissions, credentials and potentially billing; larger workflow change | Alternative, not selected for this closure pass |
| Self-hosted KVM runner | Maximum control and Linux parity, but requires human-owned server, KVM/virtualization support, runner lifecycle, patching and security isolation | Requires human infrastructure decision; not introduced |

The selected implementation changes only the instrumentation job runner to `macos-15-intel`, retains API 35/x86_64 and the existing Gradle instrumentation command, and explicitly records the macOS virtualization check. This is the lowest-change path that removes the exact Linux KVM failure without introducing external credentials.

## P1 implementation/evidence status

| P1 item | Status | Evidence / remaining gate |
|---|---|---|
| session refresh/revoke | VERIFIED | existing API tests cover refresh rotation/replay and revoke |
| device rotate/revoke | IMPLEMENTED + INTEGRATION TESTED; final exact-head CI evidence pending | rotate atomically revokes old device/session path, creates new key binding/challenge; new integration test verifies old-session denial, new-key proof, new-session authorization, revoke, and final denial |
| entitlement engine | VERIFIED | deterministic fail-closed engine and unit tests |
| billing runtime | VERIFIED | provider-neutral state machine; live Stripe intentionally excluded |
| outbox | VERIFIED | deterministic state machine with duplicate protection/retry/completion tests |
| worker manager | VERIFIED | retry/complete semantics tested |
| RLS policies | VERIFIED | explicit policies and policy tests; production role/context configuration remains an operational boundary |
| SCA/dependency report | VERIFIED | exact-SHA P1 Evidence workflow produces Python, npm and Gradle artifacts |
| reproducible deployment | IMPLEMENTED; final exact-head comparison pending | CI performs independent no-cache Docker rebuild and compares image ID plus root filesystem layers |
| performance/load baseline | VERIFIED baseline | regression guards + P1 evidence workflow; production load characterization remains OPEN |
| backup/restore | VERIFIED smoke only | production-level evidence remains OPEN and is intentionally not simulated |

## Full Validation evidence

For the continuation branch, Build & Test run `31679419386` at exact HEAD `61bcfd085cad6d1eb706da1399bc45f4415274e1` had repository verification and core tests green while Android build, PostgreSQL, Web, and the macOS instrumentation job were still executing at the time of this document revision. The core job recorded 32 passed tests, including the new device lifecycle integration test.

No final gate is marked VERIFIED here until its exact-head CI job has completed successfully. The final report must replace the pending statuses with the final exact HEAD and completed run IDs.

## Evidence rule

This document records implementation and evidence mapping only. It never turns a non-green or unavailable external gate into PASS. Every final gate must reference the exact commit and its actual CI/runtime artifact.

## External boundaries

Production credentials, live Stripe integrations, live infrastructure and external Android keystore secrets are intentionally not touched by repository automation. Gate A and production operational evidence are independent gates.
