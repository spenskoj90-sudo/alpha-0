# Companion Knowledge Consumer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fail-closed Companion main-process consumer for the authenticated PostgreSQL knowledge-pack distribution without adding game-action authority.

**Architecture:** A focused local runtime validates complete packs and bounded byte-splice deltas, persists monotonic revision/revocation metadata and content-addressed bytes atomically, and grants only a short monotonic presentation lease. `CoreSessionManager` owns authenticated, origin-pinned, redirect-free, bounded transport. The Electron main process owns lifecycle, clears authority on Stop/logout/access denial, and exposes only a sanitized read-only status to the renderer.

**Tech Stack:** Node.js 24 built-ins, Electron IPC, `node:test`, SHA-256, atomic filesystem replacement.

**Spec:** `docs/GAME_KNOWLEDGE_RUNTIME_V1.md`

## Global Constraints

- Maximum full pack and reconstructed delta output: 262144 bytes.
- Manifest lease: at most 60000 ms and never beyond pack expiry.
- Exact coordinates are `game`, `platform`, `patch`, `environment`, `profile`.
- Authenticated Core origin and session are pinned; redirects are rejected.
- Complete destination bytes are digest/schema/profile validated before atomic installation or lease renewal.
- Revision and revocation state are monotonic and survive restart; rollback and revoked-digest reuse fail closed.
- Knowledge never grants action authority; `execution_authority` must be exactly `false`.
- `source_verified !== true`, stale observations, profile/session mismatch, Stop, logout and access denial yield no recommendations.
- `AUTOMATIC_EXECUTION_DISABLED` remains unchanged; no input, ARM or game-action path is added.

## Review Focus

- A delta envelope with valid-looking destination metadata but malformed base64, overlap or unsafe integers must not install or renew a lease.
- A process restart with corrupt or rolled-back state must fail closed without trusting orphaned bytes.
- Logout/Stop/session rotation during an in-flight fetch must prevent late installation.
- A 401 refresh retry must remain bound to the same Core origin and new authenticated session epoch.
- Network loss may retain only the already-granted monotonic lease; explicit auth/access denial clears it immediately.

---

### Task 1: Local pack, delta and durable lease runtime

**Files:**
- Create: `launcher/knowledge-runtime.js`
- Create: `launcher/test/knowledge-runtime.test.js`
- Create: `launcher/test/knowledge-delta.test.js`

**Interfaces:**
- Consumes: transport methods `manifest(profile, knownDigest)`, `pack(profile, digest)`, `delta(profile, destinationDigest, baseDigest)`.
- Produces: `KnowledgeRuntime({directory, transport, authority, wallClock, monotonicClock})`, `refresh(profile, sessionId)`, `clear()`, `status()`, `evaluate(observation, {sessionId, locale})`, plus pure `parsePack` and `reconstructDelta` validators.

- [ ] **Step 1: Write failing behavior tests** for exact pack validation, deterministic presentation-only evaluation, unverified/stale/profile/session denial, bounded delta reconstruction/fallback, rollback/revocation persistence, corrupt restart state, lease monotonicity, and in-flight clear.
- [ ] **Step 2: Run `node --test test/knowledge-runtime.test.js test/knowledge-delta.test.js`** and verify failure because the module does not exist.
- [ ] **Step 3: Implement the minimal validators and runtime** with atomic `0600` writes, a bounded state file, complete destination revalidation, durable tombstones and epoch cancellation.
- [ ] **Step 4: Run the two test files** and verify all pass.
- [ ] **Step 5: Commit** `feat(launcher): add durable knowledge consumer runtime`.

### Task 2: Authenticated bounded Core transport

**Files:**
- Modify: `launcher/core-session.js`
- Create: `launcher/test/knowledge-transport.test.js`

**Interfaces:**
- Consumes: exact profile and digest values validated by Task 1.
- Produces: `knowledgeManifest(profile, knownDigest)`, `knowledgePack(profile, digest)`, and `knowledgeDelta(profile, destinationDigest, baseDigest)` on `CoreSessionManager`.

- [ ] **Step 1: Write failing transport tests** for authentication, origin/query binding, `redirect: 'error'`, timeout signal, streamed byte/JSON bounds, digest syntax, 401 refresh correlation, access-denial classification and session-epoch cancellation.
- [ ] **Step 2: Run `node --test test/knowledge-transport.test.js`** and verify missing methods fail.
- [ ] **Step 3: Implement bounded authorized reads** without exposing tokens or accepting caller origins; classify 401-after-refresh, 403 and oversized/malformed bodies safely.
- [ ] **Step 4: Run transport plus existing Core session tests** and verify all pass.
- [ ] **Step 5: Commit** `feat(launcher): add authenticated knowledge transport`.

### Task 3: Main-process lifecycle and read-only product state

**Files:**
- Modify: `launcher/main.js`
- Modify: `launcher/preload.js`
- Modify: `launcher/renderer.js`
- Modify: `launcher/index.html`
- Create: `launcher/knowledge-presentation.js`
- Create: `launcher/test/knowledge-lifecycle.test.js`
- Create: `launcher/test/knowledge-presentation.test.js`

**Interfaces:**
- Consumes: `KnowledgeRuntime` from Task 1 and an explicit main-process closure adapter from Task 2 (`manifest → knowledgeManifest`, `pack → knowledgePack`, `delta → knowledgeDelta`); the adapter never exposes the session object or tokens.
- Produces: sender-bound `knowledge:status` and `knowledge:refresh` IPC plus a sanitized renderer state whose `actionAuthority` is always `false`.

- [ ] **Step 1: Write failing lifecycle/presentation tests** proving initial signed-out/stopped states, explicit refresh-only UI, bounded periodic refresh while Companion is active, Stop/logout/window close cleanup, terminal auth/access-denial invalidation, and transient-network lease retention.
- [ ] **Step 2: Run `node --test test/knowledge-lifecycle.test.js test/knowledge-presentation.test.js`** and verify missing lifecycle/presentation code fails.
- [ ] **Step 3: Implement lifecycle and renderer surface** with `WAITING_FOR_VERIFIED_PROFILE` and no distribution request until a trusted adapter supplies exact coordinates; never accept renderer-owned profile authority or invoke `evaluate` from unverified Shattered/WoW evidence.
- [ ] **Step 4: Run all launcher tests and package smoke**; verify no action-capable field or renderer token exposure.
- [ ] **Step 5: Commit** `feat(launcher): wire knowledge consumer lifecycle`.
