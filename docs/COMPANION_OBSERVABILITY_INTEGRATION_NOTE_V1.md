# Companion Observability — Integration Note v1

The runtime telemetry seam is deliberately provider-neutral and local to the process. Persistent delivery may be added later without changing runtime lifecycle semantics.

Any future sink must preserve these boundaries:

- operational telemetry is observational, not authorization;
- no raw game payloads, chat content or user identifiers are emitted by default;
- bounded buffering/backpressure remains explicit;
- provider failure must not change Companion authorization state;
- audit/security truth remains separate from product telemetry.

This document does not claim persistent telemetry, external ingestion, or production readiness.