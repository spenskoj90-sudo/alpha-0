# Android scoped agent instructions

Review focus: Keystore/session identity, exact provider/package/signing bindings, capture revocation,
foreground/window/session changes, stale observations, immediate Stop and no blind retries.
Calibration observations never prove action readiness or physical acceptance on their own.

Scope: app/ plus directly required shared contracts/tests.

- Follow root AGENTS.md.
- Android user-facing readiness requires exact physical-device Owner review; emulator/build success is supplemental.
- Preserve Keystore identity, session/auth boundaries, and fail-closed provider behavior.
- Do not introduce release signing into routine CI.
- Default validation: ./gradlew assembleDebug and ./gradlew test; run applicable instrumentation/physical-test workflows when required.
- UI work must cover loading, empty, error, offline/degraded, and accessibility states when applicable.
- Parallel Android writers must own disjoint files/features; otherwise use one writer.
