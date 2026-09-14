# SENTINEL Packaged Companion Host Acceptance v1

Status: repository acceptance contract for the unsigned Windows Companion host.

## Scope

This block closes the repository-internal prerequisite for exact-host acceptance by producing an executable Windows Companion package from pinned, independently verified runtime inputs.

It does **not** claim signed release readiness, production installation, target-PC compatibility, physical microphone quality, exact WoW/private-server compatibility, production credentials, release publication, or live deployment.

## Target

- platform: Windows x64 (`win32-x64`)
- Electron runtime: exactly `37.2.0`
- official upstream asset: `electron-v37.2.0-win32-x64.zip`
- expected upstream SHA-256: `4d4451179993fa22a1125bbc0130858903bc16e5c87900a969fa7bbac5c8f6a3`
- application payload: unpacked `resources/app`
- executable: `SENTINEL Companion.exe`
- ordinary CI signing state: unsigned

The unpacked application payload is deliberate. The launcher starts the Companion worker through Node child-process paths; keeping those JavaScript sources as normal files avoids treating an ASAR container as executable filesystem evidence.

## Trust and provenance boundary

`launcher/scripts/package-windows.ps1`:

1. reads the pinned version and digest from `launcher/package.json`;
2. downloads only the corresponding official Electron GitHub release asset when it is not already in the local build cache;
3. rejects the runtime when its SHA-256 differs from the pinned digest;
4. stages the official runtime without signing or modifying security controls;
5. replaces Electron's default application with the bounded SENTINEL application payload;
6. writes `resources/app/build-provenance.json` containing the package/source identity available to the running Companion;
7. includes that embedded provenance file in the sorted SHA-256 manifest for every staged file;
8. writes external build evidence bound to `SENTINEL_SOURCE_SHA`.

The embedded runtime provenance contains the exact source SHA, target, launcher version, Electron version and signing state. `launcher/packaged-runtime.js` bounds and validates the file and computes its SHA-256 digest. A package built without an exact source SHA may remain usable for local development but is marked `local-unbound` and is rejected by exact-environment L3 capture.

The browser/player cannot influence the runtime version, upstream asset URL, expected digest, packaged source list, evidence source SHA, or embedded build provenance through renderer IPC.

## CI evidence

`.github/workflows/packaged-companion.yml` is an additional acceptance workflow. For every PR to `main` and every `main` push it:

1. runs the launcher regression suite;
2. builds package A;
3. independently stages package B from the same verified upstream runtime;
4. requires identical canonical file-content manifests;
5. verifies both build-evidence documents are bound to the exact PR HEAD SHA (or push SHA on `main`);
6. starts the staged `SENTINEL Companion.exe` with the packaged smoke entrypoint;
7. requires the running Electron process to report version `37.2.0`, validate embedded source provenance and resolve the Companion runtime module graph from `resources/app`;
8. explicitly loads the exact-environment evidence recorder module as part of packaged smoke;
9. records exact-SHA smoke evidence;
10. uploads the unsigned Windows package plus manifests and evidence.

Reproducibility means equality of the staged runtime filesystem contents. The compressed ZIP archive is a transport artifact; ZIP metadata is not used as the reproducibility criterion.

## Fail-closed conditions

Packaging or smoke evidence fails when any of the following occurs:

- runtime asset SHA-256 mismatch;
- Electron dependency/version drift;
- non-Windows packaged-runtime evidence;
- missing required Companion runtime source;
- missing or malformed embedded build provenance;
- embedded package/Electron provenance drift;
- unexpected executable name;
- bundled `node_modules` or launcher test sources;
- package A/B file-content manifest mismatch;
- external evidence source SHA differs from the exact PR HEAD/push SHA;
- packaged Electron process fails to start or load the required runtime module graph;
- ordinary CI evidence claims the package is signed.

## Relationship to exact-environment L3 evidence

The packaged host is the source-provenance anchor for `docs/EXACT_ENVIRONMENT_L3_EVIDENCE_V1.md`. When L3 capture is explicitly enabled on a real target host, the recorder consumes the embedded source-bound provenance and combines it only with sanitized accepted Companion handshake/health and Core-ACKed WoW checkpoint evidence.

The package itself does not establish L3. CI package smoke does not establish L3. A source SHA embedded in a package does not establish L3. The real exact game/client/server run remains a separate environment acceptance event.

## Acceptance level after this block

A green exact-SHA workflow proves **repository-produced unsigned packaged-host evidence** on a GitHub Windows runner. It upgrades the Companion from source-only launcher evidence to packaged-host CI evidence and gives real-host acceptance a source-bound runtime identity.

It does not upgrade game capabilities to L3 and does not replace physical target-PC acceptance. Exact Windows machine behavior, real WoW/private-server observation, physical audio, signing, installer UX, and production release remain separate evidence gates.
