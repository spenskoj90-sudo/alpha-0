# SENTINEL Exact-Environment L3 Evidence v1

Status: repository acceptance contract and capture/admission boundary.

## Purpose

The Game Adapter Contract defines L3 as validation in the **exact target game/client/server environment**. This document defines the repository machinery that can capture and validate that evidence for the conservative WoW path.

This machinery does not itself prove that a physical/live run happened. A fixture, a copied SavedVariables file, or an operator label can be fabricated by a person with local filesystem control. L3 therefore remains an acceptance claim that requires a real target-environment execution plus the machine-verifiable consistency checks below.

CI, replay and synthetic fixtures test the validator and failure modes only. They are not L3 evidence.

## Capability admission rule

`CapabilityStatus.AVAILABLE` is an exact-environment claim. A caller may no longer promote a capability to `AVAILABLE` merely by constructing `Capability(evidence_level=L3)`.

The only repository path that may admit an `AVAILABLE/L3` capability is:

```text
real exact environment
  -> source-bound packaged Companion
  -> accepted Companion handshake
  -> authenticated ACTIVE runtime health
  -> bounded WoW SavedVariables checkpoint
  -> ConservativeWowAdapter/Core validation
  -> WOW_OBSERVATION_ACK: PASSIVE_CHECKPOINT_ACCEPTED
  -> exact-environment evidence bundle
  -> Core evidence validator
  -> L3 admission
  -> AdapterRegistry AVAILABLE/L3
```

Capability evidence still does not grant authorization. Policy Engine / Action Gateway remains the separate authorization boundary, and this WoW path remains passive/read-only.

## Packaged-host provenance

The Windows package contains `resources/app/build-provenance.json` under the canonical package manifest. It records:

- schema `sentinel.packaged-companion-runtime.v1`;
- exact source Git SHA when built by CI or another source-bound build process;
- `win32-x64` target;
- launcher package version;
- Electron version;
- signing state.

The launcher computes a SHA-256 digest of that embedded provenance file before capture. L3 recording rejects `local-unbound` packages and requires a lowercase 40-character source SHA.

This closes the provenance gap where an external CI artifact knew the source SHA but the running package did not.

## Opt-in live capture

The packaged launcher enables the process-local recorder only when both variables are present:

- `SENTINEL_L3_EVIDENCE_OUTPUT` — absolute output path for the JSON bundle;
- `SENTINEL_L3_ENVIRONMENT_ID` — stable operator-defined identifier for the exact test stand.

The recorder is disabled in ordinary launcher use.

L3 capture rejects `SENTINEL_WOW_SAVEDVARIABLES_PATH`. Acceptance must use the SavedVariables file discovered underneath the configured WoW executable root rather than the test/diagnostic override path.

The bundle intentionally contains no Core access/refresh tokens, no password, no raw game-process memory, no executable payload, and no raw SavedVariables path. The path is represented only by a SHA-256 fingerprint.

## Classic server-profile label

Classic addon checkpoints default to `server_profile = unknown`.

For an explicitly known target, the operator may set:

```text
/sentinel server private
/sentinel server official
/sentinel server unknown
```

The value is bounded to `official | private | unknown` and persists in `SentinelDB.server_profile`.

This is **target metadata supplied by the operator**, not independent proof of server identity. The addon explicitly states that the label does not by itself establish L3 evidence. An `unknown` profile cannot be admitted as L3.

## Minimum live evidence

A bundle is not written until the packaged process has all of the following:

1. source-bound packaged-host provenance;
2. an accepted `ACTIVE` Companion handshake using exactly:
   - Companion protocol `1.0`;
   - UGS schema `1.0`;
   - adapter contract `1.0`;
   - Core protocol `1.0`;
   - capability profile `wow.passive.v1`;
3. at least one sanitized runtime-health sample showing:
   - `ACTIVE` mode;
   - authenticated peer;
   - kill switch inactive;
   - bounded reconnect/queue/drop counters and RTT;
4. at least two distinct SavedVariables checkpoints that:
   - have different source SHA-256 digests;
   - advance sequence strictly;
   - are produced under one patch/server/realm identity;
   - report addon loaded;
   - preserve addon + launcher provenance;
   - travel through the normal Companion transport;
   - receive matching Core `PASSIVE_CHECKPOINT_ACCEPTED` acknowledgements.

SavedVariables are checkpoint persistence, not realtime IPC. In a real acceptance run the operator must cause WoW to persist distinct checkpoints through the normal client lifecycle, for example a legitimate `/reload`/ReloadUI or logout boundary as appropriate for the target client. Merely waiting for the in-memory addon snapshot to change does not prove the file was persisted.

## Bundle schema

The bounded `1.0` bundle includes:

- evidence ID and `live-exact-environment` execution mode;
- exact source SHA;
- started/completed timestamps;
- exact adapter identity including environment ID, patch and server profile;
- packaged-host provenance and provenance-file digest;
- accepted handshake evidence;
- bounded runtime-health samples;
- 2–64 accepted checkpoint records;
- derived conservative capability claims.

Each checkpoint contains only:

- raw checkpoint SHA-256;
- bounded file size;
- SavedVariables path fingerprint SHA-256;
- capture time;
- bounded normalized passive observation;
- matching Core ACK and acknowledgement time.

## Capability derivation

The packaged recorder derives claims; the operator does not type arbitrary capability names into the live bundle.

The conservative capture may claim only:

- `wow.identity`;
- `wow.patch_profile`;
- `wow.realm_profile`;
- `wow.latency` when every accepted checkpoint contains bounded latency;
- `wow.addon_status`;
- `wow.launcher_association`;
- `wow.account_entitlement`;
- `wow.passive_telemetry`.

Unknown capability names fail closed. Realm/profile/latency claims have additional field requirements in the Core validator.

## Core admission validator

`server/app/core/exact_environment_evidence.py` validates the bundle independently from the launcher recorder.

It rejects, among other failures:

- `replay` or `synthetic` execution mode;
- unsupported adapter/game/patch/server identity;
- missing exact environment ID;
- `server_profile=unknown`;
- package source SHA drift;
- handshake version/profile drift;
- non-ACTIVE or unauthenticated runtime health;
- kill-switch-active evidence;
- more than one Companion connection;
- timestamps outside the bounded run window;
- duplicate event IDs or checkpoint digests;
- non-increasing checkpoint sequence;
- patch/server/realm drift;
- missing addon/launcher provenance;
- addon-not-loaded observations;
- failed launcher/account association observations;
- missing/mismatched/rejected Core ACK;
- unsupported or over-claimed capabilities.

The validator computes a deterministic SHA-256 digest over canonical JSON. Admitted capabilities record the evidence ID and `exact-environment-bound` constraint.

## Operator validation command

After a real capture, validate it against the exact intended code and environment rather than trusting values inside the file:

```text
cd server
python scripts/validate_exact_environment_evidence.py <bundle.json> \
  --expected-source-sha <40-char-source-sha> \
  --expected-environment-id <exact-environment-id>
```

The CLI rejects symlink input, files larger than 2 MiB, malformed UTF-8/JSON, source-SHA mismatch and environment-ID mismatch before returning an admission summary.

## WotLK 3.3.5a private-server acceptance sequence

For the current intended Classic target, the evidence sequence is:

1. select the exact protected `main` SHA to test;
2. build/use the unsigned source-bound packaged Companion for that exact SHA;
3. install/use the matching SENTINEL Classic addon in the target WoW 3.3.5a client;
4. configure the launcher with that WoW executable through the normal game configuration path;
5. in the target private-server session, explicitly label the target with `/sentinel server private`;
6. start the packaged Companion with the two L3 capture variables and no SavedVariables override;
7. establish the authenticated ACTIVE Companion session;
8. cause at least two normal SavedVariables persistence checkpoints while remaining in the same intended realm/environment;
9. verify Core accepted those checkpoints;
10. validate the emitted bundle with the explicit expected source SHA and environment ID;
11. preserve the resulting bundle/digest as acceptance evidence tied to that exact target.

Until those real steps occur, WotLK/private-server L3 remains **ENVIRONMENT-UNVERIFIED** even though the capture and admission machinery is implemented and regression-tested.

## Security and non-claims

This boundary does not:

- read or modify WoW process memory;
- inject code into WoW;
- execute game actions;
- turn capability evidence into authorization;
- expose tokens in evidence;
- use CI replay as live evidence;
- provide hardware-backed attestation of the physical PC;
- prove that an operator-supplied server-profile label is truthful;
- sign the Windows executable;
- publish a release or deploy production.

Signed release-candidate execution, physical target-PC acceptance, exact live game/server acceptance, release publication and production deployment remain separate gates.
