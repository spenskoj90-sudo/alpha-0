# SENTINEL — Canonical Current State

> **Source-of-truth rule:** Git `main` is authoritative for repository/product state. This document is a semantic state summary, not a live mirror of commit SHAs or workflow runs. Do not embed a mutable `main` HEAD here; exact commit/check evidence belongs to GitHub commit and Actions records.
>
> Exact CI/release claims require an exact SHA plus workflow/check Run ID where applicable. Unknown facts remain **UNVERIFIED**.

## 1. Product surfaces

- Android client exists under `app/`.
- FastAPI Core exists under `server/`.
- Next.js control plane exists under `web/`.
- Electron launcher exists under `launcher/`.
- WoW addon sources exist under `wow-addon/`.

## 2. Security and persistence baseline

- Android device identity is Keystore-backed P-256 with SHA-256 fingerprinting.
- Sessions use opaque tokens with one-time refresh rotation.
- Authorization is server-authoritative and default-deny.
- PostgreSQL is the production persistence architecture when `DATABASE_URL` is configured; migration `004_p1_rls_force.sql` applies FORCE RLS.
- Release signing controls and production/live deployment remain Owner-gated.

## 3. Game integration architecture

- Game Adapter Contract v1 is implemented as the canonical adapter boundary.
- Unified Game State v1 is defined as the normalized Core state contract.
- Adapter Registry / Capability Registry v1 is implemented on `main` with:
  - typed adapter identity;
  - capability status and L1/L2/L3 evidence discipline;
  - L3 enforcement for `AVAILABLE` capabilities;
  - capability downgrade tracking;
  - bounded normalized event envelopes;
  - Core-side usable-capability guards;
  - registration, capability, evidence, sequencing and payload-bound tests.
- The registry is not an authorization store and does not execute game actions or access game-process memory.
- Exact Retail and WotLK 3.3.5a/private-server validation remains **UNVERIFIED** until exact-environment L3 evidence exists.

## 4. Telemetry and performance

- PostHog telemetry contract v1 is defined and provider-neutral.
- Runtime PostHog instrumentation is not yet established as a complete implementation; the contract and runtime instrumentation are separate stages.
- Performance baseline methodology/contract exists; measured results must be treated as branch/Run-ID evidence until reconciled onto `main`.
- Launcher/WoW-addon dedicated test and coverage evidence remains **UNVERIFIED**.

## 5. Architecture work that remains

The current architecture gap register includes, at minimum:

- UGS validator: schema compatibility, ordering, idempotency, quality propagation and bounded staleness/expiry;
- deterministic replay fixture format and replay tests;
- conservative first WoW adapter vertical slice;
- Companion protocol and measurable latency classes;
- Policy Engine / Action Gateway boundary for action-capable features;
- adapter/companion observability implementation;
- simulation harness before expanding recommendation logic;
- exact-environment WoW validation with L3 evidence;
- AI provider abstraction/routing, confidence/provenance implementation, compatibility/version negotiation, overlay/voice interaction contracts and related MVP architecture items where implementation evidence is absent;
- Android `AuthApi` transport architecture remains technical debt because it still uses synchronous `HttpURLConnection`.

These items must be marked only from repository evidence and remain **PARTIAL**, **UNVERIFIED**, or **NOT STARTED** until their implementation/evidence exists.

## 6. Governance

The canonical operating model is `docs/GPT_ONLY_AUTONOMOUS_ENGINEERING_OS.md`: GPT/ChatGPT is the sole AI engineering participant, the Human Owner is final authority, routine CI failures are diagnosed/fixed autonomously, and merges require exact-SHA successful required checks without bypassing security or branch protection.

## 7. Documentation model

This document intentionally avoids self-referential commit snapshots and workflow-run mirrors. A change to repository code does not require a generated HEAD-sync commit. Semantic state changes should update this document in the same logical PR when the product/architecture state actually changes.

For live state, use:

- Git `main` for the current repository commit and file tree;
- GitHub Actions for current workflow/check results and exact Run IDs;
- issues/PRs for active work and historical implementation evidence;
- architecture contracts and capability matrices for normative requirements.
