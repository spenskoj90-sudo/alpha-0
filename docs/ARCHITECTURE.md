# SENTINEL Architecture — RC1

## Baseline

SENTINEL is a security-first modular monolith with three product surfaces:

- Android client (`app/`)
- SENTINEL CORE (`server/`)
- Next.js control plane (`web/`)

The authoritative architecture reference is `docs/ARCHITECTURE_V4.md`; this document records the release implementation mapping.

## Security decisions

- D-001: modular monolith.
- D-002: SENTINEL CORE is the authoritative decision point.
- D-003: authentication/session state is server-controlled.
- D-004: authorization is default-deny.
- D-005: least privilege is enforced through scopes and policies.
- D-006: role membership is not sufficient authorization by itself.
- D-007: scopes are first-class authorization inputs.

## Request path

`device identity -> challenge proof -> opaque session -> principal -> policy + scope authorization -> domain action -> audit`

The client never supplies roles or permissions as an authority input.

## Persistence

PostgreSQL is the production system of record. Migrations are deterministic and checksum-verified by `server/migrate.py`.

## Product domains

Game catalog, entitlements, WoW support, admin control, knowledge/recommendation and audit are separate modules around the Core authorization boundary.

## Failure model

Security failures fail closed. Invalid authorization, invalid device proof, replay, expired sessions and missing production configuration do not grant access.
