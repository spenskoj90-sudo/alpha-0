# Game Knowledge Runtime v1

Status: data-only deterministic runtime implemented; production combat integration and exact target acceptance pending. Global `AUTOMATIC_EXECUTION_DISABLED` remains active. New game = profile/adapter/capability pack, not another Core.

## Layers and trust

A. Content-addressed knowledge packs bind schema/version/game/platform/patch/environment/profile, expiry, provenance, revocation and bounded rules. `server/app/data/knowledge-pack-index.v1.json` is a source-controlled distribution index. An expected digest must come from a trusted distribution channel, never from the request that supplies the bytes. Digest validation proves byte identity, not publisher permission or strategy quality. Release signing is a separate Owner custody gate.

B. `knowledge_packs.evaluate` performs bounded deterministic comparisons and ordered priorities. It has no network, LLM call, interpreter, executor or authorization API. Missing/invalid values remain unknown; a bool is not numeric health. Exact patch/profile/environment/session and verified-source context are mandatory. Stale/future observations, revoked/expired/draft packs produce no recommendation. The caller must bind verified source/session from trusted runtime evidence; a client assertion is insufficient. Output is RECOMMENDATION with real source, reason, priority, observation time and nullable confidence. No command or permission is emitted.

C. AI exception work is outside the hot path: patch/encounter/build uncertainty, explanations, post-session/log analysis, offline simulation and candidate-pack refinement. AI candidates require independent review before distribution. FACT / INFERENCE / RECOMMENDATION never become authorization. The action boundary remains observed state → deterministic policy → server entitlement → bounded consent/ARM → Action Gateway → executor → observed outcome. UNKNOWN outcomes cannot trigger blind retries.

D. Core `PackRegistry` provides a bounded LRU and atomic persistent content-addressed cache. Trusted digest allowlist and durable revocation precede cache hits. Restart independently checks stored digest. Expiry/profile/freshness are rechecked on each evaluation. Local last-valid permitted packs may continue presentation during AI outage only while their policy remains valid; revoked/expired packs cannot serve as fallback. Companion and Android integration must use the same digest/policy semantics and monotonic observation age. No claim of an active local combat integration is made by the Core evaluator.

## Canonical persistence and update protocol

PostgreSQL canonical distribution is a separate implementation seam: immutable `digest → pack bytes + reviewed provenance`, current profile/version pointer, revocation revision and validity window. Runtime role reads authorized distribution; migration/operator role changes schema; reviewed publisher permission and signed-release custody stay independent. Device/Companion refresh compares version/digest/revocation revision; install validates complete bytes atomically before replacing the pointer. Delta transport must reconstruct and validate the full destination digest; failure keeps the previous still-valid pack. This pass implements filesystem persistence, not the PostgreSQL canonical service or delta wire transport.

## Catalog and first verticals

`/v1/game-capabilities` requires existing authenticated `game:read` policy and publishes the machine-readable inventory. It does not add entitlement games or action allowlists. Unknown installed patches, timing/confidence and publisher permissions are explicitly null/unverified; online action capabilities remain disabled. Android stock Shattered Pixel Dungeon remains an uncalibrated observer pilot with source UNVERIFIED.

The WotLK 3.3.5a / WoWCircle foundation pack covers class/spec/talent/glyph/gear assumptions, stats/caps, targets/phases, buffs/debuffs, cooldowns/resources/procs/movement, interrupts/defensives/threat/tank mitigation/healing/dispels/consumables and encounter/group/PvE/PvP differences. Its rules are deliberately empty and status DRAFT until actual reviewed strategies and exact environment evidence exist. Inventory coverage is a schema capability, not a claim of complete strategies or L3 PASS.
