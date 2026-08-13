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

## Reproducible deployment — failure and fix

Two exact-head comparisons were allowed to fail and their logs were inspected.

### Failure 1 — nondeterministic Python wheel

Build & Test run `31679499650`, job `94381891358`:
- artifact A image ID: `sha256:9de063341a5a4cb401d3d72a6cfad82eccca73dda0d8591cf1059d31992652c2`
- artifact B image ID: `sha256:a0920be1a5f050e5a6104c7c22c13eef522b005a58aac0f755f04e430f714a42`
- locally built wheel hashes differed: `9f7c810fe627bfb1c46bcffd60b4690f9f16ddd9f50241c422fef5efd827f89e` vs `3982f36cfdf91a1666c52d842a815792e1c1bf60e917b3c2fc7d5a1b38c28d42`.

Fix: pin base digest, pip `26.2.1`, setuptools `80.9.0`, disable build isolation, and set deterministic Python/build environment variables.

### Failure 2 — runtime user creation remained nondeterministic

Build & Test run `31679821312`, job `94382634367`:
- the locally built wheel was now identical in both builds (`c60960a29f...`), proving the Python wheel issue was fixed;
- the first differing final-image layer was the runtime user/group creation layer (`RUN addgroup --system sentinel && adduser --system --ingroup sentinel sentinel`);
- artifact A and B therefore still had different image IDs and all following copied layers diverged.

Root cause: the runtime `addgroup/adduser` mutation changes `/etc/passwd`/`/etc/group` and associated filesystem metadata during the image build. That mutation is time/build-instance dependent even after SOURCE_DATE_EPOCH controls were applied.

Fix: remove runtime user/group creation entirely and run the container as fixed numeric non-root identity `10001:10001`. The application only needs read access to its packaged files and writes state to PostgreSQL, so no writable application filesystem ownership is required.

A new exact-head reproducibility comparison is required. Only a green image-ID and layer-digest comparison can move this gate to VERIFIED.

## P1 implementation/evidence status

| P1 item | Status | Evidence / remaining gate |
|---|---|---|
| session refresh/revoke | VERIFIED | existing API tests cover refresh rotation/replay and revoke |
| device rotate/revoke | IMPLEMENTED + INTEGRATION TESTED; final exact-head CI evidence pending | rotate atomically revokes old device/session path, creates new key binding/challenge; integration test verifies old-session denial, new-key proof, new-session authorization, revoke, and final denial |
| entitlement engine | VERIFIED | deterministic fail-closed engine and unit tests |
| billing runtime | VERIFIED | provider-neutral state machine; live Stripe intentionally excluded |
| outbox | VERIFIED | deterministic state machine with duplicate protection/retry/completion tests |
| worker manager | VERIFIED | retry/complete semantics tested |
| RLS policies | VERIFIED | explicit policies and policy tests; production role/context configuration remains an operational boundary |
| SCA/dependency report | VERIFIED | exact-SHA P1 Evidence workflow produces Python, npm and Gradle artifacts |
| reproducible deployment | IMPLEMENTED; two concrete failures diagnosed and fixed; final exact-head comparison pending | final proof requires a green comparison after the fixed numeric non-root runtime identity |
| performance/load baseline | VERIFIED baseline | regression guards + P1 evidence workflow; production load characterization remains OPEN |
| backup/restore | VERIFIED smoke only | production-level evidence remains OPEN and is intentionally not simulated |

## Full Validation evidence

Final release evidence must reference only the final exact HEAD after the deterministic-build fix. Prior runs are retained as diagnostic evidence and are not mixed into the final PASS/VERIFIED claim.

## Evidence rule

This document records implementation and evidence mapping only. It never turns a non-green or unavailable external gate into PASS. Every final gate must reference the exact commit and its actual CI/runtime artifact.

## External boundaries

Production credentials, live Stripe integrations, live infrastructure and external Android keystore secrets are intentionally not touched by repository automation. Gate A and production operational evidence are independent gates.
