# SENTINEL audit closure evidence — 2026-08-13

## Gate A — external secrets / keystore

Gate A is CLOSED by the owner through GitHub Actions Secrets. The private keystore, passwords and private key are not committed or exposed in chat.

Active CI secret contract:
- `ANDROID_KEYSTORE_BASE64`
- `ANDROID_KEYSTORE_PASSWORD`
- `ANDROID_KEY_ALIAS` = `sentinel_release`
- `ANDROID_KEY_PASSWORD`

The replacement keystore is PKCS12 and uses the same password for store and key entry. The previous PKCS12 keystore was retired after `keytool -keypasswd` confirmed that changing an individual entry password is unsupported for PKCS12.

Active release certificate SHA-256 fingerprint:
`43:5A:F3:E5:7E:0B:0D:1F:AE:38:6B:B4:52:C3:45:F9:3A:4F:FD:83:56:AE:E9:D8:63:F5:EF:69:DD:26:BD:C1`

The superseded fingerprint `1D:22:78:D0:BE:AB:77:7F:66:E1:96:15:47:F5:76:ED:51:6D:59:82:6D:75:81:B4:67:27:15:90:01:70:76:08` is no longer valid and must not be used as release evidence.

## External boundary — not part of CI closure

- **Production-level backup/restore:** OPEN; requires a real production or production-equivalent staging database, representative backup set, restore target, credentials, network access, and evidence that the restored service is functionally equivalent. CI smoke restore is not relabeled as production evidence.
- **Production load characterization:** OPEN; requires real staging/production-equivalent infrastructure, representative traffic/data profile, agreed SLOs, load generator access, and monitoring. No production load is simulated or claimed here.
- **Live Stripe:** intentionally untouched.
- **Google Play App Signing:** owner-managed external release step; not simulated by CI.

## Release baseline

The prior owner-supplied P0 baseline was `8888c17c64af6a981d054dce7f74ca3bb6b4dada`. P0 items explicitly accepted by the owner are not reopened. Final release evidence must use the exact final HEAD recorded in the final report.

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
| GitHub hosted macOS ARM64 emulator | HVF was confirmed unsupported in the relevant virtualized environment; retrying does not solve the established infrastructure cause | REJECTED |
| Firebase Test Lab | Managed Android infrastructure, removes local KVM/HVF dependency, supports instrumentation with uploaded APK/test APK, and returns a machine-readable result usable as a CI gate | **SELECTED** |
| Self-hosted KVM runner | Maximum control and Linux parity, but requires human-owned server, virtualization support, runner lifecycle, patching and security isolation | Requires human infrastructure decision; not introduced |

The active workflow uploads the debug app and instrumentation APK as CI artifacts, authenticates to Google Cloud through GitHub Actions Secrets, executes `gcloud firebase test android run`, stores the JSON result as an artifact, and uses the command exit status as the instrumentation gate.

## Android signing evidence policy

The workflow performs a diagnostic `keytool -list` against the decoded keystore using the store password, then runs `assembleRelease`. Only after a successful release APK exists does `apksigner verify --print-certs` extract the actual APK certificate SHA-256 and compare it to the active owner-supplied fingerprint. A skipped or unexecuted fingerprint step is never considered PASS.

## Reproducible deployment — failure and fix

Two exact-head comparisons were allowed to fail and their logs were inspected.

### Failure 1 — nondeterministic Python wheel

Build & Test run `31679499650`, job `94381891358`:
- artifact A image ID: `sha256:9de063341a5a4cb401d3d72a6cfad82eccca73dda0d8591cf1059d31992652c2`
- artifact B image ID: `sha256:a0920be1a5f050e5a6104c7c22c13eef522b005a58aac0f755f04e430f714a42`
- locally built wheel hashes differed.

Fix: pin base digest, pip `26.2.1`, setuptools `80.9.0`, disable build isolation, and set deterministic Python/build environment variables.

### Failure 2 — runtime user creation remained nondeterministic

Build & Test run `31679821312`, job `94382634367`:
- the locally built wheel was byte-identical in both builds;
- the first differing final-image layer was the runtime `addgroup/adduser` layer.

Root cause: runtime user/group creation mutates `/etc/passwd`/`/etc/group` with build-instance metadata.

Fix: remove runtime user/group creation and run the container as fixed numeric non-root identity `10001:10001`.

A new exact-head reproducibility comparison is required. Only a green image-ID and layer-digest comparison can move this gate to VERIFIED.

## P1 implementation/evidence status

| P1 item | Status | Evidence / remaining gate |
|---|---|---|
| session refresh/revoke | VERIFIED | existing API tests cover refresh rotation/replay and revoke |
| device rotate/revoke | IMPLEMENTED + INTEGRATION TESTED | final exact-head CI evidence must be tied to the final release HEAD |
| entitlement engine | VERIFIED | deterministic fail-closed engine and unit tests |
| billing runtime | VERIFIED | provider-neutral state machine; live Stripe intentionally excluded |
| outbox | VERIFIED | deterministic state machine with duplicate protection/retry/completion tests |
| worker manager | VERIFIED | retry/complete semantics tested |
| RLS policies | VERIFIED | explicit policies and policy tests; production role/context configuration remains operational |
| SCA/dependency report | VERIFIED | exact-SHA P1 Evidence workflow produces Python, npm and Gradle dependency artifacts |
| reproducible deployment | IMPLEMENTED; final exact-head comparison pending | final proof requires a green independent rebuild comparison |
| performance/load baseline | VERIFIED baseline | regression guards + P1 evidence workflow; production load characterization remains OPEN |
| backup/restore | VERIFIED smoke only | production-level evidence remains OPEN and intentionally not simulated |

## Full Validation evidence

Final release evidence must reference only the final exact HEAD after all signing and instrumentation gates are green. Prior runs are retained as diagnostic evidence and are not mixed into the final PASS/VERIFIED claim.

## Evidence rule

This document never turns a non-green or unavailable external gate into PASS. Every final gate must reference the exact commit and its actual CI/runtime artifact.
