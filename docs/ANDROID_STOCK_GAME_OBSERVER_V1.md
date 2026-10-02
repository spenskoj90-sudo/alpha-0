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
The release build has no entry point and its service is manifest-disabled and
runtime-denied. Build type never grants account/admin or game-action authority.

Only Android 14+ is supported for this pilot. The disclosure asks the user to
select **one app: Shattered Pixel Dungeon** in Android's consent chooser. Android
also offers whole-display capture. The public MediaProjection API does not attest
the selected package to SENTINEL; the source therefore remains user-selected and
**UNVERIFIED**. Do not describe this pilot as enforcing app-only capture.

## Capture lifecycle

- A fresh Android consent result is required for every session.
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
