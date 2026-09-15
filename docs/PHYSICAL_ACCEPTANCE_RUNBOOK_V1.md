# SENTINEL physical acceptance runbook v1

Status: **ACTIVE**

This runbook is the execution companion to `docs/FINAL_RELEASE_ACCEPTANCE_V1.md`. It standardizes the physical checks that cannot be proven by CI. It does not turn physical observations into automatic PASS claims: the human operator still performs the real test, and the existing exact-candidate gate tool binds retained evidence to the signed APK and Companion digest.

## Candidate freeze

Before any physical test:

1. Select one exact protected-`main` source SHA with a completed MAIN PASS.
2. Record the release candidate version and candidate manifest digest.
3. Record the signed release APK SHA-256 when testing release bytes.
4. Record the source-bound packaged Companion archive SHA-256.
5. Never mix APK, Companion, addon, diagnostics or evidence from different source SHAs/candidates.
6. Verify every retained CI artifact is unexpired before the campaign begins.

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

The final evidence becomes the retained source for `companion-host`.

## Voice/acoustic acceptance

Use the real intended microphone/driver/audio path. Do not satisfy this gate with synthetic CI audio alone.

Check:

- intended input device selection and permission path;
- capture start/stop/restart;
- silence, ordinary speech, background noise and relevant device switching;
- expected bounded latency and failure presentation;
- reconnect/recovery after device/driver interruption;
- privacy indicators and explicit capture state;
- no unintended background recording outside the supported flow.

Retain measurements/results, not raw private speech unless the Owner intentionally chooses a controlled test sample. Production quality diagnostics do not capture raw audio by default.

The retained evidence is used for `voice-acoustic`.

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

Retained evidence is used for `accessibility-visual`.

## Exact WoW environment

The WoW WotLK 3.3.5a/private-server L3 test is governed separately by `docs/EXACT_ENVIRONMENT_L3_EVIDENCE_V1.md` and issue #277. Do not replace its independent bundle/validator with a generic manual checklist.

## Failure workflow

When a physical check fails:

1. Do **not** mark the gate PASS.
2. Preserve exact candidate/source identity.
3. On Android physical-test builds, export the full forensic log after reproducing the measured failure where safe.
4. Preserve relevant Core/Companion bounded evidence and workflow/run identity.
5. Triage the smallest measured defect.
6. Implement a regression test wherever the failure is automatable.
7. Pass exact-HEAD CI, merge under the normal protected-main gate, obtain a new MAIN PASS and new exact-SHA physical-test artifact.
8. Repeat the failed physical scenario on the new candidate.

Never weaken source binding, device proof, authorization, privacy, validation or a required release gate merely to obtain PASS.

## Producing a final gate record

After the real test passes and its evidence file has been retained externally, bind it to the exact candidate with the existing tool:

```bash
python scripts/final_release_acceptance.py gate \
  --id android-physical \
  --candidate release-candidate.json \
  --apk app-release.apk \
  --companion-sha256-file archive-sha256.txt \
  --environment-id <stable-bounded-environment-id> \
  --evidence-file <retained-evidence-file> \
  --media-type application/json \
  --recorded-at <UTC-ISO-8601-Z> \
  --output android-physical.gate.json
```

Use the same mechanism with `companion-host`, `voice-acoustic` and `accessibility-visual`. Use the WoW-specific validator/evidence bundle before producing `wow-exact-environment`.

The gate record proves exact candidate/evidence binding and a declared PASS. It does not independently prove that a human performed the test; retained evidence and the Owner-authorized final-acceptance workflow preserve that separate claim.

## End of campaign

After final physical testing:

- preserve only the evidence required by release policy;
- remove the `.physicaltest` app and its local forensic data from test devices;
- do not distribute the test APK as the public application;
- keep production diagnostics in the bounded privacy/consent model defined by `docs/DIAGNOSTICS_AND_QUALITY_PROGRAM_V1.md`.
