# PostgreSQL / Neon staging audit — 2026-09-23

**Status:** PARTIALLY VERIFIED  
**Repository PostgreSQL:** INTEGRATION-TESTED  
**Live Neon inspection:** ENVIRONMENT-UNVERIFIED due connector schema/runtime mismatch

## Repository database truth

SENTINEL remains on PostgreSQL major 18. The reproducible database image is pinned to current stable patch 18.6 and an immutable image digest:

`postgres:18.6-alpine@sha256:77f585114c32fbca283dc835b0596f4e52b51b4c6662d7810b2f4084f60a1873`

PostgreSQL 18.6 is the current upstream 18.x patch as of this audit. The existing migration, FORCE RLS, service-role, integration and recovery suites remain mandatory exact-SHA CI gates. Service-role activation remains transaction-local rather than a pooled-session startup GUC.

## Neon connector discovery

The current Neon connector exposes actions such as `describe_project` and `list_branches` with schemas that do not accept a `project_id` argument. At runtime both actions reject the request because `project_id` is required internally.

No `list_projects` action is exposed by the current connector.

Therefore this pass:

- does **not** guess a Neon project ID;
- does **not** request or print a connection string;
- does **not** perform a write;
- does **not** claim live Neon branch/database state;
- preserves production database activation as Owner-gated.

This is a connector contract defect/limitation, not evidence of a database defect.

## Acceptance rule

Repository PostgreSQL behavior may be marked INTEGRATION-TESTED only when the exact PR/main SHA passes the PostgreSQL integration and recovery jobs. Neon staging compatibility remains ENVIRONMENT-UNVERIFIED until the connector can identify the authorized project without guessed identifiers, or the Owner explicitly supplies the intended project identity through a safe channel.
