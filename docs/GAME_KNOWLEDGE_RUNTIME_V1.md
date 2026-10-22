# Game Knowledge Runtime v1

Status: data-only deterministic runtime implemented; closed offline fixture recommendation/action integration added; production combat integration and exact target acceptance pending. Global `AUTOMATIC_EXECUTION_DISABLED` remains active. New game = profile/adapter/capability pack, not another Core.

## Layers and trust

A. Content-addressed knowledge packs bind schema/version/game/platform/patch/environment/profile, expiry, provenance, revocation and bounded rules. `server/app/data/knowledge-pack-index.v1.json` is a source-controlled distribution index. An expected digest must come from a trusted distribution channel, never from the request that supplies the bytes. Digest validation proves byte identity, not publisher permission or strategy quality. Release signing is a separate Owner custody gate.

B. `knowledge_packs.evaluate` performs bounded deterministic comparisons and ordered priorities. It has no network, LLM call, interpreter, executor or authorization API. Cached handles re-enter their registry's local revocation guard on every evaluation; the data-only evaluator remains pure. Registry evaluation serializes same-registry revocation and rechecks external durable markers before returning. Missing/invalid values remain unknown; a bool is not numeric health. Exact patch/profile/environment/session and verified-source context are mandatory. Stale/future observations, revoked/expired/draft packs produce no recommendation. The caller must bind verified source/session from trusted runtime evidence; a client assertion is insufficient. Output is RECOMMENDATION with real source, reason, priority, observation time and nullable confidence. No command or permission is emitted.

C. AI exception work is outside the hot path: patch/encounter/build uncertainty, explanations, post-session/log analysis, offline simulation and candidate-pack refinement. AI candidates require independent review before distribution. FACT / INFERENCE / RECOMMENDATION never become authorization. The action boundary remains observed state → deterministic policy → server entitlement → bounded consent/ARM → Action Gateway → executor → observed outcome. UNKNOWN outcomes cannot trigger blind retries.

D. Core `PackRegistry` provides a bounded LRU and atomic persistent content-addressed cache. Trusted digest allowlist and durable revocation precede cache hits. Restart independently checks stored digest. Expiry/profile/freshness are rechecked on each evaluation. Local last-valid permitted packs may continue presentation during AI outage only while their policy remains valid; revoked/expired packs cannot serve as fallback. Companion and Android integration must use the same digest/policy semantics and monotonic observation age. No claim of an active local combat integration is made by the Core evaluator.

## Canonical persistence and update protocol

PostgreSQL canonical distribution uses migration `016_knowledge_distribution`: immutable content-addressed bytes and review reference, an exact five-coordinate profile pointer, monotonic publication/revocation revisions and permanent revocation. FORCE RLS permits transaction-service reads; only the table owner/operator can publish or revoke, even when runtime receives an excessive table grant. Statement guards reject TRUNCATE, including CASCADE, which PostgreSQL RLS and row triggers do not cover. Publication uses a profile advisory lock and expected-revision CAS; the current content row is locked against concurrent revocation. The serving process has no publication/evaluation endpoint. Operator custody and signed-release custody stay independent. Android/Companion authenticated local consumers remain pending; the Core filesystem registry alone does not prove that integration.

## Exact source fields and read-only domain module seam (GI-01 / GI-08)

The authenticated existing `GET /v1/game-capabilities` includes
`source_modules`, a **read-only** exact-profile inventory backed by
`server/app/data/game-source-modules.v1.json` and strict Core validation.
This is a field/source/freshness/UNKNOWN map for the two implemented-source
candidates, not an extra game entitlement or an action API:

- WoW WotLK 3.3.5a / WoWCircle: `normalized_events` have only a
  SavedVariables checkpoint hypothesis, not live combat telemetry. Health,
  target health, talents, gear and auction listings are UNKNOWN.
- Shattered Pixel Dungeon stock Android: `health_candidate` has an
  uncalibrated, consent-bound HUD OCR hypothesis. Authoritative health
  and inventory are UNKNOWN.

Each domain module (combat, character build, or economy where listed)
declares its required signal IDs and presentation surfaces. Versioned
module metadata also declares `module_contract_version=1`, a bounded
semantic `module_version`, shared player-state schema v1,
`session_bound` or `checkpoint_bound` lifecycle, same-profile
module dependencies and a finite set of **presentation-only** outputs.
The declaration is validated against exact-profile field IDs: a
SavedVariables-dependent module must be checkpoint-bound, an OCR-dependent
module session-bound; unknown/cross-profile/self dependencies, cycles,
duplicate references, undeclared output types and action/entitlement fields
are rejected. Output types must match the declared UI surfaces.

This is a contract for future routing, **not a running domain module**.
Lifecycle status is `NOT_STARTED`, all `outputs_available` lists are empty,
shared player-state availability is `UNKNOWN` with no session binding or
update timestamp. No module can self-start, promote source trust, emit
commands, or publish state by appearing in this inventory. All source-field
`availability` values remain `UNKNOWN`, verified freshness/latency/
confidence remain `null`, module readiness is
`WAITING_FOR_VERIFIED_SOURCE` and `execution_authority=false`.
Source provenance must match the **separate** existing research catalog
at the same exact game/platform/patch/environment. Unknown sources may
not self-declare timestamps or quality, and metadata cannot register
executor/action/entitlement fields. Registry validation is not L3
attestation. Adding a module gives no capture, game write or entitlement.

### Bounded module lifecycle replay (L2 only)

`server/app/core/game_module_lifecycle_replay.py` is an isolated, in-memory
**synthetic replay reducer**, not a runtime adapter, production recommendation
engine or action API. It exercises the exact registered module dependencies and
source lifecycle class using only synthetic **field-presence flags**, never
game contents, images, OCR text, character inventories or credentials.
`scripts/game_module_replay.py` demonstrates combat + economy in WoW and
combat + character-build on stock Android with two distinct fake event streams.
The runnable regression suite checks exact profile/session, contiguous
sequence, monotonic timestamps, five-second replay freshness, strict OCR-session versus SavedVariables-checkpoint source-kind rejection, checkpoint
supersession, dependency blocking, stopped sessions and atomic rejection of
invalid/late frames. A saved-variable field cannot masquerade as a session
stream.

All replay outputs are permanently tagged `L2_SYNTHETIC_ONLY` and
`source_trust=UNVERIFIED`. The shared player-state remains `UNKNOWN` and
has no session binding or timestamp; module `outputs_available` is always
empty and `execution_authority=false`, even when a replay module reports
`L2_SIMULATED_ONLY`. Existing authenticated `GET /v1/game-capabilities`
remains source-truth `UNKNOWN`/`NOT_STARTED`. No real gameplay fields are
accepted or emitted by this fixture and no endpoint, entitlement, operator
upload or ARM activation is added.

A later source-specific integration must independently prove freshness,
correctness, publisher/environment permission and physical L3 calibration
before any status can be promoted. This contract deliberately cannot
self-promote from a client-supplied field, model answer or knowledge pack.
Other catalog profiles remain research-only and are not silently enrolled.

## Catalog and first verticals

`/v1/game-capabilities` requires existing authenticated `game:read` policy and publishes the machine-readable inventory. It does not add entitlement games or action allowlists. Unknown installed patches, timing/confidence and publisher permissions are explicitly null/unverified; online action capabilities remain disabled. Android stock Shattered Pixel Dungeon remains an uncalibrated observer pilot with source UNVERIFIED.

The WotLK 3.3.5a / WoWCircle foundation pack covers class/spec/talent/glyph/gear assumptions, stats/caps, targets/phases, buffs/debuffs, cooldowns/resources/procs/movement, interrupts/defensives/threat/tank mitigation/healing/dispels/consumables and encounter/group/PvE/PvP differences. Its rules are deliberately empty and status DRAFT until actual reviewed strategies and exact environment evidence exist. Inventory coverage is a schema capability, not a claim of complete strategies or L3 PASS.


## Canonical distribution API and delta v1

`GET /v1/knowledge/manifest` and `GET /v1/knowledge/packs/{digest}` require an existing authenticated `game:read` session. Query coordinates are `game`, `platform`, `patch`, `environment`, `profile`; the optional manifest `known_digest` is only a cache hint. The server independently validates digest/schema/profile, review reference, validated status, revocation and expiry before delivering current full bytes. Missing database remains unavailable; database errors return a safe 503. Replies use `Cache-Control: no-store`. A manifest carries revision, server time and at most a 60-second presentation lease, bounded by pack expiry, with `execution_authority=false`. A refresh must not renew a local lease until complete bytes validate and install atomically. A lease is not entitlement, verified game evidence or action permission. Offline revocation discovery cannot be promised to be instantaneous.

`GET /v1/knowledge/deltas/{digest}` requires the same session/profile and a `base_digest`. One PostgreSQL statement snapshot binds the current destination and both revocation states. A base must have matching exact profile, valid schema/digest, reviewed validated content and no revocation; an expired base may be used only as reconstruction bytes. The destination must still be current, unexpired and unrevoked. An unavailable delta returns 404; a consumer can obtain the current full pack instead, within its remaining trusted lease.

The JSON envelope is data-only: `schema_version=1`, `algorithm=byte-splice-v1`, `base_digest`, `destination_digest`, `destination_size`, `prefix_bytes`, `suffix_bytes`, `insert_b64`. Reconstruct `base[:prefix_bytes] + decoded_insert + base[len(base)-suffix_bytes:]`, treating zero suffix as empty. Prefix/suffix cannot overlap. Both input/output are bounded to 262144 bytes; strict integers, bounded base64, exact fields and full output size are mandatory. `reconstruct_delta` compares the destination digest to the independently trusted manifest digest, verifies base digest, reconstructs full bytes and validates the complete destination through `load_pack`. The envelope's digest cannot grant trust. Reconstruction changes no pointer or lease; installation remains a consumer responsibility. This protocol prioritizes bounded validation over compression ratio and does not guarantee every delta is smaller than full bytes.

Publication is an offline operation: `PYTHONPATH=. python scripts/publish_knowledge_pack.py --file ... --digest ... --review-reference ... --expected-revision ...`. Credentials come only from native `DATABASE_MIGRATION_URL`, never CLI arguments or a runtime-URL fallback. `--revoke --digest ...` records permanent revocation. A review reference records operator-supplied independent review evidence; it does not itself prove strategy quality, publisher permission or model reliability. No real-game strategy is seeded or activated by this migration. The WotLK foundation remains draft; Shattered source remains UNVERIFIED and physically uncalibrated, without recommendations/input/ARM. `AUTOMATIC_EXECUTION_DISABLED` is unchanged.

Next consumers must pin authenticated Core origin/session, reject redirects, bound bytes/time, persist revision/tombstones, reject rollback and revalidate complete packs on restart. Round-trip time consumes the lease; monotonic observation age and immediate Stop/logout/access-denial invalidation remain mandatory. Old local implementation files recovered from an abandoned workspace are reference material until reviewed, integrated and tested on the current main. This server continuation does not claim Android/Companion, physical, Owner-visible or release acceptance.
