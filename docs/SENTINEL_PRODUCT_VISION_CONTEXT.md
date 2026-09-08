# SENTINEL — Product Vision Context

**Status:** canonical source-backed product context  
**Issue:** #194  
**Date:** 2026-09-08

## 1. Why SENTINEL exists

SENTINEL did not originate as a purely technical or security exercise. The retained migration sources identify **byster.one/ru** as the original inspiration and record that the first product discussions centered on:

- WOW-level capabilities;
- genuinely valuable capabilities for users;
- capabilities specifically valuable to players;
- a differentiated user experience;
- useful automation and intelligence;
- making SENTINEL substantially more powerful than a conventional application.

The durable product principle is:

> **Technology → capability → experience → WOW → user value.**

Security, reliability, correctness, performance and engineering quality are enabling constraints that make those experiences trustworthy; they are not the entire product purpose.

## 2. What is source-supported today

The retained continuity package explicitly describes two inseparable layers.

### Product layer

- WOW;
- player capabilities;
- user capabilities;
- differentiated experience;
- intelligence;
- useful automation.

### Engineering layer

- security and trust;
- identity and authentication;
- server-authoritative authorization;
- reliability and deterministic behavior;
- performance;
- testing and regression coverage;
- CI/CD and evidence;
- release quality.

The long-term objective is therefore not merely a "secure application", but a **trustworthy platform capable of delivering compelling user/player experiences**.

## 3. Current platform direction

The current repository has evolved the engineering foundation needed to support that product ambition. Its architecture separates domains such as Identity, Authentication, Authorization, Entitlement, Billing, Game State, Knowledge, Telemetry, AI, Event Processing, Audit and Worker Manager, with Android, a web control plane, game adapters, a knowledge/recommendation engine and PostgreSQL around the Core boundary.

The knowledge model is deliberately constrained: knowledge is represented as fact, inference or recommendation, with confidence and provenance; AI may summarize, infer and recommend but must not grant entitlement, change authorization, mutate billing, revoke security state or issue privileged game commands.

This creates the intended product-to-trust path:

`USER / PLAYER CONTEXT → OBSERVATION → TRUSTED CORE → KNOWLEDGE / INFERENCE → RECOMMENDATION → USER EXPERIENCE`

Any future execution capability must still pass through the established authorization, policy and security boundaries.

## 4. Player / game direction

The repository now contains an explicit WoW support surface: a game-adapter contract, WoW catalog/API support, a conservative passive WoW adapter, and a draft game capability matrix covering WoW Retail, WoW Legacy 3.3.5a and a private-server profile. The adapter boundary exists so the Core consumes SENTINEL semantic facts/events rather than game-specific client shapes or private-server assumptions.

This is important product context, but it is **not** evidence that every historical or envisioned WoW capability is implemented. Exact environment validation remains required for capabilities that depend on a real game client, launcher, addon, server or device.

## 5. What was not recovered

The migration sources explicitly state that the complete historical WOW/product brainstorm is not present in retained context. The exact bodies of historical decisions D-001 through D-020 are also not present.

Those gaps remain classified as historical-recovery work. They must not be filled by invented memories or silently converted into requirements.

Future ideas follow:

`IDEA → DISCOVERY → VALIDATED PRODUCT REQUIREMENT → ARCHITECTURAL REQUIREMENT → IMPLEMENTATION → TESTED FEATURE`

An idea is not automatically a requirement.

## 6. Visual/product continuity

The retained visual direction is consistent with a security-first SENTINEL experience: dark high-contrast surfaces, blue security accents, shield/SENTINEL identity, Android user experience, web control plane, device/security status, intelligence/alerts and a unified control surface.

Visual concepts are product-direction references, not implementation evidence. The interface should evolve from the established visual language while remaining consistent with the actual capabilities and security boundaries implemented in the repository.

## 7. Product priority

When product and engineering decisions compete, the retained project priority is:

1. Human Owner intent;
2. product vision and user/player value;
3. security and trust;
4. correctness;
5. reliability;
6. performance;
7. maintainability;
8. release quality;
9. additional WOW features.

WOW must not undermine security, reliability or correctness. Engineering quality must not become an excuse to abandon the product ambition.

## 8. Continuity contract

Future SENTINEL work must preserve all three layers:

- **WHY** — product vision, WOW, user/player value;
- **HOW** — architecture, security, implementation and integration;
- **PROOF** — tests, CI, security review, artifacts and release evidence.

A feature is not considered complete merely because it is attractive, architecturally plausible or historically discussed. Completion requires implementation plus appropriate validation and evidence.

## 9. Relationship to current state

`main` and current GitHub evidence remain authoritative for mutable implementation facts. This document preserves product intent and source-supported historical context; it does not override current code, tests, CI, security gates or Owner-only boundaries.

Historical source: `SENTINEL_MASTER_STATE_v1.0.md`, `SENTINEL_KNOWLEDGE_BASE_v2.0.md`, and `SENTINEL_CHAT_MIGRATION_RUNBOOK.md` retained in the project continuity package.
