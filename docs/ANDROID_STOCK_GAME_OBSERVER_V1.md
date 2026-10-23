# Android stock-game observer v1

**Status:** private diagnostic/development pilot; exact-device acceptance pending.
**Direction:** Owner authorization, 2026-10-02; tracking #430.
**Implementation baseline:** `46de12ce74340c0f06159d3a94a735dc4151d0a1`.

## Scope and evidence

This is the first real Android screen-source implementation for an ordinary installed
Shattered Pixel Dungeon APK. It does not repackage the game, load a game module,
read game memory, inspect private files, inject code, dispatch gestures or call
the Core Action Gateway. `AUTOMATIC_EXECUTION_DISABLED` remains in force.

The user opens Games → Android game test in diagnostic/development builds.
Detection uses one explicit package query, observes installed version name/code,
and offers the game's own launch intent. Package metadata is not publisher-signature
verification, an entitlement, capture-source verification or an L3 capability.
The diagnostic build also reads the installed package's single current APK
signer certificate SHA-256. Missing/multiple current signers are recorded as
unknown; signer history and official publisher identity are NOT verified.
This digest binds observed installed-package metadata, not the app selected
by Android's MediaProjection chooser.
The release build has no entry point and its service is manifest-disabled and
runtime-denied. Build type never grants account/admin or game-action authority.

Only Android 14+ is supported for this pilot. The disclosure asks the user to
select **one app: Shattered Pixel Dungeon** in Android's consent chooser. Android
also offers whole-display capture. The public MediaProjection API does not attest
the selected package to SENTINEL; the source therefore remains user-selected and
**UNVERIFIED**. Do not describe this pilot as enforcing app-only capture.

## Capture lifecycle

- A fresh Android consent result is required for every session.
- The observed installed package version **name**, version code and current signer digest
  are rechecked after the consent chooser and again on foreground-service start;
  if any field changed, the session is denied. This is package-metadata
  time-of-check/time-of-use fencing, **not** capture-source attestation.
- A non-exported `mediaProjection` foreground service owns one projection and one
  virtual display. It never persists a projection token or restarts itself.
- Resize reuses that virtual display, replaces the image surface and invalidates
  pending recognition. Capture dimensions are bounded to a 1280-pixel longest edge.
- A two-image reader drains latest frames. Recognition permits one in-flight task
  and starts at most once per two seconds. No unbounded frame/event queue exists.
- Stop is available in the screen and the foreground notification when Android
  displays notifications. Android's own screen-sharing/task controls remain valid.
  The pilot does not require notification permission or bypass notification settings.
- Capture stops after five minutes even without new frames, on screen lock, token
  revocation, task/service destruction, or a local account/session boundary.
- The service checks local device-session presence and installed game/version every
  30 seconds. Server revocation is acted on when the existing auth transport receives
  invalidation; offline capture does not claim immediate knowledge of server changes.
- Capture Stop clears current and historical numeric candidates. Old session,
  hidden-source, resized-source and stale OCR callbacks cannot revive current state.

## Observation and privacy boundary

This source is local and read-only; it deliberately does not use the existing
offline Core event queue. Frames and raw OCR text are not logged, saved or uploaded
by SENTINEL. Only the upper-left HUD region is copied into a bounded bitmap;
the full frame is not copied or persisted. ImageReader images and recognition
bitmaps are released. Android secure-window/capture restrictions are respected.
Observation timestamps use monotonic local image-acquisition time, not an
authoritative game-event timestamp; no UGS/live-combat latency claim is made.

Bundled ML Kit `com.google.mlkit:text-recognition:16.0.1` provides on-device digit/
Latin-script OCR without a first-use model download. It is not external inference
and does not claim Cyrillic-text recognition. SDK operational data handling follows
Google's SDK terms; this document does not claim zero SDK operational telemetry.

The initial parser considers one plausible health ratio in a constrained HUD region,
including shield notation, and rejects malformed/impossible/ambiguous values.
The geometry is **uncalibrated** until a physical stock-game test. Parsed values are
explicit **INFERENCE**, never authoritative game health. A timestamped historical
candidate can be viewed after returning to SENTINEL; it is labelled potentially
wrong/outdated and is separate from current state. Current health becomes unknown
when content is hidden or its observation is more than five seconds old. Combat,
targets, abilities and recommendations remain unknown/unimplemented.

The upstream source inspected for format context was
`00-Evan/shattered-pixel-dungeon@2bb34a4e91d29c8785a9363cad6ddfe5122b1d4f`
(source version 4.0.0 / code 912). No upstream code/assets were copied. That source
SHA is **not** proof of the version installed on the Owner's phone. Each session
records the actually observed installed version in bounded diagnostic metadata.
No game/version has L3 screen-recognition evidence yet.

## Validation and progression

### Numeric calibration preparation

`scripts/game_observer_calibration.py` summarizes at most 32 opt-in numeric
comparisons for one exact source/APK/package/version/signer, installed game
version, language/HUD and a narrowly allowlisted physical-test environment. It accepts only structured
health ratios and age/sequence metadata; extra fields including pixels or raw
OCR are rejected. Only the explicit Infinix/API34 and Xiaomi/API35 evidence
pairs are supported. Input/summary schema v2 requires a lowercase 64-character
`game.signerSha256` from the locally observed current APK signer. Unknown or
ambiguous signer prevents creation of a v2 report; historic v1 records cannot
be silently upgraded. The certificate digest must be reconciled with the
Owner-exported diagnostics and exact installation evidence, not guessed. Input is bounded to 32 KiB. Missing and stale observations
remain in the agreement denominator; fresh mismatches report absolute error.
The 95% lower bound describes sample agreement uncertainty, not recognizer
confidence. Synthetic records must be labelled synthetic.

Every output is `PENDING_PHYSICAL_REVIEW`, source `UNVERIFIED`, recognizer
`UNCALIBRATED`, capability unavailable. A physical label or perfect agreement
cannot attest the selected app or promote capability. The report records
asserted source/byte identity and an input digest; these are checked against
retained artifact/diagnostics evidence during review, not trusted by declaration.

The engineer constructs the bounded input from the exact retained manifest and
Owner-opted-in numeric ground truth after a real capture campaign; the Owner
does not need Python or a PC. Record one visible health ratio in the ordinary
game, then compare SENTINEL's labelled candidate and its age. Keep incorrect,
missing and stale examples. Do not enable recommendations or input merely to
collect these records, and do not export full frames/raw OCR by default.

Run in the engineering workspace:

```text
python scripts/game_observer_calibration.py --input numeric-samples.json --output calibration-summary.json
```

The runnable three-step offline action fixture and separate v1 migration boundary
are described in `GAME_ACTION_OFFLINE_V1.md`. They do not change this observer or
the physical prerequisites below.

JVM tests cover consent/source-state gating, Stop, deadlines without frames,
prior-session callbacks, freshness/order, resize/hide invalidation, independent
historical observations, bounded geometry, missing/malformed/ambiguous ratios and
shield separation. Instrumentation covers missing-game denial, explicit consent,
and accessible Stop in a paused capture state; these UI fixtures are not live-game
or MediaProjection acceptance.

Before physical testing: exact-SHA Android build/unit/instrumentation and repository
CI must pass. Then use one exact protected-main diagnostic APK with its manifest,
hash and signer evidence. Physical checks on the Infinix API34 device must establish:

1. Unchanged ordinary game remains playable with SENTINEL stopped.
2. Installed package/version is reported; consent cancellation produces no capture.
3. Single-app selection, visible frame processing and actual HUD recognition are tested.
4. Hidden source, landscape/portrait, screen lock, system revoke, Stop and task removal
   terminate/invalidate correctly; restarting requires fresh consent.
5. Diagnostics contain identity, version, frame counts and stop reasons, never pixels
   or raw text. Export is Owner-initiated through the existing diagnostic path.

Next implementation stages are actual game-profile calibration, presentation-only
in-game recommendations, and a separately authorized/tested user-confirmed action
executor. Bounded deterministic automation comes after those stages. Autonomous
combat is an architecture direction, not an available Android capability.
SOURCE, BUILD, RUNTIME, OWNER-VISIBLE, OWNER-ACCEPTED and RELEASE-ACCEPTED remain separate.

## Primary references

- [Android MediaProjection](https://developer.android.com/media/grow/media-projection)
- [ML Kit Android text recognition](https://developers.google.com/ml-kit/vision/text-recognition/v2/android)
- [Stock game source](https://github.com/00-Evan/shattered-pixel-dungeon)
- [Game integration and automation research](https://drive.google.com/file/d/110Cj16l3vR6HGd-Qz8s1At8VfznEGc5B/view)

## Phone-only numeric calibration collection — 2026-10-03

The diagnostic observer screen now accepts an explicit user-entered current/maximum health comparison. Pressing **Save numeric comparison to diagnostics** records at most 32 opt-in numeric samples per local campaign, tied to the locally observed installed version, candidate age, campaign ID and source UNVERIFIED. Each successful comparison additionally stores the ephemeral capture UUID, increasing completed-frame sequence, monotonic frame acquisition time and monotonic Save time. A failed diagnostic write does not consume the frame, and an older/duplicate frame cannot be saved later in the same campaign. Both frame acquisition and Save monotonic clocks must also be nondecreasing across successfully stored comparisons; invalid chronology is rejected before logging, consistent with offline import. A rejected/failed write does not advance either clock fence. The process-local campaign ID, successfully recorded count and one-frame-per-sample fence survive Android Activity/Compose recreation during the same foreground capture (including rotation); starting a different capture, changing installed identity or stopping/revoking capture clears this state. Process death does not restore a stopped capture or its campaign. This metadata is **not** an Android app-source, frame-content or publisher attestation. It stores no pixels/raw OCR and does not upload automatically. The ordinary observer still does not persist numeric candidates by itself. Missing/stale candidates are retained for the denominator; changing installed identity (including its observed current signing certificate)
disables comparisons against old candidate identity. The digest is diagnostic
provenance and never attests which application was captured. Export uses existing Owner-initiated diagnostics. Engineer reconciles exact manifest/signer/device/game/HUD and constructs the bounded calibration input; UI labels/user entries are not physical or app-source attestations. Recommendations, semantic input and ARM stay unavailable until the prerequisite physical calibration and target/session binding are proven.

## Bounded diagnostic-export import — 2026-10-14

`scripts/game_observer_diagnostics_import.py` accepts an **Owner-initiated**
`sentinel_forensic_diagnostics.jsonl.gz` export and produces the strict v2
numeric **summary**, without saving a raw intermediary. This is an offline
engineering tool; the Android app does not auto-upload diagnostics. It reads at
most 2 MiB decompressed and 4,000 JSONL records, selects only explicit
`GAME/CALIBRATION_NUMERIC_SAMPLE/OBSERVED` events, and never copies other
events, exception stacks, arbitrary details, pixels, raw OCR or credentials.

An export with more than one campaign requires an explicit UUID selection.
Each selected campaign must begin with sequence 1, be contiguous, have at most
32 samples, and share one installed game package/version/signer SHA-256.
Frame-bound exports from this implementation also require one canonical capture UUID,
strictly increasing completed-frame numbers, nondecreasing monotonic capture/Save
timestamps, and exact `age_ms == sample_saved_at_ms - frame_captured_at_ms`.
Missing, older or inconsistent frame provenance **fails closed**, including exports
from older APKs without these fields; historical records are never silently upgraded.
The v2 numeric summary adds `frameTraceDigestSha256`: a hash of the selected
campaign's capture UUID, frame numbers and timestamps for later comparison to the
retained private export, **not** the raw capture ID and not a trusted attestation.
Incomplete/ambiguous samples, changed signers, malformed input, invalid
reference data or an existing output path **fail closed**. Numeric rows still
include missing and stale observations in the denominator. An observed signer
is diagnostic metadata, not publisher identity or MediaProjection source proof.

Example from a controlled engineering workspace (the Owner needs **no PC**):

```bash
python scripts/game_observer_diagnostics_import.py \
  --diagnostics sentinel_forensic_diagnostics.jsonl.gz \
  --output calibration-summary.json \
  --source-sha EXACT_40_HEX_BUILD_SHA \
  --apk-sha256 EXACT_64_HEX_APK_DIGEST \
  --signer-sha256 EXACT_64_HEX_SENTINEL_APK_SIGNER \
  --apk-version-code EXACT_ANDROID_VERSION_CODE \
  --game-signer-sha256 EXACT_64_HEX_OBSERVED_GAME_SIGNER \
  --language ru --hud portrait-upper-left \
  --device "Xiaomi 25028PC03G" --api 35
```

The engineer must reconcile the command's build/APK/signature assertions with
the independently retained **exact SHA artifact manifest**; those arguments
are not attestations by themselves. Device model/API and language/HUD are
operator assertions too. If diagnostics omit any samples due to ring rotation,
a complete calibration cannot be reconstructed; do not selectively relabel the
remaining rows as a full campaign or fabricate values. Every summary remains
`PENDING_PHYSICAL_REVIEW` / `UNVERIFIED` / `UNCALIBRATED`,
`capabilityAvailable=false`. No game-input action or recommendation is enabled.

## Xiaomi Android 15 opt-in physical diagnostics — 2026-10-22

Owner exported a privately retained forensic diagnostics archive for protected-main
source `dd0606a507d9b779c0480e9b6683120d7d82d57a`. The GitHub Physical Test
APK artifact manifest identifies versionCode `100000718`, and its actual APK
SHA-256 matches that manifest. The export's PROCESS_START and PACKAGE_SIGNER
metadata agree with the exact source SHA, app version and single APK signer.
The observed environment is `Xiaomi 25028PC03G`, Android API 35, with the
installed Shattered Pixel Dungeon version `4.0.2` / code `922`.
Observed game signer is consistent within the export; this is not proof of
publisher identity or of the MediaProjection-selected application.

The first opt-in calibration campaign had four ordered completed-frame samples:
three numeric OCR outputs equal the manually entered values, and one OCR miss.
**All four samples were 5.8–7.7 seconds old at Save**, above the five-second
live-freshness threshold: zero qualifying fresh exact matches, four stale,
no live recognizer accuracy confidence and no action readiness. The first
capture stopped at the five-minute limit (102 processed frames); a second
was revoked (21 frames). This test confirms a functioning capture/consent and
opt-in diagnostics path, not game-source attestation, on-screen calibration
acceptance or real-time recommendation timing.

The importer now requires explicit `--device` and `--api`, accepts only
the evidence-scoped old Infinix/API34 and Xiaomi/API35 pairs, and cross-checks
the export's own PROCESS_START and PACKAGE_SIGNER against independently
reviewed artifact identity assertions. This rejects mixing devices, APKs and
diagnostics before summarization; it is not cryptographic hardware attestation.
Do not include raw logs, private session/capture UUIDs or raw pixels in
repository artifacts.

**Promotion remains blocked:** all outputs stay `PENDING_PHYSICAL_REVIEW`,
`UNVERIFIED`, `UNCALIBRATED` and `capabilityAvailable=false`. Recommend
a non-automatic guidance path only once live source/version and current
freshness are validated; a separately gated and reversible action executor
requires explicit on-device consent, foreground app/source validation, runtime
Stop, TTL, replay protections and verified single-action dry runs. Never
enable game input automatically from this historical diagnostic set.

## Separating OCR callback latency from manual Save age

Following the 2026-10-22 Xiaomi/API35 opt-in export, three historic numeric
matches and one OCR miss were observed, but all four rows were stale
(5.8–7.7 seconds since acquisition when the user pressed Save). That age
**does not establish OCR processing latency**: the user must switch from
the game and type a manual comparison into SENTINEL.

The observer now records `lastCompletedOcrAt` and the corresponding
nonnegative `lastOcrLatencyMs` only when a completed OCR callback belongs to
the current frame and occurs within the existing five-second acceptance
window. A callback older than five seconds increments a bounded late count
but never becomes a fresh result or a calibration miss. Frame replacement,
rotation/resize invalidation, visibility resume and Stop clear live timing;
aggregate completed/miss/late counters reset only on a new capture.

The diagnostic Stop event reports completed OCR frames, OCR misses,
late callbacks and maximum accepted processing latency without screenshots,
raw OCR, captured content or session identity. The opt-in Save event adds
`ocr_completed_at_ms` and `ocr_processing_latency_ms` alongside its
existing acquisition/Save timestamps. The strict importer validates that
these two new fields appear together, have integer types, that completion
lies between frame acquisition and Save, and that reported processing latency
equals the elapsed acquisition-to-completion interval and is at most five
seconds. Legacy evidence without both fields remains readable without
inventing an OCR completion time. The frame-provenance digest binds the
extra timing values for new rows while the public summary omits raw clocks.

This is **diagnostic timing instrumentation only**. It does not assert
the captured application's identity, calibrate recognizer accuracy, grant
trusted game observations, authorize recommendations or enable game input.
A new opt-in on-device run is required to measure how much latency is OCR
processing versus human Save; earlier logs cannot supply these timestamps.

## Offline comparison quality and timing decomposition — 2026-10-23

The same Owner-entered health values can answer two **different** diagnostic
questions. They must never be conflated:

- **Fresh sample agreement** (`exactMatches / samples`) includes missing,
  mismatched and >5000 ms old samples in its strict denominator. Existing
  L3/verification thresholds and the five-second gate are unchanged.
- **Retrospective value equality** counts numerically equal, different and
  unavailable OCR values against what the Owner typed at manual Save,
  **irrespective of age**. It is labelled
  `USER_ENTERED_AT_SAVE_NOT_FRAME_TRUTH`. It is a debugging comparison,
  **not** evidence that the character's health was unchanged between the
  frame and Save; it is not recognizer accuracy or an authorization threshold.

The privacy-bounded `sentinel.observer-calibration-summary.v2` retains its
strict `sampleAgreement` and adds only
`retrospectiveValueEquality` (equal/different/missing).
The opt-in diagnostic importer additionally computes
`optInTimingDiagnostics` exclusively from the at-most-32 **saved comparisons**:
a count of frames with valid callback timing, an explicit total count, and
minimum/lower-median/maximum for acquisition-to-OCR and OCR-to-Save intervals
in milliseconds. Legacy exports or partially instrumented campaigns retain
`null` latency summaries and/or explicit partial coverage instead of
inventing zero latency. The derived output contains no raw clocks, capture
UUID, images, OCR text or user-entered per-frame health values.

The 2026-10-22 Xiaomi export predates OCR callback timing and cannot tell us
whether its 5.8–7.7 second Save ages were caused by slow OCR or by returning
to the app and entering ground truth. Historical numerical equality can be
reported with its severe timing qualifier but **cannot** promote source trust,
recognizer confidence, recommendations or automated actions. Both summaries
stay `PENDING_PHYSICAL_REVIEW`, `UNVERIFIED`, `UNCALIBRATED` and
`capabilityAvailable=false`. Physical source binding and a separate Owner
acceptance remain gates for any game recommendation or executor.
