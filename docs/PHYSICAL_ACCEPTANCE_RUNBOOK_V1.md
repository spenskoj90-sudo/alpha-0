# SENTINEL physical acceptance runbook v1

Status: **ACTIVE**

This runbook is the execution companion to `docs/FINAL_RELEASE_ACCEPTANCE_V1.md`. It standardizes the physical checks that cannot be proven by CI. It does not turn physical observations into automatic PASS claims: the human operator still performs the real test. The final-acceptance tool additionally requires a machine-readable all-`PASS` checkpoint record bound to the exact signed APK, Companion digest and environment before it will build a gate.

## Candidate freeze

Before any physical test:

1. Select one exact protected-`main` source SHA with a completed MAIN PASS.
2. Record the release candidate version and candidate manifest digest.
3. Record the signed release APK SHA-256 when testing release bytes.
4. Record the source-bound packaged Companion archive SHA-256.
5. Never mix APK, Companion, addon, diagnostics or evidence from different source SHAs/candidates.
6. Verify every retained CI artifact is unexpired before the campaign begins.
7. Generate the required checkpoint template for each gate before performing the measured campaign.

The `physicalTest` APK is a diagnostic instrument, not the signed release APK. Use it to reproduce/diagnose Android behavior. Any release gate that claims acceptance against the signed APK must also exercise the exact signed candidate required by `FINAL_RELEASE_ACCEPTANCE_V1.md`.

## Android physical acceptance

Use the exact selected device(s) and Android version(s) intended for release acceptance.

Required observations include:

- installation/launch and upgrade path applicable to the candidate;
- login/session refresh and device binding/proof;
- background/foreground transitions and process recreation;
- network loss/recovery and bounded timeout/error presentation;
- battery/background constraints relevant to supported flows;
- dashboard/device/game navigation;
- quality-report flow with and without diagnostic attachment;
- TalkBack traversal, names/roles/states, focus order and dynamic error/status announcements;
- text scaling and orientation/configuration behavior applicable to the release;
- no hidden permission/security bypass introduced by the test build.

These map one-for-one to the `android-physical` structured checkpoint IDs emitted by the tool. A checkpoint stays `PENDING` until the real observation has been made.

For a failure on the diagnostic build, preserve the full exported forensic trace plus exact APK/source/device/OS identity. For the signed release candidate, preserve the minimum evidence needed for the final `android-physical` gate.

## Packaged Companion host acceptance

On the intended Windows x64 host, using the exact source-bound Companion archive:

- unpack/start through the supported packaged path;
- verify source/version identity before relying on the session;
- establish authenticated ACTIVE Core/Companion health;
- exercise normal reconnect, Core unavailability and recovery;
- verify kill-switch behavior and fail-closed authorization boundary;
- exercise supported launcher/game configuration paths;
- verify packaged overlay/window behavior, click-through/focus and multi-monitor/DPI behavior where applicable;
- exercise clean shutdown/restart and relevant host sleep/resume behavior;
- preserve packaged-host evidence without copying credentials or authentication material.

These observations correspond to the `companion-host` checkpoint template. The final evidence becomes the retained source for that gate.

## Voice/acoustic acceptance

Use the real intended microphone/driver/audio path. Do not satisfy this gate with synthetic CI audio alone.

Check:

- real intended microphone/driver path, not a synthetic-only source;
- intended input device selection and permission path;
- capture start/stop/restart;
- silence, ordinary speech, background noise and relevant device switching;
- expected bounded latency and failure presentation;
- reconnect/recovery after device/driver interruption;
- privacy indicators and explicit capture state;
- no unintended background recording outside the supported flow.

Retain measurements/results, not raw private speech unless the Owner intentionally chooses a controlled test sample. Production quality diagnostics do not capture raw audio by default.

These observations correspond to the `voice-acoustic` checkpoint template.

## Accessibility and visual acceptance

Android:

- TalkBack exploration/traversal;
- control names, roles and state;
- form validation/error announcements;
- focus restoration across navigation/configuration changes;
- large text and applicable contrast/visibility checks.

Windows packaged host:

- keyboard-only operation for supported controls;
- NVDA/JAWS reading and focus behavior as applicable to scope;
- visible focus and state changes;
- overlay positioning/click-through/focus behavior on the intended desktop configuration;
- scaling/DPI and relevant multi-monitor behavior.

These observations correspond to the `accessibility-visual` checkpoint template.

## Exact WoW environment

The WoW WotLK 3.3.5a/private-server L3 test is governed separately by `docs/EXACT_ENVIRONMENT_L3_EVIDENCE_V1.md` and issue #277. Do not replace its independent bundle/validator with a generic manual checklist.

The final `wow-exact-environment` checkpoint document therefore includes checkpoints proving the source-bound packaged host, authenticated ACTIVE handshake, ACTIVE health, persisted checkpoint pair, Core passive-checkpoint acknowledgement and successful L3 bundle validator. The L3 bundle/validator remains the authoritative detailed evidence.

## Failure workflow

When a physical check fails:

1. Do **not** change the affected checkpoint from `PENDING` to `PASS`.
2. Do **not** finalize the checkpoint document or build a final gate record.
3. Preserve exact candidate/source identity.
4. On Android physical-test builds, export the full forensic log after reproducing the measured failure where safe.
5. Preserve relevant Core/Companion bounded evidence and workflow/run identity.
6. Triage the smallest measured defect.
7. Implement a regression test wherever the failure is automatable.
8. Pass exact-HEAD CI, merge under the normal protected-main gate, obtain a new MAIN PASS and new exact-SHA physical-test artifact.
9. Generate new source-bound checkpoint templates for the new candidate and repeat the failed physical scenario.

Never weaken source binding, device proof, authorization, privacy, validation or a required release gate merely to obtain PASS.

## Producing a structured checkpoint record

Before the measured test, create a template bound to the exact release set:

```bash
python scripts/final_release_acceptance.py checkpoint-template \
  --id android-physical \
  --candidate release-candidate.json \
  --apk app-release.apk \
  --companion-sha256-file archive-sha256.txt \
  --environment-id <stable-bounded-environment-id> \
  --device-or-host <bounded-device-or-host-id> \
  --platform <bounded-platform-id> \
  --tool sentinel-physical-acceptance \
  --output android-physical.checkpoints.json
```

The generated statuses are all `PENDING`. They are intentionally not auto-promoted.

After the real test, change only the statuses of checkpoints actually observed to `PASS`. Then ask the repository tool to validate the exact checkpoint set, exact release/environment binding and recompute the canonical digest:

```bash
python scripts/final_release_acceptance.py checkpoint-finalize \
  --input android-physical.checkpoints.json \
  --candidate release-candidate.json \
  --apk app-release.apk \
  --companion-sha256-file archive-sha256.txt \
  --output android-physical.checkpoints.final.json
```

Missing, unknown, duplicated or still-`PENDING` checkpoints are rejected. Do not type or edit `checkpointsDigest` by hand.

## Producing a final gate record

After every required checkpoint is `PASS`, checkpoint finalization succeeds, and the detailed evidence file has been retained externally, bind both to the exact candidate:

```bash
python scripts/final_release_acceptance.py gate \
  --id android-physical \
  --candidate release-candidate.json \
  --apk app-release.apk \
  --companion-sha256-file archive-sha256.txt \
  --environment-id <stable-bounded-environment-id> \
  --checkpoints-file android-physical.checkpoints.final.json \
  --evidence-file <retained-evidence-file> \
  --media-type application/json \
  --recorded-at <UTC-ISO-8601-Z> \
  --output android-physical.gate.json
```

Use the same mechanism with `companion-host`, `voice-acoustic` and `accessibility-visual`. Use the WoW-specific validator/evidence bundle before completing and finalizing the `wow-exact-environment` checkpoints.

The gate record proves exact candidate/evidence binding and required-checklist completeness. It still does not independently prove that a human performed the test; retained evidence and the Owner-authorized final-acceptance workflow preserve that separate real-world claim.

## End of campaign

After final physical testing:

- preserve only the evidence required by release policy;
- remove the `.physicaltest` app and its local forensic data from test devices;
- do not distribute the test APK as the public application;
- keep production diagnostics in the bounded privacy/consent model defined by `docs/DIAGNOSTICS_AND_QUALITY_PROGRAM_V1.md`.
